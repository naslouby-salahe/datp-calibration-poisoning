"""Fleet-level FPR statistics: CV, IQR, max-min gap, and worst-client identification."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


def cv(arr: np.ndarray, ddof: int = 0) -> float:
    """Compute the coefficient of variation (std/mean), returning NaN when mean is zero."""
    a = np.asarray(arr, dtype=np.float64)
    if a.size < 2:
        return math.nan
    m = float(a.mean())
    if not m:
        return math.nan
    return float(a.std(ddof=ddof) / m)


def iqr(arr: np.ndarray) -> float:
    """Compute the interquartile range (P75 minus P25), returning NaN when array is too small."""
    a = np.asarray(arr, dtype=np.float64)
    if a.size < 2:
        return math.nan
    p25, p75 = np.percentile(a, [25.0, 75.0])
    return float(p75 - p25)


@dataclass(frozen=True, slots=True)
class FprFleetStats:
    """Fleet-level FPR summary: CV, IQR, max-min gap, and worst-client value and index."""

    cv: float
    mean: float
    std: float
    iqr: float
    max_min_gap: float
    worst_value: float
    worst_index: int | None
    n: int


def compute_fpr_fleet_stats(fpr_arr: np.ndarray) -> FprFleetStats:
    """Compute fleet-wide FPR statistics from a per-client FPR array."""
    arr = np.asarray(fpr_arr, dtype=np.float64)
    n = arr.size
    if n == 0:
        return FprFleetStats(
            math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, None, 0
        )

    worst_idx = int(np.argmax(arr))
    return FprFleetStats(
        cv=cv(arr),
        mean=float(arr.mean()),
        std=float(arr.std(ddof=1)) if n >= 2 else math.nan,
        iqr=iqr(arr),
        max_min_gap=float(arr.max() - arr.min()),
        worst_value=float(arr[worst_idx]),
        worst_index=worst_idx,
        n=n,
    )
