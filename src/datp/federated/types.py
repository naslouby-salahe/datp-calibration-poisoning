"""Shared types and validators for federated client data."""

from __future__ import annotations

import enum
from dataclasses import dataclass

import torch


class ClientMetricKey(enum.StrEnum):
    """Keys for per-client training and validation loss metrics."""

    TRAIN_LOSS = "train_loss"
    VAL_LOSS = "val_loss"


@dataclass(frozen=True, slots=True)
class ClientData:
    """Per-client tensors for train, validation, benign test, and attack test splits."""

    train: torch.Tensor
    val: torch.Tensor
    test_benign: torch.Tensor
    test_attack: torch.Tensor


def validate_tensor_input(
    tensor: torch.Tensor, name: str, client_id: str, expected_dim: int | None = None
) -> None:
    """Validate that a client tensor is 2-D, non-empty, finite, and of expected width."""
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
    client_data: ClientData, client_id: str, expected_dim: int | None = None
) -> None:
    """Validate all four tensors in a ClientData record."""
    for name in ("train", "val", "test_benign", "test_attack"):
        validate_tensor_input(getattr(client_data, name), name, client_id, expected_dim)
