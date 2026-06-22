"""Per-cell metric reproduction: recompute threshold policies from stored scores and compare to stored metrics.json.

Reuses canonical threshold computation (``thresholding.thresholds.derive_threshold``),
canonical metric computation (``evaluation.metrics``), and canonical score loading
(``evaluation.score_loading``). Does not retrain, re-score, or modify any formula.
"""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import enum
import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from datp.artifacts.io import write_json_atomic
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactDir, ArtifactFile
from datp.config.compose import compose_config
from datp.config.models import DatpConfig
from datp.config.stages import ExperimentStage
from datp.core.enums import (
    CONTROLLED_POLICIES,
    ScoringStage,
)
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.metric_enums import ConfusionKey, MetricName, PayloadKey
from datp.core.types import ThresholdResult
from datp.evaluation.metrics import (
    EvaluationResult,
    evaluate_policy_run,
)
from datp.scoring.loading import ScoreProvider, load_parquets_from_dir
from datp.thresholding.thresholds import _DeriveInput, derive_threshold
from datp.validation.constants import (
    COVERAGE_RATIO_TOLERANCE,
    RECOMPUTED_METRICS_INDEX_JSON,
    RECOMPUTED_METRICS_JSON,
    SCALAR_METRIC_TOLERANCE,
)
from datp.validation.discovery import iter_score_cells, parse_score_cell_dir
from datp.validation.enums import AuditStatus
from datp.validation.schemas import ValidationCheck

_SCALAR_METRIC_FIELDS: tuple[MetricName, ...] = (
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

_CONFUSION_KEYS: tuple[str, ...] = tuple(ConfusionKey)


class MetricCheckCode(enum.StrEnum):
    SCALAR_WITHIN_TOLERANCE = "scalar_within_tolerance"
    COVERAGE_RATIO_WITHIN_TOLERANCE = "coverage_ratio_within_tolerance"
    ELIGIBLE_COUNT_EXACT = "eligible_count_exact"
    PENDING_COUNT_EXACT = "pending_count_exact"
    ELIGIBLE_IDS_EXACT = "eligible_ids_exact"
    PENDING_IDS_EXACT = "pending_ids_exact"
    CLIENT_COUNT_EXACT = "client_count_exact"
    PER_CLIENT_CONFUSION_EXACT = "per_client_confusion_exact"
    PER_CLIENT_THRESHOLDS_WITHIN_TOLERANCE = "per_client_thresholds_within_tolerance"


def _format_check_detail(
    field: str = "",
    expected: Any = None,
    actual: Any = None,
    abs_diff: float | None = None,
    tolerance: float | None = None,
    detail: str = "",
) -> str:
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


class PolicyReproductionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    policy: ThresholdPolicy
    status: AuditStatus
    metrics_path: str
    recomputed: dict[str, Any]
    stored: dict[str, Any]
    checks: list[ValidationCheck]


class CellReproductionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)
    cell: TrainingCellId
    overall_status: AuditStatus
    policies: list[PolicyReproductionResult]
    missing_policies: list[ThresholdPolicy] = Field(default_factory=list)


def _abs_diff(expected: float | None, actual: float | None) -> float | None:
    if expected is None or actual is None:
        return None
    either_nan = (isinstance(expected, float) and math.isnan(expected)) or (
        isinstance(actual, float) and math.isnan(actual)
    )
    if either_nan:
        return None
    return abs(float(expected) - float(actual))


def _both_nan(expected: float | None, actual: float | None) -> bool:
    return (
        expected is not None
        and actual is not None
        and isinstance(expected, float)
        and isinstance(actual, float)
        and math.isnan(expected)
        and math.isnan(actual)
    )


