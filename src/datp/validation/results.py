from __future__ import annotations

import dataclasses
import json
import math
from collections import defaultdict
from pathlib import Path
from collections.abc import Sequence
from typing import Any

import numpy as np

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import PathToken, ArtifactFile
from datp.scoring.schema import SCORING_MANIFEST_NOT_PROVIDED
from datp.validation.constants import (
    AUDIT_SCHEMA_VERSION,
    AUDIT_SUMMARY_MD,
    B4_CLUSTER_STABILITY_CSV,
    BASELINE_INVARIANTS_JSON,
    BINARY_ATTACK_LABEL,
    BLOCKED_RESUME_COMMAND,
    BLOCKED_RESUME_REGIME_A_COMMAND,
    CICIOT_HOMOGENEITY_AUDIT_CSV,
    CLUSTER_ASSIGNMENTS_CSV,
    CONVERGENCE_AUDIT_CSV,
    DATASET_PARTITION_AUDIT_JSON,
    DEFAULT_COVERAGE_RATIO,
    DIAGNOSTIC_REGIME_A_COMMAND,
    FINGERPRINT_METHOD_BENIGN_RECON_ERROR_HISTOGRAM,
    FPR_COMPANION_METRICS_CSV,
    METRIC_DENOMINATOR_AUDIT_CSV,
    METRIC_RECOMPUTATION_AUDIT_CSV,
    PER_ATTACK_METRICS_CSV,
    PER_CLIENT_METRICS_CSV,
    RECONSTRUCTION_ERROR_SUMMARY_CSV,
    REGIME_C_ALPHA_AUDIT_CSV,
    REGIME_C_SEVERITY_TREND_CSV,
    RUN_MANIFEST_CSV,
    SEED_DELTAS_CSV,
    THRESHOLD_VALUES_CSV,
    WARNINGS_MD,
    WORST_CLIENT_TRACKING_CSV,
    _AUDIT_RESULTS_COMMAND,
)
from datp.validation.convergence import convergence_payload as _convergence_payload
from datp.validation.datasets import (
    build_ciciot_protocol,
    build_nbaiot_per_device,
    build_regime_c_alpha_audit,
    chronological_flags_for,
    compute_b4_cluster_stability,
    compute_ciciot_homogeneity,
    compute_regime_c_severity_trend,
    confound_summary_for,
)
from datp.validation.discovery import completed_metric_paths as _completed_metric_paths
from datp.validation.discovery import parse_metric_path as _parse_metric_path
from datp.statistics.constants import EXTREME_PERCENTILE
from datp.core.enums import CONTROLLED_BASELINES, ConvergenceStatus
from datp.validation.enums import (
    AuditStatus,
    AuditSeverity,
    WarningCode,
    WORST_CLIENT_DIRECTIONS,
    DenominatorStatus,
    WorstDirection,
)
from datp.validation.invariants import (
    InvariantHashes,
    InvariantKey,
    build_invariant_results,
)
from datp.validation.schemas import (
    B4ClusterStabilityRecord,
    BaselineInvariantResult,
    CICIoTHomogeneityRecord,
    ClientMetricRecord,
    ClusterAssignmentRecord,
    ConvergenceAuditRecord,
    DatasetPartitionAudit,
    FPRCompanionRecord,
    MetricDenominatorAuditRecord,
    MetricRecomputationRecord,
    NBaIoTDeviceCounts,
    PerAttackMetricRecord,
    ReconstructionErrorSummaryRecord,
    RegimeCAlphaAuditRecord,
    RegimeCSeverityTrendRecord,
    RunManifestRecord,
    SeedDeltaRecord,
    ThresholdRecord,
    WarningRecord,
    WorstClientRecord,
)
from datp.validation._recomputation import (
    RecomputationParams,
    append_recomputation_records,
)
from datp.validation._warnings import (
    check_b2_utility_tradeoff as _check_b2_utility_tradeoff,
    emit_ciciot_homogeneity_warnings as _emit_ciciot_homogeneity_warnings,
    emit_flat_cv_tpr_warnings as _emit_flat_cv_tpr_warnings,
    emit_worst_client_stability_warnings as _emit_worst_client_stability_warnings,
)
from datp.artifacts.io import write_csv as _write_csv
from datp.artifacts.io import write_json_atomic as _write_json
from datp.thresholding.thresholds import derive_threshold
from datp.config.models import DatpConfig
from datp.core.types import ThresholdResult
from datp.core.enums import (
    BASELINE_THRESHOLD_SOURCE,
    THRESHOLD_AGGREGATION_BY_BASELINE,
    B0NormalizationMode,
    Baseline,
    NormalizationScope,
    Regime,
    ScoringStage,
    ThresholdAggregationMethod,
    ThresholdSource,
)
from datp.core.identity import (
    TrainingCellId,
    alpha_label,
)
from datp.core.provenance import (
    array_hash,
    git_commit as current_git_commit,
    hash_file,
    hash_jsonable,
    source_hash,
    utc_timestamp,
)
from datp.data.catalog import DatasetID
from datp.data.paths import prepared_root_for_regime
from datp.data.regimes.catalog import dataset_for_regime
from datp.core.enums import PayloadKey, ConfusionKey, MetricName
from datp.evaluation.artifact_validation import validate_metrics_payload
from datp.evaluation.metrics import compute_per_attack_tpr
from datp.evaluation.ranking import compute_binary_ranking_metrics
from datp.scoring.loading import read_score_column as _read_scores


