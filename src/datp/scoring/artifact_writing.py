from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl
import torch

from datp.artifacts.io import write_json_atomic
from datp.artifacts.names import ArtifactFile
from datp.config.stages import ExperimentStage
from datp.core.enums import SCORING_STAGES, ScoringStage
from datp.core.logging import get_logger
from datp.core.provenance import git_commit, hash_file, utc_timestamp
from datp.data.catalog import DatasetID
from datp.data.common.storage import write_artifact
from datp.federated.types import ClientData
from datp.modeling.autoencoder import Autoencoder
from datp.scoring.manifest import (
    ScoringColumnDtype,
    ScoringManifest,
    ScoringManifestContext,
    ScoringRecord,
)
from datp.scoring.manifest_validation import validate_scoring_manifest
from datp.scoring.paths import score_output_path
from datp.scoring.reconstruction import compute_reconstruction_errors
from datp.scoring.schema import (
    SCORE_COLUMN,
    SCORING_MANIFEST_NOT_PROVIDED,
    SCORING_MANIFEST_SCHEMA_VERSION,
    ScoringManifestStatus,
)

logger = get_logger(__name__)


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


@dataclass(frozen=True, slots=True)
class _SplitScoringParams:
    model: Autoencoder
    model_device: torch.device
    data: torch.Tensor
    cid: str
    stage: ScoringStage
    score_base: Path
    batch_size: int


def _score_one_split(p: _SplitScoringParams) -> ScoringRecord:
    data = (
        p.data.to(p.model_device, non_blocking=True)
        if p.data.device != p.model_device
        else p.data
    )
    errors = compute_reconstruction_errors(p.model, data, batch_size=p.batch_size)
    out_path = score_output_path(p.score_base, p.stage, p.cid)
    write_artifact(_errors_to_dataframe(errors), out_path)
    logger.debug(
        "wrote scores",
        n_scores=len(errors),
        path=str(out_path),
        client=p.cid,
        stage=p.stage,
    )
    return _score_record(out_path, p.cid, p.stage, errors)


def score_clients_impl(
    client_data: Mapping[str, ClientData],
    *,
    score_base: Path,
    scoring_batch_size: int,
    get_model: Callable[[str], Autoencoder],
) -> list[ScoringRecord]:
    records: list[ScoringRecord] = []
    for cid, splits in client_data.items():
        model = get_model(cid)
        model.eval()
        model_device = next(model.parameters()).device
        for stage in SCORING_STAGES:
            records.append(
                _score_one_split(
                    _SplitScoringParams(
                        model=model,
                        model_device=model_device,
                        data=getattr(splits, stage.client_data_attr),
                        cid=cid,
                        stage=stage,
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

    records = score_clients_impl(
        client_data,
        score_base=score_base,
        scoring_batch_size=scoring_batch_size,
        get_model=lambda _cid: model,
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
