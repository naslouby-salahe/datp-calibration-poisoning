"""Verify that score paths are policy-independent."""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import inspect
from pathlib import Path

import pytest

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactDir
from datp.config.models import ExperimentStage
from datp.core.identity import TrainingCellId


@pytest.mark.integration
def test_same_artifact_path_all_policies() -> None:
    """Score paths are identical across policies and the API does not accept a baseline parameter."""
    layout = ArtifactLayout(
        base_dir=Path(ArtifactDir.OUTPUTS), stage=ExperimentStage.NBAIOT_MAIN
    )
    cell = TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=0)
    paths = [
        layout.score_cell(cell).score_dir
        for _ in (
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        )
    ]

    assert len(set(paths)) == 1, f"Expected one unique path, got {set(paths)}"

    for method in (layout.score_cell, layout.score_file):
        sig = inspect.signature(method)
        assert "baseline" not in sig.parameters, (
            f"{method.__name__}() must not accept a 'baseline' parameter -- "
            "scores are shared across all threshold policies"
        )