def _load_client_attack_labels(
    regime: Regime, client_id: str, prepared_data_root: Path
) -> "np.ndarray | None":
    if regime != Regime.B:
        return None
    from datp.data.datasets.ciciot2023.spec import (
        LABEL_COLUMN,
        TEST_ATTACK_LABELS_ARTIFACT,
    )  # noqa: PLC0415

    labels_path = prepared_data_root / client_id / TEST_ATTACK_LABELS_ARTIFACT
    if not labels_path.exists():
        return None
    import polars as pl  # noqa: PLC0415

    series = pl.read_parquet(labels_path)[LABEL_COLUMN]
    if series.is_empty():
        return np.empty(0, dtype=object)
    return series.to_numpy().astype(object)


@dataclasses.dataclass(frozen=True, slots=True)
class _CellPanel:
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
    def empty(cls) -> _CellPanel:
        """Explicit sentinel for a cell with no available data."""
        return cls()


def _lookup_threshold_agg(baseline: Baseline) -> ThresholdAggregationMethod:
    try:
        return THRESHOLD_AGGREGATION_BY_BASELINE[baseline]
    except KeyError:
        return ThresholdAggregationMethod.PER_CLIENT_PERCENTILE


def _lookup_dataset(regime: Regime) -> DatasetID:
    return dataset_for_regime(regime)



def _partition_manifest_path(
    regime: Regime,
    seed: int,
    alpha: float | None,
    base_dir: Path,
    data_root: Path | None = None,
) -> Path:
    _data_root = data_root if data_root is not None else base_dir
    return (
        prepared_root_for_regime(regime, base_dir=_data_root, alpha=alpha, seed=seed)
        / ArtifactFile.MANIFEST
    )


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _manifest_payload(path: Path) -> dict[str, Any]:
    return _load_json(path) if path.exists() else {}


def _split_hash(manifest_path: Path) -> str:
    payload = _manifest_payload(manifest_path)
    return hash_jsonable(payload)


def _feature_hash(feature_count: int | None) -> str:
    if feature_count is None:
        return SCORING_MANIFEST_NOT_PROVIDED
    return hash_jsonable({"feature_count": feature_count})