def _scalar_check(
    field: str,
    expected: float | None,
    actual: float | None,
    tolerance: float,
    code: MetricCheckCode = MetricCheckCode.SCALAR_WITHIN_TOLERANCE,
) -> ValidationCheck:
    if _both_nan(expected, actual):
        return ValidationCheck(
            code=code,
            status=AuditStatus.PASS,
            detail=_format_check_detail(
                field=field,
                expected=expected,
                actual=actual,
                abs_diff=0.0,
                tolerance=tolerance,
            ),
        )
    if expected is None or actual is None:
        return ValidationCheck(
            code=code,
            status=AuditStatus.MISSING,
            detail=_format_check_detail(
                field=field,
                expected=expected,
                actual=actual,
                tolerance=tolerance,
                detail="expected or actual is None",
            ),
        )
    diff = _abs_diff(expected, actual)
    if diff is None:
        return ValidationCheck(
            code=code,
            status=AuditStatus.MISSING,
            detail=_format_check_detail(
                field=field,
                expected=expected,
                actual=actual,
                tolerance=tolerance,
                detail="NaN encountered on only one side",
            ),
        )
    status = AuditStatus.PASS if diff <= tolerance else AuditStatus.FAIL
    return ValidationCheck(
        code=code,
        status=status,
        detail=_format_check_detail(
            field=field,
            expected=expected,
            actual=actual,
            abs_diff=diff,
            tolerance=tolerance,
        ),
    )


def _exact_match_check(
    code: MetricCheckCode,
    field: str,
    expected: Any,
    actual: Any,
) -> ValidationCheck:
    if expected == actual:
        return ValidationCheck(
            code=code,
            status=AuditStatus.PASS,
            detail=_format_check_detail(field=field, expected=expected, actual=actual),
        )
    return ValidationCheck(
        code=code,
        status=AuditStatus.FAIL,
        detail=_format_check_detail(
            field=field,
            expected=expected,
            actual=actual,
            detail=f"expected={expected!r}, actual={actual!r}",
        ),
    )


def _id_set_check(
    code: MetricCheckCode,
    field: str,
    expected: list[str],
    actual: list[str],
) -> ValidationCheck:
    expected_set = set(expected)
    actual_set = set(actual)
    if expected_set == actual_set:
        return ValidationCheck(
            code=code,
            status=AuditStatus.PASS,
            detail=_format_check_detail(
                field=field, expected=sorted(expected_set), actual=sorted(actual_set)
            ),
        )
    return ValidationCheck(
        code=code,
        status=AuditStatus.FAIL,
        detail=_format_check_detail(
            field=field,
            expected=sorted(expected_set),
            actual=sorted(actual_set),
            detail=(
                f"only_in_expected={sorted(expected_set - actual_set)}, "
                f"only_in_actual={sorted(actual_set - expected_set)}"
            ),
        ),
    )


def _confusion_check(
    expected_per_client: Mapping[str, Mapping[str, int]],
    actual_per_client: Mapping[str, Mapping[str, int]],
) -> ValidationCheck:
    diffs: list[str] = []
    common = sorted(set(expected_per_client) & set(actual_per_client))
    for cid in common:
        for key in _CONFUSION_KEYS:
            exp = int(expected_per_client[cid][key])
            act = int(actual_per_client[cid][key])
            if exp != act:
                diffs.append(f"{cid}.{key}: expected={exp}, actual={act}")
    if diffs:
        return ValidationCheck(
            code=MetricCheckCode.PER_CLIENT_CONFUSION_EXACT,
            status=AuditStatus.FAIL,
            detail=_format_check_detail(
                field=f"{PayloadKey.PER_CLIENT}.{PayloadKey.CONFUSION_MATRIX}",
                detail=f"{len(diffs)} mismatches; first: {diffs[0]}",
            ),
        )
    return ValidationCheck(
        code=MetricCheckCode.PER_CLIENT_CONFUSION_EXACT,
        status=AuditStatus.PASS,
        detail=_format_check_detail(
            field=f"{PayloadKey.PER_CLIENT}.{PayloadKey.CONFUSION_MATRIX}"
        ),
    )


