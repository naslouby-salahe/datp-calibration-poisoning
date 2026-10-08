from __future__ import annotations

from datp.enums import ErrorScope
import torch
import torch.nn as nn
import torch.nn.functional as F

from datp.enums import Activation
from datp.types import FeatureCount

_ACTIVATION_CLASSES: dict[Activation, type[nn.Module]] = {
    Activation.RELU: nn.ReLU,
    Activation.LEAKY_RELU: nn.LeakyReLU,
    Activation.ELU: nn.ELU,
    Activation.TANH: nn.Tanh,
    Activation.SIGMOID: nn.Sigmoid,
}


class Autoencoder(nn.Module):
    def __init__(
        self,
        input_dim: FeatureCount,
        hidden_dims: list[FeatureCount],
        activation: Activation,
        use_bn: bool,
    ) -> None:
        super().__init__()
        if not hidden_dims:
            raise ValueError("hidden_dims must be non-empty")
        if activation not in _ACTIVATION_CLASSES:
            raise ValueError(f"Unknown activation: {activation!r}")

        act_cls = _ACTIVATION_CLASSES[activation]
        dims: list[FeatureCount] = [input_dim, *hidden_dims]

        enc: list[nn.Module] = []
        for i in range(len(dims) - 1):
            enc.extend(
                [nn.Linear(dims[i], dims[i + 1])]
                + ([nn.BatchNorm1d(dims[i + 1])] if use_bn else [])
                + [act_cls()]
            )
        self.encoder = nn.Sequential(*enc)

        dec: list[nn.Module] = []
        dec_dims = dims[::-1]
        for i in range(len(dec_dims) - 1):
            dec.append(nn.Linear(dec_dims[i], dec_dims[i + 1]))
            if i < len(dec_dims) - 2:
                if use_bn:
                    dec.append(nn.BatchNorm1d(dec_dims[i + 1]))
                dec.append(act_cls())
        self.decoder = nn.Sequential(*dec)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        return ((x - self.forward(x)) ** 2).mean(dim=1)

    def reconstruction_loss(self, x: torch.Tensor) -> torch.Tensor:
        return F.mse_loss(self.forward(x), x)


def validate_model_on_cuda(model: nn.Module) -> None:
    for name, param in model.named_parameters():
        if not param.is_cuda:
            raise RuntimeError(
                f"[{ErrorScope.MODELING_AUTOENCODER}] Parameter '{name}' is on {param.device}, not CUDA."
            )