def _finite_mean(values: list[float]) -> float | None:
    arr = np.asarray(values, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    return float(arr.mean()) if arr.size else None


def _finite_array(values: list[float]) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    return arr[np.isfinite(arr)]


def _percentile_or_none(values: list[float], q: float) -> float | None:
    arr = _finite_array(values)
    return float(np.percentile(arr, q)) if arr.size else None


def _std_or_none(values: list[float]) -> float | None:
    arr = _finite_array(values)
    return float(np.std(arr, ddof=1)) if arr.size > 1 else None


def _iqr_or_none(values: list[float]) -> float | None:
    arr = _finite_array(values)
    if arr.size == 0:
        return None
    return float(np.percentile(arr, 75) - np.percentile(arr, 25))


def _float_or_none(raw: object) -> float | None:
    """Convert a metrics-dict value to float, returning None when absent or non-finite."""
    if raw is None:
        return None
    try:
        val = float(raw)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return None
    return val if math.isfinite(val) else None


def _argworst(
    pairs: list[tuple[str, float]],
    direction: WorstDirection,
) -> tuple[str | None, float | None]:
    finite = [(cid, float(v)) for cid, v in pairs if math.isfinite(float(v))]
    if not finite:
        return None, None
    if direction == WorstDirection.MAX_IS_WORST:
        cid, value = max(finite, key=lambda item: item[1])
    else:
        cid, value = min(finite, key=lambda item: item[1])
    return cid, float(value)


def _safe_diff(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or not math.isfinite(a) or not math.isfinite(b):
        return None
    return float(a - b)


def _build_seed_deltas(
    cell_panel: dict[tuple[Regime, int, str | None, Baseline], _CellPanel],
    warnings: list[WarningRecord],
) -> list[SeedDeltaRecord]:
    # Side effect: emits B2_UTILITY_TRADEOFF warnings.
    out: list[SeedDeltaRecord] = []
    for regime, seed, alpha_text in sorted({(r, s, a) for r, s, a, _ in cell_panel}):
        b1_key = (regime, seed, alpha_text, Baseline.B1)
        b2_key = (regime, seed, alpha_text, Baseline.B2)
        b4_key = (regime, seed, alpha_text, Baseline.B4)
        b1 = cell_panel[b1_key] if b1_key in cell_panel else _CellPanel.empty()
        b2 = cell_panel[b2_key] if b2_key in cell_panel else _CellPanel.empty()
        b4 = cell_panel[b4_key] if b4_key in cell_panel else _CellPanel.empty()
        out.append(
            SeedDeltaRecord(
                regime=regime,
                alpha=alpha_text,
                seed=seed,
                b1_cv_fpr=b1.cv_fpr,
                b2_cv_fpr=b2.cv_fpr,
                b4_cv_fpr=b4.cv_fpr,
                b1_cv_tpr=b1.cv_tpr,
                b2_cv_tpr=b2.cv_tpr,
                b4_cv_tpr=b4.cv_tpr,
                b1_macro_f1_mean=b1.macro_f1_mean,
                b2_macro_f1_mean=b2.macro_f1_mean,
                b4_macro_f1_mean=b4.macro_f1_mean,
                b1_macro_f1_p10=b1.macro_f1_p10,
                b2_macro_f1_p10=b2.macro_f1_p10,
                b4_macro_f1_p10=b4.macro_f1_p10,
                b1_auroc_mean=b1.auroc_mean,
                b2_auroc_mean=b2.auroc_mean,
                b4_auroc_mean=b4.auroc_mean,
                b1_pr_auc_mean=b1.pr_auc_mean,
                b2_pr_auc_mean=b2.pr_auc_mean,
                b4_pr_auc_mean=b4.pr_auc_mean,
                b1_mean_fpr=b1.mean_fpr,
                b2_mean_fpr=b2.mean_fpr,
                b4_mean_fpr=b4.mean_fpr,
                b1_std_fpr=b1.std_fpr,
                b2_std_fpr=b2.std_fpr,
                b4_std_fpr=b4.std_fpr,
                b1_iqr_fpr=b1.iqr_fpr,
                b2_iqr_fpr=b2.iqr_fpr,
                b4_iqr_fpr=b4.iqr_fpr,
                b1_worst_client_fpr=b1.worst_client_fpr,
                b2_worst_client_fpr=b2.worst_client_fpr,
                b4_worst_client_fpr=b4.worst_client_fpr,
                b1_worst_client_tpr=b1.worst_client_tpr,
                b2_worst_client_tpr=b2.worst_client_tpr,
                b4_worst_client_tpr=b4.worst_client_tpr,
                b1_worst_client_macro_f1=b1.worst_client_macro_f1,
                b2_worst_client_macro_f1=b2.worst_client_macro_f1,
                b4_worst_client_macro_f1=b4.worst_client_macro_f1,
                b1_worst_client_balanced_accuracy=b1.worst_client_balanced_accuracy,
                b2_worst_client_balanced_accuracy=b2.worst_client_balanced_accuracy,
                b4_worst_client_balanced_accuracy=b4.worst_client_balanced_accuracy,
                delta_cv_fpr_b1_minus_b2=_safe_diff(b1.cv_fpr, b2.cv_fpr),
                delta_cv_fpr_b1_minus_b4=_safe_diff(b1.cv_fpr, b4.cv_fpr),
                delta_cv_tpr_b1_minus_b2=_safe_diff(b1.cv_tpr, b2.cv_tpr),
                delta_cv_tpr_b1_minus_b4=_safe_diff(b1.cv_tpr, b4.cv_tpr),
                delta_macro_f1_b1_minus_b2=_safe_diff(
                    b1.macro_f1_mean, b2.macro_f1_mean
                ),
                delta_macro_f1_b1_minus_b4=_safe_diff(
                    b1.macro_f1_mean, b4.macro_f1_mean
                ),
                delta_pr_auc_b1_minus_b2=_safe_diff(b1.pr_auc_mean, b2.pr_auc_mean),
                delta_pr_auc_b1_minus_b4=_safe_diff(b1.pr_auc_mean, b4.pr_auc_mean),
                delta_auroc_b1_minus_b2=_safe_diff(b1.auroc_mean, b2.auroc_mean),
                delta_auroc_b1_minus_b4=_safe_diff(b1.auroc_mean, b4.auroc_mean),
                b1_convergence_round=b1.convergence_round,
                b2_convergence_round=b2.convergence_round,
                b4_convergence_round=b4.convergence_round,
                b1_tau_global=b1.tau_global,
                b2_tau_global=b2.tau_global,
                b4_tau_global=b4.tau_global,
                coverage_ratio=str(
                    b1.coverage_ratio or b2.coverage_ratio or b4.coverage_ratio or DEFAULT_COVERAGE_RATIO
                ),
                status=AuditStatus.PASS
                if (b1.cv_fpr is not None and b2.cv_fpr is not None)
                else AuditStatus.BLOCKED_PENDING_RUN,
            )
        )

        _check_b2_utility_tradeoff(regime, seed, alpha_text, b1, b2, warnings)
    return out


def _binary_auc_fields(
    row: dict[str, Any], benign: np.ndarray | None, attack: np.ndarray | None
) -> tuple[float | None, float | None]:
    if MetricName.AUROC in row or MetricName.PR_AUC in row:
        return (
            None if row.get(MetricName.AUROC) is None else float(row[MetricName.AUROC]),
            None
            if row.get(MetricName.PR_AUC) is None
            else float(row[MetricName.PR_AUC]),
        )
    if benign is None or attack is None:
        return None, None
    ranking = compute_binary_ranking_metrics(benign, attack)
    return ranking.auroc, ranking.pr_auc


def _recon_summary(
    *,
    run_id: str | None,
    baseline: Baseline | None,
    seed: int,
    regime: Regime,
    alpha: str | None,
    client_id: str,
    stage: ScoringStage,
    arr: np.ndarray,
    overlap: float | None = None,
) -> ReconstructionErrorSummaryRecord:
    return ReconstructionErrorSummaryRecord(
        run_id=run_id,
        baseline=baseline,
        seed=seed,
        regime=regime,
        alpha=alpha,
        client_id=client_id,
        stage=stage,
        count=int(arr.size),
        mean=float(np.mean(arr)) if arr.size else None,
        std=float(np.std(arr, ddof=1)) if arr.size > 1 else None,
        min=float(np.min(arr)) if arr.size else None,
        p50=float(np.percentile(arr, 50)) if arr.size else None,
        p95=float(np.percentile(arr, EXTREME_PERCENTILE)) if arr.size else None,
        max=float(np.max(arr)) if arr.size else None,
        benign_attack_overlap=overlap,
        array_hash=array_hash(arr),
    )


def _score_stage_files(score_root: Path, stage: ScoringStage) -> list[Path]:
    stage_dir = score_root / stage
    return sorted(stage_dir.glob(PathToken.PARQUET_GLOB)) if stage_dir.exists() else []


def _load_cal_errors(score_root: Path) -> dict[str, np.ndarray]:
    return {
        path.stem: _read_scores(path)
        for path in _score_stage_files(score_root, ScoringStage.CAL)
    }


def _threshold_result(
    baseline: Baseline,
    regime: Regime,
    cal_errors: dict[str, np.ndarray],
    tau_global: float,
    *,
    cfg: DatpConfig,
    seed: int = 0,
    alpha: float | None = None,
) -> ThresholdResult:
    """Delegate to the canonical derive_threshold so audit and pipeline stay in lock-step."""
    return derive_threshold(
        baseline,
        cal_errors,
        n_min=cfg.threshold.n_min,
        q=cfg.threshold.q,
        tau_global=tau_global,
        regime=regime,
        threshold_cfg=cfg.threshold,
        seed=seed,
        alpha=alpha,
    )


def _build_partition_audit(
    *,
    regime: Regime,
    alpha_text: str | None,
    seed: int,
    partition_path: Path,
    partition_payload: dict[str, Any],
    metadata: dict[str, Any],
    feature_count: int | None,
    split_hash: str,
) -> DatasetPartitionAudit:
    file_hash_keys: list[str] = list(partition_payload["file_hashes"].keys())

    nbaiot_per_device: list[NBaIoTDeviceCounts] = []
    if regime in (Regime.A, Regime.C):
        processed_root = partition_path.parent
        nbaiot_per_device = build_nbaiot_per_device(processed_root, file_hash_keys)

    ciciot_protocol = build_ciciot_protocol() if regime == Regime.B else None
    chrono_ok, gap_ok = chronological_flags_for(regime)

    return DatasetPartitionAudit(
        dataset=partition_payload["dataset"],
        regime=regime,
        alpha=alpha_text,
        seed=seed if regime == Regime.C else None,
        manifest_path=str(partition_path),
        manifest_hash=hash_file(partition_path),
        split_hash=split_hash,
        feature_count=feature_count,
        client_count=metadata["n_clients"]
        if "n_clients" in metadata
        else metadata["n_devices"],
        nbaiot_per_device=nbaiot_per_device,
        ciciot_protocol=ciciot_protocol,
        confound_summary=confound_summary_for(regime),
        chronological_split_verified=chrono_ok,
        contiguous_gap_verified=gap_ok,
    )


def _metric_counts(
    metrics: dict[str, Any],
) -> tuple[int | None, int | None, int | None]:
    """Return (train_count, calibration_count, test_count).

    train_count and calibration_count are not available from the metrics payload;
    test_count is the sum of per-client benign + attack sample counts.
    """
    per_client = _normalized_per_client(metrics)
    test = sum(int(row[PayloadKey.N_BENIGN]) + int(row[PayloadKey.N_ATTACK]) for row in per_client)
    return None, None, test


def _normalized_per_client(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    per_client = metrics[PayloadKey.PER_CLIENT]
    if isinstance(per_client, dict):
        return [
            dict(values, client_id=client_id)
            for client_id, values in per_client.items()
        ]
    return list(per_client)


@dataclasses.dataclass(slots=True)
class _AuditAccumulator:
    manifest_records: list[RunManifestRecord] = dataclasses.field(default_factory=list)
    client_records: list[ClientMetricRecord] = dataclasses.field(default_factory=list)
    attack_records: list[PerAttackMetricRecord] = dataclasses.field(
        default_factory=list
    )
    threshold_records: list[ThresholdRecord] = dataclasses.field(default_factory=list)
    recon_records: list[ReconstructionErrorSummaryRecord] = dataclasses.field(
        default_factory=list
    )
    denominator_records: list[MetricDenominatorAuditRecord] = dataclasses.field(
        default_factory=list
    )
    convergence_records: list[ConvergenceAuditRecord] = dataclasses.field(
        default_factory=list
    )
    cluster_records: list[ClusterAssignmentRecord] = dataclasses.field(
        default_factory=list
    )
    companion_records: list[FPRCompanionRecord] = dataclasses.field(
        default_factory=list
    )
    worst_client_records: list[WorstClientRecord] = dataclasses.field(
        default_factory=list
    )
    homogeneity_records: list[CICIoTHomogeneityRecord] = dataclasses.field(
        default_factory=list
    )
    regime_c_alpha_records: list[RegimeCAlphaAuditRecord] = dataclasses.field(
        default_factory=list
    )
    partition_audits: dict[str, DatasetPartitionAudit] = dataclasses.field(
        default_factory=dict
    )
    invariant_inputs: dict[InvariantKey, dict[Baseline, InvariantHashes]] = (
        dataclasses.field(default_factory=lambda: defaultdict(dict))
    )
    score_hashes_by_cell: dict[
        InvariantKey, dict[Baseline, dict[tuple[ScoringStage, str], str]]
    ] = dataclasses.field(default_factory=lambda: defaultdict(dict))
    recomputation_records: list[MetricRecomputationRecord] = dataclasses.field(
        default_factory=list
    )
    cell_panel: dict[tuple[Regime, int, str | None, Baseline], _CellPanel] = (
        dataclasses.field(default_factory=dict)
    )
    warnings: list[WarningRecord] = dataclasses.field(default_factory=list)
    missing_confusion_warned: set[str] = dataclasses.field(default_factory=set)


@dataclasses.dataclass(frozen=True, slots=True)
class _RunContext:
    """All loaded and validated data for a single metrics run."""

    regime: Regime
    baseline: Baseline
    seed: int
    alpha: float | None
    alpha_text: str | None
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


@dataclasses.dataclass(frozen=True, slots=True)
class _ThresholdState:
    """Reconstructed thresholds and score arrays from threshold processing."""

    client_thresholds: dict[str, float]
    threshold_aggregation_method: ThresholdAggregationMethod
    test_benign_scores: dict[str, np.ndarray]
    test_attack_scores: dict[str, np.ndarray]
    cal_errors: dict[str, np.ndarray]

    @classmethod
    def empty(cls, baseline: Baseline) -> "_ThresholdState":
        return cls(
            client_thresholds={},
            threshold_aggregation_method=_lookup_threshold_agg(baseline),
            test_benign_scores={},
            test_attack_scores={},
            cal_errors={},
        )


def _load_run_context(
    metrics_path: Path,
    base_dir: Path,
    acc: _AuditAccumulator,
    data_root: Path | None,
) -> _RunContext | None:
    """Load and validate all data for a single metrics run. Returns None on schema failure."""
    run_id_obj = _parse_metric_path(base_dir, metrics_path)
    regime = run_id_obj.regime
    baseline = run_id_obj.baseline
    seed = run_id_obj.seed
    alpha = run_id_obj.alpha
    alpha_text = alpha_label(alpha)
    run_id = run_id_obj.audit_id()
    metrics = _load_json(metrics_path)
    schema_failures = validate_metrics_payload(metrics, module="audit.results")
    if schema_failures:
        for failure in schema_failures:
            acc.warnings.append(
                WarningRecord(
                    severity=AuditSeverity.FAIL,
                    code=WarningCode.SCHEMA_VERSION_MISMATCH,
                    message=f"{metrics_path}: {failure}",
                )
            )
        return None
    _data_root = data_root if data_root is not None else base_dir
    checkpoint_round: int | None = metrics.get("checkpoint_round")
    cell = TrainingCellId(regime=regime, seed=seed, alpha=alpha)
    layout = ArtifactLayout(base_dir=base_dir, regime=regime)
    if checkpoint_round is not None:
        score_root = layout.score_cell_for_round(cell, checkpoint_round).score_dir
        checkpoint = (
            layout.checkpoint_dir_for_round(cell, checkpoint_round)
            / ArtifactFile.MODEL_CHECKPOINT
        )
    else:
        score_root = layout.score_cell(cell).score_dir
        checkpoint = layout.checkpoint_dir(cell) / ArtifactFile.MODEL_CHECKPOINT
    partition_path = _partition_manifest_path(
        regime, seed, alpha, base_dir, data_root=_data_root
    )
    partition_payload = _manifest_payload(partition_path)
    metadata = partition_payload.get("metadata", {})
    feature_count = metadata["n_features"] if "n_features" in metadata else None
    normalized_clients = _normalized_per_client(metrics)
    client_count = int(metrics[PayloadKey.CLIENT_COUNT])
    split_hash = _split_hash(partition_path)
    model_hash = hash_file(checkpoint)
    training_hash = hash_file(metrics_path.parent / ArtifactFile.RESOLVED_CONFIG)
    preprocessing_hash = hash_file(partition_path)
    train_count, calibration_count, test_count = _metric_counts(metrics)
    eligible_count = int(metrics[PayloadKey.ELIGIBLE_COUNT])
    pending_count = int(metrics[PayloadKey.PENDING_COUNT])
    incomplete_ids = frozenset(str(cid) for cid in metrics[PayloadKey.EVAL_INCOMPLETE_IDS])
    eligible_client_ids = frozenset(str(cid) for cid in metrics[PayloadKey.ELIGIBLE_IDS])
    pending_client_ids = frozenset(str(cid) for cid in metrics[PayloadKey.PENDING_IDS])
    conv = _convergence_payload(checkpoint)
    invariant_key = InvariantKey(regime, seed, alpha_text)
    return _RunContext(
        regime=regime,
        baseline=baseline,
        seed=seed,
        alpha=alpha,
        alpha_text=alpha_text,
        run_id=run_id,
        metrics=metrics,
        data_root=_data_root,
        score_root=score_root,
        checkpoint=checkpoint,
        partition_path=partition_path,
        partition_payload=partition_payload,
        metadata=metadata,
        feature_count=feature_count,
        normalized_clients=normalized_clients,
        client_count=client_count,
        split_hash=split_hash,
        model_hash=model_hash,
        training_hash=training_hash,
        preprocessing_hash=preprocessing_hash,
        train_count=train_count,
        calibration_count=calibration_count,
        test_count=test_count,
        eligible_count=eligible_count,
        pending_count=pending_count,
        incomplete_ids=incomplete_ids,
        eligible_client_ids=eligible_client_ids,
        pending_client_ids=pending_client_ids,
        convergence_round=conv.convergence_round,
        convergence_value=conv.convergence_criterion_value,
        convergence_status=conv.convergence_status,
        curve_path=conv.curve_path,
        invariant_key=invariant_key,
    )


@dataclasses.dataclass(frozen=True, slots=True)
class _ScoreArrays:
    """Loaded score arrays from disk for a single run."""

    cal_errors: dict[str, np.ndarray]
    test_benign_scores: dict[str, np.ndarray]
    test_attack_scores: dict[str, np.ndarray]
    threshold_result: ThresholdResult | None


def _load_score_arrays(
    acc: _AuditAccumulator,
    ctx: _RunContext,
    cfg: DatpConfig,
) -> _ScoreArrays:
    """Load cal, test_benign, and test_attack score arrays; build threshold_result."""
    cal_errors: dict[str, np.ndarray] = {}
    test_benign_scores: dict[str, np.ndarray] = {}
    test_attack_scores: dict[str, np.ndarray] = {}
    threshold_result = None
    try:
        cal_errors = _load_cal_errors(ctx.score_root)
        test_benign_scores = {
            p.stem: _read_scores(p)
            for p in _score_stage_files(ctx.score_root, ScoringStage.TEST_BENIGN)
        }
        test_attack_scores = {
            p.stem: _read_scores(p)
            for p in _score_stage_files(ctx.score_root, ScoringStage.TEST_ATTACK)
        }
        threshold_result = _threshold_result(
            ctx.baseline,
            ctx.regime,
            cal_errors,
            float(ctx.metrics[MetricName.TAU_GLOBAL]),
            cfg=cfg,
            seed=ctx.seed,
            alpha=ctx.alpha,
        )
    except Exception as exc:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.FAIL,
                code=WarningCode.THRESHOLD_RECONSTRUCTION_FAILED,
                message=f"Could not reconstruct threshold assignments for {ctx.run_id}: {exc}",
            )
        )
    return _ScoreArrays(
        cal_errors=cal_errors,
        test_benign_scores=test_benign_scores,
        test_attack_scores=test_attack_scores,
        threshold_result=threshold_result,
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


@dataclasses.dataclass(frozen=True, slots=True)
class _ClientMetricParams:
    """Bundle per-client metric inputs to keep argument count below threshold."""

    client_id: str
    row: dict[str, Any]
    n_benign: int
    n_attack: int
    tp: int
    fp: int
    tn: int
    fn: int
    auroc: float | None
    pr_auc: float | None
    eligible: bool
    calibration_pending: bool
    evaluation_incomplete: bool
    coverage_ratio: str


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
                saved_balanced_accuracy=_float_or_none(row.get(MetricName.BALANCED_ACCURACY)),
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
    from datp.data.datasets.ciciot2023.spec import attack_family as _attack_family  # noqa: PLC0415

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
        if r[PayloadKey.CLIENT_ID] in eligible_ids
        and MetricName.FPR in r
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
        if r[PayloadKey.CLIENT_ID] in eligible_ids
        and MetricName.MACRO_F1 in r
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
        f"{ctx.eligible_count}/{ctx.client_count}" if ctx.client_count else DEFAULT_COVERAGE_RATIO
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
        tau_key = PayloadKey.TAU_B0 if PayloadKey.TAU_B0 in ctx.metrics else MetricName.TAU_GLOBAL
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


def _emit_structural_warnings(
    acc: _AuditAccumulator, seed_deltas: list[SeedDeltaRecord]
) -> None:
    if any(
        row.convergence_status == ConvergenceStatus.BLOCKED_PENDING_RUN
        for row in acc.convergence_records
    ):
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.MISSING_CONVERGENCE_CURVES,
                message="Existing checkpoints do not include convergence curves or FedAvg-weighted benign validation loss per round.",
                exact_command=BLOCKED_RESUME_COMMAND,
            )
        )
    if not any(
        row.regime == Regime.A and row.status == AuditStatus.PASS for row in seed_deltas
    ):
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.PRIMARY_DELTA_INCOMPLETE,
                message="Regime A B1-vs-B2 seed delta table is incomplete.",
                exact_command=BLOCKED_RESUME_COMMAND,
            )
        )
    if not acc.cluster_records:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.B4_CLUSTER_DIAGNOSTICS_INCOMPLETE,
                message="No B4 cluster assignment diagnostics were generated from completed artifacts.",
                exact_command=BLOCKED_RESUME_COMMAND,
            )
        )
    if not any(row.baseline == Baseline.B0 for row in acc.manifest_records):
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.B0_NORMALIZATION_DIAGNOSTIC_BLOCKED,
                message="Centralized pooled-normalization vs per-device-normalization diagnostic cannot run because B0 artifacts are missing.",
                exact_command=BLOCKED_RESUME_REGIME_A_COMMAND,
            )
        )
    acc.warnings.append(
        WarningRecord(
            severity=AuditSeverity.BLOCKED_PENDING_RUN,
            code=WarningCode.FIXED_OPERATING_POINT_METRICS_PENDING,
            message="FPR at fixed TPR and TPR at fixed FPR require persisted score arrays and operating-point configuration for every completed baseline cell.",
            exact_command=_AUDIT_RESULTS_COMMAND,
        )
    )


