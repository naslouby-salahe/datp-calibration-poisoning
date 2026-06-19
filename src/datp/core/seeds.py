import os
import random

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import torch
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SeedPair:
    training_seed: int
    poisoning_seed: int


def set_seeds(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    # 'high' precision allows Tensor Cores; does not affect reconstruction-error ranking.
    torch.set_float32_matmul_precision("high")
