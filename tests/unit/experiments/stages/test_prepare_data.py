"""Unit tests for the data-preparation experiment stage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from datp.artifacts.names import ArtifactFile
from datp.config.compose import BASE_CONFIG
from datp.config.models import ExperimentStage
from datp.data.manifests import ManifestMetadata, create_manifest
from datp.data.splits import Split, filename_for_split
from datp.experiments.stages.prepare_data import (
    PreparedDataRequest,
    ensure_prepared_data,
)

_STAGE = ExperimentStage.NBAIOT_MAIN


def _write_raw_file(raw_dir: Path) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_file = raw_dir / "raw.csv"
    raw_file.write_text("x\n1\n")
    return raw_file


def _write_processed_client(prepared_dir: Path) -> None:
    client_dir = prepared_dir / "client_0"
    client_dir.mkdir(parents=True, exist_ok=True)
    for split in Split:
        (client_dir / filename_for_split(split)).write_text("placeholder")
    (client_dir / ArtifactFile.SCALER).write_bytes(b"scaler")


def _write_manifest(prepared_dir: Path, raw_dir: Path, raw_file: Path) -> None:
    create_manifest(
        dataset="nbaiot",
        raw_files=[raw_file],
        raw_base_dir=raw_dir,
        metadata=ManifestMetadata.model_validate({"n_devices": 1, "n_features": 2}),
        manifest_path=prepared_dir / ArtifactFile.MANIFEST,
    )


def _patch_paths(monkeypatch, prepared_dir: Path, raw_dir: Path) -> None:
    import datp.experiments.stages.prepare_data as mod

    monkeypatch.setattr(mod, "processed_root", lambda *a, **kw: prepared_dir)
    monkeypatch.setattr(mod, "raw_root", lambda *a, **kw: raw_dir)


def test_existing_processed_data_is_verified_and_reused(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_file = _write_raw_file(raw_dir)
    prepared_dir = tmp_path / "processed" / "nbaiot"
    _write_processed_client(prepared_dir)
    _write_manifest(prepared_dir, raw_dir, raw_file)
    _patch_paths(monkeypatch, prepared_dir, raw_dir)

    prepare_mock = Mock()
    monkeypatch.setattr(
        "datp.experiments.stages.prepare_data.prepare_nbaiot", prepare_mock
    )

    result = ensure_prepared_data(
        PreparedDataRequest(
            stage=_STAGE,
            seed=0,
            cfg=BASE_CONFIG,
            base_dir=tmp_path,
        )
    )

    assert result == prepared_dir
    prepare_mock.assert_not_called()


def test_missing_processed_data_runs_preparation_then_verifies(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw_dir = tmp_path / "raw"
    raw_file = _write_raw_file(raw_dir)
    prepared_dir = tmp_path / "processed" / "nbaiot"
    _patch_paths(monkeypatch, prepared_dir, raw_dir)

    def prepare(*, raw_dir, output_dir, **kwargs) -> None:
        _write_processed_client(prepared_dir)
        _write_manifest(prepared_dir, raw_dir, raw_file)

    prepare_mock = Mock(side_effect=prepare)
    monkeypatch.setattr(
        "datp.experiments.stages.prepare_data.prepare_nbaiot", prepare_mock
    )

    result = ensure_prepared_data(
        PreparedDataRequest(
            stage=_STAGE,
            seed=0,
            cfg=BASE_CONFIG,
            base_dir=tmp_path,
        )
    )

    assert result == prepared_dir
    prepare_mock.assert_called_once()
