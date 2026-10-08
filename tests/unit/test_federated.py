from __future__ import annotations

from dataclasses import FrozenInstanceError
import inspect
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import polars as pl
import pytest
import torch
import torch.nn as nn
from flwr.common import (
    Code,
    Context,
    EvaluateRes,
    FitRes,
    RecordDict,
    Status,
    ndarrays_to_parameters,
)

from datp.artifacts import ArtifactLayout
from datp.config import BASE_CONFIG, ConvergenceConfig, ExperimentStage
from datp.core import TrainingCellId, resolve_device, set_seeds
from datp.data import (
    ClientData,
    ClientMetricKey,
    FederatedTensorLabel,
    Split,
    filename_for_split,
    split_path,
    validate_client_data,
    validate_tensor_input,
    write_artifact,
)
from datp.enums import (
    Activation,
    ArtifactFile,
    ConvergenceStatus,
    ConvergenceSummaryKey,
    DeviceType,
)
from datp.federated import (
    ALL_SPLITS,
    TRAINING_SPLITS,
    ClientFactoryConfig,
    ConvergenceMonitor,
    DatpClient,
    DatpFedAvg,
    TrainingResult,
    _client_ids,
    _score_dir,
    _scoring_data,
    build_model,
    check_object_store_capacity,
    derive_client_resources,
    df_to_tensor,
    discover_client_dirs,
    ensure_ray_memory_threshold,
    evaluate_benign,
    get_parameters,
    load_client_artifact,
    load_client_data,
    load_single_client_training_data,
    make_client_fn,
    release_freed_heap,
    run_fl_training,
    save_convergence_artifacts,
    set_parameters,
    train_local,
    validate_prepared_splits,
)
from datp.modeling import Autoencoder
from tests.fixtures import make_fl_cfg

_STAGE = ExperimentStage.NBAIOT_MAIN


class TestRunFlTrainingSignature:
    """run_fl_training function signature validation."""

    def test_accepts_output_layout_parameter(self) -> None:
        sig = inspect.signature(run_fl_training)
        p = sig.parameters.get("output_layout")
        assert p is not None, "run_fl_training must have output_layout parameter"
        assert p.default is None

    def test_accepts_base_dir_parameter(self) -> None:
        sig = inspect.signature(run_fl_training)
        p = sig.parameters.get("base_dir")
        assert p is not None, "run_fl_training must have base_dir parameter"
        assert p.default is None

    def test_accepts_prepared_dir_parameter(self) -> None:
        sig = inspect.signature(run_fl_training)
        p = sig.parameters.get("prepared_dir")
        assert p is not None
        assert p.default is None


class TestScoreDirRouting:
    """run_fl_training derives its score directory from the layout or base_dir."""

    def test_with_output_layout_uses_layout_score_dir(self, tmp_path: Path) -> None:
        layout = ArtifactLayout(base_dir=tmp_path, stage=_STAGE)
        expected = layout.score_cell(TrainingCellId(stage=_STAGE, seed=5)).score_dir

        assert _score_dir(_STAGE, 5, None, layout) == expected

    def test_with_base_dir_builds_layout_correctly(self, tmp_path: Path) -> None:
        layout = ArtifactLayout(base_dir=tmp_path, stage=_STAGE)
        expected = layout.score_cell(TrainingCellId(stage=_STAGE, seed=7)).score_dir

        assert _score_dir(_STAGE, 7, tmp_path, None) == expected

    def test_output_layout_takes_precedence_over_base_dir(self, tmp_path: Path) -> None:
        layout = ArtifactLayout(base_dir=tmp_path / "layout", stage=_STAGE)
        expected = layout.score_cell(TrainingCellId(stage=_STAGE, seed=2)).score_dir

        assert _score_dir(_STAGE, 2, tmp_path / "base", layout) == expected

    def test_requires_a_location(self) -> None:
        with pytest.raises(ValueError, match="base_dir or output_layout required"):
            _score_dir(_STAGE, 0, None, None)


def _write_client_dir(
    prepared_dir: Path, name: str, *, omit: str | None = None
) -> None:
    client_dir = prepared_dir / name
    client_dir.mkdir(parents=True)
    df = pl.DataFrame({"f0": [1.0], "f1": [2.0]})
    for split in Split:
        artifact = filename_for_split(split)
        if artifact != omit:
            write_artifact(df, client_dir / artifact)
    (client_dir / str(ArtifactFile.SCALER)).write_bytes(b"scaler")


def _client_data(*names: str) -> dict[str, ClientData]:
    return {
        name: ClientData(
            train=torch.zeros(4, 2),
            val=torch.zeros(2, 2),
            test_benign=torch.zeros(2, 2),
            test_attack=torch.zeros(2, 2),
        )
        for name in names
    }


class TestClientIds:
    def test_from_prepared_dir_sorted(self, tmp_path: Path) -> None:
        _write_client_dir(tmp_path, "client_b")
        _write_client_dir(tmp_path, "client_a")

        assert _client_ids({}, tmp_path) == ["client_a", "client_b"]

    def test_from_client_data_sorted(self) -> None:
        assert _client_ids(_client_data("z", "a"), None) == ["a", "z"]

    def test_prepared_dir_takes_precedence(self, tmp_path: Path) -> None:
        _write_client_dir(tmp_path, "disk_client")

        assert _client_ids(_client_data("memory_client"), tmp_path) == ["disk_client"]

    def test_raises_when_no_source(self) -> None:
        with pytest.raises(ValueError, match="No non-empty client_data"):
            _client_ids({}, None)


class TestValidatePreparedSplits:
    def test_accepts_complete_client(self, tmp_path: Path) -> None:
        _write_client_dir(tmp_path, "client_0")

        validate_prepared_splits(tmp_path, ["client_0"])

    def test_rejects_missing_test_attack(self, tmp_path: Path) -> None:
        _write_client_dir(
            tmp_path, "client_0", omit=filename_for_split(Split.TEST_ATTACK)
        )

        with pytest.raises(
            FileNotFoundError, match=filename_for_split(Split.TEST_ATTACK)
        ):
            validate_prepared_splits(tmp_path, ["client_0"])


def _make_ae(input_dim: int = 4, hidden_dims: list[int] | None = None) -> Autoencoder:
    """Helper to build a standard Autoencoder model for tests."""
    return Autoencoder(
        input_dim=input_dim,
        hidden_dims=hidden_dims or [3, 2],
        activation=Activation.RELU,
        use_bn=False,
    )


def _mock_cfg(
    local_epochs: int = 1, lr: float = 0.01, batch_size: int = 8
) -> MagicMock:
    """Helper to build a mock config for DatpClient initialization."""
    cfg = MagicMock()
    cfg.federation.local_epochs = local_epochs
    cfg.machine.batch_size_train = batch_size
    cfg.model.lr = lr
    return cfg


class TestDatpClientConstruction:
    """Tests verifying correct initialization and property parsing of DatpClient."""

    def test_stores_cid(self) -> None:
        """Verify that the client ID is correctly stored on construction."""
        client = DatpClient(
            cid="c0",
            model=_make_ae(),
            train_data=torch.randn(16, 4),
            cal_data=torch.randn(8, 4),
            cfg=_mock_cfg(),
        )
        assert client.cid == "c0"

    def test_stores_config_derived_values(self) -> None:
        """Verify client training hyperparameters match config values."""
        client = DatpClient(
            cid="c0",
            model=_make_ae(),
            train_data=torch.randn(16, 4),
            cal_data=torch.randn(8, 4),
            cfg=_mock_cfg(local_epochs=3, lr=0.05, batch_size=16),
        )
        assert client._local_epochs == 3
        assert client._batch_size == 16
        assert client._lr == pytest.approx(0.05)


class TestDatpClientShapeValidation:
    """Tests verifying input validation on training and calibration data tensors."""

    def test_rejects_1d_train_data(self) -> None:
        """Verify ValueError is raised if training data tensor is 1-D."""
        model = _make_ae()
        randn_value = torch.randn(16)
        randn_value_2 = torch.randn(8, 4)
        mock_cfg_value = _mock_cfg()
        with pytest.raises(ValueError, match="train_data must be 2-D"):
            DatpClient(
                cid="c0",
                model=model,
                train_data=randn_value,
                cal_data=randn_value_2,
                cfg=mock_cfg_value,
            )

    def test_rejects_3d_cal_data(self) -> None:
        """Verify ValueError is raised if calibration data tensor is 3-D."""
        model = _make_ae()
        randn_value = torch.randn(16, 4)
        randn_value_2 = torch.randn(8, 4, 2)
        mock_cfg_value = _mock_cfg()
        with pytest.raises(ValueError, match="cal_data must be 2-D"):
            DatpClient(
                cid="c1",
                model=model,
                train_data=randn_value,
                cal_data=randn_value_2,
                cfg=mock_cfg_value,
            )

    def test_rejects_empty_train_data(self) -> None:
        """Verify ValueError is raised if training data tensor is empty."""
        model = _make_ae()
        empty_value = torch.empty(0, 4)
        randn_value = torch.randn(8, 4)
        mock_cfg_value = _mock_cfg()
        with pytest.raises(ValueError, match="train_data must be non-empty"):
            DatpClient(
                cid="c0",
                model=model,
                train_data=empty_value,
                cal_data=randn_value,
                cfg=mock_cfg_value,
            )

    def test_rejects_nan_train_data(self) -> None:
        """Verify ValueError is raised if training data contains non-finite values."""
        model = _make_ae()
        data = torch.randn(16, 4)
        data[0, 0] = float("nan")
        randn_value = torch.randn(8, 4)
        mock_cfg_value = _mock_cfg()
        with pytest.raises(ValueError, match="non-finite"):
            DatpClient(
                cid="c0",
                model=model,
                train_data=data,
                cal_data=randn_value,
                cfg=mock_cfg_value,
            )


