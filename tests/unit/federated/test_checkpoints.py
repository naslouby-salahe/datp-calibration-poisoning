# SPDX-License-Identifier: Proprietary
"""Tests for checkpoint saving and convergence artifact persistence."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch.nn as nn

from datp.artifacts.names import ArtifactFile
from datp.config.models import ConvergenceConfig
from datp.core.enums import ConvergenceStatus, ConvergenceSummaryKey
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
    return ConvergenceConfig(
        rounds_initial=rounds_initial,
        rounds_max=rounds_max,
        relative_threshold=relative_threshold,
        window=window,
        round_timeout_s=round_timeout_s,
    )


def test_save_checkpoint_writes_final_path_atomically(tmp_path: Path) -> None:
    model = nn.Linear(2, 1)

    ckpt_file = save_checkpoint(model, tmp_path)

    assert ckpt_file.name == "model.pt"
    assert ckpt_file.exists()
    assert not (tmp_path / "model.pt.tmp").exists()


class TestSaveConvergenceArtifacts:
    def test_writes_both_files_atomically(self, tmp_path: Path) -> None:
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
        snapshot = ConvergenceSnapshot(
            loss_history=[2.0, 1.5, 1.0],
            converged_round=3,
            criterion_value=0.02,
        )
        save_convergence_artifacts(tmp_path, snapshot, _make_conv_cfg())

        payload = json.loads(
            (tmp_path / ArtifactFile.CONVERGENCE_SUMMARY).read_text()
        )
        assert payload[ConvergenceSummaryKey.CONVERGENCE_ROUND] == 3
        assert payload[ConvergenceSummaryKey.CONVERGENCE_CRITERION] == 0.02
        assert payload[ConvergenceSummaryKey.CONVERGENCE_STATUS] == ConvergenceStatus.CONVERGED
        assert payload[ConvergenceSummaryKey.ACTUAL_ROUNDS] == 3
        assert payload[ConvergenceSummaryKey.ROUNDS_INITIAL] == 5

    def test_summary_not_converged(self, tmp_path: Path) -> None:
        snapshot = ConvergenceSnapshot(
            loss_history=[3.0, 2.9, 2.8],
            converged_round=None,
            criterion_value=None,
        )
        save_convergence_artifacts(tmp_path, snapshot, _make_conv_cfg())

        payload = json.loads(
            (tmp_path / ArtifactFile.CONVERGENCE_SUMMARY).read_text()
        )
        assert payload[ConvergenceSummaryKey.CONVERGENCE_ROUND] is None
        assert payload[ConvergenceSummaryKey.CONVERGENCE_CRITERION] is None
        assert payload[ConvergenceSummaryKey.CONVERGENCE_STATUS] == ConvergenceStatus.NOT_CONVERGED

    def test_empty_loss_history(self, tmp_path: Path) -> None:
        snapshot = ConvergenceSnapshot(
            loss_history=[],
            converged_round=None,
            criterion_value=None,
        )
        save_convergence_artifacts(tmp_path, snapshot, _make_conv_cfg())

        payload = json.loads(
            (tmp_path / ArtifactFile.CONVERGENCE_SUMMARY).read_text()
        )
        assert payload[ConvergenceSummaryKey.ACTUAL_ROUNDS] == 0
        assert payload[ConvergenceSummaryKey.WEIGHTED_LOSS] == []


class TestConvergenceSnapshot:
    def test_construction(self) -> None:
        s = ConvergenceSnapshot(
            loss_history=[1.0, 0.5],
            converged_round=2,
            criterion_value=0.01,
        )
        assert s.loss_history == [1.0, 0.5]
        assert s.converged_round == 2
        assert s.criterion_value == 0.01

    def test_none_fields(self) -> None:
        s = ConvergenceSnapshot(
            loss_history=[],
            converged_round=None,
            criterion_value=None,
        )
        assert s.converged_round is None
        assert s.criterion_value is None

    def test_is_frozen(self) -> None:
        s = ConvergenceSnapshot(
            loss_history=[1.0],
            converged_round=1,
            criterion_value=0.0,
        )
        with pytest.raises(Exception):
            s.converged_round = 5 # type: ignore[misc]


class TestSaveParamsSnapshot:
    def _make_params(self) -> list[np.ndarray]:
        return [
            np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32),
            np.array([0.1, 0.2], dtype=np.float32),
        ]

    def test_writes_npz_atomically(self, tmp_path: Path) -> None:
        params = self._make_params()
        snap_file = save_params_snapshot(params, tmp_path)

        assert snap_file.name == "params.npz"
        assert snap_file.exists()
        assert not (tmp_path / "params.npz.tmp").exists()

    def test_file_is_loadable(self, tmp_path: Path) -> None:
        params = self._make_params()
        save_params_snapshot(params, tmp_path)

        archive = np.load(str(tmp_path / "params.npz"))
        loaded = [archive[k] for k in sorted(archive.files)]
        assert len(loaded) == 2
        np.testing.assert_array_equal(loaded[0], params[0])
        np.testing.assert_array_equal(loaded[1], params[1])

    def test_creates_parent_dir(self, tmp_path: Path) -> None:
        subdir = tmp_path / "round_25"
        params = self._make_params()
        save_params_snapshot(params, subdir)
        assert (subdir / "params.npz").exists()

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        params1 = [np.array([1.0], dtype=np.float32)]
        params2 = [np.array([9.9], dtype=np.float32)]
        save_params_snapshot(params1, tmp_path)
        save_params_snapshot(params2, tmp_path)

        loaded = load_params_snapshot(tmp_path)
        assert loaded is not None
        np.testing.assert_array_almost_equal(loaded[0], [9.9])


class TestLoadParamsSnapshot:
    def test_returns_none_when_file_absent(self, tmp_path: Path) -> None:
        assert load_params_snapshot(tmp_path) is None

    def test_returns_arrays_matching_saved(self, tmp_path: Path) -> None:
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
        params = [np.ones((3, 3), dtype=np.float32)]
        save_params_snapshot(params, tmp_path)
        loaded = load_params_snapshot(tmp_path)
        assert loaded is not None
        assert loaded[0].dtype == np.float32
