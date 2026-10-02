from datp.types import (
    ArtifactName,
    ClientId,
    ContentHash,
    JsonValue,
    NarrativeText,
    RandomSeed,
    RoundIndex,
    SampleCount,
    SchemaVersion,
    ScoreValue,
)

import enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from datp.artifacts.names import ArtifactFile
from datp.config.models import ExperimentStage
from datp.core.enums import ScoringStage
from datp.data.catalog import DatasetID

_MODULE = "scoring.manifest"


class ScoringColumn(enum.StrEnum):

    RECONSTRUCTION_ERROR = "reconstruction_error"


class ScoringManifestField(enum.StrEnum):

    COMPLETION_STATUS = "completion_status"


class ScoringManifestSentinel(enum.StrEnum):

    NOT_PROVIDED = "NOT_PROVIDED"


class ScoringManifestStatus(enum.StrEnum):

    COMPLETE = "complete"
    PARTIAL = "partial"


class ScoringManifestIdentityFields(BaseModel):

    model_config = ConfigDict(extra="ignore", frozen=True, strict=True)

    checkpoint_round: RoundIndex
    model_checkpoint_hash: ContentHash
    expected_client_ids: tuple[ClientId, ...]
    expected_splits: tuple[ScoringStage, ...]


class ScoringColumnDtype(BaseModel):

    column: ScoringColumn
    dtype: NarrativeText


class ScoringRecord(BaseModel):

    client_id: ClientId
    split: ScoringStage
    path: ArtifactName
    row_count: SampleCount
    columns: tuple[ScoringColumn, ...]
    dtypes: tuple[ScoringColumnDtype, ...]
    score_min: ScoreValue | None
    score_max: ScoreValue | None
    score_nan_count: SampleCount
    file_hash: ContentHash

    @field_validator("dtypes", mode="before")
    @classmethod
    def _parse_dtypes(cls, value: JsonValue) -> JsonValue:
        if isinstance(value, dict):
            return [
                {"column": column, "dtype": dtype}
                for column, dtype in value.items()
            ]
        return value


class ScoringManifest(BaseModel):

    dataset: DatasetID
    stage: ExperimentStage | None
    seed: RandomSeed | None = None
    model_checkpoint_path: ArtifactName | ScoringManifestSentinel = ScoringManifestSentinel.NOT_PROVIDED
    model_checkpoint_hash: ContentHash | ScoringManifestSentinel = ScoringManifestSentinel.NOT_PROVIDED
    checkpoint_round: RoundIndex | None = None
    scoring_code_version: SchemaVersion | ScoringManifestSentinel = ScoringManifestSentinel.NOT_PROVIDED
    score_column_name: ScoringColumn = ScoringColumn.RECONSTRUCTION_ERROR
    expected_client_ids: tuple[ClientId, ...]
    expected_splits: tuple[ScoringStage, ...]
    actual_client_ids: tuple[ClientId, ...]
    actual_splits: tuple[ScoringStage, ...]
    records: tuple[ScoringRecord, ...]
    completion_status: ScoringManifestStatus
    generated_at_utc: NarrativeText | None = None


class ScoringManifestAuditRecord(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    client_id: ClientId
    split: ScoringStage


class ScoringManifestAuditView(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    dataset: DatasetID | None = None
    stage: ExperimentStage | None = None
    seed: RandomSeed | None = None
    model_checkpoint_path: ArtifactName | ScoringManifestSentinel = ScoringManifestSentinel.NOT_PROVIDED
    model_checkpoint_hash: ContentHash | ScoringManifestSentinel = ScoringManifestSentinel.NOT_PROVIDED
    expected_client_ids: tuple[ClientId, ...] = ()
    expected_splits: tuple[ScoringStage, ...] = ()
    actual_client_ids: tuple[ClientId, ...] = ()
    actual_splits: tuple[ScoringStage, ...] = ()
    score_column_name: ScoringColumn = ScoringColumn.RECONSTRUCTION_ERROR
    records: tuple[ScoringManifestAuditRecord, ...] = ()
    completion_status: ScoringManifestStatus | None = None


class ScoringManifestContext(BaseModel):

    dataset: DatasetID
    stage: ExperimentStage | None = None
    seed: RandomSeed | None = None
    checkpoint_path: Path | None = None
    checkpoint_round: RoundIndex | None = None


class ScoringManifestCoverage(BaseModel):

    missing_pairs: tuple[tuple[ClientId, ScoringStage], ...]
    missing_files: tuple[ArtifactName, ...]
    invalid_files: tuple[ArtifactName, ...]


def resolve_within_score_base(score_base: Path, candidate: Path) -> Path:
    resolved_base = score_base.resolve()
    resolved_candidate = (
        candidate.resolve()
        if candidate.is_absolute()
        else (score_base / candidate).resolve()
    )
    if not resolved_candidate.is_relative_to(resolved_base):
        raise ValueError(
            f"[{_MODULE}] Path escapes scoring directory. Expected: {resolved_base}. Got: {resolved_candidate}."
        )
    return resolved_candidate


def check_manifest_coverage(
    manifest: ScoringManifest,
    score_base: Path,
) -> ScoringManifestCoverage:
    expected_pairs = {
        (client_id, split)
        for client_id in manifest.expected_client_ids
        for split in manifest.expected_splits
    }
    actual_pairs = {
        (record.client_id, record.split) for record in manifest.records
    }
    missing_pairs = tuple(sorted(expected_pairs - actual_pairs))

    missing_files: list[ArtifactName] = []
    invalid_files: list[ArtifactName] = []
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
    score_base = Path(score_base)
    manifest_path = score_base / ArtifactFile.SCORING_MANIFEST
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"[{_MODULE}] Scoring manifest missing. Expected: {manifest_path}. Got: missing file."
        )

    try:
        manifest = ScoringManifest.model_validate_json(manifest_path.read_text())
    except ValidationError as error:
        if any(
            item["loc"] == (ScoringManifestField.COMPLETION_STATUS,)
            for item in error.errors()
        ):
            raise ValueError(
                f"[{_MODULE}] Scoring manifest incomplete. Expected: completion_status={ScoringManifestStatus.COMPLETE}. Got: invalid status."
            ) from error
        raise
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