class TestDatpClientGetParameters:
    """Tests verifying parameter state retrieval via client API."""

    def test_result_matches_get_parameters_helper(self) -> None:
        """Verify client get_parameters returns same weights as direct helper."""
        model = _make_ae()
        client = DatpClient(
            cid="c0",
            model=model,
            train_data=torch.randn(16, 4),
            cal_data=torch.randn(8, 4),
            cfg=_mock_cfg(),
        )
        direct = get_parameters(model)
        via_client = client.get_parameters({})
        for a, b in zip(direct, via_client, strict=True):
            assert (a == b).all()


class TestDatpClientFit:
    """Tests verifying model training process and state changes inside client fit."""

    def test_returns_params_count_and_train_loss(self) -> None:
        """Verify client fit returns expected samples count, loss value, and parameters."""
        model = _make_ae()
        client = DatpClient(
            cid="c0",
            model=model,
            train_data=torch.randn(16, 4),
            cal_data=torch.randn(8, 4),
            cfg=_mock_cfg(local_epochs=2),
        )
        initial_params = get_parameters(model)
        result_params, n_train, metrics = client.fit(initial_params, {})

        assert n_train == 16
        assert ClientMetricKey.TRAIN_LOSS in metrics
        assert isinstance(metrics[ClientMetricKey.TRAIN_LOSS], float)
        assert not torch.isnan(torch.tensor(metrics[ClientMetricKey.TRAIN_LOSS]))
        assert len(result_params) == len(initial_params)

    def test_updates_model_parameters(self) -> None:
        """Verify fit updates model weights successfully."""
        model = _make_ae()
        client = DatpClient(
            cid="c0",
            model=model,
            train_data=torch.randn(32, 4),
            cal_data=torch.randn(8, 4),
            cfg=_mock_cfg(local_epochs=3),
        )
        params_before = get_parameters(model)
        client.fit(params_before, {})
        params_after = get_parameters(model)

        any_changed = any(
            not (a == b).all() for a, b in zip(params_before, params_after, strict=True)
        )
        assert any_changed, "Model parameters should change after fit"

    def test_sets_model_to_train_mode(self) -> None:
        """Verify fit sets PyTorch model to training mode."""
        model = _make_ae()
        model.eval()
        client = DatpClient(
            cid="c0",
            model=model,
            train_data=torch.randn(16, 4),
            cal_data=torch.randn(8, 4),
            cfg=_mock_cfg(local_epochs=1),
        )
        client.fit(get_parameters(model), {})
        assert model.training, "Model should be in train mode after fit"


class TestDatpClientEvaluate:
    """Tests verifying validation metrics computation inside client evaluate."""

    def test_returns_loss_count_and_val_loss_key(self) -> None:
        """Verify evaluate returns expected validation loss, sample count, and metrics dict."""
        model = _make_ae()
        client = DatpClient(
            cid="c0",
            model=model,
            train_data=torch.randn(16, 4),
            cal_data=torch.randn(8, 4),
            cfg=_mock_cfg(),
        )
        loss, count, metrics = client.evaluate(get_parameters(model), {})

        assert count == 8
        assert loss > 0.0
        assert ClientMetricKey.VAL_LOSS in metrics
        assert metrics[ClientMetricKey.VAL_LOSS] == pytest.approx(loss)

    def test_sets_model_to_eval_mode(self) -> None:
        """Verify evaluate sets PyTorch model to evaluation mode."""
        model = _make_ae()
        model.train()
        client = DatpClient(
            cid="c0",
            model=model,
            train_data=torch.randn(16, 4),
            cal_data=torch.randn(8, 4),
            cfg=_mock_cfg(),
        )
        client.evaluate(get_parameters(model), {})
        assert not model.training, "Model should be in eval mode after evaluate"

    def test_evaluate_does_not_change_model_parameters(self) -> None:
        """Confirm evaluate does not modify model parameters."""
        model = _make_ae()
        client = DatpClient(
            cid="c0",
            model=model,
            train_data=torch.randn(16, 4),
            cal_data=torch.randn(8, 4),
            cfg=_mock_cfg(),
        )
        params_before = get_parameters(model)
        client.evaluate(params_before, {})
        params_after = get_parameters(model)
        for a, b in zip(params_before, params_after, strict=True):
            assert (a == b).all(), "Evaluate should not modify model parameters"


class TestDatpClientDeterminism:
    """Tests verifying seed-based reproducibility for client-side training."""

    def test_same_seed_same_fit_result(self) -> None:
        """Verify identical seeds produce identical train loss under identical setup."""
        import copy

        set_seeds(42)
        model_a = _make_ae()
        data = torch.randn(16, 4)
        cal_data = torch.randn(8, 4)

        model_b = copy.deepcopy(model_a)

        client_a = DatpClient(
            cid="c0",
            model=model_a,
            train_data=data,
            cal_data=cal_data,
            cfg=_mock_cfg(local_epochs=2),
        )
        client_b = DatpClient(
            cid="c0",
            model=model_b,
            train_data=data,
            cal_data=cal_data,
            cfg=_mock_cfg(local_epochs=2),
        )

        set_seeds(42)
        _, _, m_a = client_a.fit(get_parameters(model_a), {})
        set_seeds(42)
        _, _, m_b = client_b.fit(get_parameters(model_b), {})

        assert m_a[ClientMetricKey.TRAIN_LOSS] == pytest.approx(
            m_b[ClientMetricKey.TRAIN_LOSS], abs=1e-6
        )


def _feed(monitor: ConvergenceMonitor, losses: list[float]) -> int | None:
    """Helper method to feed a list of losses into a ConvergenceMonitor."""
    for r, loss in enumerate(losses, start=1):
        monitor.record(loss)
        if monitor.should_stop(r):
            return r
    return None


class TestConvergenceTrigger:
    """Tests verifying that convergence triggers under stable/flat loss sequences."""

    def test_convergence_triggers_at_expected_round(self) -> None:
        """Verify convergence triggers correctly for a decaying loss sequence."""
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=100,
            relative_threshold=0.03,
            window=4,
        )

        losses = [1.0, 0.8, 0.6, 0.5, 0.4, 0.35, 0.32, 0.30]
        losses += [0.30] * 10

        stop_round = _feed(monitor, losses)

        assert stop_round is not None
        assert stop_round >= 5
        assert stop_round >= 2 * 4
        assert monitor.converged_round == stop_round

    def test_gradual_convergence(self) -> None:
        """Verify convergence triggers for a gradually decaying sequence."""
        monitor = ConvergenceMonitor(
            rounds_initial=10,
            rounds_max=200,
            relative_threshold=0.05,
            window=5,
        )
        losses = [1.0 * (0.95**i) for i in range(30)]
        losses += [losses[-1]] * 20

        stop_round = _feed(monitor, losses)

        assert stop_round is not None
        assert stop_round >= 10
        assert stop_round >= 2 * 5

    def test_window_mean_comparison_differs_from_first_last(self) -> None:
        """Confirm window comparison checks are mean-based, not endpoint-based."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=100,
            relative_threshold=0.02,
            window=4,
        )

        losses = [1.0, 0.9, 0.8, 0.7, 0.7, 0.8, 0.7, 0.7]
        stop_round = _feed(monitor, losses)

        assert stop_round is None

    def test_flat_sequence_converges_with_mean_comparison(self) -> None:
        """Verify that flat sequence triggers convergence."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=100,
            relative_threshold=0.02,
            window=4,
        )

        losses = [0.5] * 8
        stop_round = _feed(monitor, losses)
        assert stop_round == 8


class TestRoundsInitialGuard:
    """Tests verifying that initial training rounds are guarded from stopping early."""

    def test_convergence_does_not_fire_before_rounds_initial(self) -> None:
        """Ensure convergence does not stop training before rounds_initial is reached."""
        monitor = ConvergenceMonitor(
            rounds_initial=20,
            rounds_max=100,
            relative_threshold=0.05,
            window=4,
        )
        flat_losses = [0.5] * 19

        for r, loss in enumerate(flat_losses, start=1):
            monitor.record(loss)
            assert not monitor.should_stop(r), (
                f"should_stop fired at round {r}, before rounds_initial=20"
            )

        monitor.record(0.5)
        assert monitor.should_stop(20)


class TestHardCap:
    """Tests verifying the max rounds cap behavior."""

    def test_convergence_hard_cap_at_rounds_max(self) -> None:
        """Verify convergence forces stopping at rounds_max."""
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=10,
            relative_threshold=0.001,
            window=4,
        )
        losses = [1.0 - 0.05 * i for i in range(10)]

        stop_round = _feed(monitor, losses)

        assert stop_round == 10, f"Expected hard cap at round 10, got {stop_round}"

    def test_hard_cap_does_not_require_recorded_losses(self) -> None:
        """Verify hard cap is enforced even if no loss records are available."""
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=10,
            relative_threshold=0.03,
            window=4,
        )
        assert monitor.should_stop(10)


class TestInsufficientHistory:
    """Tests verifying history length requirements."""

    def test_convergence_does_not_fire_without_2x_window(self) -> None:
        """Ensure convergence requires history length of at least twice the window size."""
        window = 4
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=100,
            relative_threshold=0.05,
            window=window,
        )

        for r in range(1, 2 * window):
            monitor.record(0.5)
            assert not monitor.should_stop(r), (
                f"should_stop fired with only {r} recorded losses "
                f"(need 2*window={2 * window})"
            )

        monitor.record(0.5)
        assert monitor.should_stop(2 * window)


class TestFiniteLossValidation:
    """Tests verifying input validation for loss values."""

    def test_nan_loss_raises(self) -> None:
        """Verify record raises ValueError if input loss is NaN."""
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=100,
            relative_threshold=0.03,
            window=4,
        )
        float_value = float("nan")
        with pytest.raises(ValueError, match="Non-finite loss"):
            monitor.record(float_value)

    def test_inf_loss_raises(self) -> None:
        """Verify record raises ValueError if input loss is positive infinity."""
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=100,
            relative_threshold=0.03,
            window=4,
        )
        float_value = float("inf")
        with pytest.raises(ValueError, match="Non-finite loss"):
            monitor.record(float_value)

    def test_negative_inf_loss_raises(self) -> None:
        """Verify record raises ValueError if input loss is negative infinity."""
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=100,
            relative_threshold=0.03,
            window=4,
        )
        float_value = float("-inf")
        with pytest.raises(ValueError, match="Non-finite loss"):
            monitor.record(float_value)


