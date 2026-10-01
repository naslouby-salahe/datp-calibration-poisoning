"""Tests for absolute error counts and non-victim downstream aggregation."""

from __future__ import annotations

import math

import numpy as np
import pytest

from datp.attacks.metrics.downstream import (
    aggregate_non_victim_metrics,
    compute_non_victim_downstream,
    compute_victim_downstream_metrics,
)
from datp.attacks.score_containers import ClientScores


def _scores(client_id: str, benign: list[float], attack: list[float]) -> ClientScores:
    return ClientScores(
        client_id=client_id,
        cal=np.zeros(200, dtype=np.float64),
        test_benign=np.array(benign, dtype=np.float64),
        test_attack=np.array(attack, dtype=np.float64),
    )


class TestAbsoluteCounts:
    """Absolute false-positive and missed-detection counts."""

    def test_counts_move_with_threshold(self) -> None:
        """Raising the threshold removes false positives and adds missed detections."""
        scores = _scores("c0", [0.1, 0.4, 0.6, 0.9], [0.5, 0.7, 0.8, 1.0])
        m = compute_victim_downstream_metrics(
            clean_threshold=0.3, poisoned_threshold=0.65, client_scores=scores
        )
        assert (m.fp_clean, m.fp_poisoned) == (3, 1)
        assert (m.fn_clean, m.fn_poisoned) == (0, 1)
        assert m.n_test_benign == 4
        assert m.n_test_attack == 4

    def test_fpr_delta_matches_counts(self) -> None:
        """Delta FPR equals the change in false-positive count over benign samples."""
        scores = _scores("c0", [0.1, 0.4, 0.6, 0.9], [0.5, 0.7, 0.8, 1.0])
        m = compute_victim_downstream_metrics(
            clean_threshold=0.3, poisoned_threshold=0.65, client_scores=scores
        )
        assert m.delta_fpr == pytest.approx((m.fp_poisoned - m.fp_clean) / 4)


class TestNonVictimAggregation:
    """Fleet aggregation over non-victim clients."""

    def _fleet(self) -> dict[str, ClientScores]:
        return {
            "victim": _scores("victim", [0.1, 0.9], [0.5, 0.8]),
            "a": _scores("a", [0.1, 0.2, 0.7, 0.9], [0.5, 0.6, 0.8, 0.95]),
            "b": _scores("b", [0.1, 0.2, 0.3, 0.4], [0.35, 0.45, 0.8, 0.9]),
        }

    def test_victim_is_excluded(self) -> None:
        """The victim never contributes to the non-victim aggregate."""
        fleet = self._fleet()
        result = compute_non_victim_downstream(
            thresholds={cid: (0.3, 0.65) for cid in fleet},
            scores_by_client=fleet,
            victim_id="victim",
        )
        assert result.n_clients == 2

    def test_totals_are_sums_of_client_deltas(self) -> None:
        """Total error-count deltas equal the sum over non-victim clients."""
        fleet = self._fleet()
        per_client = {
            cid: compute_victim_downstream_metrics(
                clean_threshold=0.3, poisoned_threshold=0.65, client_scores=fleet[cid]
            )
            for cid in ("a", "b")
        }
        agg = aggregate_non_victim_metrics(per_client)
        assert agg.delta_fn_total == sum(
            m.fn_poisoned - m.fn_clean for m in per_client.values()
        )
        assert agg.delta_fp_total == sum(
            m.fp_poisoned - m.fp_clean for m in per_client.values()
        )
        assert agg.worst_delta_tpr == min(m.delta_tpr for m in per_client.values())
        assert agg.worst_delta_fpr == max(m.delta_fpr for m in per_client.values())

    def test_unchanged_thresholds_give_zero_deltas(self) -> None:
        """Identical clean and poisoned thresholds produce no downstream change."""
        fleet = self._fleet()
        result = compute_non_victim_downstream(
            thresholds={cid: (0.5, 0.5) for cid in fleet},
            scores_by_client=fleet,
            victim_id="victim",
        )
        assert result.mean_delta_tpr == pytest.approx(0.0)
        assert result.mean_delta_fpr == pytest.approx(0.0)
        assert result.delta_fp_total == 0
        assert result.delta_fn_total == 0

    def test_empty_aggregate_is_nan(self) -> None:
        """No non-victim clients yields NaN means and zero totals."""
        agg = aggregate_non_victim_metrics({})
        assert agg.n_clients == 0
        assert math.isnan(agg.mean_delta_tpr)
        assert agg.delta_fp_total == 0
