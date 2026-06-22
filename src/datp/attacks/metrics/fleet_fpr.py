from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import ThresholdPairBase
from datp.core.enums import ThresholdPolicy
from datp.statistics.cv import cv

_IQR_P25: float = 25.0
_IQR_P75: float = 75.0


@dataclass(frozen=True, slots=True)
class FleetFprMetrics:
    """CV(FPR), coverage, and guard metrics for one policy."""

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


def _client_fpr(test_benign: np.ndarray, threshold: float) -> float:
    if test_benign.size == 0:
        return math.nan
    return float(np.mean(test_benign > threshold))


def compute_fleet_fpr(
    collection: ScoreCollection,
    pair: ThresholdPairBase,
    mu_flag_threshold: float | None,
) -> FleetFprMetrics:
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

    cv_fpr = cv(fpr_arr, ddof=0) if n_valid >= 2 else math.nan
    mean_fpr = float(fpr_arr.mean()) if n_valid > 0 else math.nan
    std_fpr = float(fpr_arr.std(ddof=1)) if n_valid >= 2 else math.nan
    iqr_fpr = (
        float(np.percentile(fpr_arr, _IQR_P75) - np.percentile(fpr_arr, _IQR_P25))
        if n_valid > 0
        else math.nan
    )
    max_min_gap = float(fpr_arr.max() - fpr_arr.min()) if n_valid > 0 else math.nan

    mean_is_under_lock = (
        not math.isnan(mean_fpr)
        and mu_flag_threshold is not None
        and mean_fpr < mu_flag_threshold
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
        coverage_ratio=collection.coverage_ratio,
        n_eligible=len(eligible_ids),
        n_total=len(collection.clients),
        mu_flag_triggered=mean_is_under_lock,
    )
