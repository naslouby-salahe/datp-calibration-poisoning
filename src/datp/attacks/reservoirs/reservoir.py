"""Reservoir construction: pool extraction from victim calibration scores by strategy."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp.attacks.enums import PoisoningSourceStrategy, ReservoirStatus


@dataclass(frozen=True, slots=True)
class ReservoirResult:
    """Pool of values extracted from a victim's calibration scores for poisoning."""

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
    """Extract a poisoning-value pool from victim calibration scores by strategy."""
    if source == PoisoningSourceStrategy.RANDOM_BENIGN:
        pool = clean_cal.copy()
    else:
        n_tail = max(1, int(tail_mass * clean_cal.size))
        sorted_cal = np.sort(clean_cal)

        if source == PoisoningSourceStrategy.HIGH_SCORE_BENIGN:
            pool = sorted_cal[-n_tail:].copy()
        elif source in {
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
            PoisoningSourceStrategy.LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY,
        }:
            pool = sorted_cal[:n_tail].copy()
        else:
            raise ValueError(f"Unsupported source strategy: {source}")

    n_distinct = len(np.unique(pool))
    status = (
        ReservoirStatus.FEASIBLE
        if source == PoisoningSourceStrategy.RANDOM_BENIGN or n_distinct >= 2
        else ReservoirStatus.INFEASIBLE_DEGENERATE_TAIL
    )

    return ReservoirResult(
        pool=pool,
        status=status,
        source=source,
        n_pool=pool.size,
        n_distinct=n_distinct,
    )
