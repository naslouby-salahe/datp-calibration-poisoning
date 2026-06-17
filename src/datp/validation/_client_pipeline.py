from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from datp.config.models import DatpConfig
from datp.core.enums import (
    BASELINE_THRESHOLD_SOURCE,
    CONTROLLED_BASELINES,
    B0NormalizationMode,
    Baseline,
    NormalizationScope,
    Regime,
    ScoringStage,
    ThresholdAggregationMethod,
    ThresholdSource,
)
from datp.core.metric_enums import ConfusionKey, MetricName, PayloadKey
from datp.core.provenance import array_hash
from datp.core.types import ThresholdResult
from datp.data.paths import prepared_root_for_regime
from datp.evaluation.metrics import compute_per_attack_tpr
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
    _AUDIT_RESULTS_COMMAND,
    AUDIT_SCHEMA_VERSION,
    BINARY_ATTACK_LABEL,
    BLOCKED_RESUME_COMMAND,
    BLOCKED_RESUME_REGIME_A_COMMAND,
    DEFAULT_COVERAGE_RATIO,
    DIAGNOSTIC_REGIME_A_COMMAND,
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
                regime=ctx.regime,
                baseline=ctx.baseline,
                alpha=ctx.alpha_text,
                client_id=ct.client_id,
                threshold_value=float(ct.threshold),
                threshold_source=(
                    ThresholdSource.TAU_GLOBAL_FALLBACK
                    if ct.calibration_pending
                    else BASELINE_THRESHOLD_SOURCE[ctx.baseline]
                ),
                calibration_pending=ct.calibration_pending,
                tau_global=float(threshold_result.tau_global),
                threshold_aggregation_method=_lookup_threshold_agg(ctx.baseline),
                local_tau_i=local_taus.get(ct.client_id),
            )
        )
    return client_thresholds


def _extract_b4_fingerprint(
    fp: Sequence[float],
) -> tuple[float | None, float | None, float | None, float | None]:
    """Extract B4 fingerprint scalars with guard clauses for each position."""
    n = len(fp)
    return (
        float(fp[0]) if n > 0 else None,
        float(fp[1]) if n > 1 else None,
        float(fp[2]) if n > 2 else None,
        float(fp[3]) if n > 3 else None,
    )


def _build_b4_cluster_records(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    threshold_result: ThresholdResult,
) -> None:
    """Build ClusterAssignmentRecord entries for B4 baseline."""
    if ctx.baseline != Baseline.B4 or not threshold_result.metadata.b4:
        return
    for cluster_id, info in threshold_result.metadata.b4.cluster_info.items():
        for client_id in info.members:
            fp = threshold_result.metadata.b4.fingerprints.get(client_id, [])
            fp_mean, fp_std, fp_skew, fp_p95 = _extract_b4_fingerprint(fp)
            acc.cluster_records.append(
                ClusterAssignmentRecord(
                    run_id=ctx.run_id,
                    seed=ctx.seed,
                    regime=ctx.regime,
                    alpha=ctx.alpha_text,
                    client_id=client_id,
                    cluster_id=cluster_id,
                    threshold_value=float(info.tau_cluster),
                    fingerprint_mean=fp_mean,
                    fingerprint_std=fp_std,
                    fingerprint_skew=fp_skew,
                    fingerprint_p95=fp_p95,
                    k_selected=threshold_result.metadata.b4.k,
                    silhouette=threshold_result.metadata.b4.silhouette,
                    silhouette_scores=threshold_result.metadata.b4.silhouette_scores,
                )
            )


def _emit_b3_dispersion_warnings(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    threshold_result: ThresholdResult,
    cfg: DatpConfig,
) -> None:
    """Emit B3 family dispersion warnings when within-family variance exceeds threshold."""
    if ctx.baseline != Baseline.B3 or not threshold_result.metadata.b3:
        return
    for family, info in threshold_result.metadata.b3.family_info.items():
        if info.threshold_variance > cfg.quality_gates.b3_dispersion_threshold:
            acc.warnings.append(
                WarningRecord(
                    severity=AuditSeverity.WARNING,
                    code=WarningCode.B3_TAXONOMY_TOO_COARSE,
                    message=f"{ctx.run_id} family {family} has high within-family threshold dispersion.",
                )
            )


