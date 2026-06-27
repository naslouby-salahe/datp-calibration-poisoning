"""Full audit result generation: record extraction, convergence, warnings, and reports."""

from __future__ import annotations

import dataclasses
import json
import math
import threading
from collections import defaultdict
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import numpy as np

from datp.artifacts.io import write_csv
from datp.artifacts.io import write_json_atomic as write_json
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile, PathToken
from datp.checkpointing.enums import ConvergenceStatus, ConvergenceSummaryKey
from datp.config.models import DatpConfig
from datp.config.models import ExperimentStage
from datp.core.enums import (
    CONTROLLED_POLICIES,
    POLICY_THRESHOLD_SOURCE,
    THRESHOLD_AGGREGATION_BY_POLICY,
    ConfusionKey,
    MetricName,
    NormalizationScope,
    PayloadKey,
    ScoringStage,
    ThresholdAggregationMethod,
    ThresholdPolicy,
    ThresholdSource,
)
from datp.core.identity import TrainingCellId
from datp.core.provenance import (
    array_hash,
    hash_file,
    hash_jsonable,
    source_hash,
    utc_timestamp,
)
from datp.core.provenance import (
    git_commit as current_git_commit,
)
from datp.core.types import ClusterMetadata, ThresholdResult
from datp.data.catalog import dataset_for_stage
from datp.data.paths import processed_root
from datp.evaluation.artifact_validation import validate_metrics_payload
from datp.evaluation.metrics import compute_binary_ranking_metrics
from datp.scoring.loading import read_score_column as read_scores
from datp.scoring.manifest import SCORING_MANIFEST_NOT_PROVIDED
from datp.statistics.aggregates import iqr
from datp.statistics.constants import EXTREME_PERCENTILE
from datp.thresholding.thresholds import _DeriveInput, derive_threshold
from datp.validation.datasets import (
    ClusterAssignments,
    build_nbaiot_per_device,
    compute_cluster_stability,
)
from datp.validation.discovery import (
    completed_metric_paths,
    parse_metric_path,
)
from datp.validation.enums import (
    WORST_CLIENT_DIRECTIONS,
    AttackLabel,
    AuditArtifact,
    AuditOutputName,
    AuditSchemaVersion,
    AuditSeverity,
    AuditStatus,
    CoverageFallback,
    DenominatorStatus,
    RemediationCommand,
    ValidationThreshold,
    WarningCode,
    WorstDirection,
)
from datp.validation.invariants import (
    InvariantHashes,
    InvariantKey,
    build_invariant_results,
)
from datp.validation.metric_reproducer import (
    RecomputationParams,
    append_recomputation_records,
)
from datp.validation.schemas import (
    ClientMetricRecord,
    ClusterAssignmentRecord,
    ConvergenceAuditRecord,
    DatasetPartitionAudit,
    FPRCompanionRecord,
    MetricDenominatorAuditRecord,
    MetricRecomputationRecord,
    PerAttackMetricRecord,
    ReconstructionErrorSummaryRecord,
    RunManifestRecord,
    SeedDeltaRecord,
    ThresholdRecord,
    WarningRecord,
    WorstClientRecord,
)

NBAIOT_CONFOUND_SUMMARY = (
    "N-BaIoT natural per-device partition mixes device-specific benign "
    "feature heterogeneity with attack-variant skew (different devices were "
    "exposed to different gafgyt/mirai subtypes during capture). Threshold "
    "dispersion across this partition is therefore not pure feature-skew "
    "isolation."
)

SCORING_SOURCE_FILES = (
    Path("src/datp/scoring/generation.py"),
    Path("src/datp/scoring/loading.py"),
    Path("src/datp/scoring/manifest.py"),
)
THRESHOLD_SOURCE_FILES = (
    Path("src/datp/thresholding/policies.py"),
    Path("src/datp/thresholding/eligibility.py"),
    Path("src/datp/thresholding/thresholds.py"),
)
METRICS_SOURCE_FILES = (Path("src/datp/evaluation/metrics.py"),)


@dataclasses.dataclass(frozen=True, slots=True)
class ConvergencePayload:
    """Convergence status extracted from a checkpoint summary file."""

    convergence_round: int | None
    convergence_criterion_value: float | None
    convergence_status: ConvergenceStatus
    curve_path: str | None


def convergence_payload(checkpoint: Path) -> ConvergencePayload:
    """Extract convergence status, round, and criterion from a checkpoint."""
    ckpt_dir = checkpoint.parent
    summary_path = ckpt_dir / ArtifactFile.CONVERGENCE_SUMMARY
    curve_path = ckpt_dir / ArtifactFile.CONVERGENCE_CURVE

    if not summary_path.exists():
        status = (
            ConvergenceStatus.BLOCKED_PENDING_RUN
            if checkpoint.exists()
            else ConvergenceStatus.MISSING_CHECKPOINT
        )
        return ConvergencePayload(None, None, status, None)

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
    """Aggregated per-cell metrics used for seed-delta and panel reporting."""

    cv_fpr: float | None = None
    cv_tpr: float | None = None
    macro_f1_mean: float | None = None
    macro_f1_p10: float | None = None
    auroc_mean: float | None = None
    pr_auc_mean: float | None = None
    mean_fpr: float | None = None
    std_fpr: float | None = None
    iqr_fpr: float | None = None
    worst_client_fpr: float | None = None
    worst_client_tpr: float | None = None
    worst_client_macro_f1: float | None = None
    worst_client_balanced_accuracy: float | None = None
    convergence_round: int | None = None
    tau_global: float | None = None
    coverage_ratio: str | None = None

    @classmethod
    def empty(cls) -> CellPanel:
        """Return a CellPanel with all fields defaulted to None."""
        return cls()


