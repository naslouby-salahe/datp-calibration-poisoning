from __future__ import annotations

from datp.types import (
    ClassificationScore,
    ClientId,
    ColumnName,
    FalsePositiveRate,
    JsonRecord,
    JsonValue,
    NarrativeText,
    RandomSeed,
    RunId,
    SampleCount,
    ScoreValue,
    ScoreVector,
    SignedDelta,
    Threshold,
    Tolerance,
    TruePositiveRate,
)


import dataclasses
import json
import math
from pathlib import Path
from collections.abc import Mapping
from typing import cast

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
from datp.data.catalog import DatasetID
from datp.evaluation.metrics import EvaluationResult, evaluate_policy_run
from datp.scoring.loading import ScoreProvider, load_parquets_from_dir
from datp.thresholding.derivation import ThresholdDerivation, derive_threshold
from datp.validation.discovery import parse_score_cell_dir
from datp.validation.enums import (
    AuditStatus,
    DenominatorStatus,
    MetricCheckCode,
    ValidationThreshold,
)
from datp.validation.schemas import (
    CellReproductionResult,
    MetricRecomputationRecord,
    PolicyReproductionResult,
    RecomputedClientMetricsSnapshot,
    RecomputedMetricsSnapshot,
    StoredMetricsSnapshot,
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

CONFUSION_KEYS: tuple[ConfusionKey, ...] = tuple(ConfusionKey)
RECOMPUTATION_EPSILON = 1e-9
RECOMPUTE_METRICS = (
    MetricName.FPR,
    MetricName.TPR,
    MetricName.BALANCED_ACCURACY,
    MetricName.MACRO_F1,
)


@dataclasses.dataclass(frozen=True, slots=True)
class RecomputationParams:

    run_id: RunId
    seed: RandomSeed
    stage: ExperimentStage
    policy: ThresholdPolicy
    client_id: ClientId
    tp: SampleCount
    fp: SampleCount
    tn: SampleCount
    fn: SampleCount
    n_benign: SampleCount
    n_attack: SampleCount
    saved_fpr: FalsePositiveRate | None
    saved_tpr: TruePositiveRate | None
    saved_balanced_accuracy: ClassificationScore | None
    saved_macro_f1: ClassificationScore | None


@dataclasses.dataclass(frozen=True, slots=True)
class RecomputationResult:

    diff: SignedDelta | None
    saved_value: ScoreValue | None
    recomputed_value: ScoreValue | None
    status: DenominatorStatus


@dataclasses.dataclass(frozen=True, slots=True)
class _StoredClientMetric:

    client_id: ClientId
    confusion: dict[ConfusionKey, SampleCount] | None
    threshold: Threshold | None


@dataclasses.dataclass(frozen=True, slots=True)
class _StoredMetrics:

    policy: ThresholdPolicy | None
    stage: ExperimentStage | None
    seed: RandomSeed | None
    dataset: DatasetID | None
    direct_metrics: dict[MetricName | PayloadKey, ScoreValue | None]
    aggregate_metrics: dict[MetricName, ScoreValue | None]
    client_count: SampleCount | None
    eligible_count: SampleCount | None
    pending_count: SampleCount | None
    eligible_ids: tuple[ClientId, ...] | None
    pending_ids: tuple[ClientId, ...] | None
    per_client: dict[ClientId, _StoredClientMetric]
    worst_client_id: ClientId | None


def build_recomputation_record(
    params: RecomputationParams,
    metric: MetricName,
    *,
    saved_value: ScoreValue | None = None,
    recomputed_value: ScoreValue | None = None,
    abs_diff: SignedDelta | None = None,
    status: DenominatorStatus,
) -> MetricRecomputationRecord:
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


def compare_recomputation(saved: ScoreValue | None, recomp: ScoreValue) -> RecomputationResult:
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
    field: ColumnName = "",
    expected: JsonValue | list[NarrativeText] = None,
    actual: JsonValue | list[NarrativeText] = None,
    abs_diff: SignedDelta | None = None,
    tolerance: Tolerance | None = None,
    detail: NarrativeText = "",
) -> NarrativeText:
    parts: list[NarrativeText] = []
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
    field: ColumnName,
    expected: ScoreValue | None,
    actual: ScoreValue | None,
    tolerance: Tolerance,
    code: MetricCheckCode = MetricCheckCode.SCALAR_WITHIN_TOLERANCE,
) -> ValidationCheck:
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
    code: MetricCheckCode, field: ColumnName, expected: JsonValue, actual: JsonValue
) -> ValidationCheck:
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
    code: MetricCheckCode,
    field: ColumnName,
    expected: list[ClientId],
    actual: list[ClientId],
) -> ValidationCheck:
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
    expected_per_client: Mapping[ClientId, Mapping[ConfusionKey, SampleCount]],
    actual_per_client: Mapping[ClientId, Mapping[ConfusionKey, SampleCount]],
) -> ValidationCheck:
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
    expected_per_client: Mapping[ClientId, Threshold],
    actual_per_client: Mapping[ClientId, Threshold],
    tolerance: Tolerance,
) -> ValidationCheck:
    diffs = [
        (cid, exp, act, abs(exp - act))
        for cid in sorted(set(expected_per_client) & set(actual_per_client))
        for exp, act in [(expected_per_client[cid], actual_per_client[cid])]
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
    statuses = {c.status for c in checks}
    if AuditStatus.FAIL in statuses:
        return AuditStatus.FAIL
    if AuditStatus.MISSING in statuses:
        return AuditStatus.PARTIAL
    return AuditStatus.PASS


def read_metrics_json(path: Path) -> _StoredMetrics:
    payload = _validate_json_value(json.loads(path.read_text()))
    if not isinstance(payload, dict):
        raise TypeError("Metrics artifact must contain a JSON object")
    return _parse_stored_metrics(payload)


def _optional_score(value: JsonValue) -> ScoreValue | None:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return None


def _optional_count(value: JsonValue) -> SampleCount | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _client_ids(value: JsonValue) -> tuple[ClientId, ...] | None:
    if not isinstance(value, list):
        return None
    result: list[ClientId] = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError("Client IDs must be strings")
        result.append(ClientId(item))
    return tuple(result)


def _parse_stored_client(
    client_id: ClientId, row: JsonRecord
) -> _StoredClientMetric:
    raw_confusion = row.get(PayloadKey.CONFUSION_MATRIX)
    confusion: dict[ConfusionKey, SampleCount] | None = None
    if isinstance(raw_confusion, dict):
        confusion = {}
        for key in CONFUSION_KEYS:
            count = _optional_count(raw_confusion.get(key))
            if count is None:
                raise TypeError(f"Invalid confusion count for {client_id}/{key}")
            confusion[key] = count
    return _StoredClientMetric(
        client_id=client_id,
        confusion=confusion,
        threshold=_optional_score(row.get(PayloadKey.THRESHOLD_VALUE)),
    )


def _parse_stored_metrics(payload: JsonRecord) -> _StoredMetrics:
    direct_fields: tuple[MetricName | PayloadKey, ...] = (
        *SCALAR_METRIC_FIELDS,
        PayloadKey.COVERAGE_RATIO,
    )
    direct_metrics = {
        field: _optional_score(payload[field])
        for field in direct_fields
        if field in payload
    }
    raw_aggregate = payload.get(PayloadKey.AGGREGATE_METRICS)
    aggregate_metrics = (
        {
            field: _optional_score(raw_aggregate[field])
            for field in SCALAR_METRIC_FIELDS
            if field in raw_aggregate
        }
        if isinstance(raw_aggregate, dict)
        else {}
    )

    raw_per_client = payload.get(PayloadKey.PER_CLIENT)
    if isinstance(raw_per_client, dict):
        per_client: dict[ClientId, _StoredClientMetric] = {}
        for client_label, raw_row in raw_per_client.items():
            if not isinstance(raw_row, dict):
                raise TypeError("Per-client metric entries must be JSON objects")
            client_id = ClientId(client_label)
            per_client[client_id] = _parse_stored_client(client_id, raw_row)
    elif isinstance(raw_per_client, list):
        per_client = {}
        for raw_row in raw_per_client:
            if not isinstance(raw_row, dict):
                raise TypeError("Per-client metric entries must be JSON objects")
            raw_client_id = raw_row.get(PayloadKey.CLIENT_ID)
            if not isinstance(raw_client_id, str):
                raise TypeError("Per-client metric ID must be a string")
            client_id = ClientId(raw_client_id)
            per_client[client_id] = _parse_stored_client(client_id, raw_row)
    else:
        raise TypeError("Per-client metrics must be a list or keyed object")

    raw_policy = payload.get(PayloadKey.POLICY)
    raw_stage = payload.get(PayloadKey.STAGE)
    raw_seed = payload.get(PayloadKey.SEED)
    raw_dataset = payload.get(PayloadKey.DATASET)
    raw_worst_client = payload.get(MetricName.WORST_CLIENT_ID)
    return _StoredMetrics(
        policy=ThresholdPolicy(raw_policy) if isinstance(raw_policy, str) else None,
        stage=ExperimentStage(raw_stage) if isinstance(raw_stage, str) else None,
        seed=RandomSeed(raw_seed)
        if isinstance(raw_seed, int) and not isinstance(raw_seed, bool)
        else None,
        dataset=DatasetID(raw_dataset) if isinstance(raw_dataset, str) else None,
        direct_metrics=direct_metrics,
        aggregate_metrics=aggregate_metrics,
        client_count=_optional_count(payload.get(PayloadKey.CLIENT_COUNT)),
        eligible_count=_optional_count(payload.get(PayloadKey.ELIGIBLE_COUNT)),
        pending_count=_optional_count(payload.get(PayloadKey.PENDING_COUNT)),
        eligible_ids=_client_ids(payload.get(PayloadKey.ELIGIBLE_IDS)),
        pending_ids=_client_ids(payload.get(PayloadKey.PENDING_IDS)),
        per_client=per_client,
        worst_client_id=ClientId(raw_worst_client)
        if isinstance(raw_worst_client, str)
        else None,
    )


def _validate_json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list):
        sequence = cast(list[object], value)
        return [_validate_json_value(item) for item in sequence]
    if isinstance(value, dict):
        record = cast(dict[object, object], value)
        if not all(isinstance(key, str) for key in record):
            raise TypeError("JSON object keys must be strings")
        string_keyed = cast(dict[str, object], record)
        return {
            key: _validate_json_value(item) for key, item in string_keyed.items()
        }
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def evaluate_policy(
    threshold_result: ThresholdResult,
    score_provider: ScoreProvider,
    stage: ExperimentStage,
    seed: RandomSeed,
) -> tuple[EvaluationResult, dict[ClientId, ScoreValue]]:
    evaluation = evaluate_policy_run(
        threshold_result.client_thresholds,
        Path(""),
        stage,
        seed,
        score_provider=score_provider,
    )
    return evaluation, {
        ct.client_id: ct.threshold for ct in threshold_result.client_thresholds
    }


