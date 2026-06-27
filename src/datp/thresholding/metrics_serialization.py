"""SweepMetrics model and serialization from EvaluationResult + ThresholdResult."""

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from datp.config.models import ExperimentStage
from datp.core.enums import (
    POLICY_THRESHOLD_SOURCE,
    THRESHOLD_AGGREGATION_BY_POLICY,
    ConfusionKey,
    MetricName,
    RunKind,
    ThresholdAggregationMethod,
    ThresholdPolicy,
    ThresholdSource,
)
from datp.core.provenance import git_commit, source_hash, utc_timestamp
from datp.core.types import MetricsProvenance, ThresholdResult
from datp.data.catalog import DatasetID
from datp.evaluation.metrics import ClientEvaluationRecord, EvaluationResult

METRICS_SCHEMA_VERSION = "2"
METRIC_SCHEMA_VERSION = "2"
THRESHOLD_SCHEMA_VERSION = "1"


@dataclass(frozen=True, slots=True)
class MetricsBuildRequest:
    """Request bundling evaluation, threshold, and provenance inputs for building a SweepMetrics instance."""

    eval_result: EvaluationResult
    threshold_result: ThresholdResult
    config_identity: str
    split_manifest_identity: str
    model_checkpoint_identity: str
    score_artifact_identity: str
    checkpoint_round: int | None


class MetricsClientDetail(BaseModel):
    """Per-client metrics: FPR/TPR, confusion matrix, and threshold source."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    client_id: str
    fpr: float
    tpr: float
    tnr: float
    fnr: float
    precision: float
    recall: float
    balanced_accuracy: float
    macro_f1: float
    confusion_matrix: dict[str, int]
    n_benign: int
    n_attack: int
    calibration_pending: bool
    evaluation_incomplete: bool
    threshold_value: float
    threshold_source: ThresholdSource


class SweepMetrics(BaseModel):
    """Top-level sweep result aggregating fleet metrics, per-client details, and provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: str
    metric_schema_version: str
    threshold_schema_version: str
    run_id: str
    run_kind: RunKind
    policy: ThresholdPolicy
    stage: ExperimentStage
    seed: int
    checkpoint_round: int | None
    dataset: DatasetID
    threshold_scope: ThresholdAggregationMethod
    threshold_strategy_name: str
    tau_global: float
    eligible_ids: tuple[str, ...]
    pending_ids: tuple[str, ...]
    eval_incomplete_ids: tuple[str, ...]
    eligible_count: int
    pending_count: int
    eval_incomplete_count: int
    client_count: int
    coverage_ratio: float
    cv_fpr: float
    mean_fpr: float
    std_fpr: float
    cv_tpr: float
    iqr_fpr: float
    iqr_tpr: float
    worst_client_fpr: float
    worst_client_id: str | None
    worst_ba: float
    p10_macro_f1: float
    aggregate_metrics: dict[MetricName, float | str | None]
    provenance: MetricsProvenance
    per_client: tuple[MetricsClientDetail, ...]


def _to_client_detail(
    record: ClientEvaluationRecord, default_source: ThresholdSource
) -> MetricsClientDetail:
    return MetricsClientDetail(
        client_id=record.client_id,
        fpr=record.metrics.fpr,
        tpr=record.metrics.tpr,
        tnr=record.metrics.tnr,
        fnr=record.metrics.fnr,
        precision=record.metrics.precision,
        recall=record.metrics.recall,
        balanced_accuracy=record.metrics.balanced_accuracy,
        macro_f1=record.metrics.macro_f1,
        confusion_matrix={
            ConfusionKey.TP.value: record.confusion.tp,
            ConfusionKey.FP.value: record.confusion.fp,
            ConfusionKey.TN.value: record.confusion.tn,
            ConfusionKey.FN.value: record.confusion.fn,
        },
        n_benign=record.n_benign,
        n_attack=record.n_attack,
        calibration_pending=record.threshold.calibration_pending,
        evaluation_incomplete=record.evaluation_incomplete,
        threshold_value=record.threshold.threshold,
        threshold_source=ThresholdSource.TAU_GLOBAL_FALLBACK
        if record.threshold.calibration_pending
        else default_source,
    )


def build_metrics_dict(req: MetricsBuildRequest) -> SweepMetrics:
    """Build a complete SweepMetrics from evaluation, threshold, and provenance inputs."""
    er = req.eval_result
    tr = req.threshold_result

    aggregate_metrics = {
        MetricName.CV_FPR: er.cv_fpr,
        MetricName.MEAN_FPR: er.mean_fpr,
        MetricName.STD_FPR: er.std_fpr,
        MetricName.CV_TPR: er.cv_tpr,
        MetricName.IQR_FPR: er.iqr_fpr,
        MetricName.IQR_TPR: er.iqr_tpr,
        MetricName.MAX_MIN_FPR_GAP: er.max_min_fpr_gap,
        MetricName.WORST_CLIENT_FPR: er.worst_client_fpr,
        MetricName.WORST_CLIENT_ID: er.worst_client_id,
        MetricName.WORST_BA: er.worst_ba,
        MetricName.P10_MACRO_F1: er.p10_macro_f1,
    }

    provenance = MetricsProvenance(
        config_identity=req.config_identity,
        split_manifest_identity=req.split_manifest_identity,
        model_checkpoint_identity=req.model_checkpoint_identity,
        score_artifact_identity=req.score_artifact_identity,
        metric_code_version=source_hash([Path(__file__)]),
        threshold_code_version=git_commit(),
        package_version=git_commit(),
        generated_at_utc=utc_timestamp(),
    )

    return SweepMetrics(
        schema_version=METRICS_SCHEMA_VERSION,
        metric_schema_version=METRIC_SCHEMA_VERSION,
        threshold_schema_version=THRESHOLD_SCHEMA_VERSION,
        run_id=f"{er.stage.value}_{er.policy.value}_seed{er.seed}",
        run_kind=RunKind.CORE_LADDER,
        policy=er.policy,
        stage=er.stage,
        seed=er.seed,
        checkpoint_round=req.checkpoint_round,
        dataset=er.dataset,
        threshold_scope=THRESHOLD_AGGREGATION_BY_POLICY[er.policy],
        threshold_strategy_name=tr.run.policy.value,
        tau_global=tr.tau_global,
        eligible_ids=er.eligible_ids,
        pending_ids=er.pending_ids,
        eval_incomplete_ids=er.incomplete_ids,
        eligible_count=tr.eligible_count,
        pending_count=tr.pending_count,
        eval_incomplete_count=len(er.incomplete_ids),
        client_count=er.client_count,
        coverage_ratio=er.coverage_ratio,
        cv_fpr=er.cv_fpr,
        mean_fpr=er.mean_fpr,
        std_fpr=er.std_fpr,
        cv_tpr=er.cv_tpr,
        iqr_fpr=er.iqr_fpr,
        iqr_tpr=er.iqr_tpr,
        worst_client_fpr=er.worst_client_fpr,
        worst_client_id=er.worst_client_id,
        worst_ba=er.worst_ba,
        p10_macro_f1=er.p10_macro_f1,
        aggregate_metrics=aggregate_metrics,
        provenance=provenance,
        per_client=tuple(
            _to_client_detail(c, POLICY_THRESHOLD_SOURCE[er.policy]) for c in er.clients
        ),
    )
