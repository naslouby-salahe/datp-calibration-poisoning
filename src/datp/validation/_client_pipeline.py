from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import dataclasses
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from datp.config.models import DatpConfig
from datp.core.enums import (
    POLICY_THRESHOLD_SOURCE,
    CONTROLLED_POLICIES,
    NormalizationScope,
    ScoringStage,
    ThresholdAggregationMethod,
    ThresholdSource,
)
from datp.core.metric_enums import ConfusionKey, MetricName, PayloadKey
from datp.core.provenance import array_hash
from datp.core.types import ThresholdResult
from datp.scoring.loading import read_score_column as _read_scores
from datp.validation._audit_helpers import (
    _argworst,
    _binary_auc_fields,
    _build_partition_audit,
    _feature_hash,
    _finite_mean,
    _float_or_none,
    _iqr_or_none,
    _load_client_attack_labels,
    _load_run_context,
    _load_score_arrays,
    _lookup_dataset,
    _lookup_threshold_agg,
    _percentile_or_none,
    _recon_summary,
    _score_stage_files,
    _std_or_none,
    _ThresholdState,
)
from datp.validation._audit_types import (
    _AuditAccumulator,
    _ClientMetricParams,
    _RunContext,
    _CellPanel,
)
from datp.validation._recomputation import (
    RecomputationParams,
    append_recomputation_records,
)
from datp.validation.constants import (
    AUDIT_SCHEMA_VERSION,
    BINARY_ATTACK_LABEL,
    BLOCKED_RESUME_COMMAND,
    DEFAULT_COVERAGE_RATIO,
    FINGERPRINT_METHOD_BENIGN_RECON_ERROR_HISTOGRAM,
)
from datp.validation.datasets import compute_ciciot_homogeneity
from datp.validation.enums import (
    WORST_CLIENT_DIRECTIONS,
    AuditSeverity,
    DenominatorStatus,
    WarningCode,
)
from datp.validation.invariants import InvariantHashes
from datp.validation.schemas import (
    CICIoTHomogeneityRecord,
    ClientMetricRecord,
    ClusterAssignmentRecord,
    ConvergenceAuditRecord,
    FPRCompanionRecord,
    MetricDenominatorAuditRecord,
    PerAttackMetricRecord,
    RunManifestRecord,
    ThresholdRecord,
    WarningRecord,
    WorstClientRecord,
)


def _build_threshold_records(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    threshold_result: ThresholdResult,
    cal_errors: dict[str, np.ndarray],
    cfg: DatpConfig,
) -> dict[str, float]:
    """Build ThresholdRecord entries and return client_id → threshold mapping."""
    local_taus = {
        cid: float(np.percentile(errors, cfg.threshold.q * 100))
        for cid, errors in cal_errors.items()
        if errors.size >= cfg.threshold.n_min
    }
    client_thresholds: dict[str, float] = {}
    for ct in sorted(
        threshold_result.client_thresholds, key=lambda item: item.client_id
    ):
        client_thresholds[ct.client_id] = float(ct.threshold)
        acc.threshold_records.append(
            ThresholdRecord(
                run_id=ctx.run_id,
                seed=ctx.seed,
                stage=ctx.stage,
                policy=ctx.policy,
                                client_id=ct.client_id,
                threshold_value=float(ct.threshold),
                threshold_source=(
                    ThresholdSource.TAU_GLOBAL_FALLBACK
                    if ct.calibration_pending
                    else POLICY_THRESHOLD_SOURCE[ctx.policy]
                ),
                calibration_pending=ct.calibration_pending,
                tau_global=float(threshold_result.tau_global),
                threshold_aggregation_method=_lookup_threshold_agg(ctx.policy),
                local_tau_i=local_taus.get(ct.client_id),
            )
        )
    return client_thresholds


def _extract_cluster_fingerprint(
    fp: Sequence[float],
) -> tuple[float | None, float | None, float | None, float | None]:
    """Extract CLUSTER_THRESHOLD fingerprint scalars with guard clauses for each position."""
    n = len(fp)
    return (
        float(fp[0]) if n > 0 else None,
        float(fp[1]) if n > 1 else None,
        float(fp[2]) if n > 2 else None,
        float(fp[3]) if n > 3 else None,
    )