def compute_global_tau(
    cal_errors: dict[ClientId, ScoreVector],
    cfg: DatpConfig,
    *,
    seed: RandomSeed = RandomSeed(0),
) -> ScoreValue:
    return derive_threshold(
        ThresholdDerivation(
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            client_errors=cal_errors,
            n_min=cfg.threshold.n_min,
            q=cfg.threshold.q,
            tau_global=0.0,
            threshold_cfg=cfg.threshold,
            seed=seed,
        )
    ).tau_global


def stored_scalar(
    stored: _StoredMetrics, field: MetricName | PayloadKey
) -> ScoreValue | None:
    if field in stored.direct_metrics:
        return stored.direct_metrics[field]
    if isinstance(field, MetricName):
        return stored.aggregate_metrics.get(field)
    return None


def scalar_checks_for_policy_run(
    stored: _StoredMetrics,
    evaluation: EvaluationResult,
    threshold_result: ThresholdResult,
) -> list[ValidationCheck]:
    actuals = {
        MetricName.CV_FPR: evaluation.dispersion.cv_fpr,
        MetricName.CV_TPR: evaluation.dispersion.cv_tpr,
        MetricName.MEAN_FPR: evaluation.dispersion.mean_fpr,
        MetricName.STD_FPR: evaluation.dispersion.std_fpr,
        MetricName.IQR_FPR: evaluation.dispersion.iqr_fpr,
        MetricName.IQR_TPR: evaluation.dispersion.iqr_tpr,
        MetricName.MAX_MIN_FPR_GAP: evaluation.dispersion.max_min_fpr_gap,
        MetricName.WORST_CLIENT_FPR: evaluation.dispersion.worst_client_fpr,
        MetricName.WORST_BA: evaluation.dispersion.worst_ba,
        MetricName.P10_MACRO_F1: evaluation.dispersion.p10_macro_f1,
        MetricName.TAU_GLOBAL: threshold_result.tau_global,
    }

    checks = [
        scalar_check(
            f,
            stored_scalar(stored, f),
            actuals[f],
            ValidationThreshold.SCALAR_METRIC_TOLERANCE,
        )
        for f in SCALAR_METRIC_FIELDS
    ]
    checks.append(
        scalar_check(
            PayloadKey.COVERAGE_RATIO,
            stored_scalar(stored, PayloadKey.COVERAGE_RATIO),
            evaluation.coverage_ratio,
            ValidationThreshold.COVERAGE_RATIO_TOLERANCE,
            MetricCheckCode.COVERAGE_RATIO_WITHIN_TOLERANCE,
        )
    )
    return checks


