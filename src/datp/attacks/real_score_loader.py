"""Load real DATP-generated N-BaIoT clean scores into a score collection.

Read-only: wraps the existing DATP scoring loaders (``cal_loading``,
``scoring.loading``) and the canonical artifact layout; performs no writes,
no poisoning, no retraining. One collection is built per training seed.
"""

from __future__ import annotations

from pathlib import Path

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.poison_names import N_MIN
from datp.attacks.score_containers import ScoreCollection, build_score_collection
from datp.config.stages import ExperimentStage
from datp.core.enums import ScoringStage
from datp.core.identity import TrainingCellId
from datp.scoring.cal_loading import load_main_cal_errors
from datp.scoring.loading import load_parquets_from_dir


def load_real_score_collection(
    *,
    stage: ExperimentStage,
    seed: int,
    base_dir: Path,
    checkpoint_round: int | None = None,
    n_min: int = N_MIN,
) -> ScoreCollection:
    """Build a ``ScoreCollection`` from real per-client DATP score artifacts.

    Raises ``FileNotFoundError`` if calibration, test_benign, or test_attack
    artifacts are missing for the given (stage, seed) training cell.
    """
    cal_errors = load_main_cal_errors(stage, seed, base_dir, checkpoint_round)

    cell = TrainingCellId(stage=stage, seed=seed)
    layout = ArtifactLayout(base_dir=base_dir, stage=stage)
    score_paths = (
        layout.score_cell_for_round(cell, checkpoint_round)
        if checkpoint_round is not None
        else layout.score_cell(cell)
    )
    score_dir = score_paths.score_dir
    test_benign = load_parquets_from_dir(
        score_dir / ScoringStage.TEST_BENIGN.value, allow_empty=False
    )
    test_attack = load_parquets_from_dir(
        score_dir / ScoringStage.TEST_ATTACK.value, allow_empty=False
    )

    client_scores = {
        client_id: (cal, test_benign[client_id], test_attack[client_id])
        for client_id, cal in cal_errors.items()
    }
    return build_score_collection(client_scores, n_min=n_min)
