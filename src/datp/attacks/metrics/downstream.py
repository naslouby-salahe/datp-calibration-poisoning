"""Downstream classification-metric deltas for victim and non-victim clients."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import numpy as np

from datp.attacks.score_containers import ClientScores
from datp.evaluation.metrics import BinaryMetrics, recompute_binary_metrics


@dataclass(frozen=True, slots=True)
class VictimDownstreamMetrics:
    """Clean vs poisoned TPR, FPR, balanced-accuracy, macro-F1 and absolute error counts for one client."""

    tpr_clean: float
    tpr_poisoned: float
    delta_tpr: float
    fpr_clean: float
    fpr_poisoned: float
    delta_fpr: float
    ba_clean: float
    ba_poisoned: float
    delta_ba: float
    macro_f1_clean: float
    macro_f1_poisoned: float
    delta_macro_f1: float
    fp_clean: int
    fp_poisoned: int
    fn_clean: int
    fn_poisoned: int
    n_test_benign: int
    n_test_attack: int


@dataclass(frozen=True, slots=True)
class NonVictimDownstreamMetrics:
    """Fleet-aggregated downstream deltas over non-victim clients."""

    n_clients: int
    mean_tpr_clean: float
    mean_tpr_poisoned: float
    mean_delta_tpr: float
    worst_delta_tpr: float
    mean_fpr_clean: float
    mean_fpr_poisoned: float
    mean_delta_fpr: float
    worst_delta_fpr: float
    mean_delta_ba: float
    mean_delta_macro_f1: float
    delta_fp_total: int
    delta_fn_total: int


def _counts(scores: np.ndarray, threshold: float) -> int:
    return int(np.sum(scores > threshold))


def compute_victim_downstream_metrics(
    *,
    clean_threshold: float,
    poisoned_threshold: float,
    client_scores: ClientScores,
) -> VictimDownstreamMetrics:
    """Compute TPR, FPR, balanced-accuracy, macro-F1 and error-count deltas between clean and poisoned thresholds."""
    benign = client_scores.test_benign
    attack = client_scores.test_attack
    n_benign, n_attack = len(benign), len(attack)

    def _metrics_at(thresh: float) -> tuple[BinaryMetrics, int, int]:
        tp = _counts(attack, thresh)
        fp = _counts(benign, thresh)
        return (
            recompute_binary_metrics(tp, fp, n_benign - fp, n_attack - tp),
            fp,
            n_attack - tp,
        )

    m_clean, fp_clean, fn_clean = _metrics_at(clean_threshold)
    m_pois, fp_pois, fn_pois = _metrics_at(poisoned_threshold)

    return VictimDownstreamMetrics(
        tpr_clean=m_clean.tpr,
        tpr_poisoned=m_pois.tpr,
        delta_tpr=m_pois.tpr - m_clean.tpr,
        fpr_clean=m_clean.fpr,
        fpr_poisoned=m_pois.fpr,
        delta_fpr=m_pois.fpr - m_clean.fpr,
        ba_clean=m_clean.balanced_accuracy,
        ba_poisoned=m_pois.balanced_accuracy,
        delta_ba=m_pois.balanced_accuracy - m_clean.balanced_accuracy,
        macro_f1_clean=m_clean.macro_f1,
        macro_f1_poisoned=m_pois.macro_f1,
        delta_macro_f1=m_pois.macro_f1 - m_clean.macro_f1,
        fp_clean=fp_clean,
        fp_poisoned=fp_pois,
        fn_clean=fn_clean,
        fn_poisoned=fn_pois,
        n_test_benign=n_benign,
        n_test_attack=n_attack,
    )


def _finite_mean(values: Iterable[float]) -> float:
    finite = [v for v in values if math.isfinite(v)]
    return float(np.mean(finite)) if finite else math.nan


def aggregate_non_victim_metrics(
    per_client: Mapping[str, VictimDownstreamMetrics],
) -> NonVictimDownstreamMetrics:
    """Aggregate per-client downstream metrics over a set of non-victim clients."""
    items = list(per_client.values())
    d_tpr = [m.delta_tpr for m in items if math.isfinite(m.delta_tpr)]
    d_fpr = [m.delta_fpr for m in items if math.isfinite(m.delta_fpr)]
    return NonVictimDownstreamMetrics(
        n_clients=len(items),
        mean_tpr_clean=_finite_mean(m.tpr_clean for m in items),
        mean_tpr_poisoned=_finite_mean(m.tpr_poisoned for m in items),
        mean_delta_tpr=_finite_mean(d_tpr),
        worst_delta_tpr=min(d_tpr) if d_tpr else math.nan,
        mean_fpr_clean=_finite_mean(m.fpr_clean for m in items),
        mean_fpr_poisoned=_finite_mean(m.fpr_poisoned for m in items),
        mean_delta_fpr=_finite_mean(d_fpr),
        worst_delta_fpr=max(d_fpr) if d_fpr else math.nan,
        mean_delta_ba=_finite_mean(m.delta_ba for m in items),
        mean_delta_macro_f1=_finite_mean(m.delta_macro_f1 for m in items),
        delta_fp_total=sum(m.fp_poisoned - m.fp_clean for m in items),
        delta_fn_total=sum(m.fn_poisoned - m.fn_clean for m in items),
    )


def compute_non_victim_downstream(
    *,
    thresholds: Mapping[str, tuple[float, float]],
    scores_by_client: Mapping[str, ClientScores],
    victim_id: str,
) -> NonVictimDownstreamMetrics:
    """Compute downstream metrics for every non-victim client given (clean, poisoned) thresholds."""
    return aggregate_non_victim_metrics(
        {
            cid: compute_victim_downstream_metrics(
                clean_threshold=clean,
                poisoned_threshold=pois,
                client_scores=scores_by_client[cid],
            )
            for cid, (clean, pois) in thresholds.items()
            if cid != victim_id
        }
    )
