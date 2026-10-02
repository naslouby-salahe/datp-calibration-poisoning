from __future__ import annotations

from datp.types import (
    BootstrapCount,
    ClassificationScore,
    FalsePositiveRate,
    PoisonFraction,
    RandomSeed,
    Ratio,
    SeedCount,
    RoundIndex,
    SampleCount,
    ScoreValue,
    ScoreVector,
    SignedCount,
    SignedDelta,
    TruePositiveRate,
)


import math
from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np

from datp.attacks.constants import BOOTSTRAP_CI
from datp.checkpointing.constants import (
    COLLAPSE_BA_THRESHOLD,
    COLLAPSE_TPR_THRESHOLD,
    COVERAGE_RATIO_FLOOR,
    FPR_DELTA_ADVANTAGE_MIN,
)
from datp.checkpointing.enums import (
    PrimaryCheckpointSelectionRule,
)
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.statistics.bootstrap import BootstrapResult, bca_ci
from datp.statistics.constants import BCA_MIN_PAIRED_SEEDS
from datp.statistics.effect_size import CliffsDeltaResult, cliffs_delta
from datp.statistics.wilcoxon import WilcoxonResult, wilcoxon_test
from datp.thresholding.metrics_serialization import SweepMetrics

_MODULE = "checkpointing.summary"


@dataclass(frozen=True, slots=True)
class CheckpointPolicySummary:

    stage: ExperimentStage
    policy: ThresholdPolicy
    checkpoint_round: RoundIndex
    seed_count: SeedCount
    mean_fpr: FalsePositiveRate
    cv_fpr: FalsePositiveRate
    worst_client_fpr: FalsePositiveRate
    mean_tpr: TruePositiveRate
    cv_tpr: TruePositiveRate
    worst_client_tpr: TruePositiveRate
    macro_f1: ClassificationScore
    p10_macro_f1: ClassificationScore
    worst_client_balanced_accuracy: ClassificationScore
    coverage_ratio: Ratio
    collapse_cell_count: SampleCount


@dataclass(frozen=True, slots=True)
class CheckpointPrimaryTrainingComparison:

    checkpoint_round: RoundIndex
    cv_fpr_deltas: tuple[SignedDelta, ...]
    worst_client_fpr_deltas: tuple[SignedDelta, ...]
    cv_fpr_bca95: BootstrapResult
    cv_fpr_sign_consistency: FalsePositiveRate
    worst_fpr_sign_consistency: FalsePositiveRate
    wilcoxon: WilcoxonResult
    cliffs_delta: CliffsDeltaResult


@dataclass(frozen=True, slots=True)
class GlobalCheckpointSelection:

    selected_round: RoundIndex
    stage: ExperimentStage
    rule: PrimaryCheckpointSelectionRule
    comparisons: tuple[CheckpointPrimaryTrainingComparison, ...]
    summaries: tuple[CheckpointPolicySummary, ...]


def _aggregate_fpr_stats(items: list[SweepMetrics]) -> tuple[FalsePositiveRate, FalsePositiveRate, FalsePositiveRate]:
    mean_fprs: list[FalsePositiveRate] = []
    for metric in items:
        if metric.mean_fpr is None:
            raise ValueError(f"Missing mean_fpr in {metric.run_id}")
        mean_fprs.append(metric.mean_fpr)
    mean_fpr = _mean(mean_fprs)
    cv_fpr = _mean(m.cv_fpr for m in items)
    worst_client_fpr = _max(m.worst_client_fpr for m in items)
    return mean_fpr, cv_fpr, worst_client_fpr


def _aggregate_tpr_stats(items: list[SweepMetrics]) -> tuple[TruePositiveRate, TruePositiveRate, TruePositiveRate]:
    mean_tpr = _mean(_mean_client_tpr(m) for m in items)
    cv_tpr = _mean(m.cv_tpr for m in items)
    worst_client_tpr = _min(_worst_client_tpr(m) for m in items)
    return mean_tpr, cv_tpr, worst_client_tpr


def _require_round(item: SweepMetrics) -> RoundIndex:
    if item.checkpoint_round is None:
        raise ValueError(
            f"[{_MODULE}] Metric lacks checkpoint_round. Expected: int. Got: {item.run_id}."
        )
    return item.checkpoint_round


