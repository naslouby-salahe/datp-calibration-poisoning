from __future__ import annotations

from pathlib import Path

import pytest

from datp.artifacts import ArtifactLayout
from datp.config import ExperimentStage
from datp.core import PolicyRunId, TrainingCellId
from datp.enums import ArtifactDir, ThresholdPolicy

_OUTPUTS = Path(ArtifactDir.OUTPUTS)


def _run(stage: ExperimentStage, policy: ThresholdPolicy, seed: int):
    """Build a PolicyRunId for the given stage, policy, and seed."""
    return PolicyRunId(
        cell=TrainingCellId(stage=stage, seed=seed),
        policy=policy,
    )


def _score_cell(stage: ExperimentStage, seed: int):
    """Build a TrainingCellId for the given stage and seed."""
    return TrainingCellId(stage=stage, seed=seed)


@pytest.mark.integration
def test_canonical_path() -> None:
    """Result and score paths follow the canonical policy-seed layout."""
    layout_a = ArtifactLayout(base_dir=_OUTPUTS, stage=ExperimentStage.NBAIOT_MAIN)

    rp = layout_a.policy_run(
        _run(ExperimentStage.NBAIOT_MAIN, ThresholdPolicy.GLOBAL_THRESHOLD, 0)
    ).result_dir
    parts = rp.parts
    assert "global_threshold" in parts, (
        f"result_dir should contain policy 'global_threshold': {rp}"
    )
    assert parts[-2] == "global_threshold"
    assert parts[-3] == "nbaiot_main"
    assert parts[-1].startswith("seed_")

    sp = layout_a.score_cell(_score_cell(ExperimentStage.NBAIOT_MAIN, 0)).score_dir
    assert "global_threshold" not in sp.parts
    assert "local_threshold" not in sp.parts

    rp_check = layout_a.policy_run(
        _run(ExperimentStage.NBAIOT_MAIN, ThresholdPolicy.GLOBAL_THRESHOLD, 42)
    ).result_dir
    expected_suffix = "results/nbaiot_main/global_threshold/seed_42"
    assert str(rp_check).endswith(expected_suffix), (
        f"Expected path ending with '{expected_suffix}', got '{rp_check}'"
    )

    sp_check = layout_a.score_cell(
        _score_cell(ExperimentStage.NBAIOT_MAIN, 42)
    ).score_dir
    expected_score_suffix = "scores/nbaiot_main/seed_42"
    assert str(sp_check).endswith(expected_score_suffix), (
        f"Expected path ending with '{expected_score_suffix}', got '{sp_check}'"
    )