class TestStrategyMonitorFromConfig:
    """Tests verifying DatpFedAvg builds its ConvergenceMonitor from DatpConfig."""

    def test_monitor_built_from_config(self) -> None:
        """Verify monitor is correctly initialized using values from config parser."""
        from datp.config import BASE_CONFIG, ConvergenceConfig, FederationConfig

        cfg = BASE_CONFIG.model_copy(
            update={
                "federation": FederationConfig(
                    local_epochs=5,
                    convergence=ConvergenceConfig(
                        rounds_initial=40,
                        rounds_max=150,
                        relative_threshold=0.005,
                        window=10,
                        round_timeout_s=300,
                    ),
                ),
            }
        )
        monitor = DatpFedAvg(
            cfg, ndarrays_to_parameters([np.zeros((2, 2), dtype=np.float32)]), 1
        ).convergence_monitor

        for r in range(1, 40):
            monitor.record(0.5)
            assert not monitor.should_stop(r), (
                f"should_stop fired at round {r} < rounds_initial=40"
            )

        monitor.record(0.5)
        assert monitor.should_stop(40)
        assert monitor.converged_round == 40


class TestBaseConfigDefaults:
    """Tests verifying the default convergence configuration parameters."""

    def test_base_config_relative_threshold_is_0005(self) -> None:
        """Verify default relative threshold setting is 0.005."""
        from datp.config import BASE_CONFIG

        assert BASE_CONFIG.federation.convergence.relative_threshold == pytest.approx(
            0.005
        )

    def test_base_config_window_is_10(self) -> None:
        """Verify default evaluation sliding window setting is 10."""
        from datp.config import BASE_CONFIG

        assert BASE_CONFIG.federation.convergence.window == 10

    def test_base_config_rounds_initial_is_40(self) -> None:
        """Verify default initial rounds setting is 40."""
        from datp.config import BASE_CONFIG

        assert BASE_CONFIG.federation.convergence.rounds_initial == 40

    def test_base_config_rounds_max_is_150(self) -> None:
        """Verify default maximum rounds setting is 150."""
        from datp.config import BASE_CONFIG

        assert BASE_CONFIG.federation.convergence.rounds_max == 150


class TestValidationErrors:
    """Tests verifying monitor validation logic on settings inputs."""

    def test_rounds_initial_below_one(self) -> None:
        """Verify ValueError is raised if rounds_initial is less than 1."""
        with pytest.raises(ValueError, match=r"Invalid convergence settings"):
            ConvergenceMonitor(
                rounds_initial=0,
                rounds_max=10,
                relative_threshold=0.03,
                window=4,
            )

    def test_rounds_max_below_rounds_initial(self) -> None:
        """Verify ValueError is raised if rounds_max is less than rounds_initial."""
        with pytest.raises(ValueError, match=r"Invalid convergence settings"):
            ConvergenceMonitor(
                rounds_initial=20,
                rounds_max=10,
                relative_threshold=0.03,
                window=4,
            )

    def test_window_below_two(self) -> None:
        """Verify ValueError is raised if sliding window size is less than 2."""
        with pytest.raises(ValueError, match=r"Invalid convergence settings"):
            ConvergenceMonitor(
                rounds_initial=5,
                rounds_max=50,
                relative_threshold=0.03,
                window=1,
            )


class TestConvergedRoundLogged:
    """Tests verifying tracking of the converged round milestone."""

    def test_converged_round_logged(self) -> None:
        """Verify converged_round remains None until the milestone criteria is met."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=10,
            relative_threshold=0.05,
            window=2,
        )
        for r in range(1, 4):
            monitor.record(0.5)
            monitor.should_stop(r)

        assert monitor.converged_round is None

        monitor.record(0.5)
        assert monitor.should_stop(4)
        assert monitor.converged_round == 4

    def test_converged_round_none_before_convergence(self) -> None:
        """Verify converged_round is None before convergence fires."""
        monitor = ConvergenceMonitor(
            rounds_initial=10,
            rounds_max=100,
            relative_threshold=0.001,
            window=4,
        )
        monitor.record(1.0)
        monitor.record(0.5)
        monitor.should_stop(2)

        assert monitor.converged_round is None

    def test_first_converged_round_is_preserved(self) -> None:
        """Ensure the very first round milestone that satisfies convergence is preserved."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=100,
            relative_threshold=0.05,
            window=2,
        )
        for _ in range(1, 5):
            monitor.record(0.5)

        assert monitor.should_stop(4)
        assert monitor.converged_round == 4

        monitor.record(0.5)
        assert monitor.should_stop(5)
        assert monitor.converged_round == 4


class TestPreweightedScalar:
    """Tests verifying convergence monitor updates with pre-calculated losses."""

    def test_monitor_accepts_preweighted_scalar(self) -> None:
        """Verify monitor successfully processes external loss sequences."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.05,
            window=4,
        )

        preweighted = [0.123, 0.119, 0.115, 0.114, 0.114, 0.114, 0.114, 0.114]

        for r, loss in enumerate(preweighted, start=1):
            monitor.record(loss)

        assert monitor.num_recorded == len(preweighted)
        assert monitor.should_stop(len(preweighted))

    def test_num_recorded_tracks_calls(self) -> None:
        """Verify num_recorded increments on every record call."""
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=50,
            relative_threshold=0.03,
            window=4,
        )
        assert monitor.num_recorded == 0
        monitor.record(0.5)
        assert monitor.num_recorded == 1
        monitor.record(0.4)
        assert monitor.num_recorded == 2


class TestEdgeCases:
    """Tests verifying edge cases such as near-zero loss values and odd window sizes."""

    def test_near_zero_loss_converges(self) -> None:
        """Verify convergence succeeds for loss values close to zero."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.05,
            window=4,
        )

        losses = [1e-15] * 8
        stop_round = _feed(monitor, losses)
        assert stop_round is not None

    def test_window_odd_size(self) -> None:
        """Verify convergence monitor works correctly when sliding window has odd size."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.05,
            window=5,
        )

        losses = [0.5] * 10
        stop_round = _feed(monitor, losses)
        assert stop_round is not None


class TestConvergenceAlgorithm:
    """Tests verifying the similarity checking logic inside the monitor."""

    def test_no_convergence_with_diverging_windows(self) -> None:
        """Ensure no convergence fires when consecutive window means diverge."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.05,
            window=4,
        )

        losses = [1.0, 0.9, 0.8, 0.7, 0.3, 0.3, 0.3, 0.3]
        for r, loss in enumerate(losses, start=1):
            monitor.record(loss)
        assert not monitor.should_stop(8)

    def test_converges_when_windows_similar(self) -> None:
        """Verify convergence triggers when consecutive window means are within relative threshold."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.05,
            window=4,
        )

        losses = [0.50, 0.50, 0.50, 0.50, 0.49, 0.49, 0.49, 0.49]
        for r, loss in enumerate(losses, start=1):
            monitor.record(loss)
        assert monitor.should_stop(8)

    def test_latest_relative_change_tracks_window_means(self) -> None:
        """Verify latest_relative_change correctly computes the relative change between window means."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.50,
            window=4,
        )

        losses = [2.0, 2.0, 2.0, 2.0, 1.8, 1.8, 1.8, 1.8]
        for r, loss in enumerate(losses, start=1):
            monitor.record(loss)
        monitor.should_stop(8)
        assert monitor.latest_relative_change == pytest.approx(0.10, abs=1e-9)


class TestAggregateEvaluateGuards:
    """Tests verifying strategy interaction and evaluation safeguards."""

    def _make_strategy(self) -> DatpFedAvg:
        """Helper to instantiate a DatpFedAvg strategy (rounds_initial=1, window=2)."""
        return DatpFedAvg(
            make_fl_cfg(rounds=10),
            ndarrays_to_parameters([np.zeros((2, 2), dtype=np.float32)]),
            1,
        )

    def test_no_results_returns_none_and_does_not_record(self) -> None:
        """Verify strategy returns None evaluation loss and does not record if results list is empty."""
        strategy = self._make_strategy()
        monitor = strategy.convergence_monitor

        loss, metrics = strategy.aggregate_evaluate(
            server_round=1, results=[], failures=[]
        )

        assert loss is None
        assert metrics == {}
        assert monitor.num_recorded == 0
        assert monitor.loss_history == []

    def test_zero_total_examples_returns_none_and_does_not_record(self) -> None:
        """Verify strategy ignores evaluation results with zero client samples."""
        from unittest.mock import MagicMock

        strategy = self._make_strategy()
        monitor = strategy.convergence_monitor
        proxy = MagicMock()
        result = MagicMock()
        result.num_examples = 0
        result.loss = 0.5

        loss, metrics = strategy.aggregate_evaluate(
            server_round=1, results=[(proxy, result)], failures=[]
        )

        assert loss is None
        assert metrics == {}
        assert monitor.num_recorded == 0
        assert monitor.loss_history == []

    def test_valid_weighted_aggregation_records(self) -> None:
        """Verify strategy correctly computes weighted aggregate loss and updates the monitor."""
        from unittest.mock import MagicMock

        strategy = self._make_strategy()
        monitor = strategy.convergence_monitor
        proxy_a = MagicMock()
        res_a = MagicMock()
        res_a.num_examples = 100
        res_a.loss = 0.4
        proxy_b = MagicMock()
        res_b = MagicMock()
        res_b.num_examples = 300
        res_b.loss = 0.8

        loss, metrics = strategy.aggregate_evaluate(
            server_round=1, results=[(proxy_a, res_a), (proxy_b, res_b)], failures=[]
        )

        assert loss == pytest.approx((0.4 * 100 + 0.8 * 300) / 400)
        assert metrics["weighted_val_loss"] == pytest.approx(loss)
        assert monitor.num_recorded == 1
        assert monitor.loss_history == [pytest.approx(loss)]


