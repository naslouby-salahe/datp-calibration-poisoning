from __future__ import annotations

from pathlib import Path

import numpy as np

from datp.config.stages import ExperimentStage
from datp.artifacts.layout import ArtifactLayout
from datp.core.enums import ScoringStage
from datp.core.identity import TrainingCellId
from datp.core.logging import get_logger
from datp.scoring.loading import load_parquets_from_dir

logger = get_logger(__name__)


def load_main_cal_errors(
    stage: ExperimentStage,
    seed: int,
    base_dir: Path,
    checkpoint_round: int | None,
) -> dict[str, np.ndarray]:
    """Load calibration reconstruction errors for one training cell.

    Resolves the canonical score directory from *stage*, *seed*, and
    *base_dir*, then loads all calibration-stage ``.parquet`` files as
    ``{client_id: ndarray}``.

    Raises ``FileNotFoundError`` when the calibration directory is
    missing or contains no parquet files.
    """
    cell = TrainingCellId(stage=stage, seed=seed)
    layout = ArtifactLayout(base_dir=base_dir, stage=stage)
    score_paths = (
        layout.score_cell_for_round(cell, checkpoint_round)
        if checkpoint_round is not None
        else layout.score_cell(cell)
    )
    score_dir = score_paths.score_dir
    cal_dir = score_dir / ScoringStage.CAL.value
    client_errors = load_parquets_from_dir(cal_dir, allow_empty=False)
    logger.info(
        "loaded calibration errors",
        n_clients=len(client_errors),
        path=str(cal_dir),
    )
    return client_errors
