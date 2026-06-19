from __future__ import annotations

import dataclasses
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile, PathToken
from datp.core.enums import (
    THRESHOLD_AGGREGATION_BY_BASELINE,
    Baseline,
    Regime,
    ScoringStage,
    ThresholdAggregationMethod,
)
from datp.core.identity import TrainingCellId, alpha_label
from datp.core.metric_enums import MetricName, PayloadKey
from datp.core.provenance import array_hash, hash_file, hash_jsonable
from datp.core.types import ThresholdResult
from datp.config.models import DatpConfig
from datp.data.catalog import DatasetID
from datp.data.paths import prepared_root_for_regime
from datp.data.regimes.catalog import dataset_for_regime
from datp.evaluation.artifact_validation import validate_metrics_payload
from datp.evaluation.ranking import compute_binary_ranking_metrics
from datp.scoring.loading import read_score_column as _read_scores
from datp.scoring.schema import SCORING_MANIFEST_NOT_PROVIDED
from datp.statistics.constants import EXTREME_PERCENTILE
from datp.thresholding.thresholds import _DeriveInput, derive_threshold
from datp.validation._audit_types import (
    _AuditAccumulator,
    _RunContext,
    _ScoreArrays,
)
from datp.validation.convergence import convergence_payload as _convergence_payload
from datp.validation.datasets import (
    build_ciciot_protocol,
    build_nbaiot_per_device,
    chronological_flags_for,
    confound_summary_for,
)
from datp.validation.discovery import parse_metric_path as _parse_metric_path
from datp.validation.enums import AuditSeverity, WarningCode, WorstDirection
from datp.validation.invariants import InvariantKey
from datp.validation.schemas import (
    DatasetPartitionAudit,
    NBaIoTDeviceCounts,
    ReconstructionErrorSummaryRecord,
    WarningRecord,
)


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
    if a is None or b is None:
        return None
    if not math.isfinite(a) or not math.isfinite(b):
        return None
    return float(a - b)


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
        _DeriveInput(
            baseline=baseline,
            client_errors=cal_errors,
            n_min=cfg.threshold.n_min,
            q=cfg.threshold.q,
            tau_global=tau_global,
            regime=regime,
            threshold_cfg=cfg.threshold,
            seed=seed,
            alpha=alpha,
        )
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
    test = sum(
        int(row[PayloadKey.N_BENIGN]) + int(row[PayloadKey.N_ATTACK])
        for row in per_client
    )
    return None, None, test


def _normalized_per_client(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    per_client = metrics[PayloadKey.PER_CLIENT]
    if isinstance(per_client, dict):
        return [
            dict(values, client_id=client_id)
            for client_id, values in per_client.items()
        ]
    return list(per_client)


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


def _resolve_score_root_and_checkpoint(
    cell: TrainingCellId,
    layout: ArtifactLayout,
    checkpoint_round: int | None,
) -> tuple[Path, Path]:
    """Return (score_root, checkpoint) for the given cell and optional round."""
    if checkpoint_round is not None:
        score_root = layout.score_cell_for_round(cell, checkpoint_round).score_dir
        checkpoint = (
            layout.checkpoint_dir_for_round(cell, checkpoint_round)
            / ArtifactFile.MODEL_CHECKPOINT
        )
    else:
        score_root = layout.score_cell(cell).score_dir
        checkpoint = layout.checkpoint_dir(cell) / ArtifactFile.MODEL_CHECKPOINT
    return score_root, checkpoint


def _parse_client_id_sets(
    metrics: dict[str, Any],
) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """Return (incomplete_ids, eligible_client_ids, pending_client_ids) from metrics."""
    incomplete_ids = frozenset(
        str(cid) for cid in metrics[PayloadKey.EVAL_INCOMPLETE_IDS]
    )
    eligible_client_ids = frozenset(
        str(cid) for cid in metrics[PayloadKey.ELIGIBLE_IDS]
    )
    pending_client_ids = frozenset(str(cid) for cid in metrics[PayloadKey.PENDING_IDS])
    return incomplete_ids, eligible_client_ids, pending_client_ids


def _emit_schema_failures(
    acc: _AuditAccumulator,
    metrics_path: Path,
    schema_failures: list[str],
) -> None:
    for failure in schema_failures:
        acc.warnings.append(
            WarningRecord(
                severity=AuditSeverity.FAIL,
                code=WarningCode.SCHEMA_VERSION_MISMATCH,
                message=f"{metrics_path}: {failure}",
            )
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
        _emit_schema_failures(acc, metrics_path, schema_failures)
        return None

    _data_root = data_root if data_root is not None else base_dir
    checkpoint_round: int | None = metrics.get("checkpoint_round")
    cell = TrainingCellId(regime=regime, seed=seed, alpha=alpha)
    layout = ArtifactLayout(base_dir=base_dir, regime=regime)
    score_root, checkpoint = _resolve_score_root_and_checkpoint(
        cell, layout, checkpoint_round
    )
    partition_path = _partition_manifest_path(
        regime, seed, alpha, base_dir, data_root=_data_root
    )
    partition_payload = _manifest_payload(partition_path)
    metadata = partition_payload.get("metadata", {})
    feature_count = metadata.get("n_features")
    normalized_clients = _normalized_per_client(metrics)
    client_count = int(metrics[PayloadKey.CLIENT_COUNT])
    split_hash = _split_hash(partition_path)
    model_hash = hash_file(checkpoint)
    training_hash = hash_file(metrics_path.parent / ArtifactFile.RESOLVED_CONFIG)
    preprocessing_hash = hash_file(partition_path)
    train_count, calibration_count, test_count = _metric_counts(metrics)
    eligible_count = int(metrics[PayloadKey.ELIGIBLE_COUNT])
    pending_count = int(metrics[PayloadKey.PENDING_COUNT])
    incomplete_ids, eligible_client_ids, pending_client_ids = _parse_client_id_sets(
        metrics
    )
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