class TestConvergenceScheduling:
    """Tests verifying training round scheduling flags after convergence has been met."""

    def test_strategy_skips_fit_and_evaluate_after_convergence(self) -> None:
        """Verify strategy returns empty instructions list once convergence stopped flag is set."""
        from unittest.mock import MagicMock

        strategy = DatpFedAvg(
            make_fl_cfg(rounds=10),
            ndarrays_to_parameters([np.zeros((2, 2), dtype=np.float32)]),
            1,
        )
        monitor = strategy.convergence_monitor

        mock_proxy = MagicMock()
        mock_result = MagicMock()
        mock_result.num_examples = 100
        mock_result.loss = 0.5

        for _ in range(1, 4):
            monitor.record(0.5)
        strategy.aggregate_evaluate(
            server_round=4,
            results=[(mock_proxy, mock_result)],
            failures=[],
        )

        assert strategy.stopped is True
        assert strategy.configure_fit(5, MagicMock(), MagicMock()) == []
        assert strategy.configure_evaluate(5, MagicMock(), MagicMock()) == []


def _make_conv_cfg(
    *,
    rounds_initial: int = 5,
    rounds_max: int = 100,
    relative_threshold: float = 0.03,
    window: int = 4,
    round_timeout_s: float = 3600.0,
) -> ConvergenceConfig:
    """Helper to build a ConvergenceConfig instance."""
    return ConvergenceConfig(
        rounds_initial=rounds_initial,
        rounds_max=rounds_max,
        relative_threshold=relative_threshold,
        window=window,
        round_timeout_s=round_timeout_s,
    )


def _monitor(
    losses: list[float], converged_round: int | None, criterion: float | None
) -> ConvergenceMonitor:
    """Build a monitor carrying the given loss history and convergence state."""
    monitor = ConvergenceMonitor(1, 100, 0.03, 2)
    for loss in losses:
        monitor.record(loss)
    monitor._converged_round = converged_round
    monitor._latest_relative_change = criterion
    return monitor


class TestSaveConvergenceArtifacts:
    """Tests verifying save_convergence_artifacts output files and schemas."""

    def test_writes_both_files_atomically(self, tmp_path: Path) -> None:
        """Confirm both convergence curve and summary files are written atomically."""
        snapshot = _monitor([1.0, 0.8, 0.6], 3, 0.05)
        cfg = _make_conv_cfg()

        save_convergence_artifacts(tmp_path, snapshot, cfg)

        curve = tmp_path / ArtifactFile.CONVERGENCE_CURVE
        summary = tmp_path / ArtifactFile.CONVERGENCE_SUMMARY
        assert curve.exists()
        assert summary.exists()
        assert not (tmp_path / "convergence_curve.csv.tmp").exists()
        assert not (tmp_path / "convergence_summary.json.tmp").exists()

    def test_curve_contains_expected_columns(self, tmp_path: Path) -> None:
        """Verify convergence curve CSV contains the canonical columns and round indexes."""
        snapshot = _monitor([1.0, 0.8], 2, 0.01)
        save_convergence_artifacts(tmp_path, snapshot, _make_conv_cfg())

        df = pd.read_csv(tmp_path / ArtifactFile.CONVERGENCE_CURVE)
        assert list(df.columns) == ["round", "fedavg_weighted_benign_val_loss"]
        assert len(df) == 2
        assert df["round"].tolist() == [1, 2]

    def test_summary_converged(self, tmp_path: Path) -> None:
        """Verify convergence summary JSON entries when the simulation converged."""
        snapshot = _monitor([2.0, 1.5, 1.0], 3, 0.02)
        save_convergence_artifacts(tmp_path, snapshot, _make_conv_cfg())

        payload = json.loads((tmp_path / ArtifactFile.CONVERGENCE_SUMMARY).read_text())
        assert payload[ConvergenceSummaryKey.CONVERGENCE_ROUND] == 3
        assert payload[ConvergenceSummaryKey.CONVERGENCE_CRITERION] == pytest.approx(
            0.02
        )
        assert (
            payload[ConvergenceSummaryKey.CONVERGENCE_STATUS]
            == ConvergenceStatus.CONVERGED
        )
        assert payload[ConvergenceSummaryKey.ACTUAL_ROUNDS] == 3
        assert payload[ConvergenceSummaryKey.ROUNDS_INITIAL] == 5

    def test_summary_not_converged(self, tmp_path: Path) -> None:
        """Verify convergence summary JSON entries when the simulation did not converge."""
        snapshot = _monitor([3.0, 2.9, 2.8], None, None)
        save_convergence_artifacts(tmp_path, snapshot, _make_conv_cfg())

        payload = json.loads((tmp_path / ArtifactFile.CONVERGENCE_SUMMARY).read_text())
        assert payload[ConvergenceSummaryKey.CONVERGENCE_ROUND] is None
        assert payload[ConvergenceSummaryKey.CONVERGENCE_CRITERION] is None
        assert (
            payload[ConvergenceSummaryKey.CONVERGENCE_STATUS]
            == ConvergenceStatus.NOT_CONVERGED
        )

    def test_empty_loss_history(self, tmp_path: Path) -> None:
        """Verify convergence summary behavior when history list is empty."""
        snapshot = _monitor([], None, None)
        save_convergence_artifacts(tmp_path, snapshot, _make_conv_cfg())

        payload = json.loads((tmp_path / ArtifactFile.CONVERGENCE_SUMMARY).read_text())
        assert payload[ConvergenceSummaryKey.ACTUAL_ROUNDS] == 0
        assert payload[ConvergenceSummaryKey.WEIGHTED_LOSS] == []


_MODULE = "federated.data_loading"


def _write_client_splits(
    client_dir: Path,
    splits: tuple[Split, ...] = (Split.TRAIN, Split.CAL),
    n_features: int = 4,
    n_rows: int = 20,
) -> None:
    """Helper to write CSV parquet artifacts for various splits of a client."""
    client_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    arr = rng.standard_normal((n_rows, n_features))
    for split in splits:
        df = pl.DataFrame({f"f{i}": arr[:, i] for i in range(n_features)})
        write_artifact(df, split_path(client_dir, split))


class TestReleaseFreedHeap:
    """Tests verifying the memory garbage collection smoke test."""

    def test_smoke(self) -> None:
        """Verify that release_freed_heap executes without errors."""
        release_freed_heap()


class TestTrainingSplits:
    """Tests verifying definition of TRAINING_SPLITS."""

    def test_only_train_and_cal(self) -> None:
        """Confirm TRAINING_SPLITS consists exactly of train and cal splits."""
        assert TRAINING_SPLITS == (Split.TRAIN, Split.CAL)

    def test_test_splits_not_in_training(self) -> None:
        """Verify test splits are absent from training split definitions."""
        assert Split.TEST_BENIGN not in TRAINING_SPLITS
        assert Split.TEST_ATTACK not in TRAINING_SPLITS


class TestAllSplits:
    """Tests verifying the full set of split definitions."""

    def test_all_four_splits(self) -> None:
        """Verify that all four splits (train, cal, test_benign, test_attack) are present."""
        assert set(ALL_SPLITS) == {
            Split.TRAIN,
            Split.CAL,
            Split.TEST_BENIGN,
            Split.TEST_ATTACK,
        }

    def test_all_splits_is_superset_of_training(self) -> None:
        """Ensure all splits tuple contains the training splits subset."""
        assert set(TRAINING_SPLITS).issubset(set(ALL_SPLITS))


class TestDiscoverClientDirs:
    """Tests verifying discovery of client data directories."""

    def test_finds_client_directories(self, tmp_path: Path) -> None:
        """Verify client directories containing train split are found."""
        for name in ("client_a", "client_b"):
            _write_client_splits(tmp_path / name)

        dirs = discover_client_dirs(tmp_path)
        assert {d.name for d in dirs} == {"client_a", "client_b"}

    def test_skips_directories_without_train(self, tmp_path: Path) -> None:
        """Verify directories without train parquet files are skipped."""
        _write_client_splits(tmp_path / "good")
        (tmp_path / "bad").mkdir()
        (tmp_path / "bad" / "other.parquet").write_bytes(b"x")

        dirs = discover_client_dirs(tmp_path)
        assert {d.name for d in dirs} == {"good"}

    def test_empty_directory_raises(self, tmp_path: Path) -> None:
        """Ensure FileNotFoundError is raised if no directories exist."""
        with pytest.raises(FileNotFoundError, match="No client directories"):
            discover_client_dirs(tmp_path)

    def test_no_directories_raises(self, tmp_path: Path) -> None:
        """Ensure FileNotFoundError is raised if only non-directory files are present."""
        (tmp_path / "not_a_dir.txt").write_text("")
        with pytest.raises(FileNotFoundError, match="No client directories"):
            discover_client_dirs(tmp_path)

    def test_sorts_output(self, tmp_path: Path) -> None:
        """Verify discovered client directories are returned in sorted order."""
        for name in ("zebra", "alpha", "middle"):
            _write_client_splits(tmp_path / name)
        dirs = discover_client_dirs(tmp_path)
        names = [d.name for d in dirs]
        assert names == sorted(names)


