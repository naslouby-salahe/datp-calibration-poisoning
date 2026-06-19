"""Tests for datp.validation.discovery — path enumeration and parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from datp.artifacts.names import ArtifactDir, ArtifactFile
from datp.core.enums import Baseline, Regime
from datp.core.identity import BaselineRunId, TrainingCellId
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
    cell_dir = scores_root / "a" / "seed_42"
    location = parse_score_cell_dir(scores_root, cell_dir)
    assert location.cell == TrainingCellId(regime=Regime.A, seed=42, alpha=None)
    assert location.cell_dir == cell_dir
    assert location.regime == Regime.A
    assert location.seed == 42
    assert location.alpha is None


def test_parse_score_cell_dir_with_alpha(tmp_path: Path) -> None:
    scores_root = tmp_path / ArtifactDir.SCORES
    cell_dir = scores_root / "c" / "seed_7" / "alpha_0.5"
    location = parse_score_cell_dir(scores_root, cell_dir)
    assert location.cell == TrainingCellId(regime=Regime.C, seed=7, alpha=0.5)
    assert location.alpha == 0.5


def test_parse_score_cell_dir_alpha_iid(tmp_path: Path) -> None:
    scores_root = tmp_path / ArtifactDir.SCORES
    cell_dir = scores_root / "c" / "seed_0" / "alpha_iid"
    location = parse_score_cell_dir(scores_root, cell_dir)
    import math

    assert location.alpha == math.inf


def test_parse_score_cell_dir_invalid_regime_raises(tmp_path: Path) -> None:
    scores_root = tmp_path / ArtifactDir.SCORES
    cell_dir = scores_root / "x" / "seed_1"
    with pytest.raises(ValueError):
        parse_score_cell_dir(scores_root, cell_dir)


def test_parse_score_cell_dir_missing_seed_prefix_raises(tmp_path: Path) -> None:
    scores_root = tmp_path / ArtifactDir.SCORES
    cell_dir = scores_root / "a" / "bad_42"
    with pytest.raises(ValueError, match="Expected seed segment"):
        parse_score_cell_dir(scores_root, cell_dir)


# ─── iter_score_cells ───────────────────────────────────────────────


def test_iter_score_cells_empty(tmp_path: Path) -> None:
    assert iter_score_cells(tmp_path) == []


def test_iter_score_cells_no_alpha(tmp_path: Path) -> None:
    scores_root = tmp_path / ArtifactDir.SCORES / "a" / "seed_0"
    _write_dummy_file(scores_root / ArtifactFile.SCORING_MANIFEST)
    cells = iter_score_cells(tmp_path)
    assert len(cells) == 1
    assert cells[0].regime == Regime.A
    assert cells[0].seed == 0
    assert cells[0].alpha is None


def test_iter_score_cells_with_alpha(tmp_path: Path) -> None:
    scores_root = tmp_path / ArtifactDir.SCORES / "c" / "seed_1" / "alpha_0.1"
    _write_dummy_file(scores_root / ArtifactFile.SCORING_MANIFEST)
    cells = iter_score_cells(tmp_path)
    assert len(cells) == 1
    assert cells[0].regime == Regime.C
    assert cells[0].seed == 1
    assert cells[0].alpha == 0.1


def test_iter_score_cells_mixed(tmp_path: Path) -> None:
    _write_dummy_file(
        tmp_path / ArtifactDir.SCORES / "a" / "seed_0" / ArtifactFile.SCORING_MANIFEST
    )
    _write_dummy_file(
        tmp_path
        / ArtifactDir.SCORES
        / "a"
        / "seed_0"
        / "alpha_0.5"
        / ArtifactFile.SCORING_MANIFEST
    )
    cells = iter_score_cells(tmp_path)
    assert len(cells) == 2


def test_iter_score_cells_ignores_dirs_without_manifest(tmp_path: Path) -> None:
    (tmp_path / ArtifactDir.SCORES / "a" / "seed_0").mkdir(parents=True)
    assert iter_score_cells(tmp_path) == []


# ─── parse_metric_path ──────────────────────────────────────────────


def test_parse_metric_path_no_alpha(tmp_path: Path) -> None:
    results_root = tmp_path / ArtifactDir.RESULTS
    path = results_root / "a" / "b1" / "seed_42" / ArtifactFile.METRICS
    run_id = parse_metric_path(tmp_path, path)
    assert isinstance(run_id, BaselineRunId)
    assert run_id.regime == Regime.A
    assert run_id.baseline == Baseline.B1
    assert run_id.seed == 42
    assert run_id.alpha is None


def test_parse_metric_path_with_alpha(tmp_path: Path) -> None:
    results_root = tmp_path / ArtifactDir.RESULTS
    path = results_root / "c" / "b2" / "seed_7" / "alpha_0.5" / ArtifactFile.METRICS
    run_id = parse_metric_path(tmp_path, path)
    assert run_id.regime == Regime.C
    assert run_id.baseline == Baseline.B2
    assert run_id.seed == 7
    assert run_id.alpha == 0.5


def test_parse_metric_path_invalid_seed_raises(tmp_path: Path) -> None:
    results_root = tmp_path / ArtifactDir.RESULTS
    path = results_root / "a" / "b1" / "bad" / ArtifactFile.METRICS
    with pytest.raises(ValueError, match="Expected seed segment"):
        parse_metric_path(tmp_path, path)


def test_parse_metric_path_invalid_regime_raises(tmp_path: Path) -> None:
    results_root = tmp_path / ArtifactDir.RESULTS
    path = results_root / "x" / "b1" / "seed_1" / ArtifactFile.METRICS
    with pytest.raises(ValueError):
        parse_metric_path(tmp_path, path)


# ─── completed_metric_paths ─────────────────────────────────────────


def test_completed_metric_paths_empty(tmp_path: Path) -> None:
    assert completed_metric_paths(tmp_path) == []


def test_completed_metric_paths_finds_metrics(tmp_path: Path) -> None:
    results = tmp_path / ArtifactDir.RESULTS
    _write_dummy_file(results / "a" / "b1" / "seed_0" / ArtifactFile.METRICS)
    _write_dummy_file(results / "a" / "b2" / "seed_0" / ArtifactFile.METRICS)
    paths = completed_metric_paths(tmp_path)
    assert len(paths) == 2


def test_completed_metric_paths_with_alpha(tmp_path: Path) -> None:
    results = tmp_path / ArtifactDir.RESULTS
    _write_dummy_file(
        results / "c" / "b1" / "seed_0" / "alpha_0.1" / ArtifactFile.METRICS
    )
    paths = completed_metric_paths(tmp_path)
    assert len(paths) == 1


# ─── ScoreCellLocation ──────────────────────────────────────────────


def test_score_cell_location_is_frozen(tmp_path: Path) -> None:
    loc = ScoreCellLocation(
        cell=TrainingCellId(regime=Regime.A, seed=0, alpha=None),
        cell_dir=tmp_path,
    )
    with pytest.raises(Exception):
        loc.cell_dir = tmp_path / "other" # type: ignore[misc]