def _thresholds_check(
    expected_per_client: dict[str, float],
    actual_per_client: dict[str, float],
    tolerance: float,
) -> ValidationCheck:
    diffs: list[tuple[str, float, float, float]] = []
    for cid in sorted(set(expected_per_client) & set(actual_per_client)):
        exp = float(expected_per_client[cid])
        act = float(actual_per_client[cid])
        diff = abs(exp - act)
        if diff > tolerance:
            diffs.append((cid, exp, act, diff))
    if diffs:
        cid, exp, act, diff = diffs[0]
        return ValidationCheck(
            code=MetricCheckCode.PER_CLIENT_THRESHOLDS_WITHIN_TOLERANCE,
            status=AuditStatus.FAIL,
            detail=_format_check_detail(
                field=f"{PayloadKey.PER_CLIENT}.{PayloadKey.THRESHOLD_VALUE}",
                tolerance=tolerance,
                detail=f"{len(diffs)} threshold mismatches; first: {cid} expected={exp}, actual={act}, diff={diff}",
            ),
        )
    return ValidationCheck(
        code=MetricCheckCode.PER_CLIENT_THRESHOLDS_WITHIN_TOLERANCE,
        status=AuditStatus.PASS,
        detail=_format_check_detail(
            field=f"{PayloadKey.PER_CLIENT}.{PayloadKey.THRESHOLD_VALUE}",
            tolerance=tolerance,
        ),
    )


def _overall_status(checks: list[ValidationCheck]) -> AuditStatus:
    statuses = {c.status for c in checks}
    if AuditStatus.FAIL in statuses:
        return AuditStatus.FAIL
    if AuditStatus.MISSING in statuses:
        return AuditStatus.PARTIAL
    return AuditStatus.PASS


def _read_metrics_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_per_client(stored: dict[str, Any]) -> list[dict[str, Any]]:
    per_client = stored[PayloadKey.PER_CLIENT]
    if isinstance(per_client, dict):
        return [
            dict(values, client_id=client_id)
            for client_id, values in per_client.items()
        ]
    return list(per_client)


def _evaluate(
    threshold_result: ThresholdResult,
    score_provider: ScoreProvider,
    stage: ExperimentStage,
    seed: int,
) -> tuple[EvaluationResult, dict[str, float]]:
    evaluation = evaluate_policy_run(
        threshold_result.client_thresholds,
        Path(""),
        stage,
        seed,
        score_provider=score_provider,
    )
    client_thresholds = {
        ct.client_id: float(ct.threshold) for ct in threshold_result.client_thresholds
    }
    return evaluation, client_thresholds


def _compute_global_tau_global(
    cal_errors: dict[str, np.ndarray],
    cfg: DatpConfig,
    *,
    seed: int = 0,
) -> float:
    global_result = derive_threshold(
        _DeriveInput(
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            client_errors=cal_errors,
            n_min=cfg.threshold.n_min,
            q=cfg.threshold.q,
            tau_global=0.0,
            threshold_cfg=cfg.threshold,
            seed=seed,
        )
    )
    return float(global_result.tau_global)


def _stored_per_client_map(stored: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row[PayloadKey.CLIENT_ID]: row for row in _normalize_per_client(stored)}


def _stored_scalar(stored: dict[str, Any], field: str) -> Any:
    """Read a scalar metric from top-level keys, falling back to ``aggregate_metrics``.

    Some legacy fields (e.g. ``max_min_fpr_gap``) live only inside ``aggregate_metrics``.
    """
    if stored.get(field) is not None:
        return stored[field]
    aggregate = stored.get("aggregate_metrics") or {}
    return aggregate.get(field)


def _scalar_checks_for_policy_run(
    stored: dict[str, Any],
    evaluation: EvaluationResult,
    threshold_result: ThresholdResult,
) -> list[ValidationCheck]:
    actual_scalars = {
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
        _scalar_check(
            field=field,
            expected=_stored_scalar(stored, field),
            actual=actual_scalars[field],
            tolerance=SCALAR_METRIC_TOLERANCE,
        )
        for field in _SCALAR_METRIC_FIELDS
    ]
    checks.append(
        _scalar_check(
            field=PayloadKey.COVERAGE_RATIO,
            expected=_stored_scalar(stored, PayloadKey.COVERAGE_RATIO),
            actual=evaluation.coverage_ratio,
            tolerance=COVERAGE_RATIO_TOLERANCE,
            code=MetricCheckCode.COVERAGE_RATIO_WITHIN_TOLERANCE,
        )
    )
    return checks


