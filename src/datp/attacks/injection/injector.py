from __future__ import annotations

from datp.types import (
    PoisonFraction,
    SampleCount,
    ScoreVector,
    SignedCount,
)


from dataclasses import dataclass
from math import floor

import numpy as np

from datp.attacks.enums import PoisoningSourceStrategy, ReservoirDraw, ReservoirStatus
from datp.attacks.reservoirs.reservoir import ReservoirResult, build_reservoir


@dataclass(frozen=True, slots=True)
class InjectionResult:

    poisoned_cal: ScoreVector
    n_replaced: SampleCount
    n_total: SampleCount
    fraction: PoisonFraction
    positions_replaced: ScoreVector


def inject_fixed_budget(
    *,
    clean_cal: ScoreVector,
    reservoir: ReservoirResult,
    fraction: PoisonFraction,
    rng: np.random.Generator,
    draw: ReservoirDraw = ReservoirDraw.WITH_REPLACEMENT,
) -> InjectionResult:
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
    if draw == ReservoirDraw.DISJOINT_RESERVOIR:
        raise ValueError("DISJOINT_RESERVOIR is handled by inject_disjoint_reservoir.")
    positions = rng.choice(n, size=m, replace=False)
    poisoned = clean_cal.copy()
    poisoned[positions] = _draw_values(reservoir.pool, m, rng, draw)

    return InjectionResult(poisoned, m, n, fraction, positions)


def _draw_values(
    pool: ScoreVector, m: SignedCount, rng: np.random.Generator, draw: ReservoirDraw
) -> ScoreVector:
    match draw:
        case ReservoirDraw.WITH_REPLACEMENT:
            return rng.choice(pool, size=m, replace=True)
        case ReservoirDraw.WITHOUT_REPLACEMENT:
            if m > pool.size:
                raise ValueError(
                    f"Cannot draw {m} values without replacement from a pool of {pool.size}."
                )
            return rng.choice(pool, size=m, replace=False)
        case ReservoirDraw.INTERPOLATED_TAIL:
            ordered = np.sort(pool)
            if ordered.size < 2:
                raise ValueError("Interpolation needs a pool of at least 2 values.")
            lower = rng.integers(0, ordered.size - 1, size=m)
            weight = rng.random(m)
            return ordered[lower] + weight * (ordered[lower + 1] - ordered[lower])
        case _:
            raise ValueError(f"Unsupported draw mode: {draw}")


def disjoint_budget(n: SampleCount, requested: SignedCount, tail_mass: PoisonFraction, source: PoisoningSourceStrategy) -> SignedCount:
    for m in range(requested, 0, -1):
        source_size = n - m
        pool = (
            source_size
            if source == PoisoningSourceStrategy.RANDOM_BENIGN
            else max(1, floor(tail_mass * source_size))
        )
        if pool >= m:
            return m
    return 0


def inject_disjoint_reservoir(
    *,
    clean_cal: ScoreVector,
    source: PoisoningSourceStrategy,
    tail_mass: PoisonFraction,
    fraction: PoisonFraction,
    rng: np.random.Generator,
) -> tuple[InjectionResult, ReservoirResult]:
    n = len(clean_cal)
    if fraction <= 0.0:
        return InjectionResult(
            clean_cal.copy(), 0, n, 0.0, np.empty(0, dtype=np.intp)
        ), build_reservoir(clean_cal=clean_cal, source=source, tail_mass=tail_mass)
    m = disjoint_budget(n, max(1, round(fraction * n)), tail_mass, source)
    if m == 0:
        raise ValueError("No feasible disjoint-reservoir budget.")
    positions = rng.choice(n, size=m, replace=False)
    keep = np.ones(n, dtype=bool)
    keep[positions] = False
    reservoir = build_reservoir(
        clean_cal=clean_cal[keep], source=source, tail_mass=tail_mass
    )
    if reservoir.status == ReservoirStatus.INFEASIBLE_DEGENERATE_TAIL:
        raise ValueError(
            f"Cannot inject: disjoint reservoir is INFEASIBLE ({reservoir.n_distinct} distinct values)."
        )
    poisoned = clean_cal.copy()
    poisoned[positions] = rng.choice(reservoir.pool, size=m, replace=False)
    return InjectionResult(poisoned, m, n, m / n, positions), reservoir