def _cluster_silhouette_scores_by_client(scores: Any) -> dict[str, float]:
    """Normalize CLUSTER_THRESHOLD silhouette metadata for validation schema export."""
    if hasattr(scores, "items"):
        return {str(client_id): float(score) for client_id, score in scores.items()}
    return {score.client_id: float(score.score) for score in scores}


def _build_cluster_records(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    threshold_result: ThresholdResult,
) -> None:
    """Build ClusterAssignmentRecord entries for CLUSTER_THRESHOLD baseline."""
    if ctx.policy != ThresholdPolicy.CLUSTER_THRESHOLD or not threshold_result.metadata.cluster:
        return
    for cluster_id, info in threshold_result.metadata.cluster.cluster_info.items():
        for client_id in info.members:
            fp = threshold_result.metadata.cluster.fingerprints.get(client_id)
            if fp is None:
                fp = ()
            fp_mean, fp_std, fp_skew, fp_p95 = _extract_cluster_fingerprint(fp)
            acc.cluster_records.append(
                ClusterAssignmentRecord(
                    run_id=ctx.run_id,
                    seed=ctx.seed,
                    stage=ctx.stage,
                        client_id=client_id,
                    cluster_id=cluster_id,
                    threshold_value=float(info.tau_cluster),
                    fingerprint_mean=fp_mean,
                    fingerprint_std=fp_std,
                    fingerprint_skew=fp_skew,
                    fingerprint_p95=fp_p95,
                    k_selected=threshold_result.metadata.cluster.k,
                    silhouette=threshold_result.metadata.cluster.silhouette,
                    silhouette_scores=_cluster_silhouette_scores_by_client(
                        threshold_result.metadata.cluster.silhouette_scores
                    ),
                )
            )


def _emit_global_not_pooled_warning(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    threshold_result: ThresholdResult,
    cal_errors: dict[str, np.ndarray],
    cfg: DatpConfig,
) -> None:
    """Emit GLOBAL_THRESHOLD warning when tau_global is arithmetic mean, not pooled percentile."""
    if ctx.policy != ThresholdPolicy.GLOBAL_THRESHOLD:
        return
    pooled = float(
        np.percentile(
            np.concatenate(list(cal_errors.values())),
            cfg.threshold.q * 100,
        )
    )
    if not math.isclose(float(threshold_result.tau_global), pooled):
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.INFO,
                code=WarningCode.GLOBAL_NOT_POOLED_PERCENTILE,
                message=f"{ctx.run_id} tau_global is the arithmetic mean of eligible local tau_i values.",
                exact_command=None,
            )
        )


def _process_thresholds(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    cfg: DatpConfig,
) -> _ThresholdState:
    """Reconstruct thresholds and build threshold/cluster audit records."""
    if ctx.policy not in CONTROLLED_POLICIES:
        return _ThresholdState.empty(ctx.policy)

    arrays = _load_score_arrays(acc, ctx, cfg)
    if arrays.threshold_result is None:
        return _ThresholdState(
            client_thresholds={},
            threshold_aggregation_method=_lookup_threshold_agg(ctx.policy),
            test_benign_scores=arrays.test_benign_scores,
            test_attack_scores=arrays.test_attack_scores,
            cal_errors=arrays.cal_errors,
        )

    client_thresholds = _build_threshold_records(
        acc, ctx, arrays.threshold_result, arrays.cal_errors, cfg
    )
    _build_cluster_records(acc, ctx, arrays.threshold_result)
    _emit_global_not_pooled_warning(
        acc, ctx, arrays.threshold_result, arrays.cal_errors, cfg
    )

    return _ThresholdState(
        client_thresholds=client_thresholds,
        threshold_aggregation_method=_lookup_threshold_agg(ctx.policy),
        test_benign_scores=arrays.test_benign_scores,
        test_attack_scores=arrays.test_attack_scores,
        cal_errors=arrays.cal_errors,
    )


