"""Unit tests for runtime scientific guardrails."""

from __future__ import annotations

import numpy as np
import pytest

from datp.attacks.guardrails import (
    GuardrailError,
    assert_bounded_scale_requires_single_client,
    assert_fractions_in_locked_grid,
    assert_no_inplace_mutation,
    assert_valid_policy,
    assert_reservoir_not_test_or_training,
    assert_valid_source_objective_pair,
)
from datp.attacks.constants import NBAIOT_MAIN_SWEEP_FRACTIONS
from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)
from datp.core.enums import ScoringStage
from datp.config.stages import ExperimentStage


class TestNoInplaceMutation:
    def test_identical_arrays_pass(self) -> None:
        arr = np.array([1.0, 2.0, 3.0])
        copy = arr.copy()
        assert_no_inplace_mutation(copy, arr)

    def test_mutated_array_raises(self) -> None:
        original = np.array([1.0, 2.0, 3.0])
        original_copy = original.copy()
        original[0] = 99.0  # simulated in-place mutation
        with pytest.raises(GuardrailError, match="mutated in place"):
            assert_no_inplace_mutation(original_copy, original)

    def test_label_appears_in_error(self) -> None:
        before = np.array([1.0])
        after = np.array([2.0])
        with pytest.raises(GuardrailError, match="threshold_scores"):
            assert_no_inplace_mutation(before, after, label="threshold_scores")

    def test_empty_arrays_pass(self) -> None:
        assert_no_inplace_mutation(np.array([]), np.array([]))


class TestReservoirNotTestOrTraining:
    def test_calibration_label_passes(self) -> None:
        assert_reservoir_not_test_or_training(ScoringStage.CAL)

    def test_benign_cal_label_passes(self) -> None:
        assert_reservoir_not_test_or_training(ScoringStage.CAL)

    def test_test_label_raises(self) -> None:
        with pytest.raises(GuardrailError, match="test"):
            assert_reservoir_not_test_or_training(ScoringStage.TEST_BENIGN)


class TestAssertValidPolicy:
    def test_global_threshold_passes(self) -> None:
        assert_valid_policy(ThresholdPolicy.GLOBAL_THRESHOLD)

    def test_local_threshold_passes(self) -> None:
        assert_valid_policy(ThresholdPolicy.LOCAL_THRESHOLD)

    def test_cluster_threshold_passes(self) -> None:
        assert_valid_policy(ThresholdPolicy.CLUSTER_THRESHOLD)


class TestFractionsInLockedGrid:
    def test_bounded_fractions_all_pass(self) -> None:
        assert_fractions_in_locked_grid(
            NBAIOT_MAIN_SWEEP_FRACTIONS, ExperimentStage.NBAIOT_MAIN
        )

    def test_zero_fraction_passes(self) -> None:
        assert_fractions_in_locked_grid([0.0], ExperimentStage.NBAIOT_MAIN)

    def test_010_fraction_passes(self) -> None:
        assert_fractions_in_locked_grid([0.10], ExperimentStage.NBAIOT_MAIN)

    def test_invalid_fraction_raises(self) -> None:
        with pytest.raises(GuardrailError, match="0.3"):
            assert_fractions_in_locked_grid([0.3], ExperimentStage.NBAIOT_MAIN)

    def test_005_not_in_bounded_grid(self) -> None:
        with pytest.raises(GuardrailError, match="0.05"):
            assert_fractions_in_locked_grid([0.05], ExperimentStage.NBAIOT_MAIN)

    def test_005_allowed_in_full_scale(self) -> None:
        assert_fractions_in_locked_grid([0.05], ExperimentStage.NBAIOT_FULL_OPTIONAL)

    def test_bounded_fractions_allowed_in_full_scale(self) -> None:
        assert_fractions_in_locked_grid(
            list(NBAIOT_MAIN_SWEEP_FRACTIONS), ExperimentStage.NBAIOT_FULL_OPTIONAL
        )

    def test_empty_fractions_pass(self) -> None:
        assert_fractions_in_locked_grid([], ExperimentStage.NBAIOT_MAIN)

    def test_error_message_includes_allowed_grid(self) -> None:
        with pytest.raises(GuardrailError, match="locked grid"):
            assert_fractions_in_locked_grid([0.99], ExperimentStage.NBAIOT_MAIN)


class TestBoundedScaleRequiresSingleClient:
    def test_bounded_with_single_client_passes(self) -> None:
        assert_bounded_scale_requires_single_client(
            ExperimentStage.NBAIOT_MAIN, PoisoningTargetScope.SINGLE_CLIENT
        )

    def test_bounded_with_multi_client_raises(self) -> None:
        with pytest.raises(GuardrailError, match="SINGLE_CLIENT"):
            assert_bounded_scale_requires_single_client(
                ExperimentStage.NBAIOT_MAIN, PoisoningTargetScope.MULTI_CLIENT
            )

    def test_bounded_with_all_clients_diagnostic_only_raises(self) -> None:
        with pytest.raises(GuardrailError, match="SINGLE_CLIENT"):
            assert_bounded_scale_requires_single_client(
                ExperimentStage.NBAIOT_MAIN,
                PoisoningTargetScope.ALL_CLIENTS_DIAGNOSTIC_ONLY,
            )

    def test_full_scale_multi_client_passes(self) -> None:
        assert_bounded_scale_requires_single_client(
            ExperimentStage.NBAIOT_FULL_OPTIONAL, PoisoningTargetScope.MULTI_CLIENT
        )

    def test_smoke_scale_multi_client_passes(self) -> None:
        assert_bounded_scale_requires_single_client(
            ExperimentStage.SYNTHETIC_SMOKE, PoisoningTargetScope.MULTI_CLIENT
        )


class TestValidSourceObjectivePair:
    def test_high_score_with_raise_passes(self) -> None:
        assert_valid_source_objective_pair(
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            AttackerObjective.THRESHOLD_RAISE,
        )

    def test_low_score_with_lower_passes(self) -> None:
        assert_valid_source_objective_pair(
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
            AttackerObjective.THRESHOLD_LOWER,
        )

    def test_random_benign_with_raise_passes(self) -> None:
        assert_valid_source_objective_pair(
            PoisoningSourceStrategy.RANDOM_BENIGN,
            AttackerObjective.THRESHOLD_RAISE,
        )

    def test_random_benign_with_lower_passes(self) -> None:
        assert_valid_source_objective_pair(
            PoisoningSourceStrategy.RANDOM_BENIGN,
            AttackerObjective.THRESHOLD_LOWER,
        )

    def test_high_score_with_lower_raises(self) -> None:
        with pytest.raises(GuardrailError, match="THRESHOLD_RAISE"):
            assert_valid_source_objective_pair(
                PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
                AttackerObjective.THRESHOLD_LOWER,
            )

    def test_low_score_with_raise_raises(self) -> None:
        with pytest.raises(GuardrailError, match="THRESHOLD_LOWER"):
            assert_valid_source_objective_pair(
                PoisoningSourceStrategy.LOW_SCORE_BENIGN,
                AttackerObjective.THRESHOLD_RAISE,
            )

    def test_error_message_includes_source_and_objective(self) -> None:
        with pytest.raises(GuardrailError, match="HIGH_SCORE_BENIGN"):
            assert_valid_source_objective_pair(
                PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
                AttackerObjective.THRESHOLD_LOWER,
            )
