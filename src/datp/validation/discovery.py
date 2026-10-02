from __future__ import annotations

from datp.types import (
    NarrativeText,
    RandomSeed,
)


from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.names import ArtifactDir, ArtifactFile, PathToken
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.identity import PolicyRunId, TrainingCellId


def completed_metric_paths(base_dir: Path) -> list[Path]:
    return sorted(
        (base_dir / ArtifactDir.RESULTS).glob(
            f"*/*/{PathToken.SEED_PREFIX}*/**/{ArtifactFile.METRICS}"
        )
    )


def _parse_seed(segment: NarrativeText) -> RandomSeed:
    if not segment.startswith(PathToken.SEED_PREFIX):
        raise ValueError(
            f"Expected seed segment with prefix {PathToken.SEED_PREFIX!r}, got {segment!r}"
        )
    return RandomSeed(int(segment.removeprefix(PathToken.SEED_PREFIX)))


def parse_metric_path(base_dir: Path, path: Path) -> PolicyRunId:
    parts = path.relative_to(base_dir / ArtifactDir.RESULTS).parts
    return PolicyRunId(
        cell=TrainingCellId(
            stage=ExperimentStage(parts[0]), seed=_parse_seed(parts[2])
        ),
        policy=ThresholdPolicy(parts[1]),
    )


@dataclass(frozen=True, slots=True)
class ScoreCellLocation:

    cell: TrainingCellId
    cell_dir: Path

    @property
    def seed(self) -> RandomSeed:
        return self.cell.seed


def iter_score_cells(base_dir: Path) -> list[ScoreCellLocation]:
    root = base_dir / ArtifactDir.SCORES
    return [
        parse_score_cell_dir(root, p.parent)
        for p in sorted(
            root.glob(f"*/{PathToken.SEED_PREFIX}*/{ArtifactFile.SCORING_MANIFEST}")
        )
    ]


def parse_score_cell_dir(scores_root: Path, cell_dir: Path) -> ScoreCellLocation:
    parts = cell_dir.relative_to(scores_root).parts
    return ScoreCellLocation(
        cell=TrainingCellId(
            stage=ExperimentStage(parts[0]), seed=_parse_seed(parts[1])
        ),
        cell_dir=cell_dir,
    )
