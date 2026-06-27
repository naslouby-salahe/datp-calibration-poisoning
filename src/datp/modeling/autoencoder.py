"""Stacked autoencoder with configurable activation, batch norm, and bottleneck."""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from datp.core.enums import Activation

_ACTIVATION_CLASSES: dict[Activation, type[nn.Module]] = {
    Activation.RELU: nn.ReLU,
    Activation.LEAKY_RELU: nn.LeakyReLU,
    Activation.ELU: nn.ELU,
    Activation.TANH: nn.Tanh,
    Activation.SIGMOID: nn.Sigmoid,
}


class Autoencoder(nn.Module):
    """Symmetric stacked autoencoder with a configurable bottleneck dimension."""

    def __init__(
        self,
        input_dim: int,
        hidden_dims: list[int],
        activation: Activation,
        use_bn: bool,
    ) -> None:
        """Initialize encoder and decoder stacks with the given architecture hyperparameters."""
        super().__init__()
        if not hidden_dims:
            raise ValueError("hidden_dims must be non-empty")
        if activation not in _ACTIVATION_CLASSES:
            raise ValueError(f"Unknown activation: {activation!r}")

        act_cls = _ACTIVATION_CLASSES[activation]
        dims = [input_dim, *hidden_dims]

        enc = []
        for i in range(len(dims) - 1):
            enc.extend(
                [nn.Linear(dims[i], dims[i + 1])]
                + ([nn.BatchNorm1d(dims[i + 1])] if use_bn else [])
                + [act_cls()]
            )
        self.encoder = nn.Sequential(*enc)

        dec = []
        dec_dims = dims[::-1]
        for i in range(len(dec_dims) - 1):
            dec.append(nn.Linear(dec_dims[i], dec_dims[i + 1]))
            if i < len(dec_dims) - 2:
                if use_bn:
                    dec.append(nn.BatchNorm1d(dec_dims[i + 1]))
                dec.append(act_cls())
        self.decoder = nn.Sequential(*dec)

        self._bottleneck_dim = hidden_dims[-1]

    @property
    def bottleneck_dim(self) -> int:
        """Dimensionality of the latent bottleneck."""
        return self._bottleneck_dim

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        """Project input through the encoder to the bottleneck representation."""
        return self.encoder(x)

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """Reconstruct input from a bottleneck representation."""
        return self.decoder(z)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Full encode-decode pass returning the reconstruction."""
        return self.decode(self.encode(x))

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        """Per-sample MSE between input and reconstruction.

        Returns a 1-D tensor of shape ``(batch_size,)``.
        """
        return ((x - self.forward(x)) ** 2).mean(dim=1)

    def reconstruction_loss(self, x: torch.Tensor) -> torch.Tensor:
        """Scalar MSE loss between input and its reconstruction."""
        return F.mse_loss(self.forward(x), x)


def validate_model_on_cuda(model: nn.Module) -> None:
    """Raise if any model parameter is not on a CUDA device."""
    for name, param in model.named_parameters():
        if not param.is_cuda:
            raise RuntimeError(
                f"[modeling.autoencoder] Parameter '{name}' is on {param.device}, not CUDA."
            )
