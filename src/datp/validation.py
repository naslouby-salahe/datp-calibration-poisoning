from __future__ import annotations

import dataclasses
import json
import math
import threading
from collections import defaultdict
from collections.abc import Collection, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sklearn.metrics import adjusted_rand_score

from datp.artifacts import ArtifactLayout, write_csv
from datp.artifacts import write_json_atomic as write_json
from datp.config import DatpConfig, ExperimentStage
from datp.core import (
    ClusterCountSilhouetteScore,
    ClusterMetadata,
    PolicyRunId,
    ThresholdResult,
    TrainingCellId,
    array_hash,
    get_logger,
    hash_file,
    hash_jsonable,
    source_hash,
    utc_timestamp,
)
from datp.core import git_commit as current_git_commit
from datp.data import (
    NBAIOT_SPEC,
    PartitionManifest,
    Split,
    dataset_for_stage,
    processed_root,
    split_path,
)
from datp.enums import (
    CONTROLLED_POLICIES,
    POLICY_THRESHOLD_SOURCE,
    THRESHOLD_AGGREGATION_BY_POLICY,
    WORST_CLIENT_DIRECTIONS,
    ArtifactDir,
    ArtifactFile,
    AttackLabel,
    AuditArtifact,
    AuditOutputName,
    AuditSchemaVersion,
    AuditSeverity,
    AuditStatus,
    ClientStatus,
    ConfusionKey,
    ConvergenceStatus,
    ConvergenceSummaryKey,
    CoverageFallback,
    DatasetID,
    DenominatorStatus,
    InvariantField,
    MetricName,
    NBaIoTAttackFamily,
    NBaIoTDevice,
    NBaIoTDeviceFamily,
    NormalizationScope,
    PathToken,
    PayloadKey,
    RemediationCommand,
    ScoringStage,
    ThresholdAggregationMethod,
    ThresholdPolicy,
    ThresholdSource,
    ValidationCountThreshold,
    ValidationThreshold,
    WarningCode,
    WorstDirection,
)
from datp.evaluation import compute_binary_ranking_metrics
from datp.scoring import ScoringManifestAuditView, ScoringManifestSentinel
from datp.scoring import read_score_column as read_scores
from datp.statistics import EXTREME_PERCENTILE, iqr
from datp.thresholding import (
    ThresholdDerivation,
    derive_threshold,
    validate_metrics_payload,
)
from datp.types import (
    ArtifactName,
    ClassificationScore,
    ClientId,
    ClusterCount,
    ClusterId,
    ContentHash,
    CoverageLabel,
    FalsePositiveRate,
    FeatureCount,
    JsonRecord,
    JsonValue,
    NarrativeText,
    RandomSeed,
    Ratio,
    RecordKey,
    RoundIndex,
    RunId,
    SampleCount,
    SchemaVersion,
    ScoreValue,
    ScoreVector,
    SignedCount,
    SignedDelta,
    Threshold,
    TruePositiveRate,
)


class AuditModel(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True)


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
    score_dir: ArtifactName
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


@dataclass(frozen=True, slots=True)
class InvariantKey:

    stage: ExperimentStage
    seed: RandomSeed


@dataclass(frozen=True, slots=True)
class InvariantHashes:

    split_hash: ContentHash
    model_hash: ContentHash
    encoder_hash: ContentHash
    scoring_code_hash: ContentHash
    metrics_code_hash: ContentHash


@dataclass(frozen=True, slots=True)
class ScoreArtifactHash:
    stage: ScoringStage
    client_id: ClientId
    array_digest: ContentHash


def _check_hash_flags(hashes: list[InvariantHashes]) -> tuple[bool, bool, bool, bool]:
    sp_sh = len({h.split_hash for h in hashes}) <= 1
    mo_sh = len({h.model_hash for h in hashes} | {h.encoder_hash for h in hashes}) <= 1
    sc_sh = len({h.scoring_code_hash for h in hashes}) <= 1
    me_sh = len({h.metrics_code_hash for h in hashes}) <= 1
    return sp_sh, mo_sh, sc_sh, me_sh


def _resolve_invariant_status(
    sp_sh: bool,
    mo_sh: bool,
    sc_sh: bool,
    me_sh: bool,
    rec_sh: bool,
    rec_miss: bool,
    missing: list[ThresholdPolicy],
) -> tuple[AuditStatus, list[InvariantField]]:
    disallowed: list[InvariantField] = []
    if not sp_sh:
        disallowed.append(InvariantField.SPLIT_HASH)
    if not mo_sh:
        disallowed.append(InvariantField.MODEL_OR_ENCODER_HASH)
    if not sc_sh:
        disallowed.append(InvariantField.SCORING_CODE_HASH)
    if not me_sh:
        disallowed.append(InvariantField.METRICS_CODE_HASH)
    if not rec_sh and not rec_miss:
        disallowed.append(InvariantField.RECONSTRUCTION_ERROR_ARRAYS)
    if disallowed:
        return AuditStatus.FAIL, disallowed
    if missing or rec_miss:
        return AuditStatus.BLOCKED_PENDING_RUN, disallowed
    return AuditStatus.PASS, disallowed


def build_invariant_results(
    invariant_inputs: dict[InvariantKey, dict[ThresholdPolicy, InvariantHashes]],
    score_hashes_by_cell: dict[
        InvariantKey, dict[ThresholdPolicy, frozenset[ScoreArtifactHash]]
    ],
) -> list[PolicyInvariantResult]:
    results: list[PolicyInvariantResult] = []

    for key, by_policy in sorted(
        invariant_inputs.items(), key=lambda i: (i[0].stage, i[0].seed)
    ):
        required = list(CONTROLLED_POLICIES)
        checked = [b for b in required if b in by_policy]
        missing = [b for b in required if b not in by_policy]

        hashes = [by_policy[b] for b in checked]
        sp_sh, mo_sh, sc_sh, me_sh = _check_hash_flags(hashes)

        cell_scores = score_hashes_by_cell.get(key, {})
        score_maps = [cell_scores[b] for b in checked if b in cell_scores]
        rec_miss = not score_maps
        rec_sh = all(m == score_maps[0] for m in score_maps) if score_maps else False

        status, disallowed = _resolve_invariant_status(
            sp_sh, mo_sh, sc_sh, me_sh, rec_sh, rec_miss, missing
        )

        results.append(
            PolicyInvariantResult(
                stage=key.stage,
                seed=key.seed,
                status=status,
                checked_policies=checked,
                missing_policies=missing,
                split_hash_shared=sp_sh,
                model_or_encoder_hash_shared=mo_sh,
                reconstruction_error_hashes_shared=rec_sh,
                scoring_code_hash_shared=sc_sh,
                metrics_code_hash_shared=me_sh,
                disallowed_differences=[v for v in disallowed],
            )
        )

    return results


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
    from datp.evaluation import recompute_binary_metrics

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


_MODULE = "validation.datasets"


def _parquet_num_rows(path: Path) -> SignedCount | None:
    return pq.read_metadata(path).num_rows if path.exists() else None


def _attack_files_mapping(
    file_hash_keys: list[ContentHash], device: NBaIoTDevice
) -> dict[NBaIoTAttackFamily, list[ArtifactName]]:
    prefix = f"{device}/"
    grouped: dict[NBaIoTAttackFamily, list[ArtifactName]] = {
        family: [] for family in NBAIOT_SPEC.attack_family_dirs
    }

    for key in file_hash_keys:
        if key.startswith(prefix):
            rest = key[len(prefix) :]
            for family in NBAIOT_SPEC.attack_family_dirs:
                if rest.startswith(f"{family}/"):
                    grouped[family].append(rest[len(family) + 1 :])
                    break

    return {family: sorted(files) for family, files in grouped.items()}


def build_nbaiot_per_device(
    processed_root: Path, file_hash_keys: list[ContentHash]
) -> list[NBaIoTDeviceCounts]:
    family_map = NBAIOT_SPEC.family_map
    if family_map is None:
        raise ValueError(
            f"[{_MODULE}] N-BaIoT spec must have family_map. Expected: non-null family_map. Got: {repr(family_map)}."
        )

    out: list[NBaIoTDeviceCounts] = []
    for device in NBAIOT_SPEC.device_ids:
        device_dir = processed_root / device
        train_n = _parquet_num_rows(split_path(device_dir, Split.TRAIN))
        cal_n = _parquet_num_rows(split_path(device_dir, Split.CAL))
        benign_test_n = _parquet_num_rows(split_path(device_dir, Split.TEST_BENIGN))
        attack_test_n = _parquet_num_rows(split_path(device_dir, Split.TEST_ATTACK))

        ratio: Ratio | None = None
        if benign_test_n is not None and attack_test_n is not None:
            denom = benign_test_n + attack_test_n
            ratio = float(benign_test_n / denom) if denom > 0 else None

        out.append(
            NBaIoTDeviceCounts(
                device=device,
                family=family_map[device],
                benign_train=train_n,
                benign_cal=cal_n,
                benign_test=benign_test_n,
                attack_test_total=attack_test_n,
                benign_class_imbalance_ratio=ratio,
                attack_files_by_family=_attack_files_mapping(file_hash_keys, device),
            )
        )
    return out


