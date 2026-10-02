from __future__ import annotations

from datp.types import (
    ClientId,
    FalsePositiveRate,
    PoisonFraction,
    SampleCount,
    ScoreValue,
    ScoreVector,
    Threshold,
)


import math
from dataclasses import dataclass

import numpy as np

from datp.attacks.enums import AttackerObjective
from datp.attacks.metrics.downstream import compute_victim_downstream_metrics
from datp.attacks.metrics.metric_engine import MetricResult
from datp.attacks.score_containers import ScoreCollection
from datp.core.enums import ThresholdPolicy


@dataclass(frozen=True, slots=True)
class BlastRadiusRecord:

    policy: ThresholdPolicy
    victim_id: ClientId | None
    n_significant: SampleCount
    n_eligible: SampleCount
    blast_fraction: PoisonFraction


@dataclass(frozen=True, slots=True)
class SpilloverRecord:

    policy: ThresholdPolicy
    victim_id: ClientId
    spillover_client_ids: tuple[ClientId, ...]
    n_spillover: SampleCount
    n_non_victims: SampleCount


def compute_blast_radius(
    result: MetricResult, *, victim_id: ClientId | None = None
) -> BlastRadiusRecord:
    entries = result.delta_tau
    n_sig = sum(e.is_significant for cid, e in entries.items() if cid != victim_id)
    n_elig = len(entries) - (1 if victim_id in entries else 0)

    return BlastRadiusRecord(
        policy=result.policy,
        victim_id=victim_id,
        n_significant=n_sig,
        n_eligible=n_elig,
        blast_fraction=n_sig / n_elig if n_elig else 0.0,
    )


def compute_spillover(
    result: MetricResult,
    *,
    collection: ScoreCollection,
    victim_id: ClientId,
    objective: AttackerObjective,
) -> SpilloverRecord:
    entries = result.delta_tau
    non_victim_ids = tuple(cid for cid in entries if cid != victim_id)
    spill = tuple(
        sorted(
            cid
            for cid in non_victim_ids
            if _has_downstream_degradation(
                collection=collection,
                result=result,
                client_id=cid,
                objective=objective,
            )
        )
    )

    return SpilloverRecord(
        policy=result.policy,
        victim_id=victim_id,
        spillover_client_ids=spill,
        n_spillover=len(spill),
        n_non_victims=len(non_victim_ids),
    )


def _has_downstream_degradation(
    *,
    collection: ScoreCollection,
    result: MetricResult,
    client_id: ClientId,
    objective: AttackerObjective,
) -> bool:
    entry = result.delta_tau[client_id]
    client_scores = collection.clients[client_id]

    if objective == AttackerObjective.THRESHOLD_RAISE:
        metrics = compute_victim_downstream_metrics(
            clean_threshold=entry.tau_clean,
            poisoned_threshold=entry.tau_pois,
            client_scores=client_scores,
        )
        return (
            metrics.delta_tpr < 0.0
            or metrics.delta_ba < 0.0
            or metrics.delta_macro_f1 < 0.0
        )

    clean_fpr = _fpr(client_scores.test_benign, entry.tau_clean)
    poisoned_fpr = _fpr(client_scores.test_benign, entry.tau_pois)
    return poisoned_fpr > clean_fpr


def _fpr(test_benign: ScoreVector, threshold: Threshold) -> FalsePositiveRate:
    if test_benign.size == 0:
        return math.nan
    return float(np.mean(test_benign > threshold))


def duplicate_rate(values: ScoreVector) -> ScoreValue:
    return 1.0 - len(np.unique(values)) / values.size if values.size else math.nan


def tau_bound_utilization(
    *,
    clean_cal: ScoreVector,
    tau_clean: Threshold,
    tau_pois: Threshold,
    objective: AttackerObjective,
) -> Threshold:
    if objective == AttackerObjective.THRESHOLD_RAISE:
        reachable = float(clean_cal.max()) - tau_clean
        shift = tau_pois - tau_clean
    else:
        reachable = tau_clean - float(clean_cal.min())
        shift = tau_clean - tau_pois
    return shift / reachable if reachable > 0.0 else math.nan