def _compute_regime_c_cv_fpr(
    rec: RegimeCAlphaAuditRecord,
    cell_panel: dict[tuple[Regime, int, str | None, Baseline], _CellPanel],
) -> tuple[float | None, float | None, float | None]:
    """Look up B1, B2, B4 CV(FPR) values from cell_panel for a Regime C record."""
    from datp.core.identity import AlphaLabel

    alpha_text: str | None = rec.alpha if rec.alpha not in (AlphaLabel.IID, "inf") else None
    if rec.alpha in (AlphaLabel.IID, "inf"):
        alpha_text = AlphaLabel.IID

    def _cv(key: tuple[Regime, int, str | None, Baseline]) -> float | None:
        panel = cell_panel.get(key)
        return panel.cv_fpr if panel is not None else None

    return (
        _cv((Regime.C, rec.seed, alpha_text, Baseline.B1)),
        _cv((Regime.C, rec.seed, alpha_text, Baseline.B2)),
        _cv((Regime.C, rec.seed, alpha_text, Baseline.B4)),
    )


def _enrich_regime_c_records_with_cv(
    records: list[RegimeCAlphaAuditRecord],
    cell_panel: dict[tuple[Regime, int, str | None, Baseline], _CellPanel],
) -> list[RegimeCAlphaAuditRecord]:
    enriched: list[RegimeCAlphaAuditRecord] = []
    for rec in records:
        b1_cv, b2_cv, b4_cv = _compute_regime_c_cv_fpr(rec, cell_panel)
        enriched.append(
            rec.model_copy(
                update={
                    "b1_cv_fpr": b1_cv,
                    "b2_cv_fpr": b2_cv,
                    "b4_cv_fpr": b4_cv,
                    "delta_b1_b2": _safe_diff(b1_cv, b2_cv),
                    "delta_b1_b4": _safe_diff(b1_cv, b4_cv),
                    "eligible_only_cv_fpr": b1_cv,
                }
            )
        )
    return enriched


