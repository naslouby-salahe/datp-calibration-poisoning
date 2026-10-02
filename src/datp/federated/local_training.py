from __future__ import annotations

from datp.types import (
    BatchSize,
    EpochCount,
    LearningRate,
    ScoreValue,
)


import math
from typing import Protocol, cast

import torch

from datp.modeling.autoencoder import Autoencoder


class _Loss(Protocol):
    def backward(self) -> None: ...
    def item(self) -> float: ...


class _Optimizer(Protocol):
    def zero_grad(self) -> None: ...
    def step(self) -> None: ...


def _validate_training_args(epochs: EpochCount, batch_size: BatchSize, data: torch.Tensor) -> None:
    if epochs < 1 or batch_size < 1:
        raise ValueError(
            f"epochs and batch_size must be >= 1 (got {epochs}, {batch_size})"
        )
    if data.numel() == 0:
        raise ValueError("training data must be non-empty")


def _check_finite_loss(last_loss: ScoreValue) -> None:
    if not math.isfinite(last_loss):
        raise RuntimeError(f"Training produced non-finite loss: {last_loss}")


def train_local(
    model: Autoencoder, data: torch.Tensor, *, epochs: EpochCount, batch_size: BatchSize, lr: LearningRate
) -> ScoreValue:
    _validate_training_args(epochs, batch_size, data)
    optimizer = cast(
        _Optimizer, torch.optim.Adam(model.parameters(), lr=lr, weight_decay=0.0)
    )
    last_loss = math.nan
    n = len(data)

    for _ in range(epochs):
        indices = torch.randperm(n, device=data.device)
        epoch_loss = 0.0
        n_batches = 0

        for start in range(0, n, batch_size):
            batch = data[indices[start : start + batch_size]]
            optimizer.zero_grad()
            loss = cast(_Loss, model.reconstruction_loss(batch))
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        last_loss = epoch_loss / max(n_batches, 1)

    _check_finite_loss(last_loss)
    return last_loss


def evaluate_benign(model: Autoencoder, cal_data: torch.Tensor) -> ScoreValue:
    if cal_data.numel() == 0:
        raise ValueError("calibration data must be non-empty")
    model.eval()
    with torch.inference_mode():
        return model.reconstruction_loss(cal_data).item()
