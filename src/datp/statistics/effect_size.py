"""Cliff's delta effect-size computation with magnitude classification."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp.statistics.constants import (
    CLIFFS_DELTA_MEDIUM,
    CLIFFS_DELTA_NEGLIGIBLE,
    CLIFFS_DELTA_SMALL,
    EffectMagnitude,
)


@dataclass(frozen=True, slots=True)
class CliffsDeltaResult:
    """Cliff's delta value with effect-size magnitude classification."""

    delta: float
    magnitude: EffectMagnitude


def _cliffs_magnitude(abs_delta: float) -> EffectMagnitude:
    if abs_delta < CLIFFS_DELTA_NEGLIGIBLE:
        return EffectMagnitude.NEGLIGIBLE
    if abs_delta < CLIFFS_DELTA_SMALL:
        return EffectMagnitude.SMALL
    if abs_delta < CLIFFS_DELTA_MEDIUM:
        return EffectMagnitude.MEDIUM
    return EffectMagnitude.LARGE


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> CliffsDeltaResult:
    """Compute Cliff's delta effect size between two arrays."""
    x_arr = np.asarray(x, dtype=np.float64).ravel()
    y_arr = np.asarray(y, dtype=np.float64).ravel()
    if x_arr.size == 0 or y_arr.size == 0:
        raise ValueError("cliffs_delta: arrays must be non-empty")
    if not np.isfinite(x_arr).all() or not np.isfinite(y_arr).all():
        raise ValueError("cliffs_delta: arrays must contain only finite values")

    more = int(np.sum(x_arr[:, None] > y_arr[None, :]))
    less = int(np.sum(x_arr[:, None] < y_arr[None, :]))
    delta = float((more - less) / (x_arr.size * y_arr.size))

    return CliffsDeltaResult(delta=delta, magnitude=_cliffs_magnitude(abs(delta)))
