from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp.statistics.constants import (
    CLIFFS_DELTA_MEDIUM,
    CLIFFS_DELTA_NEGLIGIBLE,
    CLIFFS_DELTA_SMALL,
)
from datp.statistics.enums import EffectMagnitude


@dataclass(frozen=True, slots=True)
class CliffsDeltaResult:
    delta: float
    magnitude: EffectMagnitude


def _cliffs_magnitude(abs_d: float) -> EffectMagnitude:
    if abs_d < CLIFFS_DELTA_NEGLIGIBLE:
        return EffectMagnitude.NEGLIGIBLE
    if abs_d < CLIFFS_DELTA_SMALL:
        return EffectMagnitude.SMALL
    if abs_d < CLIFFS_DELTA_MEDIUM:
        return EffectMagnitude.MEDIUM
    return EffectMagnitude.LARGE


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> CliffsDeltaResult:
    """Cliff's delta: (count(x>y) - count(x<y)) / (n_x * n_y)."""
    x = np.asarray(x, dtype=np.float64).ravel()
    y = np.asarray(y, dtype=np.float64).ravel()
    if x.size == 0 or y.size == 0:
        raise ValueError("cliffs_delta: arrays must be non-empty")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("cliffs_delta: arrays must contain only finite values")

    more = int(np.sum(x[:, None] > y[None, :]))
    less = int(np.sum(x[:, None] < y[None, :]))
    delta = (more - less) / (x.size * y.size)

    return CliffsDeltaResult(
        delta=float(delta), magnitude=_cliffs_magnitude(abs(delta))
    )
