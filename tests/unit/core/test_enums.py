from __future__ import annotations

import pytest

from datp.checkpointing.enums import EvidenceRole
from datp.core.enums import (
    B4_FINGERPRINT_FEATURES,
    BASELINE_ROLE,
    CONTROLLED_BASELINES,
    ISOLATED_BASELINES,
    MAIN_BODY_BASELINES,
    REGIME_BASELINES,
    STATS_REPORTING_BASELINES,
    THRESHOLD_AGGREGATION_BY_BASELINE,
    B0NormalizationMode,
    B4RegimeAMode,
    Baseline,
    BaselineRole,
    ClientStatus,
    NormalizationScope,
    Regime,
    ScoringStage,
    SeedScope,
    ThresholdAggregationMethod,
    controlled_baselines_for_regime,
)
from datp.data.catalog import DatasetID
from datp.data.regimes.catalog import REGIME_DATASET
from datp.data.splits import Split
from datp.experiments.enums import SweepStep
from datp.reporting.enums import FigureName


class TestBaselineEnum:
    def test_main_baselines_present(self) -> None:
        assert set(Baseline) == {
            Baseline.B0,
            Baseline.B1,
            Baseline.B2,
            Baseline.B3,
            Baseline.B4,
        }

    def test_baseline_values_are_lowercase(self) -> None:
        for b in Baseline:
            assert b.value == b.value.lower()

    def test_baseline_is_str_compatible(self) -> None:
        assert Baseline.B1 == "b1"
        assert str(Baseline.B2) == "b2"


class TestDatasetIDEnum:
    def test_dataset_ids_present(self) -> None:
        assert DatasetID.NBAIOT in DatasetID
        assert DatasetID.CICIOT2023 in DatasetID


class TestDatasetByRegime:
    def test_every_regime_has_a_dataset(self) -> None:
        for r in Regime:
            assert r in REGIME_DATASET

    def test_regime_a_is_nbaiot(self) -> None:
        assert REGIME_DATASET[Regime.A] == DatasetID.NBAIOT

    def test_regime_b_is_ciciot(self) -> None:
        assert REGIME_DATASET[Regime.B] == DatasetID.CICIOT2023

    def test_regime_c_is_nbaiot(self) -> None:
        assert REGIME_DATASET[Regime.C] == DatasetID.NBAIOT


class TestThresholdAggregationByBaseline:
    def test_every_main_baseline_has_an_entry(self) -> None:
        for b in Baseline:
            assert b in THRESHOLD_AGGREGATION_BY_BASELINE, (
                f"{b} missing from THRESHOLD_AGGREGATION_BY_BASELINE"
            )

    def test_b1_is_eligible_client_arithmetic_mean(self) -> None:
        assert THRESHOLD_AGGREGATION_BY_BASELINE[Baseline.B1] == (
            ThresholdAggregationMethod.ELIGIBLE_CLIENT_ARITHMETIC_MEAN
        )

    def test_b2_is_per_client_percentile(self) -> None:
        assert THRESHOLD_AGGREGATION_BY_BASELINE[Baseline.B2] == (
            ThresholdAggregationMethod.PER_CLIENT_PERCENTILE
        )

    def test_b4_is_eligible_cluster_arithmetic_mean(self) -> None:
        assert THRESHOLD_AGGREGATION_BY_BASELINE[Baseline.B4] == (
            ThresholdAggregationMethod.ELIGIBLE_CLUSTER_ARITHMETIC_MEAN
        )

    def test_values_are_threshold_aggregation_method_instances(self) -> None:
        for b, v in THRESHOLD_AGGREGATION_BY_BASELINE.items():
            assert isinstance(v, ThresholdAggregationMethod), (
                f"{b}: expected ThresholdAggregationMethod, got {type(v)}"
            )


class TestRegimeBaselines:
    def test_b3_excluded_from_regime_b_and_c(self) -> None:
        assert Baseline.B3 not in REGIME_BASELINES[Regime.B]
        assert Baseline.B3 not in REGIME_BASELINES[Regime.C]

    def test_b0_excluded_from_regime_c(self) -> None:
        assert Baseline.B0 not in REGIME_BASELINES[Regime.C]


class TestIsolatedBaselines:
    def test_only_b0_is_isolated(self) -> None:
        assert ISOLATED_BASELINES == frozenset({Baseline.B0})

    def test_b1_b2_b3_b4_not_isolated(self) -> None:
        for b in (Baseline.B1, Baseline.B2, Baseline.B3, Baseline.B4):
            assert b not in ISOLATED_BASELINES


class TestMainBodyBaselines:
    def test_b0_to_b4_included(self) -> None:
        for b in (Baseline.B0, Baseline.B1, Baseline.B2, Baseline.B3, Baseline.B4):
            assert b in MAIN_BODY_BASELINES


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


