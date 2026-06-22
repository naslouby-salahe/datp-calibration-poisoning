from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile
from datp.checkpointing.enums import CheckpointArtifactStatus
from datp.config.stages import ExperimentStage
from datp.core.enums import CONTROLLED_POLICIES
from datp.core.identity import PolicyRunId, TrainingCellId


@dataclass(frozen=True, slots=True)
class CheckpointArtifactCellStatus:
    stage: ExperimentStage
    seed: int
    checkpoint_round: int
    checkpoint: CheckpointArtifactStatus
    scores: CheckpointArtifactStatus
    results: tuple[tuple[ThresholdPolicy, CheckpointArtifactStatus], ...]

    @property
    def complete(self) -> bool:
        result_statuses = [status for _, status in self.results]
        return (
            self.checkpoint == CheckpointArtifactStatus.PRESENT
            and self.scores == CheckpointArtifactStatus.PRESENT
            and all(
                status == CheckpointArtifactStatus.PRESENT for status in result_statuses
            )
        )


def checkpoint_artifact_status(
    *,
    artifact_root: Path,
    stage: ExperimentStage,
    seed: int,
    checkpoint_round: int,
    policies: tuple[ThresholdPolicy, ...] | None = None,
) -> CheckpointArtifactCellStatus:
    cell = TrainingCellId(stage=stage, seed=seed)
    layout = ArtifactLayout(base_dir=artifact_root, stage=stage)
    expected_policies = policies or CONTROLLED_POLICIES
    checkpoint_path = (
        layout.checkpoint_dir_for_round(cell, checkpoint_round)
        / ArtifactFile.MODEL_CHECKPOINT
    )
    score_manifest = layout.score_cell_for_round(cell, checkpoint_round).manifest_path
    result_statuses: list[tuple[ThresholdPolicy, CheckpointArtifactStatus]] = []
    for policy in expected_policies:
        run = PolicyRunId(cell=cell, policy=policy)
        metrics_path = layout.policy_run_for_round(run, checkpoint_round).metrics_path
        result_statuses.append((policy, _file_status(metrics_path)))
    return CheckpointArtifactCellStatus(
        stage=stage,
        seed=seed,
        checkpoint_round=checkpoint_round,
        checkpoint=_file_status(checkpoint_path),
        scores=_file_status(score_manifest),
        results=tuple(result_statuses),
    )


def _file_status(path: Path) -> CheckpointArtifactStatus:
    if not path.exists():
        return CheckpointArtifactStatus.MISSING
    if path.is_file():
        return CheckpointArtifactStatus.PRESENT
    return CheckpointArtifactStatus.INVALID
