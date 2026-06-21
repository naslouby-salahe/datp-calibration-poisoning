"""Per-cell score-manifest verification: schema, manifest, checkpoint hash, client IDs, splits.

Uses ``_check_column_presence`` and ``_check_column_types`` for per-file Parquet schema
validation and ``datp.scoring.generation.validate_scoring_manifest`` for manifest
completion semantics. Does not recompute metrics (T03) or assign reuse verdicts (T04).
"""

from __future__ import annotations

import enum
import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field

from datp.artifacts.io import write_json_atomic
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactDir, ArtifactFile, PathToken
from datp.config.stages import get_stage_config
from datp.core.enums import (
    SCORING_STAGES,
    ScoringStage,
)
from datp.core.identity import TrainingCellId
from datp.core.provenance import hash_file
from datp.data.catalog import dataset_spec
from datp.scoring.schema import SCORE_COLUMN, SCORING_MANIFEST_NOT_PROVIDED
from datp.validation.constants import (
    SCORE_CELL_VERIFICATION_INDEX_JSON,
    SCORE_CELL_VERIFICATION_JSON,
)
from datp.validation.discovery import (
    ScoreCellLocation,
    iter_score_cells,
    parse_score_cell_dir,
)
from datp.validation.enums import AuditStatus
from datp.validation.schemas import ValidationCheck

_REQUIRED_MANIFEST_FIELDS: tuple[str, ...] = (
    "dataset",
    "seed",
    "expected_client_ids",
    "model_checkpoint_hash",
    "model_checkpoint_path",
    "expected_splits",
    "actual_client_ids",
    "actual_splits",
    "completion_status",
    "score_column_name",
    "records",
)


class ScoreCheckCode(enum.StrEnum):
    MANIFEST_PRESENT = "manifest_present"
    MANIFEST_PARSEABLE = "manifest_parseable"
    MANIFEST_FIELDS_PRESENT = "manifest_fields_present"
    MANIFEST_COMPLETION_STATUS = "manifest_completion_status"
    SCORING_SENTINEL_PRESENT = "scoring_sentinel_present"
    STAGE_MATCH = "stage_match"
    SEED_MATCH = "seed_match"
    DATASET_MATCH = "dataset_match"
    CLIENT_IDS_MATCH_PARTITION = "client_ids_match_partition"
    EXPECTED_VS_ACTUAL_CLIENTS = "expected_vs_actual_clients"
    EXPECTED_VS_ACTUAL_SPLITS = "expected_vs_actual_splits"
    SPLIT_DIRECTORIES_PRESENT = "split_directories_present"
    PER_CLIENT_SPLIT_FILES_PRESENT = "per_client_split_files_present"
    PARQUET_SCHEMA_VALID = "parquet_schema_valid"
    PARQUET_NON_EMPTY = "parquet_non_empty"
    CHECKPOINT_HASH_FIELD_PRESENT = "checkpoint_hash_field_present"
    CHECKPOINT_FILE_PRESENT = "checkpoint_file_present"
    CHECKPOINT_HASH_MATCHES = "checkpoint_hash_matches"


class ScoreCellVerification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)
    cell: TrainingCellId
    expected_client_ids: list[str] = Field(default_factory=list)
    expected_splits: list[str] = Field(default_factory=list)
    checks: list[ValidationCheck]
    overall_status: AuditStatus


def _expected_partition_clients(
    data_root: Path, location: ScoreCellLocation
) -> tuple[str, ...] | None:
    """Return the client-id set expected by the partition on disk; None when partition is missing."""
    from datp.data.paths import processed_root  # noqa: PLC0415

    stage_cfg = get_stage_config(location.cell.stage)
    if stage_cfg.dataset is None:
        return None
    spec = dataset_spec(stage_cfg.dataset)
    if spec.device_ids:
        return tuple(sorted(spec.device_ids))
    prepared_root = processed_root(stage_cfg.dataset, base_dir=data_root)
    if not prepared_root.exists():
        return None
    return tuple(sorted(p.name for p in prepared_root.iterdir() if p.is_dir()))


