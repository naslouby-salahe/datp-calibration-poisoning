from __future__ import annotations

from datp.types import (
    ClientId,
    SignedCount,
)


import enum
from dataclasses import dataclass

import torch


class ClientMetricKey(enum.StrEnum):

    TRAIN_LOSS = "train_loss"
    VAL_LOSS = "val_loss"


class FederatedTensorLabel(enum.StrEnum):

    TRAIN = "train"
    VALIDATION = "val"
    BENIGN_TEST = "test_benign"
    ATTACK_TEST = "test_attack"
    TRAIN_DATA = "train_data"
    CALIBRATION_DATA = "cal_data"


@dataclass(frozen=True, slots=True)
class ClientData:

    train: torch.Tensor
    val: torch.Tensor
    test_benign: torch.Tensor
    test_attack: torch.Tensor


def validate_tensor_input(
    tensor: torch.Tensor,
    name: FederatedTensorLabel,
    client_id: ClientId,
    expected_dim: SignedCount | None = None,
) -> None:
    if tensor.ndim != 2:
        raise ValueError(f"{name} must be 2-D for {client_id} (got {tensor.ndim})")
    if tensor.numel() == 0:
        raise ValueError(f"{name} must be non-empty for {client_id}")
    if (~torch.isfinite(tensor)).any():
        raise ValueError(f"{name} contains non-finite values for {client_id}")
    if expected_dim is not None and tensor.shape[1] != expected_dim:
        raise ValueError(
            f"{name} expected dimension {expected_dim} for {client_id} (got {tensor.shape[1]})"
        )


def validate_client_data(
    client_data: ClientData, client_id: ClientId, expected_dim: SignedCount | None = None
) -> None:
    validate_tensor_input(client_data.train, FederatedTensorLabel.TRAIN, client_id, expected_dim)
    validate_tensor_input(client_data.val, FederatedTensorLabel.VALIDATION, client_id, expected_dim)
    validate_tensor_input(
        client_data.test_benign, FederatedTensorLabel.BENIGN_TEST, client_id, expected_dim
    )
    validate_tensor_input(
        client_data.test_attack, FederatedTensorLabel.ATTACK_TEST, client_id, expected_dim
    )
