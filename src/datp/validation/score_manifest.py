from __future__ import annotations

from datp.types import (
    ArtifactName,
    ClientId,
    ColumnName,
    NarrativeText,
)


import json
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TypeVar

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import ValidationError

from datp.artifacts.io import write_json_atomic
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactDir, ArtifactFile, PathToken
from datp.config.models import get_stage_config
from datp.core.enums import SCORING_STAGES, ScoringStage
from datp.core.provenance import hash_file
from datp.data.catalog import dataset_spec
from datp.scoring.manifest import (
    ScoringColumn,
    ScoringManifestAuditView,
    ScoringManifestSentinel,
    ScoringManifestStatus,
)
from datp.validation.discovery import (
    ScoreCellLocation,
    iter_score_cells,
    parse_score_cell_dir,
)
from datp.validation.enums import AuditArtifact, AuditStatus, ScoreCheckCode
from datp.validation.schemas import ScoreCellVerification, ValidationCheck

REQUIRED_MANIFEST_FIELDS: tuple[ColumnName, ...] = (
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

_ExactMatchValue = TypeVar("_ExactMatchValue")
_ManifestComparisonValue = TypeVar(
    "_ManifestComparisonValue", ClientId, ScoringStage
)


def expected_partition_clients(
    data_root: Path, location: ScoreCellLocation
) -> tuple[ClientId, ...] | None:
    from datp.data.paths import processed_root

    stage_cfg = get_stage_config(location.cell.stage)
    if stage_cfg.dataset is None:
        return None

    spec = dataset_spec(stage_cfg.dataset)
    if spec.device_ids:
        return tuple(ClientId(device_id) for device_id in sorted(spec.device_ids))

    prepared_root = processed_root(stage_cfg.dataset, base_dir=data_root)
    if not prepared_root.exists():
        return None
    return tuple(
        ClientId(path.name)
        for path in sorted(prepared_root.iterdir())
        if path.is_dir()
    )


def read_manifest(
    path: Path,
) -> tuple[ScoringManifestAuditView | None, ValidationCheck, ValidationCheck]:
    if not path.exists():
        return (
            None,
            ValidationCheck(
                code=ScoreCheckCode.MANIFEST_PRESENT,
                status=AuditStatus.MISSING,
                detail=f"Scoring manifest absent at {path}",
            ),
            ValidationCheck(
                code=ScoreCheckCode.MANIFEST_PARSEABLE,
                status=AuditStatus.MISSING,
                detail="Cannot parse: manifest file is absent",
            ),
        )

    present = ValidationCheck(
        code=ScoreCheckCode.MANIFEST_PRESENT, status=AuditStatus.PASS
    )
    try:
        manifest = ScoringManifestAuditView.model_validate_json(path.read_text())
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
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
            code=ScoreCheckCode.MANIFEST_PARSEABLE, status=AuditStatus.PASS
        ),
    )


def check_required_fields(manifest: ScoringManifestAuditView) -> ValidationCheck:
    missing = [field for field in REQUIRED_MANIFEST_FIELDS if field not in manifest.model_fields_set]
    if missing:
        return ValidationCheck(
            code=ScoreCheckCode.MANIFEST_FIELDS_PRESENT,
            status=AuditStatus.FAIL,
            detail=f"Missing required manifest fields: {missing}",
        )
    return ValidationCheck(
        code=ScoreCheckCode.MANIFEST_FIELDS_PRESENT, status=AuditStatus.PASS
    )


def check_completion_status(manifest: ScoringManifestAuditView) -> ValidationCheck:
    if manifest.completion_status != ScoringManifestStatus.COMPLETE:
        return ValidationCheck(
            code=ScoreCheckCode.MANIFEST_COMPLETION_STATUS,
            status=AuditStatus.FAIL,
            detail=f"completion_status is {manifest.completion_status!r}; expected 'complete'",
        )
    return ValidationCheck(
        code=ScoreCheckCode.MANIFEST_COMPLETION_STATUS, status=AuditStatus.PASS
    )


def check_sentinel(cell_dir: Path) -> ValidationCheck:
    if not (cell_dir / ArtifactFile.SCORING_SENTINEL).exists():
        return ValidationCheck(
            code=ScoreCheckCode.SCORING_SENTINEL_PRESENT,
            status=AuditStatus.MISSING,
            detail=f"{ArtifactFile.SCORING_SENTINEL} absent",
        )
    return ValidationCheck(
        code=ScoreCheckCode.SCORING_SENTINEL_PRESENT, status=AuditStatus.PASS
    )