def _read_manifest(
    path: Path,
) -> tuple[dict[str, Any] | None, ValidationCheck, ValidationCheck]:
    if not path.exists():
        present = ValidationCheck(
            code=ScoreCheckCode.MANIFEST_PRESENT,
            status=AuditStatus.MISSING,
            detail=f"Scoring manifest absent at {path}",
        )
        parseable = ValidationCheck(
            code=ScoreCheckCode.MANIFEST_PARSEABLE,
            status=AuditStatus.MISSING,
            detail="Cannot parse: manifest file is absent",
        )
        return None, present, parseable

    present = ValidationCheck(
        code=ScoreCheckCode.MANIFEST_PRESENT, status=AuditStatus.PASS
    )
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return (
            None,
            present,
            ValidationCheck(
                code=ScoreCheckCode.MANIFEST_PARSEABLE,
                status=AuditStatus.FAIL,
                detail=f"Manifest JSON parse error: {exc}",
            ),
        )
    return (
        manifest,
        present,
        ValidationCheck(
            code=ScoreCheckCode.MANIFEST_PARSEABLE,
            status=AuditStatus.PASS,
        ),
    )


def _check_required_fields(manifest: dict[str, Any]) -> ValidationCheck:
    missing = [field for field in _REQUIRED_MANIFEST_FIELDS if field not in manifest]
    if missing:
        return ValidationCheck(
            code=ScoreCheckCode.MANIFEST_FIELDS_PRESENT,
            status=AuditStatus.FAIL,
            detail=f"Missing required manifest fields: {missing}",
        )
    return ValidationCheck(
        code=ScoreCheckCode.MANIFEST_FIELDS_PRESENT, status=AuditStatus.PASS
    )


def _check_completion_status(manifest: dict[str, Any]) -> ValidationCheck:
    status = manifest.get("completion_status")
    if status != "complete":
        return ValidationCheck(
            code=ScoreCheckCode.MANIFEST_COMPLETION_STATUS,
            status=AuditStatus.FAIL,
            detail=f"completion_status is {status!r}; expected 'complete'",
        )
    return ValidationCheck(
        code=ScoreCheckCode.MANIFEST_COMPLETION_STATUS, status=AuditStatus.PASS
    )


def _check_sentinel(cell_dir: Path) -> ValidationCheck:
    sentinel = cell_dir / ArtifactFile.SCORING_SENTINEL
    if not sentinel.exists():
        return ValidationCheck(
            code=ScoreCheckCode.SCORING_SENTINEL_PRESENT,
            status=AuditStatus.MISSING,
            detail=f"{ArtifactFile.SCORING_SENTINEL} absent",
        )
    return ValidationCheck(
        code=ScoreCheckCode.SCORING_SENTINEL_PRESENT, status=AuditStatus.PASS
    )


def _check_stage(
    manifest: dict[str, Any], location: ScoreCellLocation
) -> ValidationCheck:
    return _exact_match(
        ScoreCheckCode.STAGE_MATCH,
        actual=manifest.get("stage"),
        expected=location.cell.stage.value,
    )


def _check_seed(
    manifest: dict[str, Any], location: ScoreCellLocation
) -> ValidationCheck:
    return _exact_match(
        ScoreCheckCode.SEED_MATCH,
        actual=manifest.get("seed"),
        expected=location.seed,
    )


def _check_dataset(
    manifest: dict[str, Any], location: ScoreCellLocation
) -> ValidationCheck:
    stage_cfg = get_stage_config(location.cell.stage)
    expected = stage_cfg.dataset.value if stage_cfg.dataset is not None else None
    actual = manifest.get("dataset")
    if actual != expected:
        return ValidationCheck(
            code=ScoreCheckCode.DATASET_MATCH,
            status=AuditStatus.FAIL,
            detail=f"dataset {actual!r} does not match expected {expected!r} for {location.cell.stage}",
        )
    return ValidationCheck(code=ScoreCheckCode.DATASET_MATCH, status=AuditStatus.PASS)


