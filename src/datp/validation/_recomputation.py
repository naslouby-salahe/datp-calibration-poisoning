"""Metric recomputation verification for the results audit."""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import dataclasses
import math

from datp.config.stages import ExperimentStage
from datp.core.metric_enums import MetricName
from datp.validation.enums import DenominatorStatus
from datp.validation.schemas import MetricRecomputationRecord

_RECOMPUTATION_EPSILON = 1e-9
_RECOMPUTE_METRICS = (
    MetricName.FPR,
    MetricName.TPR,
    MetricName.BALANCED_ACCURACY,
    MetricName.MACRO_F1,
)


@dataclasses.dataclass(frozen=True, slots=True)
class RecomputationParams:
    """Parameters for metric recomputation from raw confusion matrix."""

    run_id: str
    seed: int
    stage: ExperimentStage
    policy: ThresholdPolicy
    client_id: str
    tp: int
    fp: int
    tn: int
    fn: int
    n_benign: int
    n_attack: int
    saved_fpr: float | None
    saved_tpr: float | None
    saved_balanced_accuracy: float | None
    saved_macro_f1: float | None


@dataclasses.dataclass(frozen=True, slots=True)
class _RecomputationResult:
    """Result of comparing saved vs recomputed metric values."""

    diff: float | None
    saved_value: float | None
    recomputed_value: float | None
    status: DenominatorStatus


def _both_finite(saved: float | None, recomp: float) -> bool:
    """Return True when both values exist and are finite — safe for comparison."""
    return saved is not None and math.isfinite(saved) and math.isfinite(recomp)


def _both_missing(saved: float | None, recomp: float) -> bool:
    """Return True when both values are effectively missing (None or non-finite)."""
    if saved is None:
        return True
    return not math.isfinite(saved) and not math.isfinite(recomp)


def _make_recomputation_record(
    params: RecomputationParams,
    metric: MetricName,
    *,
    saved_value: float | None = None,
    recomputed_value: float | None = None,
    abs_diff: float | None = None,
    status: DenominatorStatus,
) -> MetricRecomputationRecord:
    """Build a MetricRecomputationRecord with common fields from params."""
    return MetricRecomputationRecord(
        run_id=params.run_id,
        seed=params.seed,
        stage=params.stage,
        policy=params.policy,
        client_id=params.client_id,
        metric=metric,
        saved_value=saved_value,
        recomputed_value=recomputed_value,
        abs_diff=abs_diff,
        status=status,
    )


def _compare_recomputation(saved: float | None, recomp: float) -> _RecomputationResult:
    """Compare saved and recomputed metric values, returning diff and status."""
    if _both_finite(saved, recomp):
        assert saved is not None  # type narrow for Pyright
        diff = abs(saved - recomp)
        status = (
            DenominatorStatus.PASS
            if diff <= _RECOMPUTATION_EPSILON
            else DenominatorStatus.FAIL
        )
        return _RecomputationResult(
            diff=diff,
            saved_value=saved,
            recomputed_value=recomp if math.isfinite(recomp) else None,
            status=status,
        )
    if _both_missing(saved, recomp):
        return _RecomputationResult(
            diff=None,
            saved_value=None,
            recomputed_value=recomp if math.isfinite(recomp) else None,
            status=DenominatorStatus.PASS,
        )
    return _RecomputationResult(
        diff=None,
        saved_value=saved,
        recomputed_value=recomp if math.isfinite(recomp) else None,
        status=DenominatorStatus.FAIL,
    )


def _compute_metric_status(
    metric: MetricName, params: RecomputationParams
) -> DenominatorStatus | None:
    """Return EXCLUDED_EVALUATION_INCOMPLETE if metric can't be recomputed, else None."""
    if (
        metric in (MetricName.TPR, MetricName.BALANCED_ACCURACY, MetricName.MACRO_F1)
        and params.n_attack == 0
    ):
        return DenominatorStatus.EXCLUDED_EVALUATION_INCOMPLETE
    if metric == MetricName.FPR and params.n_benign == 0:
        return DenominatorStatus.EXCLUDED_EVALUATION_INCOMPLETE
    return None


def append_recomputation_records(
    records: list[MetricRecomputationRecord],
    params: RecomputationParams,
) -> None:
    """Recompute binary metrics from confusion matrix and append comparison records."""
    from datp.evaluation.metrics import recompute_binary_metrics  # noqa: PLC0415

    bm = recompute_binary_metrics(params.tp, params.fp, params.tn, params.fn)
    recomputed: dict[MetricName, float] = {
        MetricName.FPR: bm.fpr,
        MetricName.TPR: bm.tpr,
        MetricName.BALANCED_ACCURACY: bm.balanced_accuracy,
        MetricName.MACRO_F1: bm.macro_f1,
    }
    saved: dict[MetricName, float | None] = {
        MetricName.FPR: params.saved_fpr,
        MetricName.TPR: params.saved_tpr,
        MetricName.BALANCED_ACCURACY: params.saved_balanced_accuracy,
        MetricName.MACRO_F1: params.saved_macro_f1,
    }
    for metric in _RECOMPUTE_METRICS:
        pre_status = _compute_metric_status(metric, params)
        if pre_status is not None:
            records.append(
                _make_recomputation_record(
                    params,
                    metric,
                    status=pre_status,
                )
            )
            continue
        cmp_result = _compare_recomputation(saved[metric], recomputed[metric])
        records.append(
            _make_recomputation_record(
                params,
                metric,
                saved_value=cmp_result.saved_value,
                recomputed_value=cmp_result.recomputed_value,
                abs_diff=cmp_result.diff,
                status=cmp_result.status,
            )
        )
