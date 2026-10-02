
from __future__ import annotations
from datp.types import ClientId
from datp.types import (
    RandomSeed,
    RoundIndex,
)

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


def _get_seg(seed: RandomSeed, checkpoint_round: RoundIndex | None = None) -> Path:
    seg = Path(seed_segment(seed))
    if checkpoint_round is not None:
        if checkpoint_round <= 0:
            raise ValueError("checkpoint_round must be positive")
        seg /= f"{PathToken.ROUND_PREFIX}{checkpoint_round}"
    return seg


def nbaiot_main_manifest_path(base_dir: Path) -> Path:
    return (
        poisoning_output_root(base_dir)
        / ArtifactFile.NBAIOT_MAIN_MANIFEST
    )


def poisoning_output_root(base_dir: Path) -> Path:
    return Path(base_dir) / ArtifactDir.CALIBRATION_POISONING


def sensitivity_manifest_path(base_dir: Path) -> Path:
    return poisoning_output_root(base_dir) / ArtifactFile.SENSITIVITY_MANIFEST


@dataclass(frozen=True, slots=True)
class ScoreCellPaths:

    cell: TrainingCellId
    checkpoint_dir: Path
    score_dir: Path
    manifest_path: Path
    checkpoint_round: RoundIndex | None = None


@dataclass(frozen=True, slots=True)
class PolicyRunPaths:

    run: PolicyRunId
    result_dir: Path
    log_dir: Path
    metrics_path: Path
    checkpoint_round: RoundIndex | None = None


@dataclass(frozen=True, slots=True)
class ArtifactLayout:

    base_dir: Path
    stage: ExperimentStage

    def _root(self, artifact_dir: ArtifactDir) -> Path:
        return self.base_dir / artifact_dir / self.stage

    def checkpoint_dir(
        self, cell: TrainingCellId, checkpoint_round: RoundIndex | None = None
    ) -> Path:
        return self._root(ArtifactDir.CHECKPOINTS) / _get_seg(
            cell.seed, checkpoint_round
        )

    def score_cell(
        self, cell: TrainingCellId, checkpoint_round: RoundIndex | None = None
    ) -> ScoreCellPaths:
        seg = _get_seg(cell.seed, checkpoint_round)
        score_dir = self._root(ArtifactDir.SCORES) / seg
        return ScoreCellPaths(
            cell=cell,
            checkpoint_dir=self._root(ArtifactDir.CHECKPOINTS) / seg,
            score_dir=score_dir,
            manifest_path=score_dir / ArtifactFile.SCORING_MANIFEST,
            checkpoint_round=checkpoint_round,
        )

    def score_file(
        self,
        cell: TrainingCellId,
        stage: ScoringStage,
        client_id: ClientId,
        checkpoint_round: RoundIndex | None = None,
    ) -> Path:
        return (
            self.score_cell(cell, checkpoint_round).score_dir
            / stage
            / f"{client_id}{PathToken.PARQUET_EXT}"
        )

    def policy_run(
        self, run: PolicyRunId, checkpoint_round: RoundIndex | None = None
    ) -> PolicyRunPaths:
        seg = _get_seg(run.seed, checkpoint_round)
        policy_val = run.policy
        result_dir = self._root(ArtifactDir.RESULTS) / policy_val / seg
        return PolicyRunPaths(
            run=run,
            result_dir=result_dir,
            metrics_path=result_dir / ArtifactFile.METRICS,
            log_dir=self._root(ArtifactDir.LOGS) / policy_val / seg,
            checkpoint_round=checkpoint_round,
        )
