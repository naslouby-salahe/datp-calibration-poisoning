"""Integration tests for loading real calibration and test scores from trained checkpoints."""

from __future__ import annotations

import pytest
import torch

from datp.artifacts.layout import ArtifactLayout
from datp.attacks.constants import N_MIN
from datp.attacks.score_containers import build_score_collection
from datp.core.enums import ScoringStage
from datp.scoring.loading import load_main_cal_errors
from datp.scoring.loading import load_parquets_from_dir
from datp.config.compose import BASE_CONFIG
from datp.config.models import ConvergenceConfig, DatpConfig, FederationConfig
from datp.core.device import resolve_device
from datp.config.models import ExperimentStage
from datp.core.identity import TrainingCellId
from datp.core.seeds import set_seeds
from datp.federated.protocols.fedavg import run_fl_training
from datp.federated.types import ClientData

_N_FEATURES = 10
_N_TRAIN = 200
_N_CAL = 150
_N_TEST = 50
_SEED = 42


def _make_client_data(n_clients: int, seed: int = _SEED) -> dict[str, ClientData]:
    """Build deterministic synthetic client data for a configurable number of clients."""
    device = resolve_device(require_cuda=False)
    rng = torch.Generator().manual_seed(seed)
    data = {}
    for i in range(n_clients):
        data[f"client_{i}"] = ClientData(
            train=torch.randn(_N_TRAIN, _N_FEATURES, generator=rng).to(device),
            val=torch.randn(_N_CAL, _N_FEATURES, generator=rng).to(device),
            test_benign=torch.randn(_N_TEST, _N_FEATURES, generator=rng).to(device),
            test_attack=(torch.randn(_N_TEST, _N_FEATURES, generator=rng) + 5.0).to(
                device
            ),
        )
    return data


def _make_cfg(rounds: int = 2) -> DatpConfig:
    """Build a minimal DatpConfig for nbaiot_main with configurable rounds."""
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
                    rounds_max=rounds,
                    relative_threshold=0.001,
                    window=2,
                    round_timeout_s=300.0,
                ),
            ),
        }
    )


@pytest.mark.integration
def test_load_real_score_collection_matches_trained_clients(tmp_path) -> None:
    """Real score collection built from loaded parquets matches trained client IDs and shapes."""
    set_seeds(_SEED)
    cfg = _make_cfg(rounds=2)
    client_data = _make_client_data(n_clients=3)
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
def test_load_real_score_collection_missing_cell_raises(tmp_path) -> None:
    """Loading calibration errors for a nonexistent training seed raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_main_cal_errors(ExperimentStage.NBAIOT_MAIN, 999, tmp_path, None)
