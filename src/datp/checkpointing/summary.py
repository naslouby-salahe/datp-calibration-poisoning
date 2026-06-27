"""Checkpoint metric aggregation summaries and primary-round selection."""

from __future__ import annotations

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
    CheckpointSelectionVerdict,
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
    """Aggregated metrics summary for one policy at one checkpoint round."""

    stage: ExperimentStage
    policy: ThresholdPolicy
    checkpoint_round: int
    seed_count: int
    mean_fpr: float
    cv_fpr: float
    worst_client_fpr: float
    mean_tpr: float
    cv_tpr: float
    worst_client_tpr: float
    macro_f1: float
    p10_macro_f1: float
    worst_client_balanced_accuracy: float
    coverage_ratio: float
    collapse_cell_count: int


@dataclass(frozen=True, slots=True)
class CheckpointPrimaryTrainingComparison:
    """Statistical comparison of GLOBAL vs LOCAL threshold at one round."""

    checkpoint_round: int
    cv_fpr_deltas: tuple[float, ...]
    worst_client_fpr_deltas: tuple[float, ...]
    cv_fpr_bca95: BootstrapResult
    cv_fpr_sign_consistency: float
    worst_fpr_sign_consistency: float
    wilcoxon: WilcoxonResult
    cliffs_delta: CliffsDeltaResult


@dataclass(frozen=True, slots=True)
class GlobalCheckpointSelection:
    """Result of global primary checkpoint selection with all supporting evidence."""

    selected_round: int
    verdict: CheckpointSelectionVerdict
    stage: ExperimentStage
    rule: PrimaryCheckpointSelectionRule
    comparisons: tuple[CheckpointPrimaryTrainingComparison, ...]
    summaries: tuple[CheckpointPolicySummary, ...]


def _aggregate_fpr_stats(items: list[SweepMetrics]) -> tuple[float, float, float]:
    """Aggregate mean FPR, CV FPR, and worst-client FPR across seeds."""
    mean_fpr = _mean(m.mean_fpr for m in items)
    cv_fpr = _mean(m.cv_fpr for m in items)
    worst_client_fpr = _max(m.worst_client_fpr for m in items)
    return mean_fpr, cv_fpr, worst_client_fpr


def _aggregate_tpr_stats(items: list[SweepMetrics]) -> tuple[float, float, float]:
    """Aggregate mean TPR, CV TPR, and worst-client TPR across seeds."""
    mean_tpr = _mean(_mean_client_tpr(m) for m in items)
    cv_tpr = _mean(m.cv_tpr for m in items)
    worst_client_tpr = _min(_worst_client_tpr(m) for m in items)
    return mean_tpr, cv_tpr, worst_client_tpr


def _require_round(item: SweepMetrics) -> int:
    """Extract checkpoint_round from metrics, raising if None."""
    if item.checkpoint_round is None:
        raise ValueError(
            f"[{_MODULE}] Metric lacks checkpoint_round. Expected: int. Got: {item.run_id}."
        )
    return item.checkpoint_round


def _build_policy_summary(
    stage: ExperimentStage,
    policy: ThresholdPolicy,
    checkpoint_round: int,
    items: list[SweepMetrics],
) -> CheckpointPolicySummary:
    """Aggregate all metrics for a policy-round combination into a summary."""
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
    """Group and summarize metrics by stage, policy, and checkpoint round."""
    grouped: dict[tuple[ExperimentStage, ThresholdPolicy, int], list[SweepMetrics]] = {}
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
    local_by_round: dict[int, CheckpointPolicySummary],
) -> list[int]:
    """Filter comparison rounds to those with positive FPR advantage and sufficient coverage."""
    rounds: list[int] = []
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
    """Ensure all supplied metrics are from the NBAIOT_MAIN stage."""
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
    n_bootstrap: int,
    bootstrap_seed: int,
) -> GlobalCheckpointSelection:
    """Select the primary global checkpoint by lower-tail tradeoff from NBAIOT_MAIN comparisons."""
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
        verdict=CheckpointSelectionVerdict.SELECTED,
        stage=ExperimentStage.NBAIOT_MAIN,
        rule=PrimaryCheckpointSelectionRule.GLOBAL_LOWER_TAIL_TRADEOFF_FROM_NBAIOT_MAIN,
        comparisons=comparisons,
        summaries=summaries,
    )


