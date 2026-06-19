# SPDX-License-Identifier: Proprietary
"""Score artifacts have no baseline subdirectory — they are shared across B1/B2/B3/B4."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import polars as pl
import torch

from datp.artifacts.io import write_json_atomic
from datp.artifacts.names import ArtifactFile, PathToken
from datp.core.device import resolve_device
from datp.core.enums import (
    SCORING_STAGES,
    Regime,
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
    return pl.DataFrame({SCORE_COLUMN: errors})


def _score_record(
    path: Path, client_id: str, stage: ScoringStage, errors: np.ndarray
) -> dict[str, object]:
    finite = errors[np.isfinite(errors)]
    return {
        "client_id": client_id,
        "split": stage.value,
        "path": str(path),
        "row_count": int(errors.size),
        "columns": [SCORE_COLUMN],
        "dtypes": {SCORE_COLUMN: "Float32"},
        "score_min": float(finite.min()) if finite.size else None,
        "score_max": float(finite.max()) if finite.size else None,
        "score_nan_count": int(np.isnan(errors).sum()),
        "file_hash": hash_file(path),
    }


def validate_scoring_manifest(score_base: Path) -> dict[str, object]:
    score_base = Path(score_base)
    manifest_path = score_base / ArtifactFile.SCORING_MANIFEST
    if not manifest_path.exists():
        raise FileNotFoundError(
            fmt(_MODULE, "Scoring manifest missing", str(manifest_path), "missing file")
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest["records"]
    expected = {
        (cid, split)
        for cid in manifest["expected_client_ids"]
        for split in manifest["expected_splits"]
    }
    actual = {(str(row["client_id"]), str(row["split"])) for row in records}
    missing = sorted(expected - actual)
    missing_files: list[str] = []
    invalid_files: list[str] = []
    for row in records:
        path = Path(str(row["path"]))
        try:
            resolved_path = _resolve_within_base(score_base, path)
        except ValueError:
            invalid_files.append(str(path))
            continue
        if not resolved_path.exists():
            missing_files.append(str(path))
    missing_files.sort()
    invalid_files.sort()
    completion_status = manifest["completion_status"]
    if (
        completion_status != ScoringManifestStatus.COMPLETE
        or missing
        or missing_files
        or invalid_files
    ):
        raise ValueError(
            fmt(
                _MODULE,
                "Scoring manifest incomplete",
                "complete manifest with all expected score files",
                f"status={completion_status}, missing={missing}, missing_files={missing_files}, invalid_files={invalid_files}",
            )
        )
    return manifest


def _score_clients_impl(
    client_data: dict[str, ClientData],
    *,
    score_base: Path,
    scoring_batch_size: int,
    get_model: Callable[[str], Autoencoder],
) -> list[dict[str, object]]:
    """Shared scoring loop: for each client and each ScoringStage, score with the
    model returned by *get_model(client_id)* and write a parquet artifact."""
    records: list[dict[str, object]] = []
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
) -> dict[str, object]:
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


def _write_scoring_manifest_and_sentinel(
    records: list[dict[str, object]],
    client_ids: list[str],
    score_base: Path,
    *,
    dataset: DatasetID,
    regime: Regime | None,
    seed: int | None,
    alpha: float | None,
    checkpoint_path: Path | None,
    checkpoint_round: int | None,
) -> None:
    """Shared manifest + sentinel writer for scoring results."""
    manifest = {
        "schema_version": SCORING_MANIFEST_SCHEMA_VERSION,
        "dataset": dataset,
        "regime": regime.value if regime is not None else SCORING_MANIFEST_NOT_PROVIDED,
        "seed": seed,
        "alpha": alpha,
        "model_checkpoint_path": str(checkpoint_path)
        if checkpoint_path is not None
        else SCORING_MANIFEST_NOT_PROVIDED,
        "model_checkpoint_hash": hash_file(checkpoint_path)
        if checkpoint_path is not None
        else SCORING_MANIFEST_NOT_PROVIDED,
        "checkpoint_round": checkpoint_round,
        "scoring_code_version": git_commit(),
        "score_column_name": SCORE_COLUMN,
        "expected_client_ids": sorted(client_ids),
        "expected_splits": [stage.value for stage in SCORING_STAGES],
        "actual_client_ids": sorted({str(row["client_id"]) for row in records}),
        "actual_splits": sorted({str(row["split"]) for row in records}),
        "records": records,
        "completion_status": ScoringManifestStatus.COMPLETE,
        "generated_at_utc": utc_timestamp(),
    }
    write_json_atomic(score_base / ArtifactFile.SCORING_MANIFEST, manifest)
    validate_scoring_manifest(score_base)

    sentinel = score_base / ArtifactFile.SCORING_SENTINEL
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text(f"Scoring complete: {len(client_ids)} clients.\n")


def score_clients(
    model: Autoencoder,
    client_data: dict[str, ClientData],
    *,
    score_base: Path,
    regime: Regime | None,
    seed: int | None,
    alpha: float | None,
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
        dataset=dataset,
        regime=regime,
        seed=seed,
        alpha=alpha,
        checkpoint_path=checkpoint_path,
        checkpoint_round=checkpoint_round,
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
