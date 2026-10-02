from datp.types import (
    BatchSize,
    ClientId,
    RandomSeed,
    RoundIndex,
    ScoreVector,
)

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
from datp.core.enums import ClientDataAttribute, SCORING_STAGES, ScoringStage
from datp.core.logging import get_logger
from datp.core.provenance import git_commit, hash_file, utc_timestamp
from datp.data.catalog import DatasetID
from datp.data.common.storage import write_artifact
from datp.federated.types import ClientData
from datp.modeling.autoencoder import Autoencoder
from datp.scoring.manifest import (
    ScoringColumnDtype,
    ScoringColumn,
    ScoringManifest,
    ScoringManifestContext,
    ScoringManifestSentinel,
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
    ckpt_file = ckpt_dir / ArtifactFile.MODEL_CHECKPOINT
    if not ckpt_file.exists():
        raise FileNotFoundError(
            f"[{_MODULE}] Checkpoint missing. Expected: {ckpt_file}. Got: missing file."
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
            f"[{_MODULE}] Invalid client id for score artifact path. Expected: client id without path separators. Got: {client_id}."
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
        model_checkpoint_path=str(ctx.checkpoint_path)
        if ctx.checkpoint_path is not None
        else ScoringManifestSentinel.NOT_PROVIDED,
        model_checkpoint_hash=hash_file(ctx.checkpoint_path)
        if ctx.checkpoint_path is not None
        else ScoringManifestSentinel.NOT_PROVIDED,
        checkpoint_round=ctx.checkpoint_round,
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
    checkpoint_path: Path | None,
    checkpoint_round: RoundIndex | None,
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
            checkpoint_path=checkpoint_path,
            checkpoint_round=checkpoint_round,
        ),
    )
    logger.info("scoring complete", score_base=str(score_base))
