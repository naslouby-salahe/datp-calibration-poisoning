from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy
from datp.config.stages import ExperimentStage

from pathlib import Path

import pytest

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactDir
from datp.core.identity import PolicyRunId, TrainingCellId

_OUTPUTS = Path(ArtifactDir.OUTPUTS)


def _run(stage: ExperimentStage, policy: ThresholdPolicy, seed: int):
    return PolicyRunId(
        cell=TrainingCellId(stage=stage, seed=seed),
        policy=policy,
    )


def _score_cell(stage: ExperimentStage, seed: int):
    return TrainingCellId(stage=stage, seed=seed)


@pytest.mark.integration
def test_canonical_path() -> None:
    layout_a = ArtifactLayout(base_dir=_OUTPUTS, stage=ExperimentStage.NBAIOT_MAIN)
    layout_c = ArtifactLayout(base_dir=_OUTPUTS, stage=ExperimentStage.NBAIOT_FULL_OPTIONAL)

    rp = layout_a.policy_run(_run(ExperimentStage.NBAIOT_MAIN, ThresholdPolicy.GLOBAL_THRESHOLD, 0)).result_dir
    parts = rp.parts
    assert "global_threshold" in parts, f"result_dir should contain policy 'global_threshold': {rp}"
    assert parts[-2] == "global_threshold"
    assert parts[-3] == "nbaiot_main"
    assert parts[-1].startswith("seed_")

    rp_alpha = layout_c.policy_run(_run(ExperimentStage.NBAIOT_FULL_OPTIONAL, ThresholdPolicy.LOCAL_THRESHOLD, 1)).result_dir
    parts_a = rp_alpha.parts
    assert "local_threshold" in parts_a
    assert "nbaiot_full_optional" in parts_a

    sp = layout_a.score_cell(_score_cell(ExperimentStage.NBAIOT_MAIN, 0)).score_dir
    assert "global_threshold" not in sp.parts and "local_threshold" not in sp.parts

    cp = layout_a.checkpoint_dir(TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=0))
    assert "global_threshold" not in cp.parts and "local_threshold" not in cp.parts

    rp_check = layout_a.policy_run(_run(ExperimentStage.NBAIOT_MAIN, ThresholdPolicy.GLOBAL_THRESHOLD, 42)).result_dir
    expected_suffix = "results/nbaiot_main/global_threshold/seed_42"
    assert str(rp_check).endswith(expected_suffix), (
        f"Expected path ending with '{expected_suffix}', got '{rp_check}'"
    )

    sp_check = layout_a.score_cell(_score_cell(ExperimentStage.NBAIOT_MAIN, 42)).score_dir
    expected_score_suffix = "scores/nbaiot_main/seed_42"
    assert str(sp_check).endswith(expected_score_suffix), (
        f"Expected path ending with '{expected_score_suffix}', got '{sp_check}'"
    )

    cp_check = layout_a.checkpoint_dir(
        TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=42)
    )
    expected_ckpt_suffix = "checkpoints/nbaiot_main/seed_42"
    assert str(cp_check).endswith(expected_ckpt_suffix), (
        f"Expected path ending with '{expected_ckpt_suffix}', got '{cp_check}'"
    )
