"""Unit tests for typed config schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from datp.config.attack_config import (
    B4ClusterConfig,
    CalibrationPoisoningConfig,
    SeedPools,
)
from datp.core.poison_enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    ExperimentScale,
    PoisoningDefense,
    PoisoningKnowledge,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)

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

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            B4ClusterConfig(bogus=1)  # type: ignore[call-arg]


# ── CalibrationPoisoningConfig ─────────────────────────────────────────────────────────────


def _valid_config(**overrides: object) -> CalibrationPoisoningConfig:
    defaults: dict[str, object] = {
        "policy": ThresholdPolicy.B1_GLOBAL,
        "objective": AttackerObjective.THRESHOLD_RAISE,
        "source": PoisoningSourceStrategy.RANDOM_BENIGN,
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
        assert cfg.policy == ThresholdPolicy.B1_GLOBAL
        assert cfg.objective == AttackerObjective.THRESHOLD_RAISE
        assert cfg.injection_rule == CalibrationInjectionRule.REPLACE_FIXED_BUDGET
        assert cfg.defense == PoisoningDefense.NONE
        assert cfg.fractions == (0.0, 0.10, 0.20, 0.40)
        assert cfg.n_min == 100
        assert cfg.mu_flag_threshold is None

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
        assert cfg.mu_flag_threshold == 0.025

    def test_all_three_policies_accepted(self) -> None:
        for policy in ThresholdPolicy:
            cfg = _valid_config(policy=policy)
            assert cfg.policy == policy

    def test_frozen(self) -> None:
        cfg = _valid_config()
        with pytest.raises(ValidationError):
            cfg.local_epochs = 2  # type: ignore[misc]


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


class TestConfigInjectionRule:
    def test_replace_fixed_budget_accepted(self) -> None:
        cfg = _valid_config(
            injection_rule=CalibrationInjectionRule.REPLACE_FIXED_BUDGET
        )
        assert cfg.injection_rule == CalibrationInjectionRule.REPLACE_FIXED_BUDGET


class TestConfigBoundedScaleConstraint:
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

    def test_full_scale_multi_client_accepted(self) -> None:
        cfg = _valid_config(
            scale=ExperimentScale.FULL,
            target_scope=PoisoningTargetScope.MULTI_CLIENT,
        )
        assert cfg.target_scope == PoisoningTargetScope.MULTI_CLIENT


class TestConfigB3Excluded:
    def test_b3_not_in_threshold_policy(self) -> None:
        for policy in ThresholdPolicy:
            assert "b3" not in policy.value

    def test_only_b1_b2_b4_policies_exist(self) -> None:
        expected = {"b1_global", "b2_personalized", "b4_cluster"}
        actual = {p.value for p in ThresholdPolicy}
        assert actual == expected
