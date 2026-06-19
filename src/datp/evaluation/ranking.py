from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


@dataclass(frozen=True, slots=True)
class BinaryRankingMetrics:
    auroc: float | None
    pr_auc: float | None


def compute_binary_ranking_metrics(
    benign_scores: np.ndarray, attack_scores: np.ndarray
) -> BinaryRankingMetrics:
    """Returns None for AUROC/PR-AUC when either score array is empty."""
    either_array_is_none = benign_scores is None or attack_scores is None
    benign_is_empty = (not either_array_is_none) and benign_scores.size == 0
    attack_is_empty = (not either_array_is_none) and attack_scores.size == 0
    if either_array_is_none or benign_is_empty or attack_is_empty:
        return BinaryRankingMetrics(auroc=None, pr_auc=None)

    labels = np.concatenate([np.zeros(benign_scores.size), np.ones(attack_scores.size)])
    scores = np.concatenate([benign_scores, attack_scores])
    return BinaryRankingMetrics(
        auroc=float(roc_auc_score(labels, scores)),
        pr_auc=float(average_precision_score(labels, scores)),
    )
