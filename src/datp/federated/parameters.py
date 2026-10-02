
from __future__ import annotations
from datp.types import ParameterVector
from typing import Protocol, cast

import torch
import torch.nn as nn


class _TorchArrayFactory(Protocol):
    def from_numpy(self, ndarray: ParameterVector) -> torch.Tensor: ...


def get_parameters(model: nn.Module) -> list[ParameterVector]:
    return [p.detach().cpu().numpy().copy() for p in model.parameters()]


def set_parameters(model: nn.Module, parameters: list[ParameterVector]) -> None:
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
                cast(_TorchArrayFactory, torch).from_numpy(arr).to(
                    dtype=param.dtype, device=param.device
                )
            )