def _exact_match(
    code: ScoreCheckCode, *, actual: Any, expected: Any
) -> ValidationCheck:
    if actual != expected:
        return ValidationCheck(
            code=code,
            status=AuditStatus.FAIL,
            detail=f"got {actual!r}, expected {expected!r}",
        )
    return ValidationCheck(code=code, status=AuditStatus.PASS)


def _check_clients_match_partition(
    manifest: dict[str, Any],
    expected_partition_clients: tuple[str, ...] | None,
) -> ValidationCheck:
    if expected_partition_clients is None:
        return ValidationCheck(
            code=ScoreCheckCode.CLIENT_IDS_MATCH_PARTITION,
            status=AuditStatus.MISSING,
            detail="Partition root not found; cannot cross-check client IDs",
        )
    declared = set(map(str, manifest.get("expected_client_ids", [])))
    expected_set = set(expected_partition_clients)
    if declared != expected_set:
        only_manifest = sorted(declared - expected_set)
        only_partition = sorted(expected_set - declared)
        return ValidationCheck(
            code=ScoreCheckCode.CLIENT_IDS_MATCH_PARTITION,
            status=AuditStatus.FAIL,
            detail=f"only_in_manifest={only_manifest}, only_in_partition={only_partition}",
        )
    return ValidationCheck(
        code=ScoreCheckCode.CLIENT_IDS_MATCH_PARTITION, status=AuditStatus.PASS
    )


def _check_expected_vs_actual(
    code: ScoreCheckCode,
    expected: list[Any],
    actual: list[Any],
) -> ValidationCheck:
    expected_set = set(map(str, expected))
    actual_set = set(map(str, actual))
    if expected_set != actual_set:
        return ValidationCheck(
            code=code,
            status=AuditStatus.FAIL,
            detail=f"missing={sorted(expected_set - actual_set)}, extra={sorted(actual_set - expected_set)}",
        )
    return ValidationCheck(code=code, status=AuditStatus.PASS)


def _check_split_directories(cell_dir: Path) -> ValidationCheck:
    missing = [
        stage.value for stage in SCORING_STAGES if not (cell_dir / stage.value).is_dir()
    ]
    if missing:
        return ValidationCheck(
            code=ScoreCheckCode.SPLIT_DIRECTORIES_PRESENT,
            status=AuditStatus.FAIL,
            detail=f"missing split dirs: {missing}",
        )
    return ValidationCheck(
        code=ScoreCheckCode.SPLIT_DIRECTORIES_PRESENT, status=AuditStatus.PASS
    )


def _collect_missing_stage_files(
    stage_dir: Path, stage_value: str, expected_client_ids: list[str]
) -> list[str]:
    return [
        f"{stage_value}/{cid}.parquet"
        for cid in expected_client_ids
        if not (stage_dir / f"{cid}{PathToken.PARQUET_EXT}").is_file()
    ]


def _check_per_client_split_files(
    cell_dir: Path,
    expected_client_ids: list[str],
) -> ValidationCheck:
    missing: list[str] = []
    for stage in SCORING_STAGES:
        stage_dir = cell_dir / stage.value
        if not stage_dir.is_dir():
            continue
        missing.extend(
            _collect_missing_stage_files(stage_dir, stage.value, expected_client_ids)
        )
    if missing:
        return ValidationCheck(
            code=ScoreCheckCode.PER_CLIENT_SPLIT_FILES_PRESENT,
            status=AuditStatus.FAIL,
            detail=f"missing per-client split files: {missing[:5]}{'...' if len(missing) > 5 else ''}",
        )
    return ValidationCheck(
        code=ScoreCheckCode.PER_CLIENT_SPLIT_FILES_PRESENT, status=AuditStatus.PASS
    )


