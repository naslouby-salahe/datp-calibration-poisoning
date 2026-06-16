from __future__ import annotations

import pytest
import torch

from datp.config.compose import BASE_CONFIG
from datp.config.models import (
    ConvergenceConfig,
    DatpConfig,
    FederationConfig,
)
from datp.core.device import resolve_device
from datp.core.enums import CheckpointProtocolMode, Regime
from datp.core.seeds import set_seeds
from datp.federated.protocols.fedavg import run_fl_training
from datp.federated.types import ClientData

_N_FEATURES = 10
_N_TRAIN = 200
_N_VAL = 50
_N_TEST = 50
_SEED = 42


def _make_client_data(n_clients: int, seed: int = _SEED) -> dict[str, ClientData]:
    device = resolve_device(require_cuda=True)
    rng = torch.Generator().manual_seed(seed)
    data = {}
    for i in range(n_clients):
        data[f"client_{i}"] = ClientData(
            train=torch.randn(_N_TRAIN, _N_FEATURES, generator=rng).to(device),
            val=torch.randn(_N_VAL, _N_FEATURES, generator=rng).to(device),
            test_benign=torch.randn(_N_TEST, _N_FEATURES, generator=rng).to(device),
            test_attack=(torch.randn(_N_TEST, _N_FEATURES, generator=rng) + 5.0).to(
                device
            ),
        )
    return data


def _make_cfg(
    regime: Regime,
    n_features: int = _N_FEATURES,
    rounds: int = 2,
) -> DatpConfig:
    return BASE_CONFIG.model_copy(
        update={
            "regime": regime,
            "model": BASE_CONFIG.model.model_copy(
                update={
                    "input_dim": n_features,
                    "encoder_dims": [8, 4, 8],
                }
            ),
            "dataset": BASE_CONFIG.dataset.model_copy(
                update={
                    "feature_count": n_features,
                }
            ),
            "machine": BASE_CONFIG.machine.model_copy(
                update={
                    "batch_size_train": 64,
                }
            ),
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
            # Disable checkpoint protocol: these tests verify basic FL training
            # and scoring behavior, not the checkpoint protocol artifact layout.
            "checkpoint_protocol": BASE_CONFIG.checkpoint_protocol.model_copy(
                update={"mode": CheckpointProtocolMode.DISABLED}
            ),
        }
    )


@pytest.mark.integration
def test_regime_b_smoke(tmp_path) -> None:
    cfg = _make_cfg(regime=Regime.B, rounds=2)
    client_data = _make_client_data(n_clients=2)

    result = run_fl_training(
        cfg=cfg,
        client_data=client_data,
        seed=_SEED,
        alpha=None,
        base_dir=tmp_path,
    )

    assert result.regime == Regime.B
    assert result.total_rounds >= 1
    assert result.checkpoint_dir.exists()
    assert (result.checkpoint_dir / "model.pt").exists()
    assert result.score_dir.exists()


@pytest.mark.integration
def test_regime_c_loop(tmp_path) -> None:
    alpha_levels = [0.1, 0.5, 1.0, 5.0, 10.0, float("inf")]
    n_virtual_clients = 4 # Reduced from 20 for test speed

    for alpha in alpha_levels:
        cfg = _make_cfg(regime=Regime.C, rounds=2)
        client_data = _make_client_data(n_clients=n_virtual_clients, seed=_SEED)

        result = run_fl_training(
            cfg=cfg,
            client_data=client_data,
            seed=_SEED,
            alpha=alpha,
            base_dir=tmp_path,
        )

        assert result.regime == Regime.C
        assert result.alpha == alpha
        assert result.total_rounds >= 1
        assert result.checkpoint_dir.exists()
        assert (result.checkpoint_dir / "model.pt").exists()
        assert result.score_dir.exists()


@pytest.mark.integration
def test_regime_a_smoke(tmp_path) -> None:
    set_seeds(_SEED)
    cfg = _make_cfg(regime=Regime.A, rounds=2)
    client_data = _make_client_data(n_clients=9)

    result = run_fl_training(
        cfg=cfg,
        client_data=client_data,
        seed=_SEED,
        alpha=None,
        base_dir=tmp_path,
    )

    assert result.regime == Regime.A
    assert result.total_rounds >= 1
    assert result.checkpoint_dir.exists()
    assert result.score_dir.exists()


@pytest.mark.integration
def test_convergence_round_logged(tmp_path) -> None:
    set_seeds(_SEED)
    cfg = _make_cfg(regime=Regime.A, rounds=2)
    client_data = _make_client_data(n_clients=2)

    result = run_fl_training(
        cfg=cfg,
        client_data=client_data,
        seed=_SEED,
        alpha=None,
        base_dir=tmp_path,
    )

    # Convergence may or may not trigger on 2 rounds
    assert result.converged_round is None or isinstance(result.converged_round, int)
    assert len(result.loss_history) > 0
    assert result.total_rounds >= 1