@dataclasses.dataclass(frozen=True, slots=True)
class ClusterAssignments:

    seed: RandomSeed
    assignments: dict[ClientId, ClusterId]


def compute_cluster_stability(
    cluster_assignments_by_seed: tuple[ClusterAssignments, ...],
    stage: ExperimentStage,
) -> list[ClusterStabilityRecord]:
    seed_to_assigns = {
        item.seed: dict(item.assignments) for item in cluster_assignments_by_seed
    }
    seeds = sorted(seed_to_assigns.keys())
    records: list[ClusterStabilityRecord] = []

    for i, seed_a in enumerate(seeds):
        assigns_a = seed_to_assigns[seed_a]
        for seed_b in seeds[i + 1 :]:
            assigns_b = seed_to_assigns[seed_b]
            common = sorted(assigns_a.keys() & assigns_b.keys())

            if len(common) < 2:
                continue

            labels_a = [assigns_a[client_id] for client_id in common]
            labels_b = [assigns_b[client_id] for client_id in common]

            records.append(
                ClusterStabilityRecord(
                    stage=stage,
                    seed_a=seed_a,
                    seed_b=seed_b,
                    adjusted_rand_index=float(adjusted_rand_score(labels_a, labels_b)),
                )
            )
    return records


def completed_metric_paths(base_dir: Path) -> list[Path]:
    return sorted(
        (base_dir / ArtifactDir.RESULTS).glob(
            f"*/*/{PathToken.SEED_PREFIX}*/**/{ArtifactFile.METRICS}"
        )
    )


def _parse_seed(segment: NarrativeText) -> RandomSeed:
    if not segment.startswith(PathToken.SEED_PREFIX):
        raise ValueError(
            f"Expected seed segment with prefix {PathToken.SEED_PREFIX!r}, got {segment!r}"
        )
    return RandomSeed(int(segment.removeprefix(PathToken.SEED_PREFIX)))


def parse_metric_path(base_dir: Path, path: Path) -> PolicyRunId:
    parts = path.relative_to(base_dir / ArtifactDir.RESULTS).parts
    return PolicyRunId(
        cell=TrainingCellId(
            stage=ExperimentStage(parts[0]), seed=_parse_seed(parts[2])
        ),
        policy=ThresholdPolicy(parts[1]),
    )


logger = get_logger(__name__)


NBAIOT_CONFOUND_SUMMARY = (
    "N-BaIoT natural per-device partition mixes device-specific benign "
    "feature heterogeneity with attack-variant skew (different devices were "
    "exposed to different gafgyt/mirai subtypes during capture). Threshold "
    "dispersion across this partition is therefore not pure feature-skew "
    "isolation."
)


SCORING_SOURCE_FILES = (Path("src/datp/scoring.py"),)


THRESHOLD_SOURCE_FILES = (Path("src/datp/thresholding.py"),)


METRICS_SOURCE_FILES = (Path("src/datp/evaluation.py"),)


@dataclasses.dataclass(frozen=True, slots=True)
class ConvergencePayload:

    convergence_round: RoundIndex | None
    convergence_criterion_value: ScoreValue | None
    convergence_status: ConvergenceStatus
    curve_path: ArtifactName | None


def convergence_payload(score_root: Path) -> ConvergencePayload:
    summary_path = score_root / ArtifactFile.CONVERGENCE_SUMMARY
    curve_path = score_root / ArtifactFile.CONVERGENCE_CURVE

    if not summary_path.exists():
        return ConvergencePayload(None, None, ConvergenceStatus.MISSING_SUMMARY, None)

    payload = json.loads(summary_path.read_text())
    try:
        status = ConvergenceStatus(payload[ConvergenceSummaryKey.CONVERGENCE_STATUS])
    except ValueError:
        status = ConvergenceStatus.UNKNOWN

    return ConvergencePayload(
        convergence_round=payload[ConvergenceSummaryKey.CONVERGENCE_ROUND],
        convergence_criterion_value=payload[
            ConvergenceSummaryKey.CONVERGENCE_CRITERION
        ],
        convergence_status=status,
        curve_path=str(curve_path) if curve_path.exists() else None,
    )


@dataclass(frozen=True, slots=True)
class CellPanel:

    cv_fpr: FalsePositiveRate | None = None
    cv_tpr: TruePositiveRate | None = None
    macro_f1_mean: ClassificationScore | None = None
    macro_f1_p10: ClassificationScore | None = None
    auroc_mean: ClassificationScore | None = None
    pr_auc_mean: ClassificationScore | None = None
    mean_fpr: FalsePositiveRate | None = None
    std_fpr: FalsePositiveRate | None = None
    iqr_fpr: FalsePositiveRate | None = None
    worst_client_fpr: FalsePositiveRate | None = None
    worst_client_tpr: TruePositiveRate | None = None
    worst_client_macro_f1: ClassificationScore | None = None
    worst_client_balanced_accuracy: ClassificationScore | None = None
    convergence_round: RoundIndex | None = None
    tau_global: Threshold | None = None
    coverage_ratio: CoverageLabel | None = None


@dataclass(frozen=True, slots=True)
class EligibleMetricPairs:

    fprs: list[tuple[ClientId, FalsePositiveRate]]
    tprs: list[tuple[ClientId, TruePositiveRate]]
    macro_f1s: list[tuple[ClientId, ClassificationScore]]
    balanced_accuracies: list[tuple[ClientId, ClassificationScore]]


@dataclass(frozen=True, slots=True)
class WorstClientMetrics:

    fpr: FalsePositiveRate | None
    tpr: TruePositiveRate | None
    macro_f1: ClassificationScore | None
    balanced_accuracy: ClassificationScore | None


@dataclass(frozen=True, slots=True)
class CellPanelInputs:

    cv_fpr: FalsePositiveRate
    worst_client: WorstClientMetrics
    eligible_macro_f1s: list[tuple[ClientId, ClassificationScore]]
    macro_f1_values: ScoreVector
    auroc_values: ScoreVector
    pr_auc_values: ScoreVector
    eligible_fpr_values: ScoreVector


@dataclass(slots=True)
class AuditAccumulator:

    manifest_records: list[RunManifestRecord] = field(
        default_factory=lambda: list[RunManifestRecord]()
    )
    client_records: list[ClientMetricRecord] = field(
        default_factory=lambda: list[ClientMetricRecord]()
    )
    attack_records: list[PerAttackMetricRecord] = field(
        default_factory=lambda: list[PerAttackMetricRecord]()
    )
    threshold_records: list[ThresholdRecord] = field(
        default_factory=lambda: list[ThresholdRecord]()
    )
    recon_records: list[ReconstructionErrorSummaryRecord] = field(
        default_factory=lambda: list[ReconstructionErrorSummaryRecord]()
    )
    denominator_records: list[MetricDenominatorAuditRecord] = field(
        default_factory=lambda: list[MetricDenominatorAuditRecord]()
    )
    convergence_records: list[ConvergenceAuditRecord] = field(
        default_factory=lambda: list[ConvergenceAuditRecord]()
    )
    cluster_records: list[ClusterAssignmentRecord] = field(
        default_factory=lambda: list[ClusterAssignmentRecord]()
    )
    companion_records: list[FPRCompanionRecord] = field(
        default_factory=lambda: list[FPRCompanionRecord]()
    )
    worst_client_records: list[WorstClientRecord] = field(
        default_factory=lambda: list[WorstClientRecord]()
    )
    partition_audits: dict[InvariantKey, DatasetPartitionAudit] = field(
        default_factory=lambda: dict[InvariantKey, DatasetPartitionAudit]()
    )
    invariant_inputs: dict[InvariantKey, dict[ThresholdPolicy, InvariantHashes]] = (
        field(default_factory=lambda: defaultdict(dict))
    )
    score_hashes_by_cell: dict[
        InvariantKey, dict[ThresholdPolicy, frozenset[ScoreArtifactHash]]
    ] = field(default_factory=lambda: defaultdict(dict))
    recomputation_records: list[MetricRecomputationRecord] = field(
        default_factory=lambda: list[MetricRecomputationRecord]()
    )
    cell_panel: dict[
        tuple[ExperimentStage, RandomSeed, ThresholdPolicy], CellPanel
    ] = field(
        default_factory=lambda: dict[
            tuple[ExperimentStage, RandomSeed, ThresholdPolicy], CellPanel
        ]()
    )
    warnings: list[WarningRecord] = field(
        default_factory=lambda: list[WarningRecord]()
    )
    missing_confusion_warned: set[NarrativeText] = field(
        default_factory=lambda: set[str]()
    )


class AuditClientMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    client_id: ClientId
    fpr: FalsePositiveRate
    tpr: TruePositiveRate
    balanced_accuracy: ClassificationScore
    macro_f1: ClassificationScore
    confusion_matrix: dict[ConfusionKey, SignedCount]
    n_benign: SampleCount
    n_attack: SampleCount
    auroc: ClassificationScore | None = None
    pr_auc: ClassificationScore | None = None
    ranking_metrics_provided: bool


class AuditMetricsPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    stage: ExperimentStage
    policy: ThresholdPolicy
    seed: RandomSeed
    run_id: RunId
    tau_global: Threshold
    cv_fpr: FalsePositiveRate
    mean_fpr: FalsePositiveRate | None = None
    std_fpr: FalsePositiveRate | None = None
    cv_tpr: TruePositiveRate
    client_count: SampleCount
    eligible_count: SampleCount
    pending_count: SampleCount
    eligible_ids: tuple[ClientId, ...]
    pending_ids: tuple[ClientId, ...]
    eval_incomplete_ids: tuple[ClientId, ...]
    per_client: tuple[AuditClientMetrics, ...]
    normalization_scope: NormalizationScope | None = None


@dataclass(frozen=True, slots=True)
class RunIdentity:
    stage: ExperimentStage
    policy: ThresholdPolicy
    seed: RandomSeed
    run_id: RunId

    @property
    def invariant_key(self) -> InvariantKey:
        return InvariantKey(stage=self.stage, seed=self.seed)


@dataclass(frozen=True, slots=True)
class RunArtifactPaths:
    score_root: Path
    partition_manifest: Path


@dataclass(frozen=True, slots=True)
class RunDataHashes:
    split: ContentHash
    model: NarrativeText
    training: NarrativeText
    preprocessing: NarrativeText


@dataclass(frozen=True, slots=True)
class RunContext:
    identity: RunIdentity
    metrics: AuditMetricsPayload
    paths: RunArtifactPaths
    hashes: RunDataHashes
    partition: PartitionManifest | None
    convergence: ConvergencePayload

    @property
    def test_count(self) -> SampleCount:
        return sum(row.n_benign + row.n_attack for row in self.metrics.per_client)

    @property
    def incomplete_ids(self) -> frozenset[ClientId]:
        return frozenset(self.metrics.eval_incomplete_ids)


@dataclass(frozen=True, slots=True)
class ScoreArrays:

    cal_errors: dict[ClientId, ScoreVector]
    test_benign_scores: dict[ClientId, ScoreVector]
    test_attack_scores: dict[ClientId, ScoreVector]
    threshold_result: ThresholdResult | None


@dataclass(frozen=True, slots=True)
class AuditHashes:

    git_commit: NarrativeText
    timestamp: NarrativeText
    scoring_hash: ContentHash
    threshold_hash: ContentHash
    metrics_hash: ContentHash


def lookup_threshold_agg(policy: ThresholdPolicy) -> ThresholdAggregationMethod:
    return THRESHOLD_AGGREGATION_BY_POLICY.get(
        policy, ThresholdAggregationMethod.PER_CLIENT_PERCENTILE
    )


def finite_array(values: list[ScoreValue]) -> ScoreVector:
    arr = np.asarray(values, dtype=np.float64)
    return arr[np.isfinite(arr)]


def argworst(
    pairs: list[tuple[ClientId, ScoreValue]], direction: WorstDirection
) -> tuple[ClientId | None, ScoreValue | None]:
    finite = [(cid, value) for cid, value in pairs if math.isfinite(value)]
    if not finite:
        return None, None
    return (
        max(finite, key=lambda item: item[1])
        if direction == WorstDirection.MAX_IS_WORST
        else min(finite, key=lambda item: item[1])
    )


def safe_diff(a: ScoreValue | None, b: ScoreValue | None) -> SignedDelta | None:
    return (
        a - b
        if a is not None and b is not None and math.isfinite(a) and math.isfinite(b)
        else None
    )


def binary_auc_fields(
    row: AuditClientMetrics, benign: ScoreVector | None, attack: ScoreVector | None
) -> tuple[ClassificationScore | None, ClassificationScore | None]:
    if row.ranking_metrics_provided:
        return row.auroc, row.pr_auc
    if benign is None or attack is None:
        return None, None
    ranking = compute_binary_ranking_metrics(benign, attack)
    return ranking.auroc, ranking.pr_auc


def score_stage_files(score_root: Path, stage: ScoringStage) -> list[Path]:
    stage_dir = score_root / stage
    return sorted(stage_dir.glob(PathToken.PARQUET_GLOB)) if stage_dir.exists() else []


@dataclasses.dataclass(frozen=True, slots=True)
class ThresholdState:

    client_thresholds: dict[ClientId, Threshold]
    threshold_aggregation_method: ThresholdAggregationMethod
    test_benign_scores: dict[ClientId, ScoreVector]
    test_attack_scores: dict[ClientId, ScoreVector]
    cal_errors: dict[ClientId, ScoreVector]

    @classmethod
    def empty(cls, policy: ThresholdPolicy) -> ThresholdState:
        return cls({}, lookup_threshold_agg(policy), {}, {}, {})


def _scoring_model_hash(score_root: Path) -> ContentHash:
    manifest_path = score_root / ArtifactFile.SCORING_MANIFEST
    if not manifest_path.exists():
        return "MISSING"
    return ScoringManifestAuditView.model_validate_json(
        manifest_path.read_text()
    ).model_hash


def _typed_metrics_payload(
    payload: JsonRecord,
) -> AuditMetricsPayload:
    clients = payload[PayloadKey.PER_CLIENT]
    if isinstance(clients, Mapping):
        client_rows = tuple(
            _typed_client_metrics(row, ClientId(client_id))
            for client_id, row in clients.items()
        )
    elif isinstance(clients, list):
        client_rows = tuple(_typed_client_metrics(row) for row in clients)
    else:
        raise TypeError("Per-client metrics must be a list or object")

    return AuditMetricsPayload.model_validate(
        {
            "stage": payload[PayloadKey.STAGE],
            "policy": payload[PayloadKey.POLICY],
            "seed": payload[PayloadKey.SEED],
            "run_id": payload[PayloadKey.RUN_ID],
            "tau_global": payload[MetricName.TAU_GLOBAL],
            "cv_fpr": payload[MetricName.CV_FPR],
            "mean_fpr": payload.get(MetricName.MEAN_FPR),
            "std_fpr": payload.get(MetricName.STD_FPR),
            "cv_tpr": payload[MetricName.CV_TPR],
            "client_count": payload[PayloadKey.CLIENT_COUNT],
            "eligible_count": payload[PayloadKey.ELIGIBLE_COUNT],
            "pending_count": payload[PayloadKey.PENDING_COUNT],
            "eligible_ids": payload[PayloadKey.ELIGIBLE_IDS],
            "pending_ids": payload[PayloadKey.PENDING_IDS],
            "eval_incomplete_ids": payload[PayloadKey.EVAL_INCOMPLETE_IDS],
            "per_client": client_rows,
            "normalization_scope": payload.get(PayloadKey.NORMALIZATION_SCOPE),
        }
    )


def _typed_client_metrics(
    row: JsonValue, client_id: ClientId | None = None
) -> AuditClientMetrics:
    if not isinstance(row, Mapping):
        raise TypeError("Per-client metrics must be an object")
    return AuditClientMetrics.model_validate(
        {
            "client_id": client_id
            if client_id is not None
            else row[PayloadKey.CLIENT_ID],
            "fpr": row[MetricName.FPR],
            "tpr": row[MetricName.TPR],
            "balanced_accuracy": row[MetricName.BALANCED_ACCURACY],
            "macro_f1": row[MetricName.MACRO_F1],
            "confusion_matrix": row[PayloadKey.CONFUSION_MATRIX],
            "n_benign": row[PayloadKey.N_BENIGN],
            "n_attack": row[PayloadKey.N_ATTACK],
            "auroc": (
                row[MetricName.AUROC] if MetricName.AUROC in row else None
            ),
            "pr_auc": row[MetricName.PR_AUC] if MetricName.PR_AUC in row else None,
            "ranking_metrics_provided": (
                MetricName.AUROC in row or MetricName.PR_AUC in row
            ),
        }
    )


def build_run_context(
    stage: ExperimentStage,
    policy: ThresholdPolicy,
    seed: RandomSeed,
    run_id: RunId,
    metrics: AuditMetricsPayload,
    data_root: Path,
    metrics_path: Path,
    base_dir: Path,
) -> RunContext:
    cell = TrainingCellId(stage=stage, seed=seed)
    score_root = ArtifactLayout(base_dir=base_dir, stage=stage).score_cell(cell).score_dir

    partition_path = (
        processed_root(dataset_for_stage(stage), base_dir=data_root)
        / ArtifactFile.MANIFEST
    )
    partition_payload = (
        PartitionManifest.model_validate_json(partition_path.read_bytes())
        if partition_path.exists()
        else None
    )
    conv = convergence_payload(score_root)

    return RunContext(
        identity=RunIdentity(stage, policy, seed, run_id),
        metrics=metrics,
        paths=RunArtifactPaths(score_root, partition_path),
        hashes=RunDataHashes(
            split=hash_jsonable(
                partition_payload.model_dump(mode="json") if partition_payload else {}
            ),
            model=_scoring_model_hash(score_root),
            training=hash_file(metrics_path.parent / ArtifactFile.RESOLVED_CONFIG),
            preprocessing=hash_file(partition_path),
        ),
        partition=partition_payload,
        convergence=conv,
    )


