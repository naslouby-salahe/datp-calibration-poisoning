"""Tests for datp.validation.discovery — path enumeration and parsing."""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from pathlib import Path

import pytest

from datp.artifacts.names import ArtifactDir, ArtifactFile
from datp.config.stages import ExperimentStage
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.validation.discovery import (
    ScoreCellLocation,
    completed_metric_paths,
    iter_score_cells,
    parse_metric_path,
    parse_score_cell_dir,
)


def _write_dummy_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")


# ─── parse_score_cell_dir ───────────────────────────────────────────


def test_parse_score_cell_dir_no_alpha(tmp_path: Path) -> None:
    scores_root = tmp_path / ArtifactDir.SCORES
    cell_dir = scores_root / ExperimentStage.NBAIOT_MAIN.value / "seed_42"
    location = parse_score_cell_dir(scores_root, cell_dir)
    assert location.cell == TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=42)
    assert location.cell_dir == cell_dir
    assert location.stage == ExperimentStage.NBAIOT_MAIN
    assert location.seed == 42


def test_parse_score_cell_dir_with_alpha(tmp_path: Path) -> None:
    scores_root = tmp_path / ArtifactDir.SCORES
    cell_dir = scores_root / ExperimentStage.NBAIOT_FULL_OPTIONAL.value / "seed_7"
    location = parse_score_cell_dir(scores_root, cell_dir)
    assert location.cell == TrainingCellId(
        stage=ExperimentStage.NBAIOT_FULL_OPTIONAL, seed=7
    )
    assert location.stage == ExperimentStage.NBAIOT_FULL_OPTIONAL
    assert location.seed == 7


def test_parse_score_cell_dir_alpha_iid(tmp_path: Path) -> None:
    scores_root = tmp_path / ArtifactDir.SCORES
    cell_dir = scores_root / ExperimentStage.NBAIOT_FULL_OPTIONAL.value / "seed_0"
    location = parse_score_cell_dir(scores_root, cell_dir)
    assert location.stage == ExperimentStage.NBAIOT_FULL_OPTIONAL
    assert location.seed == 0


def test_parse_score_cell_dir_invalid_stage_raises(tmp_path: Path) -> None:
    scores_root = tmp_path / ArtifactDir.SCORES
    cell_dir = scores_root / "x" / "seed_1"
    with pytest.raises(ValueError):
        parse_score_cell_dir(scores_root, cell_dir)


def test_parse_score_cell_dir_missing_seed_prefix_raises(tmp_path: Path) -> None:
    scores_root = tmp_path / ArtifactDir.SCORES
    cell_dir = scores_root / ExperimentStage.NBAIOT_MAIN.value / "bad_42"
    with pytest.raises(ValueError, match="Expected seed segment"):
        parse_score_cell_dir(scores_root, cell_dir)


# ─── iter_score_cells ───────────────────────────────────────────────


def test_iter_score_cells_empty(tmp_path: Path) -> None:
    assert iter_score_cells(tmp_path) == []


def test_iter_score_cells_no_alpha(tmp_path: Path) -> None:
    scores_root = (
        tmp_path / ArtifactDir.SCORES / ExperimentStage.NBAIOT_MAIN.value / "seed_0"
    )
    _write_dummy_file(scores_root / ArtifactFile.SCORING_MANIFEST)
    cells = iter_score_cells(tmp_path)
    assert len(cells) == 1
    assert cells[0].stage == ExperimentStage.NBAIOT_MAIN
    assert cells[0].seed == 0


def test_iter_score_cells_with_alpha(tmp_path: Path) -> None:
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
    (
        tmp_path / ArtifactDir.SCORES / ExperimentStage.NBAIOT_MAIN.value / "seed_0"
    ).mkdir(parents=True)
    assert iter_score_cells(tmp_path) == []


# ─── parse_metric_path ──────────────────────────────────────────────


def test_parse_metric_path_no_alpha(tmp_path: Path) -> None:
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


# ─── completed_metric_paths ─────────────────────────────────────────


def test_completed_metric_paths_empty(tmp_path: Path) -> None:
    assert completed_metric_paths(tmp_path) == []


def test_completed_metric_paths_finds_metrics(tmp_path: Path) -> None:
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


# ─── ScoreCellLocation ──────────────────────────────────────────────


def test_score_cell_location_is_frozen(tmp_path: Path) -> None:
    loc = ScoreCellLocation(
        cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=0),
        cell_dir=tmp_path,
    )
    with pytest.raises(Exception):
        loc.cell_dir = tmp_path / "other"  # type: ignore[misc]
