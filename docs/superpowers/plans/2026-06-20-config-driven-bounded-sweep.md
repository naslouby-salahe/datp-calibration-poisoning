# Config-Driven Bounded Sweep Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `CalibrationPoisoningConfig` as the single execution contract for the CP2 bounded sweep runner, CLI, dry-run, matrix enumeration, and manifest provenance — eliminating every module-level constant as an independent execution path.

**Architecture:** `CalibrationPoisoningConfig` gains sweep-level plural `policies` and `sources` fields (replacing per-cell singular `policy`/`objective`/`source`), a `for_bounded_mvp()` classmethod, and new validators that enforce all scientific locks at construction time. `bounded_sweep_matrix.py` drops its constant imports and reads `config.policies`, `config.sources`, `config.fractions`, and `config.seeds`. `bounded_sweep_run.py` requires a config (no default) and uses it end-to-end. The CLI dry-run shows matrix dimensions derived from the canonical config. A new CI workflow enforces ruff, pyright, and unit/integration checks.

**Tech Stack:** Pydantic v2, Typer, pytest, pyright, ruff, GitHub Actions

---

## Objective-Encoding Finding (read before implementing)

Objectives are **implicitly encoded through source strategy semantics**, not explicitly enumerated as a separate matrix dimension:

| Source | Objective |
|--------|-----------|
| `HIGH_SCORE_BENIGN` | `THRESHOLD_RAISE` |
| `LOW_SCORE_BENIGN` | `THRESHOLD_LOWER` |
| `RANDOM_BENIGN` | `None` (no directional alignment) |

Matrix size is **1620 cells** (`5 seeds × 9 victims × 3 policies × 3 sources × 4 fractions`), not 3240. Both locked objectives (RAISE and LOWER) are covered — via `HIGH_SCORE_BENIGN` and `LOW_SCORE_BENIGN` respectively. `RANDOM_BENIGN` does not encode an objective. This is intentional protocol design. The `BOUNDED_SWEEP_OBJECTIVES` constant in `constants.py` exists for documentation but is not an enumeration dimension and is not imported by the execution modules.

Tests must assert this encoding (not create a separate `objectives` dimension) and the dry-run count must be based on 1620 cells with 9 victims.

---

## File Map

| File | Action | Responsibility after change |
|------|--------|-----------------------------|
| `src/datp/config/attack_config.py` | Modify | Sweep-level config with `policies`/`sources` plural fields, new validators, `for_bounded_mvp()` |
| `src/datp/attacks/bounded_sweep_matrix.py` | Modify | Accept `CalibrationPoisoningConfig`; no constant imports |
| `src/datp/attacks/bounded_sweep_run.py` | Modify | Config required (no default); all matrix params from config |
| `src/datp/app/cli/poison.py` | Modify | `dry-run` shows config matrix; `run-bounded-sweep` unchanged |
| `tests/unit/config/test_attack_config.py` | Modify | Updated to plural fields + new negative/wiring tests |
| `tests/unit/attacks/test_bounded_sweep_matrix.py` | Modify | Pass config to all enumerate calls |
| `tests/integration/attacks/test_bounded_sweep_run.py` | Modify | Pass config; assert manifest fields come from config |
| `tests/unit/app/cli/test_poison_cli.py` | Modify | New dry-run wiring test; new no-fallback test |
| `.github/workflows/ci.yml` | Create | ruff + pyright + CP2 critical unit/integration tests |

**Not changed:** `src/datp/attacks/constants.py` (constants stay; demoted to defaults/reference only), `src/datp/attacks/bounded_sweep_manifest.py`, `src/datp/attacks/bounded_sweep_cell.py`, `src/datp/attacks/run_manifest.py`.

---

## Task 1: Extend `CalibrationPoisoningConfig` with sweep-level fields

**Files:**
- Modify: `src/datp/config/attack_config.py`

### What to change

Remove from `CalibrationPoisoningConfig`:
- `policy: ThresholdPolicy`
- `objective: AttackerObjective`
- `source: PoisoningSourceStrategy`

Add to `CalibrationPoisoningConfig`:
- `policies: tuple[ThresholdPolicy, ...]` — default `DEFAULT_POLICIES`, non-empty
- `sources: tuple[PoisoningSourceStrategy, ...]` — default `BOUNDED_SWEEP_SOURCES`, non-empty

Remove from top-level imports in `attack_config.py`:
- `AttackerObjective` (no longer a field type)

Add to `from datp.attacks.constants import (...)`:
- `BOUNDED_SWEEP_FRACTION_SET` (for bounded fraction validator)
- `DEFAULT_POLICIES` (for `policies` default and `for_bounded_mvp()`)
- `BOUNDED_SWEEP_SOURCES` (for `sources` default and `for_bounded_mvp()`)

Also add to `B4ClusterConfig`:
- `random_state` validator enforcing `== 42`

Add `for_bounded_mvp()` classmethod.

Add model validators:
- `bounded_scale_requires_all_default_policies`: BOUNDED scale → `frozenset(policies) == {B1, B2, B4}`
- `bounded_scale_requires_bounded_sources`: BOUNDED scale → `frozenset(sources) ⊆ _BOUNDED_SOURCE_SET` AND `frozenset(sources) == _BOUNDED_SOURCE_SET`
- `bounded_scale_requires_locked_fractions`: BOUNDED scale → every fraction in `frozenset(fractions) ⊆ BOUNDED_SWEEP_FRACTION_SET`

Update `bounded_scale_requires_single_client` to stay as-is (still valid).

- [ ] **Step 1: Write new failing tests (Task 2 has detailed tests — write them first, run them, confirm they fail, then implement)**

Run first to confirm failures:
```
python -m pytest tests/unit/config/test_attack_config.py -q --tb=short
```

- [ ] **Step 2: Rewrite `attack_config.py`**

Complete replacement of `CalibrationPoisoningConfig` section and `B4ClusterConfig`:

```python
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

    # Sweep dimensions — derived from config, not from module-level constants.
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
    def policies_must_not_be_empty(cls, v: tuple[ThresholdPolicy, ...]) -> tuple[ThresholdPolicy, ...]:
        if not v:
            raise ValueError("policies must not be empty")
        return v

    @field_validator("sources")
    @classmethod
    def sources_must_not_be_empty(cls, v: tuple[PoisoningSourceStrategy, ...]) -> tuple[PoisoningSourceStrategy, ...]:
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

    @field_validator("injection_rule")
    @classmethod
    def only_replace_fixed_budget(
        cls, v: CalibrationInjectionRule
    ) -> CalibrationInjectionRule:
        if v != CalibrationInjectionRule.REPLACE_FIXED_BUDGET:
            raise ValueError(f"injection_rule must be REPLACE_FIXED_BUDGET; got {v}")
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
    def bounded_scale_requires_all_default_policies(self) -> "CalibrationPoisoningConfig":
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
            invalid = frozenset(self.fractions) - BOUNDED_SWEEP_FRACTION_SET
            if invalid:
                raise ValueError(
                    f"BOUNDED scale fractions outside locked grid "
                    f"{sorted(BOUNDED_SWEEP_FRACTION_SET)}: {sorted(invalid)}"
                )
        return self

    @classmethod
    def for_bounded_mvp(cls) -> "CalibrationPoisoningConfig":
        """Canonical bounded MVP config — enforces all locked grid parameters."""
        return cls(
            policies=DEFAULT_POLICIES,
            sources=BOUNDED_SWEEP_SOURCES,
            knowledge=PoisoningKnowledge.GRAY_BOX_SCORE_ACCESS,
            target_scope=PoisoningTargetScope.SINGLE_CLIENT,
            scale=ExperimentScale.BOUNDED,
            fractions=BOUNDED_SWEEP_FRACTIONS,
            seeds=SeedPools(),
        )
```

