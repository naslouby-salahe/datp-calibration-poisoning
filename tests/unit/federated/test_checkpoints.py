"""Tests verifying training checkpoints saving, convergence serialization, and parameter snapshot round-trips."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch.nn as nn

from datp.artifacts.names import ArtifactFile
from datp.checkpointing.enums import ConvergenceStatus, ConvergenceSummaryKey
from datp.config.models import ConvergenceConfig
from datp.federated.checkpoints import (
    ConvergenceSnapshot,
    load_params_snapshot,
    save_checkpoint,
    save_convergence_artifacts,
    save_params_snapshot,
)


def _make_conv_cfg(
    *,
    rounds_initial: int = 5,
    rounds_max: int = 100,
    relative_threshold: float = 0.03,
    window: int = 4,
    round_timeout_s: float = 3600.0,
) -> ConvergenceConfig:
    """Helper to build a ConvergenceConfig instance."""
    return ConvergenceConfig(
        rounds_initial=rounds_initial,
        rounds_max=rounds_max,
        relative_threshold=relative_threshold,
        window=window,
        round_timeout_s=round_timeout_s,
    )


def test_save_checkpoint_writes_final_path_atomically(tmp_path: Path) -> None:
    """Verify save_checkpoint writes the model file atomically without leaving temporary files."""
    model = nn.Linear(2, 1)

    ckpt_file = save_checkpoint(model, tmp_path)

    assert ckpt_file.name == "model.pt"
    assert ckpt_file.exists()
    assert not (tmp_path / "model.pt.tmp").exists()


class TestSaveConvergenceArtifacts:
    """Tests verifying save_convergence_artifacts output files and schemas."""

    def test_writes_both_files_atomically(self, tmp_path: Path) -> None:
        """Confirm both convergence curve and summary files are written atomically."""
        snapshot = ConvergenceSnapshot(
            loss_history=[1.0, 0.8, 0.6],
            converged_round=3,
            criterion_value=0.05,
        )
        cfg = _make_conv_cfg()

        save_convergence_artifacts(tmp_path, snapshot, cfg)

        curve = tmp_path / ArtifactFile.CONVERGENCE_CURVE
        summary = tmp_path / ArtifactFile.CONVERGENCE_SUMMARY
        assert curve.exists()
        assert summary.exists()
        assert not (tmp_path / "convergence_curve.csv.tmp").exists()
        assert not (tmp_path / "convergence_summary.json.tmp").exists()

    def test_curve_contains_expected_columns(self, tmp_path: Path) -> None:
        """Verify convergence curve CSV contains the canonical columns and round indexes."""
        snapshot = ConvergenceSnapshot(
            loss_history=[1.0, 0.8],
            converged_round=2,
            criterion_value=0.01,
        )
        save_convergence_artifacts(tmp_path, snapshot, _make_conv_cfg())

        df = pd.read_csv(tmp_path / ArtifactFile.CONVERGENCE_CURVE)
        assert list(df.columns) == ["round", "fedavg_weighted_benign_val_loss"]
        assert len(df) == 2
        assert df["round"].tolist() == [1, 2]

    def test_summary_converged(self, tmp_path: Path) -> None:
        """Verify convergence summary JSON entries when the simulation converged."""
        snapshot = ConvergenceSnapshot(
            loss_history=[2.0, 1.5, 1.0],
            converged_round=3,
            criterion_value=0.02,
        )
        save_convergence_artifacts(tmp_path, snapshot, _make_conv_cfg())

        payload = json.loads((tmp_path / ArtifactFile.CONVERGENCE_SUMMARY).read_text())
        assert payload[ConvergenceSummaryKey.CONVERGENCE_ROUND] == 3
        assert payload[ConvergenceSummaryKey.CONVERGENCE_CRITERION] == pytest.approx(
            0.02
        )
        assert (
            payload[ConvergenceSummaryKey.CONVERGENCE_STATUS]
            == ConvergenceStatus.CONVERGED
        )
        assert payload[ConvergenceSummaryKey.ACTUAL_ROUNDS] == 3
        assert payload[ConvergenceSummaryKey.ROUNDS_INITIAL] == 5

    def test_summary_not_converged(self, tmp_path: Path) -> None:
        """Verify convergence summary JSON entries when the simulation did not converge."""
        snapshot = ConvergenceSnapshot(
            loss_history=[3.0, 2.9, 2.8],
            converged_round=None,
            criterion_value=None,
        )
        save_convergence_artifacts(tmp_path, snapshot, _make_conv_cfg())

        payload = json.loads((tmp_path / ArtifactFile.CONVERGENCE_SUMMARY).read_text())
        assert payload[ConvergenceSummaryKey.CONVERGENCE_ROUND] is None
        assert payload[ConvergenceSummaryKey.CONVERGENCE_CRITERION] is None
        assert (
            payload[ConvergenceSummaryKey.CONVERGENCE_STATUS]
            == ConvergenceStatus.NOT_CONVERGED
        )

    def test_empty_loss_history(self, tmp_path: Path) -> None:
        """Verify convergence summary behavior when history list is empty."""
        snapshot = ConvergenceSnapshot(
            loss_history=[],
            converged_round=None,
            criterion_value=None,
        )
        save_convergence_artifacts(tmp_path, snapshot, _make_conv_cfg())

        payload = json.loads((tmp_path / ArtifactFile.CONVERGENCE_SUMMARY).read_text())
        assert payload[ConvergenceSummaryKey.ACTUAL_ROUNDS] == 0
        assert payload[ConvergenceSummaryKey.WEIGHTED_LOSS] == []


class TestConvergenceSnapshot:
    """Tests verifying property mappings of ConvergenceSnapshot."""

    def test_construction(self) -> None:
        """Confirm ConvergenceSnapshot mapping stores correct values."""
        s = ConvergenceSnapshot(
            loss_history=[1.0, 0.5],
            converged_round=2,
            criterion_value=0.01,
        )
        assert s.loss_history == pytest.approx([1.0, 0.5])
        assert s.converged_round == 2
        assert s.criterion_value == pytest.approx(0.01)


class TestSaveParamsSnapshot:
    """Tests verifying parameter snapshot NPZ serialization."""

    def _make_params(self) -> list[np.ndarray]:
        """Helper to generate dummy model parameter weights as numpy arrays."""
        return [
            np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32),
            np.array([0.1, 0.2], dtype=np.float32),
        ]

    def test_writes_npz_atomically(self, tmp_path: Path) -> None:
        """Verify save_params_snapshot writes NPZ file atomically."""
        params = self._make_params()
        snap_file = save_params_snapshot(params, tmp_path)

        assert snap_file.name == "params.npz"
        assert snap_file.exists()
        assert not (tmp_path / "params.npz.tmp").exists()

    def test_file_is_loadable(self, tmp_path: Path) -> None:
        """Verify that the written NPZ parameter snapshot can be loaded by numpy."""
        params = self._make_params()
        save_params_snapshot(params, tmp_path)

        archive = np.load(str(tmp_path / "params.npz"))
        loaded = [archive[k] for k in sorted(archive.files)]
        assert len(loaded) == 2
        np.testing.assert_array_equal(loaded[0], params[0])
        np.testing.assert_array_equal(loaded[1], params[1])

    def test_creates_parent_dir(self, tmp_path: Path) -> None:
        """Verify that save_params_snapshot automatically creates parent directories if needed."""
        subdir = tmp_path / "round_25"
        params = self._make_params()
        save_params_snapshot(params, subdir)
        assert (subdir / "params.npz").exists()

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        """Verify that save_params_snapshot overwrites any existing parameter snapshot."""
        params1 = [np.array([1.0], dtype=np.float32)]
        params2 = [np.array([9.9], dtype=np.float32)]
        save_params_snapshot(params1, tmp_path)
        save_params_snapshot(params2, tmp_path)

        loaded = load_params_snapshot(tmp_path)
        assert loaded is not None
        np.testing.assert_array_almost_equal(loaded[0], [9.9])


class TestLoadParamsSnapshot:
    """Tests verifying parameter snapshot loaders and type safety."""

    def test_returns_none_when_file_absent(self, tmp_path: Path) -> None:
        """Verify load_params_snapshot returns None if the NPZ file is missing."""
        assert load_params_snapshot(tmp_path) is None

    def test_returns_arrays_matching_saved(self, tmp_path: Path) -> None:
        """Verify loaded arrays match the exact saved values."""
        params = [
            np.array([[1.0, 2.0]], dtype=np.float32),
            np.array([0.5], dtype=np.float64),
        ]
        save_params_snapshot(params, tmp_path)
        loaded = load_params_snapshot(tmp_path)

        assert loaded is not None
        assert len(loaded) == 2
        np.testing.assert_array_equal(loaded[0], params[0])
        np.testing.assert_array_equal(loaded[1], params[1])

    def test_round_trip_preserves_dtype(self, tmp_path: Path) -> None:
        """Ensure saving and loading preserves the exact float32 numpy data type."""
        params = [np.ones((3, 3), dtype=np.float32)]
        save_params_snapshot(params, tmp_path)
        loaded = load_params_snapshot(tmp_path)
        assert loaded is not None
        assert loaded[0].dtype == np.float32
