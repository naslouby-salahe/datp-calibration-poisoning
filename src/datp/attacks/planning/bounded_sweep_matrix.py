from __future__ import annotations

from datp.types import (
    ClientId,
    PoisonFraction,
    RandomSeed,
)


from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import product

from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.attacks.planning.guardrails import assert_valid_source_objective_pair
from datp.config.attack_config import CalibrationPoisoningConfig
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.seeds import SeedPair


@dataclass(frozen=True, slots=True)
class SweepCellSpec:

    seed_pair: SeedPair
    victim_id: ClientId
    policy: ThresholdPolicy
    objective: AttackerObjective
    source: PoisoningSourceStrategy
    fraction: PoisonFraction
    target_scope: PoisoningTargetScope = PoisoningTargetScope.SINGLE_CLIENT

    @property
    def training_seed(self) -> RandomSeed:
        return self.seed_pair.training_seed

    @property
    def poisoning_seed(self) -> RandomSeed:
        return self.seed_pair.poisoning_seed


def _is_valid_pair(
    source: PoisoningSourceStrategy, objective: AttackerObjective
) -> bool:
    try:
        assert_valid_source_objective_pair(source, objective)
        return True
    except ValueError:
        return False


def _enumerate_single_victim_matrix(
    victims_by_training_seed: Mapping[RandomSeed, Sequence[ClientId]],
    config: CalibrationPoisoningConfig,
) -> tuple[SweepCellSpec, ...]:
    valid_pairs = tuple(
        (source, objective)
        for source in config.sources
        for objective in config.objectives
        if _is_valid_pair(source, objective)
    )
    cells: list[SweepCellSpec] = []
    for t_seed, p_seed in zip(
        config.seeds.training, config.seeds.poisoning, strict=True
    ):
        if (victims := victims_by_training_seed.get(t_seed)) is None:
            raise KeyError(f"no victim list provided for training_seed={t_seed}")

        seed_pair = SeedPair(training_seed=t_seed, poisoning_seed=p_seed)
        cells.extend(_cells_for_seed(victims, seed_pair, config, valid_pairs))

    return tuple(cells)


def _cells_for_seed(
    victims: Sequence[ClientId],
    seed_pair: SeedPair,
    config: CalibrationPoisoningConfig,
    valid_pairs: tuple[tuple[PoisoningSourceStrategy, AttackerObjective], ...],
) -> tuple[SweepCellSpec, ...]:
    return tuple(
        SweepCellSpec(
            seed_pair=seed_pair,
            victim_id=victim,
            policy=policy,
            objective=objective,
            source=source,
            fraction=fraction,
        )
        for victim, policy, (source, objective), fraction in product(
            victims, config.policies, valid_pairs, config.fractions
        )
    )


def enumerate_bounded_sweep_matrix(
    victims_by_training_seed: Mapping[RandomSeed, Sequence[ClientId]],
    config: CalibrationPoisoningConfig,
) -> tuple[SweepCellSpec, ...]:
    if config.stage != ExperimentStage.NBAIOT_MAIN:
        raise ValueError(f"Requires ExperimentStage.NBAIOT_MAIN; got {config.stage}")
    return _enumerate_single_victim_matrix(victims_by_training_seed, config)
