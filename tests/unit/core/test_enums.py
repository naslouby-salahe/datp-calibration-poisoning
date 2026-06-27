"""Tests verifying system-wide enums and associated constants."""

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
from datp.reporting.enums import FigureName


class TestThresholdPolicyEnum:
    """Tests for verifying canonical threshold policies and values."""

    def test_canonical_policies_present(self) -> None:
        """Verify the exact set of supported threshold policies."""
        assert set(ThresholdPolicy) == {
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        }

    def test_policy_values_are_lowercase(self) -> None:
        """Ensure all threshold policy string values are lowercase."""
        for b in ThresholdPolicy:
            assert b.value == b.value.lower()

    def test_policy_is_str_compatible(self) -> None:
        """Confirm policies are string compatible and serialize correctly."""
        assert ThresholdPolicy.GLOBAL_THRESHOLD == "global_threshold"
        assert str(ThresholdPolicy.LOCAL_THRESHOLD) == "local_threshold"


class TestDatasetIDEnum:
    """Tests for validating dataset identifiers."""

    def test_dataset_ids_present(self) -> None:
        """Verify N-BAIOT identifier exists in dataset catalog enum."""
        assert DatasetID.NBAIOT in DatasetID


class TestThresholdAggregationByPolicy:
    """Tests mapping policies to threshold aggregation methods."""

    def test_every_controlled_policy_has_an_entry(self) -> None:
        """Verify every controlled threshold policy maps to an aggregation method."""
        for b in CONTROLLED_POLICIES:
            assert b in THRESHOLD_AGGREGATION_BY_POLICY, (
                f"{b} missing from THRESHOLD_AGGREGATION_BY_POLICY"
            )

    def test_global_is_eligible_client_arithmetic_mean(self) -> None:
        """Confirm GLOBAL_THRESHOLD maps to the unweighted mean over eligible clients."""
        assert THRESHOLD_AGGREGATION_BY_POLICY[ThresholdPolicy.GLOBAL_THRESHOLD] == (
            ThresholdAggregationMethod.ELIGIBLE_CLIENT_ARITHMETIC_MEAN
        )

    def test_local_is_per_client_percentile(self) -> None:
        """Confirm LOCAL_THRESHOLD maps to per-client percentile aggregation."""
        assert THRESHOLD_AGGREGATION_BY_POLICY[ThresholdPolicy.LOCAL_THRESHOLD] == (
            ThresholdAggregationMethod.PER_CLIENT_PERCENTILE
        )

    def test_cluster_is_eligible_cluster_arithmetic_mean(self) -> None:
        """Confirm CLUSTER_THRESHOLD maps to cluster arithmetic mean aggregation."""
        assert THRESHOLD_AGGREGATION_BY_POLICY[ThresholdPolicy.CLUSTER_THRESHOLD] == (
            ThresholdAggregationMethod.ELIGIBLE_CLUSTER_ARITHMETIC_MEAN
        )

    def test_values_are_threshold_aggregation_method_instances(self) -> None:
        """Ensure the mapped targets are indeed valid aggregation enums."""
        for b, v in THRESHOLD_AGGREGATION_BY_POLICY.items():
            assert isinstance(v, ThresholdAggregationMethod), (
                f"{b}: expected ThresholdAggregationMethod, got {type(v)}"
            )


class TestClientStatusEnum:
    """Tests for validating client status enum values."""

    def test_eligible_value(self) -> None:
        """Confirm 'eligible' maps to client eligibility status."""
        assert ClientStatus.ELIGIBLE == "eligible"

    def test_calibration_pending_value(self) -> None:
        """Confirm 'calibration_pending' maps to calibration pending status."""
        assert ClientStatus.CALIBRATION_PENDING == "calibration_pending"


class TestSplitEnum:
    """Tests for validating split enum members."""

    def test_all_four_splits_present(self) -> None:
        """Ensure the exact train, cal, test_benign, test_attack splits exist."""
        assert set(Split) == {
            Split.TRAIN,
            Split.CAL,
            Split.TEST_BENIGN,
            Split.TEST_ATTACK,
        }


