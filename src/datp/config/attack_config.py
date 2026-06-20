"""Typed config schema — single source of truth for all scientific parameters.

All scientific values come from here. No module-level constants for these parameters
downstream. No shift_magnitude. No attack_rate. No untyped dicts.

E=1 is enforced by validator; E=5 is explicitly rejected.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from datp.artifacts.poison_names import (
    B4_K,
    B4_MAX_ITER,
    B4_N_INIT,
    N_MIN,
    TAIL_MASS,
    TRIM_FRACTION_PRIMARY,
)
from datp.attacks.constants import (
    ANALYSIS_SEEDS,
    B4_RANDOM_STATE,
    BOUNDED_SWEEP_FRACTION_SET,
    BOUNDED_SWEEP_FRACTIONS,
    BOUNDED_SWEEP_SOURCES,
    COMPROMISE_PATTERN_SEED,
    DEFAULT_POLICIES,
    POISONING_SEEDS,
    TRAINING_SEEDS,
)
from datp.attacks.enums import (
    CalibrationInjectionRule,
    PoisoningDefense,
    PoisoningKnowledge,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)
from datp.experiments.enums import ExperimentScale

_DEFAULT_POLICY_SET: frozenset[ThresholdPolicy] = frozenset(DEFAULT_POLICIES)
_BOUNDED_SOURCE_SET: frozenset[PoisoningSourceStrategy] = frozenset(BOUNDED_SWEEP_SOURCES)


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

    Locked per scientific protocol.
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
            raise ValueError(f"B4 k must be 3 for Regime A (N-BaIoT); got {v}")
        return v

    @field_validator("random_state")
    @classmethod
    def random_state_must_be_42(cls, v: int) -> int:
        if v != 42:
            raise ValueError(f"B4 random_state must be 42 for Regime A; got {v}")
        return v


class CalibrationPoisoningConfig(BaseModel):
    """Typed sweep config — single source of truth for all scientific parameters.

    Covers all sweep dimensions: policies, sources, fractions, and seeds.
    Enforces E=1, REPLACE_FIXED_BUDGET injection rule, victim-local reservoirs,
    and the locked fraction/seed/policy/source grids for each scale.

    Objectives (THRESHOLD_RAISE, THRESHOLD_LOWER) are encoded through source
    strategy semantics: HIGH_SCORE_BENIGN → THRESHOLD_RAISE,
    LOW_SCORE_BENIGN → THRESHOLD_LOWER, RANDOM_BENIGN → None.
    They are not a separate enumeration dimension.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Protocol lock: E=1 only; E=5 explicitly rejected.
    local_epochs: int = 1

    # Sweep dimensions — runner reads these fields, not module-level constants.
    policies: tuple[ThresholdPolicy, ...] = DEFAULT_POLICIES
    sources: tuple[PoisoningSourceStrategy, ...] = BOUNDED_SWEEP_SOURCES

    injection_rule: CalibrationInjectionRule = (
        CalibrationInjectionRule.REPLACE_FIXED_BUDGET
    )
    knowledge: PoisoningKnowledge
    target_scope: PoisoningTargetScope
    defense: PoisoningDefense = PoisoningDefense.NONE
    # Trimmed-calibration symmetric trim fraction; used only when
    # defense == TRIMMED_CALIBRATION. Primary t=5%; t=10% is appendix-only.
    trim_fraction: float = Field(default=TRIM_FRACTION_PRIMARY, ge=0.0, lt=0.5)
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

    @field_validator("policies")
    @classmethod
    def policies_must_not_be_empty(
        cls, v: tuple[ThresholdPolicy, ...]
    ) -> tuple[ThresholdPolicy, ...]:
        if not v:
            raise ValueError("policies must not be empty")
        return v

    @field_validator("sources")
    @classmethod
    def sources_must_not_be_empty(
        cls, v: tuple[PoisoningSourceStrategy, ...]
    ) -> tuple[PoisoningSourceStrategy, ...]:
        if not v:
            raise ValueError("sources must not be empty")
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

    @model_validator(mode="after")
    def bounded_scale_requires_single_client(self) -> "CalibrationPoisoningConfig":
        if (
            self.scale == ExperimentScale.BOUNDED
            and self.target_scope != PoisoningTargetScope.SINGLE_CLIENT
        ):
            raise ValueError("BOUNDED scale requires SINGLE_CLIENT target scope")
        return self

    @model_validator(mode="after")
    def bounded_scale_requires_all_default_policies(
        self,
    ) -> "CalibrationPoisoningConfig":
        if self.scale == ExperimentScale.BOUNDED:
            if frozenset(self.policies) != _DEFAULT_POLICY_SET:
                raise ValueError(
                    f"BOUNDED scale requires exactly policies {_DEFAULT_POLICY_SET}; "
                    f"got {set(self.policies)}"
                )
        return self

    @model_validator(mode="after")
    def bounded_scale_requires_bounded_sources(self) -> "CalibrationPoisoningConfig":
        if self.scale == ExperimentScale.BOUNDED:
            if frozenset(self.sources) != _BOUNDED_SOURCE_SET:
                raise ValueError(
                    f"BOUNDED scale requires exactly sources {_BOUNDED_SOURCE_SET}; "
                    f"got {set(self.sources)}"
                )
        return self

    @model_validator(mode="after")
    def bounded_scale_requires_locked_fractions(self) -> "CalibrationPoisoningConfig":
        if self.scale == ExperimentScale.BOUNDED:
            if frozenset(self.fractions) != BOUNDED_SWEEP_FRACTION_SET:
                raise ValueError(
                    f"BOUNDED scale requires exactly fractions {sorted(BOUNDED_SWEEP_FRACTION_SET)}; "
                    f"got {sorted(self.fractions)}"
                )
        return self

    @classmethod
    def for_bounded_mvp(cls) -> "CalibrationPoisoningConfig":
        """Canonical bounded sweep config — enforces all locked grid parameters."""
        return cls(
            policies=DEFAULT_POLICIES,
            sources=BOUNDED_SWEEP_SOURCES,
            knowledge=PoisoningKnowledge.GRAY_BOX_SCORE_ACCESS,
            target_scope=PoisoningTargetScope.SINGLE_CLIENT,
            scale=ExperimentScale.BOUNDED,
            fractions=BOUNDED_SWEEP_FRACTIONS,
            seeds=SeedPools(),
        )
