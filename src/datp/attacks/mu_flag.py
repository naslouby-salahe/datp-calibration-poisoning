from __future__ import annotations

import math


def compute_mu_flag_threshold(mean_clean_fpr: float) -> float:
    raw = mean_clean_fpr / 8.0
    if math.isclose(raw, 0.0, abs_tol=0.0):
        return 0.0
    magnitude = math.floor(math.log10(abs(raw)))
    factor = 10 ** (1 - magnitude)
    return round(raw * factor) / factor