def _compute_denominator_status(
    has_confusion: bool,
    eval_incomplete: bool,
    fpr_ok: bool,
    tpr_ok: bool,
) -> tuple[DenominatorStatus, DenominatorStatus, DenominatorStatus]:
    """Compute FPR, TPR, and macro-F1 denominator status flags."""
    if not has_confusion:
        blocked = DenominatorStatus.BLOCKED_PENDING_RUN
        return blocked, blocked, blocked
    if eval_incomplete:
        fpr_status = DenominatorStatus.PASS if fpr_ok else DenominatorStatus.FAIL
        excluded = DenominatorStatus.EXCLUDED_EVALUATION_INCOMPLETE
        return fpr_status, excluded, excluded
    fpr_status = DenominatorStatus.PASS if fpr_ok else DenominatorStatus.FAIL
    tpr_status = DenominatorStatus.PASS if tpr_ok else DenominatorStatus.FAIL
    return fpr_status, tpr_status, DenominatorStatus.PASS


def _build_client_metric_record(
    ctx: _RunContext,
    cmp: _ClientMetricParams,
) -> ClientMetricRecord:
    """Build a ClientMetricRecord from row data and computed values."""
    return ClientMetricRecord(
        run_id=ctx.run_id,
        seed=ctx.seed,
        stage=ctx.stage,
        policy=ctx.policy,
                client_id=cmp.client_id,
        fpr=float(cmp.row[MetricName.FPR]),
        tpr=float(cmp.row[MetricName.TPR]),
        balanced_accuracy=float(cmp.row[MetricName.BALANCED_ACCURACY]),
        macro_f1=float(cmp.row[MetricName.MACRO_F1]),
        auroc=cmp.auroc,
        pr_auc=cmp.pr_auc,
        n_benign=cmp.n_benign,
        n_attack=cmp.n_attack,
        tp=cmp.tp,
        fp=cmp.fp,
        tn=cmp.tn,
        fn=cmp.fn,
        eligible=cmp.eligible,
        calibration_pending=cmp.calibration_pending,
        evaluation_incomplete=cmp.evaluation_incomplete,
        coverage_ratio=cmp.coverage_ratio,
    )


def _build_attack_metric_record(
    ctx: _RunContext,
    client_id: str,
    row: dict[str, Any],
    eval_incomplete: bool,
    tp: int,
    n_attack: int,
) -> PerAttackMetricRecord:
    """Build a PerAttackMetricRecord with eval_incomplete guard clauses."""
    return PerAttackMetricRecord(
        run_id=ctx.run_id,
        seed=ctx.seed,
        stage=ctx.stage,
        policy=ctx.policy,
                client_id=client_id,
        attack_label=BINARY_ATTACK_LABEL,
        status=(
            DenominatorStatus.EXCLUDED_EVALUATION_INCOMPLETE
            if eval_incomplete
            else DenominatorStatus.PASS
        ),
        tpr=None if eval_incomplete else float(row[MetricName.TPR]),
        detected_count=None if eval_incomplete else tp,
        denominator=None if eval_incomplete else n_attack,
    )


@dataclasses.dataclass(frozen=True, slots=True)
class _RowProcessingCtx:
    """Shared client-set and coverage context for per-row metric processing."""

    eligible_ids: frozenset[str]
    pending_ids: frozenset[str]
    incomplete: frozenset[str]
    coverage_ratio: str


def _emit_missing_confusion_warning(
    acc: _AuditAccumulator,
    run_id: str,
) -> None:
    if run_id in acc.missing_confusion_warned:
        return
    acc.missing_confusion_warned.add(run_id)
    acc.warnings.append(
        WarningRecord(
            severity=AuditSeverity.BLOCKED_PENDING_RUN,
            code=WarningCode.MISSING_CONFUSION_MATRIX,
            message=(
                f"Per-client confusion matrices are missing for {run_id}; "
                "denominator gates cannot be verified."
            ),
            exact_command=BLOCKED_RESUME_COMMAND,
        )
    )


