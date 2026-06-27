"""Filesystem discovery of metrics.json paths and score cells for audit consumption."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.names import ArtifactDir, ArtifactFile, PathToken
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.identity import PolicyRunId, TrainingCellId


def completed_metric_paths(base_dir: Path) -> list[Path]:
    """Return all ``metrics.json`` paths under ``<base_dir>/results/``."""
    return sorted(
        (base_dir / ArtifactDir.RESULTS).glob(
            f"*/*/{PathToken.SEED_PREFIX}*/**/{ArtifactFile.METRICS}"
        )
    )


def _parse_seed(segment: str) -> int:
    """Extract seed integer from a ``seed_N`` path segment."""
    if not segment.startswith(PathToken.SEED_PREFIX):
        raise ValueError(
            f"Expected seed segment with prefix {PathToken.SEED_PREFIX!r}, got {segment!r}"
        )
    return int(segment.removeprefix(PathToken.SEED_PREFIX))


def parse_metric_path(base_dir: Path, path: Path) -> PolicyRunId:
    """Parse ``<results_root>/<stage>/<policy>/seed_N/metrics.json`` into a ``PolicyRunId``."""
    parts = path.relative_to(base_dir / ArtifactDir.RESULTS).parts
    return PolicyRunId(
        cell=TrainingCellId(
            stage=ExperimentStage(parts[0]), seed=_parse_seed(parts[2])
        ),
        policy=ThresholdPolicy(parts[1]),
    )


@dataclass(frozen=True, slots=True)
class ScoreCellLocation:
    """Identifies one score cell on disk: ``<base_dir>/scores/<stage>/seed_N/``."""

    cell: TrainingCellId
    cell_dir: Path

    @property
    def stage(self) -> ExperimentStage:
        """The experiment stage of this score cell."""
        return self.cell.stage

    @property
    def seed(self) -> int:
        """The training seed of this score cell."""
        return self.cell.seed


def iter_score_cells(base_dir: Path) -> list[ScoreCellLocation]:
    """Enumerate score cells under ``<base_dir>/scores/``."""
    root = base_dir / ArtifactDir.SCORES
    return [
        parse_score_cell_dir(root, p.parent)
        for p in sorted(
            root.glob(f"*/{PathToken.SEED_PREFIX}*/{ArtifactFile.SCORING_MANIFEST}")
        )
    ]


def parse_score_cell_dir(scores_root: Path, cell_dir: Path) -> ScoreCellLocation:
    """Parse ``<scores_root>/<stage>/seed_N/`` into a ``ScoreCellLocation``."""
    parts = cell_dir.relative_to(scores_root).parts
    return ScoreCellLocation(
        cell=TrainingCellId(
            stage=ExperimentStage(parts[0]), seed=_parse_seed(parts[1])
        ),
        cell_dir=cell_dir,
    )
