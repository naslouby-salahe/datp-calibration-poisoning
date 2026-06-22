from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datp.config.stages import ExperimentStage
from datp.core.enums import ScoringStage
from datp.data.catalog import DatasetID
from datp.scoring.schema import ScoringManifestStatus


@dataclass(frozen=True, slots=True)
class ScoringColumnDtype:
    column: str
    dtype: str


@dataclass(frozen=True, slots=True)
class ScoringRecord:
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


@dataclass(frozen=True, slots=True)
class ScoringManifest:
    schema_version: str
    dataset: DatasetID | str
    stage: ExperimentStage | str
    seed: int | None
    model_checkpoint_path: str
    model_checkpoint_hash: str
    checkpoint_round: int | None
    scoring_code_version: str
    score_column_name: str
    expected_client_ids: tuple[str, ...]
    expected_splits: tuple[str, ...]
    actual_client_ids: tuple[str, ...]
    actual_splits: tuple[str, ...]
    records: tuple[ScoringRecord, ...]
    completion_status: ScoringManifestStatus | str
    generated_at_utc: str


@dataclass(frozen=True, slots=True)
class ScoringManifestCoverage:
    missing_pairs: tuple[tuple[str, str], ...]
    missing_files: tuple[str, ...]
    invalid_files: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScoringManifestContext:
    """Bundled metadata written into the scoring manifest."""

    dataset: DatasetID
    stage: ExperimentStage | None
    seed: int | None
    checkpoint_path: Path | None
    checkpoint_round: int | None
