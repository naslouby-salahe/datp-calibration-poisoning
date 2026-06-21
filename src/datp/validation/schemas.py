from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from datp.checkpointing.enums import ConvergenceStatus
from datp.config.stages import ExperimentStage
from datp.core.enums import (
    NormalizationScope,
    ScoringStage,
    ThresholdAggregationMethod,
    ThresholdSource,
)
from datp.core.metric_enums import MetricName
from datp.data.catalog import ClientIdentity, DatasetID
from datp.validation.enums import (
    AuditSeverity,
    AuditStatus,
    DenominatorStatus,
    HomogeneityVerdict,
    WarningCode,
    WorstDirection,
)


class AuditModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ValidationCheck(AuditModel):
    code: str
    status: AuditStatus
    detail: str = ""


class RunManifestRecord(AuditModel):
    run_id: str
    timestamp: str
    git_commit_hash: str
    seed: int
    dataset: DatasetID
    stage: ExperimentStage
    policy: ThresholdPolicy
    client_count: int
    split_hash: str
    model_hash: str
    encoder_hash: str
    training_config_hash: str
    preprocessing_config_hash: str
    scoring_code_hash: str
    threshold_code_hash: str
    metrics_code_hash: str
    artifact_schema_version: str
    convergence_round: int | None
    convergence_criterion_value: float | None
    convergence_status: ConvergenceStatus
    eligible_clients: int
    calibration_pending_clients: int
    evaluation_incomplete_clients: int
    feature_count: int | None
    feature_list_hash: str
    threshold_aggregation_method: ThresholdAggregationMethod
    normalization_scope: NormalizationScope | None
    train_count: int | None
    calibration_count: int | None
    test_count: int | None


class ThresholdRecord(AuditModel):
    run_id: str
    seed: int
    stage: ExperimentStage
    policy: ThresholdPolicy
    client_id: str
    threshold_value: float
    threshold_source: ThresholdSource
    calibration_pending: bool
    tau_global: float
    threshold_aggregation_method: ThresholdAggregationMethod
    local_tau_i: float | None = None


class ClientMetricRecord(AuditModel):
    run_id: str
    seed: int
    stage: ExperimentStage
    policy: ThresholdPolicy
    client_id: str
    fpr: float
    tpr: float
    balanced_accuracy: float
    macro_f1: float
    auroc: float | None = None
    pr_auc: float | None = None
    n_benign: int
    n_attack: int
    tp: int
    fp: int
    tn: int
    fn: int
    eligible: bool
    calibration_pending: bool
    evaluation_incomplete: bool
    coverage_ratio: str


class PerAttackMetricRecord(AuditModel):
    run_id: str
    seed: int
    stage: ExperimentStage
    policy: ThresholdPolicy
    client_id: str
    attack_label: str
    status: DenominatorStatus
    tpr: float | None = None
    detected_count: int | None = None
    denominator: int | None = None


class ReconstructionErrorSummaryRecord(AuditModel):
    run_id: str | None = None
    policy: ThresholdPolicy | None = None
    seed: int
    stage: ExperimentStage
    client_id: str
    stage_split: ScoringStage
    count: int
    mean: float | None
    std: float | None
    min: float | None
    p50: float | None
    p95: float | None
    max: float | None
    benign_attack_overlap: float | None = None
    array_hash: str


class NBaIoTDeviceCounts(AuditModel):
    """Per-device split counts; attack_files_by_family from raw manifest."""

    device: str
    family: str
    benign_train: int | None
    benign_cal: int | None
    benign_test: int | None
    attack_test_total: int | None
    benign_class_imbalance_ratio: float | None
    attack_files_by_family: Mapping[str, list[str]] = Field(default_factory=dict)


class CICIoTProtocolAudit(AuditModel):
    """CICIoT2023 processed split: 39 features, attack-preserving cap."""

    dataset: DatasetID
    feature_count: int
    feature_list: list[str]
    dropped_columns_note: str
    feature_list_hash: str
    client_identity_source: ClientIdentity
    n_clients: int
    cap_total: int
    cap_attack_reserve: int
    cap_strategy: str


class DatasetPartitionAudit(AuditModel):
    dataset: DatasetID
    stage: ExperimentStage
    seed: int | None
    manifest_path: str
    manifest_hash: str
    split_hash: str
    feature_count: int | None
    client_count: int | None
    nbaiot_per_device: list[NBaIoTDeviceCounts] = Field(default_factory=list)
    ciciot_protocol: CICIoTProtocolAudit | None = None
    confound_summary: str | None = None
    chronological_split_verified: bool | None = None
    contiguous_gap_verified: bool | None = None


class MetricDenominatorAuditRecord(AuditModel):
    run_id: str
    seed: int
    stage: ExperimentStage
    policy: ThresholdPolicy
    client_id: str
    fpr_denominator: int
    fpr_denominator_expected: int
    fpr_status: DenominatorStatus
    tpr_denominator: int
    tpr_denominator_expected: int
    tpr_status: DenominatorStatus
    macro_f1_label_space: str = "binary"
    macro_f1_status: DenominatorStatus


class MetricRecomputationRecord(AuditModel):
    run_id: str
    seed: int
    stage: ExperimentStage
    policy: ThresholdPolicy
    client_id: str
    metric: MetricName
    saved_value: float | None
    recomputed_value: float | None
    abs_diff: float | None
    status: DenominatorStatus


