# SPDX-License-Identifier: Proprietary
"""Domain types for training: ClientData and validation helpers."""

from __future__ import annotations

import enum
from dataclasses import dataclass

import torch

from datp.core.errors import fmt

_MODULE = "federated.types"
_EXPECTED_NDIM = 2


class ClientMetricKey(enum.StrEnum):
    """Canonical metric keys returned by all client fit()/evaluate()."""

    TRAIN_LOSS = "train_loss"
    VAL_LOSS = "val_loss"


@dataclass(frozen=True, slots=True)
class ClientData:
    """All tensors are 2-D: (n_samples, input_dim)."""

    train: torch.Tensor
    val: torch.Tensor
    test_benign: torch.Tensor
    test_attack: torch.Tensor


def validate_tensor_2d(tensor: torch.Tensor, name: str, client_id: str) -> None:
    if tensor.ndim != _EXPECTED_NDIM:
        raise ValueError(
            fmt(
                _MODULE,
                f"{name} must be 2-D for client {client_id}",
                f"ndim={_EXPECTED_NDIM}",
                f"ndim={tensor.ndim}, shape={tuple(tensor.shape)}",
            )
        )


def validate_tensor_non_empty(tensor: torch.Tensor, name: str, client_id: str) -> None:
    if tensor.numel() == 0:
        raise ValueError(
            fmt(
                _MODULE,
                f"{name} must be non-empty for client {client_id}",
                "> 0 elements",
                "0 elements",
            )
        )


def validate_tensor_finite(tensor: torch.Tensor, name: str, client_id: str) -> None:
    if not torch.isfinite(tensor).all():
        n_nonfinite = int((~torch.isfinite(tensor)).sum().item())
        raise ValueError(
            fmt(
                _MODULE,
                f"{name} contains non-finite values for client {client_id}",
                "all finite",
                f"{n_nonfinite} non-finite values",
            )
        )


def validate_feature_dim(
    tensor: torch.Tensor, expected_dim: int, name: str, client_id: str
) -> None:
    if tensor.shape[1] != expected_dim:
        raise ValueError(
            fmt(
                _MODULE,
                f"{name} feature dimension mismatch for client {client_id}",
                f"dim={expected_dim}",
                f"dim={tensor.shape[1]}",
            )
        )


def validate_client_data(
    client_data: ClientData, client_id: str, expected_dim: int | None = None
) -> None:
    """Validate all tensors in a ClientData instance."""
    for name in ("train", "val", "test_benign", "test_attack"):
        tensor = getattr(client_data, name)
        validate_tensor_2d(tensor, name, client_id)
        validate_tensor_non_empty(tensor, name, client_id)
        validate_tensor_finite(tensor, name, client_id)
        if expected_dim is not None:
            validate_feature_dim(tensor, expected_dim, name, client_id)


def validate_tensor_input(
    tensor: torch.Tensor, name: str, client_id: str, expected_dim: int | None = None
) -> None:
    """Validate a single input tensor before training or evaluation."""
    validate_tensor_2d(tensor, name, client_id)
    validate_tensor_non_empty(tensor, name, client_id)
    validate_tensor_finite(tensor, name, client_id)
    if expected_dim is not None:
        validate_feature_dim(tensor, expected_dim, name, client_id)
