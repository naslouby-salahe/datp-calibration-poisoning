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


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> CliffsDeltaResult:
    """Cliff's delta: (count(x>y) - count(x<y)) / (n_x * n_y).

    Vectorized via broadcasting for efficiency and lower cyclomatic
    complexity.  Magnitude thresholds follow Romano et al. (2006), Table 1.
    """
    x = np.asarray(x, dtype=np.float64).ravel()
    y = np.asarray(y, dtype=np.float64).ravel()
    if x.size == 0 or y.size == 0:
        raise ValueError("cliffs_delta: arrays must be non-empty")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("cliffs_delta: arrays must contain only finite values")

    n_x = x.size
    n_y = y.size

    # Broadcasting: x[:, None] > y[None, :] yields an (n_x, n_y) bool matrix.
    more = int(np.sum(x[:, None] > y[None, :]))
    less = int(np.sum(x[:, None] < y[None, :]))

    delta = (more - less) / (n_x * n_y)

    abs_d = abs(delta)
    if abs_d < CLIFFS_DELTA_NEGLIGIBLE:
        magnitude = EffectMagnitude.NEGLIGIBLE
    elif abs_d < CLIFFS_DELTA_SMALL:
        magnitude = EffectMagnitude.SMALL
    elif abs_d < CLIFFS_DELTA_MEDIUM:
        magnitude = EffectMagnitude.MEDIUM
    else:
        magnitude = EffectMagnitude.LARGE

    return CliffsDeltaResult(delta=float(delta), magnitude=magnitude)