- [ ] **Step 3: Run tests to verify new config passes and new validators are reachable**

```
python -m pytest tests/unit/config/test_attack_config.py -q --tb=short
```

Expected after Task 2 tests are written: all pass.

---

## Task 2: Update `test_attack_config.py` with new structure and all required tests

**Files:**
- Modify: `tests/unit/config/test_attack_config.py`

- [ ] **Step 1: Replace the full test file**

```python
"""Unit tests for typed config schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from datp.config.attack_config import (
    B4ClusterConfig,
    CalibrationPoisoningConfig,
    SeedPools,
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

# ── SeedPools ──────────────────────────────────────────────────────────


class TestSeedPools:
    def test_default_values(self) -> None:
        pools = SeedPools()
        assert pools.training == (0, 1, 2, 3, 4)
        assert pools.poisoning == (100, 101, 102, 103, 104)
        assert pools.analysis == (300, 301, 302, 303, 304)
        assert pools.compromise_pattern == 400
        assert pools.split == 0

    def test_len_returns_training_length(self) -> None:
        assert len(SeedPools()) == 5

    def test_triplet_returns_correct_index(self) -> None:
        pools = SeedPools()
        assert pools.triplet(0) == (0, 100, 300)
        assert pools.triplet(4) == (4, 104, 304)

    def test_mismatched_pool_lengths_raise(self) -> None:
        with pytest.raises(ValidationError, match="same length"):
            SeedPools(training=(0, 1, 2), poisoning=(100, 101))

    def test_empty_pools_raise(self) -> None:
        with pytest.raises(ValidationError, match="empty"):
            SeedPools(training=(), poisoning=(), analysis=())

    def test_overlapping_seeds_raise(self) -> None:
        with pytest.raises(ValidationError, match="pairwise distinct"):
            SeedPools(
                training=(0, 1, 2, 3, 4),
                poisoning=(0, 101, 102, 103, 104),
                analysis=(300, 301, 302, 303, 304),
            )

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            SeedPools(bogus=99)  # type: ignore[call-arg]

    def test_frozen(self) -> None:
        pools = SeedPools()
        with pytest.raises(ValidationError):
            pools.training = (9,)  # type: ignore[misc]


# ── B4ClusterConfig ───────────────────────────────────────────────────────────


class TestB4ClusterConfig:
    def test_defaults_are_locked_values(self) -> None:
        b4 = B4ClusterConfig()
        assert b4.k == 3
        assert b4.n_init == 10
        assert b4.max_iter == 300
        assert b4.random_state == 42

    def test_k_not_three_raises(self) -> None:
        with pytest.raises(ValidationError, match="k must be 3"):
            B4ClusterConfig(k=4)

    def test_invalid_random_state_raises(self) -> None:
        with pytest.raises(ValidationError, match="random_state must be 42"):
            B4ClusterConfig(random_state=0)

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            B4ClusterConfig(bogus=1)  # type: ignore[call-arg]


# ── CalibrationPoisoningConfig ─────────────────────────────────────────────────────────────


def _valid_config(**overrides: object) -> CalibrationPoisoningConfig:
    defaults: dict[str, object] = {
        "policies": (ThresholdPolicy.B1_GLOBAL, ThresholdPolicy.B2_PERSONALIZED, ThresholdPolicy.B4_CLUSTER),
        "sources": (
            PoisoningSourceStrategy.RANDOM_BENIGN,
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        ),
        "knowledge": PoisoningKnowledge.GRAY_BOX_SCORE_ACCESS,
        "target_scope": PoisoningTargetScope.SINGLE_CLIENT,
        "scale": ExperimentScale.BOUNDED,
    }
    defaults.update(overrides)
    return CalibrationPoisoningConfig(**defaults)  # type: ignore[arg-type]


class TestConfigValid:
    def test_minimal_valid_config(self) -> None:
        cfg = _valid_config()
        assert cfg.local_epochs == 1
        assert cfg.policies == (
            ThresholdPolicy.B1_GLOBAL,
            ThresholdPolicy.B2_PERSONALIZED,
            ThresholdPolicy.B4_CLUSTER,
        )
        assert cfg.injection_rule == CalibrationInjectionRule.REPLACE_FIXED_BUDGET
        assert cfg.defense == PoisoningDefense.NONE
        assert cfg.fractions == pytest.approx((0.0, 0.10, 0.20, 0.40))
        assert cfg.n_min == 100
        assert cfg.mu_flag_threshold is None

    def test_has_no_singular_policy_field(self) -> None:
        cfg = _valid_config()
        assert not hasattr(cfg, "policy"), "singular 'policy' field must not exist"

    def test_has_no_singular_source_field(self) -> None:
        cfg = _valid_config()
        assert not hasattr(cfg, "source"), "singular 'source' field must not exist"

    def test_has_no_singular_objective_field(self) -> None:
        cfg = _valid_config()
        assert not hasattr(cfg, "objective"), "singular 'objective' field must not exist"

    def test_default_seeds_are_locked_pools(self) -> None:
        cfg = _valid_config()
        assert cfg.seeds.training == (0, 1, 2, 3, 4)
        assert cfg.seeds.poisoning == (100, 101, 102, 103, 104)
        assert cfg.seeds.compromise_pattern == 400

    def test_default_b4_locked_values(self) -> None:
        cfg = _valid_config()
        assert cfg.b4.k == 3
        assert cfg.b4.n_init == 10
        assert cfg.b4.max_iter == 300
        assert cfg.b4.random_state == 42

    def test_mu_flag_threshold_can_be_set(self) -> None:
        cfg = _valid_config(mu_flag_threshold=0.025)
        assert cfg.mu_flag_threshold == pytest.approx(0.025)

    def test_frozen(self) -> None:
        cfg = _valid_config()
        with pytest.raises(ValidationError):
            cfg.local_epochs = 2  # type: ignore[misc]


# ── for_bounded_mvp() canonical constructor ────────────────────────────


class TestForBoundedMvp:
    def test_returns_config_instance(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_mvp()
        assert isinstance(cfg, CalibrationPoisoningConfig)

    def test_has_exactly_b1_b2_b4_policies(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_mvp()
        assert set(cfg.policies) == {
            ThresholdPolicy.B1_GLOBAL,
            ThresholdPolicy.B2_PERSONALIZED,
            ThresholdPolicy.B4_CLUSTER,
        }

    def test_has_exactly_three_bounded_sources(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_mvp()
        assert set(cfg.sources) == {
            PoisoningSourceStrategy.RANDOM_BENIGN,
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        }

    def test_fractions_are_locked_bounded_grid(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_mvp()
        assert set(cfg.fractions) == {0.0, 0.10, 0.20, 0.40}
        assert 0.05 not in cfg.fractions

    def test_seed_pools_are_locked(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_mvp()
        assert cfg.seeds.training == (0, 1, 2, 3, 4)
        assert cfg.seeds.poisoning == (100, 101, 102, 103, 104)
        assert cfg.seeds.compromise_pattern == 400

    def test_scale_is_bounded(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_mvp()
        assert cfg.scale == ExperimentScale.BOUNDED

    def test_target_scope_is_single_client(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_mvp()
        assert cfg.target_scope == PoisoningTargetScope.SINGLE_CLIENT

    def test_local_epochs_is_one(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_mvp()
        assert cfg.local_epochs == 1

    def test_injection_rule_is_replace_fixed_budget(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_mvp()
        assert cfg.injection_rule == CalibrationInjectionRule.REPLACE_FIXED_BUDGET

    def test_b4_config_is_locked(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_mvp()
        assert cfg.b4.k == 3
        assert cfg.b4.n_init == 10
        assert cfg.b4.max_iter == 300
        assert cfg.b4.random_state == 42


# ── E=1 enforcement ────────────────────────────────────────────────────


class TestConfigE1Enforcement:
    def test_local_epochs_1_accepted(self) -> None:
        cfg = _valid_config(local_epochs=1)
        assert cfg.local_epochs == 1

    def test_local_epochs_5_rejected(self) -> None:
        with pytest.raises(ValidationError, match="E=5 is forbidden"):
            _valid_config(local_epochs=5)

    def test_local_epochs_2_rejected(self) -> None:
        with pytest.raises(ValidationError, match="E=1 protocol lock"):
            _valid_config(local_epochs=2)

    def test_local_epochs_0_rejected(self) -> None:
        with pytest.raises(ValidationError, match="E=1 protocol lock"):
            _valid_config(local_epochs=0)


# ── Fraction validation ─────────────────────────────────────────────────


class TestConfigFractionValidation:
    def test_bounded_fractions_accepted(self) -> None:
        cfg = _valid_config(fractions=(0.0, 0.10, 0.20, 0.40))
        assert 0.0 in cfg.fractions
        assert 0.40 in cfg.fractions

    def test_fraction_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError, match="outside"):
            _valid_config(fractions=(0.0, 1.1))

    def test_negative_fraction_rejected(self) -> None:
        with pytest.raises(ValidationError, match="outside"):
            _valid_config(fractions=(-0.1, 0.10))

    def test_empty_fractions_rejected(self) -> None:
        with pytest.raises(ValidationError, match="empty"):
            _valid_config(fractions=())

    def test_bounded_scale_rejects_005_fraction(self) -> None:
        with pytest.raises(ValidationError, match="outside locked grid"):
            _valid_config(scale=ExperimentScale.BOUNDED, fractions=(0.0, 0.05, 0.10))


# ── Injection rule ──────────────────────────────────────────────────────


class TestConfigInjectionRule:
    def test_replace_fixed_budget_accepted(self) -> None:
        cfg = _valid_config(
            injection_rule=CalibrationInjectionRule.REPLACE_FIXED_BUDGET
        )
        assert cfg.injection_rule == CalibrationInjectionRule.REPLACE_FIXED_BUDGET


# ── BOUNDED scale constraints ───────────────────────────────────────────


class TestConfigBoundedScaleConstraints:
    def test_bounded_single_client_accepted(self) -> None:
        cfg = _valid_config(
            scale=ExperimentScale.BOUNDED,
            target_scope=PoisoningTargetScope.SINGLE_CLIENT,
        )
        assert cfg.scale == ExperimentScale.BOUNDED

    def test_bounded_multi_client_rejected(self) -> None:
        with pytest.raises(
            ValidationError, match="BOUNDED scale requires SINGLE_CLIENT"
        ):
            _valid_config(
                scale=ExperimentScale.BOUNDED,
                target_scope=PoisoningTargetScope.MULTI_CLIENT,
            )

    def test_bounded_requires_all_three_policies(self) -> None:
        with pytest.raises(ValidationError, match="BOUNDED scale requires exactly policies"):
            _valid_config(
                scale=ExperimentScale.BOUNDED,
                policies=(ThresholdPolicy.B1_GLOBAL, ThresholdPolicy.B2_PERSONALIZED),
                # Missing B4
            )

    def test_bounded_rejects_b1_only_policies(self) -> None:
        with pytest.raises(ValidationError, match="BOUNDED scale requires exactly policies"):
            _valid_config(
                scale=ExperimentScale.BOUNDED,
                policies=(ThresholdPolicy.B1_GLOBAL,),
            )

    def test_bounded_requires_exactly_three_bounded_sources(self) -> None:
        with pytest.raises(ValidationError, match="BOUNDED scale requires exactly sources"):
            _valid_config(
                scale=ExperimentScale.BOUNDED,
                sources=(PoisoningSourceStrategy.RANDOM_BENIGN,),
            )

    def test_full_scale_multi_client_accepted(self) -> None:
        cfg = _valid_config(
            scale=ExperimentScale.FULL,
            target_scope=PoisoningTargetScope.MULTI_CLIENT,
            policies=(ThresholdPolicy.B1_GLOBAL,),
            sources=(PoisoningSourceStrategy.RANDOM_BENIGN,),
        )
        assert cfg.target_scope == PoisoningTargetScope.MULTI_CLIENT

    def test_full_scale_accepts_fraction_005(self) -> None:
        cfg = _valid_config(
            scale=ExperimentScale.FULL,
            target_scope=PoisoningTargetScope.SINGLE_CLIENT,
            policies=(ThresholdPolicy.B1_GLOBAL, ThresholdPolicy.B2_PERSONALIZED, ThresholdPolicy.B4_CLUSTER),
            sources=(
                PoisoningSourceStrategy.RANDOM_BENIGN,
                PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
                PoisoningSourceStrategy.LOW_SCORE_BENIGN,
            ),
            fractions=(0.0, 0.05, 0.10, 0.20, 0.40),
        )
        assert 0.05 in cfg.fractions


# ── B3 excluded ─────────────────────────────────────────────────────────


class TestConfigB3Excluded:
    def test_b3_not_in_threshold_policy(self) -> None:
        for policy in ThresholdPolicy:
            assert "b3" not in policy.value

    def test_only_b1_b2_b4_policies_exist(self) -> None:
        expected = {"b1_global", "b2_personalized", "b4_cluster"}
        actual = {p.value for p in ThresholdPolicy}
        assert actual == expected


# ── Policies/sources validation ─────────────────────────────────────────


class TestPoliciesSourcesValidation:
    def test_empty_policies_rejected(self) -> None:
        with pytest.raises(ValidationError, match="policies must not be empty"):
            _valid_config(
                scale=ExperimentScale.FULL,
                target_scope=PoisoningTargetScope.SINGLE_CLIENT,
                policies=(),
                sources=(PoisoningSourceStrategy.RANDOM_BENIGN,),
            )

    def test_empty_sources_rejected(self) -> None:
        with pytest.raises(ValidationError, match="sources must not be empty"):
            _valid_config(
                scale=ExperimentScale.FULL,
                target_scope=PoisoningTargetScope.SINGLE_CLIENT,
                policies=(ThresholdPolicy.B1_GLOBAL,),
                sources=(),
            )
```

