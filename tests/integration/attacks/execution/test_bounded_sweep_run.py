"""End-to-end integration tests for the bounded-sweep poisoning run on nbaiot_main."""

from __future__ import annotations

import math

import pytest
import torch

from datp.artifacts.layout import ArtifactLayout
from datp.attacks.constants import N_MIN
from datp.attacks.execution.bounded_sweep_run import (
    run_nbaiot_main,
    write_nbaiot_main_manifest,
)
from datp.attacks.score_containers import build_score_collection
from datp.config.attack_config import CalibrationPoisoningConfig
from datp.config.compose import BASE_CONFIG
from datp.config.models import ConvergenceConfig, DatpConfig, FederationConfig
from datp.core.device import resolve_device
from datp.core.enums import ScoringStage
from datp.core.identity import TrainingCellId
from datp.config.models import ExperimentStage
from datp.core.seeds import set_seeds
from datp.federated.protocols.fedavg import run_fl_training
from datp.federated.types import ClientData
from datp.scoring.loading import load_main_cal_errors
from datp.scoring.loading import load_parquets_from_dir

_N_FEATURES = 10
_N_TRAIN = 200
_N_CAL = 150
_N_TEST = 50
_N_CLIENTS = 4
_CONFIG = CalibrationPoisoningConfig.for_bounded_sweep()


def _make_client_data(seed: int) -> dict[str, ClientData]:
    """Build deterministic synthetic client data for a given seed."""
    device = resolve_device(require_cuda=False)
    rng = torch.Generator().manual_seed(seed)
    data = {}
    for i in range(_N_CLIENTS):
        data[f"client_{i}"] = ClientData(
            train=torch.randn(_N_TRAIN, _N_FEATURES, generator=rng).to(device),
            val=torch.randn(_N_CAL, _N_FEATURES, generator=rng).to(device),
            test_benign=torch.randn(_N_TEST, _N_FEATURES, generator=rng).to(device),
            test_attack=(torch.randn(_N_TEST, _N_FEATURES, generator=rng) + 5.0).to(
                device
            ),
        )
    return data


def _make_cfg() -> DatpConfig:
    """Build a minimal DatpConfig for nbaiot_main with 1-round convergence."""
    return BASE_CONFIG.model_copy(
        update={
            "stage": ExperimentStage.NBAIOT_MAIN,
            "model": BASE_CONFIG.model.model_copy(
                update={"input_dim": _N_FEATURES, "encoder_dims": [8, 4]}
            ),
            "dataset": BASE_CONFIG.dataset.model_copy(
                update={"feature_count": _N_FEATURES}
            ),
            "machine": BASE_CONFIG.machine.model_copy(update={"batch_size_train": 64}),
            "federation": FederationConfig(
                local_epochs=1,
                convergence=ConvergenceConfig(
                    rounds_initial=1,
                    rounds_max=1,
                    relative_threshold=0.001,
                    window=2,
                    round_timeout_s=300.0,
                ),
            ),
        }
    )


