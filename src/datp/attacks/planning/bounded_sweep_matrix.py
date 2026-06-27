"""Sweep-matrix enumeration: Cartesian product of victims × policies × sources × fractions."""

from __future__ import annotations

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
    """One cell in the experiment matrix."""

    seed_pair: SeedPair
    victim_id: str
    policy: ThresholdPolicy
    objective: AttackerObjective
    source: PoisoningSourceStrategy
    fraction: float
    target_scope: PoisoningTargetScope = PoisoningTargetScope.SINGLE_CLIENT

    @property
    def training_seed(self) -> int:
        """Training seed from the cell's seed pair."""
        return self.seed_pair.training_seed

    @property
    def poisoning_seed(self) -> int:
        """Poisoning seed from the cell's seed pair."""
        return self.seed_pair.poisoning_seed


def _is_valid_pair(
    source: PoisoningSourceStrategy, objective: AttackerObjective
) -> bool:
    """Check if a source-objective pairing passes the guardrail."""
    try:
        assert_valid_source_objective_pair(source, objective)
        return True
    except ValueError:
        return False


def _enumerate_single_victim_matrix(
    victims_by_training_seed: Mapping[int, Sequence[str]],
    config: CalibrationPoisoningConfig,
) -> tuple[SweepCellSpec, ...]:
    """Enumerate the Cartesian product of victims × policies × valid source-objective pairs × fractions."""
    valid_pairs = {
        (src, obj)
        for src, obj in product(config.sources, config.objectives)
        if _is_valid_pair(src, obj)
    }

    cells = []
    for t_seed, p_seed in zip(
        config.seeds.training, config.seeds.poisoning, strict=True
    ):
        if (victims := victims_by_training_seed.get(t_seed)) is None:
            raise KeyError(f"no victim list provided for training_seed={t_seed}")

        seed_pair = SeedPair(training_seed=t_seed, poisoning_seed=p_seed)

        for victim, policy, src, obj, frac in product(
            victims,
            config.policies,
            config.sources,
            config.objectives,
            config.fractions,
        ):
            if (src, obj) in valid_pairs:
                cells.append(
                    SweepCellSpec(
                        seed_pair=seed_pair,
                        victim_id=victim,
                        policy=policy,
                        objective=obj,
                        source=src,
                        fraction=frac,
                    )
                )

    return tuple(cells)


def enumerate_bounded_sweep_matrix(
    victims_by_training_seed: Mapping[int, Sequence[str]],
    config: CalibrationPoisoningConfig,
) -> tuple[SweepCellSpec, ...]:
    """Enumerate the bounded-sweep matrix for NBAIOT_MAIN stage."""
    if config.stage != ExperimentStage.NBAIOT_MAIN:
        raise ValueError(f"Requires ExperimentStage.NBAIOT_MAIN; got {config.stage}")
    return _enumerate_single_victim_matrix(victims_by_training_seed, config)


def enumerate_full_sweep_matrix(
    victims_by_training_seed: Mapping[int, Sequence[str]],
    config: CalibrationPoisoningConfig,
) -> tuple[SweepCellSpec, ...]:
    """Enumerate the full-sweep matrix for NBAIOT_FULL_OPTIONAL stage."""
    if config.stage != ExperimentStage.NBAIOT_FULL_OPTIONAL:
        raise ValueError(
            f"Requires ExperimentStage.NBAIOT_FULL_OPTIONAL; got {config.stage}"
        )
    return _enumerate_single_victim_matrix(victims_by_training_seed, config)
