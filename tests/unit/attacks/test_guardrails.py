"""Unit tests for runtime scientific guardrails."""

from __future__ import annotations

import numpy as np
import pytest

from datp.attacks.poison_enums import (
    BOUNDED_SWEEP_FRACTIONS,
    ExperimentScale,
    ThresholdPolicy,
)
from datp.attacks.guardrails import (
    GuardrailError,
    assert_fractions_in_locked_grid,
    assert_bounded_scale_requires_single_client,
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
        original[0] = 99.0 # simulated in-place mutation
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
        assert_reservoir_not_test_or_training("calibration")

    def test_benign_cal_label_passes(self) -> None:
        assert_reservoir_not_test_or_training("victim_local_benign_cal")

    def test_test_label_raises(self) -> None:
        with pytest.raises(GuardrailError, match="test"):
            assert_reservoir_not_test_or_training("test_scores")

    def test_training_label_raises(self) -> None:
        with pytest.raises(GuardrailError, match="training"):
            assert_reservoir_not_test_or_training("training_data")

    def test_train_label_raises(self) -> None:
        with pytest.raises(GuardrailError, match="train"):
            assert_reservoir_not_test_or_training("train_split")

    def test_case_insensitive_test(self) -> None:
        with pytest.raises(GuardrailError):
            assert_reservoir_not_test_or_training("TEST_SCORES")

    def test_case_insensitive_training(self) -> None:
        with pytest.raises(GuardrailError):
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
    def test_bounded_fractions_all_pass(self) -> None:
        assert_fractions_in_locked_grid(BOUNDED_SWEEP_FRACTIONS, ExperimentScale.BOUNDED)

    def test_zero_fraction_passes(self) -> None:
        assert_fractions_in_locked_grid([0.0], ExperimentScale.BOUNDED)

    def test_010_fraction_passes(self) -> None:
        assert_fractions_in_locked_grid([0.10], ExperimentScale.BOUNDED)

    def test_invalid_fraction_raises(self) -> None:
        with pytest.raises(GuardrailError, match="0.3"):
            assert_fractions_in_locked_grid([0.3], ExperimentScale.BOUNDED)

    def test_005_not_in_bounded_grid(self) -> None:
        with pytest.raises(GuardrailError, match="0.05"):
            assert_fractions_in_locked_grid([0.05], ExperimentScale.BOUNDED)

    def test_005_allowed_in_full_scale(self) -> None:
        assert_fractions_in_locked_grid([0.05], ExperimentScale.FULL)

    def test_bounded_fractions_allowed_in_full_scale(self) -> None:
        assert_fractions_in_locked_grid(list(BOUNDED_SWEEP_FRACTIONS), ExperimentScale.FULL)

    def test_empty_fractions_pass(self) -> None:
        assert_fractions_in_locked_grid([], ExperimentScale.BOUNDED)

    def test_error_message_includes_allowed_grid(self) -> None:
        with pytest.raises(GuardrailError, match="locked grid"):
            assert_fractions_in_locked_grid([0.99], ExperimentScale.BOUNDED)


class TestMvpRequiresSingleClient:
    def test_bounded_with_single_client_passes(self) -> None:
        assert_bounded_scale_requires_single_client(ExperimentScale.BOUNDED, "single_client")

    def test_bounded_with_multi_client_raises(self) -> None:
        with pytest.raises(GuardrailError, match="SINGLE_CLIENT"):
            assert_bounded_scale_requires_single_client(ExperimentScale.BOUNDED, "multi_client")

    def test_bounded_with_all_clients_raises(self) -> None:
        with pytest.raises(GuardrailError, match="SINGLE_CLIENT"):
            assert_bounded_scale_requires_single_client(
                ExperimentScale.BOUNDED, "all_clients_diagnostic_only"
            )

    def test_full_scale_multi_client_passes(self) -> None:
        # Non-bounded scales are not gated by this guardrail.
        assert_bounded_scale_requires_single_client(ExperimentScale.FULL, "multi_client")

    def test_smoke_scale_multi_client_passes(self) -> None:
        assert_bounded_scale_requires_single_client(ExperimentScale.SMOKE, "multi_client")
