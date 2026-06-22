from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from datp.core.enums import Activation
from datp.config.stages import ExperimentStage
from datp.core.identity import TrainingCellId
from datp.experiments.enums import SweepStep
from datp.experiments.executor import (
    SharedTrainingExecutor,
    ThresholdEvaluationExecutor,
)
from datp.experiments.models import PipelineRequest, SharedPipelineContext
from datp.experiments.stages.train_encoder import ensure_fl_checkpoint


def _make_request(
    policy: ThresholdPolicy,
    tmp_path: Path,
    seed: int = 1,
) -> PipelineRequest:
    cfg = MagicMock()
    cfg.threshold.n_min = 100
    cfg.threshold.q = 0.95
    cfg.model.input_dim = 115
    cfg.model.encoder_dims = [64, 32]
    cfg.model.epochs = 5
    cfg.model.patience = 3
    cfg.model.lr = 1e-3
    cfg.model.activation = Activation.RELU
    cfg.model.use_bn = True
    cfg.machine.batch_size_train = 256
    cfg.logging.training_progress_interval = 10
    cfg.runtime.lock_timeout_seconds = 60.0
    return PipelineRequest(
        key=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=seed),
        policy=policy,
        cfg=cfg,
        base_dir=tmp_path,
        prepared_dir=tmp_path / "prepared",
        checkpoint_round=None,
    )


class TestSharedTrainingExecutor:
    def test_instantiation(self) -> None:
        executor = SharedTrainingExecutor(step_fn=None, checkpoint_status_fn=None)
        assert executor._step_fn is None
        assert executor._checkpoint_status_fn is None

    def test_step_fn_forwarded(self, tmp_path: Path) -> None:
        step_calls: list[tuple[SweepStep, str]] = []

        def record_step(step: SweepStep, detail: str = "") -> None:
            step_calls.append((step, detail))

        executor = SharedTrainingExecutor(
            step_fn=record_step, checkpoint_status_fn=None
        )
        request = _make_request(ThresholdPolicy.GLOBAL_THRESHOLD, tmp_path)

        with (
            patch.object(executor, "_step_fn", wraps=record_step),
            patch("datp.experiments.executor.ensure_fl_checkpoint") as mock_ensure,
            patch(
                "datp.experiments.executor.load_main_cal_errors",
                return_value={"c1": np.array([0.1, 0.2])},
            ),
            patch(
                "datp.experiments.executor.identify_eligible",
                return_value=(["c1"], []),
            ),
            patch(
                "datp.experiments.executor.compute_client_thresholds",
                return_value={"c1": 0.15},
            ),
            patch(
                "datp.experiments.executor.compute_tau_global",
                return_value=0.15,
            ),
            patch("datp.experiments.executor.ScoreProvider"),
        ):
            ctx = executor.build_context(request)

        mock_ensure.assert_called_once()
        assert isinstance(ctx, SharedPipelineContext)
        assert (
            len(step_calls) >= 3
        )  # LOAD_CAL_SCORES, COMPUTE_ELIGIBILITY, COMPUTE_TAU_GLOBAL, INIT_SCORE_PROVIDER

    def test_build_context_returns_typed_context(self, tmp_path: Path) -> None:
        executor = SharedTrainingExecutor(step_fn=None, checkpoint_status_fn=None)
        request = _make_request(ThresholdPolicy.GLOBAL_THRESHOLD, tmp_path)

        with (
            patch("datp.experiments.executor.ensure_fl_checkpoint"),
            patch(
                "datp.experiments.executor.load_main_cal_errors",
                return_value={"c1": np.array([0.1, 0.2])},
            ),
            patch(
                "datp.experiments.executor.identify_eligible",
                return_value=(["c1"], []),
            ),
            patch(
                "datp.experiments.executor.compute_client_thresholds",
                return_value={"c1": 0.15},
            ),
            patch(
                "datp.experiments.executor.compute_tau_global",
                return_value=0.15,
            ),
            patch("datp.experiments.executor.ScoreProvider") as mock_sp,
        ):
            ctx = executor.build_context(request)

        assert ctx.key == request.key
        assert list(ctx.client_errors.keys()) == ["c1"]
        assert np.array_equal(ctx.client_errors["c1"], np.array([0.1, 0.2]))
        assert ctx.eligible == ["c1"]
        assert ctx.pending == []
        assert ctx.client_taus == pytest.approx({"c1": 0.15})
        assert ctx.tau_global == pytest.approx(0.15)
        assert ctx.score_provider is mock_sp.return_value


