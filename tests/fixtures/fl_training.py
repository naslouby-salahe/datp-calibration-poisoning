"""Fixtures and helpers for federated learning training tests."""

from __future__ import annotations

import torch

from datp.checkpointing.enums import CheckpointProtocolMode
from datp.config.compose import BASE_CONFIG
from datp.config.models import ConvergenceConfig, DatpConfig, FederationConfig
from datp.config.models import ExperimentStage
from datp.federated.types import ClientData

N_FEATURES = 10
N_TRAIN = 200
N_VAL = 50
N_TEST = 50
SEED = 42


def make_client_data(n_clients: int, seed: int = SEED) -> dict[str, ClientData]:
    """Generate mock client datasets with train, val, test_benign, and test_attack splits."""
    device = torch.device("cpu")
    rng = torch.Generator().manual_seed(seed)
    data = {}
    for i in range(n_clients):
        data[f"client_{i}"] = ClientData(
            train=torch.randn(N_TRAIN, N_FEATURES, generator=rng).to(device),
            val=torch.randn(N_VAL, N_FEATURES, generator=rng).to(device),
            test_benign=torch.randn(N_TEST, N_FEATURES, generator=rng).to(device),
            test_attack=(torch.randn(N_TEST, N_FEATURES, generator=rng) + 5.0).to(
                device
            ),
        )
    return data


def make_fl_cfg(
    stage: ExperimentStage = ExperimentStage.NBAIOT_MAIN,
    n_features: int = N_FEATURES,
    rounds: int = 2,
    encoder_dims: list[int] | None = None,
) -> DatpConfig:
    """Build a federated learning configuration instance with customized parameters."""
    checkpoint_protocol = BASE_CONFIG.checkpoint_protocol
    disabled_checkpoint_protocol = (
        checkpoint_protocol.model_copy(update={"mode": CheckpointProtocolMode.DISABLED})
        if checkpoint_protocol is not None
        else None
    )
    return BASE_CONFIG.model_copy(
        update={
            "stage": stage,
            "model": BASE_CONFIG.model.model_copy(
                update={
                    "input_dim": n_features,
                    "encoder_dims": encoder_dims or [8, 4],
                }
            ),
            "dataset": BASE_CONFIG.dataset.model_copy(
                update={"feature_count": n_features}
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
            "checkpoint_protocol": disabled_checkpoint_protocol,
        }
    )
