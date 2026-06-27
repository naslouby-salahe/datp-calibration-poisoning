"""Spearman correlation with mechanism-wording classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
from scipy.stats import spearmanr as _scipy_spearmanr

from datp.reporting.enums import MechanismWording


@dataclass(frozen=True, slots=True)
class SpearmanResult:
    """Spearman correlation result with mechanism-wording classification."""

    rho: float
    p_value: float
    mechanism_wording: MechanismWording
    n: int


def spearman_correlation(
    divergences: np.ndarray,
    fpr_values: np.ndarray,
    significance_alpha: float,
) -> SpearmanResult:
    """Compute Spearman's rho between divergence and FPR arrays."""
    divergences_arr = np.asarray(divergences, dtype=np.float64)
    fpr_arr = np.asarray(fpr_values, dtype=np.float64)
    statistic, raw_p_value = cast(
        tuple[float, float],
        _scipy_spearmanr(divergences_arr, fpr_arr),
    )
    rho = float(statistic)
    p_value = float(raw_p_value)

    wording = (
        MechanismWording.EMPIRICAL
        if rho > 0 and p_value < significance_alpha
        else MechanismWording.HYPOTHESIS
    )

    return SpearmanResult(
        rho=rho,
        p_value=p_value,
        mechanism_wording=wording,
        n=len(divergences_arr),
    )