def _count_and_id_checks(
    stored: dict[str, Any],
    evaluation: EvaluationResult,
) -> list[ValidationCheck]:
    return [
        _exact_match_check(
            MetricCheckCode.ELIGIBLE_COUNT_EXACT,
            PayloadKey.ELIGIBLE_COUNT,
            int(stored[PayloadKey.ELIGIBLE_COUNT]),
            int(evaluation.eligible_count),
        ),
        _exact_match_check(
            MetricCheckCode.PENDING_COUNT_EXACT,
            PayloadKey.PENDING_COUNT,
            int(stored[PayloadKey.PENDING_COUNT]),
            int(len(evaluation.pending_ids)),
        ),
        _exact_match_check(
            MetricCheckCode.CLIENT_COUNT_EXACT,
            PayloadKey.CLIENT_COUNT,
            int(stored[PayloadKey.CLIENT_COUNT]),
            int(evaluation.client_count),
        ),
        _id_set_check(
            MetricCheckCode.ELIGIBLE_IDS_EXACT,
            PayloadKey.ELIGIBLE_IDS,
            list(map(str, stored[PayloadKey.ELIGIBLE_IDS])),
            list(map(str, evaluation.eligible_ids)),
        ),
        _id_set_check(
            MetricCheckCode.PENDING_IDS_EXACT,
            PayloadKey.PENDING_IDS,
            list(map(str, stored[PayloadKey.PENDING_IDS])),
            list(map(str, evaluation.pending_ids)),
        ),
    ]


def _per_client_checks(
    stored_per_client: dict[str, dict[str, Any]],
    evaluation: EvaluationResult,
    client_thresholds_actual: dict[str, float],
) -> list[ValidationCheck]:
    actual_per_client = {cr.client_id: cr for cr in evaluation.clients}
    expected_confusion = {
        cid: {k: int(row[PayloadKey.CONFUSION_MATRIX][k]) for k in _CONFUSION_KEYS}
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
        _confusion_check(expected_confusion, actual_confusion),
        _thresholds_check(
            expected_thresholds, client_thresholds_actual, SCALAR_METRIC_TOLERANCE
        ),
    ]


def _build_policy_checks(
    *,
    stored: dict[str, Any],
    evaluation: EvaluationResult,
    threshold_result: ThresholdResult,
    client_thresholds_actual: dict[str, float],
) -> list[ValidationCheck]:
    checks = _scalar_checks_for_policy_run(stored, evaluation, threshold_result)
    checks.extend(_count_and_id_checks(stored, evaluation))
    checks.extend(
        _per_client_checks(
            _stored_per_client_map(stored), evaluation, client_thresholds_actual
        )
    )
    return checks


def _serialize_recomputed(
    evaluation: EvaluationResult,
    threshold_result: ThresholdResult,
    client_thresholds: dict[str, float],
) -> dict[str, Any]:
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


def _select_stored_summary(stored: dict[str, Any]) -> dict[str, Any]:
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


def _reproduce_one_policy(
    policy: ThresholdPolicy,
    cell: TrainingCellId,
    layout: ArtifactLayout,
    cal_errors: dict[str, np.ndarray],
    score_provider: ScoreProvider,
    cfg: DatpConfig,
    tau_global_ref: float,
) -> PolicyReproductionResult | None:
    """Reproduce a single policy run for a cell; returns None when metrics artifact is absent."""
    run = PolicyRunId(cell=cell, policy=policy)
    metrics_path = layout.policy_run(run).result_dir / ArtifactFile.METRICS
    if not metrics_path.exists():
        return None
    stored = _read_metrics_json(metrics_path)
    threshold_result = derive_threshold(
        _DeriveInput(
            policy=policy,
            client_errors=cal_errors,
            n_min=cfg.threshold.n_min,
            q=cfg.threshold.q,
            tau_global=tau_global_ref,
            threshold_cfg=cfg.threshold,
            seed=cell.seed,
        )
    )
    evaluation, client_thresholds = _evaluate(
        threshold_result,
        score_provider,
        cell.stage,
        cell.seed,
    )
    checks = _build_policy_checks(
        stored=stored,
        evaluation=evaluation,
        threshold_result=threshold_result,
        client_thresholds_actual=client_thresholds,
    )
    return PolicyReproductionResult(
        policy=policy,
        status=_overall_status(checks),
        metrics_path=str(metrics_path),
        recomputed=_serialize_recomputed(
            evaluation, threshold_result, client_thresholds
        ),
        stored=_select_stored_summary(stored),
        checks=checks,
    )


