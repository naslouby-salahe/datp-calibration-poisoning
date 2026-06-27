"""Score loading from Parquet artifacts and ScoreProvider for test-time evaluation."""

from pathlib import Path

import numpy as np
import polars as pl

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import PathToken
from datp.config.models import ExperimentStage
from datp.core.enums import ScoringStage
from datp.core.identity import TrainingCellId
from datp.data.common.schemas import validate_score_artifact
from datp.scoring.manifest import SCORE_COLUMN

_MODULE = "scoring.loading"


def read_score_column(path: Path) -> np.ndarray:
    """Read and validate a single Parquet score file, returning the score column as float64."""
    validate_score_artifact(path)
    return pl.read_parquet(path).get_column(SCORE_COLUMN).to_numpy().astype(np.float64)


def load_parquets_from_dir(
    directory: Path, *, allow_empty: bool = True
) -> dict[str, np.ndarray]:
    """Load all Parquet score files from a directory into {stem: ndarray}."""
    if not directory.is_dir():
        raise FileNotFoundError(f"[{_MODULE}] score directory {directory} not found.")

    parquets = {
        pf.stem: read_score_column(pf)
        for pf in sorted(directory.glob(PathToken.PARQUET_GLOB))
    }
    if not allow_empty and not parquets:
        raise FileNotFoundError(
            f"[{_MODULE}] No parquet score artifacts at {directory}. Expected: at least one .parquet score artifact. Got: none."
        )

    return parquets


def load_main_cal_errors(
    stage: ExperimentStage, seed: int, base_dir: Path, checkpoint_round: int | None
) -> dict[str, np.ndarray]:
    """Load main calibration error scores for a given stage, seed, and checkpoint round."""
    cell = TrainingCellId(stage=stage, seed=seed)
    layout = ArtifactLayout(base_dir=base_dir, stage=stage)
    score_paths = (
        layout.score_cell_for_round(cell, checkpoint_round)
        if checkpoint_round is not None
        else layout.score_cell(cell)
    )
    return load_parquets_from_dir(
        score_paths.score_dir / ScoringStage.CAL.value, allow_empty=False
    )


class ScoreProvider:
    """Lazy loader for per-client, per-stage score Parquet files from a score root."""

    def __init__(self, score_root: Path) -> None:
        """Initialize with the root directory containing per-stage score subdirectories."""
        self._root = score_root

    @property
    def score_root(self) -> Path:
        """The root directory for score artifacts."""
        return self._root

    def load(self, client_id: str, stage: ScoringStage) -> np.ndarray:
        """Load a single client/stage score file as a float64 array."""
        path = self._root / stage.value / f"{client_id}{PathToken.PARQUET_EXT}"
        if not path.exists():
            raise FileNotFoundError(
                f"[{_MODULE}] Missing {stage} score artifact for client '{client_id}'. Expected: {str(path)}. Got: absent."
            )
        return read_score_column(path)

    def load_test_scores(self, client_id: str) -> tuple[np.ndarray, np.ndarray]:
        """Load both TEST_BENIGN and TEST_ATTACK score arrays for a single client."""
        return self.load(client_id, ScoringStage.TEST_BENIGN), self.load(
            client_id, ScoringStage.TEST_ATTACK
        )
