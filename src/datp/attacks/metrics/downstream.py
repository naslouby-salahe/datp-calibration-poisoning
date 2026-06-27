"""Downstream classification-metric deltas for victim clients."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp.attacks.score_containers import ClientScores
from datp.evaluation.metrics import recompute_binary_metrics


@dataclass(frozen=True, slots=True)
class VictimDownstreamMetrics:
    """Clean vs poisoned TPR, balanced-accuracy, and macro-F1 deltas for one victim."""

    tpr_clean: float
    tpr_poisoned: float
    delta_tpr: float
    ba_clean: float
    ba_poisoned: float
    delta_ba: float
    macro_f1_clean: float
    macro_f1_poisoned: float
    delta_macro_f1: float


def compute_victim_downstream_metrics(
    *,
    clean_threshold: float,
    poisoned_threshold: float,
    client_scores: ClientScores,
) -> VictimDownstreamMetrics:
    """Compute TPR, balanced-accuracy, and macro-F1 deltas between clean and poisoned thresholds."""
    benign = client_scores.test_benign
    attack = client_scores.test_attack
    n_benign, n_attack = len(benign), len(attack)

    def _metrics_at(thresh: float):
        tp = int(np.sum(attack > thresh))
        fp = int(np.sum(benign > thresh))
        return recompute_binary_metrics(tp, fp, n_benign - fp, n_attack - tp)

    m_clean = _metrics_at(clean_threshold)
    m_pois = _metrics_at(poisoned_threshold)

    return VictimDownstreamMetrics(
        tpr_clean=m_clean.tpr,
        tpr_poisoned=m_pois.tpr,
        delta_tpr=m_pois.tpr - m_clean.tpr,
        ba_clean=m_clean.balanced_accuracy,
        ba_poisoned=m_pois.balanced_accuracy,
        delta_ba=m_pois.balanced_accuracy - m_clean.balanced_accuracy,
        macro_f1_clean=m_clean.macro_f1,
        macro_f1_poisoned=m_pois.macro_f1,
        delta_macro_f1=m_pois.macro_f1 - m_clean.macro_f1,
    )