class TestBaselineRole:
    def test_b0_is_centralized_reference(self) -> None:
        assert BASELINE_ROLE[Baseline.B0] == BaselineRole.CENTRALIZED_REFERENCE

    def test_b1_b2_b3_b4_are_controlled_threshold(self) -> None:
        for b in (Baseline.B1, Baseline.B2, Baseline.B3, Baseline.B4):
            assert BASELINE_ROLE[b] == BaselineRole.CONTROLLED_THRESHOLD

    def test_all_baselines_have_role(self) -> None:
        assert set(BASELINE_ROLE.keys()) == set(Baseline)

    def test_role_values_are_str_enum(self) -> None:
        for role in BaselineRole:
            assert isinstance(role, str)


class TestB0NormalizationMode:
    def test_per_client_prepared_value(self) -> None:
        assert B0NormalizationMode.PER_CLIENT_PREPARED == "per_client_prepared"

    def test_pooled_zscore_value(self) -> None:
        assert B0NormalizationMode.POOLED_ZSCORE == "pooled_zscore"


class TestB4RegimeAMode:
    def test_values(self) -> None:
        assert B4RegimeAMode.FIXED == "fixed"
        assert B4RegimeAMode.SILHOUETTE == "silhouette"
        assert len(B4RegimeAMode) == 2

    def test_parse_from_string(self) -> None:
        assert B4RegimeAMode("fixed") is B4RegimeAMode.FIXED
        assert B4RegimeAMode("silhouette") is B4RegimeAMode.SILHOUETTE

    def test_invalid_value_rejected(self) -> None:
        with pytest.raises(ValueError):
            B4RegimeAMode("invalid_mode")


class TestControlledBaselines:
    def test_contains_b1_b2_b3_b4(self) -> None:
        assert set(CONTROLLED_BASELINES) == {
            Baseline.B1,
            Baseline.B2,
            Baseline.B3,
            Baseline.B4,
        }

    def test_excludes_b0(self) -> None:
        assert Baseline.B0 not in CONTROLLED_BASELINES

    def test_is_tuple(self) -> None:
        assert isinstance(CONTROLLED_BASELINES, tuple)


class TestControlledBaselinesForRegime:
    def test_regime_a_includes_b3(self) -> None:
        result = controlled_baselines_for_regime(Regime.A)
        assert Baseline.B3 in result

    def test_regime_a_includes_b1_b2_b4(self) -> None:
        result = controlled_baselines_for_regime(Regime.A)
        assert Baseline.B1 in result
        assert Baseline.B2 in result
        assert Baseline.B4 in result

    def test_regime_b_excludes_b3(self) -> None:
        result = controlled_baselines_for_regime(Regime.B)
        assert Baseline.B3 not in result

    def test_regime_c_excludes_b3(self) -> None:
        result = controlled_baselines_for_regime(Regime.C)
        assert Baseline.B3 not in result

    def test_returns_tuple(self) -> None:
        assert isinstance(controlled_baselines_for_regime(Regime.A), tuple)

    def test_excludes_b0_for_all_regimes(self) -> None:
        for regime in Regime:
            assert Baseline.B0 not in controlled_baselines_for_regime(regime)


class TestB4FingerprintFeatures:
    def test_contains_four_features(self) -> None:
        assert len(B4_FINGERPRINT_FEATURES) == 4

    def test_feature_names(self) -> None:
        assert B4_FINGERPRINT_FEATURES == ("mean", "std", "skew", "p95")

    def test_is_tuple(self) -> None:
        assert isinstance(B4_FINGERPRINT_FEATURES, tuple)


class TestStatsReportingBaselines:
    def test_all_regimes_present(self) -> None:
        for regime in Regime:
            assert regime in STATS_REPORTING_BASELINES

    def test_regime_a_excludes_b0_and_b3(self) -> None:
        s = STATS_REPORTING_BASELINES[Regime.A]
        assert Baseline.B0 not in s
        assert Baseline.B3 not in s
        assert {Baseline.B1, Baseline.B2, Baseline.B4}.issubset(s)

    def test_regime_b_excludes_b0_includes_b1_b2_b4(self) -> None:
        s = STATS_REPORTING_BASELINES[Regime.B]
        assert Baseline.B0 not in s
        assert {Baseline.B1, Baseline.B2, Baseline.B4}.issubset(s)

    def test_each_regime_is_subset_of_regime_baselines(self) -> None:
        for regime, baselines in STATS_REPORTING_BASELINES.items():
            assert baselines.issubset(REGIME_BASELINES[regime])

    def test_no_regime_contains_isolated_baselines(self) -> None:
        for baselines in STATS_REPORTING_BASELINES.values():
            assert not (baselines & ISOLATED_BASELINES)


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
