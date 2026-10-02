from datp.types import (
    ClientId,
    RandomSeed,
    RoundIndex,
    ScoreVector,
)

from pathlib import Path

import numpy as np
import polars as pl

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import PathToken
from datp.config.models import ExperimentStage
from datp.core.enums import ScoringStage
from datp.core.identity import TrainingCellId
from datp.data.common.schemas import validate_score_artifact
from datp.scoring.manifest import ScoringColumn

_MODULE = "scoring.loading"


def read_score_column(path: Path) -> ScoreVector:
    validate_score_artifact(path)
    return pl.read_parquet(path).get_column(ScoringColumn.RECONSTRUCTION_ERROR).to_numpy().astype(np.float64)


def load_parquets_from_dir(
    directory: Path, *, allow_empty: bool = True
) -> dict[ClientId, ScoreVector]:
    if not directory.is_dir():
        raise FileNotFoundError(f"[{_MODULE}] score directory {directory} not found.")

    parquets = {
        ClientId(pf.stem): read_score_column(pf)
        for pf in sorted(directory.glob(PathToken.PARQUET_GLOB))
    }
    if not allow_empty and not parquets:
        raise FileNotFoundError(
            f"[{_MODULE}] No parquet score artifacts at {directory}. Expected: at least one .parquet score artifact. Got: none."
        )

    return parquets


def load_main_cal_errors(
    stage: ExperimentStage, seed: RandomSeed, base_dir: Path, checkpoint_round: RoundIndex | None
) -> dict[ClientId, ScoreVector]:
    cell = TrainingCellId(stage=stage, seed=RandomSeed(seed))
    layout = ArtifactLayout(base_dir=base_dir, stage=stage)
    score_paths = (
        layout.score_cell(cell, checkpoint_round)
        if checkpoint_round is not None
        else layout.score_cell(cell)
    )
    calibration_dir = score_paths.score_dir / ScoringStage.CAL
    if not calibration_dir.is_dir():
        raise FileNotFoundError(
            f"[{_MODULE}] score directory {calibration_dir} not found."
        )
    score_files = sorted(calibration_dir.glob(PathToken.PARQUET_GLOB))
    if not score_files:
        raise FileNotFoundError(
            f"[{_MODULE}] No parquet score artifacts at {calibration_dir}. Expected: at least one .parquet score artifact. Got: none."
        )
    return {
        client_id: read_score_column(
            layout.score_file(cell, ScoringStage.CAL, client_id, checkpoint_round)
        )
        for score_file in score_files
        if (client_id := ClientId(score_file.stem))
    }


class ScoreProvider:

    def __init__(self, score_root: Path) -> None:
        self.score_root = score_root

    def load(self, client_id: ClientId, stage: ScoringStage) -> ScoreVector:
        path = self.score_root / stage / f"{client_id}{PathToken.PARQUET_EXT}"
        if not path.exists():
            raise FileNotFoundError(
                f"[{_MODULE}] Missing {stage} score artifact for client '{client_id}'. Expected: {path}. Got: absent."
            )
        return read_score_column(path)

    def load_test_scores(self, client_id: ClientId) -> tuple[ScoreVector, ScoreVector]:
        return self.load(client_id, ScoringStage.TEST_BENIGN), self.load(
            client_id, ScoringStage.TEST_ATTACK
        )