def _emit_b1_not_pooled_warning(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    threshold_result: ThresholdResult,
    cal_errors: dict[str, np.ndarray],
    cfg: DatpConfig,
) -> None:
    """Emit B1 warning when tau_global is arithmetic mean, not pooled percentile."""
    if ctx.baseline != Baseline.B1:
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
                code=WarningCode.B1_NOT_POOLED_PERCENTILE,
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
    if ctx.baseline not in CONTROLLED_BASELINES:
        return _ThresholdState.empty(ctx.baseline)

    arrays = _load_score_arrays(acc, ctx, cfg)
    if arrays.threshold_result is None:
        return _ThresholdState(
            client_thresholds={},
            threshold_aggregation_method=_lookup_threshold_agg(ctx.baseline),
            test_benign_scores=arrays.test_benign_scores,
            test_attack_scores=arrays.test_attack_scores,
            cal_errors=arrays.cal_errors,
        )

    client_thresholds = _build_threshold_records(
        acc, ctx, arrays.threshold_result, arrays.cal_errors, cfg
    )
    _build_b4_cluster_records(acc, ctx, arrays.threshold_result)
    _emit_b3_dispersion_warnings(acc, ctx, arrays.threshold_result, cfg)
    _emit_b1_not_pooled_warning(
        acc, ctx, arrays.threshold_result, arrays.cal_errors, cfg
    )

    return _ThresholdState(
        client_thresholds=client_thresholds,
        threshold_aggregation_method=_lookup_threshold_agg(ctx.baseline),
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
        regime=ctx.regime,
        baseline=ctx.baseline,
        alpha=ctx.alpha_text,
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
        regime=ctx.regime,
        baseline=ctx.baseline,
        alpha=ctx.alpha_text,
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


def _compute_client_metric_row(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    threshold_state: _ThresholdState,
    row: dict[str, Any],
    eligible_ids: frozenset[str],
    pending_ids: frozenset[str],
    incomplete: frozenset[str],
    coverage_ratio: str,
) -> None:
    """Process a single client row: denominator audit, recomputation, client/attack records."""
    cm = row[PayloadKey.CONFUSION_MATRIX] if PayloadKey.CONFUSION_MATRIX in row else {}
    tp, fp, tn, fn = (int(cm[k]) if k in cm else 0 for k in tuple(ConfusionKey))
    client_id = str(row[PayloadKey.CLIENT_ID])
    n_benign = int(row[PayloadKey.N_BENIGN])
    n_attack = int(row[PayloadKey.N_ATTACK])
    fpr_den, tpr_den = fp + tn, tp + fn
    eval_incomplete = client_id in incomplete or n_attack == 0
    has_confusion = bool(cm)

    if not has_confusion and ctx.run_id not in acc.missing_confusion_warned:
        acc.missing_confusion_warned.add(ctx.run_id)
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.MISSING_CONFUSION_MATRIX,
                message=(
                    f"Per-client confusion matrices are missing for {ctx.run_id}; "
                    "denominator gates cannot be verified."
                ),
                exact_command=BLOCKED_RESUME_COMMAND,
            )
        )

    fpr_ok = (
        has_confusion
        and fpr_den == n_benign
        and n_benign > 0
        and math.isfinite(float(row[MetricName.FPR]))
    )
    tpr_ok = (
        has_confusion
        and tpr_den == n_attack
        and n_attack > 0
        and math.isfinite(float(row[MetricName.TPR]))
    )

    fpr_status, tpr_status, macro_f1_status = _compute_denominator_status(
        has_confusion,
        eval_incomplete,
        fpr_ok,
        tpr_ok,
    )

    acc.denominator_records.append(
        MetricDenominatorAuditRecord(
            run_id=ctx.run_id,
            seed=ctx.seed,
            regime=ctx.regime,
            baseline=ctx.baseline,
            alpha=ctx.alpha_text,
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

    if has_confusion:
        append_recomputation_records(
            acc.recomputation_records,
            RecomputationParams(
                run_id=ctx.run_id,
                seed=ctx.seed,
                regime=ctx.regime,
                baseline=ctx.baseline,
                alpha=ctx.alpha_text,
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
                eligible=client_id in eligible_ids,
                calibration_pending=client_id in pending_ids,
                evaluation_incomplete=eval_incomplete,
                coverage_ratio=coverage_ratio,
            ),
        )
    )
    acc.attack_records.append(
        _build_attack_metric_record(
            ctx,
            client_id,
            row,
            eval_incomplete,
            tp,
            n_attack,
        )
    )


def _compute_per_attack_families(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    threshold_state: _ThresholdState,
    row: dict[str, Any],
    eval_incomplete: bool,
) -> None:
    """Process per-attack-family records for a single client (Regime B / CICIoT2023 only)."""
    if eval_incomplete:
        return
    client_id = str(row[PayloadKey.CLIENT_ID])
    raw_attack_scores = threshold_state.test_attack_scores.get(client_id)
    if raw_attack_scores is None:
        return
    attack_labels = _load_client_attack_labels(
        ctx.regime,
        client_id,
        prepared_root_for_regime(
            ctx.regime,
            base_dir=ctx.data_root,
            seed=ctx.seed,
            alpha=ctx.alpha,
        ),
    )
    if attack_labels is None or attack_labels.size == 0:
        return
    from datp.data.datasets.ciciot2023.spec import (
        attack_family as _attack_family,  # noqa: PLC0415
    )

    threshold_val = threshold_state.client_thresholds.get(client_id)
    if threshold_val is None:
        return
    for pat in compute_per_attack_tpr(
        client_id,
        raw_attack_scores,
        attack_labels,
        threshold_val,
        _attack_family,
    ):
        pat_status = (
            DenominatorStatus.FAIL if pat.family is None else DenominatorStatus.PASS
        )
        acc.attack_records.append(
            PerAttackMetricRecord(
                run_id=ctx.run_id,
                seed=ctx.seed,
                regime=ctx.regime,
                baseline=ctx.baseline,
                alpha=ctx.alpha_text,
                client_id=pat.client_id,
                attack_label=pat.attack_label,
                status=pat_status,
                tpr=pat.tpr if math.isfinite(pat.tpr) else None,
                detected_count=pat.detected_count,
                denominator=pat.denominator,
            )
        )


def _compute_aggregate_stats(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    eligible_ids: frozenset[str],
    incomplete: frozenset[str],
    coverage_ratio: str,
) -> None:
    """Compute companion records, worst clients, and cell panel for a single run."""
    eligible_pairs_fpr = [
        (str(r[PayloadKey.CLIENT_ID]), float(r[MetricName.FPR]))
        for r in ctx.normalized_clients
        if r[PayloadKey.CLIENT_ID] in eligible_ids and MetricName.FPR in r
    ]
    tprs = [
        (str(r[PayloadKey.CLIENT_ID]), float(r[MetricName.TPR]))
        for r in ctx.normalized_clients
        if r[PayloadKey.CLIENT_ID] in eligible_ids
        and MetricName.TPR in r
        and str(r[PayloadKey.CLIENT_ID]) not in incomplete
    ]
    macro_f1s = [
        (str(r[PayloadKey.CLIENT_ID]), float(r[MetricName.MACRO_F1]))
        for r in ctx.normalized_clients
        if r[PayloadKey.CLIENT_ID] in eligible_ids and MetricName.MACRO_F1 in r
    ]
    balanced_accuracies = [
        (str(r[PayloadKey.CLIENT_ID]), float(r[MetricName.BALANCED_ACCURACY]))
        for r in ctx.normalized_clients
        if r[PayloadKey.CLIENT_ID] in eligible_ids
    ]

    eligible_fpr_values = [v for _, v in eligible_pairs_fpr]
    worst_fpr_id, worst_fpr_value = _argworst(
        eligible_pairs_fpr,
        WORST_CLIENT_DIRECTIONS[MetricName.FPR],
    )
    worst_tpr_id, worst_tpr_value = _argworst(
        tprs,
        WORST_CLIENT_DIRECTIONS[MetricName.TPR],
    )
    worst_f1_id, worst_f1_value = _argworst(
        macro_f1s,
        WORST_CLIENT_DIRECTIONS[MetricName.MACRO_F1],
    )
    worst_ba_id, worst_ba_value = _argworst(
        balanced_accuracies,
        WORST_CLIENT_DIRECTIONS[MetricName.BALANCED_ACCURACY],
    )

    cv_fpr_value = float(ctx.metrics[MetricName.CV_FPR])
    cv_fpr_record_value = cv_fpr_value if math.isfinite(cv_fpr_value) else None
    if math.isfinite(cv_fpr_value):
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

    mean_fpr_value = _finite_mean(eligible_fpr_values)
    std_fpr_value = _std_or_none(eligible_fpr_values)
    iqr_fpr_value = _iqr_or_none(eligible_fpr_values)
    macro_f1_p10_value = _percentile_or_none([v for _, v in macro_f1s], 10.0)

    acc.companion_records.append(
        FPRCompanionRecord(
            run_id=ctx.run_id,
            seed=ctx.seed,
            regime=ctx.regime,
            baseline=ctx.baseline,
            alpha=ctx.alpha_text,
            cv_fpr=cv_fpr_record_value,
            mean_fpr=mean_fpr_value,
            std_fpr=std_fpr_value,
            iqr_fpr=iqr_fpr_value,
            worst_client_fpr=worst_fpr_value,
            eligible_count=len(eligible_ids),
            client_count=ctx.client_count,
            coverage_ratio=coverage_ratio,
        )
    )
    for metric_name, (cid, value, pool) in {
        MetricName.FPR: (worst_fpr_id, worst_fpr_value, len(eligible_pairs_fpr)),
        MetricName.TPR: (worst_tpr_id, worst_tpr_value, len(tprs)),
        MetricName.MACRO_F1: (
            worst_f1_id,
            worst_f1_value,
            len(macro_f1s),
        ),
        MetricName.BALANCED_ACCURACY: (
            worst_ba_id,
            worst_ba_value,
            len(balanced_accuracies),
        ),
    }.items():
        acc.worst_client_records.append(
            WorstClientRecord(
                run_id=ctx.run_id,
                seed=ctx.seed,
                regime=ctx.regime,
                baseline=ctx.baseline,
                alpha=ctx.alpha_text,
                metric=metric_name,
                direction=WORST_CLIENT_DIRECTIONS[metric_name],
                worst_client_id=cid,
                worst_value=value,
                eligible_pool_size=pool,
            )
        )

    cv_tpr_raw = ctx.metrics.get(MetricName.CV_TPR)
    cv_tpr_value = (
        float(cv_tpr_raw)
        if cv_tpr_raw is not None and math.isfinite(float(cv_tpr_raw))
        else None
    )
    acc.cell_panel[(ctx.regime, ctx.seed, ctx.alpha_text, ctx.baseline)] = _CellPanel(
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
    incomplete = ctx.incomplete_ids
    eligible_ids = ctx.eligible_client_ids
    pending_ids = ctx.pending_client_ids

    for row in ctx.normalized_clients:
        _compute_client_metric_row(
            acc,
            ctx,
            threshold_state,
            row,
            eligible_ids,
            pending_ids,
            incomplete,
            coverage_ratio,
        )
        client_id = str(row[PayloadKey.CLIENT_ID])
        eval_incomplete = client_id in incomplete or int(row[PayloadKey.N_ATTACK]) == 0
        _compute_per_attack_families(acc, ctx, threshold_state, row, eval_incomplete)

    _compute_aggregate_stats(acc, ctx, eligible_ids, incomplete, coverage_ratio)


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
            dataset=_lookup_dataset(ctx.regime),
            regime=ctx.regime,
            baseline=ctx.baseline,
            alpha=ctx.alpha_text,
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
    acc.invariant_inputs[ctx.invariant_key][ctx.baseline] = InvariantHashes(
        split_hash=ctx.split_hash,
        model_hash=ctx.model_hash,
        encoder_hash=ctx.model_hash,
        scoring_code_hash=scoring_hash,
        metrics_code_hash=metrics_hash,
    )


def _process_b0_sanity(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    cfg: DatpConfig,
) -> None:
    """Emit B0 sanity-gate warnings."""
    if ctx.baseline != Baseline.B0:
        return
    b0_auroc = (
        float(ctx.metrics[MetricName.AUROC])
        if ctx.metrics.get(MetricName.AUROC) is not None
        else math.nan
    )
    b0_pr_auc = (
        float(ctx.metrics[MetricName.PR_AUC])
        if ctx.metrics.get(MetricName.PR_AUC) is not None
        else math.nan
    )
    norm_mode = ctx.metrics[PayloadKey.NORMALIZATION_MODE]
    if not math.isfinite(b0_auroc) or not math.isfinite(b0_pr_auc):
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.B0_SANITY_PR_AUC_PENDING,
                message=(
                    f"{ctx.run_id} B0 sanity gate is incomplete because AUROC or "
                    f"PR-AUC is missing (normalization_mode={norm_mode})."
                ),
                exact_command=BLOCKED_RESUME_REGIME_A_COMMAND,
            )
        )
        return
    if b0_auroc < cfg.quality_gates.b0_sanity_min:
        code = (
            WarningCode.B0_SANITY_LOW_AUROC
            if norm_mode == B0NormalizationMode.POOLED_ZSCORE
            else WarningCode.B0_WEAK_AUC_BLOCKS_PAPER
        )
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.FAIL,
                code=code,
                message=(
                    f"{ctx.run_id} B0 AUROC={b0_auroc:.4g} below threshold "
                    f"(normalization_mode={norm_mode})."
                ),
                exact_command=_AUDIT_RESULTS_COMMAND,
            )
        )
    elif b0_pr_auc < cfg.quality_gates.b0_sanity_min:
        code = (
            WarningCode.B0_SANITY_LOW_PR_AUC
            if norm_mode == B0NormalizationMode.POOLED_ZSCORE
            else WarningCode.B0_WEAK_AUC_BLOCKS_PAPER
        )
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.FAIL,
                code=code,
                message=(
                    f"{ctx.run_id} B0 PR-AUC={b0_pr_auc:.4g} below threshold "
                    f"(normalization_mode={norm_mode})."
                ),
                exact_command=_AUDIT_RESULTS_COMMAND,
            )
        )


