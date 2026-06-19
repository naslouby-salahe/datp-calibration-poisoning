from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from datp.artifacts.names import ArtifactFile
from datp.core.enums import (
    SCORING_STAGES,
    Regime,
)
from datp.data.catalog import DatasetID
from datp.data.common.storage import write_artifact
from datp.data.datasets.nbaiot.spec import NBAIOT_SPEC
from datp.scoring.schema import SCORE_COLUMN
from datp.validation.discovery import iter_score_cells
from datp.validation.enums import AuditStatus
from datp.validation.score_manifest import (
    ScoreCheckCode,
    verify_all_score_cells,
    verify_score_cell,
)

CLIENTS: tuple[str, ...] = NBAIOT_SPEC.device_ids
PARTIAL_CLIENTS: tuple[str, ...] = NBAIOT_SPEC.device_ids[:3]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_score_parquet(path: Path, values: np.ndarray) -> None:
    write_artifact(pl.DataFrame({SCORE_COLUMN: values.astype(np.float32)}), path)


def _build_cell(
    *,
    base_dir: Path,
    data_root: Path,
    regime: Regime = Regime.A,
    seed: int = 0,
    clients: tuple[str, ...] = CLIENTS,
    dataset: DatasetID = DatasetID.NBAIOT,
    include_sentinel: bool = True,
    include_manifest: bool = True,
    drop_manifest_field: str | None = None,
    completion_status: str = "complete",
    checkpoint_hash_override: str | None = None,
    checkpoint_present: bool = True,
    write_partition: bool = True,
) -> Path:
    """Construct a minimal Regime-A score cell + partition + checkpoint."""
    cell_dir = base_dir / "scores" / regime.value / f"seed_{seed}"
    cell_dir.mkdir(parents=True, exist_ok=True)

    for stage in SCORING_STAGES:
        for client_id in clients:
            arr = np.linspace(0.01, 0.05, 25, dtype=np.float32)
            _write_score_parquet(cell_dir / stage.value / f"{client_id}.parquet", arr)

    if write_partition:
        partition_root = data_root / "data" / "processed" / dataset
        partition_root.mkdir(parents=True, exist_ok=True)
        (partition_root / "manifest.json").write_text(
            json.dumps(
                {
                    "dataset": dataset,
                    "file_hashes": {"fixture": "abc"},
                    "metadata": {
                        "n_features": 115,
                        "n_devices": len(clients),
                        "n_clients": None,
                    },
                    "created": "2026-04-26T00:00:00+00:00",
                }
            ),
            encoding="utf-8",
        )
        for client_id in clients:
            (partition_root / client_id).mkdir(parents=True, exist_ok=True)

    ckpt = (
        base_dir
        / "checkpoints"
        / regime.value
        / f"seed_{seed}"
        / ArtifactFile.MODEL_CHECKPOINT
    )
    if checkpoint_present:
        ckpt.parent.mkdir(parents=True, exist_ok=True)
        ckpt.write_bytes(b"fixture-checkpoint-bytes")
        ckpt_hash = _sha256(ckpt)
    else:
        ckpt_hash = "0" * 64

    if include_manifest:
        manifest = {
            "schema_version": "1",
            "dataset": dataset,
            "regime": regime.value,
            "seed": seed,
            "alpha": None,
            "model_checkpoint_path": str(ckpt.relative_to(data_root))
            if data_root in ckpt.parents
            else str(ckpt),
            "model_checkpoint_hash": checkpoint_hash_override or ckpt_hash,
            "scoring_code_version": "fixture",
            "score_column_name": SCORE_COLUMN,
            "expected_client_ids": sorted(clients),
            "expected_splits": [stage.value for stage in SCORING_STAGES],
            "actual_client_ids": sorted(clients),
            "actual_splits": sorted(stage.value for stage in SCORING_STAGES),
            "records": [
                {"client_id": cid, "split": stage.value}
                for cid in clients
                for stage in SCORING_STAGES
            ],
            "completion_status": completion_status,
            "generated_at_utc": "2026-04-26T00:00:00+00:00",
        }
        if drop_manifest_field is not None:
            manifest.pop(drop_manifest_field, None)
        (cell_dir / ArtifactFile.SCORING_MANIFEST).write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

    if include_sentinel:
        (cell_dir / ArtifactFile.SCORING_SENTINEL).write_text(
            "done\n", encoding="utf-8"
        )

    return cell_dir