def _append_denominator_record(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    *,
    client_id: str,
    n_benign: int,
    n_attack: int,
    tp: int,
    fp: int,
    tn: int,
    fn: int,
    has_confusion: bool,
    eval_incomplete: bool,
) -> None:
    fpr_den, tpr_den = fp + tn, tp + fn
    fpr_ok = has_confusion and fpr_den == n_benign and n_benign > 0
    tpr_ok = has_confusion and tpr_den == n_attack and n_attack > 0
    fpr_status, tpr_status, macro_f1_status = _compute_denominator_status(
        has_confusion, eval_incomplete, fpr_ok, tpr_ok
    )
    acc.denominator_records.append(
        MetricDenominatorAuditRecord(
            run_id=ctx.run_id,
            seed=ctx.seed,
            stage=ctx.stage,
            policy=ctx.policy,
                        client_id=client_id,
            fpr_denominator=fpr_den,
            fpr_denominator_expected=n_benign,
            fpr_status=fpr_status,
            tpr_denominator=tpr_den,
            tpr_denominator_expected=n_attack,
            tpr_status=tpr_status,
            macro_f1_status=macro_f1_status,
        )
    )


def _compute_client_metric_row(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    threshold_state: _ThresholdState,
    row: dict[str, Any],
    rpc: _RowProcessingCtx,
) -> None:
    """Process a single client row: denominator audit, recomputation, client/attack records."""
    cm = row[PayloadKey.CONFUSION_MATRIX] if PayloadKey.CONFUSION_MATRIX in row else {}
    tp, fp, tn, fn = (int(cm[k]) if k in cm else 0 for k in tuple(ConfusionKey))
    client_id = str(row[PayloadKey.CLIENT_ID])
    n_benign = int(row[PayloadKey.N_BENIGN])
    n_attack = int(row[PayloadKey.N_ATTACK])
    eval_incomplete = client_id in rpc.incomplete or n_attack == 0
    has_confusion = bool(cm)

    if not has_confusion:
        _emit_missing_confusion_warning(acc, ctx.run_id)

    _append_denominator_record(
        acc,
        ctx,
        client_id=client_id,
        n_benign=n_benign,
        n_attack=n_attack,
        tp=tp,
        fp=fp,
        tn=tn,
        fn=fn,
        has_confusion=has_confusion,
        eval_incomplete=eval_incomplete,
    )

    if has_confusion:
        append_recomputation_records(
            acc.recomputation_records,
            RecomputationParams(
                run_id=ctx.run_id,
                seed=ctx.seed,
                stage=ctx.stage,
                policy=ctx.policy,
                client_id=client_id,
                tp=tp,
                fp=fp,
                tn=tn,
                fn=fn,
                n_benign=n_benign,
                n_attack=n_attack,
                saved_fpr=_float_or_none(row.get(MetricName.FPR)),
                saved_tpr=_float_or_none(row.get(MetricName.TPR)),
                saved_balanced_accuracy=_float_or_none(
                    row.get(MetricName.BALANCED_ACCURACY)
                ),
                saved_macro_f1=_float_or_none(row.get(MetricName.MACRO_F1)),
            ),
        )

    auroc, pr_auc = _binary_auc_fields(
        row,
        threshold_state.test_benign_scores.get(client_id),
        threshold_state.test_attack_scores.get(client_id),
    )
    acc.client_records.append(
        _build_client_metric_record(
            ctx,
            _ClientMetricParams(
                client_id=client_id,
                row=row,
                n_benign=n_benign,
                n_attack=n_attack,
                tp=tp,
                fp=fp,
                tn=tn,
                fn=fn,
                auroc=auroc,
                pr_auc=pr_auc,
                eligible=client_id in rpc.eligible_ids,
                calibration_pending=client_id in rpc.pending_ids,
                evaluation_incomplete=eval_incomplete,
                coverage_ratio=rpc.coverage_ratio,
            ),
        )
    )
    acc.attack_records.append(
        _build_attack_metric_record(ctx, client_id, row, eval_incomplete, tp, n_attack)
    )


def _compute_per_attack_families(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    threshold_state: _ThresholdState,
    row: dict[str, Any],
    eval_incomplete: bool,
) -> None:
    """Per-attack-family records for CICIoT2023 (stretch-only diagnostic) only; out of scope."""
    return