def _check_column_presence(parquet: Path) -> str | None:
    """Check that the score artifact has exactly the required column. Returns error message or None."""
    schema = pq.read_schema(parquet)
    if schema.names != [SCORE_COLUMN]:
        return f"columns: expected [{SCORE_COLUMN}], got {schema.names}"
    return None


def _check_column_types(parquet: Path) -> str | None:
    """Check that SCORE_COLUMN is a floating type. Returns error message or None."""
    schema = pq.read_schema(parquet)
    field = schema.field(SCORE_COLUMN)
    if not pa.types.is_floating(field.type):
        return f"type: expected floating, got {field.type}"
    return None


def _validate_score_file(
    parquet: Path,
    stage: ScoringStage,
    client_id: str,
) -> tuple[str | None, str | None]:
    """Validate a single score Parquet file.

    Returns (schema_error_label, empty_label). Exactly one of the two may be
    non-None; both None means the file passed all checks.
    """
    presence_err = _check_column_presence(parquet)
    if presence_err is not None:
        return f"{stage.value}/{client_id}.parquet: {presence_err}", None
    type_err = _check_column_types(parquet)
    if type_err is not None:
        return f"{stage.value}/{client_id}.parquet: {type_err}", None
    try:
        row_count = pq.read_metadata(parquet).num_rows
    except Exception as exc:  # noqa: BLE001
        return f"{stage.value}/{client_id}.parquet: metadata read failed: {exc}", None
    if row_count == 0 and stage != ScoringStage.TEST_ATTACK:
        return None, f"{stage.value}/{client_id}.parquet"
    return None, None


def _validate_stage_files(
    stage_dir: Path,
    stage: ScoringStage,
    expected_client_ids: list[str],
) -> tuple[list[str], list[str]]:
    """Validate all score files in a single stage directory.

    Returns (schema_errors, empty_labels).
    """
    schema_errors: list[str] = []
    empty: list[str] = []
    for client_id in expected_client_ids:
        parquet = stage_dir / f"{client_id}{PathToken.PARQUET_EXT}"
        if not parquet.is_file():
            continue
        schema_err, empty_label = _validate_score_file(parquet, stage, client_id)
        if schema_err is not None:
            schema_errors.append(schema_err)
        if empty_label is not None:
            empty.append(empty_label)
    return schema_errors, empty


def _check_parquet_schema(
    cell_dir: Path,
    expected_client_ids: list[str],
) -> tuple[ValidationCheck, ValidationCheck]:
    schema_errors: list[str] = []
    empty: list[str] = []
    for stage in SCORING_STAGES:
        stage_dir = cell_dir / stage.value
        if not stage_dir.is_dir():
            continue
        stage_schema_errs, stage_empty = _validate_stage_files(
            stage_dir,
            stage,
            expected_client_ids,
        )
        schema_errors.extend(stage_schema_errs)
        empty.extend(stage_empty)
    if schema_errors:
        schema_detail = f"{len(schema_errors)} schema errors; first: {schema_errors[0]}"
        schema_check = ValidationCheck(
            code=ScoreCheckCode.PARQUET_SCHEMA_VALID,
            status=AuditStatus.FAIL,
            detail=schema_detail,
        )
    else:
        schema_check = ValidationCheck(
            code=ScoreCheckCode.PARQUET_SCHEMA_VALID,
            status=AuditStatus.PASS,
        )
    if empty:
        empty_check = ValidationCheck(
            code=ScoreCheckCode.PARQUET_NON_EMPTY,
            status=AuditStatus.FAIL,
            detail=f"empty score files: {empty}",
        )
    else:
        empty_check = ValidationCheck(
            code=ScoreCheckCode.PARQUET_NON_EMPTY,
            status=AuditStatus.PASS,
        )
    return schema_check, empty_check


