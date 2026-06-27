"""Model parameter serialization between numpy arrays and PyTorch tensors."""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn


def get_parameters(model: nn.Module) -> list[np.ndarray]:
    """Extract all model parameters as detached numpy copies."""
    return [p.detach().cpu().numpy().copy() for p in model.parameters()]


def set_parameters(model: nn.Module, parameters: list[np.ndarray]) -> None:
    """Copy numpy arrays back into model parameters in place, validating shapes."""
    params_list = list(model.parameters())
    if len(params_list) != len(parameters):
        raise ValueError(
            f"Parameter count mismatch: {len(params_list)} vs {len(parameters)}"
        )
    with torch.no_grad():
        for i, (param, arr) in enumerate(zip(params_list, parameters, strict=True)):
            if tuple(param.shape) != tuple(arr.shape):
                raise ValueError(
                    f"Shape mismatch at index {i}: {param.shape} vs {arr.shape}"
                )
            param.copy_(
                torch.from_numpy(arr).to(dtype=param.dtype, device=param.device)
            )
