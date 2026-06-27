"""Metric reproduction: re-derive thresholds, re-evaluate, and compare binary metrics."""

from __future__ import annotations

import dataclasses
import json
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from datp.artifacts.io import write_json_atomic
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactDir, ArtifactFile
from datp.config.compose import compose_config
from datp.config.models import DatpConfig
from datp.config.models import ExperimentStage
from datp.core.enums import (
    CONTROLLED_POLICIES,
    ConfusionKey,
    MetricName,
    PayloadKey,
    ScoringStage,
    ThresholdPolicy,
)
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.types import ThresholdResult
from datp.evaluation.metrics import EvaluationResult, evaluate_policy_run
from datp.scoring.loading import ScoreProvider, load_parquets_from_dir
from datp.thresholding.thresholds import _DeriveInput, derive_threshold
from datp.validation.discovery import iter_score_cells, parse_score_cell_dir
from datp.validation.enums import (
    AuditArtifact,
    AuditStatus,
    DenominatorStatus,
    MetricCheckCode,
    ValidationThreshold,
)
from datp.validation.schemas import (
    CellReproductionResult,
    MetricRecomputationRecord,
    PolicyReproductionResult,
    ValidationCheck,
)

SCALAR_METRIC_FIELDS: tuple[MetricName, ...] = (
    MetricName.CV_FPR,
    MetricName.CV_TPR,
    MetricName.MEAN_FPR,
    MetricName.STD_FPR,
    MetricName.IQR_FPR,
    MetricName.IQR_TPR,
    MetricName.MAX_MIN_FPR_GAP,
    MetricName.WORST_CLIENT_FPR,
    MetricName.WORST_BA,
    MetricName.P10_MACRO_F1,
    MetricName.TAU_GLOBAL,
)

CONFUSION_KEYS: tuple[str, ...] = tuple(ConfusionKey)
RECOMPUTATION_EPSILON = 1e-9
RECOMPUTE_METRICS = (
    MetricName.FPR,
    MetricName.TPR,
    MetricName.BALANCED_ACCURACY,
    MetricName.MACRO_F1,
)


@dataclasses.dataclass(frozen=True, slots=True)
class RecomputationParams:
    """Parameters needed to recompute binary classification metrics from raw confusion counts."""

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
class RecomputationResult:
    """Result of comparing a saved metric value against a recomputed value."""

    diff: float | None
    saved_value: float | None
    recomputed_value: float | None
    status: DenominatorStatus


def build_recomputation_record(
    params: RecomputationParams,
    metric: MetricName,
    *,
    saved_value: float | None = None,
    recomputed_value: float | None = None,
    abs_diff: float | None = None,
    status: DenominatorStatus,
) -> MetricRecomputationRecord:
    """Build a MetricRecomputationRecord from recomputation parameters and results."""
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


def compare_recomputation(saved: float | None, recomp: float) -> RecomputationResult:
    """Compare a saved metric value against a recomputed value with pass/fail status."""
    recomp_val = recomp if math.isfinite(recomp) else None

    if saved is not None and math.isfinite(saved) and math.isfinite(recomp):
        diff = abs(saved - recomp)
        status = (
            DenominatorStatus.PASS
            if diff <= RECOMPUTATION_EPSILON
            else DenominatorStatus.FAIL
        )
        return RecomputationResult(diff, saved, recomp_val, status)

    if saved is None or (not math.isfinite(saved) and not math.isfinite(recomp)):
        return RecomputationResult(None, saved, recomp_val, DenominatorStatus.PASS)

    return RecomputationResult(None, saved, recomp_val, DenominatorStatus.FAIL)


