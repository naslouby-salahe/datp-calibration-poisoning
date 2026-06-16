"""Bounded N-BaIoT MVP cell-matrix enumeration (CP2-T044-locked).

Enumerates exactly the matrix authorized by CP2-T044: ``REGIME_A_NBAIOT``,
default policies (B1/B2/B4, no B3), MVP sources, the locked MVP fraction
grid (no 0.05), ``SINGLE_CLIENT`` scope only, all eligible victims, and the
5 paired (training_seed, poisoning_seed) seeds. Nothing outside this matrix
is reachable from here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from datp.artifacts.poison_names import CP2_POISONING_SEEDS, CP2_TRAINING_SEEDS
from datp.attacks.poison_enums import (
    CP2_DEFAULT_POLICIES,
    CP2_MVP_FRACTIONS,
    CP2_MVP_SOURCES,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)


@dataclass(frozen=True, slots=True)
class Cp2MvpCellSpec:
    """One bounded-MVP cell.

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


def enumerate_mvp_matrix(
    victims_by_training_seed: Mapping[int, Sequence[str]],
) -> tuple[Cp2MvpCellSpec, ...]:
    """Enumerate the locked bounded-MVP matrix.

    ``victims_by_training_seed`` maps each training seed to its eligible
    victim ids for that seed's collection (training and poisoning seeds are
    paired 1:1 by position in ``CP2_TRAINING_SEEDS``/``CP2_POISONING_SEEDS``).
    Raises ``KeyError`` if a locked training seed has no victim list.
    """
    cells: list[Cp2MvpCellSpec] = []
    for training_seed, poisoning_seed in zip(
        CP2_TRAINING_SEEDS, CP2_POISONING_SEEDS, strict=True
    ):
        victims = victims_by_training_seed.get(training_seed)
        if victims is None:
            raise KeyError(
                f"no victim list provided for training_seed={training_seed}"
            )
        for victim_id in victims:
            for policy in CP2_DEFAULT_POLICIES:
                for source in CP2_MVP_SOURCES:
                    for fraction in CP2_MVP_FRACTIONS:
                        cells.append(
                            Cp2MvpCellSpec(
                                training_seed=training_seed,
                                poisoning_seed=poisoning_seed,
                                victim_id=victim_id,
                                policy=policy,
                                source=source,
                                fraction=fraction,
                            )
                        )
    return tuple(cells)
