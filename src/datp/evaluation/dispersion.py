from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from datp.core.errors import fmt
from datp.evaluation.client_records import ClientEvaluationRecord
from datp.evaluation.metric_filtering import _filter_eligible_metrics
from datp.statistics.cv import cv

_MODULE = "evaluation.dispersion"


@dataclass(frozen=True, slots=True)
class DispersionMetrics:
    """Aggregate dispersion statistics across eligible clients."""

    cv_fpr: float
    mean_fpr: float
    std_fpr: float
    iqr_fpr: float
    cv_tpr: float
    iqr_tpr: float
    max_min_fpr_gap: float
    worst_client_fpr: float
    worst_client_id: str | None
    eligible_count: int
    client_count: int
    worst_ba: float
    p10_macro_f1: float


def aggregate_dispersion(
    clients: tuple[ClientEvaluationRecord, ...],
    eligible_ids: tuple[str, ...],
    incomplete_ids: tuple[str, ...],
) -> DispersionMetrics:
    fm = _filter_eligible_metrics(clients, eligible_ids, incomplete_ids)

    fpr_arr = fm.fpr_eligible
    if np.isnan(fpr_arr).any():
        eligible_set = set(eligible_ids)
        bad_ids = [
            cr.client_id
            for cr in clients
            if cr.client_id in eligible_set and math.isnan(cr.metrics.fpr)
        ]
        raise ValueError(
            fmt(
                _MODULE,
                "Undefined eligible-client FPR cannot enter dispersion metrics",
                "every eligible client has at least one benign test row",
                ", ".join(bad_ids) or "unknown",
            )
        )

    tpr_arr = fm.tpr_eligible
    ba_arr = fm.ba_eligible
    f1_arr = fm.f1_eligible

    cv_fpr = cv(fpr_arr, ddof=0)
    mean_fpr = float(fpr_arr.mean()) if fpr_arr.size > 0 else math.nan
    std_fpr = float(fpr_arr.std(ddof=1)) if fpr_arr.size >= 2 else math.nan
    iqr_fpr = (
        float(np.percentile(fpr_arr, 75) - np.percentile(fpr_arr, 25))
        if fpr_arr.size >= 2
        else math.nan
    )
    if fpr_arr.size > 0:
        worst_idx = int(np.argmax(fpr_arr))
        worst_client_fpr = float(fpr_arr[worst_idx])
        eligible_list = [c for c in clients if c.client_id in set(eligible_ids)]
        worst_client_id: str | None = (
            eligible_list[worst_idx].client_id
            if worst_idx < len(eligible_list)
            else None
        )
        max_min_fpr_gap = float(fpr_arr.max() - fpr_arr.min())
    else:
        worst_client_fpr = math.nan
        worst_client_id = None
        max_min_fpr_gap = math.nan

    cv_tpr = cv(tpr_arr, ddof=0)
    iqr_tpr = (
        float(np.percentile(tpr_arr, 75) - np.percentile(tpr_arr, 25))
        if tpr_arr.size >= 2
        else math.nan
    )
    worst_ba = float(ba_arr.min()) if ba_arr.size > 0 else math.nan
    p10_macro_f1 = float(np.percentile(f1_arr, 10)) if f1_arr.size > 0 else math.nan

    return DispersionMetrics(
        cv_fpr=cv_fpr,
        mean_fpr=mean_fpr,
        std_fpr=std_fpr,
        iqr_fpr=iqr_fpr,
        cv_tpr=cv_tpr,
        iqr_tpr=iqr_tpr,
        max_min_fpr_gap=max_min_fpr_gap,
        worst_client_fpr=worst_client_fpr,
        worst_client_id=worst_client_id,
        eligible_count=fpr_arr.size,
        client_count=len(clients),
        worst_ba=worst_ba,
        p10_macro_f1=p10_macro_f1,
    )
