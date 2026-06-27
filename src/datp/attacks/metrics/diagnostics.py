"""Blast-radius and spillover diagnostics for poisoning impact assessment."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp.attacks.enums import AttackerObjective
from datp.attacks.metrics.downstream import compute_victim_downstream_metrics
from datp.attacks.metrics.metric_engine import MetricResult
from datp.attacks.score_containers import ScoreCollection
from datp.core.enums import ThresholdPolicy


@dataclass(frozen=True, slots=True)
class BlastRadiusRecord:
    """Proportion of non-victim eligible clients with significant delta-tau."""

    policy: ThresholdPolicy
    victim_id: str | None
    n_significant: int
    n_eligible: int
    blast_fraction: float


@dataclass(frozen=True, slots=True)
class SpilloverRecord:
    """Non-victim clients whose thresholds shift due to calibration poisoning."""

    policy: ThresholdPolicy
    victim_id: str
    spillover_client_ids: tuple[str, ...]
    n_spillover: int
    n_non_victims: int


def compute_blast_radius(
    result: MetricResult, *, victim_id: str | None = None
) -> BlastRadiusRecord:
    """Count how many non-victim clients show significant delta-tau."""
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
    victim_id: str,
    objective: AttackerObjective,
) -> SpilloverRecord:
    """Identify non-victim clients whose downstream metrics degraded under poisoning."""
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
    client_id: str,
    objective: AttackerObjective,
) -> bool:
    """Check if a non-victim client's TPR, BA, or macro-F1 degraded."""
    entry = result.delta_tau[client_id]
    client_scores = collection.for_client(client_id)

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


def _fpr(test_benign: np.ndarray, threshold: float) -> float:
    """Compute false-positive rate at a given threshold."""
    if test_benign.size == 0:
        return float("nan")
    return float(np.mean(test_benign > threshold))
