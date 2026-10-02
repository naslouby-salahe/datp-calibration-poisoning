
from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, cast

from pydantic import Field, field_validator, model_validator

from datp.attacks.constants import (
    ANALYSIS_SEEDS,
    CLUSTER_K_NBAIOT,
    CLUSTER_MAX_ITER,
    CLUSTER_N_INIT,
    CLUSTER_RANDOM_STATE,
    DEFAULT_POLICIES,
    N_MIN,
    NBAIOT_MAIN_SWEEP_FRACTION_SET,
    NBAIOT_MAIN_SWEEP_FRACTIONS,
    NBAIOT_MAIN_SWEEP_OBJECTIVES,
    NBAIOT_MAIN_SWEEP_SOURCES,
    POISONING_SEEDS,
    TAIL_MASS,
    TRAINING_SEEDS,
    TRIM_FRACTION_PRIMARY,
)
from datp.attacks.enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    PoisoningDefense,
    PoisoningKnowledge,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.config.models import ExperimentStage, StrictModel
from datp.core.enums import ThresholdPolicy
from datp.types import (
    IterationCount,
    PoisonFraction,
    RandomSeed,
    SampleCount,
    Threshold,
)

_DEFAULT_POLICY_SET: frozenset[ThresholdPolicy] = frozenset(DEFAULT_POLICIES)
_NBAIOT_MAIN_SOURCE_SET: frozenset[PoisoningSourceStrategy] = frozenset(
    NBAIOT_MAIN_SWEEP_SOURCES
)


class SeedPools(StrictModel):

    training: tuple[RandomSeed, ...] = TRAINING_SEEDS
    poisoning: tuple[RandomSeed, ...] = POISONING_SEEDS
    analysis: tuple[RandomSeed, ...] = ANALYSIS_SEEDS
    split: RandomSeed = RandomSeed(0)
    @model_validator(mode="after")
    def validate_pools(self) -> "SeedPools":
        if not self.training:
            raise ValueError("seed pools must not be empty")
        if len({len(self.training), len(self.poisoning), len(self.analysis)}) > 1:
            raise ValueError("all seed pools must have the same length")
        all_seeds = list(self.training) + list(self.poisoning) + list(self.analysis)
        if len(all_seeds) != len(set(all_seeds)):
            raise ValueError("all seeds must be pairwise distinct")
        return self

    def __len__(self) -> int:
        return len(self.training)


class ClusterConfig(StrictModel):

    k: Literal[3] = cast(Literal[3], CLUSTER_K_NBAIOT)
    n_init: IterationCount = Field(default=CLUSTER_N_INIT, gt=0)
    max_iter: IterationCount = Field(default=CLUSTER_MAX_ITER, gt=0)
    random_state: Literal[42] = cast(Literal[42], CLUSTER_RANDOM_STATE)


class CalibrationPoisoningConfig(StrictModel):

    local_epochs: Literal[1] = 1

    policies: tuple[ThresholdPolicy, ...] = DEFAULT_POLICIES
    sources: tuple[PoisoningSourceStrategy, ...] = NBAIOT_MAIN_SWEEP_SOURCES
    objectives: tuple[AttackerObjective, ...] = NBAIOT_MAIN_SWEEP_OBJECTIVES

    injection_rule: Literal[CalibrationInjectionRule.REPLACE_FIXED_BUDGET] = (
        CalibrationInjectionRule.REPLACE_FIXED_BUDGET
    )
    knowledge: PoisoningKnowledge
    target_scope: PoisoningTargetScope
    defense: PoisoningDefense = PoisoningDefense.NONE
    trim_fraction: PoisonFraction = Field(default=TRIM_FRACTION_PRIMARY, ge=0.0, lt=0.5)
    stage: ExperimentStage

    fractions: tuple[PoisonFraction, ...] = NBAIOT_MAIN_SWEEP_FRACTIONS
    seeds: SeedPools = SeedPools()
    n_min: SampleCount = Field(default=N_MIN, gt=0)
    cluster: ClusterConfig = ClusterConfig()
    tail_mass: PoisonFraction = Field(default=TAIL_MASS, gt=0.0, le=1.0)
    mu_flag_threshold: Threshold | None = None

    @field_validator("policies")
    @classmethod
    def require_policies(cls, v: tuple[ThresholdPolicy, ...]) -> tuple[ThresholdPolicy, ...]:
        if not v:
            raise ValueError("Policies must not be empty")
        return v

    @field_validator("sources")
    @classmethod
    def require_sources(
        cls, v: tuple[PoisoningSourceStrategy, ...]
    ) -> tuple[PoisoningSourceStrategy, ...]:
        if not v:
            raise ValueError("Sources must not be empty")
        return v

    @field_validator("objectives")
    @classmethod
    def require_objectives(cls, v: tuple[AttackerObjective, ...]) -> tuple[AttackerObjective, ...]:
        if not v:
            raise ValueError("Objectives must not be empty")
        return v

    @field_validator("fractions", mode="before")
    @classmethod
    def validate_fractions(cls, v: object) -> object:
        if isinstance(v, (str, bytes)) or not isinstance(v, Sequence):
            return v
        fractions = cast(Sequence[object], v)
        if any(
            isinstance(item, (int, float)) and not (0.0 <= item <= 1.0)
            for item in fractions
        ):
            raise ValueError("Fractions must be within [0.0, 1.0]")
        return fractions

    @field_validator("fractions")
    @classmethod
    def require_fractions(cls, v: tuple[PoisonFraction, ...]) -> tuple[PoisonFraction, ...]:
        if not v:
            raise ValueError("Fractions must not be empty")
        return v

    @model_validator(mode="after")
    def nbaiot_main_grid_lock(self) -> "CalibrationPoisoningConfig":
        if self.stage != ExperimentStage.NBAIOT_MAIN:
            return self
        if self.target_scope != PoisoningTargetScope.SINGLE_CLIENT:
            raise ValueError("NBAIOT_MAIN stage requires SINGLE_CLIENT target scope")
        if frozenset(self.policies) != _DEFAULT_POLICY_SET:
            raise ValueError(f"Required exactly policies {_DEFAULT_POLICY_SET}")
        if frozenset(self.sources) != _NBAIOT_MAIN_SOURCE_SET:
            raise ValueError(f"Required exactly sources {_NBAIOT_MAIN_SOURCE_SET}")
        if frozenset(self.objectives) != frozenset(NBAIOT_MAIN_SWEEP_OBJECTIVES):
            raise ValueError(
                f"Required exactly objectives {set(NBAIOT_MAIN_SWEEP_OBJECTIVES)}"
            )
        if frozenset(self.fractions) != NBAIOT_MAIN_SWEEP_FRACTION_SET:
            raise ValueError(
                f"Required exactly fractions {sorted(NBAIOT_MAIN_SWEEP_FRACTION_SET)}"
            )
        return self

    @classmethod
    def for_bounded_sweep(cls) -> "CalibrationPoisoningConfig":
        return cls(
            knowledge=PoisoningKnowledge.GRAY_BOX_SCORE_ACCESS,
            target_scope=PoisoningTargetScope.SINGLE_CLIENT,
            stage=ExperimentStage.NBAIOT_MAIN,
        )