@dataclass(slots=True)
class AuditAccumulator:
    """Mutable collector for all audit records, warnings, and panel data across runs."""

    manifest_records: list[RunManifestRecord] = field(default_factory=list)
    client_records: list[ClientMetricRecord] = field(default_factory=list)
    attack_records: list[PerAttackMetricRecord] = field(default_factory=list)
    threshold_records: list[ThresholdRecord] = field(default_factory=list)
    recon_records: list[ReconstructionErrorSummaryRecord] = field(default_factory=list)
    denominator_records: list[MetricDenominatorAuditRecord] = field(
        default_factory=list
    )
    convergence_records: list[ConvergenceAuditRecord] = field(default_factory=list)
    cluster_records: list[ClusterAssignmentRecord] = field(default_factory=list)
    companion_records: list[FPRCompanionRecord] = field(default_factory=list)
    worst_client_records: list[WorstClientRecord] = field(default_factory=list)
    partition_audits: dict[str, DatasetPartitionAudit] = field(default_factory=dict)
    invariant_inputs: dict[InvariantKey, dict[ThresholdPolicy, InvariantHashes]] = (
        field(default_factory=lambda: defaultdict(dict))
    )
    score_hashes_by_cell: dict[
        InvariantKey, dict[ThresholdPolicy, dict[tuple[ScoringStage, str], str]]
    ] = field(default_factory=lambda: defaultdict(dict))
    recomputation_records: list[MetricRecomputationRecord] = field(default_factory=list)
    cell_panel: dict[tuple[ExperimentStage, int, ThresholdPolicy], CellPanel] = field(
        default_factory=dict
    )
    warnings: list[WarningRecord] = field(default_factory=list)
    missing_confusion_warned: set[str] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class RunContext:
    """Immutable snapshot of all inputs needed to audit a single training run."""

    stage: ExperimentStage
    policy: ThresholdPolicy
    seed: int
    run_id: str
    metrics: dict[str, Any]
    data_root: Path
    score_root: Path
    checkpoint: Path
    partition_path: Path
    partition_payload: dict[str, Any]
    metadata: dict[str, Any]
    feature_count: int | None
    normalized_clients: list[dict[str, Any]]
    client_count: int
    split_hash: str
    model_hash: str
    training_hash: str
    preprocessing_hash: str
    train_count: int | None
    calibration_count: int | None
    test_count: int | None
    eligible_count: int
    pending_count: int
    incomplete_ids: frozenset[str]
    eligible_client_ids: frozenset[str]
    pending_client_ids: frozenset[str]
    convergence_round: int | None
    convergence_value: float | None
    convergence_status: ConvergenceStatus
    curve_path: str | None
    invariant_key: InvariantKey


@dataclass(frozen=True, slots=True)
class ScoreArrays:
    """Reconstructed score arrays and threshold result for a single run."""

    cal_errors: dict[str, np.ndarray]
    test_benign_scores: dict[str, np.ndarray]
    test_attack_scores: dict[str, np.ndarray]
    threshold_result: ThresholdResult | None


@dataclass(frozen=True, slots=True)
class AuditHashes:
    """Immutable bundle of provenance hashes and timestamp for a results audit session."""

    git_commit: str
    timestamp: str
    scoring_hash: str
    threshold_hash: str
    metrics_hash: str


def lookup_threshold_agg(policy: ThresholdPolicy) -> ThresholdAggregationMethod:
    """Resolve the threshold aggregation method for a given policy."""
    return THRESHOLD_AGGREGATION_BY_POLICY.get(
        policy, ThresholdAggregationMethod.PER_CLIENT_PERCENTILE
    )


def finite_array(values: list[float]) -> np.ndarray:
    """Convert a list of floats to a float64 ndarray and drop non-finite entries."""
    arr = np.asarray(values, dtype=np.float64)
    return arr[np.isfinite(arr)]


def float_or_none(raw: object) -> float | None:
    """Coerce a value to a finite float, returning None for non-finite inputs."""
    if raw is None:
        return None
    try:
        val = float(cast(Any, raw))
        return val if math.isfinite(val) else None
    except (ValueError, TypeError):
        return None


def argworst(
    pairs: list[tuple[str, float]], direction: WorstDirection
) -> tuple[str | None, float | None]:
    """Return the (client_id, value) pair with the worst finite value per direction."""
    finite = [(cid, float(v)) for cid, v in pairs if math.isfinite(float(v))]
    if not finite:
        return None, None
    return (
        max(finite, key=lambda item: item[1])
        if direction == WorstDirection.MAX_IS_WORST
        else min(finite, key=lambda item: item[1])
    )


def safe_diff(a: float | None, b: float | None) -> float | None:
    """Return a - b if both are finite, or None otherwise."""
    return (
        float(a - b)
        if a is not None and b is not None and math.isfinite(a) and math.isfinite(b)
        else None
    )


def binary_auc_fields(
    row: dict[str, Any], benign: np.ndarray | None, attack: np.ndarray | None
) -> tuple[float | None, float | None]:
    """Return cached AUROC and PR-AUC from row, or compute from score arrays."""
    if MetricName.AUROC in row or MetricName.PR_AUC in row:
        return float_or_none(row.get(MetricName.AUROC)), float_or_none(
            row.get(MetricName.PR_AUC)
        )
    if benign is None or attack is None:
        return None, None
    ranking = compute_binary_ranking_metrics(benign, attack)
    return ranking.auroc, ranking.pr_auc


def score_stage_files(score_root: Path, stage: ScoringStage) -> list[Path]:
    """List all Parquet score files for a given scoring stage."""
    stage_dir = score_root / stage
    return sorted(stage_dir.glob(PathToken.PARQUET_GLOB)) if stage_dir.exists() else []


def metric_counts(metrics: dict[str, Any]) -> tuple[int | None, int | None, int | None]:
    """Return (train_count, calibration_count, test_count) from a metrics payload."""
    per_client = normalized_per_client(metrics)
    test = sum(
        int(row[PayloadKey.N_BENIGN]) + int(row[PayloadKey.N_ATTACK])
        for row in per_client
    )
    return None, None, test


