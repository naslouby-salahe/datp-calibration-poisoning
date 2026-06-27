"""Resolved filesystem paths for checkpoints, scores, results, and logs by stage."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.names import ArtifactDir, ArtifactFile, PathToken
from datp.config.models import ExperimentStage
from datp.core.enums import ScoringStage
from datp.core.identity import (
    PolicyRunId,
    TrainingCellId,
    seed_segment,
)


def _get_seg(seed: int, checkpoint_round: int | None = None) -> Path:
    """Build the path segment for a seed, optionally including a checkpoint round."""
    seg = Path(seed_segment(seed))
    if checkpoint_round is not None:
        if checkpoint_round <= 0:
            raise ValueError("checkpoint_round must be positive")
        seg /= f"{PathToken.ROUND_PREFIX}{checkpoint_round}"
    return seg


@dataclass(frozen=True, slots=True)
class ScoreCellPaths:
    """Resolved paths for a scoring cell."""

    cell: TrainingCellId
    checkpoint_dir: Path
    score_dir: Path
    manifest_path: Path
    checkpoint_round: int | None = None


@dataclass(frozen=True, slots=True)
class PolicyRunPaths:
    """Resolved paths for a single policy run."""

    run: PolicyRunId
    result_dir: Path
    log_dir: Path
    metrics_path: Path
    checkpoint_round: int | None = None


@dataclass(frozen=True, slots=True)
class ArtifactLayout:
    """Directory layout for checkpoints, scores, results, and logs by stage."""

    base_dir: Path
    stage: ExperimentStage

    def _root(self, d_type: str) -> Path:
        """Return the root directory for a given artifact type and stage."""
        return self.base_dir / d_type / self.stage.value

    def checkpoint_dir(
        self, cell: TrainingCellId, checkpoint_round: int | None = None
    ) -> Path:
        """Return the checkpoint directory for a training cell and optional round."""
        return self._root(ArtifactDir.CHECKPOINTS) / _get_seg(
            cell.seed, checkpoint_round
        )

    def checkpoint_dir_for_round(
        self, cell: TrainingCellId, checkpoint_round: int
    ) -> Path:
        """Return the checkpoint directory for a specific round."""
        return self.checkpoint_dir(cell, checkpoint_round)

    def score_cell(
        self, cell: TrainingCellId, checkpoint_round: int | None = None
    ) -> ScoreCellPaths:
        """Return ScoreCellPaths for a training cell and optional round."""
        seg = _get_seg(cell.seed, checkpoint_round)
        score_dir = self._root(ArtifactDir.SCORES) / seg
        return ScoreCellPaths(
            cell=cell,
            checkpoint_dir=self._root(ArtifactDir.CHECKPOINTS) / seg,
            score_dir=score_dir,
            manifest_path=score_dir / ArtifactFile.SCORING_MANIFEST,
            checkpoint_round=checkpoint_round,
        )

    def score_cell_for_round(
        self, cell: TrainingCellId, checkpoint_round: int
    ) -> ScoreCellPaths:
        """Return ScoreCellPaths for a specific round."""
        return self.score_cell(cell, checkpoint_round)

    def policy_run(
        self, run: PolicyRunId, checkpoint_round: int | None = None
    ) -> PolicyRunPaths:
        """Return PolicyRunPaths for a policy run and optional round."""
        seg = _get_seg(run.seed, checkpoint_round)
        policy_val = run.policy.value
        result_dir = self._root(ArtifactDir.RESULTS) / policy_val / seg
        return PolicyRunPaths(
            run=run,
            result_dir=result_dir,
            metrics_path=result_dir / ArtifactFile.METRICS,
            log_dir=self._root(ArtifactDir.LOGS) / policy_val / seg,
            checkpoint_round=checkpoint_round,
        )

    def policy_run_for_round(
        self, run: PolicyRunId, checkpoint_round: int
    ) -> PolicyRunPaths:
        """Return PolicyRunPaths for a specific round."""
        return self.policy_run(run, checkpoint_round)

    def score_file(
        self,
        cell: TrainingCellId,
        stage: ScoringStage,
        client_id: str,
        checkpoint_round: int | None = None,
    ) -> Path:
        """Return the path to a Parquet score file for a client, stage, and optional round."""
        return (
            self.score_cell(cell, checkpoint_round).score_dir
            / stage
            / f"{client_id}{PathToken.PARQUET_EXT}"
        )

    def score_file_for_round(
        self,
        cell: TrainingCellId,
        stage: ScoringStage,
        client_id: str,
        checkpoint_round: int,
    ) -> Path:
        """Return the path to a Parquet score file for a specific round."""
        return self.score_file(cell, stage, client_id, checkpoint_round)