def _b4_stability_from_cluster_records(
    cluster_records: list[ClusterAssignmentRecord],
) -> list[B4ClusterStabilityRecord]:
    from collections import defaultdict as _dd

    by_regime_alpha: dict[tuple[Regime, str | None], dict[int, dict[str, int]]] = _dd(
        lambda: _dd(dict)
    )
    for rec in cluster_records:
        try:
            cluster_int = (
                int(rec.cluster_id.split("_")[-1])
                if "_" in rec.cluster_id
                else int(rec.cluster_id)
            )
        except (ValueError, IndexError):
            cluster_int = hash(rec.cluster_id)
        by_regime_alpha[(rec.regime, rec.alpha)][rec.seed][rec.client_id] = cluster_int

    stability: list[B4ClusterStabilityRecord] = []
    for (regime, alpha), by_seed in by_regime_alpha.items():
        stability.extend(compute_b4_cluster_stability(dict(by_seed), regime, alpha))
    return stability


def run_results_audit(
    base_dir: Path, audit_dir: Path, cfg: DatpConfig, data_root: Path | None = None
) -> dict[str, Path]:
    base_dir = Path(base_dir)
    audit_dir = Path(audit_dir)
    audit_dir.mkdir(parents=True, exist_ok=True)

    git_commit = current_git_commit()
    timestamp = utc_timestamp()
    scoring_hash = source_hash(
        [
            Path("src/datp/training/scoring.py"),
            Path("src/datp/baselines/common/scoring.py"),
        ]
    )
    threshold_hash = source_hash(
        [
            Path("src/datp/baselines/main/b1.py"),
            Path("src/datp/baselines/main/b2.py"),
            Path("src/datp/baselines/main/b3.py"),
            Path("src/datp/baselines/main/b4.py"),
            Path("src/datp/baselines/common/thresholds.py"),
        ]
    )
    metrics_hash = source_hash(
        [
            Path("src/datp/evaluation/metrics.py"),
            Path("src/datp/evaluation/confusion.py"),
        ]
    )

    acc = _AuditAccumulator()
    metric_paths = _completed_metric_paths(base_dir)
    if not metric_paths:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.BLOCKED_PENDING_RUN,
                code=WarningCode.NO_COMPLETED_RESULTS,
                message="No completed metrics.json artifacts were found.",
                exact_command=BLOCKED_RESUME_COMMAND,
            )
        )

    for metrics_path in metric_paths:
        _process_run(
            metrics_path,
            base_dir,
            acc,
            git_commit=git_commit,
            timestamp=timestamp,
            scoring_hash=scoring_hash,
            threshold_hash=threshold_hash,
            metrics_hash=metrics_hash,
            cfg=cfg,
            data_root=data_root,
        )

    _seen_regime_c: set[tuple[str, int]] = set()
    for metrics_path in metric_paths:
        run_id_obj = _parse_metric_path(base_dir, metrics_path)
        regime = run_id_obj.regime
        seed = run_id_obj.seed
        alpha = run_id_obj.alpha
        if regime != Regime.C or alpha is None or (str(alpha), seed) in _seen_regime_c:
            continue
        _seen_regime_c.add((str(alpha), seed))
        _data_root_c = data_root if data_root is not None else base_dir
        prepared = prepared_root_for_regime(
            Regime.C, base_dir=_data_root_c, alpha=alpha, seed=seed
        )
        record = build_regime_c_alpha_audit(prepared, alpha, seed)
        if record is not None:
            acc.regime_c_alpha_records.append(record)
        else:
            acc.warnings.append(
                WarningRecord(
                    severity=AuditSeverity.BLOCKED_PENDING_RUN,
                    code=WarningCode.REGIME_C_ALPHA_AUDIT_MISSING,
                    message=(
                        f"Regime C alpha={alpha_label(alpha)} seed={seed} prepared manifest is "
                        "missing; JS divergence and device-mixture proportions cannot be audited."
                    ),
                    exact_command=BLOCKED_RESUME_COMMAND,
                )
            )

    acc.regime_c_alpha_records = _enrich_regime_c_records_with_cv(
        acc.regime_c_alpha_records, acc.cell_panel
    )

    severity_trend_records: list[RegimeCSeverityTrendRecord] = (
        compute_regime_c_severity_trend(
            acc.regime_c_alpha_records,
            significance_alpha=float(cfg.statistics.significance_alpha),
        )
    )

    b4_stability_records: list[B4ClusterStabilityRecord] = (
        _b4_stability_from_cluster_records(acc.cluster_records)
    )

    invariant_results = build_invariant_results(
        acc.invariant_inputs, acc.score_hashes_by_cell
    )

    seed_deltas = _build_seed_deltas(acc.cell_panel, acc.warnings)

    _emit_structural_warnings(acc, seed_deltas)
    _emit_worst_client_stability_warnings(acc.worst_client_records, acc.warnings)
    _emit_flat_cv_tpr_warnings(acc.cell_panel, acc.warnings)
    _emit_ciciot_homogeneity_warnings(
        acc.homogeneity_records,
        acc.warnings,
        homogeneity_threshold=cfg.quality_gates.ciciot_homogeneity_threshold,
    )

    _write_csv(audit_dir / RUN_MANIFEST_CSV, acc.manifest_records)
    _write_csv(audit_dir / FPR_COMPANION_METRICS_CSV, acc.companion_records)
    _write_csv(audit_dir / WORST_CLIENT_TRACKING_CSV, acc.worst_client_records)
    _write_csv(audit_dir / CICIOT_HOMOGENEITY_AUDIT_CSV, acc.homogeneity_records)
    _write_csv(audit_dir / REGIME_C_ALPHA_AUDIT_CSV, acc.regime_c_alpha_records)
    _write_csv(audit_dir / REGIME_C_SEVERITY_TREND_CSV, severity_trend_records)
    _write_csv(audit_dir / B4_CLUSTER_STABILITY_CSV, b4_stability_records)
    _write_csv(audit_dir / SEED_DELTAS_CSV, seed_deltas)
    _write_csv(audit_dir / PER_CLIENT_METRICS_CSV, acc.client_records)
    _write_csv(audit_dir / PER_ATTACK_METRICS_CSV, acc.attack_records)
    _write_csv(audit_dir / THRESHOLD_VALUES_CSV, acc.threshold_records)
    _write_csv(audit_dir / RECONSTRUCTION_ERROR_SUMMARY_CSV, acc.recon_records)
    _write_csv(audit_dir / CLUSTER_ASSIGNMENTS_CSV, acc.cluster_records)
    _write_csv(audit_dir / CONVERGENCE_AUDIT_CSV, acc.convergence_records)
    _write_csv(audit_dir / METRIC_DENOMINATOR_AUDIT_CSV, acc.denominator_records)
    _write_csv(audit_dir / METRIC_RECOMPUTATION_AUDIT_CSV, acc.recomputation_records)
    _write_json(
        audit_dir / BASELINE_INVARIANTS_JSON,
        [row.model_dump(mode="json") for row in invariant_results],
    )
    _write_json(
        audit_dir / DATASET_PARTITION_AUDIT_JSON,
        {
            "schema_version": AUDIT_SCHEMA_VERSION,
            "partitions": [
                row.model_dump(mode="json") for row in acc.partition_audits.values()
            ],
        },
    )
    _write_warnings(audit_dir / WARNINGS_MD, acc.warnings)
    _write_summary(
        audit_dir / AUDIT_SUMMARY_MD,
        acc.manifest_records,
        invariant_results,
        acc.warnings,
    )

    return {
        "baseline_invariants": audit_dir / BASELINE_INVARIANTS_JSON,
        "run_manifest": audit_dir / RUN_MANIFEST_CSV,
        "seed_deltas": audit_dir / SEED_DELTAS_CSV,
        "per_client_metrics": audit_dir / PER_CLIENT_METRICS_CSV,
        "per_attack_metrics": audit_dir / PER_ATTACK_METRICS_CSV,
        "threshold_values": audit_dir / THRESHOLD_VALUES_CSV,
        "reconstruction_error_summary": audit_dir / RECONSTRUCTION_ERROR_SUMMARY_CSV,
        "cluster_assignments": audit_dir / CLUSTER_ASSIGNMENTS_CSV,
        "dataset_partition_audit": audit_dir / DATASET_PARTITION_AUDIT_JSON,
        "convergence_audit": audit_dir / CONVERGENCE_AUDIT_CSV,
        "metric_denominator_audit": audit_dir / METRIC_DENOMINATOR_AUDIT_CSV,
        "metric_recomputation_audit": audit_dir / METRIC_RECOMPUTATION_AUDIT_CSV,
        "fpr_companion_metrics": audit_dir / FPR_COMPANION_METRICS_CSV,
        "worst_client_tracking": audit_dir / WORST_CLIENT_TRACKING_CSV,
        "regime_c_alpha_audit": audit_dir / REGIME_C_ALPHA_AUDIT_CSV,
        "regime_c_severity_trend": audit_dir / REGIME_C_SEVERITY_TREND_CSV,
        "b4_cluster_stability": audit_dir / B4_CLUSTER_STABILITY_CSV,
        "warnings": audit_dir / WARNINGS_MD,
        "audit_summary": audit_dir / AUDIT_SUMMARY_MD,
    }