def normalized_per_client(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize the per-client section of a metrics payload to a list of dicts."""
    per_client = metrics[PayloadKey.PER_CLIENT]
    if isinstance(per_client, dict):
        return [
            dict(values, client_id=client_id)
            for client_id, values in per_client.items()
        ]
    return list(per_client)


@dataclasses.dataclass(frozen=True, slots=True)
class ThresholdState:
    """Resolved threshold data and score arrays produced during audit reconstruction."""

    client_thresholds: dict[str, float]
    threshold_aggregation_method: ThresholdAggregationMethod
    test_benign_scores: dict[str, np.ndarray]
    test_attack_scores: dict[str, np.ndarray]
    cal_errors: dict[str, np.ndarray]

    @classmethod
    def empty(cls, policy: ThresholdPolicy) -> ThresholdState:
        """Return an empty ThresholdState for the given policy."""
        return cls({}, lookup_threshold_agg(policy), {}, {}, {})


def resolve_score_root_and_checkpoint(
    cell: TrainingCellId, layout: ArtifactLayout, checkpoint_round: int | None
) -> tuple[Path, Path]:
    """Resolve score directory and checkpoint path for a training cell."""
    if checkpoint_round is not None:
        return layout.score_cell_for_round(
            cell, checkpoint_round
        ).score_dir, layout.checkpoint_dir_for_round(
            cell, checkpoint_round
        ) / ArtifactFile.MODEL_CHECKPOINT
    return layout.score_cell(cell).score_dir, layout.checkpoint_dir(
        cell
    ) / ArtifactFile.MODEL_CHECKPOINT


def parse_client_id_sets(
    metrics: dict[str, Any],
) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """Return (incomplete_ids, eligible_ids, pending_ids) frozensets from metrics."""
    return (
        frozenset(str(cid) for cid in metrics[PayloadKey.EVAL_INCOMPLETE_IDS]),
        frozenset(str(cid) for cid in metrics[PayloadKey.ELIGIBLE_IDS]),
        frozenset(str(cid) for cid in metrics[PayloadKey.PENDING_IDS]),
    )


def build_run_context(
    stage: ExperimentStage,
    policy: ThresholdPolicy,
    seed: int,
    run_id: str,
    metrics: dict[str, Any],
    data_root: Path,
    metrics_path: Path,
    base_dir: Path,
) -> RunContext:
    """Construct an immutable RunContext from a metrics file and artifact layout."""
    checkpoint_round = metrics.get("checkpoint_round")
    cell = TrainingCellId(stage=stage, seed=seed)
    layout = ArtifactLayout(base_dir=base_dir, stage=stage)
    score_root, checkpoint = resolve_score_root_and_checkpoint(
        cell, layout, checkpoint_round
    )

    partition_path = (
        processed_root(dataset_for_stage(stage), base_dir=data_root)
        / ArtifactFile.MANIFEST
    )
    partition_payload = (
        json.loads(partition_path.read_text()) if partition_path.exists() else {}
    )
    metadata = partition_payload.get("metadata", {})

    train_count, calibration_count, test_count = metric_counts(metrics)
    incomplete_ids, eligible_client_ids, pending_client_ids = parse_client_id_sets(
        metrics
    )
    conv = convergence_payload(checkpoint)

    return RunContext(
        stage=stage,
        policy=policy,
        seed=seed,
        run_id=run_id,
        metrics=metrics,
        data_root=data_root,
        score_root=score_root,
        checkpoint=checkpoint,
        partition_path=partition_path,
        partition_payload=partition_payload,
        metadata=metadata,
        feature_count=metadata.get("n_features"),
        normalized_clients=normalized_per_client(metrics),
        client_count=int(metrics[PayloadKey.CLIENT_COUNT]),
        split_hash=hash_jsonable(partition_payload),
        model_hash=hash_file(checkpoint),
        training_hash=hash_file(metrics_path.parent / ArtifactFile.RESOLVED_CONFIG),
        preprocessing_hash=hash_file(partition_path),
        train_count=train_count,
        calibration_count=calibration_count,
        test_count=test_count,
        eligible_count=int(metrics[PayloadKey.ELIGIBLE_COUNT]),
        pending_count=int(metrics[PayloadKey.PENDING_COUNT]),
        incomplete_ids=incomplete_ids,
        eligible_client_ids=eligible_client_ids,
        pending_client_ids=pending_client_ids,
        convergence_round=conv.convergence_round,
        convergence_value=conv.convergence_criterion_value,
        convergence_status=conv.convergence_status,
        curve_path=conv.curve_path,
        invariant_key=InvariantKey(stage=stage, seed=seed),
    )


def load_run_context(
    metrics_path: Path, base_dir: Path, acc: AuditAccumulator, data_root: Path | None
) -> RunContext | None:
    """Load and validate a metrics file, returning a RunContext or None on failure."""
    run_id_obj = parse_metric_path(base_dir, metrics_path)
    metrics = json.loads(metrics_path.read_text())

    if schema_failures := validate_metrics_payload(metrics, module="audit.results"):
        for failure in schema_failures:
            acc.warnings.append(
                WarningRecord(
                    severity=AuditSeverity.FAIL,
                    code=WarningCode.SCHEMA_VERSION_MISMATCH,
                    message=f"{metrics_path}: {failure}",
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
    """Load per-client score arrays from disk and reconstruct threshold results."""
    cal_errors, test_benign_scores, test_attack_scores, threshold_result = (
        {},
        {},
        {},
        None,
    )
    try:
        cal_errors = {
            p.stem: read_scores(p)
            for p in score_stage_files(ctx.score_root, ScoringStage.CAL)
        }
        test_benign_scores = {
            p.stem: read_scores(p)
            for p in score_stage_files(ctx.score_root, ScoringStage.TEST_BENIGN)
        }
        test_attack_scores = {
            p.stem: read_scores(p)
            for p in score_stage_files(ctx.score_root, ScoringStage.TEST_ATTACK)
        }
        threshold_result = derive_threshold(
            _DeriveInput(
                policy=ctx.policy,
                client_errors=cal_errors,
                n_min=cfg.threshold.n_min,
                q=cfg.threshold.q,
                tau_global=float(ctx.metrics[MetricName.TAU_GLOBAL]),
                threshold_cfg=cfg.threshold,
                seed=ctx.seed,
            )
        )
    except Exception as exc:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.FAIL,
                code=WarningCode.THRESHOLD_RECONSTRUCTION_FAILED,
                message=f"Could not reconstruct thresholds for {ctx.run_id}: {exc}",
            )
        )
    return ScoreArrays(
        cal_errors, test_benign_scores, test_attack_scores, threshold_result
    )


def extract_cluster_fingerprint(
    fp: Sequence[float],
) -> tuple[float | None, float | None, float | None, float | None]:
    """Unpack a 4-element fingerprint sequence into individual components."""
    n = len(fp)
    return (
        float(fp[0]) if n > 0 else None,
        float(fp[1]) if n > 1 else None,
        float(fp[2]) if n > 2 else None,
        float(fp[3]) if n > 3 else None,
    )


def cluster_silhouette_scores_by_client(scores: Any) -> dict[str, float]:
    """Normalize silhouette scores from dict or object form into a client-id-keyed dict."""
    if hasattr(scores, "items"):
        return {str(k): float(v) for k, v in scores.items()}
    return {s.client_id: float(s.score) for s in scores}


def compute_denominator_status(
    has_confusion: bool, eval_incomplete: bool, fpr_ok: bool, tpr_ok: bool
) -> tuple[DenominatorStatus, DenominatorStatus, DenominatorStatus]:
    """Determine FPR, TPR, and macro-F1 denominator statuses from confusion and eligibility flags."""
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


def extract_client_row_data(
    row: dict[str, Any], incomplete: frozenset[str]
) -> tuple[str, int, int, int, int, int, int, bool, bool]:
    """Extract client metrics and confusion counts from a single row."""
    cm = row.get(PayloadKey.CONFUSION_MATRIX, {})
    tp, fp, tn, fn = (int(cm.get(k, 0)) for k in tuple(ConfusionKey))
    client_id = str(row[PayloadKey.CLIENT_ID])
    n_benign, n_attack = int(row[PayloadKey.N_BENIGN]), int(row[PayloadKey.N_ATTACK])
    return (
        client_id,
        n_benign,
        n_attack,
        tp,
        fp,
        tn,
        fn,
        bool(cm),
        (client_id in incomplete or n_attack == 0),
    )


def collect_eligible_metric_pairs(
    normalized_clients: list[dict[str, Any]],
    eligible_ids: frozenset[str],
    incomplete: frozenset[str],
) -> tuple[
    list[tuple[str, float]],
    list[tuple[str, float]],
    list[tuple[str, float]],
    list[tuple[str, float]],
]:
    """Collect (client_id, value) pairs for FPR, TPR, macro-F1, and balanced accuracy."""
    eligible_rows = [
        r for r in normalized_clients if r[PayloadKey.CLIENT_ID] in eligible_ids
    ]
    fprs = [
        (str(r[PayloadKey.CLIENT_ID]), float(r[MetricName.FPR]))
        for r in eligible_rows
        if MetricName.FPR in r
    ]
    tprs = [
        (str(r[PayloadKey.CLIENT_ID]), float(r[MetricName.TPR]))
        for r in eligible_rows
        if MetricName.TPR in r and str(r[PayloadKey.CLIENT_ID]) not in incomplete
    ]
    f1s = [
        (str(r[PayloadKey.CLIENT_ID]), float(r[MetricName.MACRO_F1]))
        for r in eligible_rows
        if MetricName.MACRO_F1 in r
    ]
    bas = [
        (str(r[PayloadKey.CLIENT_ID]), float(r[MetricName.BALANCED_ACCURACY]))
        for r in eligible_rows
    ]
    return fprs, tprs, f1s, bas


@dataclass(frozen=True, slots=True)
class WorstClientSet:
    """Identities and values of the worst-scoring eligible client per metric."""

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


def _append_cluster_records(
    ctx: RunContext,
    cluster_meta: ClusterMetadata,
    acc: AuditAccumulator,
) -> None:
    """Append cluster assignment records for all cluster members."""
    for cluster_id, info in cluster_meta.cluster_info.items():
        for cid in info.members:
            fp = cast(
                Sequence[float],
                cluster_meta.fingerprints.get(cid) or (),
            )
            fp_m, fp_s, fp_sk, fp_p95 = extract_cluster_fingerprint(fp)
            acc.cluster_records.append(
                ClusterAssignmentRecord(
                    run_id=ctx.run_id,
                    seed=ctx.seed,
                    stage=ctx.stage,
                    client_id=cid,
                    cluster_id=cluster_id,
                    threshold_value=float(info.tau_cluster),
                    fingerprint_mean=fp_m,
                    fingerprint_std=fp_s,
                    fingerprint_skew=fp_sk,
                    fingerprint_p95=fp_p95,
                    k_selected=cluster_meta.k,
                    silhouette=cluster_meta.silhouette,
                    silhouette_scores=cluster_silhouette_scores_by_client(
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
    """Process threshold results: client thresholds, cluster assignments, global check."""
    threshold_state = ThresholdState.empty(ctx.policy)
    if ctx.policy not in CONTROLLED_POLICIES or not arrays.threshold_result:
        return threshold_state

    client_thresholds: dict[str, float] = {}
    local_taus = {
        cid: float(np.percentile(errors, cfg.threshold.q))
        for cid, errors in arrays.cal_errors.items()
        if errors.size >= cfg.threshold.n_min
    }

    for ct in sorted(
        arrays.threshold_result.client_thresholds, key=lambda i: i.client_id
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
                threshold_source=ThresholdSource.TAU_GLOBAL_FALLBACK
                if ct.calibration_pending
                else POLICY_THRESHOLD_SOURCE[ctx.policy],
                calibration_pending=ct.calibration_pending,
                tau_global=float(arrays.threshold_result.tau_global),
                threshold_aggregation_method=lookup_threshold_agg(ctx.policy),
                local_tau_i=local_taus.get(ct.client_id),
            )
        )

    if (
        ctx.policy == ThresholdPolicy.CLUSTER_THRESHOLD
        and arrays.threshold_result.metadata.cluster
    ):
        _append_cluster_records(ctx, arrays.threshold_result.metadata.cluster, acc)

    if ctx.policy == ThresholdPolicy.GLOBAL_THRESHOLD:
        pooled = float(
            np.percentile(
                np.concatenate(list(arrays.cal_errors.values())),
                cfg.threshold.q,
            )
        )
        if not math.isclose(float(arrays.threshold_result.tau_global), pooled):
            acc.warnings.append(
                WarningRecord(
                    severity=AuditSeverity.INFO,
                    code=WarningCode.GLOBAL_NOT_POOLED_PERCENTILE,
                    message=f"{ctx.run_id} tau_global is arithmetic mean.",
                )
            )

    return ThresholdState(
        client_thresholds,
        lookup_threshold_agg(ctx.policy),
        arrays.test_benign_scores,
        arrays.test_attack_scores,
        arrays.cal_errors,
    )


def _process_single_client_metrics(
    ctx: RunContext,
    row: dict[str, Any],
    threshold_state: ThresholdState,
    coverage_ratio: str,
    acc: AuditAccumulator,
) -> None:
    """Record all metric records for a single client row."""
    cid, n_benign, n_attack, tp, fp, tn, fn, has_conf, eval_inc = (
        extract_client_row_data(row, ctx.incomplete_ids)
    )

    if not has_conf and ctx.run_id not in acc.missing_confusion_warned:
        acc.missing_confusion_warned.add(ctx.run_id)
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.MISSING_CONFUSION_MATRIX,
                message=f"Missing confusion matrices for {ctx.run_id}.",
                exact_command=RemediationCommand.SWEEP_RESUME,
            )
        )

    fpr_ok = has_conf and (fp + tn) == n_benign and n_benign > 0
    tpr_ok = has_conf and (tp + fn) == n_attack and n_attack > 0
    fpr_s, tpr_s, f1_s = compute_denominator_status(has_conf, eval_inc, fpr_ok, tpr_ok)

    acc.denominator_records.append(
        MetricDenominatorAuditRecord(
            run_id=ctx.run_id,
            seed=ctx.seed,
            stage=ctx.stage,
            policy=ctx.policy,
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
                ctx.run_id,
                ctx.seed,
                ctx.stage,
                ctx.policy,
                cid,
                tp,
                fp,
                tn,
                fn,
                n_benign,
                n_attack,
                float_or_none(row.get(MetricName.FPR)),
                float_or_none(row.get(MetricName.TPR)),
                float_or_none(row.get(MetricName.BALANCED_ACCURACY)),
                float_or_none(row.get(MetricName.MACRO_F1)),
            ),
        )

    auroc, pr_auc = binary_auc_fields(
        row,
        threshold_state.test_benign_scores.get(cid),
        threshold_state.test_attack_scores.get(cid),
    )
    acc.client_records.append(
        ClientMetricRecord(
            run_id=ctx.run_id,
            seed=ctx.seed,
            stage=ctx.stage,
            policy=ctx.policy,
            client_id=cid,
            fpr=float(row[MetricName.FPR]),
            tpr=float(row[MetricName.TPR]),
            balanced_accuracy=float(row[MetricName.BALANCED_ACCURACY]),
            macro_f1=float(row[MetricName.MACRO_F1]),
            auroc=auroc,
            pr_auc=pr_auc,
            n_benign=n_benign,
            n_attack=n_attack,
            tp=tp,
            fp=fp,
            tn=tn,
            fn=fn,
            eligible=cid in ctx.eligible_client_ids,
            calibration_pending=cid in ctx.pending_client_ids,
            evaluation_incomplete=eval_inc,
            coverage_ratio=coverage_ratio,
        )
    )
    acc.attack_records.append(
        PerAttackMetricRecord(
            run_id=ctx.run_id,
            seed=ctx.seed,
            stage=ctx.stage,
            policy=ctx.policy,
            client_id=cid,
            attack_label=AttackLabel.BINARY_ATTACK,
            status=DenominatorStatus.EXCLUDED_EVALUATION_INCOMPLETE
            if eval_inc
            else DenominatorStatus.PASS,
            tpr=None if eval_inc else float(row[MetricName.TPR]),
            detected_count=None if eval_inc else tp,
            denominator=None if eval_inc else n_attack,
        )
    )


def _process_client_metrics_loop(
    ctx: RunContext,
    threshold_state: ThresholdState,
    coverage_ratio: str,
    acc: AuditAccumulator,
) -> None:
    """Process per-client metrics: denominator, recomputation, client, attack records."""
    for row in ctx.normalized_clients:
        _process_single_client_metrics(
            ctx,
            row,
            threshold_state,
            coverage_ratio,
            acc,
        )


def _build_cell_panel(
    ctx: RunContext,
    cv_fpr_val: float,
    fpr_v: float | None,
    tpr_v: float | None,
    f1_v: float | None,
    ba_v: float | None,
    f1s: list[tuple[str, float]],
    f1_arr: np.ndarray,
    auroc_arr: np.ndarray,
    pr_arr: np.ndarray,
    eligible_fpr_vals: np.ndarray,
    coverage_ratio: str,
) -> CellPanel:
    """Build a CellPanel from precomputed aggregate values."""
    f1_p10_arr = finite_array([v for _, v in f1s])
    cv_tpr_raw = ctx.metrics.get(MetricName.CV_TPR)

    return CellPanel(
        cv_fpr_val if math.isfinite(cv_fpr_val) else None,
        float(cv_tpr_raw) if cv_tpr_raw and math.isfinite(float(cv_tpr_raw)) else None,
        float(f1_arr.mean()) if f1_arr.size else None,
        float(np.percentile(f1_p10_arr, 10.0)) if f1_p10_arr.size else None,
        float(auroc_arr.mean()) if auroc_arr.size else None,
        float(pr_arr.mean()) if pr_arr.size else None,
        float(eligible_fpr_vals.mean()) if eligible_fpr_vals.size else None,
        float(np.std(eligible_fpr_vals, ddof=1))
        if eligible_fpr_vals.size > 1
        else None,
        iqr(eligible_fpr_vals) if eligible_fpr_vals.size else None,
        fpr_v,
        tpr_v,
        f1_v,
        ba_v,
        ctx.convergence_round,
        float(ctx.metrics[MetricName.TAU_GLOBAL])
        if ctx.metrics.get(MetricName.TAU_GLOBAL) is not None
        else None,
        coverage_ratio,
    )


def _record_aggregates_and_cell_panel(
    ctx: RunContext,
    coverage_ratio: str,
    acc: AuditAccumulator,
) -> None:
    """Record FPR companion, worst client records, and cell panel."""
    fprs, tprs, f1s, bas = collect_eligible_metric_pairs(
        ctx.normalized_clients, ctx.eligible_client_ids, ctx.incomplete_ids
    )
    eligible_fpr_vals = finite_array([v for _, v in fprs])
    cv_fpr_val = float(ctx.metrics[MetricName.CV_FPR])

    if math.isfinite(cv_fpr_val) and (
        ctx.metrics.get(MetricName.MEAN_FPR) is None
        or ctx.metrics.get(MetricName.STD_FPR) is None
    ):
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.FAIL,
                code=WarningCode.NAKED_CV_FPR,
                message=f"{ctx.run_id} naked CV FPR.",
                exact_command=RemediationCommand.SWEEP_RESUME,
            )
        )

    fpr_id, fpr_v = argworst(fprs, WORST_CLIENT_DIRECTIONS[MetricName.FPR])
    tpr_id, tpr_v = argworst(tprs, WORST_CLIENT_DIRECTIONS[MetricName.TPR])
    f1_id, f1_v = argworst(f1s, WORST_CLIENT_DIRECTIONS[MetricName.MACRO_F1])
    ba_id, ba_v = argworst(bas, WORST_CLIENT_DIRECTIONS[MetricName.BALANCED_ACCURACY])

    acc.companion_records.append(
        FPRCompanionRecord(
            run_id=ctx.run_id,
            seed=ctx.seed,
            stage=ctx.stage,
            policy=ctx.policy,
            cv_fpr=cv_fpr_val if math.isfinite(cv_fpr_val) else None,
            mean_fpr=float(eligible_fpr_vals.mean())
            if eligible_fpr_vals.size
            else None,
            std_fpr=float(np.std(eligible_fpr_vals, ddof=1))
            if eligible_fpr_vals.size > 1
            else None,
            iqr_fpr=iqr(eligible_fpr_vals) if eligible_fpr_vals.size else None,
            worst_client_fpr=fpr_v,
            eligible_count=len(ctx.eligible_client_ids),
            client_count=ctx.client_count,
            coverage_ratio=coverage_ratio,
        )
    )

    for m_name, (w_cid, w_val, p_size) in {
        MetricName.FPR: (fpr_id, fpr_v, len(fprs)),
        MetricName.TPR: (tpr_id, tpr_v, len(tprs)),
        MetricName.MACRO_F1: (f1_id, f1_v, len(f1s)),
        MetricName.BALANCED_ACCURACY: (ba_id, ba_v, len(bas)),
    }.items():
        acc.worst_client_records.append(
            WorstClientRecord(
                run_id=ctx.run_id,
                seed=ctx.seed,
                stage=ctx.stage,
                policy=ctx.policy,
                metric=m_name,
                direction=WORST_CLIENT_DIRECTIONS[m_name],
                worst_client_id=w_cid,
                worst_value=w_val,
                eligible_pool_size=p_size,
            )
        )

    f1_arr = finite_array(
        [float(r[MetricName.MACRO_F1]) for r in ctx.normalized_clients]
    )
    auroc_arr = finite_array(
        [
            float(r[MetricName.AUROC])
            for r in ctx.normalized_clients
            if r.get(MetricName.AUROC) is not None
        ]
    )
    pr_arr = finite_array(
        [
            float(r[MetricName.PR_AUC])
            for r in ctx.normalized_clients
            if r.get(MetricName.PR_AUC) is not None
        ]
    )

    acc.cell_panel[(ctx.stage, ctx.seed, ctx.policy)] = _build_cell_panel(
        ctx,
        cv_fpr_val,
        fpr_v,
        tpr_v,
        f1_v,
        ba_v,
        f1s,
        f1_arr,
        auroc_arr,
        pr_arr,
        eligible_fpr_vals,
        coverage_ratio,
    )


def _record_manifest_and_partition(
    ctx: RunContext,
    threshold_state: ThresholdState,
    hashes: AuditHashes,
    acc: AuditAccumulator,
) -> None:
    """Record run manifest, invariant hashes, partition audit, and convergence."""
    acc.manifest_records.append(
        RunManifestRecord(
            run_id=ctx.run_id,
            timestamp=hashes.timestamp,
            git_commit_hash=hashes.git_commit,
            seed=ctx.seed,
            dataset=dataset_for_stage(ctx.stage),
            stage=ctx.stage,
            policy=ctx.policy,
            client_count=ctx.client_count,
            split_hash=ctx.split_hash,
            model_hash=ctx.model_hash,
            encoder_hash=ctx.model_hash,
            training_config_hash=ctx.training_hash,
            preprocessing_config_hash=ctx.preprocessing_hash,
            scoring_code_hash=hashes.scoring_hash,
            threshold_code_hash=hashes.threshold_hash,
            metrics_code_hash=hashes.metrics_hash,
            artifact_schema_version=AuditSchemaVersion.V1_0,
            convergence_round=ctx.convergence_round,
            convergence_criterion_value=ctx.convergence_value,
            convergence_status=ctx.convergence_status,
            eligible_clients=ctx.eligible_count,
            calibration_pending_clients=ctx.pending_count,
            evaluation_incomplete_clients=len(ctx.incomplete_ids),
            feature_count=ctx.feature_count,
            feature_list_hash=SCORING_MANIFEST_NOT_PROVIDED
            if ctx.feature_count is None
            else hash_jsonable({"feature_count": ctx.feature_count}),
            threshold_aggregation_method=threshold_state.threshold_aggregation_method,
            normalization_scope=NormalizationScope(
                ctx.metrics[PayloadKey.NORMALIZATION_SCOPE]
            )
            if ctx.metrics.get(PayloadKey.NORMALIZATION_SCOPE)
            else None,
            train_count=ctx.train_count,
            calibration_count=ctx.calibration_count,
            test_count=ctx.test_count,
        )
    )
    acc.invariant_inputs[ctx.invariant_key][ctx.policy] = InvariantHashes(
        ctx.split_hash, ctx.model_hash, ctx.model_hash, hashes.scoring_hash, hashes.metrics_hash
    )

    if ctx.partition_path.exists():
        acc.partition_audits[f"{ctx.stage.value}:{ctx.seed}"] = DatasetPartitionAudit(
            dataset=dataset_for_stage(ctx.stage),
            stage=ctx.stage,
            seed=ctx.seed,
            manifest_path=str(ctx.partition_path),
            manifest_hash=hash_file(ctx.partition_path),
            split_hash=ctx.split_hash,
            feature_count=ctx.feature_count,
            client_count=ctx.metadata.get("n_clients", ctx.metadata.get("n_devices")),
            nbaiot_per_device=build_nbaiot_per_device(
                ctx.partition_path.parent,
                list(ctx.partition_payload.get("file_hashes", {}).keys()),
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
                message=f"Missing partition for {ctx.run_id}.",
                exact_command=RemediationCommand.SWEEP_RESUME,
            )
        )

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


def _add_reconstruction_record(
    ctx: RunContext,
    sp: Path,
    arr: np.ndarray,
    stage: ScoringStage,
    acc: AuditAccumulator,
) -> None:
    """Add a single reconstruction error summary record."""
    acc.recon_records.append(
        ReconstructionErrorSummaryRecord(
            run_id=ctx.run_id,
            policy=ctx.policy,
            seed=ctx.seed,
            stage=ctx.stage,
            client_id=sp.stem,
            stage_split=stage,
            count=int(arr.size),
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
    """Record score hashes and reconstruction error summaries."""
    if not (ctx.policy in CONTROLLED_POLICIES and ctx.score_root.exists()):
        return

    cell_hashes: dict[tuple[ScoringStage, str], str] = {}
    for stage in ScoringStage:
        for sp in score_stage_files(ctx.score_root, stage):
            arr = read_scores(sp)
            cell_hashes[(stage, sp.stem)] = array_hash(arr)
            if ctx.policy == ThresholdPolicy.GLOBAL_THRESHOLD:
                _add_reconstruction_record(ctx, sp, arr, stage, acc)
    acc.score_hashes_by_cell[ctx.invariant_key][ctx.policy] = cell_hashes


def process_run(
    metrics_path: Path,
    base_dir: Path,
    acc: AuditAccumulator,
    lock: threading.Lock,
    hashes: AuditHashes,
    cfg: DatpConfig,
    data_root: Path | None,
) -> None:
    """Load and process a single metrics file, appending records to the accumulator."""
    ctx = load_run_context(metrics_path, base_dir, acc, data_root)
    if ctx is None:
        return

    arrays = load_score_arrays(acc, ctx, cfg)

    with lock:
        threshold_state = _record_thresholds_and_clusters(ctx, arrays, cfg, acc)

    coverage_ratio = (
        f"{ctx.eligible_count}/{ctx.client_count}"
        if ctx.client_count
        else CoverageFallback.DEFAULT
    )

    with lock:
        _process_client_metrics_loop(ctx, threshold_state, coverage_ratio, acc)
        _record_aggregates_and_cell_panel(ctx, coverage_ratio, acc)
        _record_manifest_and_partition(ctx, threshold_state, hashes, acc)
        _record_score_hashes(ctx, acc)


_PANEL_FIELD_NAMES: tuple[str, ...] = (
    "cv_fpr",
    "cv_tpr",
    "macro_f1_mean",
    "macro_f1_p10",
    "auroc_mean",
    "pr_auc_mean",
    "mean_fpr",
    "std_fpr",
    "iqr_fpr",
    "worst_client_fpr",
    "worst_client_tpr",
    "worst_client_macro_f1",
    "worst_client_balanced_accuracy",
    "convergence_round",
    "tau_global",
)

_DELTA_FIELD_MAP: tuple[tuple[str, str], ...] = (
    ("cv_fpr", "cv_fpr"),
    ("cv_tpr", "cv_tpr"),
    ("macro_f1", "macro_f1_mean"),
    ("pr_auc", "pr_auc_mean"),
    ("auroc", "auroc_mean"),
)


def _panel_field_dict(
    panels: list[tuple[str, CellPanel]],
) -> dict[str, object]:
    """Build {prefix_field: value} entries for all panels and panel field names."""
    return {
        f"{prefix}_{field}": getattr(panel, field)
        for prefix, panel in panels
        for field in _PANEL_FIELD_NAMES
    }


def _delta_field_dict(
    g: CellPanel,
    comparisons: list[tuple[str, CellPanel]],
) -> dict[str, object]:
    """Build {delta_k_global_minus_p: diff} entries for each delta metric and comparison panel."""
    return {
        f"delta_{k}_global_minus_{p}": safe_diff(getattr(g, v), getattr(panel, v))
        for k, v in _DELTA_FIELD_MAP
        for p, panel in comparisons
    }


def build_seed_deltas(
    cell_panel: dict[tuple[ExperimentStage, int, ThresholdPolicy], CellPanel],
    warnings: list[WarningRecord],
) -> list[SeedDeltaRecord]:
    """Build seed-delta records from the cell panel, computing global-local and global-cluster deltas."""
    out = []
    for stage, seed in sorted({(s, sd) for s, sd, _ in cell_panel}):
        g = cell_panel.get(
            (stage, seed, ThresholdPolicy.GLOBAL_THRESHOLD), CellPanel.empty()
        )
        loc = cell_panel.get(
            (stage, seed, ThresholdPolicy.LOCAL_THRESHOLD), CellPanel.empty()
        )
        c = cell_panel.get(
            (stage, seed, ThresholdPolicy.CLUSTER_THRESHOLD), CellPanel.empty()
        )

        check_local_threshold_utility_tradeoff((stage, seed), g, loc, warnings)

        panels = [("global", g), ("local", loc), ("cluster", c)]
        comparisons = [("local", loc), ("cluster", c)]
        coverage = str(
            g.coverage_ratio
            or loc.coverage_ratio
            or c.coverage_ratio
            or CoverageFallback.DEFAULT
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


def _is_worsened(global_val: float | None, local_val: float | None) -> bool:
    """Return True if local_val is strictly lower than global_val (i.e. LOCAL worsens the metric)."""
    return global_val is not None and local_val is not None and local_val < global_val


def check_local_threshold_utility_tradeoff(
    cell_key: tuple[ExperimentStage, int],
    global_panel: CellPanel,
    local_panel: CellPanel,
    warnings: list[WarningRecord],
) -> None:
    """Warn if LOCAL_THRESHOLD worsens macro-F1, AUROC, or PR-AUC relative to GLOBAL_THRESHOLD."""
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
    """Emit structural audit warnings (missing runs, blocked policies, convergence)."""
    if any(
        row.convergence_status == ConvergenceStatus.BLOCKED_PENDING_RUN
        for row in acc.convergence_records
    ):
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.MISSING_CONVERGENCE_CURVES,
                message="Missing convergence curves.",
                exact_command=RemediationCommand.SWEEP_RESUME,
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
                exact_command=RemediationCommand.SWEEP_RESUME,
            )
        )
    if not acc.cluster_records:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.CLUSTER_DIAGNOSTICS_INCOMPLETE,
                message="No cluster diagnostics.",
                exact_command=RemediationCommand.SWEEP_RESUME,
            )
        )
    acc.warnings.append(
        WarningRecord(
            severity=AuditSeverity.BLOCKED_PENDING_RUN,
            code=WarningCode.FIXED_OPERATING_POINT_METRICS_PENDING,
            message="FPR/TPR fixed point pending.",
            exact_command=RemediationCommand.AUDIT_RESULTS,
        )
    )


def emit_worst_client_stability_warnings(
    worst_client_records: list[WorstClientRecord], warnings: list[WarningRecord]
) -> None:
    """Warn if the worst client on a metric is stable or rotates across seeds."""
    grouped = defaultdict(list)
    for r in worst_client_records:
        grouped[(r.stage, r.policy, r.metric)].append((r.seed, r.worst_client_id))
    for (stage, policy, metric), entries in grouped.items():
        if len(entries) >= ValidationThreshold.WORST_CLIENT_STABLE_MIN_SEEDS.value:
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
    cell_panel: dict[tuple[ExperimentStage, int, ThresholdPolicy], CellPanel],
    warnings: list[WarningRecord],
) -> None:
    """Warn if CV(TPR) is near zero across policies, suggesting flat TPR distributions."""
    by_cell = defaultdict(list)
    for (stage, seed, _), panel in cell_panel.items():
        if panel.cv_tpr is not None:
            by_cell[(stage, seed)].append(float(panel.cv_tpr))
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
                abs(v - tpr_vals[0]) < ValidationThreshold.FLAT_CV_TPR_EPSILON.value
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
class AuditOutputPath:
    """Pairing of an audit output name with its filesystem path."""

    name: AuditOutputName
    path: Path


@dataclass(frozen=True, slots=True)
class AuditOutputPaths:
    """Immutable collection of audit output paths with lookup support."""

    paths: tuple[AuditOutputPath, ...]

    def __contains__(self, name: object) -> bool:
        """Check whether an audit output name is present."""
        return any(i.name == name or i.name.value == name for i in self.paths)

    def items(self) -> tuple[tuple[str, Path], ...]:
        """Return (name_value, path) pairs for every contained output path."""
        return tuple((i.name.value, i.path) for i in self.paths)

    def path_for(self, name: AuditOutputName) -> Path:
        """Look up the filesystem path for a given audit output name."""
        for i in self.paths:
            if i.name == name:
                return i.path
        raise KeyError(name)


def _compute_cluster_stability_records(
    acc: AuditAccumulator,
) -> list[Any]:
    """Build cluster stability records from accumulated cluster assignment records."""
    keyed_assigns = [
        (
            r.stage,
            r.seed,
            r.client_id,
            int(r.cluster_id.split("_")[-1])
            if "_" in r.cluster_id
            else int(r.cluster_id)
            if r.cluster_id.isdigit()
            else hash(r.cluster_id),
        )
        for r in acc.cluster_records
    ]
    records: list[Any] = []
    for stage in sorted({r[0] for r in keyed_assigns}):
        seed_keys = sorted({r[1] for r in keyed_assigns if r[0] == stage})
        assignments = tuple(
            ClusterAssignments(
                seed,
                tuple(
                    sorted(
                        (r[2], r[3])
                        for r in keyed_assigns
                        if r[0] == stage and r[1] == seed
                    )
                ),
            )
            for seed in seed_keys
        )
        records.extend(compute_cluster_stability(assignments, stage))
    return records


def _write_audit_outputs(
    audit_dir: Path,
    acc: AuditAccumulator,
    seed_deltas: list[SeedDeltaRecord],
    cluster_stability_records: list[Any],
    invariant_results: list[Any],
) -> None:
    """Write all CSV, JSON, and text audit output files."""
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


_AUDIT_OUTPUT_NAME_ARTIFACT_PAIRS: tuple[tuple[str, str], ...] = (
    ("POLICY_INVARIANTS", AuditArtifact.POLICY_INVARIANTS),
    ("RUN_MANIFEST", AuditArtifact.RUN_MANIFEST),
    ("SEED_DELTAS", AuditArtifact.SEED_DELTAS),
    ("PER_CLIENT_METRICS", AuditArtifact.PER_CLIENT_METRICS),
    ("PER_ATTACK_METRICS", AuditArtifact.PER_ATTACK_METRICS),
    ("THRESHOLD_VALUES", AuditArtifact.THRESHOLD_VALUES),
    ("RECONSTRUCTION_ERROR_SUMMARY", AuditArtifact.RECONSTRUCTION_ERROR_SUMMARY),
    ("CLUSTER_ASSIGNMENTS", AuditArtifact.CLUSTER_ASSIGNMENTS),
    ("DATASET_PARTITION_AUDIT", AuditArtifact.DATASET_PARTITION_AUDIT),
    ("CONVERGENCE_AUDIT", AuditArtifact.CONVERGENCE_AUDIT),
    ("METRIC_DENOMINATOR_AUDIT", AuditArtifact.METRIC_DENOMINATOR_AUDIT),
    ("METRIC_RECOMPUTATION_AUDIT", AuditArtifact.METRIC_RECOMPUTATION_AUDIT),
    ("FPR_COMPANION_METRICS", AuditArtifact.FPR_COMPANION_METRICS),
    ("WORST_CLIENT_TRACKING", AuditArtifact.WORST_CLIENT_TRACKING),
    ("CLUSTER_STABILITY", AuditArtifact.CLUSTER_STABILITY),
    ("WARNINGS", AuditArtifact.WARNINGS),
    ("AUDIT_SUMMARY", AuditArtifact.AUDIT_SUMMARY),
)


def run_results_audit(
    base_dir: Path, audit_dir: Path, cfg: DatpConfig, data_root: Path | None = None
) -> AuditOutputPaths:
    """Run the full results audit pipeline and return all generated output paths."""
    base_dir, audit_dir = Path(base_dir), Path(audit_dir)
    audit_dir.mkdir(parents=True, exist_ok=True)

    acc = AuditAccumulator()
    metric_paths = completed_metric_paths(base_dir)
    if not metric_paths:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.NO_COMPLETED_RESULTS,
                message="No completed metrics.json found.",
                exact_command=RemediationCommand.SWEEP_RESUME,
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
        for path in metric_paths:
            executor.submit(process_run, path, base_dir, acc, lock, hashes, cfg, data_root)

    cluster_stability_records = _compute_cluster_stability_records(acc)
    invariant_results = build_invariant_results(
        acc.invariant_inputs, acc.score_hashes_by_cell
    )
    seed_deltas = build_seed_deltas(acc.cell_panel, acc.warnings)

    emit_structural_warnings(acc, seed_deltas)
    emit_worst_client_stability_warnings(acc.worst_client_records, acc.warnings)
    emit_flat_cv_tpr_warnings(acc.cell_panel, acc.warnings)

    _write_audit_outputs(audit_dir, acc, seed_deltas, cluster_stability_records, invariant_results)

    return AuditOutputPaths(
        tuple(
            AuditOutputPath(AuditOutputName[k], audit_dir / v)
            for k, v in _AUDIT_OUTPUT_NAME_ARTIFACT_PAIRS
        )
    )
