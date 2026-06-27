"""Score generation: model loading, reconstruction-errors, and per-client Parquet output."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
import torch

from datp.artifacts.io import write_json_atomic
from datp.artifacts.names import ArtifactFile, PathToken
from datp.config.models import DatpConfig
from datp.config.models import ExperimentStage
from datp.core.device import resolve_device
from datp.core.enums import SCORING_STAGES, ScoringStage
from datp.core.logging import get_logger
from datp.core.provenance import git_commit, hash_file, utc_timestamp
from datp.data.catalog import DatasetID
from datp.data.common.storage import write_artifact
from datp.federated.types import ClientData
from datp.modeling.autoencoder import Autoencoder
from datp.scoring.manifest import (
    SCORE_COLUMN,
    SCORING_MANIFEST_NOT_PROVIDED,
    ScoringColumnDtype,
    ScoringManifest,
    ScoringManifestContext,
    ScoringManifestStatus,
    ScoringRecord,
    resolve_within_score_base,
    validate_scoring_manifest,
)

logger = get_logger(__name__)
_MODULE = "scoring.generation"


def load_model_from_checkpoint(
    cfg: DatpConfig, *, ckpt_dir: Path, require_cuda: bool
) -> Autoencoder:
    """Load an Autoencoder from a checkpoint file on the resolved device."""
    ckpt_file = ckpt_dir / ArtifactFile.MODEL_CHECKPOINT
    if not ckpt_file.exists():
        raise FileNotFoundError(
            f"[{_MODULE}] Checkpoint missing. Expected: {str(ckpt_file)}. Got: missing file."
        )

    device = resolve_device(require_cuda)
    model = Autoencoder(
        input_dim=cfg.model.input_dim,
        hidden_dims=cfg.model.encoder_dims,
        activation=cfg.model.activation,
        use_bn=cfg.model.use_bn,
    )
    model.load_state_dict(torch.load(ckpt_file, map_location=device, weights_only=True))
    model.to(device)
    model.eval()
    logger.info("loaded checkpoint", path=str(ckpt_file), device=str(device))
    return model


def compute_reconstruction_errors(
    model: Autoencoder,
    data: torch.Tensor,
    batch_size: int | None = None,
) -> np.ndarray:
    """Compute reconstruction errors for a tensor in batches, returning a float32 array."""
    if data.shape[0] == 0:
        return np.array([], dtype=np.float32)

    effective_batch = batch_size or data.shape[0]
    model.eval()
    all_errors: list[np.ndarray] = []
    with torch.inference_mode():
        for start in range(0, data.shape[0], effective_batch):
            batch_errors = model.reconstruction_error(
                data[start : start + effective_batch]
            )
            all_errors.append(batch_errors.cpu().numpy().astype(np.float32))
    return np.concatenate(all_errors)


def _errors_to_dataframe(errors: np.ndarray) -> pl.DataFrame:
    return pl.DataFrame({SCORE_COLUMN: errors.astype(np.float32, copy=False)})


def _score_output_path(score_base: Path, stage: ScoringStage, client_id: str) -> Path:
    filename = f"{client_id}{PathToken.PARQUET_EXT}"
    if Path(filename).name != filename:
        raise ValueError(
            f"[{_MODULE}] Invalid client id for score artifact path. Expected: client id without path separators. Got: {client_id}."
        )
    out_path = score_base / stage.value / filename
    resolve_within_score_base(score_base, out_path)
    return out_path


def _score_record(
    path: Path,
    client_id: str,
    stage: ScoringStage,
    errors: np.ndarray,
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
        row_count=int(errors.size),
        columns=(SCORE_COLUMN,),
        dtypes=(ScoringColumnDtype(column=SCORE_COLUMN, dtype="Float32"),),
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
    client_id: str
    stage: ScoringStage
    score_base: Path
    batch_size: int


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
    write_artifact(_errors_to_dataframe(errors), out_path)
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
    client_data: Mapping[str, ClientData],
    *,
    score_base: Path,
    scoring_batch_size: int,
    get_model: Callable[[str], Autoencoder],
) -> list[ScoringRecord]:
    """Compute and persist per-client reconstruction errors across all scoring stages."""
    records: list[ScoringRecord] = []
    for client_id, splits in client_data.items():
        model = get_model(client_id)
        model.eval()
        model_device = next(model.parameters()).device
        for scoring_stage in SCORING_STAGES:
            records.append(
                _score_one_split(
                    _SplitScoringParams(
                        model=model,
                        model_device=model_device,
                        data=getattr(splits, scoring_stage.client_data_attr),
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
    client_ids: list[str],
    score_base: Path,
    ctx: ScoringManifestContext,
) -> None:
    """Write the scoring manifest JSON and DONE sentinel file."""
    manifest = ScoringManifest(
        dataset=str(ctx.dataset),
        stage=str(ctx.stage)
        if ctx.stage is not None
        else SCORING_MANIFEST_NOT_PROVIDED,
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
        expected_splits=tuple(s.value for s in SCORING_STAGES),
        actual_client_ids=tuple(sorted({record.client_id for record in records})),
        actual_splits=tuple(sorted({record.split.value for record in records})),
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
    """Score all client splits, persist Parquet files, and write the manifest."""
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