class TestThresholdEvaluationExecutor:
    def test_instantiation(self) -> None:
        executor = ThresholdEvaluationExecutor(step_fn=None)
        assert executor._step_fn is None

    def test_run_returns_sweep_metrics(self, tmp_path: Path) -> None:
        from datp.thresholding.metrics_serialization import SweepMetrics

        executor = ThresholdEvaluationExecutor(step_fn=None)
        request = _make_request(ThresholdPolicy.LOCAL_THRESHOLD, tmp_path)

        ctx = SharedPipelineContext(
            key=request.key,
            client_errors={"c1": np.array([0.1, 0.2])},
            eligible=["c1"],
            pending=[],
            client_taus={"c1": 0.15},
            tau_global=0.15,
            score_provider=MagicMock(),
            checkpoint_round=None,
        )

        mock_metrics = MagicMock(spec=SweepMetrics)
        with (
            patch(
                "datp.experiments.executor.derive_threshold",
                return_value=MagicMock(
                    tau_global=0.15,
                    eligible_count=1,
                    pending_count=0,
                    client_thresholds={"c1": 0.15},
                ),
            ),
            patch(
                "datp.experiments.executor.evaluate_policy_run",
                return_value=MagicMock(),
            ),
            patch(
                "datp.experiments.executor.build_metrics_dict",
                return_value=mock_metrics,
            ),
            patch("datp.experiments.executor.write_metrics_atomic"),
            patch("datp.experiments.executor.RunLifecycle"),
            patch("datp.experiments.executor.log_metrics"),
        ):
            result = executor.run(request, ctx)

        assert result is mock_metrics

    def test_step_fn_called(self, tmp_path: Path) -> None:
        step_calls: list[tuple[SweepStep, str]] = []

        def record_step(step: SweepStep, detail: str = "") -> None:
            step_calls.append((step, detail))

        executor = ThresholdEvaluationExecutor(step_fn=record_step)
        request = _make_request(ThresholdPolicy.LOCAL_THRESHOLD, tmp_path)

        ctx = SharedPipelineContext(
            key=request.key,
            client_errors={"c1": np.array([0.1, 0.2])},
            eligible=["c1"],
            pending=[],
            client_taus={"c1": 0.15},
            tau_global=0.15,
            score_provider=MagicMock(),
            checkpoint_round=None,
        )

        with (
            patch(
                "datp.experiments.executor.derive_threshold",
                return_value=MagicMock(
                    tau_global=0.15,
                    eligible_count=1,
                    pending_count=0,
                    client_thresholds={"c1": 0.15},
                ),
            ),
            patch(
                "datp.experiments.executor.evaluate_policy_run",
                return_value=MagicMock(),
            ),
            patch(
                "datp.experiments.executor.build_metrics_dict",
                return_value=MagicMock(),
            ),
            patch("datp.experiments.executor.write_metrics_atomic"),
            patch("datp.experiments.executor.RunLifecycle"),
            patch("datp.experiments.executor.log_metrics"),
        ):
            executor.run(request, ctx)

        assert len(step_calls) >= 3  # DERIVE_THRESHOLD, EVALUATE, WRITE_METRICS
        assert step_calls[0][0] == SweepStep.DERIVE_THRESHOLD


