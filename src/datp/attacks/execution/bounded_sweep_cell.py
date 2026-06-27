"""Bounded-sweep cell execution: injection, threshold recomputation, and metrics."""

from __future__ import annotations

from dataclasses import dataclass

from datp.attacks.constants import THRESHOLD_QUANTILE
from datp.attacks.enums import AttackerObjective, PoisoningSourceStrategy
from datp.attacks.execution.cell_runner import (
    InjectionSpec,
    PolicyPair,
    inject_single_victim,
    recompute_pair,
)
from datp.attacks.metrics.metric_engine import (
    MetricResult,
    compute_metrics,
    compute_mu_flag_threshold,
)
from datp.attacks.planning.bounded_sweep_matrix import SweepCellSpec
from datp.attacks.planning.guardrails import (
    assert_bounded_scale_requires_single_client,
    assert_fractions_in_locked_grid,
    assert_valid_source_objective_pair,
)
from datp.attacks.score_containers import ScoreCollection
from datp.attacks.types import AurocSet, MetricEngineInput, PoisonedCalibrationSet
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.seeds import SeedPair


def lock_mu_flag_threshold(collection: ScoreCollection) -> float:
    """Compute the mu-flag threshold from the minimum clean mean FPR across all policies."""
    clean_cal_set = PoisonedCalibrationSet.from_mapping(
        {cid: collection.clients[cid].cal.copy() for cid in collection.eligible_ids}
    )
    fprs = [
        compute_metrics(
            MetricEngineInput(
                collection=collection,
                pair=recompute_pair(collection, clean_cal_set, policy),
                mu_flag_threshold=None,
            )
        ).fleet_fpr.mean_fpr
        for policy in (
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        )
    ]
    positive_fprs = [v for v in fprs if v > 0.0]
    return compute_mu_flag_threshold(min(positive_fprs)) if positive_fprs else 0.0


@dataclass(frozen=True, slots=True)
class SweepCellConfig:
    """Per-cell configuration for a bounded-sweep execution."""

    collection: ScoreCollection
    mu_flag_threshold: float
    auroc_set: AurocSet | None = None
    scope_idx: int = 0
    q: float = THRESHOLD_QUANTILE
    cluster_seed: int = 0


@dataclass(frozen=True, slots=True)
class SweepCellResult:
    """Immutable result of one bounded-sweep cell."""

    policy: ThresholdPolicy
    victim_id: str
    objective: AttackerObjective
    source: PoisoningSourceStrategy
    fraction: float
    seed_pair: SeedPair
    thresholds_under_clean: PolicyPair
    thresholds_under_poisoning: PolicyPair
    clean_metrics: MetricResult
    poisoned_metrics: MetricResult

    @property
    def training_seed(self) -> int:
        """Training seed from the cell's seed pair."""
        return self.seed_pair.training_seed

    @property
    def poisoning_seed(self) -> int:
        """Poisoning seed from the cell's seed pair."""
        return self.seed_pair.poisoning_seed


def _cell_injection_and_metrics(
    spec: SweepCellSpec,
    config: SweepCellConfig,
    *,
    fraction: float,
    mu_flag_threshold: float | None,
) -> tuple[PolicyPair, MetricResult]:
    """Inject at the given fraction and compute the threshold pair and metrics."""
    outcome = inject_single_victim(
        config.collection,
        victim_id=spec.victim_id,
        spec=InjectionSpec(
            source=spec.source,
            fraction=fraction,
            seed_pair=spec.seed_pair,
            scope_idx=config.scope_idx,
            objective=spec.objective,
        ),
    )
    pair = recompute_pair(config.collection, outcome.poisoned_cal_set, spec.policy)
    metrics = compute_metrics(
        MetricEngineInput(
            collection=config.collection,
            pair=pair,
            mu_flag_threshold=mu_flag_threshold,
            auroc_set=config.auroc_set,
        )
    )
    return pair, metrics


def run_sweep_cell(spec: SweepCellSpec, *, config: SweepCellConfig) -> SweepCellResult:
    """Run one sweep cell: guardrails, clean baseline, then poisoned metrics."""
    assert_fractions_in_locked_grid([spec.fraction], ExperimentStage.NBAIOT_MAIN)
    assert_bounded_scale_requires_single_client(
        ExperimentStage.NBAIOT_MAIN, spec.target_scope
    )
    assert_valid_source_objective_pair(spec.source, spec.objective)

    clean_pair, clean_metrics = _cell_injection_and_metrics(
        spec, config, fraction=0.0, mu_flag_threshold=None
    )
    poisoned_pair, poisoned_metrics = _cell_injection_and_metrics(
        spec, config, fraction=spec.fraction, mu_flag_threshold=config.mu_flag_threshold
    )

    return SweepCellResult(
        policy=spec.policy,
        victim_id=spec.victim_id,
        objective=spec.objective,
        source=spec.source,
        fraction=spec.fraction,
        seed_pair=spec.seed_pair,
        thresholds_under_clean=clean_pair,
        thresholds_under_poisoning=poisoned_pair,
        clean_metrics=clean_metrics,
        poisoned_metrics=poisoned_metrics,
    )
