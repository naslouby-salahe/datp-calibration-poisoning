
from __future__ import annotations
from datp.types import (
    Probability,
    ScoreVector,
)

import math
from itertools import product

import numpy as np
from numpy.typing import NDArray

from datp.attacks.constants import PERMUTATION_MAX_EXACT_SEEDS


def sign_flip_p_value(values: ScoreVector) -> Probability:
    arr = np.asarray(values, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    n = arr.size
    if n == 0:
        return math.nan
    if n > PERMUTATION_MAX_EXACT_SEEDS:
        raise ValueError(
            f"exact sign-flip test supports at most {PERMUTATION_MAX_EXACT_SEEDS} seeds; got {n}"
        )
    signs: NDArray[np.float64] = np.array(
        list(product((-1.0, 1.0), repeat=n)), dtype=np.float64
    )
    means = np.abs((signs * arr).mean(axis=1))
    observed = abs(float(arr.mean()))
    extreme: NDArray[np.bool_] = means >= observed - 1e-15
    return float(np.count_nonzero(extreme) / extreme.size)
