"""Victim-local reservoir selection for CP2 calibration poisoning.

Reservoirs are built exclusively from the victim's own clean calibration scores.
Test scores are NEVER a reservoir. Training scores are NOT a reservoir.
No cross-client reservoirs in the main matrix.

Source strategies:
  RANDOM_BENIGN: full pool (resample with replacement from all cal scores).
  HIGH_SCORE_BENIGN: upper tail_mass fraction of sorted cal scores.
  LOW_SCORE_BENIGN: lower tail_mass fraction of sorted cal scores.

Degenerate tails (< 2 distinct values) are flagged INFEASIBLE → FB2 path.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

import numpy as np

from datp.attacks.poison_enums import PoisoningSourceStrategy


class ReservoirStatus(enum.StrEnum):
    FEASIBLE = "feasible"
    INFEASIBLE_DEGENERATE_TAIL = "infeasible_degenerate_tail"


@dataclass(frozen=True, slots=True)
class ReservoirResult:
    """Result of reservoir construction for one victim client."""

    pool: np.ndarray
    status: ReservoirStatus
    source: PoisoningSourceStrategy
    n_pool: int
    n_distinct: int


def build_reservoir(
    *,
    clean_cal: np.ndarray,
    source: PoisoningSourceStrategy,
    tail_mass: float,
) -> ReservoirResult:
    """Build a victim-local reservoir from clean calibration scores.

    Never mutates clean_cal. Returns a ReservoirResult with the pool and
    feasibility status.

    For RANDOM_BENIGN, the entire calibration array is the pool.
    For HIGH_SCORE_BENIGN, the upper tail_mass fraction.
    For LOW_SCORE_BENIGN, the lower tail_mass fraction.

    Degenerate: if the tail has < 2 distinct values, status is INFEASIBLE.
    """
    if source == PoisoningSourceStrategy.RANDOM_BENIGN:
        pool = clean_cal.copy()
        n_distinct = len(np.unique(pool))
        return ReservoirResult(
            pool=pool,
            status=ReservoirStatus.FEASIBLE,
            source=source,
            n_pool=pool.shape[0],
            n_distinct=n_distinct,
        )

    sorted_cal = np.sort(clean_cal)
    n = sorted_cal.shape[0]
    n_tail = max(1, int(tail_mass * n))

    if source == PoisoningSourceStrategy.HIGH_SCORE_BENIGN:
        pool = sorted_cal[-n_tail:].copy()
    elif source in (
        PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        PoisoningSourceStrategy.LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY,
    ):
        pool = sorted_cal[:n_tail].copy()
    else:
        raise ValueError(f"Unsupported source strategy for reservoir: {source}")

    n_distinct = len(np.unique(pool))
    status = (
        ReservoirStatus.FEASIBLE
        if n_distinct >= 2
        else ReservoirStatus.INFEASIBLE_DEGENERATE_TAIL
    )

    return ReservoirResult(
        pool=pool,
        status=status,
        source=source,
        n_pool=pool.shape[0],
        n_distinct=n_distinct,
    )