class TestLoadClientArtifact:
    """Tests verifying single artifact file loading."""

    def test_loads_parquet(self, tmp_path: Path) -> None:
        """Verify loading an existing parquet file returns a Polars DataFrame."""
        client_dir = tmp_path / "c1"
        client_dir.mkdir()
        df_in = pl.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        write_artifact(df_in, split_path(client_dir, Split.TRAIN))

        df_out = load_client_artifact(client_dir, Split.TRAIN)
        assert df_out.shape == (2, 2)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Verify FileNotFoundError is raised if the target split artifact is missing."""
        client_dir = tmp_path / "c1"
        client_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="Missing"):
            load_client_artifact(client_dir, Split.CAL)


class TestDfToTensor:
    """Tests verifying conversion of DataFrames to PyTorch float32 tensors."""

    def test_from_polars(self) -> None:
        """Verify conversion of a Polars DataFrame to a float32 tensor."""
        df = pl.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        t = df_to_tensor(df, torch.device(DeviceType.CPU))
        assert t.shape == (2, 2)
        assert t.dtype == torch.float32
        assert torch.allclose(t, torch.tensor([[1.0, 3.0], [2.0, 4.0]]))

    def test_from_numpy(self) -> None:
        """Verify conversion of a NumPy array to a float32 tensor."""
        arr = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64)
        t = df_to_tensor(arr, torch.device(DeviceType.CPU))
        assert t.shape == (2, 2)
        assert t.dtype == torch.float32

    def test_empty_dataframe(self) -> None:
        """Verify empty DataFrame converts to empty tensor of same column dimension."""
        df = pl.DataFrame({"a": [], "b": []}, schema={"a": pl.Float64, "b": pl.Float64})
        t = df_to_tensor(df, torch.device(DeviceType.CPU))
        assert t.shape == (0, 2)


class TestLoadSingleClientTrainingData:
    """Tests verifying training data loading for a single client directory."""

    def test_loads_train_and_cal(self, tmp_path: Path) -> None:
        """Verify loading training and calibration splits for a client."""
        _write_client_splits(tmp_path, splits=(Split.TRAIN, Split.CAL))
        train_t, cal_t = load_single_client_training_data(
            tmp_path, torch.device(DeviceType.CPU)
        )
        assert train_t.shape == (20, 4)
        assert cal_t.shape == (20, 4)
        assert train_t.dtype == torch.float32

    def test_repeated_loads_reuse_cached_tensors(self, tmp_path: Path) -> None:
        """Verify each client's data is read from disk once per process."""
        _write_client_splits(tmp_path, splits=(Split.TRAIN, Split.CAL))
        device = torch.device(DeviceType.CPU)
        first = load_single_client_training_data(tmp_path, device)
        second = load_single_client_training_data(tmp_path, device)
        assert first[0] is second[0]
        assert first[1] is second[1]

    def test_missing_cal_raises(self, tmp_path: Path) -> None:
        """Ensure FileNotFoundError is raised if calibration split is missing."""
        _write_client_splits(tmp_path, splits=(Split.TRAIN,))
        device_value = torch.device(DeviceType.CPU)
        with pytest.raises(FileNotFoundError):
            load_single_client_training_data(tmp_path, device_value)


class TestLoadClientData:
    """Tests verifying multi-client split directory loading."""

    def test_loads_training_splits(self, tmp_path: Path) -> None:
        """Verify loading only the training splits for all client folders."""
        for name in ("c1", "c2"):
            _write_client_splits(tmp_path / name, splits=TRAINING_SPLITS)

        data = load_client_data(
            tmp_path, device=torch.device(DeviceType.CPU), splits=TRAINING_SPLITS
        )
        assert sorted(data.keys()) == ["c1", "c2"]
        for cd in data.values():
            assert cd.train.shape == (20, 4)
            assert cd.val.shape == (20, 4)
            assert cd.test_benign.numel() == 0
            assert cd.test_attack.numel() == 0

    def test_loads_all_splits(self, tmp_path: Path) -> None:
        """Verify loading all four splits for all client folders."""
        all_splits = (Split.TRAIN, Split.CAL, Split.TEST_BENIGN, Split.TEST_ATTACK)
        _write_client_splits(tmp_path / "c1", splits=all_splits)

        data = load_client_data(
            tmp_path, device=torch.device(DeviceType.CPU), splits=ALL_SPLITS
        )
        cd = data["c1"]
        assert cd.train.shape == (20, 4)
        assert cd.val.shape == (20, 4)
        assert cd.test_benign.shape == (20, 4)
        assert cd.test_attack.shape == (20, 4)

    def test_loads_subset_of_splits(self, tmp_path: Path) -> None:
        """Verify loading only the requested splits subset for client folders."""
        _write_client_splits(
            tmp_path / "c1", splits=(Split.TRAIN, Split.CAL, Split.TEST_BENIGN)
        )

        data = load_client_data(
            tmp_path,
            device=torch.device(DeviceType.CPU),
            splits=(Split.TRAIN, Split.CAL),
        )
        cd = data["c1"]
        assert cd.train.shape == (20, 4)
        assert cd.val.shape == (20, 4)
        assert cd.test_benign.numel() == 0

    def test_empty_features_raises(self, tmp_path: Path) -> None:
        """Ensure ValueError is raised if loaded splits have zero column dimension."""
        client_dir = tmp_path / "c1"
        client_dir.mkdir()
        df = pl.DataFrame({})
        write_artifact(df, split_path(client_dir, Split.TRAIN))

        device_value = torch.device(DeviceType.CPU)
        with pytest.raises(ValueError, match="0 columns"):
            load_client_data(tmp_path, device=device_value, splits=TRAINING_SPLITS)

    def test_device_is_respected(self, tmp_path: Path) -> None:
        """Verify tensors are loaded onto the requested PyTorch device."""
        _write_client_splits(tmp_path / "c1", splits=TRAINING_SPLITS)

        data = load_client_data(
            tmp_path, device=torch.device(DeviceType.CPU), splits=TRAINING_SPLITS
        )
        cd = data["c1"]
        assert cd.train.device.type == DeviceType.CPU
        assert cd.val.device.type == DeviceType.CPU


def _make_cfg() -> MagicMock:
    """Helper to build a mock config with preset model properties."""
    cfg = MagicMock()
    cfg.model.input_dim = 4
    cfg.model.encoder_dims = [3, 2]
    cfg.model.activation = Activation.RELU
    cfg.model.use_bn = False
    cfg.model.lr = 0.01
    cfg.federation.local_epochs = 1
    cfg.machine.batch_size_train = 8
    cfg.machine.require_cuda = False
    return cfg


def _make_client_data() -> dict[str, ClientData]:
    """Helper to generate a dictionary of client identifiers to ClientData."""
    return {
        "client_a": ClientData(
            train=torch.randn(16, 4),
            val=torch.randn(8, 4),
            test_benign=torch.randn(8, 4),
            test_attack=torch.randn(8, 4),
        ),
        "client_b": ClientData(
            train=torch.randn(16, 4),
            val=torch.randn(8, 4),
            test_benign=torch.randn(8, 4),
            test_attack=torch.randn(8, 4),
        ),
    }


def _make_context(partition_id: int) -> Context:
    """Helper to create a Flower Context for client instantiations."""
    return Context(
        run_id=0,
        node_id=0,
        node_config={"partition-id": str(partition_id)},
        state=RecordDict(),
        run_config={},
    )


class TestBuildModel:
    """Tests verifying build_model parser mapping and property validation."""

    def test_returns_autoencoder(self) -> None:
        """Verify that build_model returns an Autoencoder network by default."""
        cfg = _make_cfg()
        model = build_model(cfg)
        assert model is not None
        assert hasattr(model, "encoder")
        assert hasattr(model, "decoder")

    def test_respects_input_dim(self) -> None:
        """Verify that the model first layer input size matches config input_dim."""
        cfg = _make_cfg()
        model = build_model(cfg)

        first_linear = model.encoder[0]
        assert first_linear.in_features == 4

    def test_respects_hidden_dims(self) -> None:
        """Verify that the number of hidden encoder layers matches config hidden dimensions."""
        cfg = _make_cfg()
        cfg.model.encoder_dims = [8, 4]
        model = build_model(cfg)

        linear_layers = [m for m in model.encoder if isinstance(m, torch.nn.Linear)]
        assert len(linear_layers) >= 2

    def test_respects_activation(self) -> None:
        """Verify that the model uses the activation function specified in config."""
        cfg = _make_cfg()
        cfg.model.activation = Activation.TANH
        model = build_model(cfg)
        activations = [m for m in model.encoder if isinstance(m, torch.nn.Tanh)]
        assert len(activations) >= 1

    def test_respects_use_bn(self) -> None:
        """Verify that batch normalization layers are added when enabled in config."""
        cfg = _make_cfg()
        cfg.model.use_bn = True
        model = build_model(cfg)
        bn_layers = [m for m in model.encoder if isinstance(m, torch.nn.BatchNorm1d)]
        assert len(bn_layers) >= 1

    def test_no_bn_when_disabled(self) -> None:
        """Verify that batch normalization layers are absent when disabled in config."""
        cfg = _make_cfg()
        cfg.model.use_bn = False
        model = build_model(cfg)
        bn_layers = [m for m in model.encoder if isinstance(m, torch.nn.BatchNorm1d)]
        assert len(bn_layers) == 0


class TestMakeClientFn:
    """Tests verifying client function generation in memory-only mode."""

    def test_returns_callable(self) -> None:
        """Verify that make_client_fn returns a callable client generator."""
        cfg = _make_cfg()
        client_data = _make_client_data()
        client_ids = sorted(client_data.keys())
        fn = make_client_fn(
            client_data,
            ClientFactoryConfig(
                client_ids=client_ids,
                cfg=cfg,
                device=torch.device(DeviceType.CPU),
                seed=0,
            ),
        )
        assert callable(fn)

    def test_default_client_cls(self) -> None:
        """Verify that invoking the generated function returns a client instance."""
        cfg = _make_cfg()
        client_data = _make_client_data()
        client_ids = sorted(client_data.keys())
        fn = make_client_fn(
            client_data,
            ClientFactoryConfig(
                client_ids=client_ids,
                cfg=cfg,
                device=torch.device(DeviceType.CPU),
                seed=0,
            ),
        )
        client = fn(_make_context(0))
        assert client is not None

    def test_partition_id_maps_to_correct_client(self) -> None:
        """Verify partition IDs map to correct client indices."""
        cfg = _make_cfg()
        client_data = _make_client_data()
        client_ids = sorted(client_data.keys())

        fn = make_client_fn(
            client_data,
            ClientFactoryConfig(
                client_ids=client_ids,
                cfg=cfg,
                device=torch.device(DeviceType.CPU),
                seed=0,
            ),
        )

        fn(_make_context(0))
        fn(_make_context(1))

    def test_required_cuda_validates_client_model(self) -> None:
        cfg = _make_cfg()
        cfg.machine.require_cuda = True
        client_data = _make_client_data()
        with patch("datp.federated.validate_model_on_cuda") as validate:
            make_client_fn(
                client_data,
                ClientFactoryConfig(
                    client_ids=sorted(client_data),
                    cfg=cfg,
                    device=torch.device(DeviceType.CPU),
                    seed=0,
                ),
            )(_make_context(0))

        validate.assert_called_once()


