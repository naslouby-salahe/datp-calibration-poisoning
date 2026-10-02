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
from scipy.stats import spearmanr as _scipy_spearmanr

from datp.reporting.enums import MechanismWording


@dataclass(frozen=True, slots=True)
class SpearmanResult:

    rho: ScoreValue
    p_value: Probability
    mechanism_wording: MechanismWording
    n: SampleCount


def spearman_correlation(
    divergences: ScoreVector,
    fpr_values: ScoreVector,
    significance_alpha: SignificanceLevel,
) -> SpearmanResult:
    divergences_arr = np.asarray(divergences, dtype=np.float64)
    fpr_arr = np.asarray(fpr_values, dtype=np.float64)
    statistic, raw_p_value = _scipy_spearmanr(divergences_arr, fpr_arr)
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
