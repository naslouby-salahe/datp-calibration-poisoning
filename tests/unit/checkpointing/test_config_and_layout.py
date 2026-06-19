from __future__ import annotations

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
from datp.core.enums import Baseline, Regime
from datp.core.identity import BaselineRunId, TrainingCellId


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
        primary_selection_regime=Regime.A,
        primary_selection_rule=PrimaryCheckpointSelectionRule.GLOBAL_LOWER_TAIL_TRADEOFF_FROM_REGIME_A,
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


def test_round_aware_paths_include_round_and_temp_root(tmp_path: Path) -> None:
    layout = ArtifactLayout(base_dir=tmp_path, regime=Regime.A)
    cell = TrainingCellId(regime=Regime.A, seed=7, alpha=None)
    run = BaselineRunId(cell=cell, baseline=Baseline.B2)

    checkpoint_dir = layout.checkpoint_dir_for_round(cell, 50)
    score_dir = layout.score_cell_for_round(cell, 50).score_dir
    result_dir = layout.baseline_run_for_round(run, 50).result_dir

    assert checkpoint_dir == tmp_path / "checkpoints" / "a" / "seed_7" / "round_50"
    assert score_dir == tmp_path / "scores" / "a" / "seed_7" / "round_50"
    assert result_dir == tmp_path / "results" / "a" / "b2" / "seed_7" / "round_50"
    assert "outputs" not in checkpoint_dir.parts