def reproduce_cell_metrics(
    cell_dir: Path,
    base_dir: Path,
    *,
    config: DatpConfig | None = None,
) -> CellReproductionResult:
    """Reproduce metrics for every policy result that exists for the given score cell.

    ``cell_dir`` is the score cell directory ``<base_dir>/scores/<stage>/seed_N/``.
    ``base_dir`` is the experiment root (containing ``scores/`` and ``results/``).
    ``config`` overrides the composed runtime config (used in tests). When None, the canonical
    config is composed via Hydra using the cell's stage/seed.

    Raises FileNotFoundError when no policy metrics.json exist for the cell.
    """
    cell_dir = cell_dir.resolve()
    base_dir = base_dir.resolve()
    scores_root = base_dir / ArtifactDir.SCORES
    location = parse_score_cell_dir(scores_root, cell_dir)
    stage = location.cell.stage
    seed = location.cell.seed

    layout = ArtifactLayout(base_dir=base_dir, stage=stage)
    cell = TrainingCellId(stage=stage, seed=seed)
    score_root = layout.score_cell(cell).score_dir
    cal_errors = load_parquets_from_dir(score_root / ScoringStage.CAL)
    score_provider = ScoreProvider(score_root)

    cfg = config or compose_config(
        stage=stage,
        policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        seed=seed,
    )
    tau_global_ref = _compute_global_tau_global(cal_errors, cfg, seed=seed)

    policy_results: list[PolicyReproductionResult] = []
    missing_policies: list[ThresholdPolicy] = []
    for policy in CONTROLLED_POLICIES:
        result = _reproduce_one_policy(
            policy, cell, layout, cal_errors, score_provider, cfg, tau_global_ref
        )
        if result is None:
            missing_policies.append(policy)
        else:
            policy_results.append(result)

    overall = _aggregate_overall([pr.status for pr in policy_results], missing_policies)
    return CellReproductionResult(
        cell=TrainingCellId(stage=stage, seed=seed),
        overall_status=overall,
        policies=policy_results,
        missing_policies=missing_policies,
    )


def _aggregate_overall(
    statuses: list[AuditStatus],
    missing_policies: list[ThresholdPolicy],
) -> AuditStatus:
    if AuditStatus.FAIL in statuses:
        return AuditStatus.FAIL
    any_incomplete = (
        bool(missing_policies)
        or AuditStatus.MISSING in statuses
        or AuditStatus.PARTIAL in statuses
    )
    if any_incomplete:
        return AuditStatus.PARTIAL
    if not statuses:
        return AuditStatus.MISSING
    return AuditStatus.PASS


def reproduce_all_cells(
    base_dir: Path,
    *,
    config: DatpConfig | None = None,
    write_reports: bool = False,
) -> list[CellReproductionResult]:
    """Reproduce metrics for every discoverable score cell under ``base_dir/scores/``."""
    base_dir = base_dir.resolve()
    results: list[CellReproductionResult] = []
    for location in iter_score_cells(base_dir):
        result = reproduce_cell_metrics(location.cell_dir, base_dir, config=config)
        results.append(result)
        if write_reports:
            write_json_atomic(
                location.cell_dir / RECOMPUTED_METRICS_JSON,
                result.model_dump(mode="json"),
            )
    if write_reports:
        write_json_atomic(
            base_dir / ArtifactDir.SCORES / RECOMPUTED_METRICS_INDEX_JSON,
            {"cells": [r.model_dump(mode="json") for r in results]},
        )
    return results