class PolicyInvariantResult(AuditModel):
    stage: ExperimentStage
    seed: int
    status: AuditStatus
    checked_policies: list[ThresholdPolicy]
    missing_policies: list[ThresholdPolicy] = Field(default_factory=list)
    split_hash_shared: bool
    model_or_encoder_hash_shared: bool
    reconstruction_error_hashes_shared: bool
    scoring_code_hash_shared: bool
    metrics_code_hash_shared: bool
    disallowed_differences: list[str] = Field(default_factory=list)


class WarningRecord(AuditModel):
    severity: AuditSeverity
    code: WarningCode
    message: str
    exact_command: str | None = None


class ConvergenceAuditRecord(AuditModel):
    stage: ExperimentStage
    seed: int
    checkpoint_path: str
    convergence_round: int | None
    convergence_criterion_value: float | None
    convergence_status: ConvergenceStatus
    curve_path: str | None


class SeedDeltaRecord(AuditModel):
    """Per-(stage, seed) raw metric values and GLOBAL_THRESHOLD-LOCAL_THRESHOLD / GLOBAL_THRESHOLD-CLUSTER_THRESHOLD deltas; required for bootstrap CI generation."""

    stage: ExperimentStage
    seed: int
    global_cv_fpr: float | None
    local_cv_fpr: float | None
    cluster_cv_fpr: float | None
    global_cv_tpr: float | None
    local_cv_tpr: float | None
    cluster_cv_tpr: float | None
    global_macro_f1_mean: float | None
    local_macro_f1_mean: float | None
    cluster_macro_f1_mean: float | None
    global_macro_f1_p10: float | None
    local_macro_f1_p10: float | None
    cluster_macro_f1_p10: float | None
    global_auroc_mean: float | None
    local_auroc_mean: float | None
    cluster_auroc_mean: float | None
    global_pr_auc_mean: float | None
    local_pr_auc_mean: float | None
    cluster_pr_auc_mean: float | None
    global_mean_fpr: float | None
    local_mean_fpr: float | None
    cluster_mean_fpr: float | None
    global_std_fpr: float | None
    local_std_fpr: float | None
    cluster_std_fpr: float | None
    global_iqr_fpr: float | None
    local_iqr_fpr: float | None
    cluster_iqr_fpr: float | None
    global_worst_client_fpr: float | None
    local_worst_client_fpr: float | None
    cluster_worst_client_fpr: float | None
    global_worst_client_tpr: float | None
    local_worst_client_tpr: float | None
    cluster_worst_client_tpr: float | None
    global_worst_client_macro_f1: float | None
    local_worst_client_macro_f1: float | None
    cluster_worst_client_macro_f1: float | None
    global_worst_client_balanced_accuracy: float | None
    local_worst_client_balanced_accuracy: float | None
    cluster_worst_client_balanced_accuracy: float | None
    delta_cv_fpr_global_minus_local: float | None
    delta_cv_fpr_global_minus_cluster: float | None
    delta_cv_tpr_global_minus_local: float | None
    delta_cv_tpr_global_minus_cluster: float | None
    delta_macro_f1_global_minus_local: float | None
    delta_macro_f1_global_minus_cluster: float | None
    delta_pr_auc_global_minus_local: float | None
    delta_pr_auc_global_minus_cluster: float | None
    delta_auroc_global_minus_local: float | None
    delta_auroc_global_minus_cluster: float | None
    global_convergence_round: int | None
    local_convergence_round: int | None
    cluster_convergence_round: int | None
    global_tau_global: float | None
    local_tau_global: float | None
    cluster_tau_global: float | None
    coverage_ratio: str
    status: AuditStatus


class FPRCompanionRecord(AuditModel):
    """CV(FPR) must never be reported alone; this row is its mandatory companion with mean/std/IQR/worst FPR and coverage_ratio."""

    run_id: str
    seed: int
    stage: ExperimentStage
    policy: ThresholdPolicy
    cv_fpr: float | None
    mean_fpr: float | None
    std_fpr: float | None
    iqr_fpr: float | None
    worst_client_fpr: float | None
    eligible_count: int
    client_count: int
    coverage_ratio: str


class CICIoTHomogeneityRecord(AuditModel):
    """Artifact claims may only describe CICIoT2023 clients as homogeneous when verdict is HOMOGENEOUS; HETEROGENEOUS or BLOCKED_PENDING_RUN blocks that claim."""

    stage: ExperimentStage
    seed: int
    policy: ThresholdPolicy
    n_clients_compared: int
    n_pairs: int
    n_bins: int
    pairwise_js_mean: float | None
    pairwise_js_std: float | None
    pairwise_js_p50: float | None
    pairwise_js_p95: float | None
    pairwise_js_max: float | None
    fingerprint_method: Literal["benign_recon_error_histogram"]
    homogeneity_verdict: HomogeneityVerdict


class WorstClientRecord(AuditModel):
    """Worst-client identity per (cell, metric); if constant across seeds, reported claims must label it as an encoder-quality limitation, not a threshold-strategy effect."""

    run_id: str
    seed: int
    stage: ExperimentStage
    policy: ThresholdPolicy
    metric: MetricName
    direction: WorstDirection
    worst_client_id: str | None
    worst_value: float | None
    eligible_pool_size: int


class ClusterAssignmentRecord(AuditModel):
    run_id: str
    seed: int
    stage: ExperimentStage
    client_id: str
    cluster_id: str
    threshold_value: float
    fingerprint_mean: float | None = None
    fingerprint_std: float | None = None
    fingerprint_skew: float | None = None
    fingerprint_p95: float | None = None
    k_selected: int | None = None
    silhouette: float | None = None
    silhouette_scores: dict[str, float] = Field(default_factory=dict)


class ClusterStabilityRecord(AuditModel):
    stage: ExperimentStage
    seed_a: int
    seed_b: int
    adjusted_rand_index: float
