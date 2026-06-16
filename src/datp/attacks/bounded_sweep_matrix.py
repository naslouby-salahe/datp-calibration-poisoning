"""Bounded N-BaIoT cell-matrix enumeration .

Enumerates exactly the authorized matrix: ``REGIME_A_NBAIOT``,
default policies (B1/B2/B4, no B3), bounded sources, the locked bounded fraction
grid (no 0.05), ``SINGLE_CLIENT`` scope only, all eligible victims, and the
5 paired (training_seed, poisoning_seed) seeds. Nothing outside this matrix
is reachable from here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from datp.artifacts.poison_names import POISONING_SEEDS, TRAINING_SEEDS
from datp.attacks.poison_enums import (
    DEFAULT_POLICIES,
    BOUNDED_SWEEP_FRACTIONS,
    BOUNDED_SWEEP_SOURCES,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)


@dataclass(frozen=True, slots=True)
class BoundedSweepCellSpec:
    """One bounded cell.

    Identity: (training_seed, poisoning_seed, victim_id, policy, source,
    fraction). ``target_scope`` is always SINGLE_CLIENT for this matrix.
    """

    training_seed: int
    poisoning_seed: int
    victim_id: str
    policy: ThresholdPolicy
    source: PoisoningSourceStrategy
    fraction: float
    target_scope: PoisoningTargetScope = PoisoningTargetScope.SINGLE_CLIENT


def enumerate_bounded_sweep_matrix(
    victims_by_training_seed: Mapping[int, Sequence[str]],
) -> tuple[BoundedSweepCellSpec, ...]:
    """Enumerate the locked bounded matrix.

    ``victims_by_training_seed`` maps each training seed to its eligible
    victim ids for that seed's collection (training and poisoning seeds are
    paired 1:1 by position in ``TRAINING_SEEDS``/``POISONING_SEEDS``).
    Raises ``KeyError`` if a locked training seed has no victim list.
    """
    cells: list[BoundedSweepCellSpec] = []
    for training_seed, poisoning_seed in zip(
        TRAINING_SEEDS, POISONING_SEEDS, strict=True
    ):
        victims = victims_by_training_seed.get(training_seed)
        if victims is None:
            raise KeyError(
                f"no victim list provided for training_seed={training_seed}"
            )
        for victim_id in victims:
            for policy in DEFAULT_POLICIES:
                for source in BOUNDED_SWEEP_SOURCES:
                    for fraction in BOUNDED_SWEEP_FRACTIONS:
                        cells.append(
                            BoundedSweepCellSpec(
                                training_seed=training_seed,
                                poisoning_seed=poisoning_seed,
                                victim_id=victim_id,
                                policy=policy,
                                source=source,
                                fraction=fraction,
                            )
                        )
    return tuple(cells)
