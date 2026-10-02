
from __future__ import annotations

from dataclasses import dataclass

from datp.attacks.metrics.auroc import compute_auroc_records
from datp.attacks.metrics.delta_tau import DeltaTauEntry, compute_delta_tau
from datp.attacks.metrics.downstream import (
    VictimDownstreamMetrics,
    compute_victim_downstream_metrics,
)
from datp.attacks.metrics.fleet_fpr import FleetFprMetrics, compute_fleet_fpr
from datp.attacks.metrics.mu_flag import compute_mu_flag_threshold
from datp.attacks.types import AurocSet, MetricEngineInput
from datp.core.enums import ThresholdPolicy
from datp.types import (
    ClientId,
    Threshold,
)

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

    policy: ThresholdPolicy
    delta_tau: dict[ClientId, DeltaTauEntry]
    fleet_fpr: FleetFprMetrics
    auroc_records: AurocSet
    mu_flag_threshold: Threshold | None


def compute_metrics(inputs: MetricEngineInput) -> MetricResult:
    return MetricResult(
        policy=inputs.pair.policy,
        delta_tau=compute_delta_tau(inputs.collection, inputs.pair),
        fleet_fpr=compute_fleet_fpr(
            inputs.collection, inputs.pair, inputs.mu_flag_threshold
        ),
        auroc_records=inputs.auroc_set or compute_auroc_records(inputs.collection),
        mu_flag_threshold=inputs.mu_flag_threshold,
    )
