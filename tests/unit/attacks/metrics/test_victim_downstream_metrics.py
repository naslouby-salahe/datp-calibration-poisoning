"""Tests verifying calculation of victim-specific downstream metrics like TPR, FPR, BA, and Macro F1."""

from __future__ import annotations

import math

import numpy as np
import pytest

from datp.attacks.metrics.metric_engine import (
    VictimDownstreamMetrics,
    compute_victim_downstream_metrics,
)
from datp.attacks.score_containers import ClientScores


def _scores(
    benign: list[float],
    attack: list[float],
    client_id: str = "c0",
) -> ClientScores:
    """Helper to build ClientScores with dummy calibration scores and configured test sets."""
    return ClientScores(
        client_id=client_id,
        cal=np.zeros(200, dtype=np.float64),
        test_benign=np.array(benign, dtype=np.float64),
        test_attack=np.array(attack, dtype=np.float64),
    )


class TestBasicComputation:
    """Tests verifying simple accuracy, TPR, FPR, and balanced accuracy calculations."""

    def test_tpr_all_attack_above_threshold(self) -> None:
        """Verify that TPR is 1.0 when all attack scores lie above the threshold."""
        scores = _scores(benign=[0.1, 0.2, 0.3], attack=[0.8, 0.9, 1.0])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )

        assert result.tpr_clean == pytest.approx(1.0)
        assert result.tpr_poisoned == pytest.approx(1.0)
        assert result.delta_tpr == pytest.approx(0.0)

    def test_fpr_no_benign_above_threshold(self) -> None:
        """Verify balanced accuracy is 1.0 when no benign scores lie above the threshold."""
        scores = _scores(benign=[0.1, 0.2, 0.3], attack=[0.8, 0.9, 1.0])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )

        assert result.ba_clean == pytest.approx(1.0)
        assert result.ba_poisoned == pytest.approx(1.0)

    def test_tpr_half_attack_above_threshold(self) -> None:
        """Verify correct calculation when exactly half of attack scores cross threshold."""
        scores = _scores(benign=[0.1, 0.6], attack=[0.4, 0.8])

        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert result.tpr_clean == pytest.approx(0.5)
        assert result.ba_clean == pytest.approx(0.5)

    def test_macro_f1_perfect_separation(self) -> None:
        """Verify macro F1 is 1.0 under perfect separation of benign and attack scores."""
        scores = _scores(benign=[0.1, 0.2], attack=[0.8, 0.9])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert result.macro_f1_clean == pytest.approx(1.0)
        assert result.macro_f1_poisoned == pytest.approx(1.0)
        assert result.delta_macro_f1 == pytest.approx(0.0)

    def test_delta_fields_are_poisoned_minus_clean(self) -> None:
        """Verify that delta_tpr represents poisoned TPR minus clean TPR."""
        scores = _scores(benign=[0.1, 0.2], attack=[0.7, 0.9])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.85,
            client_scores=scores,
        )
        expected_tpr_clean = 1.0
        expected_tpr_pois = 0.5
        assert result.tpr_clean == pytest.approx(expected_tpr_clean)
        assert result.tpr_poisoned == pytest.approx(expected_tpr_pois)
        assert result.delta_tpr == pytest.approx(expected_tpr_pois - expected_tpr_clean)

    def test_delta_ba_is_poisoned_minus_clean(self) -> None:
        """Verify that delta_ba represents poisoned Balanced Accuracy minus clean Balanced Accuracy."""
        scores = _scores(benign=[0.1, 0.2], attack=[0.7, 0.9])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.85,
            client_scores=scores,
        )

        assert result.ba_clean == pytest.approx(1.0)
        assert result.ba_poisoned == pytest.approx(0.75)
        assert result.delta_ba == pytest.approx(0.75 - 1.0)

    def test_returns_victim_downstream_metrics_instance(self) -> None:
        """Verify that compute_victim_downstream_metrics returns a VictimDownstreamMetrics model instance."""
        scores = _scores(benign=[0.1], attack=[0.9])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert isinstance(result, VictimDownstreamMetrics)