def exact_match(
    code: ScoreCheckCode,
    *,
    actual: _ExactMatchValue,
    expected: _ExactMatchValue,
) -> ValidationCheck:
    if actual != expected:
        return ValidationCheck(
            code=code,
            status=AuditStatus.FAIL,
            detail=f"got {actual!r}, expected {expected!r}",
        )
    return ValidationCheck(code=code, status=AuditStatus.PASS)


def check_clients_match_partition(
    manifest: ScoringManifestAuditView,
    expected_partition_clients: tuple[ClientId, ...] | None,
) -> ValidationCheck:
    if expected_partition_clients is None:
        return ValidationCheck(
            code=ScoreCheckCode.CLIENT_IDS_MATCH_PARTITION,
            status=AuditStatus.MISSING,
            detail="Partition root not found; cannot cross-check client IDs",
        )

    declared = set(manifest.expected_client_ids)
    expected_set = set(expected_partition_clients)

    if declared != expected_set:
        return ValidationCheck(
            code=ScoreCheckCode.CLIENT_IDS_MATCH_PARTITION,
            status=AuditStatus.FAIL,
            detail=f"only_in_manifest={sorted(declared - expected_set)}, only_in_partition={sorted(expected_set - declared)}",
        )
    return ValidationCheck(
        code=ScoreCheckCode.CLIENT_IDS_MATCH_PARTITION, status=AuditStatus.PASS
    )


def check_expected_vs_actual(
    code: ScoreCheckCode,
    expected: Sequence[_ManifestComparisonValue],
    actual: Sequence[_ManifestComparisonValue],
) -> ValidationCheck:
    expected_set, actual_set = set(expected), set(actual)
    if expected_set != actual_set:
        missing = ", ".join(str(item) for item in sorted(expected_set - actual_set))
        extra = ", ".join(str(item) for item in sorted(actual_set - expected_set))
        return ValidationCheck(
            code=code,
            status=AuditStatus.FAIL,
            detail=f"missing=[{missing}], extra=[{extra}]",
        )
    return ValidationCheck(code=code, status=AuditStatus.PASS)


def check_split_directories(cell_dir: Path) -> ValidationCheck:
    if missing := [
        stage for stage in SCORING_STAGES if not (cell_dir / stage).is_dir()
    ]:
        return ValidationCheck(
            code=ScoreCheckCode.SPLIT_DIRECTORIES_PRESENT,
            status=AuditStatus.FAIL,
            detail=f"missing split dirs: {missing}",
        )
    return ValidationCheck(
        code=ScoreCheckCode.SPLIT_DIRECTORIES_PRESENT, status=AuditStatus.PASS
    )


def check_per_client_split_files(
    cell_dir: Path, expected_client_ids: list[ClientId]
) -> ValidationCheck:
    missing = [
        f"{stage}/{cid}.parquet"
        for stage in SCORING_STAGES
        if (stage_dir := cell_dir / stage).is_dir()
        for cid in expected_client_ids
        if not (stage_dir / f"{cid}{PathToken.PARQUET_EXT}").is_file()
    ]
    if missing:
        return ValidationCheck(
            code=ScoreCheckCode.PER_CLIENT_SPLIT_FILES_PRESENT,
            status=AuditStatus.FAIL,
            detail=f"missing per-client split files: {missing[:5]}{'...' if len(missing) > 5 else ''}",
        )
    return ValidationCheck(
        code=ScoreCheckCode.PER_CLIENT_SPLIT_FILES_PRESENT, status=AuditStatus.PASS
    )


def validate_score_file(
    parquet: Path, stage: ScoringStage, client_id: ClientId
) -> tuple[ArtifactName | None, ArtifactName | None]:
    try:
        schema = pq.read_schema(parquet)
        if schema.names != [ScoringColumn.RECONSTRUCTION_ERROR]:
            return (
                f"{stage}/{client_id}.parquet: columns: expected [{ScoringColumn.RECONSTRUCTION_ERROR}], got {schema.names}",
                None,
            )
        if not pa.types.is_floating(schema.field(ScoringColumn.RECONSTRUCTION_ERROR).type):
            return (
                f"{stage}/{client_id}.parquet: type: expected floating, got {schema.field(ScoringColumn.RECONSTRUCTION_ERROR).type}",
                None,
            )

        row_count = pq.read_metadata(parquet).num_rows
        if row_count == 0 and stage != ScoringStage.TEST_ATTACK:
            return None, f"{stage}/{client_id}.parquet"
    except Exception as exc:
        return f"{stage}/{client_id}.parquet: read failed: {exc}", None

    return None, None