- [ ] **Step 2: Run updated tests**

```
python -m pytest tests/unit/config/test_attack_config.py -q --tb=short
```

Expected: All pass (after Task 1 implementation).

- [ ] **Step 3: Commit**

```bash
git add src/datp/config/attack_config.py tests/unit/config/test_attack_config.py
git commit -m "feat: extend CalibrationPoisoningConfig with sweep-level policies/sources fields and for_bounded_mvp()"
```

---

## Task 3: Wire `CalibrationPoisoningConfig` into `bounded_sweep_matrix.py`

**Files:**
- Modify: `src/datp/attacks/bounded_sweep_matrix.py`

### What to change

- Change `enumerate_bounded_sweep_matrix` and `enumerate_full_sweep_matrix` to accept `config: CalibrationPoisoningConfig` as second parameter.
- Change `_enumerate_single_victim_matrix` to accept `config: CalibrationPoisoningConfig` (instead of `fractions: Sequence[float]`).
- Remove all imports from `datp.attacks.constants`.
- Use `config.seeds.training`, `config.seeds.poisoning`, `config.policies`, `config.sources`, `config.fractions` inside `_enumerate_single_victim_matrix`.

- [ ] **Step 1: Rewrite `bounded_sweep_matrix.py`**

```python
"""N-BaIoT single-victim cell-matrix enumeration.

Enumerates exactly the authorized matrix: ``REGIME_A_NBAIOT``,
default policies (B1/B2/B4, no B3), bounded sources, ``SINGLE_CLIENT`` scope
only, all eligible victims, and the 5 paired (training_seed, poisoning_seed)
seeds. The bounded enumerator uses the locked bounded fraction grid (no 0.05);
the full-scope enumerator uses the full grid (adds 0.05). Nothing outside these
matrices is reachable from here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import product

from datp.attacks.enums import (
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)
from datp.config.attack_config import CalibrationPoisoningConfig
from datp.core.seeds import SeedPair


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
    """Enumerate the single-victim matrix from a validated config.

    ``victims_by_training_seed`` maps each training seed to its eligible
    victim ids for that seed's collection (training and poisoning seeds are
    paired 1:1 by position in config.seeds).
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


def enumerate_bounded_sweep_matrix(
    victims_by_training_seed: Mapping[int, Sequence[str]],
    config: CalibrationPoisoningConfig,
) -> tuple[SweepCellSpec, ...]:
    """Enumerate the locked bounded matrix from a validated config."""
    return _enumerate_single_victim_matrix(victims_by_training_seed, config)


def enumerate_full_sweep_matrix(
    victims_by_training_seed: Mapping[int, Sequence[str]],
    config: CalibrationPoisoningConfig,
) -> tuple[SweepCellSpec, ...]:
    """Enumerate the full-scope matrix from a validated config.

    Execution remains gated behind the full-scope run authorization.
    """
    return _enumerate_single_victim_matrix(victims_by_training_seed, config)
```