def _collect_eligible_metric_pairs(
    normalized_clients: list[dict[str, Any]],
    eligible_ids: frozenset[str],
    incomplete: frozenset[str],
) -> tuple[
    list[tuple[str, float]],
    list[tuple[str, float]],
    list[tuple[str, float]],
    list[tuple[str, float]],
]:
    """Collect (client_id, value) pairs for FPR, TPR, macro_f1, balanced_accuracy."""
    eligible_pairs_fpr = [
        (str(r[PayloadKey.CLIENT_ID]), float(r[MetricName.FPR]))
        for r in normalized_clients
        if r[PayloadKey.CLIENT_ID] in eligible_ids and MetricName.FPR in r
    ]
    tprs = [
        (str(r[PayloadKey.CLIENT_ID]), float(r[MetricName.TPR]))
        for r in normalized_clients
        if r[PayloadKey.CLIENT_ID] in eligible_ids
        and MetricName.TPR in r
        and str(r[PayloadKey.CLIENT_ID]) not in incomplete
    ]
    macro_f1s = [
        (str(r[PayloadKey.CLIENT_ID]), float(r[MetricName.MACRO_F1]))
        for r in normalized_clients
        if r[PayloadKey.CLIENT_ID] in eligible_ids and MetricName.MACRO_F1 in r
    ]
    balanced_accuracies = [
        (str(r[PayloadKey.CLIENT_ID]), float(r[MetricName.BALANCED_ACCURACY]))
        for r in normalized_clients
        if r[PayloadKey.CLIENT_ID] in eligible_ids
    ]
    return eligible_pairs_fpr, tprs, macro_f1s, balanced_accuracies


def _check_naked_cv_fpr(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    cv_fpr_value: float,
) -> None:
    if not math.isfinite(cv_fpr_value):
        return
    mean_fpr_raw = ctx.metrics.get(MetricName.MEAN_FPR)
    std_fpr_raw = ctx.metrics.get(MetricName.STD_FPR)
    if mean_fpr_raw is None or std_fpr_raw is None:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.FAIL,
                code=WarningCode.NAKED_CV_FPR,
                message=(
                    f"{ctx.run_id} contains cv_fpr={cv_fpr_value:.4g} without "
                    "companion fields mean_fpr/std_fpr. Re-run datp sweep to "
                    "regenerate metrics artifacts."
                ),
                exact_command=BLOCKED_RESUME_COMMAND,
            )
        )


def _find_worst_values(
    eligible_pairs_fpr: list[tuple[str, float]],
    tprs: list[tuple[str, float]],
    macro_f1s: list[tuple[str, float]],
    balanced_accuracies: list[tuple[str, float]],
) -> _WorstClientSet:
    """Compute worst (client_id, value) for each metric and bundle with pool sizes."""
    fpr_id, fpr_val = _argworst(
        eligible_pairs_fpr, WORST_CLIENT_DIRECTIONS[MetricName.FPR]
    )
    tpr_id, tpr_val = _argworst(tprs, WORST_CLIENT_DIRECTIONS[MetricName.TPR])
    f1_id, f1_val = _argworst(macro_f1s, WORST_CLIENT_DIRECTIONS[MetricName.MACRO_F1])
    ba_id, ba_val = _argworst(
        balanced_accuracies, WORST_CLIENT_DIRECTIONS[MetricName.BALANCED_ACCURACY]
    )
    return _WorstClientSet(
        fpr_id=fpr_id,
        fpr_value=fpr_val,
        fpr_pool=len(eligible_pairs_fpr),
        tpr_id=tpr_id,
        tpr_value=tpr_val,
        tpr_pool=len(tprs),
        f1_id=f1_id,
        f1_value=f1_val,
        f1_pool=len(macro_f1s),
        ba_id=ba_id,
        ba_value=ba_val,
        ba_pool=len(balanced_accuracies),
    )


@dataclasses.dataclass(frozen=True, slots=True)
class _WorstClientSet:
    """Per-metric worst (client_id, value, pool_size) tuples for a single run."""

    fpr_id: str | None
    fpr_value: float | None
    fpr_pool: int
    tpr_id: str | None
    tpr_value: float | None
    tpr_pool: int
    f1_id: str | None
    f1_value: float | None
    f1_pool: int
    ba_id: str | None
    ba_value: float | None
    ba_pool: int


