"""Exact sign-flip permutation test over paired seed-level deltas."""

from __future__ import annotations

import math
from itertools import product

import numpy as np

from datp.attacks.constants import PERMUTATION_MAX_EXACT_SEEDS


def sign_flip_p_value(values: np.ndarray) -> float:
    """Return the exact two-sided sign-flip permutation p-value for the mean of paired deltas."""
    arr = np.asarray(values, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    n = arr.size
    if n == 0:
        return math.nan
    if n > PERMUTATION_MAX_EXACT_SEEDS:
        raise ValueError(
            f"exact sign-flip test supports at most {PERMUTATION_MAX_EXACT_SEEDS} seeds; got {n}"
        )
    signs = np.array(list(product((-1.0, 1.0), repeat=n)))
    means = np.abs((signs * arr).mean(axis=1))
    observed = abs(float(arr.mean()))
    return float(np.mean(means >= observed - 1e-15))
