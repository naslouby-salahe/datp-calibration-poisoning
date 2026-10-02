from __future__ import annotations

from datp.types import (
    Index,
    SampleCount,
    ScoreValue,
    ScoreVector,
    SignedCount,
)


import math
from dataclasses import dataclass

import numpy as np


def cv(arr: ScoreVector, ddof: SignedCount = 0) -> ScoreValue:
    a = np.asarray(arr, dtype=np.float64)
    if a.size < 2:
        return math.nan
    m = float(a.mean())
    if not m:
        return math.nan
    return float(a.std(ddof=ddof) / m)


def iqr(arr: ScoreVector) -> ScoreValue:
    a = np.asarray(arr, dtype=np.float64)
    if a.size < 2:
        return math.nan
    p25, p75 = np.percentile(a, [25.0, 75.0])
    return float(p75 - p25)


@dataclass(frozen=True, slots=True)
class FprFleetStats:

    cv: ScoreValue
    mean: ScoreValue
    std: ScoreValue
    iqr: ScoreValue
    max_min_gap: ScoreValue
    worst_value: ScoreValue
    worst_index: Index | None
    n: SampleCount


def compute_fpr_fleet_stats(fpr_arr: ScoreVector) -> FprFleetStats:
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