def _emit_worst_client_records(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    worst: _WorstClientSet,
) -> None:
    for metric_name, (cid, value, pool) in {
        MetricName.FPR: (worst.fpr_id, worst.fpr_value, worst.fpr_pool),
        MetricName.TPR: (worst.tpr_id, worst.tpr_value, worst.tpr_pool),
        MetricName.MACRO_F1: (worst.f1_id, worst.f1_value, worst.f1_pool),
        MetricName.BALANCED_ACCURACY: (worst.ba_id, worst.ba_value, worst.ba_pool),
    }.items():
        acc.worst_client_records.append(
            WorstClientRecord(
                run_id=ctx.run_id,
                seed=ctx.seed,
                stage=ctx.stage,
                policy=ctx.policy,
                                metric=metric_name,
                direction=WORST_CLIENT_DIRECTIONS[metric_name],
                worst_client_id=cid,
                worst_value=value,
                eligible_pool_size=pool,
            )
        )


def _build_cell_panel(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    *,
    cv_fpr_record_value: float | None,
    mean_fpr_value: float | None,
    std_fpr_value: float | None,
    iqr_fpr_value: float | None,
    macro_f1_p10_value: float | None,
    worst_fpr_value: float | None,
    worst_tpr_value: float | None,
    worst_f1_value: float | None,
    worst_ba_value: float | None,
    coverage_ratio: str,
) -> None:
    cv_tpr_raw = ctx.metrics.get(MetricName.CV_TPR)
    cv_tpr_value = (
        float(cv_tpr_raw)
        if cv_tpr_raw is not None and math.isfinite(float(cv_tpr_raw))
        else None
    )
    acc.cell_panel[(ctx.stage, ctx.seed, ctx.policy)] = _CellPanel(
        cv_fpr=cv_fpr_record_value,
        cv_tpr=cv_tpr_value,
        mean_fpr=mean_fpr_value,
        std_fpr=std_fpr_value,
        iqr_fpr=iqr_fpr_value,
        worst_client_fpr=worst_fpr_value,
        worst_client_tpr=worst_tpr_value,
        worst_client_macro_f1=worst_f1_value,
        worst_client_balanced_accuracy=worst_ba_value,
        macro_f1_mean=_finite_mean(
            [float(r[MetricName.MACRO_F1]) for r in ctx.normalized_clients]
        ),
        macro_f1_p10=macro_f1_p10_value,
        auroc_mean=_finite_mean(
            [
                float(r[MetricName.AUROC])
                for r in ctx.normalized_clients
                if r.get(MetricName.AUROC) is not None
            ]
        ),
        pr_auc_mean=_finite_mean(
            [
                float(r[MetricName.PR_AUC])
                for r in ctx.normalized_clients
                if r.get(MetricName.PR_AUC) is not None
            ]
        ),
        convergence_round=ctx.convergence_round,
        tau_global=(
            float(ctx.metrics[MetricName.TAU_GLOBAL])
            if ctx.metrics.get(MetricName.TAU_GLOBAL) is not None
            else None
        ),
        coverage_ratio=coverage_ratio,
    )


def _compute_aggregate_stats(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    eligible_ids: frozenset[str],
    incomplete: frozenset[str],
    coverage_ratio: str,
) -> None:
    """Compute companion records, worst clients, and cell panel for a single run."""
    eligible_pairs_fpr, tprs, macro_f1s, balanced_accuracies = (
        _collect_eligible_metric_pairs(ctx.normalized_clients, eligible_ids, incomplete)
    )

    eligible_fpr_values = [v for _, v in eligible_pairs_fpr]
    cv_fpr_value = float(ctx.metrics[MetricName.CV_FPR])
    cv_fpr_record_value = cv_fpr_value if math.isfinite(cv_fpr_value) else None
    _check_naked_cv_fpr(acc, ctx, cv_fpr_value)

    mean_fpr_value = _finite_mean(eligible_fpr_values)
    std_fpr_value = _std_or_none(eligible_fpr_values)
    iqr_fpr_value = _iqr_or_none(eligible_fpr_values)
    macro_f1_p10_value = _percentile_or_none([v for _, v in macro_f1s], 10.0)

    worst = _find_worst_values(eligible_pairs_fpr, tprs, macro_f1s, balanced_accuracies)

    acc.companion_records.append(
        FPRCompanionRecord(
            run_id=ctx.run_id,
            seed=ctx.seed,
            stage=ctx.stage,
            policy=ctx.policy,
                        cv_fpr=cv_fpr_record_value,
            mean_fpr=mean_fpr_value,
            std_fpr=std_fpr_value,
            iqr_fpr=iqr_fpr_value,
            worst_client_fpr=worst.fpr_value,
            eligible_count=len(eligible_ids),
            client_count=ctx.client_count,
            coverage_ratio=coverage_ratio,
        )
    )

    _emit_worst_client_records(acc, ctx, worst)

    _build_cell_panel(
        acc,
        ctx,
        cv_fpr_record_value=cv_fpr_record_value,
        mean_fpr_value=mean_fpr_value,
        std_fpr_value=std_fpr_value,
        iqr_fpr_value=iqr_fpr_value,
        macro_f1_p10_value=macro_f1_p10_value,
        worst_fpr_value=worst.fpr_value,
        worst_tpr_value=worst.tpr_value,
        worst_f1_value=worst.f1_value,
        worst_ba_value=worst.ba_value,
        coverage_ratio=coverage_ratio,
    )