class TestNormalizationScopeEnum:
    """Tests for validating normalization scope enum values."""

    def test_normalization_scope_values(self) -> None:
        """Verify global and per-client normalization scope values."""
        assert NormalizationScope.GLOBAL == "global"
        assert NormalizationScope.PER_CLIENT == "per_client"


class TestScoringStageEnum:
    """Tests for validating scoring stage enum values."""

    def test_scoring_stage_values(self) -> None:
        """Verify cal, test_benign, and test_attack scoring stage values."""
        assert ScoringStage.CAL == "cal"
        assert ScoringStage.TEST_BENIGN == "test_benign"
        assert ScoringStage.TEST_ATTACK == "test_attack"


class TestControlledPolicies:
    """Tests for validating controlled policies constant definition."""

    def test_contains_global_local_cluster(self) -> None:
        """Verify controlled policies include global, local, and cluster thresholds."""
        assert set(CONTROLLED_POLICIES) == {
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        }

    def test_is_tuple(self) -> None:
        """Ensure controlled policies is represented as an immutable tuple."""
        assert isinstance(CONTROLLED_POLICIES, tuple)


class TestClusterThresholdFingerprintFeatures:
    """Tests for verifying cluster threshold fingerprint features definition."""

    def test_contains_four_features(self) -> None:
        """Ensure exactly four statistical features are defined for clustering."""
        assert len(CLUSTER_FINGERPRINT_FEATURES) == 4

    def test_feature_names(self) -> None:
        """Verify statistical fingerprint feature tuple entries."""
        assert CLUSTER_FINGERPRINT_FEATURES == ("mean", "std", "skew", "p95")

    def test_is_tuple(self) -> None:
        """Ensure cluster fingerprint features is represented as a tuple."""
        assert isinstance(CLUSTER_FINGERPRINT_FEATURES, tuple)


class TestEvidenceRole:
    """Tests for validating evidence role enum values."""

    def test_descriptive_value(self) -> None:
        """Verify descriptive evidence role string value."""
        assert EvidenceRole.DESCRIPTIVE == "descriptive"

    def test_secondary_value(self) -> None:
        """Verify secondary evidence role string value."""
        assert EvidenceRole.SECONDARY == "secondary"

    def test_descriptive_with_sidecar_delta_value(self) -> None:
        """Verify descriptive confirmatory sidecar delta role string."""
        assert (
            EvidenceRole.DESCRIPTIVE_WITH_CONFIRMATORY_SIDECAR_DELTA
            == "descriptive_with_confirmatory_sidecar_delta"
        )

    def test_is_str_compatible(self) -> None:
        """Ensure all EvidenceRole members are string-compatible."""
        for role in EvidenceRole:
            assert isinstance(role, str)


class TestSeedScope:
    """Tests for validating seed scope enum values."""

    def test_representative_seed_value(self) -> None:
        """Verify representative seed scope string value."""
        assert SeedScope.REPRESENTATIVE_SEED == "representative_seed"

    def test_all_seed_value(self) -> None:
        """Verify all seeds scope string value."""
        assert SeedScope.ALL_SEEDS == "all_seeds"

    def test_is_str_compatible(self) -> None:
        """Ensure all SeedScope members are string-compatible."""
        for scope in SeedScope:
            assert isinstance(scope, str)


class TestFigureName:
    """Tests for validating figure name enum values."""

    def test_four_figures_defined(self) -> None:
        """Verify exactly four figures are defined in the enum."""
        assert len(FigureName) == 4

    def test_figure_values(self) -> None:
        """Verify FigureName mapping values match standard identifiers."""
        assert FigureName.FIGURE_1 == "figure_1"
        assert FigureName.FIGURE_2 == "figure_2"
        assert FigureName.FIGURE_3 == "figure_3"
        assert FigureName.FIGURE_4 == "figure_4"

    def test_is_str_compatible(self) -> None:
        """Ensure all FigureName members are string-compatible."""
        for name in FigureName:
            assert isinstance(name, str)