- [ ] **Step 2: Run pyright on modified file**

```
pyright src/datp/attacks/bounded_sweep_matrix.py
```

Expected: no errors.

---

## Task 4: Update `test_bounded_sweep_matrix.py`

**Files:**
- Modify: `tests/unit/attacks/test_bounded_sweep_matrix.py`

The tests must pass a `CalibrationPoisoningConfig` to both enumerate functions. Use `for_bounded_mvp()` for bounded tests and a FULL-scale config for full tests.

- [ ] **Step 1: Rewrite the test file**

```python
"""Unit tests for the locked bounded sweep cell-matrix enumerator."""

from __future__ import annotations

import math

import pytest

from datp.attacks.bounded_sweep_matrix import (
    enumerate_bounded_sweep_matrix,
    enumerate_full_sweep_matrix,
)
from datp.attacks.constants import FULL_SWEEP_FRACTIONS
from datp.attacks.enums import (
    PoisoningKnowledge,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)
from datp.config.attack_config import CalibrationPoisoningConfig, SeedPools
from datp.experiments.enums import ExperimentScale

_VICTIMS: tuple[str, ...] = ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8")
_VICTIMS_BY_SEED: dict[int, tuple[str, ...]] = dict.fromkeys((0, 1, 2, 3, 4), _VICTIMS)


def _bounded_config() -> CalibrationPoisoningConfig:
    return CalibrationPoisoningConfig.for_bounded_mvp()


def _full_config() -> CalibrationPoisoningConfig:
    return CalibrationPoisoningConfig(
        policies=(
            ThresholdPolicy.B1_GLOBAL,
            ThresholdPolicy.B2_PERSONALIZED,
            ThresholdPolicy.B4_CLUSTER,
        ),
        sources=(
            PoisoningSourceStrategy.RANDOM_BENIGN,
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        ),
        knowledge=PoisoningKnowledge.GRAY_BOX_SCORE_ACCESS,
        target_scope=PoisoningTargetScope.SINGLE_CLIENT,
        scale=ExperimentScale.FULL,
        fractions=FULL_SWEEP_FRACTIONS,
    )


# ---------------------------------------------------------------------------
# Runner wiring test — proves config is used, not module constants
# ---------------------------------------------------------------------------


def test_enumerator_uses_config_policies_not_constants() -> None:
    """Wiring: enumerator reads policies from config, not module-level DEFAULT_POLICIES."""
    victims_by_seed = dict.fromkeys((0, 1, 2, 3, 4), ("c0",))
    config = CalibrationPoisoningConfig(
        policies=(ThresholdPolicy.B1_GLOBAL,),
        sources=(PoisoningSourceStrategy.RANDOM_BENIGN,),
        fractions=(0.0,),
        knowledge=PoisoningKnowledge.GRAY_BOX_SCORE_ACCESS,
        target_scope=PoisoningTargetScope.SINGLE_CLIENT,
        scale=ExperimentScale.FULL,
    )
    cells = enumerate_bounded_sweep_matrix(victims_by_seed, config)
    # If module-level DEFAULT_POLICIES were used, B2 and B4 cells would appear.
    assert all(c.policy == ThresholdPolicy.B1_GLOBAL for c in cells)
    # 5 seeds × 1 victim × 1 policy × 1 source × 1 fraction = 5
    assert len(cells) == 5


def test_enumerator_uses_config_fractions_not_constants() -> None:
    """Wiring: enumerator reads fractions from config, not module-level BOUNDED_SWEEP_FRACTIONS."""
    victims_by_seed = dict.fromkeys((0, 1, 2, 3, 4), ("c0",))
    config = CalibrationPoisoningConfig(
        policies=(ThresholdPolicy.B1_GLOBAL,),
        sources=(PoisoningSourceStrategy.RANDOM_BENIGN,),
        fractions=(0.10,),  # single non-standard fraction
        knowledge=PoisoningKnowledge.GRAY_BOX_SCORE_ACCESS,
        target_scope=PoisoningTargetScope.SINGLE_CLIENT,
        scale=ExperimentScale.FULL,
    )
    cells = enumerate_bounded_sweep_matrix(victims_by_seed, config)
    # If BOUNDED_SWEEP_FRACTIONS constants were used, 0.0/0.20/0.40 cells would appear.
    assert all(math.isclose(c.fraction, 0.10) for c in cells)


def test_enumerator_uses_config_seeds_not_constants() -> None:
    """Wiring: enumerator reads seeds from config.seeds, not module-level TRAINING_SEEDS."""
    single_seed_pools = SeedPools(
        training=(0,),
        poisoning=(100,),
        analysis=(300,),
    )
    config = CalibrationPoisoningConfig(
        policies=(ThresholdPolicy.B1_GLOBAL,),
        sources=(PoisoningSourceStrategy.RANDOM_BENIGN,),
        fractions=(0.0,),
        knowledge=PoisoningKnowledge.GRAY_BOX_SCORE_ACCESS,
        target_scope=PoisoningTargetScope.SINGLE_CLIENT,
        scale=ExperimentScale.FULL,
        seeds=single_seed_pools,
    )
    victims_by_seed = {0: ("c0",)}
    cells = enumerate_bounded_sweep_matrix(victims_by_seed, config)
    # Only 1 seed pair → 1 cell
    assert len(cells) == 1
    assert cells[0].training_seed == 0
    assert cells[0].poisoning_seed == 100


# ---------------------------------------------------------------------------
# Bounded matrix shape tests
# ---------------------------------------------------------------------------


def test_matrix_size_is_exactly_1620() -> None:
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert len(cells) == 5 * 9 * 3 * 3 * 4


def test_matrix_policies_are_exactly_default_three() -> None:
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert {c.policy for c in cells} == {
        ThresholdPolicy.B1_GLOBAL,
        ThresholdPolicy.B2_PERSONALIZED,
        ThresholdPolicy.B4_CLUSTER,
    }


def test_matrix_excludes_fraction_005() -> None:
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert all(not math.isclose(c.fraction, 0.05, abs_tol=0.0) for c in cells)


def test_matrix_fractions_are_exactly_locked_grid() -> None:
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert sorted({c.fraction for c in cells}) == pytest.approx([0.0, 0.10, 0.20, 0.40])


def test_matrix_sources_are_exactly_bounded_three() -> None:
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert {c.source for c in cells} == {
        PoisoningSourceStrategy.RANDOM_BENIGN,
        PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        PoisoningSourceStrategy.LOW_SCORE_BENIGN,
    }


def test_matrix_seed_pairs_are_exactly_the_locked_five() -> None:
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    pairs = {(c.training_seed, c.poisoning_seed) for c in cells}
    assert pairs == {(0, 100), (1, 101), (2, 102), (3, 103), (4, 104)}


def test_matrix_target_scope_is_always_single_client() -> None:
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert all(c.target_scope == PoisoningTargetScope.SINGLE_CLIENT for c in cells)


def test_matrix_missing_seed_raises_keyerror() -> None:
    incomplete = {0: _VICTIMS}
    with pytest.raises(KeyError):
        enumerate_bounded_sweep_matrix(incomplete, _bounded_config())


# ---------------------------------------------------------------------------
# Full-scope matrix (fraction 0.05 added) — execution gated; enumeration only.
# ---------------------------------------------------------------------------


def test_full_matrix_size_is_exactly_2025() -> None:
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, _full_config())
    assert len(cells) == 5 * 9 * 3 * 3 * 5


def test_full_matrix_fractions_add_005_to_bounded_grid() -> None:
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, _full_config())
    assert sorted({c.fraction for c in cells}) == pytest.approx(
        [0.0, 0.05, 0.10, 0.20, 0.40]
    )


def test_full_matrix_superset_of_bounded_matrix() -> None:
    bounded = set(enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config()))
    full = set(enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, _full_config()))
    assert bounded.issubset(full)
    assert sorted({c.fraction for c in (full - bounded)}) == pytest.approx([0.05])


def test_full_matrix_keeps_all_other_locks() -> None:
    cells = enumerate_full_sweep_matrix(_VICTIMS_BY_SEED, _full_config())
    assert {c.policy for c in cells} == set(ThresholdPolicy)
    assert all(c.target_scope == PoisoningTargetScope.SINGLE_CLIENT for c in cells)
    assert {(c.training_seed, c.poisoning_seed) for c in cells} == {
        (0, 100),
        (1, 101),
        (2, 102),
        (3, 103),
        (4, 104),
    }


def test_full_matrix_missing_seed_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        enumerate_full_sweep_matrix({0: _VICTIMS}, _full_config())
```

