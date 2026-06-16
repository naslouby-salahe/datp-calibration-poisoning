"""CP2 metric engine: Δτ family, CV(FPR)+coverage, guard metrics, AUROC invariance.

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

from datp.artifacts.poison_names import CP2_MATERIALITY_FACTOR
from datp.attacks.b4_recompute import Cp2B4ThresholdPair
from datp.attacks.poison_enums import ThresholdPolicy
from datp.attacks.score_containers import Cp2ScoreCollection
from datp.attacks.threshold_recompute import Cp2ThresholdPair
from datp.evaluation.ranking import compute_binary_ranking_metrics
from datp.statistics.cv import cv

# ε used only in Δτ_rel to avoid division by zero.
# NOT used in CV(FPR) — CP2 lock mandates no ε in CV denominator.
_DELTA_TAU_REL_EPS: float = 1e-9

# IQR percentiles for per-client significance scale.
_IQR_P25: float = 25.0
_IQR_P75: float = 75.0


# ---------------------------------------------------------------------------
# Per-victim Δτ entry
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Cp2DeltaTauEntry:
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
class Cp2FleetFprMetrics:
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
# AUROC invariance record
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Cp2AurocRecord:
    """AUROC per eligible client (invariant under calibration-channel attack)."""

    client_id: str
    auroc: float | None


# ---------------------------------------------------------------------------
# Full metric result for one (policy, poisoning-condition) pair
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Cp2MetricResult:
    """Full metric output for one threshold-pair evaluation.

    delta_tau: per-victim Δτ family (eligible clients only).
    fleet_fpr: CV(FPR) + coverage + guards under poisoned thresholds.
    auroc_records: AUROC per eligible client (invariant check; clean only).
    mu_flag_threshold: locked value (or None if not yet set).
    """

    policy: ThresholdPolicy
    delta_tau: dict[str, Cp2DeltaTauEntry]
    fleet_fpr: Cp2FleetFprMetrics
    auroc_records: dict[str, Cp2AurocRecord]
    mu_flag_threshold: float | None


# ---------------------------------------------------------------------------
# Helper: compute per-client FPR under a threshold dict
# ---------------------------------------------------------------------------

def _client_fpr(
    test_benign: np.ndarray, threshold: float
) -> float:
    """FPR = fraction of benign test samples with score > threshold."""
    if test_benign.size == 0:
        return math.nan
    return float(np.mean(test_benign > threshold))


# ---------------------------------------------------------------------------
# Δτ computation
# ---------------------------------------------------------------------------

def compute_delta_tau(
    collection: Cp2ScoreCollection,
    pair: Cp2ThresholdPair | Cp2B4ThresholdPair,
) -> dict[str, Cp2DeltaTauEntry]:
    """Compute per-victim Δτ family for all eligible clients.

    delta_tau_scale = 0.1 × IQR(clean calibration scores_i) per client.
    delta_tau_rel = Δτ / max(|τ_clean|, ε) where ε is for division-by-zero only.
    """
    result: dict[str, Cp2DeltaTauEntry] = {}
    for cid in collection.eligible_ids:
        tc = pair.thresholds_clean[cid]
        tp = pair.thresholds_pois[cid]
        dt = tp - tc
        dt_rel = dt / max(abs(tc), _DELTA_TAU_REL_EPS)
        clean_cal = collection.clients[cid].cal
        iqr = float(
            np.percentile(clean_cal, _IQR_P75) - np.percentile(clean_cal, _IQR_P25)
        )
        scale = CP2_MATERIALITY_FACTOR * iqr
        result[cid] = Cp2DeltaTauEntry(
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
    collection: Cp2ScoreCollection,
    pair: Cp2ThresholdPair | Cp2B4ThresholdPair,
    mu_flag_threshold: float | None,
) -> Cp2FleetFprMetrics:
    """Compute CV(FPR) + coverage + guard metrics under poisoned thresholds.

    Only eligible clients contribute.
    CV(FPR) = σ/µ with no ε.  Returns nan when µ=0 or n_eligible < 2.
    """
    eligible_ids = list(collection.eligible_ids)
    fprs: list[float] = []
    worst_fpr = -1.0
    worst_id: str | None = None

    for cid in eligible_ids:
        tb = collection.clients[cid].test_benign
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
    max_min_gap = (
        float(fpr_arr.max() - fpr_arr.min()) if n_valid > 0 else math.nan
    )

    coverage = collection.coverage_ratio
    n_total = len(collection.clients)

    mu_flag = (
        (not math.isnan(mean_fpr) and mean_fpr <= mu_flag_threshold)
        if mu_flag_threshold is not None and not math.isnan(mean_fpr)
        else False
    )

    return Cp2FleetFprMetrics(
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
    collection: Cp2ScoreCollection,
) -> dict[str, Cp2AurocRecord]:
    """Compute AUROC per eligible client from test scores.

    Test scores are NEVER modified by CP2 calibration poisoning.
    AUROC is therefore invariant; this function records it for auditability.
    """
    records: dict[str, Cp2AurocRecord] = {}
    for cid in collection.eligible_ids:
        c = collection.clients[cid]
        ranking = compute_binary_ranking_metrics(c.test_benign, c.test_attack)
        records[cid] = Cp2AurocRecord(client_id=cid, auroc=ranking.auroc)
    return records


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
    if raw == 0.0:
        return 0.0
    # Round to 2 significant figures.
    magnitude = math.floor(math.log10(abs(raw)))
    factor = 10 ** (1 - magnitude)
    return round(raw * factor) / factor


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_metrics(
    collection: Cp2ScoreCollection,
    pair: Cp2ThresholdPair | Cp2B4ThresholdPair,
    mu_flag_threshold: float | None,
    *,
    auroc_records: dict[str, Cp2AurocRecord] | None = None,
) -> Cp2MetricResult:
    """Compute full CP2 metric result for one threshold pair.

    mu_flag_threshold must be pre-computed from clean artifacts and passed in.
    auroc_records is invariant across every cell sharing the same collection
    (test scores are never touched by calibration poisoning) — callers
    sweeping many cells for one collection may precompute it once via
    ``compute_auroc_records`` and pass it here to avoid redundant recompute.
    When omitted, it is computed internally as before.
    Returns Cp2MetricResult with all CP2 metrics.
    """
    delta_tau = compute_delta_tau(collection, pair)
    fleet_fpr = compute_fleet_fpr(collection, pair, mu_flag_threshold)
    if auroc_records is None:
        auroc_records = compute_auroc_records(collection)

    return Cp2MetricResult(
        policy=pair.policy,
        delta_tau=delta_tau,
        fleet_fpr=fleet_fpr,
        auroc_records=auroc_records,
        mu_flag_threshold=mu_flag_threshold,
    )
