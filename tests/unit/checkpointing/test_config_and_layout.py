from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

from pathlib import Path

import pytest
from pydantic import ValidationError

from datp.artifacts.layout import ArtifactLayout
from datp.checkpointing.enums import (
    CheckpointArtifactPathMode,
    CheckpointConvergenceMode,
    CheckpointProtocolMode,
    PrimaryCheckpointSelectionRule,
)
from datp.config.models import CheckpointProtocolConfig
from datp.config.stages import ExperimentStage
from datp.core.identity import PolicyRunId, TrainingCellId

_STAGE = ExperimentStage.NBAIOT_MAIN


def _checkpoint_config(
    *,
    milestones: tuple[int, ...] = (25, 50, 75, 100, 125, 150, 200),
    max_rounds: int = 200,
) -> CheckpointProtocolConfig:
    return CheckpointProtocolConfig(
        mode=CheckpointProtocolMode.ENABLED,
        max_rounds=max_rounds,
        milestones=milestones,
        convergence_mode=CheckpointConvergenceMode.LOG_ONLY,
        primary_selection_rule=PrimaryCheckpointSelectionRule.GLOBAL_LOWER_TAIL_TRADEOFF_FROM_NBAIOT_MAIN,
        artifact_path_mode=CheckpointArtifactPathMode.ROUND_AWARE,
    )


def test_checkpoint_config_accepts_milestones() -> None:
    cfg = _checkpoint_config()

    assert cfg.enabled is True
    assert cfg.max_rounds == 200
    assert cfg.milestones == (25, 50, 75, 100, 125, 150, 200)
    assert cfg.convergence_mode == CheckpointConvergenceMode.LOG_ONLY


@pytest.mark.parametrize(
    ("milestones", "max_rounds"),
    [
        ((), 200),
        ((25, 25), 200),
        ((50, 25), 200),
        ((0, 25), 200),
        ((25, 250), 200),
        ((25, 50), 40),
    ],
)
def test_checkpoint_config_rejects_invalid_milestones(
    milestones: tuple[int, ...], max_rounds: int
) -> None:
    with pytest.raises(ValidationError):
        _checkpoint_config(milestones=milestones, max_rounds=max_rounds)


def test_round_aware_paths_include_round(tmp_path: Path) -> None:
    layout = ArtifactLayout(base_dir=tmp_path, stage=_STAGE)
    cell = TrainingCellId(stage=_STAGE, seed=7)
    run = PolicyRunId(cell=cell, policy=ThresholdPolicy.LOCAL_THRESHOLD)

    checkpoint_dir = layout.checkpoint_dir_for_round(cell, 50)
    score_dir = layout.score_cell_for_round(cell, 50).score_dir
    result_dir = layout.policy_run_for_round(run, 50).result_dir

    assert checkpoint_dir == tmp_path / "checkpoints" / "nbaiot_main" / "seed_7" / "round_50"
    assert score_dir == tmp_path / "scores" / "nbaiot_main" / "seed_7" / "round_50"
    assert result_dir == tmp_path / "results" / "nbaiot_main" / "local_threshold" / "seed_7" / "round_50"
    assert "outputs" not in checkpoint_dir.parts
