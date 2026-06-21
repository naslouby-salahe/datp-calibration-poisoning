# SPDX-License-Identifier: Proprietary
"""Score artifacts have no baseline subdirectory — they are shared across threshold policies (GLOBAL, LOCAL, CLUSTER)."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar, cast

import numpy as np
import polars as pl
import torch

from datp.artifacts.io import write_json_atomic
from datp.artifacts.names import ArtifactFile, PathToken
from datp.core.device import resolve_device
from datp.config.stages import ExperimentStage
from datp.core.enums import (
    SCORING_STAGES,
    ScoringStage,
)
from datp.core.errors import fmt
from datp.core.logging import get_logger
from datp.core.provenance import git_commit, hash_file, utc_timestamp
from datp.data.catalog import DatasetID
from datp.data.common.storage import write_artifact
from datp.federated.types import ClientData
from datp.modeling.autoencoder import Autoencoder
from datp.scoring.schema import (
    SCORE_COLUMN,
    SCORING_MANIFEST_NOT_PROVIDED,
    SCORING_MANIFEST_SCHEMA_VERSION,
    ScoringManifestStatus,
)

if TYPE_CHECKING:
    from datp.config.models import DatpConfig

logger = get_logger(__name__)

_MODULE = "scoring.generation"
_SequenceItemT = TypeVar("_SequenceItemT")


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


def _resolve_within_base(base: Path, candidate: Path) -> Path:
    resolved_base = base.resolve()
    resolved_candidate = candidate.resolve()
    if not resolved_candidate.is_relative_to(resolved_base):
        raise ValueError(
            fmt(
                _MODULE,
                "Path escapes scoring directory",
                str(resolved_base),
                str(resolved_candidate),
            )
        )
    return resolved_candidate


def _score_output_path(score_base: Path, stage: ScoringStage, client_id: str) -> Path:
    filename = f"{client_id}{PathToken.PARQUET_EXT}"
    if Path(filename).name != filename:
        raise ValueError(
            fmt(
                _MODULE,
                "Invalid client id for score artifact path",
                "client id without path separators",
                client_id,
            )
        )
    out_path = Path(score_base) / stage.value / filename
    _resolve_within_base(Path(score_base), out_path)
    return out_path


def compute_reconstruction_errors(
    model: Autoencoder, data: torch.Tensor, batch_size: int | None = None
) -> np.ndarray:
    """Batched reconstruction-error computation. No gradients tracked.

    When *batch_size* is ``None`` the entire tensor is processed in one pass.
    """
    effective_batch = batch_size if batch_size is not None else data.shape[0]
    model.eval()
    n = data.shape[0]
    if n == 0:
        return np.array([], dtype=np.float32)
    all_errors: list[np.ndarray] = []
    with torch.inference_mode():
        for start in range(0, n, effective_batch):
            batch = data[start : start + effective_batch]
            errors = model.reconstruction_error(batch)
            all_errors.append(errors.cpu().numpy().astype(np.float32))
    return np.concatenate(all_errors)


def _errors_to_dataframe(errors: np.ndarray) -> pl.DataFrame:
    return pl.DataFrame([pl.Series(SCORE_COLUMN, errors)])


def _score_record(
    path: Path, client_id: str, stage: ScoringStage, errors: np.ndarray
) -> ScoringRecord:
    finite = errors[np.isfinite(errors)]
    return ScoringRecord(
        client_id=client_id,
        split=stage,
        path=str(path),
        row_count=int(errors.size),
        columns=(SCORE_COLUMN,),
        dtypes=(ScoringColumnDtype(column=SCORE_COLUMN, dtype="Float32"),),
        score_min=float(finite.min()) if finite.size else None,
        score_max=float(finite.max()) if finite.size else None,
        score_nan_count=int(np.isnan(errors).sum()),
        file_hash=hash_file(path),
    )


def _check_manifest_coverage(
    manifest: ScoringManifest,
    score_base: Path,
) -> ScoringManifestCoverage:
    """Return missing manifest entries and invalid or missing files."""
    expected = {
        (cid, split)
        for cid in manifest.expected_client_ids
        for split in manifest.expected_splits
    }
    actual = {(row.client_id, row.split.value) for row in manifest.records}
    missing = sorted(expected - actual)

    missing_files: list[str] = []
    invalid_files: list[str] = []
    for row in manifest.records:
        path = Path(row.path)
        try:
            resolved_path = _resolve_within_base(score_base, path)
        except ValueError:
            invalid_files.append(str(path))
            continue
        if not resolved_path.exists():
            missing_files.append(str(path))

    missing_files.sort()
    invalid_files.sort()
    return ScoringManifestCoverage(
        missing_pairs=tuple(missing),
        missing_files=tuple(missing_files),
        invalid_files=tuple(invalid_files),
    )


def _required(payload: Mapping[str, object], key: str) -> object:
    if key not in payload:
        raise KeyError(key)
    return payload[key]


def _required_text(payload: Mapping[str, object], key: str) -> str:
    return str(_required(payload, key))


def _required_int(payload: Mapping[str, object], key: str) -> int:
    value = _required(payload, key)
    if isinstance(value, bool):
        raise TypeError(f"{key} must be an integer, not bool")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise TypeError(f"{key} must be convertible to int")


def _sequence(
    value: object, item_type: type[_SequenceItemT]
) -> tuple[_SequenceItemT, ...]:
    if isinstance(value, (str, bytes)):
        raise TypeError("expected a sequence, not text")
    if not isinstance(value, Sequence):
        raise TypeError("expected a sequence")
    if not all(isinstance(item, item_type) for item in value):
        raise TypeError(f"expected a sequence of {item_type.__name__}")
    return tuple(value)


def _required_sequence(
    payload: Mapping[str, object], key: str, item_type: type[_SequenceItemT]
) -> tuple[_SequenceItemT, ...]:
    return _sequence(_required(payload, key), item_type)


def _optional_sequence(
    payload: Mapping[str, object], key: str, item_type: type[_SequenceItemT]
) -> tuple[_SequenceItemT, ...]:
    return _sequence(payload.get(key, ()), item_type)


def _optional_text(payload: Mapping[str, object], key: str) -> str:
    return str(payload.get(key, SCORING_MANIFEST_NOT_PROVIDED))


def _optional_int(payload: Mapping[str, object], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    return _required_int(payload, key)


def _optional_float(payload: Mapping[str, object], key: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError(f"{key} must be numeric, not bool")
    if isinstance(value, (int, float, str)):
        return float(value)
    raise TypeError(f"{key} must be convertible to float")


def _text_tuple(payload: Mapping[str, object], key: str) -> tuple[str, ...]:
    return tuple(str(item) for item in _required_sequence(payload, key, object))


def _dtype_entries(raw: object) -> tuple[ScoringColumnDtype, ...]:
    if isinstance(raw, Mapping):
        return tuple(
            ScoringColumnDtype(column=str(column), dtype=str(dtype))
            for column, dtype in raw.items()
        )
    rows = _sequence(raw, Mapping)
    return tuple(
        ScoringColumnDtype(
            column=_required_text(row, "column"),
            dtype=_required_text(row, "dtype"),
        )
        for row in rows
    )


def _record_from_payload(payload: Mapping[str, object]) -> ScoringRecord:
    return ScoringRecord(
        client_id=_required_text(payload, "client_id"),
        split=ScoringStage(_required_text(payload, "split")),
        path=_required_text(payload, "path"),
        row_count=_required_int(payload, "row_count"),
        columns=_text_tuple(payload, "columns"),
        dtypes=_dtype_entries(_required(payload, "dtypes")),
        score_min=_optional_float(payload, "score_min"),
        score_max=_optional_float(payload, "score_max"),
        score_nan_count=_required_int(payload, "score_nan_count"),
        file_hash=_required_text(payload, "file_hash"),
    )


def _manifest_from_payload(payload: Mapping[str, object]) -> ScoringManifest:
    records = tuple(
        _record_from_payload(row)
        for row in _required_sequence(payload, "records", Mapping)
    )
    return ScoringManifest(
        schema_version=_required_text(payload, "schema_version"),
        dataset=str(payload.get("dataset", SCORING_MANIFEST_NOT_PROVIDED)),
        stage=str(payload.get("stage", SCORING_MANIFEST_NOT_PROVIDED)),
        seed=_optional_int(payload, "seed"),
        model_checkpoint_path=_optional_text(payload, "model_checkpoint_path"),
        model_checkpoint_hash=_optional_text(payload, "model_checkpoint_hash"),
        checkpoint_round=_optional_int(payload, "checkpoint_round"),
        scoring_code_version=_optional_text(payload, "scoring_code_version"),
        score_column_name=str(payload.get("score_column_name", SCORE_COLUMN)),
        expected_client_ids=_text_tuple(payload, "expected_client_ids"),
        expected_splits=_text_tuple(payload, "expected_splits"),
        actual_client_ids=tuple(
            str(item)
            for item in _optional_sequence(payload, "actual_client_ids", object)
        ),
        actual_splits=tuple(
            str(item) for item in _optional_sequence(payload, "actual_splits", object)
        ),
        records=records,
        completion_status=_required_text(payload, "completion_status"),
        generated_at_utc=_optional_text(payload, "generated_at_utc"),
    )


def validate_scoring_manifest(score_base: Path) -> ScoringManifest:
    score_base = Path(score_base)
    manifest_path = score_base / ArtifactFile.SCORING_MANIFEST
    if not manifest_path.exists():
        raise FileNotFoundError(
            fmt(_MODULE, "Scoring manifest missing", str(manifest_path), "missing file")
        )
    manifest = _manifest_from_payload(
        cast(
            Mapping[str, object], json.loads(manifest_path.read_text(encoding="utf-8"))
        )
    )
    coverage = _check_manifest_coverage(manifest, score_base)
    if (
        manifest.completion_status != ScoringManifestStatus.COMPLETE
        or coverage.missing_pairs
        or coverage.missing_files
        or coverage.invalid_files
    ):
        raise ValueError(
            fmt(
                _MODULE,
                "Scoring manifest incomplete",
                "complete manifest with all expected score files",
                f"status={manifest.completion_status}, missing={coverage.missing_pairs}, missing_files={coverage.missing_files}, invalid_files={coverage.invalid_files}",
            )
        )
    return manifest


def _score_clients_impl(
    client_data: Mapping[str, ClientData],
    *,
    score_base: Path,
    scoring_batch_size: int,
    get_model: Callable[[str], Autoencoder],
) -> list[ScoringRecord]:
    """Shared scoring loop: score each client × ScoringStage and write parquet artifacts."""
    records: list[ScoringRecord] = []
    for cid, splits in client_data.items():
        model = get_model(cid)
        model.eval()
        model_device = next(model.parameters()).device
        for stage in SCORING_STAGES:
            records.append(
                _score_one_split(
                    model,
                    model_device,
                    getattr(splits, stage.client_data_attr),
                    cid,
                    stage,
                    score_base,
                    scoring_batch_size,
                )
            )
    return records


def _score_one_split(
    model: Autoencoder,
    model_device: torch.device,
    data: torch.Tensor,
    cid: str,
    stage: ScoringStage,
    score_base: Path,
    batch_size: int,
) -> ScoringRecord:
    if data.device != model_device:
        data = data.to(model_device, non_blocking=True)
    errors = compute_reconstruction_errors(model, data, batch_size=batch_size)
    out_path = _score_output_path(score_base, stage, cid)
    write_artifact(_errors_to_dataframe(errors), out_path)
    logger.debug(
        "wrote scores",
        n_scores=len(errors),
        path=str(out_path),
        client=cid,
        stage=stage,
    )
    return _score_record(out_path, cid, stage, errors)


@dataclass(frozen=True, slots=True)
class ScoringManifestContext:
    """Bundled metadata written into the scoring manifest."""

    dataset: DatasetID
    stage: ExperimentStage | None
    seed: int | None
    checkpoint_path: Path | None
    checkpoint_round: int | None


def _write_scoring_manifest_and_sentinel(
    records: list[ScoringRecord],
    client_ids: list[str],
    score_base: Path,
    ctx: ScoringManifestContext,
) -> None:
    """Write manifest + sentinel for scoring results."""
    manifest = ScoringManifest(
        schema_version=SCORING_MANIFEST_SCHEMA_VERSION,
        dataset=ctx.dataset,
        stage=ctx.stage if ctx.stage is not None else SCORING_MANIFEST_NOT_PROVIDED,
        seed=ctx.seed,
        model_checkpoint_path=str(ctx.checkpoint_path)
        if ctx.checkpoint_path is not None
        else SCORING_MANIFEST_NOT_PROVIDED,
        model_checkpoint_hash=hash_file(ctx.checkpoint_path)
        if ctx.checkpoint_path is not None
        else SCORING_MANIFEST_NOT_PROVIDED,
        checkpoint_round=ctx.checkpoint_round,
        scoring_code_version=git_commit(),
        score_column_name=SCORE_COLUMN,
        expected_client_ids=tuple(sorted(client_ids)),
        expected_splits=tuple(stage.value for stage in SCORING_STAGES),
        actual_client_ids=tuple(sorted({record.client_id for record in records})),
        actual_splits=tuple(sorted({record.split.value for record in records})),
        records=tuple(records),
        completion_status=ScoringManifestStatus.COMPLETE,
        generated_at_utc=utc_timestamp(),
    )
    write_json_atomic(score_base / ArtifactFile.SCORING_MANIFEST, manifest)
    validate_scoring_manifest(score_base)

    sentinel = score_base / ArtifactFile.SCORING_SENTINEL
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text(f"Scoring complete: {len(client_ids)} clients.\n")


def score_clients(
    model: Autoencoder,
    client_data: Mapping[str, ClientData],
    *,
    score_base: Path,
    stage: ExperimentStage | None,
    seed: int | None,
    dataset: DatasetID,
    checkpoint_path: Path | None,
    checkpoint_round: int | None,
    scoring_batch_size: int,
) -> None:
    model.eval()
    n_clients = len(client_data)
    logger.info("scoring clients", n_clients=n_clients, score_base=str(score_base))

    records = _score_clients_impl(
        client_data,
        score_base=score_base,
        scoring_batch_size=scoring_batch_size,
        get_model=lambda _cid: model,
    )

    _write_scoring_manifest_and_sentinel(
        records,
        sorted(client_data.keys()),
        score_base,
        ScoringManifestContext(
            dataset=dataset,
            stage=stage,
            seed=seed,
            checkpoint_path=checkpoint_path,
            checkpoint_round=checkpoint_round,
        ),
    )
    logger.info("scoring complete", score_base=str(score_base))


def load_model_from_checkpoint(
    cfg: "DatpConfig",
    *,
    ckpt_dir: Path,
    require_cuda: bool,
) -> Autoencoder:
    ckpt_file = ckpt_dir / ArtifactFile.MODEL_CHECKPOINT
    if not ckpt_file.exists():
        raise FileNotFoundError(
            fmt(_MODULE, "Checkpoint missing", str(ckpt_file), "missing file")
        )

    model = Autoencoder(
        input_dim=cfg.model.input_dim,
        hidden_dims=cfg.model.encoder_dims,
        activation=cfg.model.activation,
        use_bn=cfg.model.use_bn,
    )
    device = resolve_device(require_cuda)
    state_dict = torch.load(ckpt_file, map_location=device, weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    logger.info("loaded checkpoint", path=str(ckpt_file), device=str(device))
    return model
