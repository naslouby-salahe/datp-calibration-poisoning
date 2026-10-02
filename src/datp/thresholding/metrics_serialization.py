from datp.types import (
    ClassificationScore,
    ClientCount,
    ClientId,
    ContentHash,
    FalseNegativeRate,
    FalsePositiveRate,
    NarrativeText,
    RandomSeed,
    Ratio,
    RoundIndex,
    RunId,
    SampleCount,
    SchemaVersion,
    ScoreValue,
    Threshold,
    TrueNegativeRate,
    TruePositiveRate,
)

from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, model_validator

from datp.config.models import ExperimentStage
from datp.core.enums import (
    ClientStatus,
    POLICY_THRESHOLD_SOURCE,
    THRESHOLD_AGGREGATION_BY_POLICY,
    MetricName,
    ProvenanceSentinel,
    RunKind,
    ThresholdAggregationMethod,
    ThresholdPolicy,
    ThresholdSource,
)
from datp.core.provenance import git_commit, source_hash, utc_timestamp
from datp.core.types import MetricsProvenance, ThresholdResult
from datp.data.catalog import DatasetID
from datp.evaluation.metrics import ClientEvaluationRecord, EvaluationResult

METRICS_SCHEMA_VERSION: SchemaVersion = "2"
METRIC_SCHEMA_VERSION: SchemaVersion = "2"
THRESHOLD_SCHEMA_VERSION: SchemaVersion = "1"


@dataclass(frozen=True, slots=True)
class MetricsBuildRequest:

    eval_result: EvaluationResult
    threshold_result: ThresholdResult
    config_identity: ContentHash
    split_manifest_identity: ContentHash
    model_checkpoint_identity: ContentHash
    score_artifact_identity: ContentHash
    checkpoint_round: RoundIndex | None


