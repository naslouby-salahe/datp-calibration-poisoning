"""Attack diagnostics: ASR, blast radius, spillover.

Pure functions over MetricResult objects. No new scoring or thresholding.

Definitions:
  ASR (Attack Success Rate): fraction of victim instances where |Δτ| > δ_τ,i
    in the intended direction (THRESHOLD_RAISE → Δτ > 0; THRESHOLD_LOWER → Δτ < 0).
  Blast radius: number of clients with |Δτ| > δ_τ,i per single victim/cell.
    B1: fleet-wide (all eligible clients affected by global shift).
    B2: victim-local (only the victim's threshold changes).
    B4: cluster-local (cluster-mates are affected via intra-cluster aggregation).
  Spillover: threshold changes on non-victims due to policy propagation.
    B1: global propagation → all clients experience tau_global shift.
    B4: cluster spillover → co-cluster non-victims experience Δτ_agg.
    B2: no spillover by construction (each client's threshold is local).
"""

from __future__ import annotations

from dataclasses import dataclass

from datp.attacks.metric_engine import MetricResult
from datp.core.poison_enums import AttackerObjective, ThresholdPolicy


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
    n_significant = 0
    n_total = len(entries)

    for entry in entries.values():
        if objective == AttackerObjective.THRESHOLD_RAISE:
            if entry.delta_tau > entry.delta_tau_scale:
                n_significant += 1
        else:
            if entry.delta_tau < -entry.delta_tau_scale:
                n_significant += 1

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
    """Compute blast radius: number of eligible clients with significant |Δτ|.

    victim_id is optional metadata only; it does not filter the count.
    B1: global → blast radius counts all eligible clients whose threshold shifted.
    B2: local → blast radius is typically 1 (only the victim).
    B4: cluster-local → counts cluster-mates with significant agg spillover.
    """
    entries = result.delta_tau
    n_significant = sum(1 for e in entries.values() if e.is_significant)
    n_eligible = len(entries)
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
    B2: no spillover expected (each client's threshold is local to their cal).
    B1: all non-victims can experience spillover via tau_global shift.
    B4: cluster-mates of the victim can experience agg spillover.
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