def _required_count(value: SampleCount | None) -> SampleCount:
    if value is None:
        raise TypeError(f"Expected a count, received {value!r}")
    return value


def count_and_id_checks(
    stored: _StoredMetrics, evaluation: EvaluationResult
) -> list[ValidationCheck]:
    if stored.eligible_ids is None:
        raise TypeError("Expected a list of client IDs")
    if stored.pending_ids is None:
        raise TypeError("Expected a list of client IDs")
    return [
        exact_match_check(
            MetricCheckCode.ELIGIBLE_COUNT_EXACT,
            PayloadKey.ELIGIBLE_COUNT,
            _required_count(stored.eligible_count),
            evaluation.dispersion.eligible_count,
        ),
        exact_match_check(
            MetricCheckCode.PENDING_COUNT_EXACT,
            PayloadKey.PENDING_COUNT,
            _required_count(stored.pending_count),
            len(evaluation.pending_ids),
        ),
        exact_match_check(
            MetricCheckCode.CLIENT_COUNT_EXACT,
            PayloadKey.CLIENT_COUNT,
            _required_count(stored.client_count),
            evaluation.dispersion.client_count,
        ),
        id_set_check(
            MetricCheckCode.ELIGIBLE_IDS_EXACT,
            PayloadKey.ELIGIBLE_IDS,
            list(stored.eligible_ids),
            list(evaluation.eligible_ids),
        ),
        id_set_check(
            MetricCheckCode.PENDING_IDS_EXACT,
            PayloadKey.PENDING_IDS,
            list(stored.pending_ids),
            list(evaluation.pending_ids),
        ),
    ]


