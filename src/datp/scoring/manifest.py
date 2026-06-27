"""Scoring manifest model, coverage checks, and validation entry-point."""

import enum
from pathlib import Path

from pydantic import BaseModel, field_validator

from datp.artifacts.names import ArtifactFile
from datp.config.models import ExperimentStage
from datp.core.enums import ScoringStage
from datp.data.catalog import DatasetID

SCORE_COLUMN: str = "reconstruction_error"
SCORING_MANIFEST_SCHEMA_VERSION: str = "1"
SCORING_MANIFEST_NOT_PROVIDED: str = "NOT_PROVIDED"
_MODULE = "scoring.manifest"


class ScoringManifestStatus(enum.StrEnum):
    """Completion status values for a scoring manifest."""

    COMPLETE = "complete"


class ScoringColumnDtype(BaseModel):
    """Column name and its dtype string for a score artifact."""

    column: str
    dtype: str


class ScoringRecord(BaseModel):
    """Metadata and summary statistics for a single client/split score Parquet file."""

    client_id: str
    split: ScoringStage
    path: str
    row_count: int
    columns: tuple[str, ...]
    dtypes: tuple[ScoringColumnDtype, ...]
    score_min: float | None
    score_max: float | None
    score_nan_count: int
    file_hash: str

    @field_validator("dtypes", mode="before")
    @classmethod
    def _parse_dtypes(cls, value: object) -> object:
        if isinstance(value, dict):
            return [
                {"column": str(column), "dtype": str(dtype)}
                for column, dtype in value.items()
            ]
        return value


class ScoringManifest(BaseModel):
    """Top-level manifest describing a complete set of score artifacts for one experiment."""

    dataset: str
    stage: str
    seed: int | None = None
    model_checkpoint_path: str = SCORING_MANIFEST_NOT_PROVIDED
    model_checkpoint_hash: str = SCORING_MANIFEST_NOT_PROVIDED
    checkpoint_round: int | None = None
    scoring_code_version: str = SCORING_MANIFEST_NOT_PROVIDED
    score_column_name: str = SCORE_COLUMN
    expected_client_ids: tuple[str, ...]
    expected_splits: tuple[str, ...]
    actual_client_ids: tuple[str, ...]
    actual_splits: tuple[str, ...]
    records: tuple[ScoringRecord, ...]
    completion_status: ScoringManifestStatus | str
    generated_at_utc: str | None = None


class ScoringManifestContext(BaseModel):
    """Contextual metadata used to locate or validate a scoring manifest."""

    dataset: DatasetID
    stage: ExperimentStage | None = None
    seed: int | None = None
    checkpoint_path: Path | None = None
    checkpoint_round: int | None = None


class ScoringManifestCoverage(BaseModel):
    """Coverage report listing missing or invalid score files against a manifest."""

    missing_pairs: tuple[tuple[str, str], ...]
    missing_files: tuple[str, ...]
    invalid_files: tuple[str, ...]


def resolve_within_score_base(score_base: Path, candidate: Path) -> Path:
    """Resolve a candidate path safely within the scoring base directory."""
    resolved_base = score_base.resolve()
    resolved_candidate = (
        candidate.resolve()
        if candidate.is_absolute()
        else (score_base / candidate).resolve()
    )
    if not resolved_candidate.is_relative_to(resolved_base):
        raise ValueError(
            f"[{_MODULE}] Path escapes scoring directory. Expected: {str(resolved_base)}. Got: {str(resolved_candidate)}."
        )
    return resolved_candidate


def check_manifest_coverage(
    manifest: ScoringManifest,
    score_base: Path,
) -> ScoringManifestCoverage:
    """Cross-check expected client/split pairs against actual manifest records and file presence."""
    expected_pairs = {
        (client_id, split)
        for client_id in manifest.expected_client_ids
        for split in manifest.expected_splits
    }
    actual_pairs = {
        (record.client_id, record.split.value) for record in manifest.records
    }
    missing_pairs = tuple(sorted(expected_pairs - actual_pairs))

    missing_files: list[str] = []
    invalid_files: list[str] = []
    for record in manifest.records:
        record_path = Path(record.path)
        try:
            resolved_path = resolve_within_score_base(score_base, record_path)
        except ValueError:
            invalid_files.append(str(record_path))
            continue
        if not resolved_path.exists():
            missing_files.append(str(record_path))

    return ScoringManifestCoverage(
        missing_pairs=missing_pairs,
        missing_files=tuple(sorted(missing_files)),
        invalid_files=tuple(sorted(invalid_files)),
    )


def validate_scoring_manifest(score_base: Path) -> ScoringManifest:
    """Load, validate coverage, and return the scoring manifest at the given base path."""
    score_base = Path(score_base)
    manifest_path = score_base / ArtifactFile.SCORING_MANIFEST
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"[{_MODULE}] Scoring manifest missing. Expected: {str(manifest_path)}. Got: missing file."
        )

    manifest = ScoringManifest.model_validate_json(manifest_path.read_text())
    coverage = check_manifest_coverage(manifest, score_base)
    if (
        manifest.completion_status != ScoringManifestStatus.COMPLETE
        or coverage.missing_pairs
        or coverage.missing_files
        or coverage.invalid_files
    ):
        raise ValueError(
            f"[{_MODULE}] Scoring manifest incomplete. Expected: complete manifest with all expected score files. Got: status={manifest.completion_status}, missing={coverage.missing_pairs}, missing_files={coverage.missing_files}, invalid_files={coverage.invalid_files}."
        )
    return manifest