class TestThresholdDirectionInvariants:
    """Tests verifying monotonic changes in metrics when shifting threshold values."""

    def test_raising_threshold_does_not_increase_tpr(self) -> None:
        """Verify that raising the decision threshold results in a negative delta_tpr."""
        scores = _scores(benign=[0.1, 0.2, 0.3], attack=[0.6, 0.7, 0.8, 0.9])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.55,
            poisoned_threshold=0.75,
            client_scores=scores,
        )

        assert result.tpr_poisoned < result.tpr_clean
        assert result.delta_tpr < 0.0

    def test_lowering_threshold_does_not_decrease_fpr(self) -> None:
        """Verify that lowering the decision threshold decreases balanced accuracy by raising FPR."""
        scores = _scores(benign=[0.4, 0.5, 0.6, 0.7], attack=[0.5, 0.9, 1.0])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.65,
            poisoned_threshold=0.45,
            client_scores=scores,
        )

        assert result.delta_tpr > 0.0
        assert result.ba_poisoned < result.ba_clean


class TestZeroFractionInvariant:
    """Tests verifying that identical clean and poisoned thresholds yield zero metric changes."""

    def test_identical_thresholds_produce_zero_deltas(self) -> None:
        """Verify that equal thresholds produce exact zero metric delta values."""
        scores = _scores(benign=[0.1, 0.4, 0.7], attack=[0.6, 0.8, 0.95])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert result.delta_tpr == pytest.approx(0.0)
        assert result.delta_ba == pytest.approx(0.0)
        if not math.isnan(result.delta_macro_f1):
            assert result.delta_macro_f1 == pytest.approx(0.0)

    def test_zero_fraction_tpr_and_poisoned_are_equal(self) -> None:
        """Verify that clean and poisoned TPR/balanced accuracy values match when thresholds are equal."""
        scores = _scores(benign=[0.1, 0.2], attack=[0.8, 0.9])
        threshold = 0.5
        result = compute_victim_downstream_metrics(
            clean_threshold=threshold,
            poisoned_threshold=threshold,
            client_scores=scores,
        )
        assert result.tpr_clean == pytest.approx(result.tpr_poisoned)
        assert result.ba_clean == pytest.approx(result.ba_poisoned)


class TestNoMutationOfTestScores:
    """Tests verifying that original test score arrays are not mutated in-place."""

    def test_test_benign_not_mutated(self) -> None:
        """Verify that test score arrays remain unmodified after metrics extraction."""
        benign = np.array([0.1, 0.4, 0.7], dtype=np.float64)
        attack = np.array([0.8, 0.9], dtype=np.float64)
        benign_copy = benign.copy()
        attack_copy = attack.copy()
        scores = ClientScores(
            client_id="c0",
            cal=np.zeros(200),
            test_benign=benign,
            test_attack=attack,
        )
        compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.6,
            client_scores=scores,
        )
        np.testing.assert_array_equal(benign, benign_copy)
        np.testing.assert_array_equal(attack, attack_copy)


class TestEdgeCases:
    """Tests verifying behavior under empty inputs or extreme score ranges."""

    def test_empty_attack_array_returns_nan_tpr(self) -> None:
        """Verify that empty attack score arrays evaluate to NaN TPR."""
        scores = _scores(benign=[0.1, 0.2], attack=[])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert math.isnan(result.tpr_clean)
        assert math.isnan(result.tpr_poisoned)

    def test_empty_benign_array_returns_nan_ba(self) -> None:
        """Verify that empty benign score arrays evaluate to NaN balanced accuracy."""
        scores = _scores(benign=[], attack=[0.8, 0.9])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert math.isnan(result.ba_clean)
        assert math.isnan(result.ba_poisoned)

    def test_all_below_threshold_gives_zero_tpr(self) -> None:
        """Verify that TPR evaluates to 0.0 when all attack scores fall below the decision threshold."""
        scores = _scores(benign=[0.1, 0.2], attack=[0.3, 0.4])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert result.tpr_clean == pytest.approx(0.0)
        assert result.tpr_poisoned == pytest.approx(0.0)


class TestThresholdRaiseReducesDetection:
    """Tests verifying that raising thresholds specifically leads to lower True Positive Rates."""

    def test_raised_threshold_produces_non_positive_delta_tpr(self) -> None:
        """Verify that raising decision threshold yields a negative delta_tpr."""
        scores = _scores(
            benign=[0.1, 0.2, 0.3, 0.4],
            attack=[0.6, 0.7, 0.8, 0.9],
        )
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.75,
            client_scores=scores,
        )
        assert result.tpr_clean == pytest.approx(1.0)
        assert result.tpr_poisoned == pytest.approx(0.5)
        assert result.delta_tpr < 0.0

    def test_clean_and_raised_equal_threshold_zero_delta_tpr(self) -> None:
        """Verify delta_tpr is exactly zero when thresholds are identical."""
        scores = _scores(
            benign=[0.1, 0.2],
            attack=[0.6, 0.8],
        )
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert result.delta_tpr == pytest.approx(0.0)
