"""Fixed-budget calibration-value injection into victim calibration arrays."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp.attacks.enums import ReservoirStatus
from datp.attacks.reservoirs.reservoir import ReservoirResult


@dataclass(frozen=True, slots=True)
class InjectionResult:
    """Result of a fixed-budget calibration injection: poisoned array and replacement metadata."""

    poisoned_cal: np.ndarray
    n_replaced: int
    n_total: int
    fraction: float
    positions_replaced: np.ndarray


def inject_fixed_budget(
    *,
    clean_cal: np.ndarray,
    reservoir: ReservoirResult,
    fraction: float,
    rng: np.random.Generator,
) -> InjectionResult:
    """Replace a random fraction of calibration values with reservoir draws."""
    if not 0.0 <= fraction <= 1.0:
        raise ValueError(f"fraction must be in [0, 1]; got {fraction}")

    n = len(clean_cal)

    if fraction <= 0.0:
        return InjectionResult(clean_cal.copy(), 0, n, 0.0, np.empty(0, dtype=np.intp))

    if reservoir.status == ReservoirStatus.INFEASIBLE_DEGENERATE_TAIL:
        raise ValueError(
            f"Cannot inject: reservoir is INFEASIBLE "
            f"(degenerate tail, {reservoir.n_distinct} distinct values). "
            f"Mark cell INFEASIBLE."
        )

    m = max(1, round(fraction * n))
    positions = rng.choice(n, size=m, replace=False)

    poisoned = clean_cal.copy()
    poisoned[positions] = rng.choice(reservoir.pool, size=m, replace=True)

    return InjectionResult(poisoned, m, n, fraction, positions)
