from __future__ import annotations

from datp.attacks.constants import (
    BOUNDED_SWEEP_FRACTIONS,
    BOUNDED_SWEEP_OBJECTIVES,
    BOUNDED_SWEEP_SOURCES,
    DEFAULT_POLICIES,
    FULL_SWEEP_FRACTIONS,
)
from datp.attacks.enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    PoisoningDefense,
    PoisoningKnowledge,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)
from datp.experiments.enums import ExperimentScale


class TestThresholdPolicy:
    def test_b3_excluded(self) -> None:
        values = {p.value for p in ThresholdPolicy}
        assert "b3" not in values
        assert "b3_family" not in values

    def test_contains_b1_b2_b4(self) -> None:
        assert ThresholdPolicy.B1_GLOBAL == "b1_global"
        assert ThresholdPolicy.B2_PERSONALIZED == "b2_personalized"
        assert ThresholdPolicy.B4_CLUSTER == "b4_cluster"

    def test_exactly_three_members(self) -> None:
        assert len(ThresholdPolicy) == 3

    def test_is_str_compatible(self) -> None:
        for policy in ThresholdPolicy:
            assert isinstance(policy, str)

    def test_default_policies_tuple(self) -> None:
        assert set(DEFAULT_POLICIES) == set(ThresholdPolicy)
        assert len(DEFAULT_POLICIES) == 3


class TestAttackerObjective:
    def test_threshold_raise_value(self) -> None:
        assert AttackerObjective.THRESHOLD_RAISE == "threshold_raise"

    def test_threshold_lower_value(self) -> None:
        assert AttackerObjective.THRESHOLD_LOWER == "threshold_lower"

    def test_exactly_two_members(self) -> None:
        assert len(AttackerObjective) == 2

    def test_is_str_compatible(self) -> None:
        for obj in AttackerObjective:
            assert isinstance(obj, str)

    def test_bounded_objectives_tuple(self) -> None:
        assert set(BOUNDED_SWEEP_OBJECTIVES) == set(AttackerObjective)


class TestPoisoningSourceStrategy:
    def test_random_benign_value(self) -> None:
        assert PoisoningSourceStrategy.RANDOM_BENIGN == "random_benign"

    def test_high_score_benign_value(self) -> None:
        assert PoisoningSourceStrategy.HIGH_SCORE_BENIGN == "high_score_benign"

    def test_low_score_benign_value(self) -> None:
        assert PoisoningSourceStrategy.LOW_SCORE_BENIGN == "low_score_benign"

    def test_diagnostic_only_member_exists(self) -> None:
        assert (
            PoisoningSourceStrategy.TARGETED_REMOVAL_LOW_SCORE
            in PoisoningSourceStrategy
        )

    def test_bounded_sources_excludes_diagnostic(self) -> None:
        for s in BOUNDED_SWEEP_SOURCES:
            assert "diagnostic" not in s.value

    def test_bounded_sources_contains_three_members(self) -> None:
        assert len(BOUNDED_SWEEP_SOURCES) == 3


class TestCalibrationInjectionRule:
    def test_replace_fixed_budget_value(self) -> None:
        assert CalibrationInjectionRule.REPLACE_FIXED_BUDGET == "replace_fixed_budget"

    def test_exactly_one_member(self) -> None:
        assert len(CalibrationInjectionRule) == 1

    def test_no_shift_magnitude_member(self) -> None:
        values = {r.value for r in CalibrationInjectionRule}
        assert not any("shift" in v for v in values)


class TestPoisoningKnowledge:
    def test_gray_box_value(self) -> None:
        assert PoisoningKnowledge.GRAY_BOX_SCORE_ACCESS == "gray_box_score_access"

    def test_white_box_diagnostic_only_value(self) -> None:
        assert PoisoningKnowledge.WHITE_BOX == "white_box"

    def test_exactly_two_members(self) -> None:
        assert len(PoisoningKnowledge) == 2


class TestPoisoningTargetScope:
    def test_single_client_value(self) -> None:
        assert PoisoningTargetScope.SINGLE_CLIENT == "single_client"

    def test_multi_client_value(self) -> None:
        assert PoisoningTargetScope.MULTI_CLIENT == "multi_client"

    def test_all_clients_diagnostic_only_value(self) -> None:
        assert PoisoningTargetScope.ALL_CLIENTS == "all_clients"


class TestPoisoningDefense:
    def test_none_value(self) -> None:
        assert PoisoningDefense.NONE == "none"

    def test_trimmed_calibration_value(self) -> None:
        assert PoisoningDefense.TRIMMED_CALIBRATION == "trimmed_calibration"

    def test_exactly_two_members(self) -> None:
        assert len(PoisoningDefense) == 2


class TestExperimentScale:
    def test_smoke_value(self) -> None:
        assert ExperimentScale.SMOKE == "smoke"

    def test_bounded_value(self) -> None:
        assert ExperimentScale.BOUNDED == "bounded"

    def test_full_value(self) -> None:
        assert ExperimentScale.FULL == "full"

    def test_stretch_value(self) -> None:
        assert ExperimentScale.STRETCH == "stretch"

    def test_exactly_four_members(self) -> None:
        assert len(ExperimentScale) == 4


class TestBoundedSweepFractions:
    def test_fraction_grid(self) -> None:
        assert BOUNDED_SWEEP_FRACTIONS == (0.0, 0.10, 0.20, 0.40)

    def test_four_fractions(self) -> None:
        assert len(BOUNDED_SWEEP_FRACTIONS) == 4

    def test_no_fraction_five_percent(self) -> None:
        assert 0.05 not in BOUNDED_SWEEP_FRACTIONS

    def test_zero_fraction_present(self) -> None:
        assert 0.0 in BOUNDED_SWEEP_FRACTIONS


class TestFullSweepFractions:
    def test_full_grid_adds_005(self) -> None:
        assert FULL_SWEEP_FRACTIONS == (0.0, 0.05, 0.10, 0.20, 0.40)

    def test_full_grid_is_bounded_plus_005(self) -> None:
        assert set(BOUNDED_SWEEP_FRACTIONS) | {0.05} == set(FULL_SWEEP_FRACTIONS)

    def test_full_grid_has_five_fractions(self) -> None:
        assert len(FULL_SWEEP_FRACTIONS) == 5
