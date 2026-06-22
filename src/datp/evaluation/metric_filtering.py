"""Calibration-Pending clients are excluded from personalized dispersion metrics."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import numpy as np


class _MetricValues(Protocol):
    fpr: float
    tpr: float
    balanced_accuracy: float
    macro_f1: float


class _ClientMetricRecord(Protocol):
    client_id: str
    metrics: _MetricValues


@dataclass(frozen=True, slots=True)
class _FilteredMetrics:
    """fpr_eligible covers all eligible clients; tpr_eligible/ba_eligible/f1_eligible additionally exclude evaluation-incomplete clients."""

    fpr_eligible: np.ndarray
    tpr_eligible: np.ndarray
    ba_eligible: np.ndarray
    f1_eligible: np.ndarray


def _collect_complete_metrics(
    cr: _ClientMetricRecord,
    incomplete_set: set[str],
    tpr_list: list[float],
    ba_list: list[float],
    f1_list: list[float],
) -> None:
    if cr.client_id in incomplete_set:
        return
    if not math.isnan(cr.metrics.tpr):
        tpr_list.append(cr.metrics.tpr)
    if not math.isnan(cr.metrics.balanced_accuracy):
        ba_list.append(cr.metrics.balanced_accuracy)
    if not math.isnan(cr.metrics.macro_f1):
        f1_list.append(cr.metrics.macro_f1)


def _filter_eligible_metrics(
    clients: Sequence[_ClientMetricRecord],
    eligible_ids: Sequence[str],
    incomplete_ids: Sequence[str] | None,
) -> _FilteredMetrics:
    eligible_set = set(eligible_ids)
    incomplete_set = set() if incomplete_ids is None else set(incomplete_ids)

    fpr_list: list[float] = []
    tpr_list: list[float] = []
    ba_list: list[float] = []
    f1_list: list[float] = []

    for cr in clients:
        if cr.client_id not in eligible_set:
            continue
        fpr_list.append(cr.metrics.fpr)
        _collect_complete_metrics(cr, incomplete_set, tpr_list, ba_list, f1_list)

    return _FilteredMetrics(
        fpr_eligible=np.array(fpr_list, dtype=np.float64),
        tpr_eligible=np.array(tpr_list, dtype=np.float64),
        ba_eligible=np.array(ba_list, dtype=np.float64),
        f1_eligible=np.array(f1_list, dtype=np.float64),
    )