def compute_metric_status(
    metric: MetricName, params: RecomputationParams
) -> DenominatorStatus | None:
    """Return EXCLUDED_EVALUATION_INCOMPLETE when a metric's denominator is zero, else None."""
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
    """Recompute binary metrics from confusion counts and append comparison records."""
    from datp.evaluation.metrics import recompute_binary_metrics

    bm = recompute_binary_metrics(params.tp, params.fp, params.tn, params.fn)
    recomputed = {
        MetricName.FPR: bm.fpr,
        MetricName.TPR: bm.tpr,
        MetricName.BALANCED_ACCURACY: bm.balanced_accuracy,
        MetricName.MACRO_F1: bm.macro_f1,
    }
    saved = {
        MetricName.FPR: params.saved_fpr,
        MetricName.TPR: params.saved_tpr,
        MetricName.BALANCED_ACCURACY: params.saved_balanced_accuracy,
        MetricName.MACRO_F1: params.saved_macro_f1,
    }

    for metric in RECOMPUTE_METRICS:
        pre_status = compute_metric_status(metric, params)
        if pre_status is not None:
            records.append(
                build_recomputation_record(params, metric, status=pre_status)
            )
            continue

        cmp_result = compare_recomputation(saved[metric], recomputed[metric])
        records.append(
            build_recomputation_record(
                params,
                metric,
                saved_value=cmp_result.saved_value,
                recomputed_value=cmp_result.recomputed_value,
                abs_diff=cmp_result.diff,
                status=cmp_result.status,
            )
        )


def format_check_detail(
    field: str = "",
    expected: Any = None,
    actual: Any = None,
    abs_diff: float | None = None,
    tolerance: float | None = None,
    detail: str = "",
) -> str:
    """Format validation check details as a comma-separated key=value string."""
    parts = []
    if field:
        parts.append(f"field={field}")
    if expected is not None:
        parts.append(f"expected={expected}")
    if actual is not None:
        parts.append(f"actual={actual}")
    if abs_diff is not None:
        parts.append(f"diff={abs_diff:.4g}")
    if tolerance is not None:
        parts.append(f"tol={tolerance:.4g}")
    if detail:
        parts.append(detail)
    return ", ".join(parts)


def scalar_check(
    field: str,
    expected: float | None,
    actual: float | None,
    tolerance: float,
    code: MetricCheckCode = MetricCheckCode.SCALAR_WITHIN_TOLERANCE,
) -> ValidationCheck:
    """Compare expected and actual scalar values within tolerance, handling None and NaN."""
    if expected is None or actual is None:
        return ValidationCheck(
            code=code,
            status=AuditStatus.MISSING,
            detail=format_check_detail(
                field=field,
                expected=expected,
                actual=actual,
                tolerance=tolerance,
                detail="expected or actual is None",
            ),
        )

    if math.isnan(expected) and math.isnan(actual):
        return ValidationCheck(
            code=code,
            status=AuditStatus.PASS,
            detail=format_check_detail(
                field=field,
                expected=expected,
                actual=actual,
                abs_diff=0.0,
                tolerance=tolerance,
            ),
        )

    if math.isnan(expected) or math.isnan(actual):
        return ValidationCheck(
            code=code,
            status=AuditStatus.MISSING,
            detail=format_check_detail(
                field=field,
                expected=expected,
                actual=actual,
                tolerance=tolerance,
                detail="NaN encountered on only one side",
            ),
        )

    diff = abs(expected - actual)
    return ValidationCheck(
        code=code,
        status=AuditStatus.PASS if diff <= tolerance else AuditStatus.FAIL,
        detail=format_check_detail(
            field=field,
            expected=expected,
            actual=actual,
            abs_diff=diff,
            tolerance=tolerance,
        ),
    )


def exact_match_check(
    code: MetricCheckCode, field: str, expected: Any, actual: Any
) -> ValidationCheck:
    """Check that expected and actual values match exactly, returning a pass/fail ValidationCheck."""
    if expected == actual:
        return ValidationCheck(
            code=code,
            status=AuditStatus.PASS,
            detail=format_check_detail(field=field, expected=expected, actual=actual),
        )
    return ValidationCheck(
        code=code,
        status=AuditStatus.FAIL,
        detail=format_check_detail(
            field=field,
            expected=expected,
            actual=actual,
            detail=f"expected={expected!r}, actual={actual!r}",
        ),
    )


