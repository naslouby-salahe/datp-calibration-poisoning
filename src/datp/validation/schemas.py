from __future__ import annotations

from datp.types import (
    ArtifactName,
    ClassificationScore,
    ClientId,
    CoverageLabel,
    ClusterCount,
    ClusterId,
    ContentHash,
    FalsePositiveRate,
    FeatureCount,
    NarrativeText,
    RandomSeed,
    Ratio,
    RecordKey,
    RoundIndex,
    RunId,
    SampleCount,
    SchemaVersion,
    ScoreValue,
    SignedCount,
    SignedDelta,
    Threshold,
    TruePositiveRate,
)


from pydantic import BaseModel, ConfigDict, Field

from datp.checkpointing.enums import ConvergenceStatus
from datp.config.models import ExperimentStage
from datp.core.enums import (
    ConfusionKey,
    MetricName,
    NBaIoTAttackFamily,
    NBaIoTDevice,
    NBaIoTDeviceFamily,
    NormalizationScope,
    ScoringStage,
    ThresholdAggregationMethod,
    ThresholdPolicy,
    ThresholdSource,
)
from datp.core.identity import TrainingCellId
from datp.data.catalog import DatasetID
from datp.validation.enums import (
    AuditSeverity,
    AuditStatus,
    CellVerdictReason,
    DenominatorStatus,
    ReuseVerdict,
    WarningCode,
    WorstDirection,
)


class AuditModel(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True)


class ValidationCheck(AuditModel):

    code: NarrativeText
    status: AuditStatus
    detail: NarrativeText = ""


class RunManifestRecord(AuditModel):

    run_id: RunId
    timestamp: NarrativeText
    git_commit_hash: ContentHash
    seed: RandomSeed
    dataset: DatasetID
    stage: ExperimentStage
    policy: ThresholdPolicy
    client_count: SampleCount
    split_hash: ContentHash
    model_hash: ContentHash
    encoder_hash: ContentHash
    training_config_hash: ContentHash
    preprocessing_config_hash: ContentHash
    scoring_code_hash: ContentHash
    threshold_code_hash: ContentHash
    metrics_code_hash: ContentHash
    artifact_schema_version: SchemaVersion
    convergence_round: RoundIndex | None
    convergence_criterion_value: ScoreValue | None
    convergence_status: ConvergenceStatus
    eligible_clients: SignedCount
    calibration_pending_clients: SignedCount
    evaluation_incomplete_clients: SignedCount
    feature_count: FeatureCount | None
    feature_list_hash: ContentHash
    threshold_aggregation_method: ThresholdAggregationMethod
    normalization_scope: NormalizationScope | None
    train_count: SampleCount | None
    calibration_count: SampleCount | None
    test_count: SampleCount | None


class ThresholdRecord(AuditModel):

    run_id: RunId
    seed: RandomSeed
    stage: ExperimentStage
    policy: ThresholdPolicy
    client_id: ClientId
    threshold_value: Threshold
    threshold_source: ThresholdSource
    calibration_pending: bool
    tau_global: Threshold
    threshold_aggregation_method: ThresholdAggregationMethod
    local_tau_i: ScoreValue | None = None


class ClientMetricRecord(AuditModel):

    run_id: RunId
    seed: RandomSeed
    stage: ExperimentStage
    policy: ThresholdPolicy
    client_id: ClientId
    fpr: FalsePositiveRate
    tpr: TruePositiveRate
    balanced_accuracy: ClassificationScore
    macro_f1: ClassificationScore
    auroc: ClassificationScore | None = None
    pr_auc: ClassificationScore | None = None
    n_benign: SampleCount
    n_attack: SampleCount
    tp: SampleCount
    fp: SampleCount
    tn: SampleCount
    fn: SampleCount
    eligible: bool
    calibration_pending: bool
    evaluation_incomplete: bool
    coverage_ratio: CoverageLabel


class PerAttackMetricRecord(AuditModel):

    run_id: RunId
    seed: RandomSeed
    stage: ExperimentStage
    policy: ThresholdPolicy
    client_id: ClientId
    attack_label: NarrativeText
    status: DenominatorStatus
    tpr: TruePositiveRate | None = None
    detected_count: SampleCount | None = None
    denominator: SignedCount | None = None