class TestEnsureFlCheckpoint:
    def test_lock_wraps_score_only_recovery(self, tmp_path: Path) -> None:
        cfg = MagicMock()
        request = PipelineRequest(
            key=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=4),
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            cfg=cfg,
            base_dir=tmp_path,
            prepared_dir=tmp_path / "prepared",
            checkpoint_round=None,
        )
        (tmp_path / "prepared").mkdir(parents=True, exist_ok=True)
        ckpt_dir = tmp_path / "checkpoints" / "nbaiot_main" / "seed_4"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        ckpt = ckpt_dir / "model.pt"
        ckpt.touch()

        score_dir = tmp_path / "scores" / "nbaiot_main" / "seed_4"
        score_dir.mkdir(parents=True, exist_ok=True)

        class _Lock:
            entered = False

            def __enter__(self) -> "_Lock":
                self.entered = True
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                del exc_type, exc, tb

        lock = _Lock()
        with (
            patch("datp.experiments.stages.train_encoder.FileLock", return_value=lock),
            patch(
                "datp.federated.data_loading.load_client_data",
                return_value={"c1": object()},
            ),
            patch(
                "datp.scoring.generation.load_model_from_checkpoint",
                return_value=object(),
            ),
            patch("datp.scoring.generation.score_clients") as score_clients,
        ):
            ensure_fl_checkpoint(
                request,
                step_fn=None,
                checkpoint_status_fn=None,
                lock_timeout=60.0,
            )

        assert lock.entered is True
        score_clients.assert_called_once()

    def test_skips_when_checkpoint_and_scoring_exist(self, tmp_path: Path) -> None:
        cfg = MagicMock()
        cfg.machine.require_cuda = False
        request = PipelineRequest(
            key=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=5),
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            cfg=cfg,
            base_dir=tmp_path,
            prepared_dir=tmp_path / "prepared",
            checkpoint_round=None,
        )
        (tmp_path / "prepared").mkdir(parents=True, exist_ok=True)
        ckpt_dir = tmp_path / "checkpoints" / "nbaiot_main" / "seed_5"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        (ckpt_dir / "model.pt").touch()

        score_dir = tmp_path / "scores" / "nbaiot_main" / "seed_5"
        score_dir.mkdir(parents=True, exist_ok=True)

        with (
            patch(
                "datp.scoring.generation.validate_scoring_manifest",
                return_value={"records": []},
            ),
            patch("datp.federated.protocols.fedavg.run_fl_training") as run_fl,
            patch("datp.federated.data_loading.discover_client_dirs", return_value=[]),
        ):
            ensure_fl_checkpoint(
                request,
                step_fn=None,
                checkpoint_status_fn=None,
                lock_timeout=60.0,
            )

        run_fl.assert_not_called()

    def test_trains_when_checkpoint_missing(self, tmp_path: Path) -> None:
        cfg = MagicMock()
        cfg.machine.require_cuda = False
        request = PipelineRequest(
            key=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=6),
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            cfg=cfg,
            base_dir=tmp_path,
            prepared_dir=tmp_path / "prepared",
            checkpoint_round=None,
        )
        ckpt_dir = tmp_path / "checkpoints" / "a" / "seed_6"
        ckpt_dir.mkdir(parents=True, exist_ok=True)

        with (
            patch(
                "datp.federated.data_loading.load_client_data",
                return_value={"c1": object()},
            ),
            patch("datp.federated.protocols.fedavg.run_fl_training") as run_fl,
        ):
            ensure_fl_checkpoint(
                request,
                step_fn=None,
                checkpoint_status_fn=None,
                lock_timeout=60.0,
            )

        run_fl.assert_called_once()


class TestNoProductionAssert:
    def test_no_assert_in_executor_source(self) -> None:
        import inspect

        import datp.experiments.executor as mod

        source = inspect.getsource(mod)
        # Strip comment lines then check for bare assert statements
        non_comment = "\n".join(
            line for line in source.splitlines() if not line.strip().startswith("#")
        )
        assert "assert " not in non_comment, (
            "Production assert found in pipeline/executor.py"
        )
