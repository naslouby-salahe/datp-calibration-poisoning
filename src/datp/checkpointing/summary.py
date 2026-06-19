from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np

from datp.checkpointing.enums import (
    CheckpointSelectionVerdict,
    PrimaryCheckpointSelectionRule,
)
from datp.core.enums import (
    Baseline,
    Regime,
)
from datp.core.errors import fmt
from datp.statistics.bootstrap import BootstrapResult, bca_ci
from datp.statistics.effect_size import CliffsDeltaResult, cliffs_delta
from datp.statistics.wilcoxon import WilcoxonResult, wilcoxon_test
from datp.thresholding.metrics_serialization import SweepMetrics

_MODULE = "checkpointing.summary"
_COLLAPSE_BA_THRESHOLD = 0.9
_COLLAPSE_TPR_THRESHOLD = 0.9


@dataclass(frozen=True, slots=True)
class CheckpointBaselineSummary:
    regime: Regime
    baseline: Baseline
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
class CheckpointRegimeAComparison:
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
    selected_round: int
    verdict: CheckpointSelectionVerdict
    regime: Regime
    rule: PrimaryCheckpointSelectionRule
    comparisons: tuple[CheckpointRegimeAComparison, ...]
    summaries: tuple[CheckpointBaselineSummary, ...]


def _aggregate_fpr_stats(items: list[SweepMetrics]) -> tuple[float, float, float]:
    mean_fpr = _mean(m.mean_fpr for m in items)
    cv_fpr = _mean(m.cv_fpr for m in items)
    worst_client_fpr = _max(m.worst_client_fpr for m in items)
    return mean_fpr, cv_fpr, worst_client_fpr


def _aggregate_tpr_stats(items: list[SweepMetrics]) -> tuple[float, float, float]:
    mean_tpr = _mean(_mean_client_tpr(m) for m in items)
    cv_tpr = _mean(m.cv_tpr for m in items)
    worst_client_tpr = _min(_worst_client_tpr(m) for m in items)
    return mean_tpr, cv_tpr, worst_client_tpr


def _build_baseline_summary(
    regime: Regime,
    baseline: Baseline,
    checkpoint_round: int,
    items: list[SweepMetrics],
) -> CheckpointBaselineSummary:
    mean_fpr, cv_fpr, worst_client_fpr = _aggregate_fpr_stats(items)
    mean_tpr, cv_tpr, worst_client_tpr = _aggregate_tpr_stats(items)
    return CheckpointBaselineSummary(
        regime=regime,
        baseline=baseline,
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
) -> tuple[CheckpointBaselineSummary, ...]:
    grouped: dict[tuple[Regime, Baseline, int], list[SweepMetrics]] = {}
    for item in metrics:
        if item.checkpoint_round is None:
            raise ValueError(
                fmt(_MODULE, "Metric lacks checkpoint_round", "int", item.run_id)
            )
        key = (item.regime, item.baseline, item.checkpoint_round)
        grouped.setdefault(key, []).append(item)
    return tuple(
        _build_baseline_summary(regime, baseline, checkpoint_round, items)
        for (regime, baseline, checkpoint_round), items in sorted(grouped.items())
    )


def _eligible_rounds(
    comparisons: tuple[CheckpointRegimeAComparison, ...],
    b2_by_round: dict[int, CheckpointBaselineSummary],
) -> list[int]:
    rounds: list[int] = []
    for comparison in comparisons:
        b2_summary = b2_by_round.get(comparison.checkpoint_round)
        if b2_summary is None:
            continue
        if comparison.cv_fpr_bca95.mean_delta <= 0.0:
            continue
        if _mean(comparison.worst_client_fpr_deltas) <= 0.0:
            continue
        if b2_summary.coverage_ratio < 1.0:
            continue
        rounds.append(comparison.checkpoint_round)
    return rounds


def _validate_regime_a_metrics(metrics: tuple[SweepMetrics, ...]) -> None:
    if not metrics:
        raise ValueError(
            fmt(_MODULE, "No checkpoint metrics supplied", "Regime A metrics", "empty")
        )
    if any(metric.regime != Regime.A for metric in metrics):
        raise ValueError(
            fmt(
                _MODULE,
                "Selection input must be Regime A only",
                "regime a",
                "mixed regimes",
            )
        )


def select_global_primary_checkpoint(
    *,
    metrics: tuple[SweepMetrics, ...],
    n_bootstrap: int,
    bootstrap_seed: int,
) -> GlobalCheckpointSelection:
    _validate_regime_a_metrics(metrics)
    summaries = summarize_checkpoint_metrics(metrics)
    b2_by_round = {
        summary.checkpoint_round: summary
        for summary in summaries
        if summary.baseline == Baseline.B2
    }
    comparisons = _regime_a_comparisons(
        metrics=metrics,
        n_bootstrap=n_bootstrap,
        bootstrap_seed=bootstrap_seed,
    )
    eligible = _eligible_rounds(comparisons, b2_by_round)
    if not eligible:
        raise ValueError(
            fmt(
                _MODULE,
                "No checkpoint satisfies Regime A selection constraints",
                "B2 CV(FPR), worst-FPR, and coverage advantages",
                "none",
            )
        )
    selected = min(
        eligible,
        key=lambda r: (-_lower_tail_tradeoff(b2_by_round[r]), r),
    )
    return GlobalCheckpointSelection(
        selected_round=selected,
        verdict=CheckpointSelectionVerdict.SELECTED,
        regime=Regime.A,
        rule=PrimaryCheckpointSelectionRule.GLOBAL_LOWER_TAIL_TRADEOFF_FROM_REGIME_A,
        comparisons=comparisons,
        summaries=summaries,
    )