def _build_policy_summary(
    stage: ExperimentStage,
    policy: ThresholdPolicy,
    checkpoint_round: RoundIndex,
    items: list[SweepMetrics],
) -> CheckpointPolicySummary:
    mean_fpr, cv_fpr, worst_client_fpr = _aggregate_fpr_stats(items)
    mean_tpr, cv_tpr, worst_client_tpr = _aggregate_tpr_stats(items)
    return CheckpointPolicySummary(
        stage=stage,
        policy=policy,
        checkpoint_round=checkpoint_round,
        seed_count=len(items),
        mean_fpr=mean_fpr,
        cv_fpr=cv_fpr,
        worst_client_fpr=worst_client_fpr,
        mean_tpr=mean_tpr,
        cv_tpr=cv_tpr,
        worst_client_tpr=worst_client_tpr,
        macro_f1=_mean(_mean_client_macro_f1(m) for m in items),
        p10_macro_f1=_mean(m.p10_macro_f1 for m in items),
        worst_client_balanced_accuracy=_min(m.worst_ba for m in items),
        coverage_ratio=_min(m.coverage_ratio for m in items),
        collapse_cell_count=sum(_collapse_cell_count(m) for m in items),
    )


def summarize_checkpoint_metrics(
    metrics: tuple[SweepMetrics, ...],
) -> tuple[CheckpointPolicySummary, ...]:
    grouped: dict[tuple[ExperimentStage, ThresholdPolicy, SignedCount], list[SweepMetrics]] = {}
    for item in metrics:
        grouped.setdefault((item.stage, item.policy, _require_round(item)), []).append(
            item
        )

    return tuple(
        _build_policy_summary(stage, policy, checkpoint_round, items)
        for (stage, policy, checkpoint_round), items in sorted(grouped.items())
    )


def _eligible_rounds(
    comparisons: tuple[CheckpointPrimaryTrainingComparison, ...],
    local_by_round: dict[RoundIndex, CheckpointPolicySummary],
) -> list[RoundIndex]:
    rounds: list[RoundIndex] = []
    for comparison in comparisons:
        local_summary = local_by_round.get(comparison.checkpoint_round)
        if local_summary is None:
            continue
        if comparison.cv_fpr_bca95.mean_delta <= FPR_DELTA_ADVANTAGE_MIN:
            continue
        if _mean(comparison.worst_client_fpr_deltas) <= FPR_DELTA_ADVANTAGE_MIN:
            continue
        if local_summary.coverage_ratio < COVERAGE_RATIO_FLOOR:
            continue
        rounds.append(comparison.checkpoint_round)
    return rounds


def _validate_primary_training_metrics(metrics: tuple[SweepMetrics, ...]) -> None:
    if not metrics:
        raise ValueError(
            f"[{_MODULE}] No checkpoint metrics supplied. Expected: primary training metrics. Got: empty."
        )
    if any(metric.stage != ExperimentStage.NBAIOT_MAIN for metric in metrics):
        raise ValueError(
            f"[{_MODULE}] Selection input must be NBAIOT_MAIN only. Expected: stage.nbaiot_main. Got: mixed stages."
        )


def select_global_primary_checkpoint(
    *,
    metrics: tuple[SweepMetrics, ...],
    n_bootstrap: BootstrapCount,
    bootstrap_seed: RandomSeed,
) -> GlobalCheckpointSelection:
    _validate_primary_training_metrics(metrics)
    summaries = summarize_checkpoint_metrics(metrics)
    local_by_round = {
        summary.checkpoint_round: summary
        for summary in summaries
        if summary.policy == ThresholdPolicy.LOCAL_THRESHOLD
    }
    comparisons = _primary_training_comparisons(
        metrics=metrics,
        n_bootstrap=n_bootstrap,
        bootstrap_seed=bootstrap_seed,
    )
    eligible = _eligible_rounds(comparisons, local_by_round)
    if not eligible:
        raise ValueError(
            f"[{_MODULE}] No checkpoint satisfies primary training selection constraints. Expected: LOCAL_THRESHOLD CV(FPR), worst-FPR, and coverage advantages. Got: none."
        )
    selected = min(
        eligible,
        key=lambda r: (-_lower_tail_tradeoff(local_by_round[r]), r),
    )
    return GlobalCheckpointSelection(
        selected_round=selected,
        stage=ExperimentStage.NBAIOT_MAIN,
        rule=PrimaryCheckpointSelectionRule.GLOBAL_LOWER_TAIL_TRADEOFF_FROM_NBAIOT_MAIN,
        comparisons=comparisons,
        summaries=summaries,
    )