def _process_per_client_metrics(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    threshold_state: _ThresholdState,
) -> None:
    """Process per-client metrics: denominators, recomputation, worst clients, cell panel."""
    coverage_ratio = (
        f"{ctx.eligible_count}/{ctx.client_count}"
        if ctx.client_count
        else DEFAULT_COVERAGE_RATIO
    )
    rpc = _RowProcessingCtx(
        eligible_ids=ctx.eligible_client_ids,
        pending_ids=ctx.pending_client_ids,
        incomplete=ctx.incomplete_ids,
        coverage_ratio=coverage_ratio,
    )

    for row in ctx.normalized_clients:
        _compute_client_metric_row(acc, ctx, threshold_state, row, rpc)
        client_id = str(row[PayloadKey.CLIENT_ID])
        eval_incomplete = (
            client_id in rpc.incomplete or int(row[PayloadKey.N_ATTACK]) == 0
        )
        _compute_per_attack_families(acc, ctx, threshold_state, row, eval_incomplete)

    _compute_aggregate_stats(acc, ctx, rpc.eligible_ids, rpc.incomplete, coverage_ratio)


def _build_run_manifest(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    *,
    git_commit: str,
    timestamp: str,
    scoring_hash: str,
    threshold_hash: str,
    metrics_hash: str,
    threshold_aggregation_method: ThresholdAggregationMethod,
) -> None:
    """Build RunManifestRecord and invariant input records."""
    acc.manifest_records.append(
        RunManifestRecord(
            run_id=ctx.run_id,
            timestamp=timestamp,
            git_commit_hash=git_commit,
            seed=ctx.seed,
            dataset=_lookup_dataset(ctx.stage),
            stage=ctx.stage,
            policy=ctx.policy,
                        client_count=ctx.client_count,
            split_hash=ctx.split_hash,
            model_hash=ctx.model_hash,
            encoder_hash=ctx.model_hash,
            training_config_hash=ctx.training_hash,
            preprocessing_config_hash=ctx.preprocessing_hash,
            scoring_code_hash=scoring_hash,
            threshold_code_hash=threshold_hash,
            metrics_code_hash=metrics_hash,
            artifact_schema_version=AUDIT_SCHEMA_VERSION,
            convergence_round=ctx.convergence_round,
            convergence_criterion_value=ctx.convergence_value,
            convergence_status=ctx.convergence_status,
            eligible_clients=ctx.eligible_count,
            calibration_pending_clients=ctx.pending_count,
            evaluation_incomplete_clients=len(ctx.incomplete_ids),
            feature_count=ctx.feature_count,
            feature_list_hash=_feature_hash(ctx.feature_count),
            threshold_aggregation_method=threshold_aggregation_method,
            normalization_scope=(
                NormalizationScope(ctx.metrics[PayloadKey.NORMALIZATION_SCOPE])
                if ctx.metrics.get(PayloadKey.NORMALIZATION_SCOPE)
                else None
            ),
            train_count=ctx.train_count,
            calibration_count=ctx.calibration_count,
            test_count=ctx.test_count,
        )
    )
    acc.invariant_inputs[ctx.invariant_key][ctx.policy] = InvariantHashes(
        split_hash=ctx.split_hash,
        model_hash=ctx.model_hash,
        encoder_hash=ctx.model_hash,
        scoring_code_hash=scoring_hash,
        metrics_code_hash=metrics_hash,
    )