def _check_client_parquet(
    parquet: Path, stage: ScoringStage, cid: ClientId
) -> tuple[NarrativeText | None, NarrativeText | None]:
    if not parquet.is_file():
        return None, None
    return validate_score_file(parquet, stage, cid)


def _scan_score_files(
    cell_dir: Path, expected_client_ids: list[ClientId]
) -> tuple[list[NarrativeText], list[NarrativeText]]:
    schema_errors: list[NarrativeText] = []
    empty: list[NarrativeText] = []
    for stage in SCORING_STAGES:
        stage_dir = cell_dir / stage
        if not stage_dir.is_dir():
            continue
        for cid in expected_client_ids:
            parquet = stage_dir / f"{cid}{PathToken.PARQUET_EXT}"
            schema_err, empty_label = _check_client_parquet(parquet, stage, cid)
            if schema_err:
                schema_errors.append(schema_err)
            if empty_label:
                empty.append(empty_label)
    return schema_errors, empty


def check_parquet_schema(
    cell_dir: Path, expected_client_ids: list[ClientId]
) -> tuple[ValidationCheck, ValidationCheck]:
    schema_errors, empty = _scan_score_files(cell_dir, expected_client_ids)

    schema_check = ValidationCheck(
        code=ScoreCheckCode.PARQUET_SCHEMA_VALID,
        status=AuditStatus.FAIL if schema_errors else AuditStatus.PASS,
        detail=f"{len(schema_errors)} schema errors; first: {schema_errors[0]}"
        if schema_errors
        else "",
    )
    empty_check = ValidationCheck(
        code=ScoreCheckCode.PARQUET_NON_EMPTY,
        status=AuditStatus.FAIL if empty else AuditStatus.PASS,
        detail=f"empty score files: {empty}" if empty else "",
    )
    return schema_check, empty_check


def check_checkpoint(
    base_dir: Path,
    data_root: Path,
    location: ScoreCellLocation,
    manifest: ScoringManifestAuditView,
) -> tuple[ValidationCheck, ValidationCheck, ValidationCheck]:
    declared_hash = manifest.model_checkpoint_hash
    declared_path = manifest.model_checkpoint_path

    if not declared_hash or declared_hash == ScoringManifestSentinel.NOT_PROVIDED:
        return (
            ValidationCheck(
                code=ScoreCheckCode.CHECKPOINT_HASH_FIELD_PRESENT,
                status=AuditStatus.FAIL,
                detail=f"model_checkpoint_hash is {declared_hash!r}",
            ),
            ValidationCheck(
                code=ScoreCheckCode.CHECKPOINT_FILE_PRESENT,
                status=AuditStatus.MISSING,
                detail="Skipped: hash field missing",
            ),
            ValidationCheck(
                code=ScoreCheckCode.CHECKPOINT_HASH_MATCHES,
                status=AuditStatus.MISSING,
                detail="Skipped: hash field missing",
            ),
        )

    hash_field = ValidationCheck(
        code=ScoreCheckCode.CHECKPOINT_HASH_FIELD_PRESENT, status=AuditStatus.PASS
    )
    canonical = (
        ArtifactLayout(base_dir=base_dir, stage=location.cell.stage).checkpoint_dir(
            location.cell
        )
        / ArtifactFile.MODEL_CHECKPOINT
    )
    if canonical.exists():
        candidate = canonical
    elif declared_path:
        candidate = data_root / declared_path
    else:
        candidate = canonical

    if not candidate.exists():
        declared_loc = data_root / declared_path if declared_path else canonical
        return (
            hash_field,
            ValidationCheck(
                code=ScoreCheckCode.CHECKPOINT_FILE_PRESENT,
                status=AuditStatus.MISSING,
                detail=f"Checkpoint not found at canonical {canonical} or declared {declared_loc}",
            ),
            ValidationCheck(
                code=ScoreCheckCode.CHECKPOINT_HASH_MATCHES,
                status=AuditStatus.MISSING,
                detail="Skipped: checkpoint file missing",
            ),
        )

    actual_hash = hash_file(candidate)
    return (
        hash_field,
        ValidationCheck(
            code=ScoreCheckCode.CHECKPOINT_FILE_PRESENT, status=AuditStatus.PASS
        ),
        ValidationCheck(
            code=ScoreCheckCode.CHECKPOINT_HASH_MATCHES,
            status=AuditStatus.PASS
            if actual_hash == declared_hash
            else AuditStatus.FAIL,
            detail=""
            if actual_hash == declared_hash
            else f"declared={declared_hash}, actual={actual_hash} (at {candidate})",
        ),
    )