- [ ] **Step 2: Run matrix tests**

```
python -m pytest tests/unit/attacks/test_bounded_sweep_matrix.py -q --tb=short
```

Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add src/datp/attacks/bounded_sweep_matrix.py tests/unit/attacks/test_bounded_sweep_matrix.py
git commit -m "feat: wire CalibrationPoisoningConfig into bounded sweep matrix enumerator"
```

---

## Task 5: Wire `CalibrationPoisoningConfig` into `bounded_sweep_run.py`

**Files:**
- Modify: `src/datp/attacks/bounded_sweep_run.py`

### What to change

- Remove `config: CalibrationPoisoningConfig | None = None` default — make `config` required.
- Remove dummy `CalibrationPoisoningConfig(...)` construction in the `if config is None:` block.
- Remove imports: `BOUNDED_SWEEP_FRACTIONS`, `BOUNDED_SWEEP_SOURCES`, `DEFAULT_POLICIES`, `POISONING_SEEDS`, `TRAINING_SEEDS` from `datp.attacks.constants`.
- Remove imports: `AttackerObjective`, `PoisoningKnowledge`, `PoisoningTargetScope` (no longer needed for dummy config construction).
- Keep: `ExperimentScale` (still needed — check if actually used after changes; if not, remove too).
- Use `config.seeds.training` for the training-seed loop.
- Pass `config` to `enumerate_bounded_sweep_matrix(victims_by_seed, config)`.
- Use `config.policies`, `config.sources`, `config.fractions`, `config.seeds.training`, `config.seeds.poisoning` for manifest construction.
- Change `write_nbaiot_bounded_sweep_manifest` to instantiate `CalibrationPoisoningConfig.for_bounded_mvp()` and pass it.

- [ ] **Step 1: Rewrite `bounded_sweep_run.py`**

```python
"""Bounded N-BaIoT execution.

Single owner of the end-to-end bounded run: loads each training seed's
real score collection once, locks ``mu_flag_threshold`` per seed before any
poisoned cell for that seed, sweeps the locked 1620-cell matrix, and
assembles the single ``nbaiot_bounded_sweep_manifest.json`` artifact. This is the only
path that should ever produce that file — diagnostic/ad hoc scripts must not
duplicate this orchestration.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from datp.artifacts.poison_layout import PoisonLayout
from datp.attacks.bounded_sweep_cell import (
    SweepCellConfig,
    SweepCellResult,
    lock_mu_flag_threshold,
    run_sweep_cell,
)
from datp.attacks.bounded_sweep_manifest import (
    BoundedSweepManifest,
    BoundedSweepResultRow,
)
from datp.attacks.bounded_sweep_matrix import (
    SweepCellSpec,
    enumerate_bounded_sweep_matrix,
)
from datp.attacks.diagnostics import compute_blast_radius, compute_spillover
from datp.attacks.metric_engine import (
    compute_auroc_records,
    compute_victim_downstream_metrics,
)
from datp.attacks.real_score_loader import load_real_score_collection
from datp.attacks.run_manifest import ProvenanceRecord
from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import AurocSet
from datp.attacks.enums import objective_for_source
from datp.core.enums import Regime
from datp.config.attack_config import CalibrationPoisoningConfig
from datp.core.seed_sequence import derive_seed_record

_REPOSITORY_NAME: str = "datp-calibration-poisoning"


def _auroc_invariant(result: SweepCellResult) -> bool:
    clean = result.clean_metrics.auroc_records
    poisoned = result.poisoned_metrics.auroc_records
    return all(
        clean.for_client(record.client_id).auroc
        == poisoned.for_client(record.client_id).auroc
        for record in clean.records
    )


def _row_for_cell(
    collection: ScoreCollection,
    spec: SweepCellSpec,
    *,
    mu_flag_threshold: float,
    auroc_set: AurocSet,
) -> BoundedSweepResultRow:
    result = run_sweep_cell(
        spec,
        config=SweepCellConfig(
            collection=collection,
            mu_flag_threshold=mu_flag_threshold,
            auroc_set=auroc_set,
        ),
    )
    entry = result.poisoned_metrics.delta_tau[spec.victim_id]
    blast = compute_blast_radius(result.poisoned_metrics, victim_id=spec.victim_id)
    spill = compute_spillover(result.poisoned_metrics, victim_id=spec.victim_id)
    seed_record = derive_seed_record(
        spec.seed_pair,
        client_idx=collection.client_index(spec.victim_id),
        scope_idx=0,
    )
    victim_scores = collection.for_client(spec.victim_id)
    downstream = compute_victim_downstream_metrics(
        clean_threshold=entry.tau_clean,
        poisoned_threshold=entry.tau_pois,
        client_scores=victim_scores,
    )
    return BoundedSweepResultRow(
        policy=spec.policy,
        source=spec.source,
        objective=objective_for_source(spec.source),
        fraction=spec.fraction,
        target_scope=spec.target_scope,
        victim_id=spec.victim_id,
        training_seed=spec.training_seed,
        poisoning_seed=spec.poisoning_seed,
        seed_record=seed_record,
        delta_tau=entry.delta_tau,
        delta_tau_rel=entry.delta_tau_rel,
        is_victim_significant=entry.is_significant,
        cv_fpr=result.poisoned_metrics.fleet_fpr.cv_fpr,
        mean_fpr=result.poisoned_metrics.fleet_fpr.mean_fpr,
        coverage_ratio=result.poisoned_metrics.fleet_fpr.coverage_ratio,
        n_eligible=result.poisoned_metrics.fleet_fpr.n_eligible,
        mu_flag_triggered=result.poisoned_metrics.fleet_fpr.mu_flag_triggered,
        auroc_invariant=_auroc_invariant(result),
        blast_fraction=blast.blast_fraction,
        n_blast_significant=blast.n_significant,
        n_spillover=spill.n_spillover,
        n_non_victims=spill.n_non_victims,
        victim_tpr_clean=downstream.tpr_clean,
        victim_tpr_poisoned=downstream.tpr_poisoned,
        victim_delta_tpr=downstream.delta_tpr,
        victim_ba_clean=downstream.ba_clean,
        victim_ba_poisoned=downstream.ba_poisoned,
        victim_delta_ba=downstream.delta_ba,
        victim_macro_f1_clean=downstream.macro_f1_clean,
        victim_macro_f1_poisoned=downstream.macro_f1_poisoned,
        victim_delta_macro_f1=downstream.delta_macro_f1,
    )


def run_nbaiot_bounded_sweep(
    base_dir: Path,
    config: CalibrationPoisoningConfig,
) -> BoundedSweepManifest:
    """Execute the locked bounded matrix and return the assembled manifest.

    Loads one real score collection per training seed, locks
    ``mu_flag_threshold`` from that seed's clean B1 fleet FPR before any
    poisoned cell, and reuses it unmodified across every cell for that seed.
    Does not write to disk; callers persist via ``write_nbaiot_bounded_sweep_manifest``.
    """
    collections: dict[int, ScoreCollection] = {}
    mu_flag_by_seed: dict[int, float] = {}
    auroc_by_seed: dict[int, AurocSet] = {}
    victims_by_seed: dict[int, Sequence[str]] = {}

    for training_seed in config.seeds.training:
        collection = load_real_score_collection(
            regime=Regime.A, seed=training_seed, base_dir=base_dir
        )
        collections[training_seed] = collection
        mu_flag_by_seed[training_seed] = lock_mu_flag_threshold(collection)
        auroc_by_seed[training_seed] = compute_auroc_records(collection)
        victims_by_seed[training_seed] = collection.eligible_ids

    cells = enumerate_bounded_sweep_matrix(victims_by_seed, config)
    rows = [
        _row_for_cell(
            collections[spec.training_seed],
            spec,
            mu_flag_threshold=mu_flag_by_seed[spec.training_seed],
            auroc_set=auroc_by_seed[spec.training_seed],
        )
        for spec in cells
    ]

    provenance = ProvenanceRecord(local_epochs=1, repository=_REPOSITORY_NAME)
    return BoundedSweepManifest(
        generated_at_utc=datetime.now(UTC).isoformat(),
        provenance=provenance,
        policies=config.policies,
        sources=config.sources,
        fractions=config.fractions,
        training_seeds=config.seeds.training,
        poisoning_seeds=config.seeds.poisoning,
        mu_flag_threshold_by_training_seed=mu_flag_by_seed,
        n_cells=len(rows),
        results=tuple(rows),
    )


def write_nbaiot_bounded_sweep_manifest(base_dir: Path) -> Path:
    """Run the bounded sweep with the canonical config and write the manifest.

    Returns the path written (``PoisonLayout.nbaiot_bounded_sweep_manifest()``).
    """
    config = CalibrationPoisoningConfig.for_bounded_mvp()
    manifest = run_nbaiot_bounded_sweep(base_dir=base_dir, config=config)
    layout = PoisonLayout(base_dir=base_dir)
    out_path = layout.nbaiot_bounded_sweep_manifest()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return out_path
```

- [ ] **Step 2: Run pyright on the modified file**

```
pyright src/datp/attacks/bounded_sweep_run.py
```

Expected: no errors.

- [ ] **Step 3: Run unit tests to catch obvious regressions**

```
python -m pytest tests/unit/attacks/ -q --tb=short
```

Expected: all pass.

---

## Task 6: Update `test_bounded_sweep_run.py` (integration)

**Files:**
- Modify: `tests/integration/attacks/test_bounded_sweep_run.py`

Remove `from datp.attacks.constants import POISONING_SEEDS, TRAINING_SEEDS`. Replace all references to `TRAINING_SEEDS` / `POISONING_SEEDS` with `config.seeds.training` / `config.seeds.poisoning` from `CalibrationPoisoningConfig.for_bounded_mvp()`.

Add assertion that `manifest.policies`, `manifest.sources`, `manifest.fractions`, `manifest.training_seeds`, `manifest.poisoning_seeds` match config fields (proving manifest provenance came from config).

Add no-fallback test.

- [ ] **Step 1: Rewrite the integration test file**

```python
"""Integration test for the single bounded sweep run path.

