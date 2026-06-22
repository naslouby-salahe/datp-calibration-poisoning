from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from datp.attacks.score_containers import ClientScores
from datp.evaluation.metrics import recompute_binary_metrics


@dataclass(frozen=True, slots=True)
class VictimDownstreamMetrics:
    """Per-victim detection performance under clean and poisoned thresholds."""

    tpr_clean: float
    tpr_poisoned: float
    delta_tpr: float

    ba_clean: float
    ba_poisoned: float
    delta_ba: float

    macro_f1_clean: float
    macro_f1_poisoned: float
    delta_macro_f1: float


def _counts_from_threshold(
    test_benign: np.ndarray,
    test_attack: np.ndarray,
    threshold: float,
) -> tuple[int, int, int, int]:
    tp = int(np.sum(test_attack > threshold))
    fn = int(np.sum(test_attack <= threshold))
    fp = int(np.sum(test_benign > threshold))
    tn = int(np.sum(test_benign <= threshold))
    return tp, fp, tn, fn


def compute_victim_downstream_metrics(
    *,
    clean_threshold: float,
    poisoned_threshold: float,
    client_scores: ClientScores,
) -> VictimDownstreamMetrics:
    benign = client_scores.test_benign
    attack = client_scores.test_attack

    tp_c, fp_c, tn_c, fn_c = _counts_from_threshold(benign, attack, clean_threshold)
    tp_p, fp_p, tn_p, fn_p = _counts_from_threshold(benign, attack, poisoned_threshold)

    m_clean = recompute_binary_metrics(tp_c, fp_c, tn_c, fn_c)
    m_pois = recompute_binary_metrics(tp_p, fp_p, tn_p, fn_p)

    def _safe_delta(a: float, b: float) -> float:
        if math.isnan(a) or math.isnan(b):
            return math.nan
        return b - a

    return VictimDownstreamMetrics(
        tpr_clean=m_clean.tpr,
        tpr_poisoned=m_pois.tpr,
        delta_tpr=_safe_delta(m_clean.tpr, m_pois.tpr),
        ba_clean=m_clean.balanced_accuracy,
        ba_poisoned=m_pois.balanced_accuracy,
        delta_ba=_safe_delta(m_clean.balanced_accuracy, m_pois.balanced_accuracy),
        macro_f1_clean=m_clean.macro_f1,
        macro_f1_poisoned=m_pois.macro_f1,
        delta_macro_f1=_safe_delta(m_clean.macro_f1, m_pois.macro_f1),
    )