def _check_status(report, code: ScoreCheckCode) -> AuditStatus:
    for check in report.checks:
        if check.code == code:
            return check.status
    raise AssertionError(f"check {code} not present in report")


def test_valid_cell_passes_all_checks(tmp_path: Path) -> None:
    base_dir = tmp_path / "outputs"
    cell = _build_cell(base_dir=base_dir, data_root=tmp_path)
    report = verify_score_cell(cell, base_dir, data_root=tmp_path)

    assert report.overall_status == AuditStatus.PASS, report.checks
    assert report.cell.regime == Regime.A
    assert report.cell.seed == 0
    assert set(report.expected_client_ids) == set(CLIENTS)


def test_missing_manifest_fails(tmp_path: Path) -> None:
    base_dir = tmp_path / "outputs"
    cell = _build_cell(base_dir=base_dir, data_root=tmp_path, include_manifest=False)
    report = verify_score_cell(cell, base_dir, data_root=tmp_path)

    assert report.overall_status == AuditStatus.PARTIAL
    assert _check_status(report, ScoreCheckCode.MANIFEST_PRESENT) == AuditStatus.MISSING
    assert (
        _check_status(report, ScoreCheckCode.MANIFEST_PARSEABLE) == AuditStatus.MISSING
    )


def test_missing_client_directory_fails(tmp_path: Path) -> None:
    base_dir = tmp_path / "outputs"
    cell = _build_cell(base_dir=base_dir, data_root=tmp_path)
    # Remove all per-client files in cal/ for one client.
    (cell / "cal" / f"{CLIENTS[0]}.parquet").unlink()
    report = verify_score_cell(cell, base_dir, data_root=tmp_path)

    assert report.overall_status == AuditStatus.FAIL
    assert (
        _check_status(report, ScoreCheckCode.PER_CLIENT_SPLIT_FILES_PRESENT)
        == AuditStatus.FAIL
    )


def test_wrong_parquet_schema_fails(tmp_path: Path) -> None:
    base_dir = tmp_path / "outputs"
    cell = _build_cell(base_dir=base_dir, data_root=tmp_path)
    # Overwrite one parquet with the wrong column name.
    bad = cell / "cal" / f"{CLIENTS[0]}.parquet"
    table = pa.table({"wrong_col": pa.array([0.1, 0.2], type=pa.float32())})
    pq.write_table(table, bad)

    report = verify_score_cell(cell, base_dir, data_root=tmp_path)

    assert report.overall_status == AuditStatus.FAIL
    assert (
        _check_status(report, ScoreCheckCode.PARQUET_SCHEMA_VALID) == AuditStatus.FAIL
    )


def test_missing_checkpoint_hash_field_fails(tmp_path: Path) -> None:
    base_dir = tmp_path / "outputs"
    cell = _build_cell(base_dir=base_dir, data_root=tmp_path)
    manifest_path = cell / ArtifactFile.SCORING_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["model_checkpoint_hash"] = "NOT_PROVIDED"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = verify_score_cell(cell, base_dir, data_root=tmp_path)

    assert report.overall_status != AuditStatus.PASS
    assert (
        _check_status(report, ScoreCheckCode.CHECKPOINT_HASH_FIELD_PRESENT)
        == AuditStatus.FAIL
    )


def test_missing_checkpoint_file_fails(tmp_path: Path) -> None:
    base_dir = tmp_path / "outputs"
    cell = _build_cell(base_dir=base_dir, data_root=tmp_path)
    # Remove the actual checkpoint file.
    (base_dir / "checkpoints" / "a" / "seed_0" / ArtifactFile.MODEL_CHECKPOINT).unlink()

    report = verify_score_cell(cell, base_dir, data_root=tmp_path)

    assert (
        _check_status(report, ScoreCheckCode.CHECKPOINT_FILE_PRESENT)
        == AuditStatus.MISSING
    )
    assert (
        _check_status(report, ScoreCheckCode.CHECKPOINT_HASH_MATCHES)
        == AuditStatus.MISSING
    )


def test_wrong_checkpoint_hash_fails(tmp_path: Path) -> None:
    base_dir = tmp_path / "outputs"
    cell = _build_cell(
        base_dir=base_dir,
        data_root=tmp_path,
        checkpoint_hash_override="0" * 64,
    )
    report = verify_score_cell(cell, base_dir, data_root=tmp_path)

    assert report.overall_status == AuditStatus.FAIL
    assert (
        _check_status(report, ScoreCheckCode.CHECKPOINT_HASH_MATCHES)
        == AuditStatus.FAIL
    )


