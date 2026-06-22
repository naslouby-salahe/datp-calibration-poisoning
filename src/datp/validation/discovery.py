from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from dataclasses import dataclass
from pathlib import Path

from datp.artifacts.names import (
    ArtifactDir,
    ArtifactFile,
    PathToken,
)
from datp.config.stages import ExperimentStage
from datp.core.identity import (
    PolicyRunId,
    TrainingCellId,
)


def completed_metric_paths(base_dir: Path) -> list[Path]:
    """Return all ``metrics.json`` paths under ``<base_dir>/results/``."""
    return sorted(
        (base_dir / ArtifactDir.RESULTS).glob(
            f"*/*/{PathToken.SEED_PREFIX}*/**/{ArtifactFile.METRICS}"
        )
    )


def _parse_seed(parts: tuple[str, ...], seed_idx: int) -> int:
    """Extract seed integer from a ``seed_N`` path segment."""
    seed_seg = parts[seed_idx]
    if not seed_seg.startswith(PathToken.SEED_PREFIX):
        raise ValueError(
            f"Expected seed segment with prefix {PathToken.SEED_PREFIX!r}, got {seed_seg!r}"
        )
    return int(seed_seg.removeprefix(PathToken.SEED_PREFIX))


def parse_metric_path(base_dir: Path, path: Path) -> PolicyRunId:
    """Parse ``<results_root>/<stage>/<policy>/seed_N/metrics.json`` into a ``PolicyRunId``."""
    rel = path.relative_to(base_dir / ArtifactDir.RESULTS)
    parts = rel.parts
    stage = ExperimentStage(parts[0])
    policy = ThresholdPolicy(parts[1])
    seed = _parse_seed(parts, seed_idx=2)
    return PolicyRunId(
        cell=TrainingCellId(stage=stage, seed=seed),
        policy=policy,
    )


@dataclass(frozen=True, slots=True)
class ScoreCellLocation:
    """Identifies one score cell on disk: ``<base_dir>/scores/<stage>/seed_N/``."""

    cell: TrainingCellId
    cell_dir: Path

    @property
    def stage(self) -> ExperimentStage:
        return self.cell.stage

    @property
    def seed(self) -> int:
        return self.cell.seed


def iter_score_cells(base_dir: Path) -> list[ScoreCellLocation]:
    """Enumerate score cells (directories containing ``scoring_manifest.json``) under ``<base_dir>/scores/``."""
    scores_root = base_dir / ArtifactDir.SCORES
    if not scores_root.exists():
        return []
    cells: list[ScoreCellLocation] = []
    for manifest_path in sorted(
        scores_root.glob(f"*/{PathToken.SEED_PREFIX}*/{ArtifactFile.SCORING_MANIFEST}")
    ):
        cells.append(parse_score_cell_dir(scores_root, manifest_path.parent))
    return cells


def parse_score_cell_dir(scores_root: Path, cell_dir: Path) -> ScoreCellLocation:
    """Parse ``<scores_root>/<stage>/seed_N/`` into a ``ScoreCellLocation``."""
    rel = cell_dir.relative_to(scores_root)
    parts = rel.parts
    stage = ExperimentStage(parts[0])
    seed = _parse_seed(parts, seed_idx=1)
    return ScoreCellLocation(
        cell=TrainingCellId(stage=stage, seed=seed),
        cell_dir=cell_dir,
    )
