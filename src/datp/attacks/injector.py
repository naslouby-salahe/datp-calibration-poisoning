"""Fixed-budget replacement injector (REPLACE_FIXED_BUDGET).

Protocol: for victim i with fraction f > 0:
  m_i = max(1, round(f * n_i)) positions replaced with values
  resampled WITH REPLACEMENT from the victim-local reservoir.
  Cardinality n_i is preserved. f=0 returns an exact copy (zero change).

Never mutates clean arrays in place. No shift_magnitude. No attack_rate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp.attacks.reservoir import ReservoirResult, ReservoirStatus


@dataclass(frozen=True, slots=True)
class InjectionResult:
    """Result of one injection operation on a single victim's calibration array."""

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
    """Replace a fixed budget of positions with reservoir-sampled values.

    Args:
        clean_cal: Victim clean calibration scores. Never mutated.
        reservoir: Victim-local reservoir to sample from.
        fraction: Poisoning fraction ``f`` in ``[0, 1]``.
        rng: Deterministic generator from ``SeedSequence``.

    Returns:
        Injection metadata and the poisoned calibration array.

    Raises:
        ValueError: If ``fraction`` is outside ``[0, 1]`` or the reservoir is
            infeasible.
    """
    if fraction < 0.0 or fraction > 1.0:
        raise ValueError(f"fraction must be in [0, 1]; got {fraction}")

    n = clean_cal.shape[0]
    poisoned = clean_cal.copy()

    if fraction == 0.0:
        return InjectionResult(
            poisoned_cal=poisoned,
            n_replaced=0,
            n_total=n,
            fraction=fraction,
            positions_replaced=np.array([], dtype=np.intp),
        )

    if reservoir.status == ReservoirStatus.INFEASIBLE_DEGENERATE_TAIL:
        raise ValueError(
            f"Cannot inject: reservoir is INFEASIBLE "
            f"(degenerate tail, {reservoir.n_distinct} distinct values). "
            f"Mark cell INFEASIBLE."
        )

    m = max(1, round(fraction * n))
    positions = rng.choice(n, size=m, replace=False)
    replacement_values = rng.choice(reservoir.pool, size=m, replace=True)
    poisoned[positions] = replacement_values

    return InjectionResult(
        poisoned_cal=poisoned,
        n_replaced=m,
        n_total=n,
        fraction=fraction,
        positions_replaced=positions,
    )
