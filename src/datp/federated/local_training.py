"""Local autoencoder training and evaluation loops for FL clients."""

from __future__ import annotations

import math

import torch

from datp.modeling.autoencoder import Autoencoder


def _validate_training_args(epochs: int, batch_size: int, data: torch.Tensor) -> None:
    """Raise if local-training hyperparameters or data are invalid."""
    if epochs < 1 or batch_size < 1:
        raise ValueError(
            f"epochs and batch_size must be >= 1 (got {epochs}, {batch_size})"
        )
    if data.numel() == 0:
        raise ValueError("training data must be non-empty")


def _check_finite_loss(last_loss: float) -> None:
    """Raise if the final epoch loss is non-finite."""
    if not math.isfinite(last_loss):
        raise RuntimeError(f"Training produced non-finite loss: {last_loss}")


def train_local(
    model: Autoencoder, data: torch.Tensor, *, epochs: int, batch_size: int, lr: float
) -> float:
    """Run SGD training on a single client's data, returning the final epoch loss."""
    _validate_training_args(epochs, batch_size, data)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=0.0)
    last_loss = float("nan")
    n = len(data)

    for _ in range(epochs):
        indices = torch.randperm(n, device=data.device)
        epoch_loss = 0.0
        n_batches = 0

        for start in range(0, n, batch_size):
            batch = data[indices[start : start + batch_size]]
            optimizer.zero_grad()
            loss = torch.nn.functional.mse_loss(model(batch), batch)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        last_loss = epoch_loss / max(n_batches, 1)

    _check_finite_loss(last_loss)
    return last_loss


def evaluate_benign(model: Autoencoder, cal_data: torch.Tensor) -> float:
    """Compute MSE reconstruction loss on calibration data in inference mode."""
    if cal_data.numel() == 0:
        raise ValueError("calibration data must be non-empty")
    model.eval()
    with torch.inference_mode():
        return torch.nn.functional.mse_loss(model(cal_data), cal_data).item()
