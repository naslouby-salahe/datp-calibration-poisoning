"""Metric engine orchestration for calibration-channel poisoning."""

from __future__ import annotations

from dataclasses import dataclass

from datp.attacks.auroc import compute_auroc_records
from datp.attacks.delta_tau import DeltaTauEntry, compute_delta_tau
from datp.attacks.downstream import (
    VictimDownstreamMetrics,
    compute_victim_downstream_metrics,
)
from datp.attacks.fleet_fpr import FleetFprMetrics, compute_fleet_fpr
from datp.attacks.mu_flag import compute_mu_flag_threshold
from datp.attacks.types import AurocSet, MetricInput
from datp.core.enums import ThresholdPolicy

__all__ = [
    "DeltaTauEntry",
    "FleetFprMetrics",
    "MetricResult",
    "VictimDownstreamMetrics",
    "compute_auroc_records",
    "compute_delta_tau",
    "compute_fleet_fpr",
    "compute_metrics",
    "compute_mu_flag_threshold",
    "compute_victim_downstream_metrics",
]


@dataclass(frozen=True, slots=True)
class MetricResult:
    """Full metric output for one threshold-pair evaluation."""

    policy: ThresholdPolicy
    delta_tau: dict[str, DeltaTauEntry]
    fleet_fpr: FleetFprMetrics
    auroc_records: AurocSet
    mu_flag_threshold: float | None


def compute_metrics(inputs: MetricInput) -> MetricResult:
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
