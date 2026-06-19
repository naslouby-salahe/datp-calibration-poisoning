from __future__ import annotations

import numpy as np
import pytest

from datp.evaluation.ranking import BinaryRankingMetrics, compute_binary_ranking_metrics


class TestBinaryRankingMetrics:
    def test_is_frozen_dataclass(self) -> None:
        m = BinaryRankingMetrics(auroc=0.9, pr_auc=0.8)
        with pytest.raises(Exception):
            m.auroc = 0.5  # type: ignore[misc]

    def test_construct_with_values(self) -> None:
        m = BinaryRankingMetrics(auroc=0.95, pr_auc=0.87)
        assert m.auroc == pytest.approx(0.95)
        assert m.pr_auc == pytest.approx(0.87)

    def test_construct_with_none(self) -> None:
        m = BinaryRankingMetrics(auroc=None, pr_auc=None)
        assert m.auroc is None
        assert m.pr_auc is None


class TestComputeBinaryRankingMetrics:
    def test_perfect_separation(self) -> None:
        benign = np.array([0.1, 0.2, 0.15], dtype=np.float64)
        attack = np.array([0.9, 0.95, 0.85], dtype=np.float64)
        result = compute_binary_ranking_metrics(benign, attack)
        assert result.auroc == pytest.approx(1.0)
        assert result.pr_auc == pytest.approx(1.0)

    def test_random_scores_near_chance(self) -> None:
        rng = np.random.default_rng(42)
        benign = rng.normal(0.5, 0.1, size=500).astype(np.float64)
        attack = rng.normal(0.5, 0.1, size=500).astype(np.float64)
        result = compute_binary_ranking_metrics(benign, attack)
        assert result.auroc is not None
        assert result.pr_auc is not None
        assert 0.3 < result.auroc < 0.7
        assert 0.3 < result.pr_auc < 0.7

    def test_moderate_separation(self) -> None:
        rng = np.random.default_rng(42)
        benign = rng.normal(0.3, 0.1, size=200).astype(np.float64)
        attack = rng.normal(0.7, 0.1, size=200).astype(np.float64)
        result = compute_binary_ranking_metrics(benign, attack)
        assert result.auroc is not None
        assert result.pr_auc is not None
        assert result.auroc > 0.8
        assert result.pr_auc > 0.8

    def test_empty_benign_returns_none(self) -> None:
        result = compute_binary_ranking_metrics(
            np.empty(0, dtype=np.float64), np.array([0.5, 0.6])
        )
        assert result.auroc is None
        assert result.pr_auc is None

    def test_empty_attack_returns_none(self) -> None:
        result = compute_binary_ranking_metrics(
            np.array([0.1, 0.2]), np.empty(0, dtype=np.float64)
        )
        assert result.auroc is None
        assert result.pr_auc is None

    def test_none_benign_returns_none(self) -> None:
        result = compute_binary_ranking_metrics(
            None,  # pyright: ignore[reportArgumentType]
            np.array([0.5, 0.6]),  # type: ignore[arg-type]
        )
        assert result.auroc is None
        assert result.pr_auc is None

    def test_none_attack_returns_none(self) -> None:
        result = compute_binary_ranking_metrics(
            np.array([0.1, 0.2]),
            None,  # type: ignore[arg-type]
        )
        assert result.auroc is None
        assert result.pr_auc is None

    def test_single_sample_each(self) -> None:
        result = compute_binary_ranking_metrics(np.array([0.3]), np.array([0.7]))
        assert result.auroc == pytest.approx(1.0)
        assert result.pr_auc == pytest.approx(1.0)

    def test_single_sample_tied(self) -> None:
        result = compute_binary_ranking_metrics(np.array([0.5]), np.array([0.5]))
        assert result.auroc is not None
        assert result.pr_auc is not None
        assert 0.0 <= result.auroc <= 1.0
        assert 0.0 <= result.pr_auc <= 1.0

    def test_inverted_scores_low_auroc(self) -> None:
        benign = np.array([0.9, 0.95, 0.85], dtype=np.float64)
        attack = np.array([0.1, 0.2, 0.15], dtype=np.float64)
        result = compute_binary_ranking_metrics(benign, attack)
        # AUROC = 0.0 for perfectly inverted ranking;
        # PR-AUC baseline equals class fraction and will not dip to 0.
        assert result.auroc == pytest.approx(0.0)
        assert result.pr_auc is not None
        assert 0.3 <= result.pr_auc <= 0.5