def _build_round_comparison(
    checkpoint_round: RoundIndex,
    global_seeds: dict[RandomSeed, SweepMetrics],
    local_seeds: dict[RandomSeed, SweepMetrics],
    n_bootstrap: BootstrapCount,
    bootstrap_seed: RandomSeed,
) -> CheckpointPrimaryTrainingComparison:
    seeds = tuple(sorted(set(global_seeds) & set(local_seeds)))
    if len(seeds) < BCA_MIN_PAIRED_SEEDS:
        raise ValueError(
            f"[{_MODULE}] BCa checkpoint selection needs at least {BCA_MIN_PAIRED_SEEDS} paired seeds. Expected: >={BCA_MIN_PAIRED_SEEDS}. Got: {len(seeds)}."
        )
    cv_deltas = tuple(
        global_seeds[seed].cv_fpr - local_seeds[seed].cv_fpr for seed in seeds
    )
    worst_deltas = tuple(
        global_seeds[seed].worst_client_fpr - local_seeds[seed].worst_client_fpr
        for seed in seeds
    )
    global_cv = np.array(
        [global_seeds[seed].cv_fpr for seed in seeds], dtype=np.float64
    )
    local_cv = np.array([local_seeds[seed].cv_fpr for seed in seeds], dtype=np.float64)
    return CheckpointPrimaryTrainingComparison(
        checkpoint_round=checkpoint_round,
        cv_fpr_deltas=cv_deltas,
        worst_client_fpr_deltas=worst_deltas,
        cv_fpr_bca95=bca_ci(
            np.array(cv_deltas, dtype=np.float64),
            n_bootstrap=n_bootstrap,
            ci=BOOTSTRAP_CI,
            seed=bootstrap_seed,
        ),
        cv_fpr_sign_consistency=_positive_fraction(cv_deltas),
        worst_fpr_sign_consistency=_positive_fraction(worst_deltas),
        wilcoxon=wilcoxon_test(global_cv, local_cv),
        cliffs_delta=cliffs_delta(global_cv, local_cv),
    )


def _primary_training_comparisons(
    *,
    metrics: tuple[SweepMetrics, ...],
    n_bootstrap: BootstrapCount,
    bootstrap_seed: RandomSeed,
) -> tuple[CheckpointPrimaryTrainingComparison, ...]:
    grouped: dict[
        RoundIndex, dict[ThresholdPolicy, dict[RandomSeed, SweepMetrics]]
    ] = {}
    for metric in metrics:
        policy_map = grouped.setdefault(_require_round(metric), {})
        seed_map = policy_map.setdefault(metric.policy, {})
        seed_map[metric.seed] = metric

    comparisons: list[CheckpointPrimaryTrainingComparison] = []
    for checkpoint_round, policy_map in sorted(grouped.items()):
        global_seeds = policy_map.get(ThresholdPolicy.GLOBAL_THRESHOLD)
        local_seeds = policy_map.get(ThresholdPolicy.LOCAL_THRESHOLD)
        if global_seeds is None or local_seeds is None:
            continue
        comparisons.append(
            _build_round_comparison(
                checkpoint_round, global_seeds, local_seeds, n_bootstrap, bootstrap_seed
            )
        )

    return tuple(comparisons)


def _lower_tail_tradeoff(summary: CheckpointPolicySummary) -> ScoreValue:
    return min(summary.p10_macro_f1, summary.worst_client_balanced_accuracy)


def _collapse_cell_count(metric: SweepMetrics) -> SampleCount:
    count = 0
    for detail in metric.per_client:
        if detail.calibration_pending:
            continue
        if (
            detail.balanced_accuracy < COLLAPSE_BA_THRESHOLD
            or detail.tpr < COLLAPSE_TPR_THRESHOLD
        ):
            count += 1
    return count


def _mean_client_tpr(metric: SweepMetrics) -> TruePositiveRate:
    return _mean(
        detail.tpr for detail in metric.per_client if not detail.calibration_pending
    )


def _worst_client_tpr(metric: SweepMetrics) -> TruePositiveRate:
    return _min(
        detail.tpr for detail in metric.per_client if not detail.calibration_pending
    )


def _mean_client_macro_f1(metric: SweepMetrics) -> ClassificationScore:
    return _mean(
        detail.macro_f1
        for detail in metric.per_client
        if not detail.calibration_pending
    )


def _positive_fraction(values: tuple[ScoreValue, ...]) -> PoisonFraction:
    if not values:
        return math.nan
    return sum(value > FPR_DELTA_ADVANTAGE_MIN for value in values) / len(values)


def _mean(values: Iterable[ScoreValue]) -> ScoreValue:
    arr = _finite_array(values)
    return float(np.mean(arr)) if arr.size else math.nan


def _min(values: Iterable[ScoreValue]) -> ScoreValue:
    arr = _finite_array(values)
    return float(np.min(arr)) if arr.size else math.nan


def _max(values: Iterable[ScoreValue]) -> ScoreValue:
    arr = _finite_array(values)
    return float(np.max(arr)) if arr.size else math.nan


def _finite_array(values: Iterable[ScoreValue]) -> ScoreVector:
    arr = np.array(tuple(values), dtype=np.float64)
    return arr[np.isfinite(arr)]
