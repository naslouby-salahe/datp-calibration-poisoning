"""Real-data bounded sweep cell runner.

Orchestrates the real-data bounded matrix on ``REGIME_A_NBAIOT`` using the same
tested primitives as the synthetic smoke harness
(``datp.attacks.cell_runner``). The key difference from the smoke harness:
``mu_flag_threshold`` is locked once per training seed from the *clean B1*
eligible-client mean FPR and passed in explicitly, then reused unmodified
across every policy/source/fraction/victim/poisoning-seed cell for that
training seed — it is never recomputed from a non-B1 policy's clean pair.
"""

from __future__ import annotations

from dataclasses import dataclass

from datp.artifacts.poison_names import THRESHOLD_QUANTILE
from datp.attacks.cell_runner import PolicyPair, inject_single_victim, recompute_pair
from datp.attacks.metric_engine import (
    AurocRecord,
    MetricResult,
    compute_auroc_records,
    compute_metrics,
    compute_mu_flag_threshold,
)
from datp.attacks.poison_enums import PoisoningSourceStrategy, ThresholdPolicy
from datp.attacks.score_containers import ScoreCollection


def lock_mu_flag_threshold(
    collection: ScoreCollection, *, q: float = THRESHOLD_QUANTILE
) -> float:
    """Lock ``mu_flag_threshold`` from the clean B1 eligible-client mean FPR.

    Must be called once per training seed, before any poisoned run for that
    seed, and the returned value reused unmodified across every policy/cell
    for that seed (CLAUDE.md: "mu_flag_threshold locked before poisoned
    runs"; the lock is always B1-derived, regardless of which policy a given
    cell evaluates).
    """
    clean_cal = {
        cid: collection.clients[cid].cal.copy() for cid in collection.eligible_ids
    }
    clean_b1_pair = recompute_pair(
        collection, clean_cal, ThresholdPolicy.B1_GLOBAL, q=q
    )
    clean_metrics = compute_metrics(collection, clean_b1_pair, None)
    return compute_mu_flag_threshold(clean_metrics.fleet_fpr.mean_fpr)


@dataclass(frozen=True, slots=True)
class SweepCellResult:
    """Clean-vs-poisoned result for one (policy, source, fraction, victim, seed) cell."""

    policy: ThresholdPolicy
    victim_id: str
    source: PoisoningSourceStrategy
    fraction: float
    training_seed: int
    poisoning_seed: int
    clean_pair: PolicyPair
    poisoned_pair: PolicyPair
    clean_metrics: MetricResult
    poisoned_metrics: MetricResult


def run_sweep_cell(
    collection: ScoreCollection,
    *,
    victim_id: str,
    policy: ThresholdPolicy,
    source: PoisoningSourceStrategy,
    fraction: float,
    training_seed: int,
    poisoning_seed: int,
    mu_flag_threshold: float,
    scope_idx: int = 0,
    q: float = THRESHOLD_QUANTILE,
    b4_seed: int = 0,
    auroc_records: dict[str, AurocRecord] | None = None,
) -> SweepCellResult:
    """Run one bounded cell using a pre-locked ``mu_flag_threshold``.

    The clean baseline pair is still recomputed per (training_seed, policy)
    here (cheap; correctness-first) — it defines this policy's own Δτ
    baseline, which is distinct from the B1-derived ``mu_flag_threshold``
    passed in. ``auroc_records`` is invariant across every cell sharing this
    collection (test scores are never touched); callers sweeping many cells
    for one training seed should precompute it once via
    ``compute_auroc_records`` and pass it here — otherwise it is recomputed
    on every call, which is correct but wasteful at BOUNDED scale.
    """
    if auroc_records is None:
        auroc_records = compute_auroc_records(collection)

    clean_outcome = inject_single_victim(
        collection,
        victim_id=victim_id,
        source=source,
        fraction=0.0,
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        scope_idx=scope_idx,
    )
    clean_pair = recompute_pair(
        collection, clean_outcome.poisoned_cal, policy, q=q, seed=b4_seed
    )
    clean_metrics = compute_metrics(
        collection, clean_pair, None, auroc_records=auroc_records
    )

    outcome = inject_single_victim(
        collection,
        victim_id=victim_id,
        source=source,
        fraction=fraction,
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        scope_idx=scope_idx,
    )
    poisoned_pair = recompute_pair(
        collection, outcome.poisoned_cal, policy, q=q, seed=b4_seed
    )
    poisoned_metrics = compute_metrics(
        collection, poisoned_pair, mu_flag_threshold, auroc_records=auroc_records
    )

    return SweepCellResult(
        policy=policy,
        victim_id=victim_id,
        source=source,
        fraction=fraction,
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        clean_pair=clean_pair,
        poisoned_pair=poisoned_pair,
        clean_metrics=clean_metrics,
        poisoned_metrics=poisoned_metrics,
    )
