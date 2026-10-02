from __future__ import annotations

from datp.types import (
    RandomSeed,
    RoundIndex,
)


from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile
from datp.checkpointing.enums import CheckpointArtifactStatus
from datp.config.models import ExperimentStage
from datp.core.enums import CONTROLLED_POLICIES, ThresholdPolicy
from datp.core.identity import PolicyRunId, TrainingCellId


@dataclass(frozen=True, slots=True)
class CheckpointArtifactCellStatus:

    stage: ExperimentStage
    seed: RandomSeed
    checkpoint_round: RoundIndex
    checkpoint: CheckpointArtifactStatus
    scores: CheckpointArtifactStatus
    results: tuple[tuple[ThresholdPolicy, CheckpointArtifactStatus], ...]

    @property
    def complete(self) -> bool:
        return (
            self.checkpoint == CheckpointArtifactStatus.PRESENT
            and self.scores == CheckpointArtifactStatus.PRESENT
            and all(
                status == CheckpointArtifactStatus.PRESENT for _, status in self.results
            )
        )


def checkpoint_artifact_status(
    *,
    artifact_root: Path,
    stage: ExperimentStage,
    seed: RandomSeed,
    checkpoint_round: RoundIndex,
    policies: tuple[ThresholdPolicy, ...] | None = None,
) -> CheckpointArtifactCellStatus:
    cell = TrainingCellId(stage=stage, seed=RandomSeed(seed))
    layout = ArtifactLayout(base_dir=artifact_root, stage=stage)
    expected_policies = policies or CONTROLLED_POLICIES

    return CheckpointArtifactCellStatus(
        stage=stage,
        seed=seed,
        checkpoint_round=checkpoint_round,
        checkpoint=_file_status(
            layout.checkpoint_dir(cell, checkpoint_round)
            / ArtifactFile.MODEL_CHECKPOINT
        ),
        scores=_file_status(
            layout.score_cell(cell, checkpoint_round).manifest_path
        ),
        results=tuple(
            (
                policy,
                _file_status(
                    layout.policy_run(
                        PolicyRunId(cell=cell, policy=policy), checkpoint_round
                    ).metrics_path
                ),
            )
            for policy in expected_policies
        ),
    )


def _file_status(path: Path) -> CheckpointArtifactStatus:
    if path.is_file():
        return CheckpointArtifactStatus.PRESENT
    if path.exists():
        return CheckpointArtifactStatus.INVALID
    return CheckpointArtifactStatus.MISSING