class ReconstructionErrorSummaryRecord(AuditModel):

    run_id: RunId | None = None
    policy: ThresholdPolicy | None = None
    seed: RandomSeed
    stage: ExperimentStage
    client_id: ClientId
    stage_split: ScoringStage
    count: SignedCount
    mean: ScoreValue | None
    std: ScoreValue | None
    min: ScoreValue | None
    p50: ScoreValue | None
    p95: ScoreValue | None
    max: ScoreValue | None
    benign_attack_overlap: ScoreValue | None = None
    array_hash: ContentHash


class NBaIoTDeviceCounts(AuditModel):

    device: NBaIoTDevice
    family: NBaIoTDeviceFamily
    benign_train: SignedCount | None
    benign_cal: SignedCount | None
    benign_test: SignedCount | None
    attack_test_total: SignedCount | None
    benign_class_imbalance_ratio: Ratio | None
    attack_files_by_family: dict[NBaIoTAttackFamily, list[ArtifactName]] = Field(
        default_factory=lambda: {
            family: [] for family in NBaIoTAttackFamily
        }
    )


class DatasetPartitionAudit(AuditModel):

    dataset: DatasetID
    stage: ExperimentStage
    seed: RandomSeed | None
    manifest_path: ArtifactName
    manifest_hash: ContentHash
    split_hash: ContentHash
    feature_count: FeatureCount | None
    client_count: SampleCount | None
    nbaiot_per_device: list[NBaIoTDeviceCounts] = Field(
        default_factory=lambda: list[NBaIoTDeviceCounts]()
    )
    confound_summary: NarrativeText | None = None
    chronological_split_verified: bool | None = None
    contiguous_gap_verified: bool | None = None


class MetricDenominatorAuditRecord(AuditModel):

    run_id: RunId
    seed: RandomSeed
    stage: ExperimentStage
    policy: ThresholdPolicy
    client_id: ClientId
    fpr_denominator: SignedCount
    fpr_denominator_expected: SignedCount
    fpr_status: DenominatorStatus
    tpr_denominator: SignedCount
    tpr_denominator_expected: SignedCount
    tpr_status: DenominatorStatus
    macro_f1_label_space: NarrativeText = "binary"
    macro_f1_status: DenominatorStatus


class MetricRecomputationRecord(AuditModel):

    run_id: RunId
    seed: RandomSeed
    stage: ExperimentStage
    policy: ThresholdPolicy
    client_id: ClientId
    metric: MetricName
    saved_value: ScoreValue | None
    recomputed_value: ScoreValue | None
    abs_diff: SignedDelta | None
    status: DenominatorStatus


class PolicyInvariantResult(AuditModel):

    stage: ExperimentStage
    seed: RandomSeed
    status: AuditStatus
    checked_policies: list[ThresholdPolicy]
    missing_policies: list[ThresholdPolicy] = Field(
        default_factory=lambda: list[ThresholdPolicy]()
    )
    split_hash_shared: bool
    model_or_encoder_hash_shared: bool
    reconstruction_error_hashes_shared: bool
    scoring_code_hash_shared: bool
    metrics_code_hash_shared: bool
    disallowed_differences: list[NarrativeText] = Field(default_factory=list)


class WarningRecord(AuditModel):

    severity: AuditSeverity
    code: WarningCode
    message: NarrativeText
    exact_command: NarrativeText | None = None


class ConvergenceAuditRecord(AuditModel):

    stage: ExperimentStage
    seed: RandomSeed
    checkpoint_path: ArtifactName
    convergence_round: RoundIndex | None
    convergence_criterion_value: ScoreValue | None
    convergence_status: ConvergenceStatus
    curve_path: ArtifactName | None


