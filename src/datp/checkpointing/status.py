from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile
from datp.checkpointing.enums import CheckpointArtifactStatus
from datp.core.enums import (
    Baseline,
    Regime,
    controlled_baselines_for_regime,
)
from datp.core.identity import BaselineRunId, TrainingCellId


@dataclass(frozen=True, slots=True)
class CheckpointArtifactCellStatus:
    regime: Regime
    seed: int
    alpha: float | None
    checkpoint_round: int
    checkpoint: CheckpointArtifactStatus
    scores: CheckpointArtifactStatus
    results: tuple[tuple[Baseline, CheckpointArtifactStatus], ...]

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
    regime: Regime,
    seed: int,
    alpha: float | None,
    checkpoint_round: int,
    baselines: tuple[Baseline, ...] | None = None,
) -> CheckpointArtifactCellStatus:
    cell = TrainingCellId(regime=regime, seed=seed, alpha=alpha)
    layout = ArtifactLayout(base_dir=artifact_root, regime=regime)
    expected_baselines = baselines or controlled_baselines_for_regime(regime)
    checkpoint_path = (
        layout.checkpoint_dir_for_round(cell, checkpoint_round)
        / ArtifactFile.MODEL_CHECKPOINT
    )
    score_manifest = layout.score_cell_for_round(cell, checkpoint_round).manifest_path
    result_statuses: list[tuple[Baseline, CheckpointArtifactStatus]] = []
    for baseline in expected_baselines:
        run = BaselineRunId(cell=cell, baseline=baseline)
        metrics_path = layout.baseline_run_for_round(run, checkpoint_round).metrics_path
        result_statuses.append((baseline, _file_status(metrics_path)))
    return CheckpointArtifactCellStatus(
        regime=regime,
        seed=seed,
        alpha=alpha,
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