@pytest.mark.integration
def test_run_nbaiot_main_sweep_end_to_end(tmp_path) -> None:
    """Full nbaiot_main sweep trains all cells, runs poisoning, and writes a manifest with AUROC invariance."""
    cfg = _make_cfg()
    for training_seed in _CONFIG.seeds.training:
        set_seeds(training_seed)
        client_data = _make_client_data(training_seed)
        run_fl_training(
            cfg=cfg,
            client_data=client_data,
            seed=training_seed,
            base_dir=tmp_path,
        )

    manifest = run_nbaiot_main(base_dir=tmp_path, config=_CONFIG)

    assert manifest.n_cells == len(_CONFIG.seeds.training) * _N_CLIENTS * 3 * 4 * 4
    assert len(manifest.results) == manifest.n_cells
    assert set(manifest.mu_flag_threshold_by_training_seed) == set(
        _CONFIG.seeds.training
    )
    assert tuple(sorted(manifest.training_seeds)) == tuple(
        sorted(_CONFIG.seeds.training)
    )
    assert tuple(sorted(manifest.poisoning_seeds)) == tuple(
        sorted(_CONFIG.seeds.poisoning)
    )
    assert manifest.provenance.local_epochs == 1

    assert all(row.auroc_invariant for row in manifest.results)

    zero_fraction_rows = [
        r for r in manifest.results if math.isclose(r.fraction, 0.0, abs_tol=0.0)
    ]
    assert zero_fraction_rows
    assert all(r.delta_tau == pytest.approx(0.0) for r in zero_fraction_rows)

    for row in manifest.results:
        assert hasattr(row, "victim_tpr_clean")
        assert hasattr(row, "victim_delta_tpr")
        assert hasattr(row, "victim_ba_clean")
        assert hasattr(row, "victim_delta_ba")


_SEED = 42


@pytest.mark.integration
def test_score_collection_matches_trained_clients(tmp_path) -> None:
    """Loaded calibration and test scores match the trained client IDs and shapes."""
    set_seeds(_SEED)
    cfg = _make_cfg()
    client_data = _make_client_data(_SEED)
    client_ids = sorted(client_data.keys())

    run_fl_training(cfg=cfg, client_data=client_data, seed=_SEED, base_dir=tmp_path)

    cal_errors = load_main_cal_errors(
        ExperimentStage.NBAIOT_MAIN, _SEED, tmp_path, None
    )
    layout = ArtifactLayout(base_dir=tmp_path, stage=ExperimentStage.NBAIOT_MAIN)
    score_dir = layout.score_cell(
        TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=_SEED)
    ).score_dir
    test_benign = load_parquets_from_dir(
        score_dir / ScoringStage.TEST_BENIGN.value, allow_empty=False
    )
    test_attack = load_parquets_from_dir(
        score_dir / ScoringStage.TEST_ATTACK.value, allow_empty=False
    )
    collection = build_score_collection(
        {
            cid: (cal, test_benign[cid], test_attack[cid])
            for cid, cal in cal_errors.items()
        },
        n_min=N_MIN,
    )

    assert sorted(collection.clients.keys()) == client_ids
    assert collection.eligible_ids == tuple(client_ids)
    assert collection.pending_ids == ()
    for cid in client_ids:
        client = collection.clients[cid]
        assert client.cal.shape[0] == _N_CAL
        assert client.test_benign.shape[0] == _N_TEST
        assert client.test_attack.shape[0] == _N_TEST


@pytest.mark.integration
def test_missing_cell_raises(tmp_path) -> None:
    """Loading calibration errors for a nonexistent training seed raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_main_cal_errors(ExperimentStage.NBAIOT_MAIN, 999, tmp_path, None)


@pytest.mark.integration
def test_write_nbaiot_main_manifest_writes_canonical_path(tmp_path) -> None:
    """Manifest is written to the canonical layout path under the base directory."""
    cfg = _make_cfg()
    for training_seed in _CONFIG.seeds.training:
        set_seeds(training_seed)
        client_data = _make_client_data(training_seed)
        run_fl_training(
            cfg=cfg,
            client_data=client_data,
            seed=training_seed,
            base_dir=tmp_path,
        )

    out_path = write_nbaiot_main_manifest(tmp_path)

    assert out_path.name == "nbaiot_main_manifest.json"
    assert out_path.exists()


def test_run_nbaiot_main_sweep_config_is_required() -> None:
    """run_nbaiot_main requires a config argument (not optional)."""

    import inspect

    sig = inspect.signature(run_nbaiot_main)
    config_param = sig.parameters["config"]
    assert config_param.default is inspect.Parameter.empty, (
        "run_nbaiot_main must not have a default config — "
        "callers must construct and pass CalibrationPoisoningConfig explicitly"
    )
