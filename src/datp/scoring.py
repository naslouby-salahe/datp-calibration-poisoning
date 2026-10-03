from __future__ import annotations

import enum
import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
import torch
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from datp.artifacts import ArtifactLayout, write_json_atomic
from datp.config import ExperimentStage
from datp.core import TrainingCellId, get_logger, git_commit, hash_file, utc_timestamp
from datp.data import ClientData, write_artifact
from datp.enums import (
    SCORING_STAGES,
    ArtifactFile,
    ClientDataAttribute,
    DatasetID,
    PathToken,
    ScoringStage,
)
from datp.modeling import Autoencoder
from datp.types import (
    ArtifactName,
    BatchSize,
    ClientId,
    ContentHash,
    JsonValue,
    NarrativeText,
    RandomSeed,
    SampleCount,
    SchemaVersion,
    ScoreValue,
    ScoreVector,
)

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
    model_hash: ContentHash
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
    model_hash: ContentHash | ScoringManifestSentinel = ScoringManifestSentinel.NOT_PROVIDED
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
    model_hash: ContentHash


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


logger = get_logger(__name__)


_MODULE_generation = "scoring.generation"


def hash_model_state(model: Autoencoder) -> ContentHash:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def compute_reconstruction_errors(
    model: Autoencoder,
    data: torch.Tensor,
    batch_size: BatchSize | None = None,
) -> ScoreVector:
    if data.shape[0] == 0:
        return np.array([], dtype=np.float32)

    effective_batch = batch_size or data.shape[0]
    model.eval()
    all_errors: list[ScoreVector] = []
    with torch.inference_mode():
        for start in range(0, data.shape[0], effective_batch):
            batch_errors = model.reconstruction_error(
                data[start : start + effective_batch]
            )
            all_errors.append(batch_errors.cpu().numpy().astype(np.float32))
    return np.concatenate(all_errors)


def _score_output_path(
    score_base: Path, stage: ScoringStage, client_id: ClientId
) -> Path:
    filename = f"{client_id}{PathToken.PARQUET_EXT}"
    if Path(filename).name != filename:
        raise ValueError(
            f"[{_MODULE_generation}] Invalid client id for score artifact path. Expected: client id without path separators. Got: {client_id}."
        )
    out_path = score_base / stage / filename
    resolve_within_score_base(score_base, out_path)
    return out_path


def _score_record(
    path: Path,
    client_id: ClientId,
    stage: ScoringStage,
    errors: ScoreVector,
    *,
    score_base: Path | None = None,
) -> ScoringRecord:
    finite = errors[np.isfinite(errors)]
    record_path = (
        str(path.relative_to(score_base)) if score_base is not None else str(path)
    )
    return ScoringRecord(
        client_id=client_id,
        split=stage,
        path=record_path,
        row_count=errors.size,
        columns=(ScoringColumn.RECONSTRUCTION_ERROR,),
        dtypes=(ScoringColumnDtype(column=ScoringColumn.RECONSTRUCTION_ERROR, dtype="Float32"),),
        score_min=float(finite.min()) if finite.size else None,
        score_max=float(finite.max()) if finite.size else None,
        score_nan_count=int(np.isnan(errors).sum()),
        file_hash=hash_file(path),
    )


@dataclass(frozen=True, slots=True)
class _SplitScoringParams:
    model: Autoencoder
    model_device: torch.device
    data: torch.Tensor
    client_id: ClientId
    stage: ScoringStage
    score_base: Path
    batch_size: BatchSize


def _score_one_split(params: _SplitScoringParams) -> ScoringRecord:
    data = (
        params.data.to(params.model_device, non_blocking=True)
        if params.data.device != params.model_device
        else params.data
    )
    errors = compute_reconstruction_errors(
        params.model,
        data,
        batch_size=params.batch_size,
    )
    out_path = _score_output_path(params.score_base, params.stage, params.client_id)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_artifact(
        pl.DataFrame({ScoringColumn.RECONSTRUCTION_ERROR: errors.astype(np.float32, copy=False)}), out_path
    )
    logger.debug(
        "wrote scores",
        n_scores=len(errors),
        path=str(out_path),
        client=params.client_id,
        stage=params.stage,
    )
    return _score_record(
        out_path,
        params.client_id,
        params.stage,
        errors,
        score_base=params.score_base,
    )


def score_clients_impl(
    client_data: Mapping[ClientId, ClientData],
    *,
    score_base: Path,
    scoring_batch_size: BatchSize,
    get_model: Callable[[ClientId], Autoencoder],
) -> list[ScoringRecord]:
    records: list[ScoringRecord] = []
    scoring_stages: tuple[ScoringStage, ...] = SCORING_STAGES
    for client_key, splits in client_data.items():
        client_id = ClientId(client_key)
        model = get_model(client_id)
        model.eval()
        model_device = next(model.parameters()).device
        for scoring_stage in scoring_stages:
            data = (
                splits.val
                if scoring_stage.client_data_attr is ClientDataAttribute.VAL
                else splits.test_benign
                if scoring_stage.client_data_attr is ClientDataAttribute.TEST_BENIGN
                else splits.test_attack
            )
            records.append(
                _score_one_split(
                    _SplitScoringParams(
                        model=model,
                        model_device=model_device,
                        data=data,
                        client_id=client_id,
                        stage=scoring_stage,
                        score_base=score_base,
                        batch_size=scoring_batch_size,
                    )
                )
            )
    return records