def summaries_for_global_primary_checkpoint(
    summaries: tuple[CheckpointPolicySummary, ...],
    selection: GlobalCheckpointSelection,
) -> tuple[CheckpointPolicySummary, ...]:
    """Filter summaries to only the selected checkpoint round."""
    return tuple(
        summary
        for summary in summaries
        if summary.checkpoint_round == selection.selected_round
    )


def _build_round_comparison(
    checkpoint_round: int,
    global_seeds: dict[int, SweepMetrics],
    local_seeds: dict[int, SweepMetrics],
    n_bootstrap: int,
    bootstrap_seed: int,
) -> CheckpointPrimaryTrainingComparison:
    """Build a statistical comparison between GLOBAL and LOCAL FPR at one round."""
    seeds = tuple(sorted(set(global_seeds) & set(local_seeds)))
    if len(seeds) < BCA_MIN_PAIRED_SEEDS:
        raise ValueError(
            f"[{_MODULE}] BCa checkpoint selection needs at least {BCA_MIN_PAIRED_SEEDS} paired seeds. Expected: >={BCA_MIN_PAIRED_SEEDS}. Got: {str(len(seeds))}."
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
    n_bootstrap: int,
    bootstrap_seed: int,
) -> tuple[CheckpointPrimaryTrainingComparison, ...]:
    """Build paired comparisons across all rounds where both policies are present."""
    grouped: dict[int, dict[ThresholdPolicy, dict[int, SweepMetrics]]] = {}
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


def _lower_tail_tradeoff(summary: CheckpointPolicySummary) -> float:
    """Return the minimum of p10 macro F1 and worst-client balanced accuracy."""
    return min(summary.p10_macro_f1, summary.worst_client_balanced_accuracy)


def _collapse_cell_count(metric: SweepMetrics) -> int:
    """Count clients below BA or TPR collapse thresholds, excluding calibration-pending."""
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


def _mean_client_tpr(metric: SweepMetrics) -> float:
    """Mean TPR across non-calibration-pending clients."""
    return _mean(
        detail.tpr for detail in metric.per_client if not detail.calibration_pending
    )


def _worst_client_tpr(metric: SweepMetrics) -> float:
    """Minimum TPR across non-calibration-pending clients."""
    return _min(
        detail.tpr for detail in metric.per_client if not detail.calibration_pending
    )


def _mean_client_macro_f1(metric: SweepMetrics) -> float:
    """Mean macro F1 across non-calibration-pending clients."""
    return _mean(
        detail.macro_f1
        for detail in metric.per_client
        if not detail.calibration_pending
    )


def _positive_fraction(values: tuple[float, ...]) -> float:
    """Fraction of values strictly above FPR_DELTA_ADVANTAGE_MIN."""
    if not values:
        return math.nan
    return sum(value > FPR_DELTA_ADVANTAGE_MIN for value in values) / len(values)


def _mean(values: Iterable[float]) -> float:
    """Mean of finite float values, NaN if empty."""
    arr = _finite_array(values)
    return float(np.mean(arr)) if arr.size else math.nan


def _min(values: Iterable[float]) -> float:
    """Minimum of finite float values, NaN if empty."""
    arr = _finite_array(values)
    return float(np.min(arr)) if arr.size else math.nan


def _max(values: Iterable[float]) -> float:
    """Maximum of finite float values, NaN if empty."""
    arr = _finite_array(values)
    return float(np.max(arr)) if arr.size else math.nan


def _finite_array(values: Iterable[float]) -> np.ndarray:
    """Convert an iterable of floats to a numpy array, dropping non-finite values."""
    arr = np.array(tuple(values), dtype=np.float64)
    return arr[np.isfinite(arr)]
