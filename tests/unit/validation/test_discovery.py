"""Tests verifying path parsing, score cell workspace discovery, and metric file locators."""

from __future__ import annotations

from pathlib import Path

import pytest

from datp.artifacts.names import ArtifactDir, ArtifactFile
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.validation.discovery import (
    ScoreCellLocation,
    completed_metric_paths,
    iter_score_cells,
    parse_metric_path,
    parse_score_cell_dir,
)


def _write_dummy_file(path: Path) -> None:
    """Helper to write an empty JSON file at the given target path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}")


def test_parse_score_cell_dir_no_alpha(tmp_path: Path) -> None:
    """Verify parse_score_cell_dir parses standard non-alpha stages and seeds correctly."""
    scores_root = tmp_path / ArtifactDir.SCORES
    cell_dir = scores_root / ExperimentStage.NBAIOT_MAIN.value / "seed_42"
    location = parse_score_cell_dir(scores_root, cell_dir)
    assert location.cell == TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=42)
    assert location.cell_dir == cell_dir
    assert location.stage == ExperimentStage.NBAIOT_MAIN
    assert location.seed == 42


def test_parse_score_cell_dir_with_alpha(tmp_path: Path) -> None:
    """Verify parse_score_cell_dir parses optional/alpha stage identifiers and seeds correctly."""
    scores_root = tmp_path / ArtifactDir.SCORES
    cell_dir = scores_root / ExperimentStage.NBAIOT_FULL_OPTIONAL.value / "seed_7"
    location = parse_score_cell_dir(scores_root, cell_dir)
    assert location.cell == TrainingCellId(
        stage=ExperimentStage.NBAIOT_FULL_OPTIONAL, seed=7
    )
    assert location.stage == ExperimentStage.NBAIOT_FULL_OPTIONAL
    assert location.seed == 7


def test_parse_score_cell_dir_alpha_iid(tmp_path: Path) -> None:
    """Verify stage parsing on boundary conditions (e.g. optional stage seed 0)."""
    scores_root = tmp_path / ArtifactDir.SCORES
    cell_dir = scores_root / ExperimentStage.NBAIOT_FULL_OPTIONAL.value / "seed_0"
    location = parse_score_cell_dir(scores_root, cell_dir)
    assert location.stage == ExperimentStage.NBAIOT_FULL_OPTIONAL
    assert location.seed == 0


def test_parse_score_cell_dir_invalid_stage_raises(tmp_path: Path) -> None:
    """Verify ValueError is raised when parsing a directory with an invalid stage name."""
    scores_root = tmp_path / ArtifactDir.SCORES
    cell_dir = scores_root / "x" / "seed_1"
    with pytest.raises(ValueError):
        parse_score_cell_dir(scores_root, cell_dir)


def test_parse_score_cell_dir_missing_seed_prefix_raises(tmp_path: Path) -> None:
    """Verify ValueError is raised if the seed folder lacks the expected seed_ prefix."""
    scores_root = tmp_path / ArtifactDir.SCORES
    cell_dir = scores_root / ExperimentStage.NBAIOT_MAIN.value / "bad_42"
    with pytest.raises(ValueError, match="Expected seed segment"):
        parse_score_cell_dir(scores_root, cell_dir)


def test_iter_score_cells_empty(tmp_path: Path) -> None:
    """Verify iter_score_cells returns an empty list if directory is empty."""
    assert iter_score_cells(tmp_path) == []


def test_iter_score_cells_no_alpha(tmp_path: Path) -> None:
    """Verify iter_score_cells discovers standard stage cells with a valid manifest."""
    scores_root = (
        tmp_path / ArtifactDir.SCORES / ExperimentStage.NBAIOT_MAIN.value / "seed_0"
    )
    _write_dummy_file(scores_root / ArtifactFile.SCORING_MANIFEST)
    cells = iter_score_cells(tmp_path)
    assert len(cells) == 1
    assert cells[0].stage == ExperimentStage.NBAIOT_MAIN
    assert cells[0].seed == 0


def test_iter_score_cells_with_alpha(tmp_path: Path) -> None:
    """Verify iter_score_cells discovers optional stage cells with a valid manifest."""
    scores_root = (
        tmp_path
        / ArtifactDir.SCORES
        / ExperimentStage.NBAIOT_FULL_OPTIONAL.value
        / "seed_1"
    )
    _write_dummy_file(scores_root / ArtifactFile.SCORING_MANIFEST)
    cells = iter_score_cells(tmp_path)
    assert len(cells) == 1
    assert cells[0].stage == ExperimentStage.NBAIOT_FULL_OPTIONAL
    assert cells[0].seed == 1


def test_iter_score_cells_mixed(tmp_path: Path) -> None:
    """Verify iter_score_cells finds all valid cells of standard and optional stages."""
    _write_dummy_file(
        tmp_path
        / ArtifactDir.SCORES
        / ExperimentStage.NBAIOT_MAIN.value
        / "seed_0"
        / ArtifactFile.SCORING_MANIFEST
    )
    _write_dummy_file(
        tmp_path
        / ArtifactDir.SCORES
        / ExperimentStage.NBAIOT_FULL_OPTIONAL.value
        / "seed_0"
        / ArtifactFile.SCORING_MANIFEST
    )
    cells = iter_score_cells(tmp_path)
    assert len(cells) == 2


def test_iter_score_cells_ignores_dirs_without_manifest(tmp_path: Path) -> None:
    """Verify directories lacking scoring_manifest.json are completely ignored."""
    (
        tmp_path / ArtifactDir.SCORES / ExperimentStage.NBAIOT_MAIN.value / "seed_0"
    ).mkdir(parents=True)
    assert iter_score_cells(tmp_path) == []


def test_parse_metric_path_no_alpha(tmp_path: Path) -> None:
    """Verify parse_metric_path parses standard stage run IDs correctly."""
    results_root = tmp_path / ArtifactDir.RESULTS
    path = (
        results_root
        / ExperimentStage.NBAIOT_MAIN.value
        / ThresholdPolicy.GLOBAL_THRESHOLD.value
        / "seed_42"
        / ArtifactFile.METRICS
    )
    run_id = parse_metric_path(tmp_path, path)
    assert isinstance(run_id, PolicyRunId)
    assert run_id.stage == ExperimentStage.NBAIOT_MAIN
    assert run_id.policy == ThresholdPolicy.GLOBAL_THRESHOLD
    assert run_id.seed == 42


def test_parse_metric_path_with_alpha(tmp_path: Path) -> None:
    """Verify parse_metric_path parses optional stage run IDs correctly."""
    results_root = tmp_path / ArtifactDir.RESULTS
    path = (
        results_root
        / ExperimentStage.NBAIOT_FULL_OPTIONAL.value
        / ThresholdPolicy.LOCAL_THRESHOLD.value
        / "seed_7"
        / ArtifactFile.METRICS
    )
    run_id = parse_metric_path(tmp_path, path)
    assert run_id.stage == ExperimentStage.NBAIOT_FULL_OPTIONAL
    assert run_id.policy == ThresholdPolicy.LOCAL_THRESHOLD
    assert run_id.seed == 7


def test_parse_metric_path_invalid_seed_raises(tmp_path: Path) -> None:
    """Verify parse_metric_path raises ValueError if seed segment is malformed."""
    results_root = tmp_path / ArtifactDir.RESULTS
    path = (
        results_root
        / ExperimentStage.NBAIOT_MAIN.value
        / ThresholdPolicy.GLOBAL_THRESHOLD.value
        / "bad"
        / ArtifactFile.METRICS
    )
    with pytest.raises(ValueError, match="Expected seed segment"):
        parse_metric_path(tmp_path, path)


def test_parse_metric_path_invalid_stage_raises(tmp_path: Path) -> None:
    """Verify parse_metric_path raises ValueError if stage segment is unrecognized."""
    results_root = tmp_path / ArtifactDir.RESULTS
    path = (
        results_root
        / "x"
        / ThresholdPolicy.GLOBAL_THRESHOLD.value
        / "seed_1"
        / ArtifactFile.METRICS
    )
    with pytest.raises(ValueError):
        parse_metric_path(tmp_path, path)


def test_completed_metric_paths_empty(tmp_path: Path) -> None:
    """Verify completed_metric_paths returns an empty list when no metrics are written."""
    assert completed_metric_paths(tmp_path) == []


def test_completed_metric_paths_finds_metrics(tmp_path: Path) -> None:
    """Verify completed_metric_paths discovers all metrics.json files."""
    results = tmp_path / ArtifactDir.RESULTS
    _write_dummy_file(
        results
        / ExperimentStage.NBAIOT_MAIN.value
        / ThresholdPolicy.GLOBAL_THRESHOLD.value
        / "seed_0"
        / ArtifactFile.METRICS
    )
    _write_dummy_file(
        results
        / ExperimentStage.NBAIOT_MAIN.value
        / ThresholdPolicy.LOCAL_THRESHOLD.value
        / "seed_0"
        / ArtifactFile.METRICS
    )
    paths = completed_metric_paths(tmp_path)
    assert len(paths) == 2


def test_completed_metric_paths_with_alpha(tmp_path: Path) -> None:
    """Verify completed_metric_paths discovers metrics.json for optional stages."""
    results = tmp_path / ArtifactDir.RESULTS
    _write_dummy_file(
        results
        / ExperimentStage.NBAIOT_FULL_OPTIONAL.value
        / ThresholdPolicy.GLOBAL_THRESHOLD.value
        / "seed_0"
        / ArtifactFile.METRICS
    )
    paths = completed_metric_paths(tmp_path)
    assert len(paths) == 1


def test_score_cell_location_is_frozen(tmp_path: Path) -> None:
    """Verify that ScoreCellLocation properties are frozen to modifications."""
    loc = ScoreCellLocation(
        cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=0),
        cell_dir=tmp_path,
    )
    with pytest.raises(Exception):
        setattr(loc, "cell_dir", tmp_path / "other")