def summaries_for_global_primary_checkpoint(
    summaries: tuple[CheckpointBaselineSummary, ...],
    selection: GlobalCheckpointSelection,
) -> tuple[CheckpointBaselineSummary, ...]:
    """Return main-table summaries at the one globally selected checkpoint round."""
    return tuple(
        summary
        for summary in summaries
        if summary.checkpoint_round == selection.selected_round
    )


def _build_round_comparison(
    checkpoint_round: int,
    b1: dict[int, SweepMetrics],
    b2: dict[int, SweepMetrics],
    n_bootstrap: int,
    bootstrap_seed: int,
) -> CheckpointRegimeAComparison:
    seeds = tuple(sorted(set(b1) & set(b2)))
    if len(seeds) < 3:
        raise ValueError(
            fmt(
                _MODULE,
                "BCa checkpoint selection needs at least 3 paired seeds",
                ">=3",
                str(len(seeds)),
            )
        )
    cv_deltas = tuple(b1[seed].cv_fpr - b2[seed].cv_fpr for seed in seeds)
    worst_deltas = tuple(
        b1[seed].worst_client_fpr - b2[seed].worst_client_fpr for seed in seeds
    )
    b1_cv = np.array([b1[seed].cv_fpr for seed in seeds], dtype=np.float64)
    b2_cv = np.array([b2[seed].cv_fpr for seed in seeds], dtype=np.float64)
    return CheckpointRegimeAComparison(
        checkpoint_round=checkpoint_round,
        cv_fpr_deltas=cv_deltas,
        worst_client_fpr_deltas=worst_deltas,
        cv_fpr_bca95=bca_ci(
            np.array(cv_deltas, dtype=np.float64),
            n_bootstrap=n_bootstrap,
            ci=0.95,
            seed=bootstrap_seed,
        ),
        cv_fpr_sign_consistency=_positive_fraction(cv_deltas),
        worst_fpr_sign_consistency=_positive_fraction(worst_deltas),
        wilcoxon=wilcoxon_test(b1_cv, b2_cv),
        cliffs_delta=cliffs_delta(b1_cv, b2_cv),
    )


def _regime_a_comparisons(
    *,
    metrics: tuple[SweepMetrics, ...],
    n_bootstrap: int,
    bootstrap_seed: int,
) -> tuple[CheckpointRegimeAComparison, ...]:
    grouped: dict[int, dict[Baseline, dict[int, SweepMetrics]]] = {}
    for metric in metrics:
        if metric.checkpoint_round is None:
            raise ValueError(
                fmt(_MODULE, "Metric lacks checkpoint_round", "int", metric.run_id)
            )
        baseline_map = grouped.setdefault(metric.checkpoint_round, {})
        seed_map = baseline_map.setdefault(metric.baseline, {})
        seed_map[metric.seed] = metric

    comparisons: list[CheckpointRegimeAComparison] = []
    for checkpoint_round, baseline_map in sorted(grouped.items()):
        b1 = baseline_map.get(Baseline.B1)
        b2 = baseline_map.get(Baseline.B2)
        if b1 is None or b2 is None:
            continue
        comparisons.append(
            _build_round_comparison(
                checkpoint_round, b1, b2, n_bootstrap, bootstrap_seed
            )
        )
    return tuple(comparisons)


def _lower_tail_tradeoff(summary: CheckpointBaselineSummary) -> float:
    return min(summary.p10_macro_f1, summary.worst_client_balanced_accuracy)


def _collapse_cell_count(metric: SweepMetrics) -> int:
    count = 0
    for detail in metric.per_client:
        if detail.calibration_pending:
            continue
        if (
            detail.balanced_accuracy < _COLLAPSE_BA_THRESHOLD
            or detail.tpr < _COLLAPSE_TPR_THRESHOLD
        ):
            count += 1
    return count


def _mean_client_tpr(metric: SweepMetrics) -> float:
    return _mean(
        detail.tpr for detail in metric.per_client if not detail.calibration_pending
    )


def _worst_client_tpr(metric: SweepMetrics) -> float:
    return _min(
        detail.tpr for detail in metric.per_client if not detail.calibration_pending
    )


def _mean_client_macro_f1(metric: SweepMetrics) -> float:
    return _mean(
        detail.macro_f1
        for detail in metric.per_client
        if not detail.calibration_pending
    )


def _positive_fraction(values: tuple[float, ...]) -> float:
    if not values:
        return math.nan
    return sum(value > 0.0 for value in values) / len(values)


def _mean(values: Iterable[float]) -> float:
    arr = _finite_array(values)
    return float(np.mean(arr)) if arr.size else math.nan


def _min(values: Iterable[float]) -> float:
    arr = _finite_array(values)
    return float(np.min(arr)) if arr.size else math.nan


def _max(values: Iterable[float]) -> float:
    arr = _finite_array(values)
    return float(np.max(arr)) if arr.size else math.nan


def _finite_array(values: Iterable[float]) -> np.ndarray:
    arr = np.array(tuple(values), dtype=np.float64)
    return arr[np.isfinite(arr)]