def load_run_context(
    metrics_path: Path, base_dir: Path, acc: AuditAccumulator, data_root: Path | None
) -> RunContext | None:
    run_id_obj = parse_metric_path(base_dir, metrics_path)
    metrics_payload = json.loads(metrics_path.read_text())

    if schema_failures := validate_metrics_payload(
        metrics_payload, module="audit.results"
    ):
        for failure in schema_failures:
            acc.warnings.append(
                WarningRecord(
                    severity=AuditSeverity.FAIL,
                    code=WarningCode.SCHEMA_VERSION_MISMATCH,
                    message=f"{metrics_path}: {failure}",
                )
            )
        return None

    try:
        metrics = _typed_metrics_payload(metrics_payload)
    except (ValidationError, ValueError, TypeError) as exc:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.FAIL,
                code=WarningCode.SCHEMA_VERSION_MISMATCH,
                message=f"{metrics_path}: metrics payload failed typed validation: {exc}",
            )
        )
        return None

    return build_run_context(
        stage=run_id_obj.stage,
        policy=run_id_obj.policy,
        seed=run_id_obj.seed,
        run_id=run_id_obj.audit_id(),
        metrics=metrics,
        data_root=data_root or base_dir,
        metrics_path=metrics_path,
        base_dir=base_dir,
    )


def load_score_arrays(
    acc: AuditAccumulator, ctx: RunContext, cfg: DatpConfig
) -> ScoreArrays:
    cal_errors, test_benign_scores, test_attack_scores, threshold_result = (
        {},
        {},
        {},
        None,
    )
    try:
        cal_errors = {
            ClientId(p.stem): read_scores(p)
            for p in score_stage_files(ctx.paths.score_root, ScoringStage.CAL)
        }
        test_benign_scores = {
            ClientId(p.stem): read_scores(p)
            for p in score_stage_files(ctx.paths.score_root, ScoringStage.TEST_BENIGN)
        }
        test_attack_scores = {
            ClientId(p.stem): read_scores(p)
            for p in score_stage_files(ctx.paths.score_root, ScoringStage.TEST_ATTACK)
        }
        threshold_result = derive_threshold(
            ThresholdDerivation(
                policy=ctx.identity.policy,
                client_errors=cal_errors,
                n_min=cfg.threshold.n_min,
                q=cfg.threshold.q,
                tau_global=ctx.metrics.tau_global,
                threshold_cfg=cfg.threshold,
                seed=ctx.identity.seed,
            )
        )
    except Exception as exc:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.FAIL,
                code=WarningCode.THRESHOLD_RECONSTRUCTION_FAILED,
                message=f"Could not reconstruct thresholds for {ctx.identity.run_id}: {exc}",
            )
        )
    return ScoreArrays(
        cal_errors, test_benign_scores, test_attack_scores, threshold_result
    )


def cluster_silhouette_scores_for_report(
    scores: tuple[ClusterCountSilhouetteScore, ...],
) -> dict[RecordKey, ClassificationScore]:
    return {str(score.cluster_count): score.score for score in scores}


def compute_denominator_status(
    has_confusion: bool, eval_incomplete: bool, fpr_ok: bool, tpr_ok: bool
) -> tuple[DenominatorStatus, DenominatorStatus, DenominatorStatus]:
    if not has_confusion:
        return (
            DenominatorStatus.BLOCKED_PENDING_RUN,
            DenominatorStatus.BLOCKED_PENDING_RUN,
            DenominatorStatus.BLOCKED_PENDING_RUN,
        )
    if eval_incomplete:
        return (
            (DenominatorStatus.PASS if fpr_ok else DenominatorStatus.FAIL),
            DenominatorStatus.EXCLUDED_EVALUATION_INCOMPLETE,
            DenominatorStatus.EXCLUDED_EVALUATION_INCOMPLETE,
        )
    return (
        (DenominatorStatus.PASS if fpr_ok else DenominatorStatus.FAIL),
        (DenominatorStatus.PASS if tpr_ok else DenominatorStatus.FAIL),
        DenominatorStatus.PASS,
    )


@dataclasses.dataclass(frozen=True, slots=True)
class ClientRowData:
    client_id: ClientId
    n_benign: SampleCount
    n_attack: SampleCount
    tp: SignedCount
    fp: SignedCount
    tn: SignedCount
    fn: SignedCount
    has_confusion: bool
    evaluation_incomplete: bool


def extract_client_row_data(
    row: AuditClientMetrics, incomplete: frozenset[ClientId]
) -> ClientRowData:
    cm = row.confusion_matrix
    tp, fp, tn, fn = (cm.get(k, 0) for k in ConfusionKey)
    client_id = ClientId(row.client_id)
    n_benign, n_attack = row.n_benign, row.n_attack
    return ClientRowData(
        client_id=client_id,
        n_benign=n_benign,
        n_attack=n_attack,
        tp=tp,
        fp=fp,
        tn=tn,
        fn=fn,
        has_confusion=bool(cm),
        evaluation_incomplete=client_id in incomplete or n_attack == 0,
    )


def collect_eligible_metric_pairs(
    normalized_clients: tuple[AuditClientMetrics, ...],
    eligible_ids: Collection[ClientId],
    incomplete: frozenset[ClientId],
) -> EligibleMetricPairs:
    eligible_rows = [
        r for r in normalized_clients if ClientId(r.client_id) in eligible_ids
    ]
    fprs = [(ClientId(r.client_id), r.fpr) for r in eligible_rows]
    tprs = [
        (ClientId(r.client_id), r.tpr)
        for r in eligible_rows
        if ClientId(r.client_id) not in incomplete
    ]
    f1s = [(ClientId(r.client_id), r.macro_f1) for r in eligible_rows]
    bas = [(ClientId(r.client_id), r.balanced_accuracy) for r in eligible_rows]
    return EligibleMetricPairs(fprs, tprs, f1s, bas)


def _append_cluster_records(
    ctx: RunContext,
    cluster_meta: ClusterMetadata,
    acc: AuditAccumulator,
) -> None:
    for info in cluster_meta.cluster_info:
        for cid in info.members:
            fingerprint = cluster_meta.fingerprint_for(cid)
            acc.cluster_records.append(
                ClusterAssignmentRecord(
                    run_id=ctx.identity.run_id,
                    seed=ctx.identity.seed,
                    stage=ctx.identity.stage,
                    client_id=cid,
                    cluster_id=info.cluster_id,
                    threshold_value=info.tau_cluster,
                    fingerprint_mean=fingerprint.mean,
                    fingerprint_std=fingerprint.std,
                    fingerprint_skew=fingerprint.skewness,
                    fingerprint_p95=fingerprint.p95,
                    k_selected=cluster_meta.k,
                    silhouette=cluster_meta.silhouette,
                    silhouette_scores=cluster_silhouette_scores_for_report(
                        cluster_meta.silhouette_scores
                    ),
                )
            )


def _record_thresholds_and_clusters(
    ctx: RunContext,
    arrays: ScoreArrays,
    cfg: DatpConfig,
    acc: AuditAccumulator,
) -> ThresholdState:
    threshold_state = ThresholdState.empty(ctx.identity.policy)
    if ctx.identity.policy not in CONTROLLED_POLICIES or not arrays.threshold_result:
        return threshold_state

    client_thresholds: dict[ClientId, Threshold] = {}
    local_taus = {
        cid: float(np.percentile(errors, cfg.threshold.q))
        for cid, errors in arrays.cal_errors.items()
        if errors.size >= cfg.threshold.n_min
    }

    for ct in sorted(
        arrays.threshold_result.client_thresholds, key=lambda i: i.client_id
    ):
        client_thresholds[ct.client_id] = ct.threshold
        acc.threshold_records.append(
            ThresholdRecord(
                run_id=ctx.identity.run_id,
                seed=ctx.identity.seed,
                stage=ctx.identity.stage,
                policy=ctx.identity.policy,
                client_id=ct.client_id,
                threshold_value=ct.threshold,
                threshold_source=ThresholdSource.TAU_GLOBAL_FALLBACK
                if ct.status is ClientStatus.CALIBRATION_PENDING
                else POLICY_THRESHOLD_SOURCE[ctx.identity.policy],
                calibration_pending=ct.status is ClientStatus.CALIBRATION_PENDING,
                tau_global=arrays.threshold_result.tau_global,
                threshold_aggregation_method=lookup_threshold_agg(ctx.identity.policy),
                local_tau_i=local_taus.get(ct.client_id),
            )
        )

    if (
        ctx.identity.policy == ThresholdPolicy.CLUSTER_THRESHOLD
        and arrays.threshold_result.cluster
    ):
        _append_cluster_records(ctx, arrays.threshold_result.cluster, acc)

    if ctx.identity.policy == ThresholdPolicy.GLOBAL_THRESHOLD:
        pooled = float(
            np.percentile(
                np.concatenate(list(arrays.cal_errors.values())),
                cfg.threshold.q,
            )
        )
        if not math.isclose(arrays.threshold_result.tau_global, pooled):
            acc.warnings.append(
                WarningRecord(
                    severity=AuditSeverity.INFO,
                    code=WarningCode.GLOBAL_NOT_POOLED_PERCENTILE,
                    message=f"{ctx.identity.run_id} tau_global is arithmetic mean.",
                )
            )

    return ThresholdState(
        client_thresholds,
        lookup_threshold_agg(ctx.identity.policy),
        arrays.test_benign_scores,
        arrays.test_attack_scores,
        arrays.cal_errors,
    )


