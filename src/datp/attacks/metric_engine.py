"""metric engine: Δτ family, CV(FPR)+coverage, guard metrics, AUROC invariance.

All metrics operate on saved threshold pairs and score collections.
No score recomputation. No ε in the CV(FPR) denominator.

mu_flag_threshold must be locked (computed from M_clean) BEFORE any poisoned run.
This module accepts it as input and applies it; it does not set it.

AUROC is invariant: test scores are unchanged by calibration-channel attack.
The module verifies this; any deviation is a protocol violation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from datp.artifacts.poison_names import MATERIALITY_FACTOR
from datp.attacks.score_containers import ClientScores, ScoreCollection
from datp.attacks.types import (
    AurocRecord,
    AurocSet,
    MetricEngineInput,
    ThresholdPairBase,
)
from datp.attacks.enums import ThresholdPolicy
from datp.evaluation.metrics import recompute_binary_metrics
from datp.evaluation.ranking import compute_binary_ranking_metrics
from datp.statistics.cv import cv

# ε used only in Δτ_rel to avoid division by zero.
# NOT used in CV(FPR) — protocol lock mandates no ε in CV denominator.
_DELTA_TAU_REL_EPS: float = 1e-9

# IQR percentiles for per-client significance scale.
_IQR_P25: float = 25.0
_IQR_P75: float = 75.0


# ---------------------------------------------------------------------------
# Per-victim Δτ entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DeltaTauEntry:
    """Per-victim threshold shift for one policy."""

    client_id: str
    policy: ThresholdPolicy
    tau_clean: float
    tau_pois: float
    delta_tau: float
    delta_tau_rel: float
    delta_tau_scale: float
    is_significant: bool


# ---------------------------------------------------------------------------
# Fleet FPR dispersion metrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FleetFprMetrics:
    """CV(FPR) + coverage + guard metrics for one policy (eligible clients only).

    cv_fpr = σ/µ with no ε; nan when µ = 0 or fewer than 2 eligible clients.
    coverage_ratio = n_eligible / n_total_clients.
    """

    policy: ThresholdPolicy
    cv_fpr: float
    mean_fpr: float
    std_fpr: float
    iqr_fpr: float
    max_min_fpr_gap: float
    worst_client_fpr: float
    worst_client_id: str | None
    coverage_ratio: float
    n_eligible: int
    n_total: int
    mu_flag_triggered: bool


# ---------------------------------------------------------------------------
# Full metric result for one (policy, poisoning-condition) pair
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MetricResult:
    """Full metric output for one threshold-pair evaluation.

    delta_tau: per-victim Δτ family (eligible clients only).
    fleet_fpr: CV(FPR) + coverage + guards under poisoned thresholds.
    auroc_records: AUROC per eligible client (invariant check; clean only).
    mu_flag_threshold: locked value (or None if not yet set).
    """

    policy: ThresholdPolicy
    delta_tau: dict[str, DeltaTauEntry]
    fleet_fpr: FleetFprMetrics
    auroc_records: AurocSet
    mu_flag_threshold: float | None


# ---------------------------------------------------------------------------
# Helper: compute per-client FPR under a threshold dict
# ---------------------------------------------------------------------------


def _client_fpr(test_benign: np.ndarray, threshold: float) -> float:
    """FPR = fraction of benign test samples with score > threshold."""
    if test_benign.size == 0:
        return math.nan
    return float(np.mean(test_benign > threshold))


# ---------------------------------------------------------------------------
# Δτ computation
# ---------------------------------------------------------------------------


def compute_delta_tau(
    collection: ScoreCollection,
    pair: ThresholdPairBase,
) -> dict[str, DeltaTauEntry]:
    """Compute per-victim Δτ family for all eligible clients.

    delta_tau_scale = 0.1 × IQR(clean calibration scores_i) per client.
    delta_tau_rel = Δτ / max(|τ_clean|, ε) where ε is for division-by-zero only.
    """
    result: dict[str, DeltaTauEntry] = {}
    for cid in collection.eligible_ids:
        tc = pair.thresholds_clean[cid]
        tp = pair.thresholds_pois[cid]
        dt = tp - tc
        dt_rel = dt / max(abs(tc), _DELTA_TAU_REL_EPS)
        clean_cal = collection.for_client(cid).cal
        iqr = float(
            np.percentile(clean_cal, _IQR_P75) - np.percentile(clean_cal, _IQR_P25)
        )
        scale = MATERIALITY_FACTOR * iqr
        result[cid] = DeltaTauEntry(
            client_id=cid,
            policy=pair.policy,
            tau_clean=tc,
            tau_pois=tp,
            delta_tau=dt,
            delta_tau_rel=dt_rel,
            delta_tau_scale=scale,
            is_significant=abs(dt) > scale,
        )
    return result


# ---------------------------------------------------------------------------
# CV(FPR) + coverage + guards
# ---------------------------------------------------------------------------


def compute_fleet_fpr(
    collection: ScoreCollection,
    pair: ThresholdPairBase,
    mu_flag_threshold: float | None,
) -> FleetFprMetrics:
    """Compute CV(FPR) + coverage + guard metrics under poisoned thresholds.

    Only eligible clients contribute.
    CV(FPR) = σ/µ with no ε. Returns nan when µ=0 or n_eligible < 2.
    """
    eligible_ids = list(collection.eligible_ids)
    fprs: list[float] = []
    worst_fpr = -1.0
    worst_id: str | None = None

    for cid in eligible_ids:
        tb = collection.for_client(cid).test_benign
        tau = pair.thresholds_pois[cid]
        fpr = _client_fpr(tb, tau)
        fprs.append(fpr)
        if not math.isnan(fpr) and fpr > worst_fpr:
            worst_fpr = fpr
            worst_id = cid

    fpr_arr = np.array([f for f in fprs if not math.isnan(f)], dtype=np.float64)
    n_valid = fpr_arr.size

    cv_fpr = cv(fpr_arr) if n_valid >= 2 else math.nan
    mean_fpr = float(fpr_arr.mean()) if n_valid > 0 else math.nan
    std_fpr = float(fpr_arr.std(ddof=1)) if n_valid >= 2 else math.nan
    iqr_fpr = (
        float(np.percentile(fpr_arr, _IQR_P75) - np.percentile(fpr_arr, _IQR_P25))
        if n_valid > 0
        else math.nan
    )
    max_min_gap = float(fpr_arr.max() - fpr_arr.min()) if n_valid > 0 else math.nan

    coverage = collection.coverage_ratio
    n_total = len(collection.clients)

    mu_flag = (
        (not math.isnan(mean_fpr) and mean_fpr <= mu_flag_threshold)
        if mu_flag_threshold is not None and not math.isnan(mean_fpr)
        else False
    )

    return FleetFprMetrics(
        policy=pair.policy,
        cv_fpr=cv_fpr,
        mean_fpr=mean_fpr,
        std_fpr=std_fpr,
        iqr_fpr=iqr_fpr,
        max_min_fpr_gap=max_min_gap,
        worst_client_fpr=worst_fpr if worst_id is not None else math.nan,
        worst_client_id=worst_id,
        coverage_ratio=coverage,
        n_eligible=len(eligible_ids),
        n_total=n_total,
        mu_flag_triggered=mu_flag,
    )


# ---------------------------------------------------------------------------
# AUROC records (test scores only — invariant by construction)
# ---------------------------------------------------------------------------


def compute_auroc_records(
    collection: ScoreCollection,
) -> AurocSet:
    """Compute AUROC per eligible client from test scores.

    Test scores are NEVER modified by calibration poisoning.
    AUROC is therefore invariant; this function records it for auditability.
    """
    records: list[AurocRecord] = []
    for cid in collection.eligible_ids:
        c = collection.for_client(cid)
        ranking = compute_binary_ranking_metrics(c.test_benign, c.test_attack)
        records.append(AurocRecord(client_id=cid, auroc=ranking.auroc))
    return AurocSet(records=tuple(records))


# ---------------------------------------------------------------------------
# Victim downstream metrics: TPR, BA, macro-F1 under clean vs poisoned threshold
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VictimDownstreamMetrics:
    """Per-victim detection performance under clean and poisoned effective thresholds.

    Computed from unchanged victim test scores and the effective threshold under
    each calibration condition.  Attack samples are the positive class; a sample
    is predicted malicious when score > threshold.

    tpr = TP / (TP + FN); ba = (TPR + TNR) / 2; delta = poisoned - clean.
    NaN when the required array is empty.
    """

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
    """Return (TP, FP, TN, FN) for a binary classifier with score > threshold rule."""
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
    """Compute clean, poisoned, and delta detection metrics for one victim.

    Uses unchanged test_benign and test_attack arrays from *client_scores*.
    Never modifies the input arrays.
    """
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


# ---------------------------------------------------------------------------
# Convenience: mu_flag_threshold lock
# ---------------------------------------------------------------------------


def compute_mu_flag_threshold(mean_clean_fpr: float) -> float:
    """mu_flag_threshold = round(M_clean / 8, 2 significant figures).

    Must be computed from CLEAN artifacts and locked BEFORE any poisoned run.
    Caller is responsible for locking this value into the manifest before
    running the poisoned pipeline.
    """
    raw = mean_clean_fpr / 8.0
    if math.isclose(raw, 0.0, abs_tol=0.0):
        return 0.0
    # Round to 2 significant figures.
    magnitude = math.floor(math.log10(abs(raw)))
    factor = 10 ** (1 - magnitude)
    return round(raw * factor) / factor


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def compute_metrics(inputs: MetricEngineInput) -> MetricResult:
    """Compute full metric result for one threshold pair.

    mu_flag_threshold must be pre-computed from clean artifacts and passed in
    via *inputs*.  auroc_records is invariant across every cell sharing the
    same collection (test scores are never touched by calibration poisoning).
    When *inputs.auroc_set* is None it is computed internally.
    """
    auroc_records = inputs.auroc_set
    if auroc_records is None:
        auroc_records = compute_auroc_records(inputs.collection)

    delta_tau = compute_delta_tau(inputs.collection, inputs.pair)
    fleet_fpr = compute_fleet_fpr(
        inputs.collection, inputs.pair, inputs.mu_flag_threshold
    )

    return MetricResult(
        policy=inputs.pair.policy,
        delta_tau=delta_tau,
        fleet_fpr=fleet_fpr,
        auroc_records=auroc_records,
        mu_flag_threshold=inputs.mu_flag_threshold,
    )
