from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import inspect
from pathlib import Path

import pytest

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactDir
from datp.config.stages import ExperimentStage
from datp.core.identity import TrainingCellId


@pytest.mark.integration
def test_same_artifact_path_all_baselines() -> None:
    layout = ArtifactLayout(base_dir=Path(ArtifactDir.OUTPUTS), stage=ExperimentStage.NBAIOT_MAIN)
    cell = TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=0)
    paths = [
        layout.score_cell(cell).score_dir
        for _ in (ThresholdPolicy.GLOBAL_THRESHOLD, ThresholdPolicy.LOCAL_THRESHOLD, ThresholdPolicy.CLUSTER_THRESHOLD, ThresholdPolicy.CLUSTER_THRESHOLD)
    ]

    assert len(set(paths)) == 1, f"Expected one unique path, got {set(paths)}"

    # score_cell()/score_file() must NOT accept a 'baseline' argument —
    # scores are shared across all threshold policies (GLOBAL_THRESHOLD/LOCAL_THRESHOLD/CLUSTER_THRESHOLD).
    for method in (layout.score_cell, layout.score_file):
        sig = inspect.signature(method)
        assert "baseline" not in sig.parameters, (
            f"{method.__name__}() must not accept a 'baseline' parameter -- "
            "scores are shared across all threshold policies"
        )