def _process_single_client_metrics(
    ctx: RunContext,
    row: AuditClientMetrics,
    threshold_state: ThresholdState,
    coverage_ratio: CoverageLabel,
    acc: AuditAccumulator,
) -> None:
    row_data = extract_client_row_data(row, ctx.incomplete_ids)
    cid = row_data.client_id
    n_benign = row_data.n_benign
    n_attack = row_data.n_attack
    tp, fp, tn, fn = row_data.tp, row_data.fp, row_data.tn, row_data.fn
    has_conf = row_data.has_confusion
    eval_inc = row_data.evaluation_incomplete

    if not has_conf and ctx.identity.run_id not in acc.missing_confusion_warned:
        acc.missing_confusion_warned.add(ctx.identity.run_id)
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.MISSING_CONFUSION_MATRIX,
                message=f"Missing confusion matrices for {ctx.identity.run_id}.",
                exact_command=RemediationCommand.RUN_BASELINE,
            )
        )

    fpr_ok = has_conf and (fp + tn) == n_benign and n_benign > 0
    tpr_ok = has_conf and (tp + fn) == n_attack and n_attack > 0
    fpr_s, tpr_s, f1_s = compute_denominator_status(has_conf, eval_inc, fpr_ok, tpr_ok)

    acc.denominator_records.append(
        MetricDenominatorAuditRecord(
            run_id=ctx.identity.run_id,
            seed=ctx.identity.seed,
            stage=ctx.identity.stage,
            policy=ctx.identity.policy,
            client_id=cid,
            fpr_denominator=fp + tn,
            fpr_denominator_expected=n_benign,
            fpr_status=fpr_s,
            tpr_denominator=tp + fn,
            tpr_denominator_expected=n_attack,
            tpr_status=tpr_s,
            macro_f1_status=f1_s,
        )
    )

    if has_conf:
        append_recomputation_records(
            acc.recomputation_records,
            RecomputationParams(
                ctx.identity.run_id,
                ctx.identity.seed,
                ctx.identity.stage,
                ctx.identity.policy,
                cid,
                tp,
                fp,
                tn,
                fn,
                n_benign,
                n_attack,
                row.fpr,
                row.tpr,
                row.balanced_accuracy,
                row.macro_f1,
            ),
        )

    auroc, pr_auc = binary_auc_fields(
        row,
        threshold_state.test_benign_scores.get(cid),
        threshold_state.test_attack_scores.get(cid),
    )
    acc.client_records.append(
        ClientMetricRecord(
            run_id=ctx.identity.run_id,
            seed=ctx.identity.seed,
            stage=ctx.identity.stage,
            policy=ctx.identity.policy,
            client_id=cid,
            fpr=row.fpr,
            tpr=row.tpr,
            balanced_accuracy=row.balanced_accuracy,
            macro_f1=row.macro_f1,
            auroc=auroc,
            pr_auc=pr_auc,
            n_benign=n_benign,
            n_attack=n_attack,
            tp=tp,
            fp=fp,
            tn=tn,
            fn=fn,
            eligible=cid in ctx.metrics.eligible_ids,
            calibration_pending=cid in ctx.metrics.pending_ids,
            evaluation_incomplete=eval_inc,
            coverage_ratio=coverage_ratio,
        )
    )
    acc.attack_records.append(
        PerAttackMetricRecord(
            run_id=ctx.identity.run_id,
            seed=ctx.identity.seed,
            stage=ctx.identity.stage,
            policy=ctx.identity.policy,
            client_id=cid,
            attack_label=AttackLabel.BINARY_ATTACK,
            status=DenominatorStatus.EXCLUDED_EVALUATION_INCOMPLETE
            if eval_inc
            else DenominatorStatus.PASS,
            tpr=None if eval_inc else row.tpr,
            detected_count=None if eval_inc else tp,
            denominator=None if eval_inc else n_attack,
        )
    )


def _process_client_metrics_loop(
    ctx: RunContext,
    threshold_state: ThresholdState,
    coverage_ratio: CoverageLabel,
    acc: AuditAccumulator,
) -> None:
    for row in ctx.metrics.per_client:
        _process_single_client_metrics(
            ctx,
            row,
            threshold_state,
            coverage_ratio,
            acc,
        )


def _build_cell_panel(
    ctx: RunContext,
    inputs: CellPanelInputs,
    coverage_ratio: CoverageLabel,
) -> CellPanel:
    f1_p10_arr = finite_array([value for _, value in inputs.eligible_macro_f1s])
    cv_tpr_raw = ctx.metrics.cv_tpr

    return CellPanel(
        inputs.cv_fpr if math.isfinite(inputs.cv_fpr) else None,
        cv_tpr_raw if math.isfinite(cv_tpr_raw) else None,
        float(inputs.macro_f1_values.mean()) if inputs.macro_f1_values.size else None,
        float(np.percentile(f1_p10_arr, 10.0)) if f1_p10_arr.size else None,
        float(inputs.auroc_values.mean()) if inputs.auroc_values.size else None,
        float(inputs.pr_auc_values.mean()) if inputs.pr_auc_values.size else None,
        float(inputs.eligible_fpr_values.mean())
        if inputs.eligible_fpr_values.size
        else None,
        float(np.std(inputs.eligible_fpr_values, ddof=1))
        if inputs.eligible_fpr_values.size > 1
        else None,
        iqr(inputs.eligible_fpr_values)
        if inputs.eligible_fpr_values.size
        else None,
        inputs.worst_client.fpr,
        inputs.worst_client.tpr,
        inputs.worst_client.macro_f1,
        inputs.worst_client.balanced_accuracy,
        ctx.convergence.convergence_round,
        ctx.metrics.tau_global,
        coverage_ratio,
    )


def _record_aggregates_and_cell_panel(
    ctx: RunContext,
    threshold_state: ThresholdState,
    coverage_ratio: CoverageLabel,
    acc: AuditAccumulator,
) -> None:
    pairs = collect_eligible_metric_pairs(
        ctx.metrics.per_client, ctx.metrics.eligible_ids, ctx.incomplete_ids
    )
    eligible_fpr_vals = finite_array([value for _, value in pairs.fprs])
    cv_fpr_val = ctx.metrics.cv_fpr

    if math.isfinite(cv_fpr_val) and (
        ctx.metrics.mean_fpr is None or ctx.metrics.std_fpr is None
    ):
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.FAIL,
                code=WarningCode.NAKED_CV_FPR,
                message=f"{ctx.identity.run_id} naked CV FPR.",
                exact_command=RemediationCommand.RUN_BASELINE,
            )
        )

    fpr_id, fpr_v = argworst(pairs.fprs, WORST_CLIENT_DIRECTIONS[MetricName.FPR])
    tpr_id, tpr_v = argworst(pairs.tprs, WORST_CLIENT_DIRECTIONS[MetricName.TPR])
    f1_id, f1_v = argworst(
        pairs.macro_f1s, WORST_CLIENT_DIRECTIONS[MetricName.MACRO_F1]
    )
    ba_id, ba_v = argworst(
        pairs.balanced_accuracies,
        WORST_CLIENT_DIRECTIONS[MetricName.BALANCED_ACCURACY],
    )

    acc.companion_records.append(
        FPRCompanionRecord(
            run_id=ctx.identity.run_id,
            seed=ctx.identity.seed,
            stage=ctx.identity.stage,
            policy=ctx.identity.policy,
            cv_fpr=cv_fpr_val if math.isfinite(cv_fpr_val) else None,
            mean_fpr=float(eligible_fpr_vals.mean())
            if eligible_fpr_vals.size
            else None,
            std_fpr=float(np.std(eligible_fpr_vals, ddof=1))
            if eligible_fpr_vals.size > 1
            else None,
            iqr_fpr=iqr(eligible_fpr_vals) if eligible_fpr_vals.size else None,
            worst_client_fpr=fpr_v,
            eligible_count=len(ctx.metrics.eligible_ids),
            client_count=ctx.metrics.client_count,
            coverage_ratio=coverage_ratio,
        )
    )

    for m_name, (w_cid, w_val, p_size) in {
        MetricName.FPR: (fpr_id, fpr_v, len(pairs.fprs)),
        MetricName.TPR: (tpr_id, tpr_v, len(pairs.tprs)),
        MetricName.MACRO_F1: (f1_id, f1_v, len(pairs.macro_f1s)),
        MetricName.BALANCED_ACCURACY: (
            ba_id,
            ba_v,
            len(pairs.balanced_accuracies),
        ),
    }.items():
        acc.worst_client_records.append(
            WorstClientRecord(
                run_id=ctx.identity.run_id,
                seed=ctx.identity.seed,
                stage=ctx.identity.stage,
                policy=ctx.identity.policy,
                metric=m_name,
                direction=WORST_CLIENT_DIRECTIONS[m_name],
                worst_client_id=w_cid,
                worst_value=w_val,
                eligible_pool_size=p_size,
            )
        )

    f1_arr = finite_array([r.macro_f1 for r in ctx.metrics.per_client])
    auroc_arr = finite_array(
        [row.auroc for row in ctx.metrics.per_client if row.auroc is not None]
    )
    pr_arr = finite_array(
        [row.pr_auc for row in ctx.metrics.per_client if row.pr_auc is not None]
    )
    panel_inputs = CellPanelInputs(
        cv_fpr=cv_fpr_val,
        worst_client=WorstClientMetrics(fpr_v, tpr_v, f1_v, ba_v),
        eligible_macro_f1s=pairs.macro_f1s,
        macro_f1_values=f1_arr,
        auroc_values=auroc_arr,
        pr_auc_values=pr_arr,
        eligible_fpr_values=eligible_fpr_vals,
    )
    acc.cell_panel[(ctx.identity.stage, ctx.identity.seed, ctx.identity.policy)] = (
        _build_cell_panel(ctx, panel_inputs, coverage_ratio)
    )