@pytest.mark.parametrize("split_to_drop", ["cal", "test_benign", "test_attack"])
def test_incomplete_split_directory_fails(tmp_path: Path, split_to_drop: str) -> None:
    base_dir = tmp_path / "outputs"
    cell = _build_cell(base_dir=base_dir, data_root=tmp_path)
    split_dir = cell / split_to_drop
    for f in split_dir.glob("*.parquet"):
        f.unlink()
    split_dir.rmdir()

    report = verify_score_cell(cell, base_dir, data_root=tmp_path)

    assert report.overall_status == AuditStatus.FAIL
    assert (
        _check_status(report, ScoreCheckCode.SPLIT_DIRECTORIES_PRESENT)
        == AuditStatus.FAIL
    )


def test_empty_parquet_fails(tmp_path: Path) -> None:
    base_dir = tmp_path / "outputs"
    cell = _build_cell(base_dir=base_dir, data_root=tmp_path)
    # Replace one cal parquet with an empty one (zero rows but correct schema).
    bad = cell / "cal" / f"{CLIENTS[0]}.parquet"
    table = pa.table({SCORE_COLUMN: pa.array([], type=pa.float32())})
    pq.write_table(table, bad)

    report = verify_score_cell(cell, base_dir, data_root=tmp_path)

    assert report.overall_status == AuditStatus.FAIL
    assert _check_status(report, ScoreCheckCode.PARQUET_NON_EMPTY) == AuditStatus.FAIL


def test_required_manifest_field_missing_fails(tmp_path: Path) -> None:
    base_dir = tmp_path / "outputs"
    cell = _build_cell(
        base_dir=base_dir,
        data_root=tmp_path,
        drop_manifest_field="model_checkpoint_hash",
    )
    report = verify_score_cell(cell, base_dir, data_root=tmp_path)

    assert report.overall_status == AuditStatus.FAIL
    assert (
        _check_status(report, ScoreCheckCode.MANIFEST_FIELDS_PRESENT)
        == AuditStatus.FAIL
    )


def test_completion_status_not_complete_fails(tmp_path: Path) -> None:
    base_dir = tmp_path / "outputs"
    cell = _build_cell(
        base_dir=base_dir,
        data_root=tmp_path,
        completion_status="partial",
    )
    report = verify_score_cell(cell, base_dir, data_root=tmp_path)

    assert (
        _check_status(report, ScoreCheckCode.MANIFEST_COMPLETION_STATUS)
        == AuditStatus.FAIL
    )


def test_missing_sentinel_marker_partial(tmp_path: Path) -> None:
    base_dir = tmp_path / "outputs"
    cell = _build_cell(base_dir=base_dir, data_root=tmp_path, include_sentinel=False)
    report = verify_score_cell(cell, base_dir, data_root=tmp_path)

    assert (
        _check_status(report, ScoreCheckCode.SCORING_SENTINEL_PRESENT)
        == AuditStatus.MISSING
    )


def test_client_mismatch_vs_partition_fails(tmp_path: Path) -> None:
    base_dir = tmp_path / "outputs"
    # Manifest claims only 3 NBAIOT clients but partition spec expects all 9.
    cell = _build_cell(base_dir=base_dir, data_root=tmp_path, clients=PARTIAL_CLIENTS)
    report = verify_score_cell(cell, base_dir, data_root=tmp_path)

    assert (
        _check_status(report, ScoreCheckCode.CLIENT_IDS_MATCH_PARTITION)
        == AuditStatus.FAIL
    )


def test_iter_score_cells_and_verify_all(tmp_path: Path) -> None:
    base_dir = tmp_path / "outputs"
    _build_cell(base_dir=base_dir, data_root=tmp_path, regime=Regime.A, seed=0)
    _build_cell(base_dir=base_dir, data_root=tmp_path, regime=Regime.A, seed=1)

    cells = iter_score_cells(base_dir)
    assert {(c.regime, c.seed) for c in cells} == {(Regime.A, 0), (Regime.A, 1)}

    reports = verify_all_score_cells(base_dir, data_root=tmp_path, write_reports=True)
    assert len(reports) == 2
    for cell in cells:
        assert (cell.cell_dir / "score_cell_verification.json").is_file()
    assert (base_dir / "scores" / "score_cell_verification_index.json").is_file()