class TestMakeClientFnPreparedDir:
    """Tests verifying client function generation from disk directory."""

    def test_uses_discover_and_load(self, tmp_path: Path) -> None:
        """Verify client factory loads data from disk when prepared_dir is set."""
        cfg = _make_cfg()
        client_ids = ["client_a", "client_b"]
        client_data: dict[str, ClientData] = {}

        for cid in client_ids:
            d = tmp_path / cid
            d.mkdir()

        train_t = torch.randn(8, 4)
        cal_t = torch.randn(4, 4)

        with (
            patch(
                "datp.federated.load_single_client_training_data",
                return_value=(train_t, cal_t),
            ),
            patch(
                "datp.federated.discover_client_dirs",
                return_value=[tmp_path / cid for cid in client_ids],
            ),
        ):
            fn = make_client_fn(
                client_data,
                ClientFactoryConfig(
                    client_ids=client_ids,
                    cfg=cfg,
                    device=torch.device(DeviceType.CPU),
                    prepared_dir=tmp_path,
                    seed=0,
                ),
            )
            client = fn(_make_context(0))
            assert client is not None


class TestPreparedDirUpfrontValidation:
    """Tests verifying client folder existence checks on initialization."""

    def test_missing_client_dir_raises_upfront(self, tmp_path: Path) -> None:
        """Ensure upfront configuration check raises FileNotFoundError if directories are missing."""
        cfg = _make_cfg()
        client_ids = ["client_a", "client_b", "client_missing"]
        client_data: dict[str, ClientData] = {}

        import pytest

        with patch(
            "datp.federated.discover_client_dirs",
            return_value=[tmp_path / "client_a", tmp_path / "client_b"],
        ):
            client_factory_config = ClientFactoryConfig(
                client_ids=client_ids,
                cfg=cfg,
                device=torch.device(DeviceType.CPU),
                prepared_dir=tmp_path,
                seed=0,
            )
            with pytest.raises(
                FileNotFoundError, match="Prepared directories missing"
            ) as exc_info:
                make_client_fn(
                    client_data,
                    client_factory_config,
                )
            assert "client_missing" in str(exc_info.value)

    def test_all_client_dirs_present_returns_callable(self, tmp_path: Path) -> None:
        """Ensure call passes if all client directories exist in prepared_dir."""
        cfg = _make_cfg()
        client_ids = ["client_a", "client_b"]
        client_data: dict[str, ClientData] = {}

        with patch(
            "datp.federated.discover_client_dirs",
            return_value=[tmp_path / cid for cid in client_ids],
        ):
            fn = make_client_fn(
                client_data,
                ClientFactoryConfig(
                    client_ids=client_ids,
                    cfg=cfg,
                    device=torch.device(DeviceType.CPU),
                    prepared_dir=tmp_path,
                    seed=0,
                ),
            )
            assert callable(fn)


class TestWorkerSideSeeding:
    """Tests verifying worker-side determinism seeding configuration."""

    def test_seed_param_calls_set_seeds(self) -> None:
        """Verify worker seeds are set and offset by partition index."""
        cfg = _make_cfg()
        client_data = _make_client_data()
        client_ids = sorted(client_data.keys())

        with patch("datp.federated.set_seeds") as mock_seeds:
            fn = make_client_fn(
                client_data,
                ClientFactoryConfig(
                    client_ids=client_ids,
                    cfg=cfg,
                    device=torch.device(DeviceType.CPU),
                    seed=42,
                ),
            )
            fn(_make_context(0))
            fn(_make_context(1))

        assert mock_seeds.call_count == 2

        assert mock_seeds.call_args_list[0].args == (42,)
        assert mock_seeds.call_args_list[1].args == (43,)

    def test_seed_param_in_prepared_dir_path(self, tmp_path: Path) -> None:
        """Verify worker seed offset logic in prepared directory mode."""
        cfg = _make_cfg()
        client_ids = ["client_a", "client_b"]
        client_data: dict[str, ClientData] = {}
        train_t = torch.randn(8, 4)
        cal_t = torch.randn(4, 4)

        with (
            patch(
                "datp.federated.discover_client_dirs",
                return_value=[tmp_path / cid for cid in client_ids],
            ),
            patch(
                "datp.federated.load_single_client_training_data",
                return_value=(train_t, cal_t),
            ),
            patch("datp.federated.set_seeds") as mock_seeds,
        ):
            fn = make_client_fn(
                client_data,
                ClientFactoryConfig(
                    client_ids=client_ids,
                    cfg=cfg,
                    device=torch.device(DeviceType.CPU),
                    prepared_dir=tmp_path,
                    seed=7,
                ),
            )
            fn(_make_context(1))

        mock_seeds.assert_called_once_with(7 ^ 1)


def _make_model() -> Autoencoder:
    """Helper to build a default Autoencoder model for tests."""
    return Autoencoder(
        input_dim=4, hidden_dims=[3, 2], activation=Activation.RELU, use_bn=False
    )


