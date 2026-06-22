from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from datp.checkpointing.enums import EvidenceRole
from datp.core.enums import (
    CLUSTER_FINGERPRINT_FEATURES,
    CONTROLLED_POLICIES,
    ClientStatus,
    NormalizationScope,
    ScoringStage,
    SeedScope,
    THRESHOLD_AGGREGATION_BY_POLICY,
    ThresholdAggregationMethod,
)
from datp.data.catalog import DatasetID
from datp.data.splits import Split
from datp.experiments.enums import SweepStep
from datp.reporting.enums import FigureName


class TestThresholdPolicyEnum:
    def test_canonical_policies_present(self) -> None:
        assert set(ThresholdPolicy) == {
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        }

    def test_policy_values_are_lowercase(self) -> None:
        for b in ThresholdPolicy:
            assert b.value == b.value.lower()

    def test_policy_is_str_compatible(self) -> None:
        assert ThresholdPolicy.GLOBAL_THRESHOLD == "global_threshold"
        assert str(ThresholdPolicy.LOCAL_THRESHOLD) == "local_threshold"


class TestDatasetIDEnum:
    def test_dataset_ids_present(self) -> None:
        assert DatasetID.NBAIOT in DatasetID
        assert DatasetID.CICIOT2023 in DatasetID


class TestThresholdAggregationByPolicy:
    def test_every_controlled_policy_has_an_entry(self) -> None:
        for b in CONTROLLED_POLICIES:
            assert b in THRESHOLD_AGGREGATION_BY_POLICY, (
                f"{b} missing from THRESHOLD_AGGREGATION_BY_POLICY"
            )

    def test_global_is_eligible_client_arithmetic_mean(self) -> None:
        assert THRESHOLD_AGGREGATION_BY_POLICY[ThresholdPolicy.GLOBAL_THRESHOLD] == (
            ThresholdAggregationMethod.ELIGIBLE_CLIENT_ARITHMETIC_MEAN
        )

    def test_local_is_per_client_percentile(self) -> None:
        assert THRESHOLD_AGGREGATION_BY_POLICY[ThresholdPolicy.LOCAL_THRESHOLD] == (
            ThresholdAggregationMethod.PER_CLIENT_PERCENTILE
        )

    def test_cluster_is_eligible_cluster_arithmetic_mean(self) -> None:
        assert THRESHOLD_AGGREGATION_BY_POLICY[ThresholdPolicy.CLUSTER_THRESHOLD] == (
            ThresholdAggregationMethod.ELIGIBLE_CLUSTER_ARITHMETIC_MEAN
        )

    def test_values_are_threshold_aggregation_method_instances(self) -> None:
        for b, v in THRESHOLD_AGGREGATION_BY_POLICY.items():
            assert isinstance(v, ThresholdAggregationMethod), (
                f"{b}: expected ThresholdAggregationMethod, got {type(v)}"
            )


class TestClientStatusEnum:
    def test_eligible_value(self) -> None:
        assert ClientStatus.ELIGIBLE == "eligible"

    def test_calibration_pending_value(self) -> None:
        assert ClientStatus.CALIBRATION_PENDING == "calibration_pending"


class TestSplitEnum:
    def test_all_four_splits_present(self) -> None:
        assert set(Split) == {
            Split.TRAIN,
            Split.CAL,
            Split.TEST_BENIGN,
            Split.TEST_ATTACK,
        }


class TestNewEnums:
    def test_normalization_scope_values(self) -> None:
        assert NormalizationScope.GLOBAL == "global"
        assert NormalizationScope.PER_CLIENT == "per_client"

    def test_scoring_stage_values(self) -> None:
        assert ScoringStage.CAL == "cal"
        assert ScoringStage.TEST_BENIGN == "test_benign"
        assert ScoringStage.TEST_ATTACK == "test_attack"

    def test_init_score_provider_step_exists(self) -> None:
        assert SweepStep.INIT_SCORE_PROVIDER == "init_score_provider"

    def test_preload_test_scores_step_removed(self) -> None:
        assert "PRELOAD_TEST_SCORES" not in SweepStep.__members__


class TestControlledPolicies:
    def test_contains_global_local_cluster(self) -> None:
        assert set(CONTROLLED_POLICIES) == {
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        }

    def test_is_tuple(self) -> None:
        assert isinstance(CONTROLLED_POLICIES, tuple)


class TestClusterThresholdFingerprintFeatures:
    def test_contains_four_features(self) -> None:
        assert len(CLUSTER_FINGERPRINT_FEATURES) == 4

    def test_feature_names(self) -> None:
        assert CLUSTER_FINGERPRINT_FEATURES == ("mean", "std", "skew", "p95")

    def test_is_tuple(self) -> None:
        assert isinstance(CLUSTER_FINGERPRINT_FEATURES, tuple)


class TestEvidenceRole:
    def test_descriptive_value(self) -> None:
        assert EvidenceRole.DESCRIPTIVE == "descriptive"

    def test_secondary_value(self) -> None:
        assert EvidenceRole.SECONDARY == "secondary"

    def test_descriptive_with_sidecar_delta_value(self) -> None:
        assert (
            EvidenceRole.DESCRIPTIVE_WITH_CONFIRMATORY_SIDECAR_DELTA
            == "descriptive_with_confirmatory_sidecar_delta"
        )

    def test_is_str_compatible(self) -> None:
        for role in EvidenceRole:
            assert isinstance(role, str)


class TestSeedScope:
    def test_representative_seed_value(self) -> None:
        assert SeedScope.REPRESENTATIVE_SEED == "representative_seed"

    def test_all_seed_value(self) -> None:
        assert SeedScope.ALL_SEEDS == "all_seeds"

    def test_is_str_compatible(self) -> None:
        for scope in SeedScope:
            assert isinstance(scope, str)


class TestFigureName:
    def test_four_figures_defined(self) -> None:
        assert len(FigureName) == 4

    def test_figure_values(self) -> None:
        assert FigureName.FIGURE_1 == "figure_1"
        assert FigureName.FIGURE_2 == "figure_2"
        assert FigureName.FIGURE_3 == "figure_3"
        assert FigureName.FIGURE_4 == "figure_4"

    def test_is_str_compatible(self) -> None:
        for name in FigureName:
            assert isinstance(name, str)