def _record_manifest_and_partition(
    ctx: RunContext,
    threshold_state: ThresholdState,
    hashes: AuditHashes,
    acc: AuditAccumulator,
) -> None:
    metadata = ctx.partition.metadata if ctx.partition else None
    feature_count = metadata.n_features if metadata else None
    acc.manifest_records.append(
        RunManifestRecord(
            run_id=ctx.identity.run_id,
            timestamp=hashes.timestamp,
            git_commit_hash=hashes.git_commit,
            seed=ctx.identity.seed,
            dataset=dataset_for_stage(ctx.identity.stage),
            stage=ctx.identity.stage,
            policy=ctx.identity.policy,
            client_count=ctx.metrics.client_count,
            split_hash=ctx.hashes.split,
            model_hash=ctx.hashes.model,
            encoder_hash=ctx.hashes.model,
            training_config_hash=ctx.hashes.training,
            preprocessing_config_hash=ctx.hashes.preprocessing,
            scoring_code_hash=hashes.scoring_hash,
            threshold_code_hash=hashes.threshold_hash,
            metrics_code_hash=hashes.metrics_hash,
            artifact_schema_version=AuditSchemaVersion.V1_0,
            convergence_round=ctx.convergence.convergence_round,
            convergence_criterion_value=ctx.convergence.convergence_criterion_value,
            convergence_status=ctx.convergence.convergence_status,
            eligible_clients=ctx.metrics.eligible_count,
            calibration_pending_clients=ctx.metrics.pending_count,
            evaluation_incomplete_clients=len(ctx.incomplete_ids),
            feature_count=feature_count,
            feature_list_hash=ScoringManifestSentinel.NOT_PROVIDED
            if feature_count is None
            else hash_jsonable({"feature_count": feature_count}),
            threshold_aggregation_method=threshold_state.threshold_aggregation_method,
            normalization_scope=ctx.metrics.normalization_scope,
            train_count=None,
            calibration_count=None,
            test_count=ctx.test_count,
        )
    )
    acc.invariant_inputs[ctx.identity.invariant_key][ctx.identity.policy] = InvariantHashes(
        ctx.hashes.split,
        ctx.hashes.model,
        ctx.hashes.model,
        hashes.scoring_hash,
        hashes.metrics_hash,
    )

    if ctx.paths.partition_manifest.exists():
        acc.partition_audits[ctx.identity.invariant_key] = DatasetPartitionAudit(
            dataset=dataset_for_stage(ctx.identity.stage),
            stage=ctx.identity.stage,
            seed=ctx.identity.seed,
            manifest_path=str(ctx.paths.partition_manifest),
            manifest_hash=hash_file(ctx.paths.partition_manifest),
            split_hash=ctx.hashes.split,
            feature_count=feature_count,
            client_count=(
                metadata.n_clients or metadata.n_devices
                if metadata
                else None
            ),
            nbaiot_per_device=build_nbaiot_per_device(
                ctx.paths.partition_manifest.parent,
                list(ctx.partition.file_hashes)
                if ctx.partition
                else [],
            ),
            confound_summary=NBAIOT_CONFOUND_SUMMARY,
            chronological_split_verified=True,
            contiguous_gap_verified=True,
        )
    else:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.MISSING_PARTITION_MANIFEST,
                message=f"Missing partition for {ctx.identity.run_id}.",
                exact_command=RemediationCommand.RUN_BASELINE,
            )
        )

    acc.convergence_records.append(
        ConvergenceAuditRecord(
            stage=ctx.identity.stage,
            seed=ctx.identity.seed,
            score_dir=str(ctx.paths.score_root),
            convergence_round=ctx.convergence.convergence_round,
            convergence_criterion_value=ctx.convergence.convergence_criterion_value,
            convergence_status=ctx.convergence.convergence_status,
            curve_path=ctx.convergence.curve_path,
        )
    )


def _add_reconstruction_record(
    ctx: RunContext,
    sp: Path,
    arr: ScoreVector,
    stage: ScoringStage,
    acc: AuditAccumulator,
) -> None:
    acc.recon_records.append(
        ReconstructionErrorSummaryRecord(
            run_id=ctx.identity.run_id,
            policy=ctx.identity.policy,
            seed=ctx.identity.seed,
            stage=ctx.identity.stage,
            client_id=ClientId(sp.stem),
            stage_split=stage,
            count=arr.size,
            mean=float(np.mean(arr)) if arr.size else None,
            std=float(np.std(arr, ddof=1)) if arr.size > 1 else None,
            min=float(np.min(arr)) if arr.size else None,
            p50=float(np.percentile(arr, 50)) if arr.size else None,
            p95=float(np.percentile(arr, EXTREME_PERCENTILE)) if arr.size else None,
            max=float(np.max(arr)) if arr.size else None,
            benign_attack_overlap=None,
            array_hash=array_hash(arr),
        )
    )


def _record_score_hashes(
    ctx: RunContext,
    acc: AuditAccumulator,
) -> None:
    if not (ctx.identity.policy in CONTROLLED_POLICIES and ctx.paths.score_root.exists()):
        return

    cell_hashes: set[ScoreArtifactHash] = set()
    for stage in ScoringStage:
        for sp in score_stage_files(ctx.paths.score_root, stage):
            arr = read_scores(sp)
            cell_hashes.add(
                ScoreArtifactHash(
                    stage=stage,
                    client_id=ClientId(sp.stem),
                    array_digest=array_hash(arr),
                )
            )
            if ctx.identity.policy == ThresholdPolicy.GLOBAL_THRESHOLD:
                _add_reconstruction_record(ctx, sp, arr, stage, acc)
    acc.score_hashes_by_cell[ctx.identity.invariant_key][ctx.identity.policy] = frozenset(cell_hashes)


def process_run(
    metrics_path: Path,
    base_dir: Path,
    acc: AuditAccumulator,
    lock: threading.Lock,
    hashes: AuditHashes,
    cfg: DatpConfig,
    data_root: Path | None,
) -> None:
    ctx = load_run_context(metrics_path, base_dir, acc, data_root)
    if ctx is None:
        return

    arrays = load_score_arrays(acc, ctx, cfg)

    with lock:
        threshold_state = _record_thresholds_and_clusters(ctx, arrays, cfg, acc)

    coverage_ratio = (
        CoverageLabel(f"{ctx.metrics.eligible_count}/{ctx.metrics.client_count}")
        if ctx.metrics.client_count
        else CoverageLabel(CoverageFallback.DEFAULT)
    )

    with lock:
        _process_client_metrics_loop(ctx, threshold_state, coverage_ratio, acc)
        _record_aggregates_and_cell_panel(ctx, threshold_state, coverage_ratio, acc)
        _record_manifest_and_partition(ctx, threshold_state, hashes, acc)
        _record_score_hashes(ctx, acc)


_PANEL_FIELD_NAMES: tuple[MetricName, ...] = (
    MetricName.CV_FPR,
    MetricName.CV_TPR,
    MetricName.MACRO_F1_MEAN,
    MetricName.MACRO_F1_P10,
    MetricName.AUROC_MEAN,
    MetricName.PR_AUC_MEAN,
    MetricName.MEAN_FPR,
    MetricName.STD_FPR,
    MetricName.IQR_FPR,
    MetricName.WORST_CLIENT_FPR,
    MetricName.WORST_CLIENT_TPR,
    MetricName.WORST_CLIENT_MACRO_F1,
    MetricName.WORST_CLIENT_BALANCED_ACCURACY,
    MetricName.CONVERGENCE_ROUND,
    MetricName.TAU_GLOBAL,
)


