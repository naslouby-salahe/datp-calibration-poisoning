"""Integration test for the single bounded sweep run path .

Exercises the same wiring the real 1620-cell N-BaIoT execution uses:
real_score_loader -> bounded_matrix -> bounded_runner -> bounded_manifest, end to end,
against tiny FL-trained artifacts for all 5 locked seeds.
"""

from __future__ import annotations

import pytest
import torch

from datp.artifacts.poison_names import POISONING_SEEDS, TRAINING_SEEDS
from datp.attacks.bounded_sweep_run import run_nbaiot_bounded_sweep, write_nbaiot_bounded_sweep_manifest
from datp.config.compose import BASE_CONFIG
from datp.config.models import ConvergenceConfig, DatpConfig, FederationConfig
from datp.core.device import resolve_device
from datp.core.enums import Regime
from datp.core.seeds import set_seeds
from datp.federated.protocols.fedavg import run_fl_training
from datp.federated.types import ClientData

_N_FEATURES = 10
_N_TRAIN = 200
_N_CAL = 150
_N_TEST = 50
_N_CLIENTS = 4 # B4_CLUSTER's locked K=3 requires eligible_count > k


def _make_client_data(seed: int) -> dict[str, ClientData]:
    device = resolve_device(require_cuda=True)
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
    return BASE_CONFIG.model_copy(
        update={
            "regime": Regime.A,
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
def test_run_nbaiot_bounded_sweep_end_to_end(tmp_path) -> None:
    cfg = _make_cfg()
    for training_seed in TRAINING_SEEDS:
        set_seeds(training_seed)
        client_data = _make_client_data(training_seed)
        run_fl_training(
            cfg=cfg,
            client_data=client_data,
            seed=training_seed,
            alpha=None,
            base_dir=tmp_path,
        )

    manifest = run_nbaiot_bounded_sweep(base_dir=tmp_path)

    assert manifest.n_cells == len(TRAINING_SEEDS) * _N_CLIENTS * 3 * 3 * 4
    assert len(manifest.results) == manifest.n_cells
    assert set(manifest.mu_flag_threshold_by_training_seed) == set(TRAINING_SEEDS)
    assert tuple(sorted(manifest.training_seeds)) == tuple(sorted(TRAINING_SEEDS))
    assert tuple(sorted(manifest.poisoning_seeds)) == tuple(sorted(POISONING_SEEDS))
    assert manifest.provenance.local_epochs == 1

    # Calibration-channel-only invariant: every cell's test scores were untouched.
    assert all(row.auroc_invariant for row in manifest.results)

    # f=0.0 cells must carry exactly zero Δτ (no-op poisoning).
    zero_fraction_rows = [r for r in manifest.results if r.fraction == 0.0]
    assert zero_fraction_rows
    assert all(r.delta_tau == 0.0 for r in zero_fraction_rows)


@pytest.mark.integration
def test_write_nbaiot_bounded_sweep_manifest_writes_canonical_path(tmp_path) -> None:
    cfg = _make_cfg()
    for training_seed in TRAINING_SEEDS:
        set_seeds(training_seed)
        client_data = _make_client_data(training_seed)
        run_fl_training(
            cfg=cfg,
            client_data=client_data,
            seed=training_seed,
            alpha=None,
            base_dir=tmp_path,
        )

    out_path = write_nbaiot_bounded_sweep_manifest(tmp_path)

    assert out_path.name == "nbaiot_bounded_sweep_manifest.json"
    assert out_path.exists()
