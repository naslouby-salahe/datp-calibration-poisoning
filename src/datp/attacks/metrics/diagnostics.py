"""Attack diagnostics: ASR, blast radius, spillover.

Pure functions over MetricResult objects. No new scoring or thresholding.

Definitions:
  ASR (Attack Success Rate): fraction of victim instances where |Δτ| > δ_τ,i
    in the intended direction (THRESHOLD_RAISE → Δτ > 0; THRESHOLD_LOWER → Δτ < 0).
  Blast radius: number of clients with |Δτ| > δ_τ,i per single victim/cell.
    GLOBAL_THRESHOLD: fleet-wide (all eligible clients affected by global shift).
    LOCAL_THRESHOLD: victim-local (only the victim's threshold changes).
    CLUSTER_THRESHOLD: cluster-local (cluster-mates are affected via intra-cluster aggregation).
  Spillover: threshold changes on non-victims due to policy propagation.
    GLOBAL_THRESHOLD: global propagation → all clients experience tau_global shift.
    CLUSTER_THRESHOLD: cluster spillover → co-cluster non-victims experience Δτ_agg.
    LOCAL_THRESHOLD: no spillover by construction (each client's threshold is local).
"""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from dataclasses import dataclass

from datp.attacks.metrics.metric_engine import MetricResult
from datp.attacks.enums import AttackerObjective


@dataclass(frozen=True, slots=True)
class AsrRecord:
    """Attack Success Rate for one (policy, victim, condition) cell."""

    policy: ThresholdPolicy
    victim_id: str
    objective: AttackerObjective
    n_significant: int
    n_total: int
    asr: float


@dataclass(frozen=True, slots=True)
class BlastRadiusRecord:
    """Blast radius: number of clients with |Δτ| > δ_τ,i per cell."""

    policy: ThresholdPolicy
    victim_id: str | None
    n_significant: int
    n_eligible: int
    blast_fraction: float


@dataclass(frozen=True, slots=True)
class SpilloverRecord:
    """Spillover: non-victim clients with |Δτ| > δ_τ,i."""

    policy: ThresholdPolicy
    victim_id: str
    spillover_client_ids: tuple[str, ...]
    n_spillover: int
    n_non_victims: int


def _is_directionally_significant(
    delta_tau: float, delta_tau_scale: float, objective: AttackerObjective
) -> bool:
    if objective == AttackerObjective.THRESHOLD_RAISE:
        return delta_tau >= delta_tau_scale
    return delta_tau <= -delta_tau_scale


def compute_asr(
    result: MetricResult,
    *,
    victim_id: str,
    objective: AttackerObjective,
) -> AsrRecord:
    """Compute ASR for one victim: fraction of eligible clients with significant,
    directional Δτ.

    For THRESHOLD_RAISE: count clients with Δτ > delta_tau_scale.
    For THRESHOLD_LOWER: count clients with Δτ < -delta_tau_scale.
    """
    entries = result.delta_tau
    n_total = len(entries)
    n_significant = sum(
        _is_directionally_significant(entry.delta_tau, entry.delta_tau_scale, objective)
        for entry in entries.values()
    )

    asr = n_significant / n_total if n_total > 0 else 0.0
    return AsrRecord(
        policy=result.policy,
        victim_id=victim_id,
        objective=objective,
        n_significant=n_significant,
        n_total=n_total,
        asr=asr,
    )


def compute_blast_radius(
    result: MetricResult,
    *,
    victim_id: str | None = None,
) -> BlastRadiusRecord:
    """Compute blast radius: number of non-victim eligible clients with material |Δτ|.

    Excludes the victim client when victim_id is provided (roadmap §10.6).
    GLOBAL_THRESHOLD: blast radius counts all non-victim eligible clients whose threshold shifted.
    LOCAL_THRESHOLD: blast radius is 0 (victim excluded; no other clients affected).
    CLUSTER_THRESHOLD: blast radius counts non-victim cluster-mates with significant |Δτ|.
    """
    entries = result.delta_tau
    n_significant = sum(
        1 for cid, e in entries.items() if cid != victim_id and e.is_significant
    )
    n_eligible = len(entries) - (1 if victim_id is not None and victim_id in entries else 0)
    blast_fraction = n_significant / n_eligible if n_eligible > 0 else 0.0
    return BlastRadiusRecord(
        policy=result.policy,
        victim_id=victim_id,
        n_significant=n_significant,
        n_eligible=n_eligible,
        blast_fraction=blast_fraction,
    )


def compute_spillover(
    result: MetricResult,
    *,
    victim_id: str,
) -> SpilloverRecord:
    """Compute spillover: non-victim clients with significant |Δτ|.

    Spillover is mechanistic (policy propagation), not an independence violation.
    LOCAL_THRESHOLD: no spillover expected (each client's threshold is local to their cal).
    GLOBAL_THRESHOLD: all non-victims can experience spillover via tau_global shift.
    CLUSTER_THRESHOLD: cluster-mates of the victim can experience agg spillover.
    """
    entries = result.delta_tau
    spillover_ids = [
        cid
        for cid, entry in entries.items()
        if cid != victim_id and entry.is_significant
    ]
    n_non_victims = len(entries) - (1 if victim_id in entries else 0)
    return SpilloverRecord(
        policy=result.policy,
        victim_id=victim_id,
        spillover_client_ids=tuple(sorted(spillover_ids)),
        n_spillover=len(spillover_ids),
        n_non_victims=n_non_victims,
    )
