"""Mu-flag threshold computation for CV(FPR) instability gating."""

from __future__ import annotations

from datp.attacks.constants import MU_FLAG_DIVISOR


def compute_mu_flag_threshold(mean_clean_fpr: float) -> float:
    """``mu_flag_threshold = mean_clean_fpr / MU_FLAG_DIVISOR``.

    The locked protocol formula divides by MU_FLAG_DIVISOR exactly. No
    significant-figure rounding is applied: any rounding would silently
    alter the locked CV(FPR) instability gate and could flip a stability
    flag near the boundary.
    """
    return mean_clean_fpr / MU_FLAG_DIVISOR
