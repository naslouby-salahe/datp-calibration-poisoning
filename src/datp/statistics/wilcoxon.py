from __future__ import annotations

from datp.types import (
    Probability,
    SampleCount,
    ScoreValue,
    ScoreVector,
    SignificanceLevel,
)


from dataclasses import dataclass
import numpy as np
from scipy.stats import wilcoxon as _scipy_wilcoxon


@dataclass(frozen=True, slots=True)
class WilcoxonResult:

    statistic: ScoreValue
    p_value: Probability
    n: SampleCount


@dataclass(frozen=True, slots=True)
class BonferroniResult:

    corrected_alpha: SignificanceLevel
    significant: tuple[bool, ...]
    original_p_values: tuple[Probability, ...]


def wilcoxon_test(x: ScoreVector, y: ScoreVector) -> WilcoxonResult:
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    if x_arr.size == 0 or y_arr.size == 0:
        raise ValueError("wilcoxon_test: arrays must be non-empty")
    if x_arr.shape != y_arr.shape:
        raise ValueError("wilcoxon_test: arrays must have the same shape")
    if not np.isfinite(x_arr).all() or not np.isfinite(y_arr).all():
        raise ValueError("wilcoxon_test: arrays must contain only finite values")

    if np.all(x_arr - y_arr == 0):
        return WilcoxonResult(statistic=0.0, p_value=1.0, n=len(x_arr))

    statistic, p_value = _scipy_wilcoxon(x_arr, y_arr)
    return WilcoxonResult(
        statistic=float(statistic),
        p_value=float(p_value),
        n=len(x_arr),
    )


def bonferroni_correct(
    p_values: list[Probability], alpha: SignificanceLevel
) -> BonferroniResult:
    if not p_values:
        raise ValueError("bonferroni_correct: p_values must be non-empty")
    corrected_alpha = alpha / len(p_values)
    return BonferroniResult(
        corrected_alpha=corrected_alpha,
        significant=tuple(p < corrected_alpha for p in p_values),
        original_p_values=tuple(p_values),
    )
