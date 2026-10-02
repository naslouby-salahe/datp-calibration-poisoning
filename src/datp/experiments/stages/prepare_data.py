
from __future__ import annotations
from datp.types import FeatureCount, RandomSeed

from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.names import ArtifactFile
from datp.config.models import DatpConfig
from datp.config.models import ExperimentStage
from datp.core.logging import get_logger
from datp.data.catalog import dataset_for_stage
from datp.data.catalog import dataset_spec
from datp.data.common.audit import audit_partitions, run_schema_audit
from datp.data.common.storage import assert_no_csv_artifacts
from datp.data.datasets.nbaiot.prepare import prepare_nbaiot
from datp.data.manifests import PartitionManifest
from datp.data.paths import processed_root, raw_root
from datp.data.scaling import load_scaler
from datp.data.splits import Split, filename_for_split, split_path

logger = get_logger(__name__)

_MODULE = "experiments.stages.prepare_data"
_REQUIRED_CLIENT_ARTIFACTS = tuple(filename_for_split(s) for s in Split) + (
    ArtifactFile.SCALER,
)


@dataclass(frozen=True, slots=True)
class PreparedDataRequest:

    stage: ExperimentStage
    seed: RandomSeed
    cfg: DatpConfig
    base_dir: Path


def ensure_prepared_data(request: PreparedDataRequest) -> Path:
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
    partition_results = prepare_nbaiot(
        raw_dir=raw_dir,
        output_dir=output_dir,
        n_min=cfg.threshold.n_min,
        seed=request.seed,
        test_balance_policy=cfg.dataset.nbaiot_test_balance,
    )
    audit_partitions(
        partition_results,
        request.stage,
        request.base_dir,
        cfg.threshold.n_min,
    )


def _verify_existing_prepared_data(
    request: PreparedDataRequest, prepared_dir: Path, manifest_file: Path
) -> None:
    dataset_id = dataset_for_stage(request.stage)
    manifest: PartitionManifest = PartitionManifest.load(manifest_file)
    raw_base_dir = raw_root(dataset_id, base_dir=request.base_dir)
    manifest.verify_hashes(raw_base_dir)
    _verify_client_artifacts(prepared_dir, dataset_spec(dataset_id).feature_count)
    assert_no_csv_artifacts(prepared_dir)
    logger.info(
        "processed data verified; reusing",
        stage=request.stage,
        seed=request.seed,
        prepared_dir=str(prepared_dir),
    )


def _verify_client_artifacts(prepared_dir: Path, feature_count: FeatureCount) -> None:
    if not prepared_dir.is_dir():
        raise RuntimeError(
            f"[{_MODULE}] Prepared directory missing. Expected: {prepared_dir}. Got: not found."
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
                f"[{_MODULE}] Prepared client {client_dir.name} incomplete. "
                f"Expected: {', '.join(_REQUIRED_CLIENT_ARTIFACTS)}. "
                f"Got missing: {', '.join(missing)}."
            )
        scaler = load_scaler(client_dir / ArtifactFile.SCALER)
        if scaler.n_features_in_ != feature_count:
            raise RuntimeError(
                f"[{_MODULE}] Scaler feature count mismatch for {client_dir.name}: "
                f"expected {feature_count}, got {scaler.n_features_in_}."
            )
        for split in Split:
            run_schema_audit(split_path(client_dir, split), feature_count)
