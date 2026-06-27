"""Prepared-data gating: ensure or verify N-BaIoT preprocessing artifacts exist."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.names import ArtifactFile
from datp.config.models import DatpConfig
from datp.config.models import ExperimentStage
from datp.core.logging import get_logger
from datp.data.catalog import dataset_for_stage
from datp.data.common.storage import assert_no_csv_artifacts
from datp.data.datasets.nbaiot.prepare import prepare_nbaiot
from datp.data.manifests import PartitionManifest
from datp.data.paths import processed_root, raw_root
from datp.data.splits import Split, filename_for_split, split_path

logger = get_logger(__name__)

_MODULE = "experiments.stages.prepare_data"
_REQUIRED_CLIENT_ARTIFACTS = tuple(filename_for_split(s) for s in Split) + (
    str(ArtifactFile.SCALER),
)


@dataclass(frozen=True, slots=True)
class PreparedDataRequest:
    """Request payload carrying stage, seed, config, and base directory for data preparation."""

    stage: ExperimentStage
    seed: int
    cfg: DatpConfig
    base_dir: Path


def ensure_prepared_data(request: PreparedDataRequest) -> Path:
    """Verify or run N-BaIoT data preparation and return the prepared data directory."""
    dataset_id = dataset_for_stage(request.stage)
    prepared_dir = processed_root(dataset_id, base_dir=request.base_dir)
    manifest_file = prepared_dir / ArtifactFile.MANIFEST

    if manifest_file.exists():
        _verify_existing_prepared_data(request, prepared_dir, manifest_file)
        return prepared_dir

    logger.info(
        "processed data missing; running preparation",
        stage=request.stage,
        seed=request.seed,
        prepared_dir=str(prepared_dir),
    )
    _prepare(request)
    _verify_existing_prepared_data(request, prepared_dir, manifest_file)
    return prepared_dir


def _prepare(request: PreparedDataRequest) -> None:
    cfg = request.cfg
    dataset_id = dataset_for_stage(request.stage)
    raw_dir = raw_root(dataset_id, base_dir=request.base_dir)
    output_dir = processed_root(dataset_id, base_dir=request.base_dir)
    prepare_nbaiot(
        raw_dir=raw_dir,
        output_dir=output_dir,
        n_min=cfg.threshold.n_min,
        seed=request.seed,
        balanced_test=cfg.dataset.nbaiot_balanced_test,
    )


def _verify_existing_prepared_data(
    request: PreparedDataRequest, prepared_dir: Path, manifest_file: Path
) -> None:
    dataset_id = dataset_for_stage(request.stage)
    manifest = PartitionManifest.load(manifest_file)
    raw_base_dir = raw_root(dataset_id, base_dir=request.base_dir)
    manifest.verify_hashes(raw_base_dir)
    _verify_client_artifacts(prepared_dir)
    assert_no_csv_artifacts(prepared_dir)
    logger.info(
        "processed data verified; reusing",
        stage=request.stage,
        seed=request.seed,
        prepared_dir=str(prepared_dir),
    )


def _verify_client_artifacts(prepared_dir: Path) -> None:
    if not prepared_dir.is_dir():
        raise RuntimeError(
            f"[{_MODULE}] Prepared directory missing. Expected: {str(prepared_dir)}. Got: not found."
        )

    client_dirs = sorted(
        d
        for d in prepared_dir.iterdir()
        if d.is_dir() and split_path(d, Split.TRAIN).exists()
    )
    if not client_dirs:
        raise RuntimeError(
            f"[{_MODULE}] Prepared clients missing. Expected: at least one client directory. Got: 0."
        )

    for client_dir in client_dirs:
        missing = [
            name
            for name in _REQUIRED_CLIENT_ARTIFACTS
            if not (client_dir / name).exists()
        ]
        if missing:
            raise RuntimeError(
                f"[{_MODULE}] Prepared client {client_dir.name} incomplete. Expected: ",
                ".join(_REQUIRED_CLIENT_ARTIFACTS). Got: ",
                ".join(missing).",
            )