class ConfusionMatrix(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")
    tp: SampleCount
    fp: SampleCount
    tn: SampleCount
    fn: SampleCount


class MetricsClientDetail(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")
    client_id: ClientId
    fpr: FalsePositiveRate
    tpr: TruePositiveRate
    tnr: TrueNegativeRate
    fnr: FalseNegativeRate
    precision: ClassificationScore
    recall: ClassificationScore
    balanced_accuracy: ClassificationScore
    macro_f1: ClassificationScore
    confusion_matrix: ConfusionMatrix
    n_benign: SampleCount
    n_attack: SampleCount
    calibration_pending: bool
    evaluation_incomplete: bool
    threshold_value: Threshold
    threshold_source: ThresholdSource


class SweepMetrics(BaseModel):

    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: SchemaVersion
    metric_schema_version: SchemaVersion
    threshold_schema_version: SchemaVersion
    run_id: RunId
    run_kind: RunKind
    policy: ThresholdPolicy
    stage: ExperimentStage
    seed: RandomSeed
    checkpoint_round: RoundIndex | None
    dataset: DatasetID
    threshold_scope: ThresholdAggregationMethod
    threshold_strategy_name: NarrativeText
    tau_global: Threshold
    eligible_ids: tuple[ClientId, ...]
    pending_ids: tuple[ClientId, ...]
    eval_incomplete_ids: tuple[ClientId, ...]
    eligible_count: ClientCount
    pending_count: ClientCount
    eval_incomplete_count: ClientCount
    client_count: ClientCount
    coverage_ratio: Ratio
    cv_fpr: FalsePositiveRate
    mean_fpr: FalsePositiveRate | None = None
    std_fpr: FalsePositiveRate | None = None
    cv_tpr: TruePositiveRate
    iqr_fpr: FalsePositiveRate
    iqr_tpr: TruePositiveRate
    worst_client_fpr: FalsePositiveRate
    worst_client_id: ClientId | None
    worst_ba: ScoreValue
    p10_macro_f1: ClassificationScore
    aggregate_metrics: dict[MetricName, ScoreValue | ClientId | None]
    provenance: MetricsProvenance
    per_client: tuple[MetricsClientDetail, ...]

    @model_validator(mode="after")
    def validate_partition(self) -> "SweepMetrics":
        client_ids = tuple(client.client_id for client in self.per_client)
        client_id_set = set(client_ids)
        eligible = set(self.eligible_ids)
        pending = set(self.pending_ids)
        incomplete = set(self.eval_incomplete_ids)
        _validate_client_membership(
            self, client_ids, client_id_set, eligible, pending, incomplete
        )
        _validate_client_states(self, pending, incomplete)
        _validate_provenance(self.provenance)
        return self


def _validate_client_membership(
    metrics: SweepMetrics,
    client_ids: tuple[ClientId, ...],
    client_id_set: set[ClientId],
    eligible: set[ClientId],
    pending: set[ClientId],
    incomplete: set[ClientId],
) -> None:
    if len(client_id_set) != len(client_ids):
        raise ValueError("per_client contains duplicate client IDs")
    if overlap := eligible & pending:
        raise ValueError(f"eligible_ids overlap pending_ids: {sorted(overlap)}")
    if missing := (eligible | pending | incomplete) - client_id_set:
        raise ValueError(f"eligibility IDs missing per_client rows: {sorted(missing)}")
    if metrics.eligible_count != len(eligible):
        raise ValueError("eligible_count does not match eligible_ids")
    if metrics.pending_count != len(pending):
        raise ValueError("pending_count does not match pending_ids")
    if metrics.eval_incomplete_count != len(incomplete):
        raise ValueError("eval_incomplete_count does not match eval_incomplete_ids")
    if metrics.client_count != len(client_id_set):
        raise ValueError("client_count does not match per_client rows")
    if not 0.0 <= metrics.coverage_ratio <= 1.0:
        raise ValueError("coverage_ratio must be within [0, 1]")


def _validate_client_states(
    metrics: SweepMetrics,
    pending: set[ClientId],
    incomplete: set[ClientId],
) -> None:
    for client in metrics.per_client:
        if client.client_id in pending and not client.calibration_pending:
            raise ValueError(
                f"pending client {client.client_id} missing calibration_pending=true"
            )
        if client.client_id in incomplete and not client.evaluation_incomplete:
            raise ValueError(
                f"eval-incomplete client {client.client_id} missing evaluation_incomplete=true"
            )


def _validate_provenance(provenance: MetricsProvenance) -> None:
    values = (
        provenance.config_identity,
        provenance.split_manifest_identity,
        provenance.model_checkpoint_identity,
        provenance.score_artifact_identity,
        provenance.metric_code_version,
        provenance.threshold_code_version,
        provenance.package_version,
        provenance.generated_at_utc,
    )
    if any(
        value in {
            ProvenanceSentinel.UNKNOWN,
            ProvenanceSentinel.UNKNOWN_LOWERCASE,
        }
        for value in values
    ):
        raise ValueError("provenance contains a vague UNKNOWN value")
    identities = (
        provenance.config_identity,
        provenance.split_manifest_identity,
        provenance.model_checkpoint_identity,
        provenance.score_artifact_identity,
    )
    if any(value.startswith("MISSING_") for value in identities):
        raise ValueError("provenance contains an unresolved MISSING_* identity")


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
        confusion_matrix=ConfusionMatrix(
            tp=record.confusion.tp,
            fp=record.confusion.fp,
            tn=record.confusion.tn,
            fn=record.confusion.fn,
        ),
        n_benign=record.n_benign,
        n_attack=record.n_attack,
        calibration_pending=record.threshold.status is ClientStatus.CALIBRATION_PENDING,
        evaluation_incomplete=record.evaluation_incomplete,
        threshold_value=record.threshold.threshold,
        threshold_source=ThresholdSource.TAU_GLOBAL_FALLBACK
        if record.threshold.status is ClientStatus.CALIBRATION_PENDING
        else default_source,
    )


def build_metrics_dict(req: MetricsBuildRequest) -> SweepMetrics:
    er = req.eval_result
    tr = req.threshold_result

    aggregate_metrics = {
        MetricName.CV_FPR: er.dispersion.cv_fpr,
        MetricName.MEAN_FPR: er.dispersion.mean_fpr,
        MetricName.STD_FPR: er.dispersion.std_fpr,
        MetricName.CV_TPR: er.dispersion.cv_tpr,
        MetricName.IQR_FPR: er.dispersion.iqr_fpr,
        MetricName.IQR_TPR: er.dispersion.iqr_tpr,
        MetricName.MAX_MIN_FPR_GAP: er.dispersion.max_min_fpr_gap,
        MetricName.WORST_CLIENT_FPR: er.dispersion.worst_client_fpr,
        MetricName.WORST_CLIENT_ID: er.dispersion.worst_client_id,
        MetricName.WORST_BA: er.dispersion.worst_ba,
        MetricName.P10_MACRO_F1: er.dispersion.p10_macro_f1,
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
        run_id=RunId(f"{er.run.stage}_{er.run.policy}_seed{er.run.seed}"),
        run_kind=RunKind.CORE_LADDER,
        policy=er.run.policy,
        stage=er.run.stage,
        seed=er.run.seed,
        checkpoint_round=req.checkpoint_round,
        dataset=er.dataset,
        threshold_scope=THRESHOLD_AGGREGATION_BY_POLICY[er.run.policy],
        threshold_strategy_name=tr.run.policy,
        tau_global=tr.tau_global,
        eligible_ids=er.eligible_ids,
        pending_ids=er.pending_ids,
        eval_incomplete_ids=er.incomplete_ids,
        eligible_count=tr.eligible_count,
        pending_count=tr.pending_count,
        eval_incomplete_count=len(er.incomplete_ids),
        client_count=er.dispersion.client_count,
        coverage_ratio=er.coverage_ratio,
        cv_fpr=er.dispersion.cv_fpr,
        mean_fpr=er.dispersion.mean_fpr,
        std_fpr=er.dispersion.std_fpr,
        cv_tpr=er.dispersion.cv_tpr,
        iqr_fpr=er.dispersion.iqr_fpr,
        iqr_tpr=er.dispersion.iqr_tpr,
        worst_client_fpr=er.dispersion.worst_client_fpr,
        worst_client_id=er.dispersion.worst_client_id,
        worst_ba=er.dispersion.worst_ba,
        p10_macro_f1=er.dispersion.p10_macro_f1,
        aggregate_metrics=aggregate_metrics,
        provenance=provenance,
        per_client=tuple(
            _to_client_detail(c, POLICY_THRESHOLD_SOURCE[er.run.policy]) for c in er.clients
        ),
    )