def _process_score_hashes(
    acc: _AuditAccumulator,
    ctx: _RunContext,
) -> None:
    """Compute and store per-client score hashes for controlled baselines."""
    if ctx.baseline not in CONTROLLED_BASELINES or not ctx.score_root.exists():
        return
    cell_hashes: dict[tuple[ScoringStage, str], str] = {}
    for stage in ScoringStage:
        for score_path in _score_stage_files(ctx.score_root, stage):
            arr = _read_scores(score_path)
            cell_hashes[(stage, score_path.stem)] = array_hash(arr)
            if ctx.baseline == Baseline.B1:
                acc.recon_records.append(
                    _recon_summary(
                        run_id=ctx.run_id,
                        baseline=ctx.baseline,
                        seed=ctx.seed,
                        regime=ctx.regime,
                        alpha=ctx.alpha_text,
                        client_id=score_path.stem,
                        stage=stage,
                        arr=arr,
                    )
                )
    acc.score_hashes_by_cell[ctx.invariant_key][ctx.baseline] = cell_hashes


def _process_homogeneity(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    cfg: DatpConfig,
    cal_errors: dict[str, np.ndarray],
) -> None:
    """Compute CICIoT homogeneity audit for B1 + Regime B."""
    if not (
        ctx.baseline == Baseline.B1
        and ctx.score_root.exists()
        and ctx.regime == Regime.B
        and cal_errors
    ):
        return
    payload = compute_ciciot_homogeneity(
        cal_errors,
        n_bins=cfg.quality_gates.js_divergence_n_bins,
        threshold=cfg.quality_gates.ciciot_homogeneity_threshold,
    )
    acc.homogeneity_records.append(
        CICIoTHomogeneityRecord(
            regime=ctx.regime,
            seed=ctx.seed,
            alpha=ctx.alpha_text,
            baseline=ctx.baseline,
            n_clients_compared=payload.js_summary.n_compared,
            n_pairs=payload.js_summary.n_pairs,
            n_bins=payload.js_summary.n_bins,
            pairwise_js_mean=payload.js_summary.mean,
            pairwise_js_std=payload.js_summary.std,
            pairwise_js_p50=payload.js_summary.p50,
            pairwise_js_p95=payload.js_summary.p95,
            pairwise_js_max=payload.js_summary.max,
            fingerprint_method=FINGERPRINT_METHOD_BENIGN_RECON_ERROR_HISTOGRAM,
            homogeneity_verdict=payload.verdict,
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

    # ── Partition audit ──
    if ctx.partition_path.exists():
        acc.partition_audits[f"{ctx.regime}:{ctx.seed}:{ctx.alpha_text}"] = (
            _build_partition_audit(
                regime=ctx.regime,
                alpha_text=ctx.alpha_text,
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
                exact_command=DIAGNOSTIC_REGIME_A_COMMAND,
            )
        )

    # ── Threshold processing ──
    threshold_state = _process_thresholds(acc, ctx, cfg)

    # ── B0 threshold records (built from metrics, not score artifacts) ──
    if ctx.baseline == Baseline.B0:
        tau_key = (
            PayloadKey.TAU_B0
            if PayloadKey.TAU_B0 in ctx.metrics
            else MetricName.TAU_GLOBAL
        )
        tau = float(ctx.metrics[tau_key])
        pending_ids = ctx.pending_client_ids
        for row in ctx.normalized_clients:
            acc.threshold_records.append(
                ThresholdRecord(
                    run_id=ctx.run_id,
                    seed=ctx.seed,
                    regime=ctx.regime,
                    baseline=ctx.baseline,
                    alpha=ctx.alpha_text,
                    client_id=str(row[PayloadKey.CLIENT_ID]),
                    threshold_value=tau,
                    threshold_source=ThresholdSource.B0_POOLED,
                    calibration_pending=str(row[PayloadKey.CLIENT_ID]) in pending_ids,
                    tau_global=tau,
                    threshold_aggregation_method=_lookup_threshold_agg(Baseline.B0),
                    local_tau_i=None,
                )
            )

    # ── Per-client metrics ──
    _process_per_client_metrics(acc, ctx, threshold_state)

    # ── Manifest ──
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

    # ── B0 sanity ──
    _process_b0_sanity(acc, ctx, cfg)

    # ── Convergence record ──
    acc.convergence_records.append(
        ConvergenceAuditRecord(
            regime=ctx.regime,
            seed=ctx.seed,
            alpha=ctx.alpha_text,
            checkpoint_path=str(ctx.checkpoint),
            convergence_round=ctx.convergence_round,
            convergence_criterion_value=ctx.convergence_value,
            convergence_status=ctx.convergence_status,
            curve_path=ctx.curve_path,
        )
    )

    # ── Score hashes ──
    _process_score_hashes(acc, ctx)

    # ── CICIoT homogeneity ──
    _process_homogeneity(acc, ctx, cfg, threshold_state.cal_errors)
