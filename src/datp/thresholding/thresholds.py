
from __future__ import annotations

import numpy as np

from datp.types import (
    Quantile,
    ScoreVector,
    Threshold,
)

_MODULE = "thresholding.thresholds"


def percentile_threshold(errors: ScoreVector, q: Quantile) -> Threshold:
    if errors.size == 0:
        raise ValueError(
            f"[{_MODULE}] Cannot compute percentile. Expected: non-empty array. Got: empty array."
        )
    if q < 0.0 or q > 100.0:
        raise ValueError(
            f"[{_MODULE}] Invalid percentile. Expected: 0 <= q <= 100. Got: {q}."
        )
    return float(np.percentile(errors, q))


def arithmetic_mean_threshold(tau_list: list[Threshold] | ScoreVector) -> Threshold:
    arr = np.asarray(tau_list, dtype=np.float64)
    if arr.size == 0:
        raise ValueError(
            f"[{_MODULE}] Cannot compute mean. Expected: non-empty threshold list. Got: empty list."
        )
    return float(arr.mean())