def _write_warnings(path: Path, warnings: list[WarningRecord]) -> None:
    lines = ["# DATP Results Audit Warnings", ""]
    if not warnings:
        lines.append("No warnings.")
    for warning in warnings:
        lines.append(f"- **{warning.severity} `{warning.code}`**: {warning.message}")
        if warning.exact_command:
            lines.append(f" Command: `{warning.exact_command}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_summary(
    path: Path,
    manifest_records: list[RunManifestRecord],
    invariant_results: list[BaselineInvariantResult],
    warnings: list[WarningRecord],
) -> None:
    pass_count = sum(row.status == AuditStatus.PASS for row in invariant_results)
    blocked_count = sum(
        row.status == AuditStatus.BLOCKED_PENDING_RUN for row in invariant_results
    )
    fail_count = sum(row.status == AuditStatus.FAIL for row in invariant_results)
    lines = [
        "# DATP Results Audit Summary",
        "",
        f"- Completed runs audited: {len(manifest_records)}",
        f"- B1-B4 invariant PASS cells: {pass_count}",
        f"- B1-B4 invariant BLOCKED_PENDING_RUN cells: {blocked_count}",
        f"- B1-B4 invariant FAIL cells: {fail_count}",
        f"- Warning records: {len(warnings)}",
        "",
        "B0 is a centralized reference comparator; B1\u2013B4 share the trained encoder and scores. Threshold attribution claims are valid only after the B1\u2013B4 invariant passes for the same (regime, seed, alpha) cell.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