class TestTrainLocal:
    """Tests verifying train_local execution, optimization, and determinism."""

    def test_returns_finite_loss(self) -> None:
        """Verify that training on synthetic data returns a finite float loss value."""
        model = _make_model()
        data = torch.randn(16, 4)
        loss = train_local(model, data, epochs=1, batch_size=8, lr=0.01)
        assert isinstance(loss, float)
        assert not torch.isnan(torch.tensor(loss))

    def test_optimizer_uses_no_weight_decay(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ensure the training optimizer uses 0.0 weight decay to prevent calibration distortion."""
        captured: dict[str, float] = {}
        real_adam = torch.optim.Adam

        def _capturing_adam(params: Any, **kwargs: Any) -> torch.optim.Adam:
            captured["weight_decay"] = kwargs.get("weight_decay", -1.0)
            return real_adam(params, **kwargs)

        monkeypatch.setattr(torch.optim, "Adam", _capturing_adam)
        train_local(_make_model(), torch.randn(16, 4), epochs=1, batch_size=8, lr=0.01)
        assert captured["weight_decay"] == pytest.approx(0.0)

    def test_multiple_epochs_reduce_loss(self) -> None:
        """Verify that training for more epochs leads to a lower reconstruction loss."""
        set_seeds(0)
        model = _make_model()
        data = torch.randn(32, 4)
        loss_1 = train_local(model, data, epochs=1, batch_size=8, lr=0.01)

        set_seeds(0)
        model2 = _make_model()
        loss_10 = train_local(model2, data, epochs=10, batch_size=8, lr=0.01)

        assert loss_10 < loss_1

    def test_deterministic_same_seed(self) -> None:
        """Verify that training is reproducible when seed state is matched."""
        data = torch.randn(16, 4)

        set_seeds(42)
        m1 = _make_model()
        loss1 = train_local(m1, data, epochs=2, batch_size=8, lr=0.01)

        set_seeds(42)
        m2 = _make_model()
        loss2 = train_local(m2, data, epochs=2, batch_size=8, lr=0.01)

        assert loss1 == pytest.approx(loss2, abs=1e-7)


class TestEvaluateBenign:
    """Tests verifying benign validation loss evaluation on calibration sets."""

    def test_returns_positive_loss(self) -> None:
        """Verify that evaluation loss on random validation inputs is positive."""
        model = _make_model()
        cal_data = torch.randn(8, 4)
        loss = evaluate_benign(model, cal_data)
        assert loss > 0.0

    def test_model_set_to_eval(self) -> None:
        """Ensure evaluation sets PyTorch model mode to evaluation (eval) mode."""
        model = _make_model()
        model.train()
        cal_data = torch.randn(8, 4)
        evaluate_benign(model, cal_data)
        assert not model.training

    def test_perfect_reconstruction_gives_zero_loss(self) -> None:
        """Verify loss is non-negative and zero-bounded on zeroed datasets."""
        model = _make_model()
        cal_data = torch.zeros(4, 4)
        loss = evaluate_benign(model, cal_data)
        assert loss >= 0.0


class TestEvaluateBenignValidation:
    """Tests verifying input guards on evaluate_benign."""

    def test_empty_data_raises(self) -> None:
        """Verify ValueError is raised if input data is empty."""
        model = _make_model()
        data = torch.empty(0, 4)
        with pytest.raises(ValueError, match="non-empty"):
            evaluate_benign(model, data)


class TestTrainLocalValidation:
    """Tests verifying input validation guards on train_local."""

    def test_epochs_zero_raises(self) -> None:
        """Verify ValueError is raised if local training epochs setting is less than 1."""
        model = _make_model()
        data = torch.randn(16, 4)
        with pytest.raises(ValueError, match="must be >= 1"):
            train_local(model, data, epochs=0, batch_size=8, lr=0.01)

    def test_batch_size_zero_raises(self) -> None:
        """Verify ValueError is raised if batch size setting is less than 1."""
        model = _make_model()
        data = torch.randn(16, 4)
        with pytest.raises(ValueError, match="must be >= 1"):
            train_local(model, data, epochs=1, batch_size=0, lr=0.01)

    def test_empty_data_raises(self) -> None:
        """Verify ValueError is raised if training dataset tensor is empty."""
        model = _make_model()
        data = torch.empty(0, 4)
        with pytest.raises(ValueError, match="non-empty"):
            train_local(model, data, epochs=1, batch_size=8, lr=0.01)


def _make_model_parameters() -> Autoencoder:
    """Helper to build a default Autoencoder model for tests."""
    return Autoencoder(
        input_dim=4, hidden_dims=[3, 2], activation=Activation.RELU, use_bn=False
    )


class TestGetParameters:
    """Tests verifying get_parameters behavior and copies security."""

    def test_returns_list_of_ndarrays(self) -> None:
        """Verify that get_parameters returns a list of NumPy float arrays."""
        model = _make_model_parameters()
        params = get_parameters(model)
        assert isinstance(params, list)
        assert all(isinstance(p, np.ndarray) for p in params)

    def test_returns_copies(self) -> None:
        """Verify that modifying the returned numpy arrays does not affect the model parameters."""
        model = _make_model_parameters()
        params = get_parameters(model)
        params[0][:] = 999.0
        model_params = list(model.parameters())
        assert not np.allclose(model_params[0].detach().cpu().numpy(), 999.0)


class TestSetParameters:
    """Tests verifying set_parameters behavior and validations."""

    def test_round_trip(self) -> None:
        """Verify that set_parameters successfully restores weight values after zeroing."""
        model = _make_model_parameters()
        original = get_parameters(model)

        with torch.no_grad():
            for p in model.parameters():
                p.fill_(0.0)

        set_parameters(model, original)
        restored = get_parameters(model)
        for orig, rest in zip(original, restored, strict=True):
            np.testing.assert_array_almost_equal(orig, rest)

    def test_dtype_cast(self) -> None:
        """Verify that setting float64 parameters casts back to the model's float32 type."""
        model = _make_model_parameters()
        params = get_parameters(model)

        params_f64 = [p.astype(np.float64) for p in params]
        set_parameters(model, params_f64)
        for p in model.parameters():
            assert p.dtype == torch.float32

    def test_shape_mismatch_raises(self) -> None:
        """Verify ValueError is raised if parameter array shape mismatches model parameter shape."""
        model = _make_model_parameters()
        params = get_parameters(model)
        params[0] = np.zeros((99, 99), dtype=np.float32)
        with pytest.raises(ValueError, match="Shape mismatch"):
            set_parameters(model, params)

    def test_count_mismatch_raises(self) -> None:
        """Verify ValueError is raised if parameter array count mismatches model parameter count."""
        model = _make_model_parameters()
        params = get_parameters(model)
        with pytest.raises(ValueError, match="Parameter count mismatch"):
            set_parameters(model, params[:1])


class TestSetParametersDevice:
    """Tests verifying PyTorch device safety inside parameter setter."""

    def test_stays_on_cpu(self) -> None:
        """Verify parameters set on a CPU model stay on the CPU device."""
        model = _make_model_parameters()
        params = get_parameters(model)
        set_parameters(model, params)
        for p in model.parameters():
            assert p.device == torch.device(DeviceType.CPU)

    def test_preserves_original_device(self) -> None:
        """Verify that set_parameters preserves the original device of all parameter tensors."""
        model = _make_model_parameters()
        original_devices = [p.device for p in model.parameters()]
        params = get_parameters(model)
        set_parameters(model, params)
        for p, orig_device in zip(model.parameters(), original_devices, strict=True):
            assert p.device == orig_device


class TestEmptyModel:
    """Tests verifying serialization behaviour of empty models (e.g. empty Sequential)."""

    def test_get_parameters_empty_model(self) -> None:
        """Verify get_parameters returns an empty list for models with no parameters."""
        model = nn.Sequential()
        params = get_parameters(model)
        assert params == []

    def test_set_parameters_empty_model(self) -> None:
        """Verify set_parameters is a no-op when setting an empty parameters list on a model with no parameters."""
        model = nn.Sequential()
        set_parameters(model, [])


class TestObjectStoreCapacity:
    def test_exceeds_available_ram_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("datp.federated._available_ram_mib", lambda: 1024)
        with pytest.raises(RuntimeError, match="exceeds available RAM"):
            check_object_store_capacity(4096)

    def test_equal_to_available_ram_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("datp.federated._available_ram_mib", lambda: 2048)
        check_object_store_capacity(2048)


class TestRayMemoryThreshold:
    """Tests verifying memory threshold environment settings inside Ray clusters."""

    def test_ray_memory_threshold_value(self) -> None:
        """Verify that the default configuration value of ray_memory_threshold is 0.9."""
        assert BASE_CONFIG.runtime.ray_memory_threshold == pytest.approx(0.90)

    def test_ray_memory_threshold_enforced(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify that ensure_ray_memory_threshold sets the target environment variable."""
        monkeypatch.delenv("RAY_memory_usage_threshold", raising=False)
        ensure_ray_memory_threshold(BASE_CONFIG.runtime.ray_memory_threshold)
        assert os.environ["RAY_memory_usage_threshold"] == "0.9"

    def test_ray_memory_threshold_rejects_high(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify that error is raised if environment setting is higher than configured threshold."""
        monkeypatch.setenv("RAY_memory_usage_threshold", "0.99")
        with pytest.raises(RuntimeError, match="too high"):
            ensure_ray_memory_threshold(BASE_CONFIG.runtime.ray_memory_threshold)

    def test_ray_memory_threshold_accepts_lower(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify that environment setting remains unchanged if lower than configured threshold."""
        monkeypatch.setenv("RAY_memory_usage_threshold", "0.85")
        ensure_ray_memory_threshold(BASE_CONFIG.runtime.ray_memory_threshold)
        assert os.environ["RAY_memory_usage_threshold"] == "0.85"

    def test_ray_memory_threshold_rejects_invalid(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify that ensure_ray_memory_threshold raises RuntimeError on non-float settings."""
        monkeypatch.setenv("RAY_memory_usage_threshold", "not-a-number")
        with pytest.raises(RuntimeError, match="invalid float"):
            ensure_ray_memory_threshold(BASE_CONFIG.runtime.ray_memory_threshold)


class TestDeriveClientResources:
    @pytest.fixture(autouse=True)
    def _mock_system(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("datp.federated._available_ram_mib", lambda: 16 * 1024)
        monkeypatch.setattr("os.cpu_count", lambda: 8)

    @staticmethod
    def _machine(**update: object):
        return BASE_CONFIG.machine.model_copy(
            update={
                "per_client_ram_gb": 1.5,
                "reserve_ram_gb": 3.5,
                "max_concurrent_override": None,
                "require_cuda": False,
                "ray_num_gpus_per_client": 0.5,
                **update,
            }
        )

    def test_gpu_share_in_cuda_mode(self) -> None:
        result = derive_client_resources(self._machine(require_cuda=True))
        assert result["num_gpus"] == pytest.approx(0.5)

    def test_num_gpus_zero_when_cpu_mode(self) -> None:
        result = derive_client_resources(self._machine())
        assert result["num_gpus"] == pytest.approx(0.0)

    def test_cpus_derived_from_available_ram(self) -> None:
        # floor((16 - 3.5) / 1.5) = 8 concurrent actors on 8 cores -> 1 cpu each
        assert derive_client_resources(self._machine())["num_cpus"] == pytest.approx(
            1.0
        )

    def test_honours_max_concurrent_override(self) -> None:
        result = derive_client_resources(self._machine(max_concurrent_override=4))
        assert result["num_cpus"] == pytest.approx(2.0)

    def test_device_and_resources_agree_cuda(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("datp.core.torch.cuda.is_available", lambda: True)
        device = resolve_device(require_cuda=True)
        resources = derive_client_resources(self._machine(require_cuda=True))
        assert device.type == DeviceType.CUDA
        assert resources["num_gpus"] > 0

    def test_device_and_resources_agree_cpu(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("datp.core.torch.cuda.is_available", lambda: False)
        device = resolve_device(require_cuda=False)
        resources = derive_client_resources(self._machine())
        assert device.type == DeviceType.CPU
        assert resources["num_gpus"] == pytest.approx(0.0)


class TestRunFlTrainingValidation:
    def test_raises_when_stage_is_none(self, tmp_path: Path) -> None:
        cfg = make_fl_cfg().model_copy(update={"stage": None})
        with pytest.raises(ValueError, match="stage must be set"):
            run_fl_training(cfg, {}, 0, base_dir=tmp_path)

    def test_raises_without_output_location(self) -> None:
        make_fl_cfg_value = make_fl_cfg()
        with pytest.raises(ValueError, match="base_dir or output_layout"):
            run_fl_training(make_fl_cfg_value, {}, 0)

    def test_raises_without_any_client_source(self, tmp_path: Path) -> None:
        make_fl_cfg_value = make_fl_cfg()
        with pytest.raises(ValueError, match="No non-empty client_data"):
            run_fl_training(make_fl_cfg_value, {}, 0, base_dir=tmp_path)

    def test_saves_final_model_checkpoint(self, tmp_path: Path) -> None:
        cfg = make_fl_cfg()
        model = Autoencoder(
            cfg.model.input_dim,
            cfg.model.encoder_dims,
            cfg.model.activation,
            cfg.model.use_bn,
        )
        monitor = MagicMock(num_recorded=1, converged_round=None)
        strategy = MagicMock(
            latest_parameters=[], convergence_monitor=monitor, stopped=False
        )
        data = {"c0": _client_data_simulation()}
        with (
            patch("datp.federated._client_ids", return_value=("c0",)),
            patch("datp.federated.resolve_device", return_value=torch.device("cpu")),
            patch("datp.federated.set_seeds"),
            patch("datp.federated.build_model", return_value=model),
            patch("datp.federated.DatpFedAvg", return_value=strategy),
            patch("datp.federated.make_client_fn"),
            patch("datp.federated._run_flower_simulation"),
            patch("datp.federated.set_parameters"),
            patch("datp.federated._scoring_data", return_value=data),
            patch("datp.federated.score_clients"),
            patch("datp.federated.save_convergence_artifacts"),
        ):
            run_fl_training(cfg, data, 0, base_dir=tmp_path)

        checkpoint = ArtifactLayout(base_dir=tmp_path, stage=_STAGE).model_checkpoint(
            TrainingCellId(stage=_STAGE, seed=0)
        )
        saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
        assert saved["model_config"] == cfg.model.model_dump(mode="json")
        assert set(saved["state_dict"]) == set(model.state_dict())


class TestTrainingResult:
    def test_is_frozen(self, tmp_path: Path) -> None:
        r = TrainingResult(
            stage=_STAGE,
            seed=0,
            converged_round=None,
            total_rounds=5,
            score_dir=tmp_path,
            loss_history=[],
        )
        with pytest.raises(FrozenInstanceError):
            setattr(r, "seed", 99)


def _client_data_simulation() -> ClientData:
    return ClientData(
        train=torch.zeros(2, 2),
        val=torch.zeros(2, 2),
        test_benign=torch.zeros(2, 2),
        test_attack=torch.zeros(2, 2),
    )


class TestScoringData:
    def test_returns_client_data_when_no_prepared_dir(self) -> None:
        data = {"c0": _client_data_simulation()}
        assert _scoring_data(data, None, expected_dim=2) is data

    def test_prepared_dir_wins_over_client_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from_disk = {"from_disk": _client_data_simulation()}
        monkeypatch.setattr(
            "datp.federated.load_client_data", lambda *_, **__: from_disk
        )

        result = _scoring_data(
            {"in_memory": _client_data_simulation()}, tmp_path, expected_dim=2
        )
        assert result is from_disk


def _make_strategy() -> DatpFedAvg:
    params = np.zeros((2, 2), dtype=np.float32)
    return DatpFedAvg(make_fl_cfg(rounds=10), ndarrays_to_parameters([params]), 1)


def _make_fit_result(
    params: np.ndarray, client_id: str = "c0", num_examples: int = 10
) -> tuple[MagicMock, FitRes]:
    """Helper to package weight parameters as Flower fit results."""
    proxy = MagicMock()
    fit_res = FitRes(
        status=Status(code=Code.OK, message=""),
        parameters=ndarrays_to_parameters([params]),
        num_examples=num_examples,
        metrics={ClientMetricKey.CLIENT_ID: client_id},
    )
    return proxy, fit_res


class TestLatestParameters:
    """Tests verifying the strategy retains the final aggregated parameters."""

    def test_latest_parameters_unset_before_training(self) -> None:
        """Verify no parameters are exposed before the first aggregation."""
        assert _make_strategy().latest_parameters is None

    def test_aggregate_fit_records_latest_parameters(self) -> None:
        """Verify aggregate_fit keeps the aggregated weights of the latest round."""
        strategy = _make_strategy()
        params = np.full((2, 2), 3.0, dtype=np.float32)

        strategy.aggregate_fit(1, [_make_fit_result(params)], [])

        latest = strategy.latest_parameters
        assert latest is not None
        np.testing.assert_array_equal(latest[0], params)


class TestDeterministicAggregation:
    """Tests verifying aggregation does not depend on client completion order."""

    @staticmethod
    def _fit_results() -> list[tuple[MagicMock, FitRes]]:
        rng = np.random.default_rng(0)
        return [
            _make_fit_result(
                rng.normal(size=(2, 2)).astype(np.float32),
                client_id=f"c{i}",
                num_examples=10 + 7 * i,
            )
            for i in range(6)
        ]

    def test_fit_aggregation_is_independent_of_arrival_order(self) -> None:
        """Verify permuting the fit results yields bitwise-identical parameters."""
        results = self._fit_results()
        reference = _make_strategy()
        reference.aggregate_fit(1, list(results), [])
        for shuffle_seed in range(5):
            order = np.random.default_rng(shuffle_seed).permutation(len(results))
            strategy = _make_strategy()
            strategy.aggregate_fit(1, [results[i] for i in order], [])
            assert reference.latest_parameters is not None
            assert strategy.latest_parameters is not None
            np.testing.assert_array_equal(
                reference.latest_parameters[0], strategy.latest_parameters[0]
            )

    def test_evaluate_aggregation_is_independent_of_arrival_order(self) -> None:
        """Verify permuting the evaluate results yields a bitwise-identical loss."""
        rng = np.random.default_rng(1)
        results = [
            (
                MagicMock(),
                EvaluateRes(
                    status=Status(code=Code.OK, message=""),
                    loss=float(rng.random()),
                    num_examples=100 + 13 * i,
                    metrics={ClientMetricKey.CLIENT_ID: f"c{i}"},
                ),
            )
            for i in range(6)
        ]
        reference, _ = _make_strategy().aggregate_evaluate(1, list(results), [])
        for shuffle_seed in range(5):
            order = np.random.default_rng(shuffle_seed).permutation(len(results))
            loss, _ = _make_strategy().aggregate_evaluate(
                1, [results[i] for i in order], []
            )
            assert loss == reference


class TestFullParticipationDiagnostics:
    """Tests verifying aggregate crash reporting and exception messages."""

    def test_aggregate_fit_reports_successful_and_failed_client_ids(self) -> None:
        """Ensure strategy raises error containing failed client IDs on aggregation crash."""
        strategy = _make_strategy()
        ok_proxy, ok_res = _make_fit_result(np.zeros((2, 2), dtype=np.float32))
        ok_proxy.cid = "c0"
        bad_proxy = MagicMock()
        bad_proxy.cid = "c3"
        bad_res = FitRes(
            status=Status(code=Code.FIT_NOT_IMPLEMENTED, message="trainer crashed"),
            parameters=ndarrays_to_parameters([np.zeros((2, 2), dtype=np.float32)]),
            num_examples=0,
            metrics={},
        )

        with pytest.raises(RuntimeError) as exc:
            strategy.aggregate_fit(7, [(ok_proxy, ok_res)], [(bad_proxy, bad_res)])

        message = str(exc.value)
        assert "round 7" in message
        assert "fit" in message
        assert "c3" in message

    def test_aggregate_evaluate_reports_exception_failures(self) -> None:
        """Ensure strategy raises error detailing client evaluate process exceptions."""
        strategy = _make_strategy()

        runtime_error = RuntimeError("client process died")
        with pytest.raises(RuntimeError) as exc:
            strategy.aggregate_evaluate(4, [], [runtime_error])

        message = str(exc.value)
        assert "evaluate" in message
        assert "round 4" in message


class TestValidateTensorInput:
    """Tests verifying single tensor shape and finite value validation guards."""

    def test_valid_2d_passes(self) -> None:
        """Verify that a valid 2-D tensor successfully passes validation."""
        validate_tensor_input(torch.randn(10, 4), FederatedTensorLabel.TRAIN, "c0")

    def test_1d_raises(self) -> None:
        """Verify ValueError is raised if the input tensor is 1-D."""
        randn_value = torch.randn(10)
        with pytest.raises(ValueError, match="must be 2-D"):
            validate_tensor_input(randn_value, FederatedTensorLabel.TRAIN, "c0")

    def test_3d_raises(self) -> None:
        """Verify ValueError is raised if the input tensor is 3-D."""
        randn_value = torch.randn(2, 3, 4)
        with pytest.raises(ValueError, match="must be 2-D"):
            validate_tensor_input(randn_value, FederatedTensorLabel.TRAIN, "c0")

    def test_empty_raises(self) -> None:
        """Verify ValueError is raised if the input tensor is empty."""
        empty_value = torch.empty(0, 4)
        with pytest.raises(ValueError, match="non-empty"):
            validate_tensor_input(empty_value, FederatedTensorLabel.TRAIN, "c0")

    def test_nan_raises(self) -> None:
        """Verify ValueError is raised if the input tensor contains NaN values."""
        data = torch.randn(10, 4)
        data[0, 0] = float("nan")
        with pytest.raises(ValueError, match="non-finite"):
            validate_tensor_input(data, FederatedTensorLabel.TRAIN, "c0")

    def test_inf_raises(self) -> None:
        """Verify ValueError is raised if the input tensor contains positive infinity."""
        data = torch.randn(10, 4)
        data[0, 0] = float("inf")
        with pytest.raises(ValueError, match="non-finite"):
            validate_tensor_input(data, FederatedTensorLabel.TRAIN, "c0")

    def test_correct_expected_dim_passes(self) -> None:
        """Verify that validation passes when the column dimension matches the expected value."""
        validate_tensor_input(
            torch.randn(10, 4), FederatedTensorLabel.TRAIN, "c0", expected_dim=4
        )

    def test_wrong_expected_dim_raises(self) -> None:
        """Verify ValueError is raised if the column dimension mismatches the expected value."""
        randn_value = torch.randn(10, 4)
        with pytest.raises(ValueError, match="expected dimension"):
            validate_tensor_input(
                randn_value, FederatedTensorLabel.TRAIN, "c0", expected_dim=5
            )


class TestValidateClientData:
    """Tests verifying multi-split ClientData structure schema validation."""

    def test_valid_passes(self) -> None:
        """Verify validation passes for complete ClientData containing valid splits."""
        cd = ClientData(
            train=torch.randn(16, 4),
            val=torch.randn(8, 4),
            test_benign=torch.randn(8, 4),
            test_attack=torch.randn(8, 4),
        )
        validate_client_data(cd, "c0", expected_dim=4)

    def test_wrong_dim_raises(self) -> None:
        """Verify ValueError is raised if any split has columns mismatches."""
        cd = ClientData(
            train=torch.randn(16, 5),
            val=torch.randn(8, 4),
            test_benign=torch.randn(8, 4),
            test_attack=torch.randn(8, 4),
        )
        with pytest.raises(ValueError, match="expected dimension"):
            validate_client_data(cd, "c0", expected_dim=4)
