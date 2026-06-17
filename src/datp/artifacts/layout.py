from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.names import ArtifactDir, ArtifactFile, PathToken
from datp.core.enums import Regime, ScoringStage
from datp.core.identity import (
    BaselineRunId,
    TrainingCellId,
    format_alpha_dir,
    seed_segment,
)


def _seed_segment(seed: int, alpha: float | None) -> Path:
    p = Path(seed_segment(seed))
    if alpha is not None:
        p = p / format_alpha_dir(alpha)
    return p


def _round_segment(checkpoint_round: int) -> Path:
    if not isinstance(checkpoint_round, int) or isinstance(checkpoint_round, bool):
        raise TypeError(f"checkpoint_round must be int, got {type(checkpoint_round).__name__}")
    if checkpoint_round <= 0:
        raise ValueError("checkpoint_round must be positive")
    return Path(f"{PathToken.ROUND_PREFIX}{checkpoint_round}")


def _round_aware_segment(seed: int, alpha: float | None, checkpoint_round: int) -> Path:
    return _seed_segment(seed, alpha) / _round_segment(checkpoint_round)


@dataclass(frozen=True, slots=True)
class ScoreCellPaths:
    """Resolved paths for a shared score cell (no baseline dimension)."""

    cell: TrainingCellId
    checkpoint_dir: Path
    score_dir: Path
    manifest_path: Path
    checkpoint_round: int | None = None



@dataclass(frozen=True, slots=True)
class BaselineRunPaths:
    """Resolved paths for a baseline evaluation run."""

    run: BaselineRunId
    result_dir: Path
    log_dir: Path
    metrics_path: Path
    checkpoint_round: int | None = None


@dataclass(frozen=True, slots=True)
class ArtifactLayout:
    """Canonical artifact paths for one regime.

    Checkpoint and score paths intentionally omit baseline: B1-B4 share the
    trained encoder and scores.
    """

    base_dir: Path
    regime: Regime

    @property
    def _checkpoint_root(self) -> Path:
        return self.base_dir / ArtifactDir.CHECKPOINTS / self.regime.value

    @property
    def _score_root(self) -> Path:
        return self.base_dir / ArtifactDir.SCORES / self.regime.value

    @property
    def _result_root(self) -> Path:
        return self.base_dir / ArtifactDir.RESULTS / self.regime.value

    @property
    def _log_root(self) -> Path:
        return self.base_dir / ArtifactDir.LOGS / self.regime.value

    def checkpoint_dir(self, cell: TrainingCellId) -> Path:
        return self._checkpoint_root / _seed_segment(cell.seed, cell.alpha)

    def checkpoint_dir_for_round(
        self, cell: TrainingCellId, checkpoint_round: int
    ) -> Path:
        return self._checkpoint_root / _round_aware_segment(
            cell.seed, cell.alpha, checkpoint_round
        )

    def score_cell(self, cell: TrainingCellId) -> ScoreCellPaths:
        seg = _seed_segment(cell.seed, cell.alpha)
        score_dir = self._score_root / seg
        return ScoreCellPaths(
            cell=cell,
            checkpoint_dir=self._checkpoint_root / seg,
            score_dir=score_dir,
            manifest_path=score_dir / ArtifactFile.SCORING_MANIFEST,
        )

    def score_cell_for_round(
        self, cell: TrainingCellId, checkpoint_round: int
    ) -> ScoreCellPaths:
        seg = _round_aware_segment(cell.seed, cell.alpha, checkpoint_round)
        score_dir = self._score_root / seg
        return ScoreCellPaths(
            cell=cell,
            checkpoint_dir=self._checkpoint_root / seg,
            score_dir=score_dir,
            manifest_path=score_dir / ArtifactFile.SCORING_MANIFEST,
            checkpoint_round=checkpoint_round,
        )

    def baseline_run(self, run: BaselineRunId) -> BaselineRunPaths:
        seg = _seed_segment(run.seed, run.alpha)
        result_dir = self._result_root / run.baseline.value / seg
        return BaselineRunPaths(
            run=run,
            result_dir=result_dir,
            metrics_path=result_dir / ArtifactFile.METRICS,
            log_dir=self._log_root / run.baseline.value / seg,
        )

    def baseline_run_for_round(
        self, run: BaselineRunId, checkpoint_round: int
    ) -> BaselineRunPaths:
        seg = _round_aware_segment(run.seed, run.alpha, checkpoint_round)
        result_dir = self._result_root / run.baseline.value / seg
        return BaselineRunPaths(
            run=run,
            result_dir=result_dir,
            metrics_path=result_dir / ArtifactFile.METRICS,
            log_dir=self._log_root / run.baseline.value / seg,
            checkpoint_round=checkpoint_round,
        )

    def score_file(self, cell: TrainingCellId, stage: ScoringStage, client_id: str) -> Path:
        """Return the canonical path for a client's score parquet file.

        Scores are shared across B1-B4 (no baseline dimension).
        Path: <score_dir>/<stage>/<client_id>.parquet
        """
        return self.score_cell(cell).score_dir / stage / f"{client_id}{PathToken.PARQUET_EXT}"

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
