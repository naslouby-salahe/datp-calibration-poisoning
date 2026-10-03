from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from datp.artifacts import ArtifactLayout
from datp.config import ExperimentStage
from datp.core import TrainingCellId
from datp.enums import ArtifactDir, ArtifactFile, ThresholdPolicy
from datp.federated import run_fl_training
from datp.scoring import validate_scoring_manifest
from tests.fixtures import SEED, make_client_data, make_fl_cfg


@pytest.mark.integration
def test_small_loop_writes_scores_and_convergence(tmp_path) -> None:
    """Training writes scores, a model hash and convergence artifacts, without a checkpoint."""
    cfg = make_fl_cfg(
        stage=ExperimentStage.NBAIOT_MAIN, rounds=2, encoder_dims=[8, 4, 8]
    )

    result = run_fl_training(
        cfg=cfg,
        client_data=make_client_data(n_clients=2, seed=SEED),
        seed=SEED,
        base_dir=tmp_path,
    )

    assert result.stage == ExperimentStage.NBAIOT_MAIN
    assert 1 <= result.total_rounds <= 2
    assert len(result.loss_history) == result.total_rounds
    assert result.converged_round is None or isinstance(result.converged_round, int)
    assert (result.score_dir / ArtifactFile.CONVERGENCE_SUMMARY).exists()
    assert (result.score_dir / ArtifactFile.CONVERGENCE_CURVE).exists()
    assert validate_scoring_manifest(result.score_dir).model_hash
    assert not (tmp_path / "checkpoints").exists()
    assert not list(tmp_path.rglob("model.pt"))


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
