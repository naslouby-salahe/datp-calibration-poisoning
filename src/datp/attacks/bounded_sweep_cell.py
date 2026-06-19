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
from datp.attacks.cell_runner import (
    InjectionSpec,
    PolicyPair,
    inject_single_victim,
    recompute_pair,
)
from datp.attacks.bounded_sweep_matrix import SweepCellSpec
from datp.attacks.metric_engine import (
    MetricResult,
    compute_auroc_records,
    compute_metrics,
    compute_mu_flag_threshold,
)
from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import AurocSet, MetricEngineInput, PoisonedCalibrationSet
from datp.attacks.enums import PoisoningSourceStrategy, ThresholdPolicy
from datp.core.seeds import SeedPair


def lock_mu_flag_threshold(
    collection: ScoreCollection, *, q: float = THRESHOLD_QUANTILE
) -> float:
    """Lock ``mu_flag_threshold`` from the clean B1 eligible-client mean FPR.

    Must be called once per training seed, before any poisoned run for that
    seed, and the returned value reused unmodified across every policy/cell
    for that seed. The lock is always B1-derived, regardless of which policy a
    given cell evaluates.
    """
    clean_cal = {
        cid: collection.clients[cid].cal.copy() for cid in collection.eligible_ids
    }
    clean_b1_pair = recompute_pair(
        collection,
        PoisonedCalibrationSet.from_mapping(clean_cal),
        ThresholdPolicy.B1_GLOBAL,
        q=q,
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
    seed_pair: SeedPair
    thresholds_under_clean: PolicyPair
    thresholds_under_poisoning: PolicyPair
    clean_metrics: MetricResult
    poisoned_metrics: MetricResult

    @property
    def training_seed(self) -> int:
        return self.seed_pair.training_seed

    @property
    def poisoning_seed(self) -> int:
        return self.seed_pair.poisoning_seed


def run_sweep_cell(
    spec: SweepCellSpec | ScoreCollection,
    collection: ScoreCollection | None = None,
    mu_flag_threshold: float | None = None,
    auroc_set: AurocSet | None = None,
    *,
    victim_id: str | None = None,
    policy: ThresholdPolicy | None = None,
    source: PoisoningSourceStrategy | None = None,
    fraction: float | None = None,
    training_seed: int | None = None,
    poisoning_seed: int | None = None,
    scope_idx: int = 0,
    q: float = THRESHOLD_QUANTILE,
    b4_seed: int = 0,
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
    if isinstance(spec, ScoreCollection):
        collection = spec
        if (
            victim_id is None
            or policy is None
            or source is None
            or fraction is None
            or training_seed is None
            or poisoning_seed is None
        ):
            raise TypeError("legacy run_sweep_cell calls require victim/policy/source/fraction/seeds")
        spec = SweepCellSpec(
            seed_pair=SeedPair(
                training_seed=training_seed,
                poisoning_seed=poisoning_seed,
            ),
            victim_id=victim_id,
            policy=policy,
            source=source,
            fraction=fraction,
        )
    if collection is None:
        raise TypeError("collection is required")
    if mu_flag_threshold is None:
        raise TypeError("mu_flag_threshold is required")
    if auroc_set is None:
        auroc_set = compute_auroc_records(collection)

    clean_outcome = inject_single_victim(
        collection,
        victim_id=spec.victim_id,
        spec=InjectionSpec(
            source=spec.source,
            fraction=0.0,
            seed_pair=spec.seed_pair,
            scope_idx=scope_idx,
        ),
    )
    clean_pair = recompute_pair(
        collection, clean_outcome.poisoned_cal_set, spec.policy, q=q, seed=b4_seed
    )
    clean_metrics = compute_metrics(
        MetricEngineInput(
            collection=collection,
            pair=clean_pair,
            mu_flag_threshold=None,
            auroc_set=auroc_set,
        )
    )

    outcome = inject_single_victim(
        collection,
        victim_id=spec.victim_id,
        spec=InjectionSpec(
            source=spec.source,
            fraction=spec.fraction,
            seed_pair=spec.seed_pair,
            scope_idx=scope_idx,
        ),
    )
    poisoned_pair = recompute_pair(
        collection, outcome.poisoned_cal_set, spec.policy, q=q, seed=b4_seed
    )
    poisoned_metrics = compute_metrics(
        MetricEngineInput(
            collection=collection,
            pair=poisoned_pair,
            mu_flag_threshold=mu_flag_threshold,
            auroc_set=auroc_set,
        )
    )

    return SweepCellResult(
        policy=spec.policy,
        victim_id=spec.victim_id,
        source=spec.source,
        fraction=spec.fraction,
        seed_pair=spec.seed_pair,
        thresholds_under_clean=clean_pair,
        thresholds_under_poisoning=poisoned_pair,
        clean_metrics=clean_metrics,
        poisoned_metrics=poisoned_metrics,
    )
