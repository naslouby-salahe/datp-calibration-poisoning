from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.names import ArtifactDir, ArtifactFile, PathToken
from datp.config.stages import ExperimentStage
from datp.core.enums import ScoringStage
from datp.core.identity import (
    PolicyRunId,
    TrainingCellId,
    seed_segment,
)


def _seed_segment(seed: int) -> Path:
    return Path(seed_segment(seed))


def _round_segment(checkpoint_round: int) -> Path:
    if checkpoint_round <= 0:
        raise ValueError("checkpoint_round must be positive")
    return Path(f"{PathToken.ROUND_PREFIX}{checkpoint_round}")


def _round_aware_segment(seed: int, checkpoint_round: int) -> Path:
    return _seed_segment(seed) / _round_segment(checkpoint_round)


@dataclass(frozen=True, slots=True)
class ScoreCellPaths:
    """Resolved paths for a shared score cell (no baseline dimension)."""

    cell: TrainingCellId
    checkpoint_dir: Path
    score_dir: Path
    manifest_path: Path
    checkpoint_round: int | None = None


@dataclass(frozen=True, slots=True)
class PolicyRunPaths:
    """Resolved paths for a policy evaluation run."""

    run: PolicyRunId
    result_dir: Path
    log_dir: Path
    metrics_path: Path
    checkpoint_round: int | None = None


@dataclass(frozen=True, slots=True)
class ScoreLayout:
    """Score/checkpoint cell paths for one experiment stage."""

    base_dir: Path
    stage: ExperimentStage

    @property
    def _checkpoint_root(self) -> Path:
        return self.base_dir / ArtifactDir.CHECKPOINTS / self.stage.value

    @property
    def _score_root(self) -> Path:
        return self.base_dir / ArtifactDir.SCORES / self.stage.value

    @property
    def checkpoint_root(self) -> Path:
        return self._checkpoint_root

    def checkpoint_dir(self, cell: TrainingCellId) -> Path:
        return self._checkpoint_root / _seed_segment(cell.seed)

    def checkpoint_dir_for_round(
        self, cell: TrainingCellId, checkpoint_round: int
    ) -> Path:
        return self._checkpoint_root / _round_aware_segment(cell.seed, checkpoint_round)

    def _score_cell_paths(
        self, cell: TrainingCellId, seg: Path, checkpoint_round: int | None = None
    ) -> ScoreCellPaths:
        score_dir = self._score_root / seg
        return ScoreCellPaths(
            cell=cell,
            checkpoint_dir=self._checkpoint_root / seg,
            score_dir=score_dir,
            manifest_path=score_dir / ArtifactFile.SCORING_MANIFEST,
            checkpoint_round=checkpoint_round,
        )

    def score_cell(self, cell: TrainingCellId) -> ScoreCellPaths:
        return self._score_cell_paths(cell, _seed_segment(cell.seed))

    def score_cell_for_round(
        self, cell: TrainingCellId, checkpoint_round: int
    ) -> ScoreCellPaths:
        return self._score_cell_paths(
            cell,
            _round_aware_segment(cell.seed, checkpoint_round),
            checkpoint_round,
        )

    def score_file(
        self, cell: TrainingCellId, stage: ScoringStage, client_id: str
    ) -> Path:
        """Return the canonical path for a client's score parquet file.

        Scores are shared across all three threshold policies (no policy dimension on score paths).
        Path: <score_dir>/<stage>/<client_id>.parquet
        """
        return (
            self.score_cell(cell).score_dir
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
        return (
            self.score_cell_for_round(cell, checkpoint_round).score_dir
            / stage
            / f"{client_id}{PathToken.PARQUET_EXT}"
        )


@dataclass(frozen=True, slots=True)
class RunLayout:
    """Policy-run result/log paths for one experiment stage."""

    base_dir: Path
    stage: ExperimentStage

    @property
    def _result_root(self) -> Path:
        return self.base_dir / ArtifactDir.RESULTS / self.stage.value

    @property
    def _log_root(self) -> Path:
        return self.base_dir / ArtifactDir.LOGS / self.stage.value

    def _policy_run_paths(
        self, run: PolicyRunId, seg: Path, checkpoint_round: int | None = None
    ) -> PolicyRunPaths:
        result_dir = self._result_root / run.policy.value / seg
        return PolicyRunPaths(
            run=run,
            result_dir=result_dir,
            metrics_path=result_dir / ArtifactFile.METRICS,
            log_dir=self._log_root / run.policy.value / seg,
            checkpoint_round=checkpoint_round,
        )

    def policy_run(self, run: PolicyRunId) -> PolicyRunPaths:
        return self._policy_run_paths(run, _seed_segment(run.seed))

    def policy_run_for_round(
        self, run: PolicyRunId, checkpoint_round: int
    ) -> PolicyRunPaths:
        return self._policy_run_paths(
            run,
            _round_aware_segment(run.seed, checkpoint_round),
            checkpoint_round,
        )


@dataclass(frozen=True, slots=True)
class ArtifactLayout:
    """Facade composing score and run artifact layouts."""

    base_dir: Path
    stage: ExperimentStage

    @property
    def _scores(self) -> ScoreLayout:
        return ScoreLayout(base_dir=self.base_dir, stage=self.stage)

    @property
    def _runs(self) -> RunLayout:
        return RunLayout(base_dir=self.base_dir, stage=self.stage)

    def checkpoint_dir(self, cell: TrainingCellId) -> Path:
        return self._scores.checkpoint_dir(cell)

    def checkpoint_dir_for_round(
        self, cell: TrainingCellId, checkpoint_round: int
    ) -> Path:
        return self._scores.checkpoint_dir_for_round(cell, checkpoint_round)

    def score_cell(self, cell: TrainingCellId) -> ScoreCellPaths:
        return self._scores.score_cell(cell)

    def score_cell_for_round(
        self, cell: TrainingCellId, checkpoint_round: int
    ) -> ScoreCellPaths:
        return self._scores.score_cell_for_round(cell, checkpoint_round)

    def policy_run(self, run: PolicyRunId) -> PolicyRunPaths:
        return self._runs.policy_run(run)

    def policy_run_for_round(
        self, run: PolicyRunId, checkpoint_round: int
    ) -> PolicyRunPaths:
        return self._runs.policy_run_for_round(run, checkpoint_round)

    def score_file(
        self, cell: TrainingCellId, stage: ScoringStage, client_id: str
    ) -> Path:
        return self._scores.score_file(cell, stage, client_id)

    def score_file_for_round(
        self,
        cell: TrainingCellId,
        stage: ScoringStage,
        client_id: str,
        checkpoint_round: int,
    ) -> Path:
        return self._scores.score_file_for_round(
            cell,
            stage,
            client_id,
            checkpoint_round,
        )