def id_set_check(
    code: MetricCheckCode, field: str, expected: list[str], actual: list[str]
) -> ValidationCheck:
    """Check that two lists contain the same set of IDs, reporting differences on failure."""
    expected_set, actual_set = set(expected), set(actual)
    if expected_set == actual_set:
        return ValidationCheck(
            code=code,
            status=AuditStatus.PASS,
            detail=format_check_detail(
                field=field, expected=sorted(expected_set), actual=sorted(actual_set)
            ),
        )
    return ValidationCheck(
        code=code,
        status=AuditStatus.FAIL,
        detail=format_check_detail(
            field=field,
            expected=sorted(expected_set),
            actual=sorted(actual_set),
            detail=f"only_in_expected={sorted(expected_set - actual_set)}, only_in_actual={sorted(actual_set - expected_set)}",
        ),
    )


def confusion_check(
    expected_per_client: Mapping[str, Mapping[str, int]],
    actual_per_client: Mapping[str, Mapping[str, int]],
) -> ValidationCheck:
    """Compare per-client confusion matrices and return a pass/fail check with mismatches listed."""
    diffs = [
        f"{cid}.{key}: expected={expected_per_client[cid][key]}, actual={actual_per_client[cid][key]}"
        for cid in sorted(set(expected_per_client) & set(actual_per_client))
        for key in CONFUSION_KEYS
        if expected_per_client[cid][key] != actual_per_client[cid][key]
    ]

    if diffs:
        return ValidationCheck(
            code=MetricCheckCode.PER_CLIENT_CONFUSION_EXACT,
            status=AuditStatus.FAIL,
            detail=format_check_detail(
                field=f"{PayloadKey.PER_CLIENT}.{PayloadKey.CONFUSION_MATRIX}",
                detail=f"{len(diffs)} mismatches; first: {diffs[0]}",
            ),
        )
    return ValidationCheck(
        code=MetricCheckCode.PER_CLIENT_CONFUSION_EXACT,
        status=AuditStatus.PASS,
        detail=format_check_detail(
            field=f"{PayloadKey.PER_CLIENT}.{PayloadKey.CONFUSION_MATRIX}"
        ),
    )


def thresholds_check(
    expected_per_client: dict[str, float],
    actual_per_client: dict[str, float],
    tolerance: float,
) -> ValidationCheck:
    """Compare per-client thresholds within tolerance and return a pass/fail check."""
    diffs = [
        (cid, exp, act, abs(exp - act))
        for cid in sorted(set(expected_per_client) & set(actual_per_client))
        for exp, act in [
            (float(expected_per_client[cid]), float(actual_per_client[cid]))
        ]
        if abs(exp - act) > tolerance
    ]

    if diffs:
        cid, exp, act, diff = diffs[0]
        return ValidationCheck(
            code=MetricCheckCode.PER_CLIENT_THRESHOLDS_WITHIN_TOLERANCE,
            status=AuditStatus.FAIL,
            detail=format_check_detail(
                field=f"{PayloadKey.PER_CLIENT}.{PayloadKey.THRESHOLD_VALUE}",
                tolerance=tolerance,
                detail=f"{len(diffs)} threshold mismatches; first: {cid} expected={exp}, actual={act}, diff={diff}",
            ),
        )
    return ValidationCheck(
        code=MetricCheckCode.PER_CLIENT_THRESHOLDS_WITHIN_TOLERANCE,
        status=AuditStatus.PASS,
        detail=format_check_detail(
            field=f"{PayloadKey.PER_CLIENT}.{PayloadKey.THRESHOLD_VALUE}",
            tolerance=tolerance,
        ),
    )


def evaluate_overall_status(checks: list[ValidationCheck]) -> AuditStatus:
    """Derive an overall AuditStatus: FAIL > PARTIAL > PASS."""
    statuses = {c.status for c in checks}
    if AuditStatus.FAIL in statuses:
        return AuditStatus.FAIL
    if AuditStatus.MISSING in statuses:
        return AuditStatus.PARTIAL
    return AuditStatus.PASS