def evaluate_overall_status(checks: list[ValidationCheck]) -> AuditStatus:
    statuses = {c.status for c in checks}
    if AuditStatus.FAIL in statuses:
        return AuditStatus.FAIL
    if AuditStatus.MISSING in statuses:
        return AuditStatus.PARTIAL
    return AuditStatus.PASS


def append_full_manifest_checks(
    checks: list[ValidationCheck],
    manifest: ScoringManifestAuditView,
    location: ScoreCellLocation,
    cell_dir: Path,
    base_dir: Path,
    data_root: Path,
) -> tuple[list[ClientId], list[ScoringStage]]:
    expected_client_ids = list(manifest.expected_client_ids)
    expected_splits = list(manifest.expected_splits)

    stage_cfg = get_stage_config(location.cell.stage)

    checks.extend(
        [
            check_completion_status(manifest),
            exact_match(
                ScoreCheckCode.STAGE_MATCH,
                actual=manifest.stage,
                expected=location.cell.stage,
            ),
            exact_match(
                ScoreCheckCode.SEED_MATCH,
                actual=manifest.seed,
                expected=location.seed,
            ),
            exact_match(
                ScoreCheckCode.DATASET_MATCH,
                actual=manifest.dataset,
                expected=stage_cfg.dataset,
            ),
            check_expected_vs_actual(
                ScoreCheckCode.EXPECTED_VS_ACTUAL_CLIENTS,
                manifest.expected_client_ids,
                manifest.actual_client_ids,
            ),
            check_expected_vs_actual(
                ScoreCheckCode.EXPECTED_VS_ACTUAL_SPLITS,
                manifest.expected_splits,
                manifest.actual_splits,
            ),
            check_clients_match_partition(
                manifest, expected_partition_clients(data_root, location)
            ),
            check_per_client_split_files(cell_dir, expected_client_ids),
        ]
    )

    checks.extend(check_parquet_schema(cell_dir, expected_client_ids))
    checks.extend(check_checkpoint(base_dir, data_root, location, manifest))

    return expected_client_ids, expected_splits


def verify_at_location(
    base_dir: Path, data_root: Path, location: ScoreCellLocation
) -> ScoreCellVerification:
    checks: list[ValidationCheck] = []
    manifest, present, parseable = read_manifest(
        location.cell_dir / ArtifactFile.SCORING_MANIFEST
    )
    checks.extend(
        [
            present,
            parseable,
            check_sentinel(location.cell_dir),
            check_split_directories(location.cell_dir),
        ]
    )

    if manifest is None:
        return ScoreCellVerification(
            cell=location.cell,
            checks=checks,
            overall_status=evaluate_overall_status(checks),
        )

    fields_check = check_required_fields(manifest)
    checks.append(fields_check)

    if fields_check.status != AuditStatus.PASS:
        return ScoreCellVerification(
            cell=location.cell,
            expected_client_ids=list(manifest.expected_client_ids),
            expected_splits=[split for split in manifest.expected_splits],
            checks=checks,
            overall_status=evaluate_overall_status(checks),
        )

    expected_client_ids, expected_splits = append_full_manifest_checks(
        checks, manifest, location, location.cell_dir, base_dir, data_root
    )
    return ScoreCellVerification(
        cell=location.cell,
        expected_client_ids=expected_client_ids,
        expected_splits=expected_splits,
        checks=checks,
        overall_status=evaluate_overall_status(checks),
    )


def verify_score_cell(
    cell_dir: Path, base_dir: Path, *, data_root: Path | None = None
) -> ScoreCellVerification:
    cell_dir, base_dir = cell_dir.resolve(), base_dir.resolve()
    return verify_at_location(
        base_dir,
        (data_root or base_dir.parent).resolve(),
        parse_score_cell_dir(base_dir / ArtifactDir.SCORES, cell_dir),
    )


def verify_all_score_cells(
    base_dir: Path, *, data_root: Path | None = None, write_reports: bool = False
) -> list[ScoreCellVerification]:
    resolved_base = base_dir.resolve()
    resolved_data_root = (data_root or resolved_base.parent).resolve()

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(verify_at_location, resolved_base, resolved_data_root, loc)
            for loc in iter_score_cells(base_dir)
        ]
        results = [f.result() for f in futures]

    if write_reports:
        for loc, report in zip(iter_score_cells(base_dir), results):
            write_json_atomic(
                loc.cell_dir / AuditArtifact.SCORE_CELL_VERIFICATION,
                report.model_dump(mode="json"),
            )
        write_json_atomic(
            resolved_base
            / ArtifactDir.SCORES
            / AuditArtifact.SCORE_CELL_VERIFICATION_INDEX,
            {"cells": [r.model_dump(mode="json") for r in results]},
        )

    return results
