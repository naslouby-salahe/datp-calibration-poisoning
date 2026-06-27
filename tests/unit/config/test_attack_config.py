"""Unit tests for CalibrationPoisoningConfig construction and validation."""

from __future__ import annotations

import pytest
from typing import Any
from pydantic import ValidationError

from datp.config.attack_config import (
    ClusterConfig,
    CalibrationPoisoningConfig,
    SeedPools,
)
from datp.attacks.enums import (
    CalibrationInjectionRule,
    PoisoningDefense,
    PoisoningKnowledge,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.core.enums import ThresholdPolicy
from datp.config.models import ExperimentStage


class TestSeedPools:
    """Seed pool generation and bounds."""

    def test_default_values(self) -> None:
        pools = SeedPools()
        assert pools.training == tuple(range(10))
        assert pools.poisoning == tuple(range(100, 110))
        assert pools.analysis == tuple(range(300, 310))
        assert pools.compromise_pattern == 400
        assert pools.split == 0

    def test_len_returns_training_length(self) -> None:
        assert len(SeedPools()) == 10

    def test_triplet_returns_correct_index(self) -> None:
        pools = SeedPools()
        assert pools.triplet(0) == (0, 100, 300)
        assert pools.triplet(9) == (9, 109, 309)

    def test_mismatched_pool_lengths_raise(self) -> None:
        with pytest.raises(ValidationError, match="same length"):
            SeedPools(training=(0, 1, 2), poisoning=(100, 101))

    def test_empty_pools_raise(self) -> None:
        with pytest.raises(ValidationError, match="empty"):
            SeedPools(training=(), poisoning=(), analysis=())

    def test_overlapping_seeds_raise(self) -> None:
        with pytest.raises(ValidationError, match="pairwise distinct"):
            SeedPools(
                training=tuple(range(10)),
                poisoning=(0, *range(101, 110)),
                analysis=tuple(range(300, 310)),
            )

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            SeedPools.model_validate({"bogus": 99})

    def test_frozen(self) -> None:
        pools = SeedPools()
        with pytest.raises(ValidationError):
            setattr(pools, "training", (9,))


class TestClusterConfig:
    """Cluster configuration validation."""

    def test_defaults_are_locked_values(self) -> None:
        cluster = ClusterConfig()
        assert cluster.k == 3
        assert cluster.n_init == 10
        assert cluster.max_iter == 300
        assert cluster.random_state == 42

    def test_k_not_three_raises(self) -> None:
        with pytest.raises(ValidationError, match="Input should be 3"):
            ClusterConfig.model_validate({"k": 4})

    def test_invalid_random_state_raises(self) -> None:
        with pytest.raises(ValidationError, match="Input should be 42"):
            ClusterConfig.model_validate({"random_state": 0})

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            ClusterConfig.model_validate({"bogus": 1})


def _valid_config(**overrides: Any) -> CalibrationPoisoningConfig:
    defaults: dict[str, Any] = {
        "policies": (
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ),
        "sources": (
            PoisoningSourceStrategy.RANDOM_BENIGN,
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        ),
        "knowledge": PoisoningKnowledge.GRAY_BOX_SCORE_ACCESS,
        "target_scope": PoisoningTargetScope.SINGLE_CLIENT,
        "stage": ExperimentStage.NBAIOT_MAIN,
    }
    defaults.update(overrides)
    return CalibrationPoisoningConfig(**defaults)


class TestConfigValid:
    """Valid CalibrationPoisoningConfig construction."""

    def test_minimal_valid_config(self) -> None:
        cfg = _valid_config()
        assert cfg.local_epochs == 1
        assert cfg.policies == (
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
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
        assert not hasattr(cfg, "objective"), (
            "singular 'objective' field must not exist"
        )

    def test_default_seeds_are_locked_pools(self) -> None:
        cfg = _valid_config()
        assert cfg.seeds.training == tuple(range(10))
        assert cfg.seeds.poisoning == tuple(range(100, 110))
        assert cfg.seeds.compromise_pattern == 400

    def test_default_cluster_locked_values(self) -> None:
        cfg = _valid_config()
        assert cfg.cluster.k == 3
        assert cfg.cluster.n_init == 10
        assert cfg.cluster.max_iter == 300
        assert cfg.cluster.random_state == 42

    def test_mu_flag_threshold_can_be_set(self) -> None:
        cfg = _valid_config(mu_flag_threshold=0.025)
        assert cfg.mu_flag_threshold == pytest.approx(0.025)

    def test_frozen(self) -> None:
        cfg = _valid_config()
        with pytest.raises(ValidationError):
            setattr(cfg, "local_epochs", 2)


class TestForBoundedSweep:
    """Bounded-sweep config factory method."""

    def test_returns_config_instance(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_sweep()
        assert isinstance(cfg, CalibrationPoisoningConfig)

    def test_has_exactly_three_canonical_policies(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_sweep()
        assert set(cfg.policies) == {
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        }

    def test_has_exactly_three_bounded_sources(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_sweep()
        assert set(cfg.sources) == {
            PoisoningSourceStrategy.RANDOM_BENIGN,
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        }

    def test_fractions_are_locked_bounded_grid(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_sweep()
        assert set(cfg.fractions) == {0.0, 0.10, 0.20, 0.40}
        assert 0.05 not in cfg.fractions

    def test_seed_pools_are_locked(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_sweep()
        assert cfg.seeds.training == tuple(range(10))
        assert cfg.seeds.poisoning == tuple(range(100, 110))
        assert cfg.seeds.compromise_pattern == 400

    def test_scale_is_bounded(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_sweep()
        assert cfg.stage == ExperimentStage.NBAIOT_MAIN

    def test_target_scope_is_single_client(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_sweep()
        assert cfg.target_scope == PoisoningTargetScope.SINGLE_CLIENT

    def test_local_epochs_is_one(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_sweep()
        assert cfg.local_epochs == 1

    def test_injection_rule_is_replace_fixed_budget(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_sweep()
        assert cfg.injection_rule == CalibrationInjectionRule.REPLACE_FIXED_BUDGET

    def test_cluster_config_is_locked(self) -> None:
        cfg = CalibrationPoisoningConfig.for_bounded_sweep()
        assert cfg.cluster.k == 3
        assert cfg.cluster.n_init == 10
        assert cfg.cluster.max_iter == 300
        assert cfg.cluster.random_state == 42


class TestConfigE1Enforcement:
    """Single-epoch enforcement in config."""

    def test_local_epochs_1_accepted(self) -> None:
        cfg = _valid_config(local_epochs=1)
        assert cfg.local_epochs == 1

    def test_local_epochs_5_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Input should be 1"):
            _valid_config(local_epochs=5)

    def test_local_epochs_2_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Input should be 1"):
            _valid_config(local_epochs=2)

    def test_local_epochs_0_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Input should be 1"):
            _valid_config(local_epochs=0)


class TestConfigFractionValidation:
    """Fraction field bounds and validation."""

    def test_bounded_fractions_accepted(self) -> None:
        cfg = _valid_config(fractions=(0.0, 0.10, 0.20, 0.40))
        assert 0.0 in cfg.fractions
        assert 0.40 in cfg.fractions

    def test_fraction_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError, match="within"):
            _valid_config(fractions=(0.0, 1.1))

    def test_negative_fraction_rejected(self) -> None:
        with pytest.raises(ValidationError, match="within"):
            _valid_config(fractions=(-0.1, 0.10))

    def test_empty_fractions_rejected(self) -> None:
        with pytest.raises(ValidationError, match="empty"):
            _valid_config(fractions=())

    def test_bounded_scale_rejects_005_fraction(self) -> None:
        with pytest.raises(ValidationError, match="Required exactly fractions"):
            _valid_config(
                stage=ExperimentStage.NBAIOT_MAIN, fractions=(0.0, 0.05, 0.10)
            )

    def test_bounded_scale_rejects_partial_fraction_subset(self) -> None:
        with pytest.raises(ValidationError, match="Required exactly fractions"):
            _valid_config(
                stage=ExperimentStage.NBAIOT_MAIN, fractions=(0.10, 0.20, 0.40)
            )


class TestConfigInjectionRule:
    """Injection rule validation in config."""

    def test_replace_fixed_budget_accepted(self) -> None:
        cfg = _valid_config(
            injection_rule=CalibrationInjectionRule.REPLACE_FIXED_BUDGET
        )
        assert cfg.injection_rule == CalibrationInjectionRule.REPLACE_FIXED_BUDGET


class TestConfigBoundedScaleConstraints:
    """Scale-dependent constraints on bounded-sweep config."""

    def test_bounded_single_client_accepted(self) -> None:
        cfg = _valid_config(
            stage=ExperimentStage.NBAIOT_MAIN,
            target_scope=PoisoningTargetScope.SINGLE_CLIENT,
        )
        assert cfg.stage == ExperimentStage.NBAIOT_MAIN

    def test_bounded_multi_client_rejected(self) -> None:
        with pytest.raises(
            ValidationError, match="NBAIOT_MAIN stage requires SINGLE_CLIENT"
        ):
            _valid_config(
                stage=ExperimentStage.NBAIOT_MAIN,
                target_scope=PoisoningTargetScope.MULTI_CLIENT,
            )

    def test_bounded_requires_all_three_policies(self) -> None:
        with pytest.raises(ValidationError, match="Required exactly policies"):
            _valid_config(
                stage=ExperimentStage.NBAIOT_MAIN,
                policies=(
                    ThresholdPolicy.GLOBAL_THRESHOLD,
                    ThresholdPolicy.LOCAL_THRESHOLD,
                ),
            )

    def test_bounded_rejects_incomplete_policies(self) -> None:
        with pytest.raises(ValidationError, match="Required exactly policies"):
            _valid_config(
                stage=ExperimentStage.NBAIOT_MAIN,
                policies=(ThresholdPolicy.GLOBAL_THRESHOLD,),
            )

    def test_bounded_requires_exactly_three_bounded_sources(self) -> None:
        with pytest.raises(ValidationError, match="Required exactly sources"):
            _valid_config(
                stage=ExperimentStage.NBAIOT_MAIN,
                sources=(PoisoningSourceStrategy.RANDOM_BENIGN,),
            )

    def test_full_scale_multi_client_accepted(self) -> None:
        cfg = _valid_config(
            stage=ExperimentStage.NBAIOT_FULL_OPTIONAL,
            target_scope=PoisoningTargetScope.MULTI_CLIENT,
            policies=(ThresholdPolicy.GLOBAL_THRESHOLD,),
            sources=(PoisoningSourceStrategy.RANDOM_BENIGN,),
        )
        assert cfg.target_scope == PoisoningTargetScope.MULTI_CLIENT

    def test_full_scale_accepts_fraction_005(self) -> None:
        cfg = _valid_config(
            stage=ExperimentStage.NBAIOT_FULL_OPTIONAL,
            target_scope=PoisoningTargetScope.SINGLE_CLIENT,
            policies=(
                ThresholdPolicy.GLOBAL_THRESHOLD,
                ThresholdPolicy.LOCAL_THRESHOLD,
                ThresholdPolicy.CLUSTER_THRESHOLD,
            ),
            sources=(
                PoisoningSourceStrategy.RANDOM_BENIGN,
                PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
                PoisoningSourceStrategy.LOW_SCORE_BENIGN,
            ),
            fractions=(0.0, 0.05, 0.10, 0.20, 0.40),
        )
        assert 0.05 in cfg.fractions


class TestThresholdPolicyMembership:
    """Policy membership enumeration."""

    def test_only_canonical_policies_exist(self) -> None:
        expected = {"global_threshold", "local_threshold", "cluster_threshold"}
        actual = {p.value for p in ThresholdPolicy}
        assert actual == expected


class TestPoliciesSourcesValidation:
    """Invalid source-objective pairs fail validation."""

    def test_empty_policies_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must not be empty"):
            _valid_config(
                stage=ExperimentStage.NBAIOT_FULL_OPTIONAL,
                target_scope=PoisoningTargetScope.SINGLE_CLIENT,
                policies=(),
                sources=(PoisoningSourceStrategy.RANDOM_BENIGN,),
            )

    def test_empty_sources_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must not be empty"):
            _valid_config(
                stage=ExperimentStage.NBAIOT_FULL_OPTIONAL,
                target_scope=PoisoningTargetScope.SINGLE_CLIENT,
                policies=(ThresholdPolicy.GLOBAL_THRESHOLD,),
                sources=(),
            )