def per_client_checks(
    stored_per_client: dict[ClientId, _StoredClientMetric],
    evaluation: EvaluationResult,
    client_thresholds_actual: Mapping[ClientId, Threshold],
) -> list[ValidationCheck]:
    actual_per_client = {cr.client_id: cr for cr in evaluation.clients}

    expected_confusion: dict[ClientId, dict[ConfusionKey, SampleCount]] = {}
    for client_id, row in stored_per_client.items():
        if row.confusion is not None:
            expected_confusion[client_id] = row.confusion

    actual_confusion = {
        cid: {
            ConfusionKey.TP: cr.confusion.tp,
            ConfusionKey.FP: cr.confusion.fp,
            ConfusionKey.TN: cr.confusion.tn,
            ConfusionKey.FN: cr.confusion.fn,
        }
        for cid, cr in actual_per_client.items()
    }

    expected_thresholds: dict[ClientId, Threshold] = {}
    for client_id, row in stored_per_client.items():
        if row.threshold is not None:
            expected_thresholds[client_id] = row.threshold

    return [
        confusion_check(expected_confusion, actual_confusion),
        thresholds_check(
            expected_thresholds,
            client_thresholds_actual,
            ValidationThreshold.SCALAR_METRIC_TOLERANCE,
        ),
    ]


def build_policy_checks(
    *,
    stored: _StoredMetrics,
    evaluation: EvaluationResult,
    threshold_result: ThresholdResult,
    client_thresholds_actual: Mapping[ClientId, Threshold],
) -> list[ValidationCheck]:
    return (
        scalar_checks_for_policy_run(stored, evaluation, threshold_result)
        + count_and_id_checks(stored, evaluation)
        + per_client_checks(
            stored.per_client, evaluation, client_thresholds_actual
        )
    )


