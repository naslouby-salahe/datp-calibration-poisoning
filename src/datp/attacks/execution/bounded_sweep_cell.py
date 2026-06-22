"""Real-data bounded sweep cell runner for the N-BaIoT main matrix.

Orchestrates one (policy, source, fraction, victim, seed) cell using the same
tested primitives as the synthetic smoke harness
(``datp.attacks.execution.cell_runner``). ``mu_flag_threshold`` is locked once per
training seed from the minimum positive clean mean FPR across all three
threshold policies (roadmap §9.6) and reused unmodified across every
policy/source/fraction/victim/poisoning-seed cell for that training seed.
"""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from dataclasses import dataclass

from datp.artifacts.poison_names import THRESHOLD_QUANTILE
from datp.attacks.execution.cell_runner import (
    InjectionSpec,
    PolicyPair,
    inject_single_victim,
    recompute_pair,
)
from datp.attacks.planning.bounded_sweep_matrix import SweepCellSpec
from datp.attacks.planning.guardrails import (
    assert_bounded_scale_requires_single_client,
    assert_fractions_in_locked_grid,
)
from datp.attacks.metrics.metric_engine import (
    MetricResult,
    compute_metrics,
    compute_mu_flag_threshold,
)
from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import AurocSet, MetricEngineInput, PoisonedCalibrationSet
from datp.attacks.enums import PoisoningSourceStrategy
from datp.config.stages import ExperimentStage
from datp.core.seeds import SeedPair


def lock_mu_flag_threshold(collection: ScoreCollection) -> float:
    """Lock ``mu_flag_threshold`` per roadmap §9.6.

    Computes the clean mean FPR for each of the three threshold policies
    (GLOBAL_THRESHOLD, LOCAL_THRESHOLD, CLUSTER_THRESHOLD), takes the
    smallest positive value across all three, and divides by 8.

    Must be called once per training seed, before any poisoned run for that
    seed, and the returned value reused unmodified across every policy/cell.
    """
    clean_cal_set = PoisonedCalibrationSet.from_mapping(
        {cid: collection.clients[cid].cal.copy() for cid in collection.eligible_ids}
    )
    mean_fprs: list[float] = []
    for policy in (
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    ):
        pair = recompute_pair(collection, clean_cal_set, policy)
        metrics = compute_metrics(
            MetricEngineInput(collection=collection, pair=pair, mu_flag_threshold=None)
        )
        mean_fprs.append(metrics.fleet_fpr.mean_fpr)
    positive_fprs = [v for v in mean_fprs if v > 0.0]
    if not positive_fprs:
        return 0.0
    return compute_mu_flag_threshold(min(positive_fprs))


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
    assert_fractions_in_locked_grid([spec.fraction], ExperimentStage.NBAIOT_MAIN)
    assert_bounded_scale_requires_single_client(ExperimentStage.NBAIOT_MAIN, spec.target_scope)
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
