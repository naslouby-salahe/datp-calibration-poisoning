# SPDX-License-Identifier: Proprietary
"""Shared local training mechanics: batch iteration, loss, optimizers.

Every Flower client delegates to these helpers. No client reimplements the training loop.
"""

from __future__ import annotations

import math
from collections.abc import Iterator

import torch

from datp.core.errors import fmt
from datp.modeling.autoencoder import Autoencoder

_MODULE = "training.local"
_EXPECTED_NON_EMPTY = "> 0 samples"


def _iter_shuffled_batches(
    data: torch.Tensor, batch_size: int
) -> Iterator[torch.Tensor]:
    n = len(data)
    indices = torch.randperm(n, device=data.device)
    for start in range(0, n, batch_size):
        yield data[indices[start : start + batch_size]]


def _validate_training_args(epochs: int, batch_size: int, data: torch.Tensor) -> None:
    if epochs < 1:
        raise ValueError(fmt(_MODULE, "epochs must be >= 1", ">= 1", str(epochs)))
    if batch_size < 1:
        raise ValueError(
            fmt(_MODULE, "batch_size must be >= 1", ">= 1", str(batch_size))
        )
    if data.numel() == 0:
        raise ValueError(
            fmt(_MODULE, "training data must be non-empty", _EXPECTED_NON_EMPTY, "0")
        )


def _check_finite_loss(last_loss: float) -> None:
    if not math.isfinite(last_loss):
        raise RuntimeError(
            fmt(
                _MODULE,
                "Training produced non-finite loss",
                "finite loss",
                repr(last_loss),
            )
        )


def _proximal_loss(
    model: torch.nn.Module,
    recon_loss: torch.Tensor,
    mu: float,
    global_params: list[torch.Tensor],
) -> torch.Tensor:
    prox_term = sum(
        ((p - gp) ** 2).sum()
        for p, gp in zip(model.parameters(), global_params, strict=True)
    )
    return recon_loss + 0.5 * mu * prox_term


def _run_ae_epoch(
    model: Autoencoder,
    data: torch.Tensor,
    batch_size: int,
    optimizer: torch.optim.Optimizer,
    mu: float,
    global_params: list[torch.Tensor] | None,
) -> float:
    epoch_loss = 0.0
    n_batches = 0
    for batch in _iter_shuffled_batches(data, batch_size):
        optimizer.zero_grad()
        x_hat = model(batch)
        recon_loss = torch.nn.functional.mse_loss(x_hat, batch)
        loss = (
            _proximal_loss(model, recon_loss, mu, global_params)
            if mu > 0 and global_params is not None
            else recon_loss
        )
        loss.backward()
        optimizer.step()
        epoch_loss += recon_loss.item()
        n_batches += 1
    return epoch_loss / max(n_batches, 1)


def _run_decoder_epoch(
    model: Autoencoder,
    data: torch.Tensor,
    batch_size: int,
    optimizer: torch.optim.Optimizer,
) -> float:
    epoch_loss = 0.0
    n_batches = 0
    for batch in _iter_shuffled_batches(data, batch_size):
        optimizer.zero_grad()
        with torch.no_grad():
            z = model.encoder(batch)
        x_hat = model.decoder(z)
        loss = torch.nn.functional.mse_loss(x_hat, batch)
        loss.backward()
        optimizer.step()
        epoch_loss += loss.item()
        n_batches += 1
    return epoch_loss / max(n_batches, 1)


def train_local(
    model: Autoencoder,
    data: torch.Tensor,
    *,
    epochs: int,
    batch_size: int,
    lr: float,
    mu: float = 0.0,
    global_params: list[torch.Tensor] | None = None,
) -> float:
    """Standard AE local training loop with optional proximal regularization term.

    Returns the average reconstruction loss of the final epoch.
    When mu > 0, the proximal term (mu/2)||w - w_global||² is added to the loss.
    """
    _validate_training_args(epochs, batch_size, data)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=0.0)
    last_loss = float("nan")
    for _epoch in range(epochs):
        last_loss = _run_ae_epoch(model, data, batch_size, optimizer, mu, global_params)
    _check_finite_loss(last_loss)
    return last_loss


def train_decoder_only(
    model: Autoencoder,
    data: torch.Tensor,
    *,
    epochs: int,
    batch_size: int,
    lr: float,
) -> float:
    """Local decoder training with the encoder frozen.

    Returns the average reconstruction loss of the final epoch.
    """
    _validate_training_args(epochs, batch_size, data)
    decoder_optimizer = torch.optim.Adam(
        model.decoder.parameters(), lr=lr, weight_decay=0.0
    )
    last_loss = float("nan")
    for _epoch in range(epochs):
        last_loss = _run_decoder_epoch(model, data, batch_size, decoder_optimizer)
    _check_finite_loss(last_loss)
    return last_loss


def evaluate_benign(model: Autoencoder, val_data: torch.Tensor) -> float:
    """Benign-only validation loss — never evaluated on attack data."""
    if val_data.numel() == 0:
        raise ValueError(
            fmt(_MODULE, "validation data must be non-empty", _EXPECTED_NON_EMPTY, "0")
        )
    model.eval()
    with torch.inference_mode():
        x_hat = model(val_data)
        return torch.nn.functional.mse_loss(x_hat, val_data).item()
