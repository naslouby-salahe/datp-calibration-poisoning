"""Calibration-poisoning attack sweep configuration with seed pools and grid-lock validation."""

from __future__ import annotations
from typing import Literal

from pydantic import Field, field_validator, model_validator

from datp.attacks.constants import (
    ANALYSIS_SEEDS,
    CLUSTER_K_NBAIOT,
    CLUSTER_MAX_ITER,
    CLUSTER_N_INIT,
    CLUSTER_RANDOM_STATE,
    COMPROMISE_PATTERN_SEED,
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

_DEFAULT_POLICY_SET: frozenset[ThresholdPolicy] = frozenset(DEFAULT_POLICIES)
_NBAIOT_MAIN_SOURCE_SET: frozenset[PoisoningSourceStrategy] = frozenset(
    NBAIOT_MAIN_SWEEP_SOURCES
)


class SeedPools(StrictModel):
    """Pool of training, poisoning, and analysis seeds with pairwise-distinct validation."""

    training: tuple[int, ...] = TRAINING_SEEDS
    poisoning: tuple[int, ...] = POISONING_SEEDS
    analysis: tuple[int, ...] = ANALYSIS_SEEDS
    split: int = 0
    compromise_pattern: int = COMPROMISE_PATTERN_SEED

    @model_validator(mode="after")
    def validate_pools(self) -> "SeedPools":
        """Validate seed pools are non-empty, equal-length, and pairwise distinct."""
        if not self.training:
            raise ValueError("seed pools must not be empty")
        if len({len(self.training), len(self.poisoning), len(self.analysis)}) > 1:
            raise ValueError("all seed pools must have the same length")
        all_seeds = list(self.training) + list(self.poisoning) + list(self.analysis)
        if len(all_seeds) != len(set(all_seeds)):
            raise ValueError("all seeds must be pairwise distinct")
        return self

    def triplet(self, index: int) -> tuple[int, int, int]:
        """Return the (training, poisoning, analysis) seed triplet at an index."""
        return self.training[index], self.poisoning[index], self.analysis[index]

    def __len__(self) -> int:
        """Return the number of seed triplets."""
        return len(self.training)


class ClusterConfig(StrictModel):
    """KMeans clustering hyperparameters for client grouping."""

    k: Literal[3] = CLUSTER_K_NBAIOT  # type: ignore[assignment]
    n_init: int = Field(default=CLUSTER_N_INIT, gt=0)
    max_iter: int = Field(default=CLUSTER_MAX_ITER, gt=0)
    random_state: Literal[42] = CLUSTER_RANDOM_STATE  # type: ignore[assignment]


class CalibrationPoisoningConfig(StrictModel):
    """Configuration for the calibration-poisoning attack sweep."""

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
    trim_fraction: float = Field(default=TRIM_FRACTION_PRIMARY, ge=0.0, lt=0.5)
    stage: ExperimentStage

    fractions: tuple[float, ...] = NBAIOT_MAIN_SWEEP_FRACTIONS
    seeds: SeedPools = SeedPools()
    n_min: int = Field(default=N_MIN, gt=0)
    cluster: ClusterConfig = ClusterConfig()
    tail_mass: float = Field(default=TAIL_MASS, gt=0.0, le=1.0)
    mu_flag_threshold: float | None = None

    @field_validator("policies", "sources", "objectives", "fractions")
    @classmethod
    def require_non_empty(cls, v: tuple) -> tuple:
        """Validate that a collection field is non-empty."""
        if not v:
            raise ValueError("Collection must not be empty")
        return v

    @field_validator("fractions")
    @classmethod
    def validate_fractions(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        """Validate fractions are within [0.0, 1.0]."""
        if any(not (0.0 <= f <= 1.0) for f in v):
            raise ValueError("Fractions must be within [0.0, 1.0]")
        return v

    @model_validator(mode="after")
    def nbaiot_main_grid_lock(self) -> "CalibrationPoisoningConfig":
        """Enforce the fixed grid of policies, sources, objectives, and fractions for NBAIOT_MAIN."""
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
        """Create a config preset for the bounded sweep with gray-box single-client settings."""
        return cls(
            knowledge=PoisoningKnowledge.GRAY_BOX_SCORE_ACCESS,
            target_scope=PoisoningTargetScope.SINGLE_CLIENT,
            stage=ExperimentStage.NBAIOT_MAIN,
        )