class SeedDeltaRecord(AuditModel):

    stage: ExperimentStage
    seed: RandomSeed
    global_cv_fpr: FalsePositiveRate | None
    local_cv_fpr: FalsePositiveRate | None
    cluster_cv_fpr: FalsePositiveRate | None
    global_cv_tpr: TruePositiveRate | None
    local_cv_tpr: TruePositiveRate | None
    cluster_cv_tpr: TruePositiveRate | None
    global_macro_f1_mean: ClassificationScore | None
    local_macro_f1_mean: ClassificationScore | None
    cluster_macro_f1_mean: ClassificationScore | None
    global_macro_f1_p10: ClassificationScore | None
    local_macro_f1_p10: ClassificationScore | None
    cluster_macro_f1_p10: ClassificationScore | None
    global_auroc_mean: ClassificationScore | None
    local_auroc_mean: ClassificationScore | None
    cluster_auroc_mean: ClassificationScore | None
    global_pr_auc_mean: ClassificationScore | None
    local_pr_auc_mean: ClassificationScore | None
    cluster_pr_auc_mean: ClassificationScore | None
    global_mean_fpr: FalsePositiveRate | None
    local_mean_fpr: FalsePositiveRate | None
    cluster_mean_fpr: FalsePositiveRate | None
    global_std_fpr: FalsePositiveRate | None
    local_std_fpr: FalsePositiveRate | None
    cluster_std_fpr: FalsePositiveRate | None
    global_iqr_fpr: FalsePositiveRate | None
    local_iqr_fpr: FalsePositiveRate | None
    cluster_iqr_fpr: FalsePositiveRate | None
    global_worst_client_fpr: FalsePositiveRate | None
    local_worst_client_fpr: FalsePositiveRate | None
    cluster_worst_client_fpr: FalsePositiveRate | None
    global_worst_client_tpr: TruePositiveRate | None
    local_worst_client_tpr: TruePositiveRate | None
    cluster_worst_client_tpr: TruePositiveRate | None
    global_worst_client_macro_f1: ClassificationScore | None
    local_worst_client_macro_f1: ClassificationScore | None
    cluster_worst_client_macro_f1: ClassificationScore | None
    global_worst_client_balanced_accuracy: ClassificationScore | None
    local_worst_client_balanced_accuracy: ClassificationScore | None
    cluster_worst_client_balanced_accuracy: ClassificationScore | None
    delta_cv_fpr_global_minus_local: SignedDelta | None
    delta_cv_fpr_global_minus_cluster: SignedDelta | None
    delta_cv_tpr_global_minus_local: SignedDelta | None
    delta_cv_tpr_global_minus_cluster: SignedDelta | None
    delta_macro_f1_global_minus_local: SignedDelta | None
    delta_macro_f1_global_minus_cluster: SignedDelta | None
    delta_pr_auc_global_minus_local: SignedDelta | None
    delta_pr_auc_global_minus_cluster: SignedDelta | None
    delta_auroc_global_minus_local: SignedDelta | None
    delta_auroc_global_minus_cluster: SignedDelta | None
    global_convergence_round: RoundIndex | None
    local_convergence_round: RoundIndex | None
    cluster_convergence_round: RoundIndex | None
    global_tau_global: ScoreValue | None
    local_tau_global: ScoreValue | None
    cluster_tau_global: ScoreValue | None
    coverage_ratio: CoverageLabel
    status: AuditStatus


class FPRCompanionRecord(AuditModel):

    run_id: RunId
    seed: RandomSeed
    stage: ExperimentStage
    policy: ThresholdPolicy
    cv_fpr: FalsePositiveRate | None
    mean_fpr: FalsePositiveRate | None
    std_fpr: FalsePositiveRate | None
    iqr_fpr: FalsePositiveRate | None
    worst_client_fpr: FalsePositiveRate | None
    eligible_count: SampleCount
    client_count: SampleCount
    coverage_ratio: CoverageLabel


class WorstClientRecord(AuditModel):

    run_id: RunId
    seed: RandomSeed
    stage: ExperimentStage
    policy: ThresholdPolicy
    metric: MetricName
    direction: WorstDirection
    worst_client_id: ClientId | None
    worst_value: ScoreValue | None
    eligible_pool_size: SignedCount


class ClusterAssignmentRecord(AuditModel):

    run_id: RunId
    seed: RandomSeed
    stage: ExperimentStage
    client_id: ClientId
    cluster_id: ClusterId
    threshold_value: Threshold
    fingerprint_mean: ScoreValue | None = None
    fingerprint_std: ScoreValue | None = None
    fingerprint_skew: ScoreValue | None = None
    fingerprint_p95: ScoreValue | None = None
    k_selected: ClusterCount | None = None
    silhouette: ClassificationScore | None = None
    silhouette_scores: dict[RecordKey, ClassificationScore] = Field(default_factory=dict)


