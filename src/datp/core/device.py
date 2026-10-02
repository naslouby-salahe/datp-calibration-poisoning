
from __future__ import annotations

import torch

from datp.core.enums import DeviceType


def resolve_device(require_cuda: bool) -> torch.device:
    if require_cuda and not torch.cuda.is_available():
        raise RuntimeError(
            "[core.device] CUDA required by config but not available. "
            "Expected: True. Got: False."
        )
    return torch.device(DeviceType.CUDA if require_cuda else DeviceType.CPU)