def _check_checkpoint(
    base_dir: Path,
    data_root: Path,
    location: ScoreCellLocation,
    manifest: dict[str, Any],
) -> tuple[ValidationCheck, ValidationCheck, ValidationCheck]:
    declared_hash = manifest.get("model_checkpoint_hash")
    declared_path = manifest.get("model_checkpoint_path")

    if not declared_hash or declared_hash == SCORING_MANIFEST_NOT_PROVIDED:
        hash_field = ValidationCheck(
            code=ScoreCheckCode.CHECKPOINT_HASH_FIELD_PRESENT,
            status=AuditStatus.FAIL,
            detail=f"model_checkpoint_hash is {declared_hash!r}",
        )
        file_check = ValidationCheck(
            code=ScoreCheckCode.CHECKPOINT_FILE_PRESENT,
            status=AuditStatus.MISSING,
            detail="Skipped: hash field missing",
        )
        match_check = ValidationCheck(
            code=ScoreCheckCode.CHECKPOINT_HASH_MATCHES,
            status=AuditStatus.MISSING,
            detail="Skipped: hash field missing",
        )
        return hash_field, file_check, match_check
    hash_field = ValidationCheck(
        code=ScoreCheckCode.CHECKPOINT_HASH_FIELD_PRESENT,
        status=AuditStatus.PASS,
    )

    canonical = (
        ArtifactLayout(base_dir=base_dir, stage=location.cell.stage).checkpoint_dir(
            location.cell
        )
        / ArtifactFile.MODEL_CHECKPOINT
    )
    declared_full = data_root / declared_path if declared_path else canonical

    candidate = canonical if canonical.exists() else declared_full
    if not candidate.exists():
        file_check = ValidationCheck(
            code=ScoreCheckCode.CHECKPOINT_FILE_PRESENT,
            status=AuditStatus.MISSING,
            detail=f"Checkpoint not found at canonical {canonical} or declared {declared_full}",
        )
        match_check = ValidationCheck(
            code=ScoreCheckCode.CHECKPOINT_HASH_MATCHES,
            status=AuditStatus.MISSING,
            detail="Skipped: checkpoint file missing",
        )
        return hash_field, file_check, match_check

    file_check = ValidationCheck(
        code=ScoreCheckCode.CHECKPOINT_FILE_PRESENT, status=AuditStatus.PASS
    )
    actual_hash = hash_file(candidate)
    if actual_hash != declared_hash:
        match_check = ValidationCheck(
            code=ScoreCheckCode.CHECKPOINT_HASH_MATCHES,
            status=AuditStatus.FAIL,
            detail=f"declared={declared_hash}, actual={actual_hash} (at {candidate})",
        )
    else:
        match_check = ValidationCheck(
            code=ScoreCheckCode.CHECKPOINT_HASH_MATCHES,
            status=AuditStatus.PASS,
        )
    return hash_field, file_check, match_check


def _overall_status(checks: list[ValidationCheck]) -> AuditStatus:
    statuses = {c.status for c in checks}
    if AuditStatus.FAIL in statuses:
        return AuditStatus.FAIL
    if AuditStatus.MISSING in statuses:
        return AuditStatus.PARTIAL
    return AuditStatus.PASS


def verify_score_cell(
    cell_dir: Path,
    base_dir: Path,
    *,
    data_root: Path | None = None,
) -> ScoreCellVerification:
    """Verify one score cell directory and return a structured per-cell report.

    ``base_dir`` is the experiment root (e.g. ``outputs/``); ``cell_dir`` is the cell directory
    under ``<base_dir>/scores/<stage>/seed_N/``. ``data_root`` defaults to
    ``base_dir.parent`` (repo root containing ``data/processed/``).
    """
    cell_dir = cell_dir.resolve()
    base_dir = base_dir.resolve()
    resolved_data_root = (data_root or base_dir.parent).resolve()
    scores_root = base_dir / ArtifactDir.SCORES
    location = parse_score_cell_dir(scores_root, cell_dir)
    return _verify_at_location(base_dir, resolved_data_root, location)


