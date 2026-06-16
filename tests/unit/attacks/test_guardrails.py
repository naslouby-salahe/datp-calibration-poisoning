"""Unit tests for CP2 runtime scientific guardrails."""

from __future__ import annotations

import numpy as np
import pytest

from datp.attacks.poison_enums import (
    CP2_MVP_FRACTIONS,
    ExperimentScale,
    ThresholdPolicy,
)
from datp.attacks.guardrails import (
    Cp2GuardrailError,
    assert_fractions_in_locked_grid,
    assert_mvp_requires_single_client,
    assert_no_inplace_mutation,
    assert_policy_not_b3,
    assert_reservoir_not_test_or_training,
)


class TestNoInplaceMutation:
    def test_identical_arrays_pass(self) -> None:
        arr = np.array([1.0, 2.0, 3.0])
        copy = arr.copy()
        assert_no_inplace_mutation(copy, arr)

    def test_mutated_array_raises(self) -> None:
        original = np.array([1.0, 2.0, 3.0])
        original_copy = original.copy()
        original[0] = 99.0  # simulated in-place mutation
        with pytest.raises(Cp2GuardrailError, match="mutated in place"):
            assert_no_inplace_mutation(original_copy, original)

    def test_label_appears_in_error(self) -> None:
        before = np.array([1.0])
        after = np.array([2.0])
        with pytest.raises(Cp2GuardrailError, match="threshold_scores"):
            assert_no_inplace_mutation(before, after, label="threshold_scores")

    def test_empty_arrays_pass(self) -> None:
        assert_no_inplace_mutation(np.array([]), np.array([]))


class TestReservoirNotTestOrTraining:
    def test_calibration_label_passes(self) -> None:
        assert_reservoir_not_test_or_training("calibration")

    def test_benign_cal_label_passes(self) -> None:
        assert_reservoir_not_test_or_training("victim_local_benign_cal")

    def test_test_label_raises(self) -> None:
        with pytest.raises(Cp2GuardrailError, match="test"):
            assert_reservoir_not_test_or_training("test_scores")

    def test_training_label_raises(self) -> None:
        with pytest.raises(Cp2GuardrailError, match="training"):
            assert_reservoir_not_test_or_training("training_data")

    def test_train_label_raises(self) -> None:
        with pytest.raises(Cp2GuardrailError, match="train"):
            assert_reservoir_not_test_or_training("train_split")

    def test_case_insensitive_test(self) -> None:
        with pytest.raises(Cp2GuardrailError):
            assert_reservoir_not_test_or_training("TEST_SCORES")

    def test_case_insensitive_training(self) -> None:
        with pytest.raises(Cp2GuardrailError):
            assert_reservoir_not_test_or_training("TRAINING")


class TestPolicyNotB3:
    def test_b1_global_passes(self) -> None:
        assert_policy_not_b3(ThresholdPolicy.B1_GLOBAL)

    def test_b2_personalized_passes(self) -> None:
        assert_policy_not_b3(ThresholdPolicy.B2_PERSONALIZED)

    def test_b4_cluster_passes(self) -> None:
        assert_policy_not_b3(ThresholdPolicy.B4_CLUSTER)

    def test_b3_enum_cannot_be_created(self) -> None:
        # ThresholdPolicy cannot represent B3 — assert no "b3" value exists.
        assert all("b3" not in v for v in ThresholdPolicy)


class TestFractionsInLockedGrid:
    def test_mvp_fractions_all_pass(self) -> None:
        assert_fractions_in_locked_grid(CP2_MVP_FRACTIONS, ExperimentScale.MVP)

    def test_zero_fraction_passes(self) -> None:
        assert_fractions_in_locked_grid([0.0], ExperimentScale.MVP)

    def test_010_fraction_passes(self) -> None:
        assert_fractions_in_locked_grid([0.10], ExperimentScale.MVP)

    def test_invalid_fraction_raises(self) -> None:
        with pytest.raises(Cp2GuardrailError, match="0.3"):
            assert_fractions_in_locked_grid([0.3], ExperimentScale.MVP)

    def test_005_not_in_mvp_grid(self) -> None:
        with pytest.raises(Cp2GuardrailError, match="0.05"):
            assert_fractions_in_locked_grid([0.05], ExperimentScale.MVP)

    def test_005_allowed_in_full_scale(self) -> None:
        assert_fractions_in_locked_grid([0.05], ExperimentScale.FULL)

    def test_mvp_fractions_allowed_in_full_scale(self) -> None:
        assert_fractions_in_locked_grid(list(CP2_MVP_FRACTIONS), ExperimentScale.FULL)

    def test_empty_fractions_pass(self) -> None:
        assert_fractions_in_locked_grid([], ExperimentScale.MVP)

    def test_error_message_includes_allowed_grid(self) -> None:
        with pytest.raises(Cp2GuardrailError, match="locked grid"):
            assert_fractions_in_locked_grid([0.99], ExperimentScale.MVP)


class TestMvpRequiresSingleClient:
    def test_mvp_with_single_client_passes(self) -> None:
        assert_mvp_requires_single_client(ExperimentScale.MVP, "single_client")

    def test_mvp_with_multi_client_raises(self) -> None:
        with pytest.raises(Cp2GuardrailError, match="SINGLE_CLIENT"):
            assert_mvp_requires_single_client(ExperimentScale.MVP, "multi_client")

    def test_mvp_with_all_clients_raises(self) -> None:
        with pytest.raises(Cp2GuardrailError, match="SINGLE_CLIENT"):
            assert_mvp_requires_single_client(
                ExperimentScale.MVP, "all_clients_diagnostic_only"
            )

    def test_full_scale_multi_client_passes(self) -> None:
        # Non-MVP scales are not gated by this guardrail.
        assert_mvp_requires_single_client(ExperimentScale.FULL, "multi_client")

    def test_smoke_scale_multi_client_passes(self) -> None:
        assert_mvp_requires_single_client(ExperimentScale.SMOKE, "multi_client")
