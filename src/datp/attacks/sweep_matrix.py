"""Sweep cell enumerator for calibration-poisoning experiments.

Produces a flat tuple of SweepCellSpec from a Mapping of victim IDs per
training seed and a CalibrationPoisoningConfig. Grid invariants (policies,
sources, fractions, seed pools) are enforced by the config validators, not here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import product

from datp.attacks.enums import (
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.core.enums import ThresholdPolicy
from datp.config.attack_config import CalibrationPoisoningConfig
from datp.core.seeds import SeedPair
from datp.config.stages import ExperimentStage


@dataclass(frozen=True, slots=True)
class SweepCellSpec:
    """One cell in the experiment matrix.

    Identity: (training_seed, poisoning_seed, victim_id, policy, source,
    fraction). ``target_scope`` is always SINGLE_CLIENT for the bounded matrix.
    """

    seed_pair: SeedPair
    victim_id: str
    policy: ThresholdPolicy
    source: PoisoningSourceStrategy
    fraction: float
    target_scope: PoisoningTargetScope = PoisoningTargetScope.SINGLE_CLIENT

    @property
    def training_seed(self) -> int:
        return self.seed_pair.training_seed

    @property
    def poisoning_seed(self) -> int:
        return self.seed_pair.poisoning_seed


def _enumerate_single_victim_matrix(
    victims_by_training_seed: Mapping[int, Sequence[str]],
    config: CalibrationPoisoningConfig,
) -> tuple[SweepCellSpec, ...]:
    """Enumerate the single-victim matrix driven by config.

    ``victims_by_training_seed`` maps each training seed to its eligible
    victim ids for that seed's collection (training and poisoning seeds are
    paired 1:1 by position in ``config.seeds.training``/``config.seeds.poisoning``).
    Raises ``KeyError`` if a locked training seed has no victim list.
    """
    cells: list[SweepCellSpec] = []
    for training_seed, poisoning_seed in zip(
        config.seeds.training, config.seeds.poisoning, strict=True
    ):
        victims = victims_by_training_seed.get(training_seed)
        if victims is None:
            raise KeyError(f"no victim list provided for training_seed={training_seed}")
        seed_pair = SeedPair(training_seed=training_seed, poisoning_seed=poisoning_seed)
        cells.extend(
            SweepCellSpec(
                seed_pair=seed_pair,
                victim_id=victim_id,
                policy=policy,
                source=source,
                fraction=fraction,
            )
            for victim_id, policy, source, fraction in product(
                victims, config.policies, config.sources, config.fractions
            )
        )
    return tuple(cells)


def enumerate_sweep_cells(
    victims_by_training_seed: Mapping[int, Sequence[str]],
    config: CalibrationPoisoningConfig,
) -> tuple[SweepCellSpec, ...]:
    """Enumerate the bounded matrix; config.stage must be NBAIOT_MAIN."""
    if config.stage != ExperimentStage.NBAIOT_MAIN:
        raise ValueError(
            f"enumerate_sweep_cells requires ExperimentStage.NBAIOT_MAIN config; "
            f"got {config.stage}"
        )
    return _enumerate_single_victim_matrix(victims_by_training_seed, config)


def enumerate_full_sweep_matrix(
    victims_by_training_seed: Mapping[int, Sequence[str]],
    config: CalibrationPoisoningConfig,
) -> tuple[SweepCellSpec, ...]:
    """Enumerate the full optional matrix; config.stage must be NBAIOT_FULL_OPTIONAL."""
    if config.stage != ExperimentStage.NBAIOT_FULL_OPTIONAL:
        raise ValueError(
            f"enumerate_full_sweep_matrix requires ExperimentStage.NBAIOT_FULL_OPTIONAL config; "
            f"got {config.stage}"
        )
    return _enumerate_single_victim_matrix(victims_by_training_seed, config)
