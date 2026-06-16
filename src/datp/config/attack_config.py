"""Typed config schema — single source of truth for all scientific parameters.

All scientific values come from here. No module-level constants for these parameters
downstream. No shift_magnitude. No attack_rate. No untyped dicts.

E=1 is enforced by validator; E=5 is explicitly rejected.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from datp.artifacts.poison_names import (
    ANALYSIS_SEEDS,
    B4_K,
    B4_MAX_ITER,
    B4_N_INIT,
    B4_RANDOM_STATE,
    COMPROMISE_PATTERN_SEED,
    N_MIN,
    POISONING_SEEDS,
    TAIL_MASS,
    TRAINING_SEEDS,
)
from datp.attacks.poison_enums import (
    BOUNDED_SWEEP_FRACTIONS,
    AttackerObjective,
    CalibrationInjectionRule,
    ExperimentScale,
    PoisoningDefense,
    PoisoningKnowledge,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)


class SeedPools(BaseModel):
    """Locked seed pools for runs.

    Each pool contains exactly 5 seeds. Index i of training + index i of
    poisoning + index i of analysis define one seed triplet.
    Compromise-pattern seed is fixed at 400.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    training: tuple[int, ...] = TRAINING_SEEDS
    poisoning: tuple[int, ...] = POISONING_SEEDS
    analysis: tuple[int, ...] = ANALYSIS_SEEDS
    split: int = 0
    compromise_pattern: int = COMPROMISE_PATTERN_SEED

    @model_validator(mode="after")
    def pools_same_length(self) -> "SeedPools":
        if len(self.training) != len(self.poisoning):
            raise ValueError(
                "training and poisoning seed pools must have the same length"
            )
        if len(self.training) != len(self.analysis):
            raise ValueError(
                "training and analysis seed pools must have the same length"
            )
        if not self.training:
            raise ValueError("seed pools must not be empty")
        return self

    @model_validator(mode="after")
    def no_seed_overlap(self) -> "SeedPools":
        all_seeds = list(self.training) + list(self.poisoning) + list(self.analysis)
        if len(all_seeds) != len(set(all_seeds)):
            raise ValueError(
                "training, poisoning, and analysis seeds must be pairwise distinct"
            )
        return self

    def triplet(self, index: int) -> tuple[int, int, int]:
        """Return (training_seed, poisoning_seed, analysis_seed) at index."""
        return self.training[index], self.poisoning[index], self.analysis[index]

    def __len__(self) -> int:
        return len(self.training)


class B4ClusterConfig(BaseModel):
    """B4 clustering hyperparameters — locked for N-BaIoT (Regime A).

    Do not change without a scientific ticket.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    k: int = Field(default=B4_K, gt=0)
    n_init: int = Field(default=B4_N_INIT, gt=0)
    max_iter: int = Field(default=B4_MAX_ITER, gt=0)
    random_state: int = B4_RANDOM_STATE

    @field_validator("k")
    @classmethod
    def k_must_be_three_for_regime_a(cls, v: int) -> int:
        if v != 3:
            raise ValueError(
                f"B4 k must be 3 for Regime A (N-BaIoT); got {v}"
            )
        return v


class CalibrationPoisoningConfig(BaseModel):
    """Typed experiment config — covers all scientific parameters.

    Enforces E=1 (rejects E=5), REPLACE_FIXED_BUDGET injection rule,
    victim-local reservoirs, and the locked fraction/seed grids.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Protocol lock: E=1 only; E=5 explicitly rejected.
    local_epochs: int = 1

    # Experiment design
    policy: ThresholdPolicy
    objective: AttackerObjective
    source: PoisoningSourceStrategy
    injection_rule: CalibrationInjectionRule = (
        CalibrationInjectionRule.REPLACE_FIXED_BUDGET
    )
    knowledge: PoisoningKnowledge
    target_scope: PoisoningTargetScope
    defense: PoisoningDefense = PoisoningDefense.NONE
    scale: ExperimentScale

    # Fraction grid: bounded sweep = {0, 0.10, 0.20, 0.40}; Full adds 0.05 (gated).
    fractions: tuple[float, ...] = BOUNDED_SWEEP_FRACTIONS

    # Seed pools
    seeds: SeedPools = SeedPools()

    # Eligibility threshold (clients with n_cal < n_min are calibration-pending)
    n_min: int = Field(default=N_MIN, gt=0)

    # B4 hyperparameters
    b4: B4ClusterConfig = B4ClusterConfig()

    # Reservoir: victim-local benign calibration scores; tail_mass fraction.
    tail_mass: float = Field(default=TAIL_MASS, gt=0.0, le=1.0)

    # CV(FPR) instability flag: mu_flag_threshold = round(M_clean / 8, 2 s.f.).
    # Must be computed from clean baseline artifacts and locked BEFORE any poisoned run.
    mu_flag_threshold: float | None = None

    @field_validator("local_epochs")
    @classmethod
    def enforce_e1(cls, v: int) -> int:
        if v != 1:
            raise ValueError(
                f"local_epochs must be 1 (E=1 protocol lock); "
                f"got {v} — E={v} is forbidden"
            )
        return v

    @field_validator("fractions")
    @classmethod
    def validate_fractions(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        if not v:
            raise ValueError("fractions must not be empty")
        for f in v:
            if not (0.0 <= f <= 1.0):
                raise ValueError(f"fraction {f} is outside [0.0, 1.0]")
        return v

    @field_validator("injection_rule")
    @classmethod
    def only_replace_fixed_budget(
        cls, v: CalibrationInjectionRule
    ) -> CalibrationInjectionRule:
        if v != CalibrationInjectionRule.REPLACE_FIXED_BUDGET:
            raise ValueError(
                f"injection_rule must be REPLACE_FIXED_BUDGET; got {v}"
            )
        return v

    @model_validator(mode="after")
    def bounded_scale_requires_single_client(self) -> "CalibrationPoisoningConfig":
        if (
            self.scale == ExperimentScale.BOUNDED
            and self.target_scope != PoisoningTargetScope.SINGLE_CLIENT
        ):
            raise ValueError(
                "BOUNDED scale requires SINGLE_CLIENT target scope"
            )
        return self

