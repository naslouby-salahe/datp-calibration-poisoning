"""Real-data bounded sweep cell runner.

Orchestrates the real-data bounded matrix on ``REGIME_A_NBAIOT`` using the same
tested primitives as the synthetic smoke harness
(``datp.attacks.cell_runner``). The key difference from the smoke harness:
``mu_flag_threshold`` is locked once per training seed from the *clean GLOBAL_THRESHOLD*
eligible-client mean FPR and passed in explicitly, then reused unmodified
across every policy/source/fraction/victim/poisoning-seed cell for that
training seed — it is never recomputed from a non-GLOBAL_THRESHOLD policy's clean pair.
"""

from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

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
    compute_metrics,
    compute_mu_flag_threshold,
)
from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import AurocSet, MetricEngineInput, PoisonedCalibrationSet
from datp.attacks.enums import PoisoningSourceStrategy
from datp.core.seeds import SeedPair


def lock_mu_flag_threshold(collection: ScoreCollection) -> float:
    """Lock ``mu_flag_threshold`` from the clean GLOBAL_THRESHOLD eligible-client mean FPR.

    Must be called once per training seed, before any poisoned run for that
    seed, and the returned value reused unmodified across every policy/cell
    for that seed. The lock is always GLOBAL_THRESHOLD-derived, regardless of which policy a
    given cell evaluates.
    """
    clean_cal = {
        cid: collection.clients[cid].cal.copy() for cid in collection.eligible_ids
    }
    clean_global_pair = recompute_pair(
        collection,
        PoisonedCalibrationSet.from_mapping(clean_cal),
        ThresholdPolicy.GLOBAL_THRESHOLD,
    )
    clean_metrics = compute_metrics(
        MetricEngineInput(
            collection=collection, pair=clean_global_pair, mu_flag_threshold=None
        )
    )
    return compute_mu_flag_threshold(clean_metrics.fleet_fpr.mean_fpr)


@dataclass(frozen=True, slots=True)
class SweepCellConfig:
    """Fixed-per-training-seed runtime config for sweep cells.

    Bundles the collection, locked mu_flag_threshold, precomputed auroc_set,
    and hyperparameters that are constant across all cells sharing one
    training seed.
    """

    collection: ScoreCollection
    mu_flag_threshold: float
    auroc_set: AurocSet | None = None
    scope_idx: int = 0
    q: float = THRESHOLD_QUANTILE
    cluster_seed: int = 0


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


def _cell_injection_and_metrics(
    spec: SweepCellSpec,
    config: SweepCellConfig,
    *,
    fraction: float,
    mu_flag_threshold: float | None,
) -> tuple[PolicyPair, MetricResult]:
    """Run one injection + threshold recompute + metric evaluation."""
    outcome = inject_single_victim(
        config.collection,
        victim_id=spec.victim_id,
        spec=InjectionSpec(
            source=spec.source,
            fraction=fraction,
            seed_pair=spec.seed_pair,
            scope_idx=config.scope_idx,
        ),
    )
    pair = recompute_pair(
        config.collection,
        outcome.poisoned_cal_set,
        spec.policy,
    )
    metrics = compute_metrics(
        MetricEngineInput(
            collection=config.collection,
            pair=pair,
            mu_flag_threshold=mu_flag_threshold,
            auroc_set=config.auroc_set,
        )
    )
    return pair, metrics


def run_sweep_cell(
    spec: SweepCellSpec,
    *,
    config: SweepCellConfig,
) -> SweepCellResult:
    """Run one bounded cell using a pre-locked ``mu_flag_threshold``."""
    clean_pair, clean_metrics = _cell_injection_and_metrics(
        spec, config, fraction=0.0, mu_flag_threshold=None
    )
    poisoned_pair, poisoned_metrics = _cell_injection_and_metrics(
        spec, config, fraction=spec.fraction, mu_flag_threshold=config.mu_flag_threshold
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