_DELTA_FIELD_MAP: tuple[tuple[MetricName, MetricName], ...] = (
    (MetricName.CV_FPR, MetricName.CV_FPR),
    (MetricName.CV_TPR, MetricName.CV_TPR),
    (MetricName.MACRO_F1, MetricName.MACRO_F1_MEAN),
    (MetricName.PR_AUC, MetricName.PR_AUC_MEAN),
    (MetricName.AUROC, MetricName.AUROC_MEAN),
)


def _panel_value(panel: CellPanel, metric: MetricName) -> JsonValue:
    return asdict(panel)[metric.value]


def _panel_score(panel: CellPanel, metric: MetricName) -> ScoreValue | None:
    value = asdict(panel)[metric.value]
    return value if isinstance(value, float) else None


def _panel_field_dict(
    panels: list[tuple[ThresholdSource, CellPanel]],
) -> JsonRecord:
    return {
        f"{prefix}_{field}": _panel_value(panel, field)
        for prefix, panel in panels
        for field in _PANEL_FIELD_NAMES
    }


def _delta_field_dict(
    g: CellPanel,
    comparisons: list[tuple[ThresholdSource, CellPanel]],
) -> JsonRecord:
    return {
        f"delta_{k}_global_minus_{p}": safe_diff(_panel_score(g, v), _panel_score(panel, v))
        for k, v in _DELTA_FIELD_MAP
        for p, panel in comparisons
    }


def build_seed_deltas(
    cell_panel: dict[tuple[ExperimentStage, RandomSeed, ThresholdPolicy], CellPanel],
    warnings: list[WarningRecord],
) -> list[SeedDeltaRecord]:
    out: list[SeedDeltaRecord] = []
    for stage, seed in sorted({(s, sd) for s, sd, _ in cell_panel}):
        g = cell_panel.get(
            (stage, seed, ThresholdPolicy.GLOBAL_THRESHOLD), CellPanel()
        )
        loc = cell_panel.get(
            (stage, seed, ThresholdPolicy.LOCAL_THRESHOLD), CellPanel()
        )
        c = cell_panel.get(
            (stage, seed, ThresholdPolicy.CLUSTER_THRESHOLD), CellPanel()
        )

        check_local_threshold_utility_tradeoff((stage, seed), g, loc, warnings)

        panels = [
            (ThresholdSource.GLOBAL, g),
            (ThresholdSource.LOCAL, loc),
            (ThresholdSource.CLUSTER, c),
        ]
        comparisons = [
            (ThresholdSource.LOCAL, loc),
            (ThresholdSource.CLUSTER, c),
        ]
        coverage = (
            g.coverage_ratio
            or loc.coverage_ratio
            or c.coverage_ratio
            or CoverageLabel(CoverageFallback.DEFAULT)
        )
        status = (
            AuditStatus.PASS
            if (g.cv_fpr is not None and loc.cv_fpr is not None)
            else AuditStatus.BLOCKED_PENDING_RUN
        )
        out.append(
            SeedDeltaRecord.model_validate(
                {
                    "stage": stage,
                    "seed": seed,
                    "coverage_ratio": coverage,
                    "status": status,
                    **_panel_field_dict(panels),
                    **_delta_field_dict(g, comparisons),
                }
            )
        )
    return out


def _is_worsened(global_val: ScoreValue | None, local_val: ScoreValue | None) -> bool:
    return global_val is not None and local_val is not None and local_val < global_val


def check_local_threshold_utility_tradeoff(
    cell_key: tuple[ExperimentStage, RandomSeed],
    global_panel: CellPanel,
    local_panel: CellPanel,
    warnings: list[WarningRecord],
) -> None:
    stage, seed = cell_key
    worsened = [
        name
        for name, global_val, local_val in (
            ("macro_f1_mean", global_panel.macro_f1_mean, local_panel.macro_f1_mean),
            ("auroc_mean", global_panel.auroc_mean, local_panel.auroc_mean),
            ("pr_auc_mean", global_panel.pr_auc_mean, local_panel.pr_auc_mean),
        )
        if _is_worsened(global_val, local_val)
    ]
    if worsened:
        warnings.append(
            WarningRecord(
                severity=AuditSeverity.WARNING,
                code=WarningCode.LOCAL_UTILITY_TRADEOFF,
                message=f"{stage}_seed{seed} LOCAL_THRESHOLD improves CV(FPR) but worsens {', '.join(worsened)} relative to GLOBAL_THRESHOLD.",
            )
        )


def emit_structural_warnings(
    acc: AuditAccumulator, seed_deltas: list[SeedDeltaRecord]
) -> None:
    if any(
        row.convergence_status == ConvergenceStatus.MISSING_SUMMARY
        for row in acc.convergence_records
    ):
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.MISSING_CONVERGENCE_CURVES,
                message="Missing convergence curves.",
                exact_command=RemediationCommand.RUN_BASELINE,
            )
        )
    if not any(
        row.stage == ExperimentStage.NBAIOT_MAIN and row.status == AuditStatus.PASS
        for row in seed_deltas
    ):
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.PRIMARY_DELTA_INCOMPLETE,
                message="Incomplete GLOBAL vs LOCAL delta.",
                exact_command=RemediationCommand.RUN_BASELINE,
            )
        )
    if not acc.cluster_records:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.CLUSTER_DIAGNOSTICS_INCOMPLETE,
                message="No cluster diagnostics.",
                exact_command=RemediationCommand.RUN_BASELINE,
            )
        )
    acc.warnings.append(
        WarningRecord(
            severity=AuditSeverity.BLOCKED_PENDING_RUN,
            code=WarningCode.FIXED_OPERATING_POINT_METRICS_PENDING,
            message="FPR/TPR fixed point pending.",
            exact_command=RemediationCommand.REPORT,
        )
    )


def emit_worst_client_stability_warnings(
    worst_client_records: list[WorstClientRecord], warnings: list[WarningRecord]
) -> None:
    grouped: defaultdict[
        tuple[ExperimentStage, ThresholdPolicy, MetricName],
        list[tuple[RandomSeed, ClientId | None]],
    ] = defaultdict(list)
    for r in worst_client_records:
        grouped[(r.stage, r.policy, r.metric)].append((r.seed, r.worst_client_id))
    for (stage, policy, metric), entries in grouped.items():
        if len(entries) >= ValidationCountThreshold.WORST_CLIENT_STABLE_MIN_SEEDS:
            ids = sorted({cid for _, cid in entries if cid is not None})
            if len(ids) == 1:
                warnings.append(
                    WarningRecord(
                        severity=AuditSeverity.WARNING,
                        code=WarningCode.WORST_CLIENT_STABLE,
                        message=f"{stage}/{policy} worst client on {metric} is {ids[0]} across all {len(entries)} seeds.",
                    )
                )
            elif len(ids) > 1:
                warnings.append(
                    WarningRecord(
                        severity=AuditSeverity.WARNING,
                        code=WarningCode.WORST_CLIENT_VARIES,
                        message=f"{stage}/{policy} worst client on {metric} rotates among {ids}.",
                    )
                )


def emit_flat_cv_tpr_warnings(
    cell_panel: dict[tuple[ExperimentStage, RandomSeed, ThresholdPolicy], CellPanel],
    warnings: list[WarningRecord],
) -> None:
    by_cell: defaultdict[tuple[ExperimentStage, RandomSeed], list[TruePositiveRate]] = (
        defaultdict(list)
    )
    for (stage, seed, _), panel in cell_panel.items():
        if panel.cv_tpr is not None:
            by_cell[(stage, seed)].append(panel.cv_tpr)
    for (stage, seed), tpr_vals in by_cell.items():
        if len(tpr_vals) >= 2:
            if len(set(tpr_vals)) == 1:
                warnings.append(
                    WarningRecord(
                        severity=AuditSeverity.WARNING,
                        code=WarningCode.FLAT_CV_TPR_SUSPICIOUS,
                        message=f"{stage}_seed{seed} CV(TPR) identical across policies.",
                    )
                )
            elif all(
                abs(v - tpr_vals[0]) < ValidationThreshold.FLAT_CV_TPR_EPSILON
                for v in tpr_vals
            ):
                warnings.append(
                    WarningRecord(
                        severity=AuditSeverity.WARNING,
                        code=WarningCode.FLAT_CV_TPR_SUSPICIOUS,
                        message=f"{stage}_seed{seed} CV(TPR) nearly identical.",
                    )
                )


@dataclass(frozen=True, slots=True)
class AuditOutputPaths:

    paths: tuple[tuple[AuditOutputName, Path], ...]

    def __contains__(self, name: JsonValue) -> bool:
        return any(output_name == name for output_name, _ in self.paths)

    def items(self) -> tuple[tuple[AuditOutputName, Path], ...]:
        return tuple((name, path) for name, path in self.paths)


