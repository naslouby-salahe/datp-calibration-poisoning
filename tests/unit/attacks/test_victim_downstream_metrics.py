"""Unit tests for victim downstream metrics (TPR, FPR, TNR, BA, macro F1).

Label polarity: attack samples are positive (malicious). A sample is predicted
malicious when score > threshold.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from datp.attacks.metric_engine import (
    VictimDownstreamMetrics,
    compute_victim_downstream_metrics,
)
from datp.attacks.score_containers import ClientScores


def _scores(
    benign: list[float],
    attack: list[float],
    client_id: str = "c0",
) -> ClientScores:
    return ClientScores(
        client_id=client_id,
        cal=np.zeros(200, dtype=np.float64),  # placeholder, not used by downstream
        test_benign=np.array(benign, dtype=np.float64),
        test_attack=np.array(attack, dtype=np.float64),
    )


# ---------------------------------------------------------------------------
# Deterministic correctness on small arrays
# ---------------------------------------------------------------------------


class TestBasicComputation:
    """Deterministic values on small toy arrays."""

    def test_tpr_all_attack_above_threshold(self) -> None:
        scores = _scores(benign=[0.1, 0.2, 0.3], attack=[0.8, 0.9, 1.0])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        # All attack scores > 0.5 → TPR = 1.0
        assert result.tpr_clean == pytest.approx(1.0)
        assert result.tpr_poisoned == pytest.approx(1.0)
        assert result.delta_tpr == pytest.approx(0.0)

    def test_fpr_no_benign_above_threshold(self) -> None:
        scores = _scores(benign=[0.1, 0.2, 0.3], attack=[0.8, 0.9, 1.0])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        # No benign scores > 0.5 → TNR = 1.0, BA = (TPR + TNR) / 2 = 1.0
        assert result.ba_clean == pytest.approx(1.0)
        assert result.ba_poisoned == pytest.approx(1.0)

    def test_tpr_half_attack_above_threshold(self) -> None:
        scores = _scores(benign=[0.1, 0.6], attack=[0.4, 0.8])
        # threshold 0.5 → attack scores: 0.4 < 0.5 (miss), 0.8 > 0.5 (hit)
        # TPR = 1/2 = 0.5
        # benign: 0.1 < 0.5 (TN), 0.6 > 0.5 (FP) → FPR = 1/2 = 0.5, TNR = 0.5
        # BA = (0.5 + 0.5) / 2 = 0.5
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert result.tpr_clean == pytest.approx(0.5)
        assert result.ba_clean == pytest.approx(0.5)

    def test_macro_f1_perfect_separation(self) -> None:
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
        # clean threshold: 0.5 → TPR_clean = 1.0 (both attack above 0.5)
        # poisoned threshold: 0.85 → TPR_poisoned = 0.5 (only 0.9 above 0.85)
        scores = _scores(benign=[0.1, 0.2], attack=[0.7, 0.9])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.85,
            client_scores=scores,
        )
        expected_tpr_clean = 1.0  # 0.7 > 0.5, 0.9 > 0.5
        expected_tpr_pois = 0.5  # only 0.9 > 0.85
        assert result.tpr_clean == pytest.approx(expected_tpr_clean)
        assert result.tpr_poisoned == pytest.approx(expected_tpr_pois)
        assert result.delta_tpr == pytest.approx(expected_tpr_pois - expected_tpr_clean)

    def test_delta_ba_is_poisoned_minus_clean(self) -> None:
        scores = _scores(benign=[0.1, 0.2], attack=[0.7, 0.9])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.85,
            client_scores=scores,
        )
        # clean: TPR=1.0, TNR=1.0 (no benign > 0.5) → BA=1.0
        # poisoned: TPR=0.5, TNR=1.0 (no benign > 0.85) → BA=0.75
        assert result.ba_clean == pytest.approx(1.0)
        assert result.ba_poisoned == pytest.approx(0.75)
        assert result.delta_ba == pytest.approx(0.75 - 1.0)

    def test_returns_victim_downstream_metrics_instance(self) -> None:
        scores = _scores(benign=[0.1], attack=[0.9])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert isinstance(result, VictimDownstreamMetrics)


# ---------------------------------------------------------------------------
# Threshold direction invariants
# ---------------------------------------------------------------------------


class TestThresholdDirectionInvariants:
    """When threshold strictly increases, TPR cannot increase (for fixed scores)."""

    def test_raising_threshold_does_not_increase_tpr(self) -> None:
        # Strict: attack scores span a range so raising threshold strictly lowers hits.
        # benign all below; attack: [0.6, 0.7, 0.8, 0.9]
        scores = _scores(benign=[0.1, 0.2, 0.3], attack=[0.6, 0.7, 0.8, 0.9])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.55,  # 4/4 attack hits
            poisoned_threshold=0.75,  # 2/4 attack hits (only 0.8, 0.9)
            client_scores=scores,
        )
        # TPR must decrease (strictly, no equality here)
        assert result.tpr_poisoned < result.tpr_clean
        assert result.delta_tpr < 0.0

    def test_lowering_threshold_does_not_decrease_fpr(self) -> None:
        # benign: [0.4, 0.5, 0.6, 0.7]; attack: [0.5, 0.9, 1.0]
        # attack[0]=0.5 is between the two thresholds; the others are above both.
        # clean threshold=0.65: attack above → [0.9, 1.0] → TPR_clean = 2/3
        # poisoned threshold=0.45: attack above → [0.5, 0.9, 1.0] → TPR_pois = 1.0
        # benign > 0.65 → [0.7] → FPR_clean = 1/4 = 0.25, TNR_clean = 0.75
        # benign > 0.45 → [0.5, 0.6, 0.7] → FPR_pois = 3/4 = 0.75, TNR_pois = 0.25
        # BA_clean = (2/3 + 0.75) / 2 ≈ 0.708; BA_pois = (1.0 + 0.25) / 2 = 0.625
        scores = _scores(benign=[0.4, 0.5, 0.6, 0.7], attack=[0.5, 0.9, 1.0])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.65,
            poisoned_threshold=0.45,
            client_scores=scores,
        )
        # Lowering threshold → more attack hits → TPR strictly increases
        assert result.delta_tpr > 0.0
        # Despite TPR gain, the large TNR drop means BA decreases
        assert result.ba_poisoned < result.ba_clean


# ---------------------------------------------------------------------------
# Zero-fraction / identical-threshold invariant
# ---------------------------------------------------------------------------


class TestZeroFractionInvariant:
    """When clean and poisoned thresholds are identical, all deltas must be zero."""

    def test_identical_thresholds_produce_zero_deltas(self) -> None:
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
        scores = _scores(benign=[0.1, 0.2], attack=[0.8, 0.9])
        threshold = 0.5
        result = compute_victim_downstream_metrics(
            clean_threshold=threshold,
            poisoned_threshold=threshold,
            client_scores=scores,
        )
        assert result.tpr_clean == pytest.approx(result.tpr_poisoned)
        assert result.ba_clean == pytest.approx(result.ba_poisoned)


# ---------------------------------------------------------------------------
# No mutation of test scores
# ---------------------------------------------------------------------------


class TestNoMutationOfTestScores:
    def test_test_benign_not_mutated(self) -> None:
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


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_attack_array_returns_nan_tpr(self) -> None:
        scores = _scores(benign=[0.1, 0.2], attack=[])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert math.isnan(result.tpr_clean)
        assert math.isnan(result.tpr_poisoned)

    def test_empty_benign_array_returns_nan_ba(self) -> None:
        scores = _scores(benign=[], attack=[0.8, 0.9])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert math.isnan(result.ba_clean)
        assert math.isnan(result.ba_poisoned)

    def test_all_below_threshold_gives_zero_tpr(self) -> None:
        scores = _scores(benign=[0.1, 0.2], attack=[0.3, 0.4])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert result.tpr_clean == pytest.approx(0.0)
        assert result.tpr_poisoned == pytest.approx(0.0)