class ClusterStabilityRecord(AuditModel):

    stage: ExperimentStage
    seed_a: SignedCount
    seed_b: SignedCount
    adjusted_rand_index: ClassificationScore


class ScoreCellVerification(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)
    cell: TrainingCellId
    expected_client_ids: list[ClientId] = Field(
        default_factory=lambda: list[ClientId]()
    )
    expected_splits: list[ScoringStage] = Field(
        default_factory=lambda: list[ScoringStage]()
    )
    checks: list[ValidationCheck]
    overall_status: AuditStatus


class RecomputedClientMetricsSnapshot(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True)
    fpr: FalsePositiveRate
    tpr: TruePositiveRate
    balanced_accuracy: ClassificationScore
    macro_f1: ClassificationScore
    n_benign: SampleCount
    n_attack: SampleCount
    confusion_matrix: dict[ConfusionKey, SampleCount]
    threshold_value: Threshold


class RecomputedMetricsSnapshot(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True)
    policy: ThresholdPolicy
    stage: ExperimentStage
    seed: RandomSeed
    dataset: DatasetID
    tau_global: Threshold
    coverage_ratio: Ratio
    cv_fpr: FalsePositiveRate
    cv_tpr: TruePositiveRate
    mean_fpr: FalsePositiveRate
    std_fpr: FalsePositiveRate
    iqr_fpr: FalsePositiveRate
    iqr_tpr: TruePositiveRate
    max_min_fpr_gap: FalsePositiveRate
    worst_client_fpr: FalsePositiveRate
    worst_client_id: ClientId | None
    worst_ba: ScoreValue
    p10_macro_f1: ClassificationScore
    client_count: SampleCount
    eligible_count: SampleCount
    pending_count: SampleCount
    eligible_ids: tuple[ClientId, ...]
    pending_ids: tuple[ClientId, ...]
    per_client: dict[ClientId, RecomputedClientMetricsSnapshot]


class StoredMetricsSnapshot(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True)
    policy: ThresholdPolicy | None
    stage: ExperimentStage | None
    seed: RandomSeed | None
    dataset: DatasetID | None
    tau_global: Threshold | None
    coverage_ratio: Ratio | None
    cv_fpr: FalsePositiveRate | None
    cv_tpr: TruePositiveRate | None
    mean_fpr: FalsePositiveRate | None
    std_fpr: FalsePositiveRate | None
    iqr_fpr: FalsePositiveRate | None
    iqr_tpr: TruePositiveRate | None
    max_min_fpr_gap: FalsePositiveRate | None
    worst_client_fpr: FalsePositiveRate | None
    worst_client_id: ClientId | None
    worst_ba: ScoreValue | None
    p10_macro_f1: ClassificationScore | None
    client_count: SampleCount | None
    eligible_count: SampleCount | None
    pending_count: SampleCount | None
    eligible_ids: tuple[ClientId, ...] | None
    pending_ids: tuple[ClientId, ...] | None


class PolicyReproductionResult(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True)
    policy: ThresholdPolicy
    status: AuditStatus
    metrics_path: ArtifactName
    recomputed: RecomputedMetricsSnapshot
    stored: StoredMetricsSnapshot
    checks: list[ValidationCheck]


class CellReproductionResult(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)
    cell: TrainingCellId
    overall_status: AuditStatus
    policies: list[PolicyReproductionResult]
    missing_policies: list[ThresholdPolicy] = Field(
        default_factory=lambda: list[ThresholdPolicy]()
    )


class CellVerdict(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)
    cell: TrainingCellId
    verdict: ReuseVerdict
    manifest_status: AuditStatus
    reproduction_status: AuditStatus
    reason: CellVerdictReason | NarrativeText
    failed_checks: list[ValidationCheck] = Field(
        default_factory=lambda: list[ValidationCheck]()
    )


class VerdictSummary(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True)
    total: SampleCount
    verified_reuse_safe: SignedCount
    reuse_blocked_rerun_required: SignedCount
    by_stage: dict[ExperimentStage, dict[ReuseVerdict, SignedCount]]


class VerdictTable(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True)
    cells: list[CellVerdict]
    summary: VerdictSummary