def _compute_cluster_stability_records(
    acc: AuditAccumulator,
) -> list[ClusterStabilityRecord]:
    assignments_by_stage: defaultdict[
        ExperimentStage,
        defaultdict[RandomSeed, dict[ClientId, ClusterId]],
    ] = defaultdict(lambda: defaultdict(dict))
    for record in acc.cluster_records:
        assignments_by_stage[record.stage][record.seed][record.client_id] = record.cluster_id

    return [
        record
        for stage, assignments_by_seed in assignments_by_stage.items()
        for record in compute_cluster_stability(
            tuple(
                ClusterAssignments(seed, assignments)
                for seed, assignments in assignments_by_seed.items()
            ),
            stage,
        )
    ]


def _write_audit_outputs(
    audit_dir: Path,
    acc: AuditAccumulator,
    seed_deltas: list[SeedDeltaRecord],
    cluster_stability_records: list[ClusterStabilityRecord],
    invariant_results: list[PolicyInvariantResult],
) -> None:
    write_csv(audit_dir / AuditArtifact.RUN_MANIFEST, acc.manifest_records)
    write_csv(audit_dir / AuditArtifact.FPR_COMPANION_METRICS, acc.companion_records)
    write_csv(audit_dir / AuditArtifact.WORST_CLIENT_TRACKING, acc.worst_client_records)
    write_csv(audit_dir / AuditArtifact.CLUSTER_STABILITY, cluster_stability_records)
    write_csv(audit_dir / AuditArtifact.SEED_DELTAS, seed_deltas)
    write_csv(audit_dir / AuditArtifact.PER_CLIENT_METRICS, acc.client_records)
    write_csv(audit_dir / AuditArtifact.PER_ATTACK_METRICS, acc.attack_records)
    write_csv(audit_dir / AuditArtifact.THRESHOLD_VALUES, acc.threshold_records)
    write_csv(audit_dir / AuditArtifact.RECONSTRUCTION_ERROR_SUMMARY, acc.recon_records)
    write_csv(audit_dir / AuditArtifact.CLUSTER_ASSIGNMENTS, acc.cluster_records)
    write_csv(audit_dir / AuditArtifact.CONVERGENCE_AUDIT, acc.convergence_records)
    write_csv(
        audit_dir / AuditArtifact.METRIC_DENOMINATOR_AUDIT, acc.denominator_records
    )
    write_csv(
        audit_dir / AuditArtifact.METRIC_RECOMPUTATION_AUDIT, acc.recomputation_records
    )
    write_json(audit_dir / AuditArtifact.POLICY_INVARIANTS, invariant_results)
    write_json(
        audit_dir / AuditArtifact.DATASET_PARTITION_AUDIT,
        {
            "schema_version": AuditSchemaVersion.V1_0,
            "partitions": tuple(acc.partition_audits.values()),
        },
    )

    warning_lines = ["# datp-cp Results Audit Warnings", ""] + (
        ["No warnings."]
        if not acc.warnings
        else [
            f"- **{w.severity} `{w.code}`**: {w.message}"
            + (f" Command: `{w.exact_command}`" if w.exact_command else "")
            for w in acc.warnings
        ]
    )
    (audit_dir / AuditArtifact.WARNINGS).write_text("\n".join(warning_lines) + "\n")

    pass_count = sum(r.status == AuditStatus.PASS for r in invariant_results)
    blocked_count = sum(
        r.status == AuditStatus.BLOCKED_PENDING_RUN for r in invariant_results
    )
    fail_count = sum(r.status == AuditStatus.FAIL for r in invariant_results)
    (audit_dir / AuditArtifact.AUDIT_SUMMARY).write_text(
        "\n".join(
            [
                "# datp-cp Results Audit Summary",
                "",
                f"- Completed runs audited: {len(acc.manifest_records)}",
                f"- Controlled-policy invariant PASS cells: {pass_count}",
                f"- Controlled-policy invariant BLOCKED_PENDING_RUN cells: {blocked_count}",
                f"- Controlled-policy invariant FAIL cells: {fail_count}",
                f"- Warning records: {len(acc.warnings)}",
                "",
                "Controlled threshold policies share the trained encoder and scores. Threshold attribution claims are valid only after the invariant passes for the same (stage, seed) cell.",
            ]
        )
        + "\n"
    )


_AUDIT_OUTPUT_NAME_ARTIFACT_PAIRS: tuple[tuple[AuditOutputName, AuditArtifact], ...] = (
    (AuditOutputName.POLICY_INVARIANTS, AuditArtifact.POLICY_INVARIANTS),
    (AuditOutputName.RUN_MANIFEST, AuditArtifact.RUN_MANIFEST),
    (AuditOutputName.SEED_DELTAS, AuditArtifact.SEED_DELTAS),
    (AuditOutputName.PER_CLIENT_METRICS, AuditArtifact.PER_CLIENT_METRICS),
    (AuditOutputName.PER_ATTACK_METRICS, AuditArtifact.PER_ATTACK_METRICS),
    (AuditOutputName.THRESHOLD_VALUES, AuditArtifact.THRESHOLD_VALUES),
    (AuditOutputName.RECONSTRUCTION_ERROR_SUMMARY, AuditArtifact.RECONSTRUCTION_ERROR_SUMMARY),
    (AuditOutputName.CLUSTER_ASSIGNMENTS, AuditArtifact.CLUSTER_ASSIGNMENTS),
    (AuditOutputName.DATASET_PARTITION_AUDIT, AuditArtifact.DATASET_PARTITION_AUDIT),
    (AuditOutputName.CONVERGENCE_AUDIT, AuditArtifact.CONVERGENCE_AUDIT),
    (AuditOutputName.METRIC_DENOMINATOR_AUDIT, AuditArtifact.METRIC_DENOMINATOR_AUDIT),
    (AuditOutputName.METRIC_RECOMPUTATION_AUDIT, AuditArtifact.METRIC_RECOMPUTATION_AUDIT),
    (AuditOutputName.FPR_COMPANION_METRICS, AuditArtifact.FPR_COMPANION_METRICS),
    (AuditOutputName.WORST_CLIENT_TRACKING, AuditArtifact.WORST_CLIENT_TRACKING),
    (AuditOutputName.CLUSTER_STABILITY, AuditArtifact.CLUSTER_STABILITY),
    (AuditOutputName.WARNINGS, AuditArtifact.WARNINGS),
    (AuditOutputName.AUDIT_SUMMARY, AuditArtifact.AUDIT_SUMMARY),
)


def run_results_audit(
    base_dir: Path, audit_dir: Path, cfg: DatpConfig, data_root: Path | None = None
) -> AuditOutputPaths:
    base_dir, audit_dir = Path(base_dir), Path(audit_dir)
    audit_dir.mkdir(parents=True, exist_ok=True)

    acc = AuditAccumulator()
    metric_paths = completed_metric_paths(base_dir)
    logger.info(
        "results audit started",
        metric_count=len(metric_paths),
        base_dir=base_dir.as_posix(),
        audit_dir=audit_dir.as_posix(),
    )
    if not metric_paths:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.NO_COMPLETED_RESULTS,
                message="No completed metrics.json found.",
                exact_command=RemediationCommand.RUN_BASELINE,
            )
        )

    hashes = AuditHashes(
        git_commit=current_git_commit(),
        timestamp=utc_timestamp(),
        scoring_hash=source_hash(list(SCORING_SOURCE_FILES)),
        threshold_hash=source_hash(list(THRESHOLD_SOURCE_FILES)),
        metrics_hash=source_hash(list(METRICS_SOURCE_FILES)),
    )

    lock = threading.Lock()
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(
                process_run, path, base_dir, acc, lock, hashes, cfg, data_root
            ): path
            for path in metric_paths
        }
        for future, path in futures.items():
            try:
                future.result()
            except Exception:
                logger.exception(
                    "results audit worker failed", metrics_path=path.as_posix()
                )
                raise

    cluster_stability_records = _compute_cluster_stability_records(acc)
    invariant_results = build_invariant_results(
        acc.invariant_inputs, acc.score_hashes_by_cell
    )
    seed_deltas = build_seed_deltas(acc.cell_panel, acc.warnings)

    emit_structural_warnings(acc, seed_deltas)
    emit_worst_client_stability_warnings(acc.worst_client_records, acc.warnings)
    emit_flat_cv_tpr_warnings(acc.cell_panel, acc.warnings)

    _write_audit_outputs(
        audit_dir, acc, seed_deltas, cluster_stability_records, invariant_results
    )
    logger.info(
        "results audit completed",
        metric_count=len(metric_paths),
        warning_count=len(acc.warnings),
        audit_dir=audit_dir.as_posix(),
    )

    return AuditOutputPaths(
        tuple(
            (name, audit_dir / artifact)
            for name, artifact in _AUDIT_OUTPUT_NAME_ARTIFACT_PAIRS
        )
    )
