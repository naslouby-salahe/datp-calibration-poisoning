"""Fleet-level FPR statistics under poisoned thresholds."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import ThresholdPairBase
from datp.core.enums import ThresholdPolicy
from datp.statistics.aggregates import compute_fpr_fleet_stats


@dataclass(frozen=True, slots=True)
class FleetFprMetrics:
    """Fleet-level FPR statistics including CV, dispersion, coverage, and mu-flag status."""

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


def compute_fleet_fpr(
    collection: ScoreCollection,
    pair: ThresholdPairBase,
    mu_flag_threshold: float | None,
) -> FleetFprMetrics:
    """Compute fleet-level FPR statistics across all eligible clients."""
    eligible = list(collection.eligible_ids)

    client_fprs = [
        (cid, float(np.mean(tb > pair.thresholds_pois[cid])))
        for cid in eligible
        if (tb := collection.for_client(cid).test_benign).size > 0
    ]

    n_valid = len(client_fprs)
    fpr_arr = np.array([f for _, f in client_fprs]) if n_valid else np.array([])
    stats = compute_fpr_fleet_stats(fpr_arr)
    worst_id: str | None = (
        max(client_fprs, key=lambda x: x[1])[0] if client_fprs else None
    )

    return FleetFprMetrics(
        policy=pair.policy,
        cv_fpr=stats.cv,
        mean_fpr=stats.mean,
        std_fpr=stats.std,
        iqr_fpr=stats.iqr,
        max_min_fpr_gap=stats.max_min_gap,
        worst_client_fpr=stats.worst_value,
        worst_client_id=worst_id,
        coverage_ratio=collection.coverage_ratio,
        n_eligible=len(eligible),
        n_total=len(collection.clients),
        mu_flag_triggered=bool(
            n_valid and mu_flag_threshold is not None and stats.mean < mu_flag_threshold
        ),
    )
