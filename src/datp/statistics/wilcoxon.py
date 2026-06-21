"""Wilcoxon signed-rank test utilities; secondary for N-BaIoT main (n=9 limit), with Bonferroni correction across α levels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import wilcoxon as _scipy_wilcoxon


@dataclass(frozen=True, slots=True)
class WilcoxonResult:
    statistic: float
    p_value: float
    n: int


@dataclass(frozen=True, slots=True)
class BonferroniResult:
    corrected_alpha: float
    significant: tuple[bool, ...]
    original_p_values: tuple[float, ...]


def wilcoxon_test(
    x: np.ndarray,
    y: np.ndarray,
) -> WilcoxonResult:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.size == 0 or y.size == 0:
        raise ValueError("wilcoxon_test: arrays must be non-empty")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("wilcoxon_test: arrays must contain only finite values")
    diff = x - y
    if np.all(diff == 0):
        return WilcoxonResult(statistic=0.0, p_value=1.0, n=len(x))
    result: Any = _scipy_wilcoxon(x, y)
    return WilcoxonResult(
        statistic=float(result.statistic), p_value=float(result.pvalue), n=len(x)
    )


def bonferroni_correct(
    p_values: list[float],
    alpha: float,
) -> BonferroniResult:
    m = len(p_values)
    corrected_alpha = alpha / m
    return BonferroniResult(
        corrected_alpha=corrected_alpha,
        significant=tuple(p < corrected_alpha for p in p_values),
        original_p_values=tuple(p_values),
    )
