"""Wilcoxon signed-rank test and Bonferroni correction for paired comparisons."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
from scipy.stats import wilcoxon as _scipy_wilcoxon


@dataclass(frozen=True, slots=True)
class WilcoxonResult:
    """Result of a Wilcoxon signed-rank test: statistic, p-value, and sample size."""

    statistic: float
    p_value: float
    n: int


@dataclass(frozen=True, slots=True)
class BonferroniResult:
    """Bonferroni correction result: corrected alpha, per-comparison significance, and original p-values."""

    corrected_alpha: float
    significant: tuple[bool, ...]
    original_p_values: tuple[float, ...]


def wilcoxon_test(x: np.ndarray, y: np.ndarray) -> WilcoxonResult:
    """Run a two-sided Wilcoxon signed-rank test on paired arrays x and y."""
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

    statistic, p_value = cast(tuple[float, float], _scipy_wilcoxon(x_arr, y_arr))
    return WilcoxonResult(
        statistic=float(statistic),
        p_value=float(p_value),
        n=len(x_arr),
    )


def bonferroni_correct(p_values: list[float], alpha: float) -> BonferroniResult:
    """Apply Bonferroni correction to a list of p-values given a family-wise alpha."""
    if not p_values:
        raise ValueError("bonferroni_correct: p_values must be non-empty")
    corrected_alpha = alpha / len(p_values)
    return BonferroniResult(
        corrected_alpha=corrected_alpha,
        significant=tuple(p < corrected_alpha for p in p_values),
        original_p_values=tuple(p_values),
    )