def _process_score_hashes(
    acc: _AuditAccumulator,
    ctx: _RunContext,
) -> None:
    """Compute and store per-client score hashes for controlled baselines."""
    if ctx.policy not in CONTROLLED_POLICIES or not ctx.score_root.exists():
        return
    cell_hashes: dict[tuple[ScoringStage, str], str] = {}
    for stage in ScoringStage:
        for score_path in _score_stage_files(ctx.score_root, stage):
            arr = _read_scores(score_path)
            cell_hashes[(stage, score_path.stem)] = array_hash(arr)
            if ctx.policy == ThresholdPolicy.GLOBAL_THRESHOLD:
                acc.recon_records.append(
                    _recon_summary(
                        run_id=ctx.run_id,
                        policy=ctx.policy,
                        seed=ctx.seed,
                        stage=ctx.stage,
                        client_id=score_path.stem,
                        stage_split=stage,
                        arr=arr,
                    )
                )
    acc.score_hashes_by_cell[ctx.invariant_key][ctx.policy] = cell_hashes


def _process_homogeneity(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    cfg: DatpConfig,
    cal_errors: dict[str, np.ndarray],
) -> None:
    """Compute CICIoT homogeneity audit for GLOBAL_THRESHOLD (stretch-only diagnostic; out of scope)."""
    # CICIoT2023 homogeneity is out of scope; always return.
    return

def _process_partition_audit(
    acc: _AuditAccumulator,
    ctx: _RunContext,
) -> None:
    """Build partition audit record or emit missing-manifest warning."""
    if ctx.partition_path.exists():
        acc.partition_audits[f"{ctx.stage.value}:{ctx.seed}"] = (
            _build_partition_audit(
                stage=ctx.stage,
                seed=ctx.seed,
                partition_path=ctx.partition_path,
                partition_payload=ctx.partition_payload,
                metadata=ctx.metadata,
                feature_count=ctx.feature_count,
                split_hash=ctx.split_hash,
            )
        )
    else:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.MISSING_PARTITION_MANIFEST,
                message=(
                    f"Partition manifest is missing for {ctx.run_id}: "
                    f"{ctx.partition_path}"
                ),
                exact_command=BLOCKED_RESUME_COMMAND,
            )
        )


def _append_convergence_record(
    acc: _AuditAccumulator,
    ctx: _RunContext,
) -> None:
    acc.convergence_records.append(
        ConvergenceAuditRecord(
            stage=ctx.stage,
            seed=ctx.seed,
                        checkpoint_path=str(ctx.checkpoint),
            convergence_round=ctx.convergence_round,
            convergence_criterion_value=ctx.convergence_value,
            convergence_status=ctx.convergence_status,
            curve_path=ctx.curve_path,
        )
    )


def _process_run(
    metrics_path: Path,
    base_dir: Path,
    acc: _AuditAccumulator,
    *,
    git_commit: str,
    timestamp: str,
    scoring_hash: str,
    threshold_hash: str,
    metrics_hash: str,
    cfg: DatpConfig,
    data_root: Path | None = None,
) -> None:
    """Process a single metrics file and populate the audit accumulator."""
    ctx = _load_run_context(metrics_path, base_dir, acc, data_root)
    if ctx is None:
        return

    _process_partition_audit(acc, ctx)
    threshold_state = _process_thresholds(acc, ctx, cfg)
    _process_per_client_metrics(acc, ctx, threshold_state)
    _build_run_manifest(
        acc,
        ctx,
        git_commit=git_commit,
        timestamp=timestamp,
        scoring_hash=scoring_hash,
        threshold_hash=threshold_hash,
        metrics_hash=metrics_hash,
        threshold_aggregation_method=threshold_state.threshold_aggregation_method,
    )
    _append_convergence_record(acc, ctx)
    _process_score_hashes(acc, ctx)
    _process_homogeneity(acc, ctx, cfg, threshold_state.cal_errors)