def write_scoring_manifest_and_sentinel(
    records: list[ScoringRecord],
    client_ids: list[ClientId],
    score_base: Path,
    ctx: ScoringManifestContext,
) -> None:
    manifest = ScoringManifest(
        dataset=ctx.dataset,
        stage=ctx.stage,
        seed=ctx.seed,
        model_hash=ctx.model_hash,
        scoring_code_version=git_commit(),
        score_column_name=ScoringColumn.RECONSTRUCTION_ERROR,
        expected_client_ids=tuple(sorted(client_ids)),
        expected_splits=SCORING_STAGES,
        actual_client_ids=tuple(sorted({record.client_id for record in records})),
        actual_splits=tuple(sorted({record.split for record in records})),
        records=tuple(records),
        completion_status=ScoringManifestStatus.COMPLETE,
        generated_at_utc=utc_timestamp(),
    )

    write_json_atomic(
        score_base / ArtifactFile.SCORING_MANIFEST, manifest.model_dump(mode="json")
    )
    validate_scoring_manifest(score_base)

    sentinel = score_base / ArtifactFile.SCORING_SENTINEL
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text(f"Scoring complete: {len(client_ids)} clients.\n")


def score_clients(
    model: Autoencoder,
    client_data: Mapping[ClientId, ClientData],
    *,
    score_base: Path,
    stage: ExperimentStage | None,
    seed: RandomSeed | None,
    dataset: DatasetID,
    scoring_batch_size: BatchSize,
) -> None:
    model.eval()
    logger.info(
        "scoring clients", n_clients=len(client_data), score_base=str(score_base)
    )
    records = score_clients_impl(
        client_data,
        score_base=score_base,
        scoring_batch_size=scoring_batch_size,
        get_model=lambda _client_id: model,
    )
    write_scoring_manifest_and_sentinel(
        records,
        [ClientId(client_id) for client_id in sorted(client_data)],
        score_base,
        ScoringManifestContext(
            dataset=dataset,
            stage=stage,
            seed=seed,
            model_hash=hash_model_state(model),
        ),
    )
    logger.info("scoring complete", score_base=str(score_base))


_MODULE_loading = "scoring.loading"


def read_score_column(path: Path) -> ScoreVector:
    validate_score_artifact(path)
    return pl.read_parquet(path).get_column(ScoringColumn.RECONSTRUCTION_ERROR).to_numpy().astype(np.float64)


def load_parquets_from_dir(
    directory: Path, *, allow_empty: bool = True
) -> dict[ClientId, ScoreVector]:
    if not directory.is_dir():
        raise FileNotFoundError(f"[{_MODULE_loading}] score directory {directory} not found.")

    parquets = {
        ClientId(pf.stem): read_score_column(pf)
        for pf in sorted(directory.glob(PathToken.PARQUET_GLOB))
    }
    if not allow_empty and not parquets:
        raise FileNotFoundError(
            f"[{_MODULE_loading}] No parquet score artifacts at {directory}. Expected: at least one .parquet score artifact. Got: none."
        )

    return parquets


def load_main_cal_errors(
    stage: ExperimentStage, seed: RandomSeed, base_dir: Path
) -> dict[ClientId, ScoreVector]:
    cell = TrainingCellId(stage=stage, seed=RandomSeed(seed))
    layout = ArtifactLayout(base_dir=base_dir, stage=stage)
    calibration_dir = layout.score_cell(cell).score_dir / ScoringStage.CAL
    if not calibration_dir.is_dir():
        raise FileNotFoundError(
            f"[{_MODULE_loading}] score directory {calibration_dir} not found."
        )
    score_files = sorted(calibration_dir.glob(PathToken.PARQUET_GLOB))
    if not score_files:
        raise FileNotFoundError(
            f"[{_MODULE_loading}] No parquet score artifacts at {calibration_dir}. Expected: at least one .parquet score artifact. Got: none."
        )
    return {
        client_id: read_score_column(
            layout.score_file(cell, ScoringStage.CAL, client_id)
        )
        for score_file in score_files
        if (client_id := ClientId(score_file.stem))
    }


class ScoreProvider:

    def __init__(self, score_root: Path) -> None:
        self.score_root = score_root

    def load(self, client_id: ClientId, stage: ScoringStage) -> ScoreVector:
        path = self.score_root / stage / f"{client_id}{PathToken.PARQUET_EXT}"
        if not path.exists():
            raise FileNotFoundError(
                f"[{_MODULE_loading}] Missing {stage} score artifact for client '{client_id}'. Expected: {path}. Got: absent."
            )
        return read_score_column(path)

    def load_test_scores(self, client_id: ClientId) -> tuple[ScoreVector, ScoreVector]:
        return self.load(client_id, ScoringStage.TEST_BENIGN), self.load(
            client_id, ScoringStage.TEST_ATTACK
        )


def validate_score_artifact(path: Path) -> None:
    schema = pl.read_parquet_schema(path)
    if list(schema.keys()) != [ScoringColumn.RECONSTRUCTION_ERROR]:
        raise ValueError(
            f"[{_MODULE_loading}] Schema mismatch at {path}. Expected: columns: [{ScoringColumn.RECONSTRUCTION_ERROR}]. Got: columns: {list(schema.keys())}."
        )

    if not schema[ScoringColumn.RECONSTRUCTION_ERROR].is_float():
        raise TypeError(
                f"[{_MODULE_loading}] Column '{ScoringColumn.RECONSTRUCTION_ERROR}' has non-floating type. Expected: floating. Got: {schema[ScoringColumn.RECONSTRUCTION_ERROR]}."
        )
