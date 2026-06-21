from __future__ import annotations

import pytest

from datp.config.stages import ExperimentStage
from datp.core.seeds import set_seeds
from datp.federated.protocols.fedavg import run_fl_training
from tests.fixtures.fl_training import SEED, make_client_data, make_fl_cfg


@pytest.mark.integration
def test_synthetic_smoke(tmp_path) -> None:
    cfg = make_fl_cfg(
        stage=ExperimentStage.SYNTHETIC_SMOKE, rounds=2, encoder_dims=[8, 4, 8]
    )
    client_data = make_client_data(n_clients=2)

    result = run_fl_training(
        cfg=cfg,
        client_data=client_data,
        seed=SEED,
        base_dir=tmp_path,
    )

    assert result.stage == ExperimentStage.SYNTHETIC_SMOKE
    assert result.total_rounds >= 1
    assert result.checkpoint_dir.exists()
    assert (result.checkpoint_dir / "model.pt").exists()
    assert result.score_dir.exists()


@pytest.mark.integration
def test_nbaiot_full_loop(tmp_path) -> None:
    n_virtual_clients = 4  # Reduced from 20 for test speed
    cfg = make_fl_cfg(
        stage=ExperimentStage.NBAIOT_FULL_OPTIONAL, rounds=2, encoder_dims=[8, 4, 8]
    )
    client_data = make_client_data(n_clients=n_virtual_clients, seed=SEED)

    result = run_fl_training(
        cfg=cfg,
        client_data=client_data,
        seed=SEED,
        base_dir=tmp_path,
    )

    assert result.stage == ExperimentStage.NBAIOT_FULL_OPTIONAL
    assert result.total_rounds >= 1
    assert result.checkpoint_dir.exists()
    assert (result.checkpoint_dir / "model.pt").exists()
    assert result.score_dir.exists()


@pytest.mark.integration
def test_nbaiot_main_smoke(tmp_path) -> None:
    set_seeds(SEED)
    cfg = make_fl_cfg(
        stage=ExperimentStage.NBAIOT_MAIN, rounds=2, encoder_dims=[8, 4, 8]
    )
    client_data = make_client_data(n_clients=9)

    result = run_fl_training(
        cfg=cfg,
        client_data=client_data,
        seed=SEED,
        base_dir=tmp_path,
    )

    assert result.stage == ExperimentStage.NBAIOT_MAIN
    assert result.total_rounds >= 1
    assert result.checkpoint_dir.exists()
    assert result.score_dir.exists()


@pytest.mark.integration
def test_convergence_round_logged(tmp_path) -> None:
    set_seeds(SEED)
    cfg = make_fl_cfg(
        stage=ExperimentStage.NBAIOT_MAIN, rounds=2, encoder_dims=[8, 4, 8]
    )
    client_data = make_client_data(n_clients=2)

    result = run_fl_training(
        cfg=cfg,
        client_data=client_data,
        seed=SEED,
        base_dir=tmp_path,
    )

    # Convergence may or may not trigger on 2 rounds
    assert result.converged_round is None or isinstance(result.converged_round, int)
    assert len(result.loss_history) > 0
    assert result.total_rounds >= 1