Exercises the same wiring the real 1620-cell N-BaIoT execution uses:
real_score_loader -> bounded_matrix -> bounded_runner -> bounded_manifest, end to end,
against tiny FL-trained artifacts for all 5 locked seeds.
"""

from __future__ import annotations

import inspect
import math
from pathlib import Path

import pytest
import torch

from datp.attacks.bounded_sweep_run import (
    run_nbaiot_bounded_sweep,
    write_nbaiot_bounded_sweep_manifest,
)
from datp.config.attack_config import CalibrationPoisoningConfig
from datp.config.compose import BASE_CONFIG
from datp.config.models import ConvergenceConfig, DatpConfig, FederationConfig
from datp.core.device import resolve_device
from datp.core.enums import Regime
from datp.core.seeds import set_seeds
from datp.federated.protocols.fedavg import run_fl_training
from datp.federated.types import ClientData

_N_FEATURES = 10
_N_TRAIN = 200
_N_CAL = 150
_N_TEST = 50
_N_CLIENTS = 4  # B4_CLUSTER's locked K=3 requires eligible_count > k


def _make_client_data(seed: int) -> dict[str, ClientData]:
    device = resolve_device(require_cuda=False)
    rng = torch.Generator().manual_seed(seed)
    data = {}
    for i in range(_N_CLIENTS):
        data[f"client_{i}"] = ClientData(
            train=torch.randn(_N_TRAIN, _N_FEATURES, generator=rng).to(device),
            val=torch.randn(_N_CAL, _N_FEATURES, generator=rng).to(device),
            test_benign=torch.randn(_N_TEST, _N_FEATURES, generator=rng).to(device),
            test_attack=(torch.randn(_N_TEST, _N_FEATURES, generator=rng) + 5.0).to(
                device
            ),
        )
    return data


def _make_cfg() -> DatpConfig:
    return BASE_CONFIG.model_copy(
        update={
            "regime": Regime.A,
            "model": BASE_CONFIG.model.model_copy(
                update={"input_dim": _N_FEATURES, "encoder_dims": [8, 4]}
            ),
            "dataset": BASE_CONFIG.dataset.model_copy(
                update={"feature_count": _N_FEATURES}
            ),
            "machine": BASE_CONFIG.machine.model_copy(update={"batch_size_train": 64}),
            "federation": FederationConfig(
                local_epochs=1,
                convergence=ConvergenceConfig(
                    rounds_initial=1,
                    rounds_max=1,
                    relative_threshold=0.001,
                    window=2,
                    round_timeout_s=300.0,
                ),
            ),
        }
    )


def _train_all_seeds(tmp_path: Path, config: CalibrationPoisoningConfig) -> None:
    cfg = _make_cfg()
    for training_seed in config.seeds.training:
        set_seeds(training_seed)
        client_data = _make_client_data(training_seed)
        run_fl_training(
            cfg=cfg,
            client_data=client_data,
            seed=training_seed,
            alpha=None,
            base_dir=tmp_path,
        )


# ---------------------------------------------------------------------------
# No-fallback test — config must be required, no silent default
# ---------------------------------------------------------------------------


def test_run_nbaiot_bounded_sweep_config_is_required() -> None:
    """Runner must require config with no default — no silent fallback to constants."""
    sig = inspect.signature(run_nbaiot_bounded_sweep)
    param = sig.parameters.get("config")
    assert param is not None, "run_nbaiot_bounded_sweep must have a config parameter"
    assert param.default is inspect.Parameter.empty, (
        "config must have no default value — silent fallback to constants is forbidden"
    )


# ---------------------------------------------------------------------------
# End-to-end tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_run_nbaiot_bounded_sweep_end_to_end(tmp_path: Path) -> None:
    config = CalibrationPoisoningConfig.for_bounded_mvp()
    _train_all_seeds(tmp_path, config)

    manifest = run_nbaiot_bounded_sweep(base_dir=tmp_path, config=config)

    assert manifest.n_cells == len(config.seeds.training) * _N_CLIENTS * 3 * 3 * 4
    assert len(manifest.results) == manifest.n_cells
    assert set(manifest.mu_flag_threshold_by_training_seed) == set(config.seeds.training)
    assert tuple(sorted(manifest.training_seeds)) == tuple(sorted(config.seeds.training))
    assert tuple(sorted(manifest.poisoning_seeds)) == tuple(sorted(config.seeds.poisoning))
    assert manifest.provenance.local_epochs == 1

    # Manifest provenance fields come from config — not from constants.
    assert set(manifest.policies) == set(config.policies)
    assert set(manifest.sources) == set(config.sources)
    assert set(manifest.fractions) == set(config.fractions)

    # Calibration-channel-only invariant: every cell's test scores were untouched.
    assert all(row.auroc_invariant for row in manifest.results)

    # f=0.0 cells must carry exactly zero Δτ (no-op poisoning).
    zero_fraction_rows = [
        r for r in manifest.results if math.isclose(r.fraction, 0.0, abs_tol=0.0)
    ]
    assert zero_fraction_rows
    assert all(r.delta_tau == pytest.approx(0.0) for r in zero_fraction_rows)

    # Victim downstream metrics are present on every row.
    for row in manifest.results:
        assert hasattr(row, "victim_tpr_clean")
        assert hasattr(row, "victim_delta_tpr")
        assert hasattr(row, "victim_ba_clean")
        assert hasattr(row, "victim_delta_ba")
        assert hasattr(row, "victim_macro_f1_clean")
        assert hasattr(row, "victim_delta_macro_f1")

    # f=0.0 rows: clean == poisoned thresholds → all victim downstream deltas are zero.
    for row in zero_fraction_rows:
        assert row.victim_delta_tpr == pytest.approx(0.0), (
            f"victim_delta_tpr non-zero for f=0 row: {row.victim_delta_tpr}"
        )
        assert row.victim_delta_ba == pytest.approx(0.0), (
            f"victim_delta_ba non-zero for f=0 row: {row.victim_delta_ba}"
        )
        if not math.isnan(row.victim_delta_macro_f1):
            assert row.victim_delta_macro_f1 == pytest.approx(0.0)


@pytest.mark.integration
def test_write_nbaiot_bounded_sweep_manifest_writes_canonical_path(tmp_path: Path) -> None:
    config = CalibrationPoisoningConfig.for_bounded_mvp()
    _train_all_seeds(tmp_path, config)

    out_path = write_nbaiot_bounded_sweep_manifest(tmp_path)

    assert out_path.name == "nbaiot_bounded_sweep_manifest.json"
    assert out_path.exists()
```

- [ ] **Step 2: Run (skipping integration marker, just check imports and no-fallback test)**

```
python -m pytest tests/integration/attacks/test_bounded_sweep_run.py::test_run_nbaiot_bounded_sweep_config_is_required -q --tb=short
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add src/datp/attacks/bounded_sweep_run.py tests/integration/attacks/test_bounded_sweep_run.py
git commit -m "feat: wire CalibrationPoisoningConfig as required param in bounded sweep runner"
```

---

## Task 7: Wire config into CLI dry-run and update `test_poison_cli.py`

**Files:**
- Modify: `src/datp/app/cli/poison.py`
- Modify: `tests/unit/app/cli/test_poison_cli.py`

### CLI changes

In the `dry_run` command: when `stage == ExperimentStage.NBAIOT_BOUNDED`, instantiate `CalibrationPoisoningConfig.for_bounded_mvp()` and print its matrix dimensions. This proves the CLI dry-run uses the config path.

- [ ] **Step 1: Modify `poison.py` `dry_run` command**

Replace the `dry_run` function body with:

```python
@app.command("dry-run")
def dry_run(
    stage: ExperimentStage = typer.Option(
        ExperimentStage.NBAIOT_BOUNDED, help="stage to enumerate"
    ),
) -> None:
    """Enumerate cells for the stage without executing any experiment."""
    cfg = get_stage_config(stage)
    _stdout.print(f"[bold]dry-run[/bold]: stage={stage!r}")
    _stdout.print(f" scale : {cfg.scale}")
    _stdout.print(f" dataset : {cfg.dataset.value if cfg.dataset else 'none'}")
    _stdout.print(f" allow_run : {cfg.allow_run}")
    _stdout.print(f" gate : {cfg.gate or 'none'}")
    _stdout.print(f" description: {cfg.description}")
    if stage == ExperimentStage.NBAIOT_BOUNDED:
        from datp.config.attack_config import CalibrationPoisoningConfig
        attack_cfg = CalibrationPoisoningConfig.for_bounded_mvp()
        n_seeds = len(attack_cfg.seeds)
        n_policies = len(attack_cfg.policies)
        n_sources = len(attack_cfg.sources)
        n_fractions = len(attack_cfg.fractions)
        cells_per_victim = n_policies * n_sources * n_fractions * n_seeds
        _stdout.print(f" config_policies : {[p.value for p in attack_cfg.policies]}")
        _stdout.print(f" config_sources  : {[s.value for s in attack_cfg.sources]}")
        _stdout.print(f" config_fractions: {list(attack_cfg.fractions)}")
        _stdout.print(f" config_seeds    : {n_seeds} training seeds")
        _stdout.print(f" cells/victim    : {cells_per_victim} (× n_eligible_victims = total)")
        _stdout.print(
            f" note: objectives encoded through sources — HIGH→RAISE, LOW→LOWER, RANDOM→None"
        )
    if not cfg.allow_run:
        _stderr.print(f"[yellow]{_EXECUTION_GATE_NOTICE}[/yellow]")
        if cfg.gate:
            _stderr.print(
                f"[yellow]Gate[/yellow] {cfg.gate!r} must be resolved before execution."
            )
```

- [ ] **Step 2: Add import for `CalibrationPoisoningConfig` in `poison.py`**

Note: The import is done inline (inside the function) to avoid circular imports and to keep the CLI fast for non-bounded stages. The lazy import is acceptable here.

- [ ] **Step 3: Update `test_poison_cli.py` with wiring tests**

Add to the existing test file:

```python
class TestDryRunBoundedWiring:
    """Proves CLI dry-run uses CalibrationPoisoningConfig for bounded stage output."""

    def test_dry_run_bounded_shows_config_policies(self) -> None:
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_bounded"])
        assert result.exit_code == 0
        # All three locked policies must appear in the output.
        assert "b1_global" in result.output
        assert "b2_personalized" in result.output
        assert "b4_cluster" in result.output

    def test_dry_run_bounded_shows_config_sources(self) -> None:
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_bounded"])
        assert "random_benign" in result.output
        assert "high_score_benign" in result.output
        assert "low_score_benign" in result.output

    def test_dry_run_bounded_shows_cells_per_victim(self) -> None:
        # 3 policies × 3 sources × 4 fractions × 5 seeds = 180 cells/victim
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_bounded"])
        assert "180" in result.output

    def test_dry_run_bounded_notes_objective_encoding(self) -> None:
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_bounded"])
        assert "objectives" in result.output.lower() or "raise" in result.output.lower()

    def test_dry_run_non_bounded_stage_still_works(self) -> None:
        result = _runner.invoke(app, ["poison", "dry-run", "--stage", "nbaiot_full"])
        assert result.exit_code == 0
        # Gated stage: should NOT show config matrix (no for_bounded_mvp call)
        assert "blocked" in result.output.lower() or "gate" in result.output.lower()
```

- [ ] **Step 4: Run CLI tests**

```
python -m pytest tests/unit/app/cli/test_poison_cli.py -q --tb=short
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add src/datp/app/cli/poison.py tests/unit/app/cli/test_poison_cli.py
git commit -m "feat: wire CalibrationPoisoningConfig into CLI dry-run matrix enumeration"
```

---

## Task 8: Add GitHub Actions CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create the workflow**

```yaml
name: CP2 CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-and-type:
    name: Lint and type check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install uv
          uv sync --dev

      - name: ruff
        run: uv run python -m ruff check src/ tests/

      - name: pyright (attacks + config)
        run: uv run pyright src/datp/attacks/ src/datp/config/

  unit-tests:
    name: Unit tests (attacks + config)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install uv
          uv sync --dev

      - name: Run attack/config unit tests
        run: |
          uv run python -m pytest \
            tests/unit/config/ \
            tests/unit/attacks/ \
            tests/unit/app/cli/test_poison_cli.py \
            -q --tb=short
```

Note: Integration tests are excluded from CI because they require FL-trained artifacts and GPU-level compute. They are run manually via `make test-integration`.

- [ ] **Step 2: Verify the workflow file is valid YAML**

```
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add CP2 CI workflow for lint, type check, and unit tests"
```

---

## Task 9: Full test and type-check pass

- [ ] **Step 1: Run ruff**

```
python -m ruff check src/ tests/
```

Expected: No errors.

- [ ] **Step 2: Run pyright on attacks and config**

```
pyright src/datp/attacks/ src/datp/config/
```

Expected: No errors.

- [ ] **Step 3: Run all unit tests for attacks and config**

```
python -m pytest tests/unit/config/ tests/unit/attacks/ tests/unit/app/cli/test_poison_cli.py -q --tb=short
```

Expected: All pass.

- [ ] **Step 4: Run Makefile targets**

```
make poison-stages
make poison-dry-run
```

Expected: `poison-stages` lists all stages. `poison-dry-run` shows bounded stage with config matrix dimensions (3 policies, 3 sources, 4 fractions, 5 seeds, 180 cells/victim).

- [ ] **Step 5: Commit any cleanup**

```bash
git add -p  # stage only remaining changes
git commit -m "chore: final cleanup after config-driven bounded sweep wiring"
```

---

## Self-Review

### Spec coverage check

| Requirement | Task |
|-------------|------|
| Config is canonical object consumed by runner | Task 5 |
| Runner doesn't import matrix constants | Task 5 |
| CLI instantiates config and passes to runner | Task 7 |
| Dry-run enumerates from same config path | Task 7 |
| Stage checks validate before execution | Existing (untouched) |
| Manifest provenance includes config identity | Task 5 (manifest fields come from config) + Task 6 (test) |
| Objectives: encoded through sources, not separate dimension | Task 4 (wiring tests + comment) |
| Config construction test | Task 2 `TestForBoundedMvp` |
| Runner wiring test (monkeypatch) | Task 4 `test_enumerator_uses_config_*` |
| CLI wiring test | Task 7 `TestDryRunBoundedWiring` |
| Negative: `local_epochs != 1` | Task 2 `TestConfigE1Enforcement` |
| Negative: B3 included | Task 2 `TestConfigB3Excluded` |
| Negative: missing B1/B2/B4 | Task 2 `test_bounded_requires_all_three_policies` |
| Negative: unknown policy | Type system (ThresholdPolicy enum) |
| Negative: invalid injection rule | Task 2 `TestConfigInjectionRule` |
| Negative: bounded + non-single-client scope | Task 2 `test_bounded_multi_client_rejected` |
| Negative: B4 k != 3 | Task 2 `test_k_not_three_raises` |
| Negative: invalid B4 random state | Task 2 `test_invalid_random_state_raises` |
| Negative: invalid fraction not in locked grid | Task 2 `test_bounded_scale_rejects_005_fraction` |
| Negative: missing training seed | Task 2 (SeedPools empty test) |
| Negative: wrong poisoning seed pool | Task 2 (SeedPools overlap test) |
| Negative: source outside bounded source set | Task 2 `test_bounded_requires_exactly_three_bounded_sources` |
| Negative: objective outside locked set | Implicit — source-strategy encoding |
| No-fallback test | Task 6 `test_run_nbaiot_bounded_sweep_config_is_required` |
| Manifest test | Task 6 `test_run_nbaiot_bounded_sweep_end_to_end` |
| Dry-run count test (180 cells/victim) | Task 7 `test_dry_run_bounded_shows_cells_per_victim` |
| Existing tests updated | Tasks 2, 4, 6, 7 |
| CI: ruff + pyright + unit tests | Task 8 |

### Placeholder scan

No placeholders found. All code blocks are complete.

### Type consistency

- `CalibrationPoisoningConfig.for_bounded_mvp()` returns `CalibrationPoisoningConfig` — consistent with all call sites.
- `enumerate_bounded_sweep_matrix(victims_by_training_seed, config)` — consistent between Task 3 definition and Task 4 test usage.
- `run_nbaiot_bounded_sweep(base_dir, config)` — consistent between Task 5 definition and Task 6 test usage.
- `config.policies: tuple[ThresholdPolicy, ...]` — consistent in config, runner, and manifest.
- `config.sources: tuple[PoisoningSourceStrategy, ...]` — consistent.
- `config.seeds.training: tuple[int, ...]` — consistent with `SeedPools.training`.