def serialize_recomputed(
    evaluation: EvaluationResult,
    threshold_result: ThresholdResult,
    client_thresholds: Mapping[ClientId, Threshold],
) -> RecomputedMetricsSnapshot:
    return RecomputedMetricsSnapshot(
        policy=evaluation.run.policy,
        stage=evaluation.run.stage,
        seed=evaluation.run.seed,
        dataset=evaluation.dataset,
        tau_global=threshold_result.tau_global,
        coverage_ratio=evaluation.coverage_ratio,
        cv_fpr=evaluation.dispersion.cv_fpr,
        cv_tpr=evaluation.dispersion.cv_tpr,
        mean_fpr=evaluation.dispersion.mean_fpr,
        std_fpr=evaluation.dispersion.std_fpr,
        iqr_fpr=evaluation.dispersion.iqr_fpr,
        iqr_tpr=evaluation.dispersion.iqr_tpr,
        max_min_fpr_gap=evaluation.dispersion.max_min_fpr_gap,
        worst_client_fpr=evaluation.dispersion.worst_client_fpr,
        worst_client_id=evaluation.dispersion.worst_client_id,
        worst_ba=evaluation.dispersion.worst_ba,
        p10_macro_f1=evaluation.dispersion.p10_macro_f1,
        client_count=evaluation.dispersion.client_count,
        eligible_count=evaluation.dispersion.eligible_count,
        pending_count=len(evaluation.pending_ids),
        eligible_ids=tuple(sorted(evaluation.eligible_ids)),
        pending_ids=tuple(sorted(evaluation.pending_ids)),
        per_client={
            record.client_id: RecomputedClientMetricsSnapshot(
                fpr=record.metrics.fpr,
                tpr=record.metrics.tpr,
                balanced_accuracy=record.metrics.balanced_accuracy,
                macro_f1=record.metrics.macro_f1,
                n_benign=record.n_benign,
                n_attack=record.n_attack,
                confusion_matrix={
                    ConfusionKey.TP: record.confusion.tp,
                    ConfusionKey.FP: record.confusion.fp,
                    ConfusionKey.TN: record.confusion.tn,
                    ConfusionKey.FN: record.confusion.fn,
                },
                threshold_value=client_thresholds[record.client_id],
            )
            for record in evaluation.clients
        },
    )


def select_stored_summary(stored: _StoredMetrics) -> StoredMetricsSnapshot:
    return StoredMetricsSnapshot(
        policy=stored.policy,
        stage=stored.stage,
        seed=stored.seed,
        dataset=stored.dataset,
        tau_global=stored_scalar(stored, MetricName.TAU_GLOBAL),
        coverage_ratio=stored_scalar(stored, PayloadKey.COVERAGE_RATIO),
        cv_fpr=stored_scalar(stored, MetricName.CV_FPR),
        cv_tpr=stored_scalar(stored, MetricName.CV_TPR),
        mean_fpr=stored_scalar(stored, MetricName.MEAN_FPR),
        std_fpr=stored_scalar(stored, MetricName.STD_FPR),
        iqr_fpr=stored_scalar(stored, MetricName.IQR_FPR),
        iqr_tpr=stored_scalar(stored, MetricName.IQR_TPR),
        max_min_fpr_gap=stored_scalar(stored, MetricName.MAX_MIN_FPR_GAP),
        worst_client_fpr=stored_scalar(stored, MetricName.WORST_CLIENT_FPR),
        worst_client_id=stored.worst_client_id,
        worst_ba=stored_scalar(stored, MetricName.WORST_BA),
        p10_macro_f1=stored_scalar(stored, MetricName.P10_MACRO_F1),
        client_count=stored.client_count,
        eligible_count=stored.eligible_count,
        pending_count=stored.pending_count,
        eligible_ids=stored.eligible_ids,
        pending_ids=stored.pending_ids,
    )


@dataclasses.dataclass(frozen=True, slots=True)
class CellReproductionContext:

    cell: TrainingCellId
    layout: ArtifactLayout
    cal_errors: dict[ClientId, ScoreVector]
    score_provider: ScoreProvider
    cfg: DatpConfig
    tau_global_ref: Threshold


def reproduce_one_policy(
    policy: ThresholdPolicy,
    ctx: CellReproductionContext,
) -> PolicyReproductionResult | None:
    metrics_path = (
        ctx.layout.policy_run(PolicyRunId(cell=ctx.cell, policy=policy)).result_dir
        / ArtifactFile.METRICS
    )
    if not metrics_path.exists():
        return None

    stored = read_metrics_json(metrics_path)
    threshold_result = derive_threshold(
        ThresholdDerivation(
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

    policy_results: list[PolicyReproductionResult] = []
    missing_policies: list[ThresholdPolicy] = []
    for policy in CONTROLLED_POLICIES:
        result = reproduce_one_policy(policy, ctx)
        if result is None:
            missing_policies.append(policy)
        else:
            policy_results.append(result)

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
    if AuditStatus.FAIL in statuses:
        return AuditStatus.FAIL
    if (
        missing_policies
        or AuditStatus.MISSING in statuses
        or AuditStatus.PARTIAL in statuses
    ):
        return AuditStatus.PARTIAL
    return AuditStatus.PASS if statuses else AuditStatus.MISSING