def read_metrics_json(path: Path) -> dict[str, Any]:
    """Read and parse a JSON metrics file from the given path."""
    return json.loads(path.read_text())


def normalize_per_client(stored: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize stored per-client data from dict or list form into a uniform list."""
    per_client = stored[PayloadKey.PER_CLIENT]
    return (
        [dict(v, client_id=k) for k, v in per_client.items()]
        if isinstance(per_client, dict)
        else list(per_client)
    )


def evaluate_policy(
    threshold_result: ThresholdResult,
    score_provider: ScoreProvider,
    stage: ExperimentStage,
    seed: int,
) -> tuple[EvaluationResult, dict[str, float]]:
    """Evaluate a threshold policy run and return the EvaluationResult with client thresholds."""
    evaluation = evaluate_policy_run(
        threshold_result.client_thresholds,
        Path(""),
        stage,
        seed,
        score_provider=score_provider,
    )
    return evaluation, {
        ct.client_id: float(ct.threshold) for ct in threshold_result.client_thresholds
    }


def compute_global_tau(
    cal_errors: dict[str, np.ndarray], cfg: DatpConfig, *, seed: int = 0
) -> float:
    """Derive the global threshold tau from calibration errors using configured parameters."""
    return float(
        derive_threshold(
            _DeriveInput(
                policy=ThresholdPolicy.GLOBAL_THRESHOLD,
                client_errors=cal_errors,
                n_min=cfg.threshold.n_min,
                q=cfg.threshold.q,
                tau_global=0.0,
                threshold_cfg=cfg.threshold,
                seed=seed,
            )
        ).tau_global
    )


def stored_per_client_map(stored: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build a client-id-keyed map from stored per-client data."""
    return {row[PayloadKey.CLIENT_ID]: row for row in normalize_per_client(stored)}


def stored_scalar(stored: dict[str, Any], field: str) -> Any:
    """Retrieve a scalar from stored metrics, checking top-level and aggregate_metrics fallback."""
    return stored.get(field) or stored.get("aggregate_metrics", {}).get(field)


def scalar_checks_for_policy_run(
    stored: dict[str, Any],
    evaluation: EvaluationResult,
    threshold_result: ThresholdResult,
) -> list[ValidationCheck]:
    """Build scalar metric validation checks comparing stored values against recomputed results."""
    actuals = {
        MetricName.CV_FPR: evaluation.cv_fpr,
        MetricName.CV_TPR: evaluation.cv_tpr,
        MetricName.MEAN_FPR: evaluation.mean_fpr,
        MetricName.STD_FPR: evaluation.std_fpr,
        MetricName.IQR_FPR: evaluation.iqr_fpr,
        MetricName.IQR_TPR: evaluation.iqr_tpr,
        MetricName.MAX_MIN_FPR_GAP: evaluation.max_min_fpr_gap,
        MetricName.WORST_CLIENT_FPR: evaluation.worst_client_fpr,
        MetricName.WORST_BA: evaluation.worst_ba,
        MetricName.P10_MACRO_F1: evaluation.p10_macro_f1,
        MetricName.TAU_GLOBAL: float(threshold_result.tau_global),
    }

    checks = [
        scalar_check(
            f,
            stored_scalar(stored, f),
            actuals[f],
            ValidationThreshold.SCALAR_METRIC_TOLERANCE.value,
        )
        for f in SCALAR_METRIC_FIELDS
    ]
    checks.append(
        scalar_check(
            PayloadKey.COVERAGE_RATIO,
            stored_scalar(stored, PayloadKey.COVERAGE_RATIO),
            evaluation.coverage_ratio,
            ValidationThreshold.COVERAGE_RATIO_TOLERANCE.value,
            MetricCheckCode.COVERAGE_RATIO_WITHIN_TOLERANCE,
        )
    )
    return checks


def count_and_id_checks(
    stored: dict[str, Any], evaluation: EvaluationResult
) -> list[ValidationCheck]:
    """Build exact-match checks for client counts and ID sets from stored versus evaluated data."""
    return [
        exact_match_check(
            MetricCheckCode.ELIGIBLE_COUNT_EXACT,
            PayloadKey.ELIGIBLE_COUNT,
            int(stored[PayloadKey.ELIGIBLE_COUNT]),
            int(evaluation.eligible_count),
        ),
        exact_match_check(
            MetricCheckCode.PENDING_COUNT_EXACT,
            PayloadKey.PENDING_COUNT,
            int(stored[PayloadKey.PENDING_COUNT]),
            int(len(evaluation.pending_ids)),
        ),
        exact_match_check(
            MetricCheckCode.CLIENT_COUNT_EXACT,
            PayloadKey.CLIENT_COUNT,
            int(stored[PayloadKey.CLIENT_COUNT]),
            int(evaluation.client_count),
        ),
        id_set_check(
            MetricCheckCode.ELIGIBLE_IDS_EXACT,
            PayloadKey.ELIGIBLE_IDS,
            list(map(str, stored[PayloadKey.ELIGIBLE_IDS])),
            list(map(str, evaluation.eligible_ids)),
        ),
        id_set_check(
            MetricCheckCode.PENDING_IDS_EXACT,
            PayloadKey.PENDING_IDS,
            list(map(str, stored[PayloadKey.PENDING_IDS])),
            list(map(str, evaluation.pending_ids)),
        ),
    ]


def per_client_checks(
    stored_per_client: dict[str, dict[str, Any]],
    evaluation: EvaluationResult,
    client_thresholds_actual: dict[str, float],
) -> list[ValidationCheck]:
    """Build per-client confusion and threshold validation checks against recomputed results."""
    actual_per_client = {cr.client_id: cr for cr in evaluation.clients}

    expected_confusion = {
        cid: {k: int(row[PayloadKey.CONFUSION_MATRIX][k]) for k in CONFUSION_KEYS}
        for cid, row in stored_per_client.items()
        if PayloadKey.CONFUSION_MATRIX in row
    }

    actual_confusion = {
        cid: {
            ConfusionKey.TP.value: cr.confusion.tp,
            ConfusionKey.FP.value: cr.confusion.fp,
            ConfusionKey.TN.value: cr.confusion.tn,
            ConfusionKey.FN.value: cr.confusion.fn,
        }
        for cid, cr in actual_per_client.items()
    }

    expected_thresholds = {
        cid: float(row[PayloadKey.THRESHOLD_VALUE])
        for cid, row in stored_per_client.items()
        if row.get(PayloadKey.THRESHOLD_VALUE) is not None
    }

    return [
        confusion_check(expected_confusion, actual_confusion),
        thresholds_check(
            expected_thresholds,
            client_thresholds_actual,
            ValidationThreshold.SCALAR_METRIC_TOLERANCE.value,
        ),
    ]


def build_policy_checks(
    *,
    stored: dict[str, Any],
    evaluation: EvaluationResult,
    threshold_result: ThresholdResult,
    client_thresholds_actual: dict[str, float],
) -> list[ValidationCheck]:
    """Assemble scalar, count, ID-set, and per-client checks for a single policy."""
    return (
        scalar_checks_for_policy_run(stored, evaluation, threshold_result)
        + count_and_id_checks(stored, evaluation)
        + per_client_checks(
            stored_per_client_map(stored), evaluation, client_thresholds_actual
        )
    )


def serialize_recomputed(
    evaluation: EvaluationResult,
    threshold_result: ThresholdResult,
    client_thresholds: dict[str, float],
) -> dict[str, Any]:
    """Serialize evaluation and threshold results into a JSON-compatible dict."""
    return {
        PayloadKey.POLICY: evaluation.policy.value,
        PayloadKey.STAGE: evaluation.stage.value,
        PayloadKey.SEED: evaluation.seed,
        PayloadKey.DATASET: evaluation.dataset,
        MetricName.TAU_GLOBAL: float(threshold_result.tau_global),
        PayloadKey.COVERAGE_RATIO: evaluation.coverage_ratio,
        MetricName.CV_FPR: evaluation.cv_fpr,
        MetricName.CV_TPR: evaluation.cv_tpr,
        MetricName.MEAN_FPR: evaluation.mean_fpr,
        MetricName.STD_FPR: evaluation.std_fpr,
        MetricName.IQR_FPR: evaluation.iqr_fpr,
        MetricName.IQR_TPR: evaluation.iqr_tpr,
        MetricName.MAX_MIN_FPR_GAP: evaluation.max_min_fpr_gap,
        MetricName.WORST_CLIENT_FPR: evaluation.worst_client_fpr,
        MetricName.WORST_CLIENT_ID: evaluation.worst_client_id,
        MetricName.WORST_BA: evaluation.worst_ba,
        MetricName.P10_MACRO_F1: evaluation.p10_macro_f1,
        PayloadKey.CLIENT_COUNT: evaluation.client_count,
        PayloadKey.ELIGIBLE_COUNT: evaluation.eligible_count,
        PayloadKey.PENDING_COUNT: len(evaluation.pending_ids),
        PayloadKey.ELIGIBLE_IDS: sorted(evaluation.eligible_ids),
        PayloadKey.PENDING_IDS: sorted(evaluation.pending_ids),
        PayloadKey.PER_CLIENT: {
            cr.client_id: {
                MetricName.FPR: cr.metrics.fpr,
                MetricName.TPR: cr.metrics.tpr,
                MetricName.BALANCED_ACCURACY: cr.metrics.balanced_accuracy,
                MetricName.MACRO_F1: cr.metrics.macro_f1,
                PayloadKey.N_BENIGN: cr.n_benign,
                PayloadKey.N_ATTACK: cr.n_attack,
                PayloadKey.CONFUSION_MATRIX: {
                    ConfusionKey.TP.value: cr.confusion.tp,
                    ConfusionKey.FP.value: cr.confusion.fp,
                    ConfusionKey.TN.value: cr.confusion.tn,
                    ConfusionKey.FN.value: cr.confusion.fn,
                },
                PayloadKey.THRESHOLD_VALUE: client_thresholds[cr.client_id],
            }
            for cr in evaluation.clients
        },
    }


def select_stored_summary(stored: dict[str, Any]) -> dict[str, Any]:
    """Extract a subset of known keys from stored metrics for summary comparison."""
    keys = (
        PayloadKey.POLICY,
        PayloadKey.STAGE,
        PayloadKey.SEED,
        PayloadKey.DATASET,
        MetricName.TAU_GLOBAL,
        PayloadKey.COVERAGE_RATIO,
        MetricName.CV_FPR,
        MetricName.CV_TPR,
        MetricName.MEAN_FPR,
        MetricName.STD_FPR,
        MetricName.IQR_FPR,
        MetricName.IQR_TPR,
        MetricName.MAX_MIN_FPR_GAP,
        MetricName.WORST_CLIENT_FPR,
        MetricName.WORST_CLIENT_ID,
        MetricName.WORST_BA,
        MetricName.P10_MACRO_F1,
        PayloadKey.CLIENT_COUNT,
        PayloadKey.ELIGIBLE_COUNT,
        PayloadKey.PENDING_COUNT,
        PayloadKey.ELIGIBLE_IDS,
        PayloadKey.PENDING_IDS,
    )
    return {k: stored.get(k) for k in keys}


@dataclasses.dataclass(frozen=True, slots=True)
class CellReproductionContext:
    """Shared context for reproducing metrics across all policies of a single training cell."""

    cell: TrainingCellId
    layout: ArtifactLayout
    cal_errors: dict[str, np.ndarray]
    score_provider: ScoreProvider
    cfg: DatpConfig
    tau_global_ref: float


def reproduce_one_policy(
    policy: ThresholdPolicy,
    ctx: CellReproductionContext,
) -> PolicyReproductionResult | None:
    """Recompute metrics for one policy and compare against stored results."""
    metrics_path = (
        ctx.layout.policy_run(PolicyRunId(cell=ctx.cell, policy=policy)).result_dir
        / ArtifactFile.METRICS
    )
    if not metrics_path.exists():
        return None

    stored = read_metrics_json(metrics_path)
    threshold_result = derive_threshold(
        _DeriveInput(
            policy=policy,
            client_errors=ctx.cal_errors,
            n_min=ctx.cfg.threshold.n_min,
            q=ctx.cfg.threshold.q,
            tau_global=ctx.tau_global_ref,
            threshold_cfg=ctx.cfg.threshold,
            seed=ctx.cell.seed,
        )
    )
    evaluation, client_thresholds = evaluate_policy(
        threshold_result, ctx.score_provider, ctx.cell.stage, ctx.cell.seed
    )
    checks = build_policy_checks(
        stored=stored,
        evaluation=evaluation,
        threshold_result=threshold_result,
        client_thresholds_actual=client_thresholds,
    )

    return PolicyReproductionResult(
        policy=policy,
        status=evaluate_overall_status(checks),
        metrics_path=str(metrics_path),
        recomputed=serialize_recomputed(evaluation, threshold_result, client_thresholds),
        stored=select_stored_summary(stored),
        checks=checks,
    )


def reproduce_cell_metrics(
    cell_dir: Path, base_dir: Path, *, config: DatpConfig | None = None
) -> CellReproductionResult:
    """Recompute and compare metrics for all policies in a single training cell."""
    cell_dir, base_dir = cell_dir.resolve(), base_dir.resolve()
    location = parse_score_cell_dir(base_dir / ArtifactDir.SCORES, cell_dir)
    stage, seed = location.cell.stage, location.cell.seed

    layout = ArtifactLayout(base_dir=base_dir, stage=stage)
    cell = TrainingCellId(stage=stage, seed=seed)
    score_root = layout.score_cell(cell).score_dir
    cal_errors = load_parquets_from_dir(score_root / ScoringStage.CAL)

    cfg = config or compose_config(
        stage=stage, policy=ThresholdPolicy.GLOBAL_THRESHOLD, seed=seed
    )
    ctx = CellReproductionContext(
        cell=cell,
        layout=layout,
        cal_errors=cal_errors,
        score_provider=ScoreProvider(score_root),
        cfg=cfg,
        tau_global_ref=compute_global_tau(cal_errors, cfg, seed=seed),
    )

    policy_results = []
    missing_policies = []
    for policy in CONTROLLED_POLICIES:
        result = reproduce_one_policy(policy, ctx)
        (policy_results if result else missing_policies).append(result or policy)

    return CellReproductionResult(
        cell=cell,
        overall_status=aggregate_overall(
            [pr.status for pr in policy_results], missing_policies
        ),
        policies=policy_results,
        missing_policies=missing_policies,
    )


def aggregate_overall(
    statuses: list[AuditStatus], missing_policies: list[ThresholdPolicy]
) -> AuditStatus:
    """Determine overall cell status from policy-level statuses and missing policies."""
    if AuditStatus.FAIL in statuses:
        return AuditStatus.FAIL
    if (
        missing_policies
        or AuditStatus.MISSING in statuses
        or AuditStatus.PARTIAL in statuses
    ):
        return AuditStatus.PARTIAL
    return AuditStatus.PASS if statuses else AuditStatus.MISSING


def reproduce_all_cells(
    base_dir: Path, *, config: DatpConfig | None = None, write_reports: bool = False
) -> list[CellReproductionResult]:
    """Run metric reproduction across all score cells in parallel."""
    base_dir = base_dir.resolve()

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                reproduce_cell_metrics, loc.cell_dir, base_dir, config=config
            )
            for loc in iter_score_cells(base_dir)
        ]
        results = [f.result() for f in futures]

    if write_reports:
        for loc, result in zip(iter_score_cells(base_dir), results):
            write_json_atomic(
                loc.cell_dir / AuditArtifact.RECOMPUTED_METRICS,
                result.model_dump(mode="json"),
            )
        write_json_atomic(
            base_dir / ArtifactDir.SCORES / AuditArtifact.RECOMPUTED_METRICS_INDEX,
            {"cells": [r.model_dump(mode="json") for r in results]},
        )
    return results
