"""Unit tests for checkpoint status invariants and abort/complete detection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile
from datp.checkpointing.enums import CheckpointArtifactStatus
from datp.checkpointing.invariants import load_score_manifest_identity
from datp.checkpointing.status import checkpoint_artifact_status
from datp.config.models import ExperimentStage
from datp.core.identity import TrainingCellId

_STAGE = ExperimentStage.NBAIOT_MAIN
_VALID_SCORE_MANIFEST = {
    "checkpoint_round": 50,
    "model_checkpoint_hash": "model-hash",
    "expected_client_ids": ["c2", "c1"],
    "expected_splits": ["test_attack", "cal", "test_benign"],
}


def _write_score_manifest(path: Path, **overrides: object) -> None:
    payload = _VALID_SCORE_MANIFEST | overrides
    path.write_text(json.dumps(payload))


class TestScoreManifestIdentity:
    """Score manifest identity and hash tracking."""

    def test_load_score_manifest_identity_sorts_clients_and_splits(
        self, tmp_path: Path
    ) -> None:
        manifest_path = tmp_path / "scoring_manifest.json"
        _write_score_manifest(manifest_path)

        identity = load_score_manifest_identity(manifest_path)

        assert identity.checkpoint_round == 50
        assert identity.checkpoint_identity == "model-hash"
        assert identity.client_ids == ("c1", "c2")
        assert identity.split_ids == ("cal", "test_attack", "test_benign")

    @pytest.mark.parametrize(
        ("field", "value"),
        (
            ("checkpoint_round", "50"),
            ("model_checkpoint_hash", 123),
            ("expected_client_ids", ["c1", 2]),
            ("expected_splits", "cal"),
        ),
    )
    def test_load_score_manifest_identity_rejects_wrong_field_types(
        self, tmp_path: Path, field: str, value: object
    ) -> None:
        manifest_path = tmp_path / "scoring_manifest.json"
        _write_score_manifest(manifest_path, **{field: value})

        with pytest.raises(ValueError):
            load_score_manifest_identity(manifest_path)


class TestCheckpointArtifactStatusMissing:
    """Checkpoint artifact status when artifacts are missing."""

    def test_checkpoint_artifact_status_missing(self, tmp_path: Path) -> None:
        result = checkpoint_artifact_status(
            artifact_root=tmp_path,
            stage=_STAGE,
            seed=0,
            checkpoint_round=50,
        )
        assert result.checkpoint == CheckpointArtifactStatus.MISSING


class TestCheckpointArtifactStatusPresent:
    """Checkpoint artifact status when all artifacts are present."""

    def test_checkpoint_artifact_status_present(self, tmp_path: Path) -> None:
        layout = ArtifactLayout(base_dir=tmp_path, stage=_STAGE)
        cell = TrainingCellId(stage=_STAGE, seed=1)
        ckpt_path = (
            layout.checkpoint_dir_for_round(cell, 50) / ArtifactFile.MODEL_CHECKPOINT
        )
        ckpt_path.parent.mkdir(parents=True, exist_ok=True)
        ckpt_path.write_bytes(b"fake weights")

        result = checkpoint_artifact_status(
            artifact_root=tmp_path,
            stage=_STAGE,
            seed=1,
            checkpoint_round=50,
        )
        assert result.checkpoint == CheckpointArtifactStatus.PRESENT
