from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

from pathlib import Path

import pytest

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile
from datp.checkpointing.enums import CheckpointArtifactStatus
from datp.checkpointing.status import checkpoint_artifact_status
from datp.config.stages import ExperimentStage
from datp.core.identity import TrainingCellId

_STAGE = ExperimentStage.NBAIOT_MAIN


class TestCheckpointArtifactStatusMissing:
    def test_checkpoint_artifact_status_missing(self, tmp_path: Path) -> None:
        result = checkpoint_artifact_status(
            artifact_root=tmp_path,
            stage=_STAGE,
            seed=0,
            checkpoint_round=50,
        )
        assert result.checkpoint == CheckpointArtifactStatus.MISSING


class TestCheckpointArtifactStatusPresent:
    def test_checkpoint_artifact_status_present(self, tmp_path: Path) -> None:
        layout = ArtifactLayout(base_dir=tmp_path, stage=_STAGE)
        cell = TrainingCellId(stage=_STAGE, seed=1)
        ckpt_path = layout.checkpoint_dir_for_round(cell, 50) / ArtifactFile.MODEL_CHECKPOINT
        ckpt_path.parent.mkdir(parents=True, exist_ok=True)
        ckpt_path.write_bytes(b"fake weights")

        result = checkpoint_artifact_status(
            artifact_root=tmp_path,
            stage=_STAGE,
            seed=1,
            checkpoint_round=50,
        )
        assert result.checkpoint == CheckpointArtifactStatus.PRESENT