def _append_full_manifest_checks(
    checks: list[ValidationCheck],
    manifest: dict[str, Any],
    location: "ScoreCellLocation",
    cell_dir: Path,
    base_dir: Path,
    data_root: Path,
) -> tuple[list[str], list[str]]:
    expected_client_ids = list(map(str, manifest["expected_client_ids"]))
    expected_splits = list(map(str, manifest["expected_splits"]))
    checks.append(_check_completion_status(manifest))
    checks.append(_check_stage(manifest, location))
    checks.append(_check_seed(manifest, location))
    checks.append(_check_dataset(manifest, location))
    checks.append(
        _check_expected_vs_actual(
            ScoreCheckCode.EXPECTED_VS_ACTUAL_CLIENTS,
            manifest["expected_client_ids"],
            manifest["actual_client_ids"],
        )
    )
    checks.append(
        _check_expected_vs_actual(
            ScoreCheckCode.EXPECTED_VS_ACTUAL_SPLITS,
            manifest["expected_splits"],
            manifest["actual_splits"],
        )
    )
    checks.append(
        _check_clients_match_partition(
            manifest,
            _expected_partition_clients(data_root, location),
        )
    )
    checks.append(_check_per_client_split_files(cell_dir, expected_client_ids))
    schema_check, empty_check = _check_parquet_schema(cell_dir, expected_client_ids)
    checks.extend([schema_check, empty_check])
    hash_field, file_check, match_check = _check_checkpoint(
        base_dir, data_root, location, manifest
    )
    checks.extend([hash_field, file_check, match_check])
    return expected_client_ids, expected_splits


def _verify_at_location(
    base_dir: Path,
    data_root: Path,
    location: "ScoreCellLocation",
) -> "ScoreCellVerification":
    cell_dir = location.cell_dir
    manifest_path = cell_dir / ArtifactFile.SCORING_MANIFEST
    checks: list[ValidationCheck] = []

    manifest, present, parseable = _read_manifest(manifest_path)
    checks.extend(
        [
            present,
            parseable,
            _check_sentinel(cell_dir),
            _check_split_directories(cell_dir),
        ]
    )

    if manifest is None:
        return ScoreCellVerification(
            cell=location.cell,
            expected_client_ids=[],
            expected_splits=[],
            checks=checks,
            overall_status=_overall_status(checks),
        )

    fields_check = _check_required_fields(manifest)
    checks.append(fields_check)
    if fields_check.status != AuditStatus.PASS:
        return ScoreCellVerification(
            cell=location.cell,
            expected_client_ids=list(map(str, manifest.get("expected_client_ids", []))),
            expected_splits=list(map(str, manifest.get("expected_splits", []))),
            checks=checks,
            overall_status=_overall_status(checks),
        )

    expected_client_ids, expected_splits = _append_full_manifest_checks(
        checks, manifest, location, cell_dir, base_dir, data_root
    )
    return ScoreCellVerification(
        cell=location.cell,
        expected_client_ids=expected_client_ids,
        expected_splits=expected_splits,
        checks=checks,
        overall_status=_overall_status(checks),
    )


def verify_all_score_cells(
    base_dir: Path,
    *,
    data_root: Path | None = None,
    write_reports: bool = False,
) -> list[ScoreCellVerification]:
    """Verify all discoverable score cells; optionally write a JSON report per cell + an index."""
    resolved_base = base_dir.resolve()
    resolved_data_root = (data_root or resolved_base.parent).resolve()
    results: list[ScoreCellVerification] = []
    for location in iter_score_cells(base_dir):
        report = _verify_at_location(resolved_base, resolved_data_root, location)
        results.append(report)
        if write_reports:
            write_json_atomic(
                location.cell_dir / SCORE_CELL_VERIFICATION_JSON,
                report.model_dump(mode="json"),
            )
    if write_reports:
        write_json_atomic(
            resolved_base / ArtifactDir.SCORES / SCORE_CELL_VERIFICATION_INDEX_JSON,
            {"cells": [r.model_dump(mode="json") for r in results]},
        )
    return results


def assert_score_column() -> str:
    """Sanity hook for callers; ensures the verifier uses the canonical score column name."""
    return SCORE_COLUMN
