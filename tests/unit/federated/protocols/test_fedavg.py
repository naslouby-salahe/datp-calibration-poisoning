# SPDX-License-Identifier: Proprietary
"""Tests for run_fl_training: validation, path routing, and signature contracts."""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from datp.artifacts.layout import ArtifactLayout
from datp.attacks.enums import ThresholdPolicy
from datp.config.stages import ExperimentStage
from datp.core.identity import TrainingCellId
from datp.federated.protocols.fedavg import run_fl_training

_STAGE = ExperimentStage.NBAIOT_MAIN


class TestRunFlTrainingSignature:
    def test_accepts_output_layout_parameter(self) -> None:
        sig = inspect.signature(run_fl_training)
        p = sig.parameters.get("output_layout")
        assert p is not None, "run_fl_training must have output_layout parameter"
        assert p.default is None

    def test_accepts_base_dir_parameter(self) -> None:
        sig = inspect.signature(run_fl_training)
        p = sig.parameters.get("base_dir")
        assert p is not None, "run_fl_training must have base_dir parameter"
        assert p.default is None

    def test_accepts_prepared_dir_parameter(self) -> None:
        sig = inspect.signature(run_fl_training)
        p = sig.parameters.get("prepared_dir")
        assert p is not None
        assert p.default is None


class TestRunFlTrainingValidation:
    def test_raises_when_stage_is_none(self, tmp_path: Path) -> None:
        cfg = MagicMock()
        cfg.stage = None
        with pytest.raises(ValueError, match="stage must be set"):
            run_fl_training(cfg, {}, seed=0, base_dir=tmp_path)

    def test_raises_when_both_base_dir_and_output_layout_are_none(self) -> None:
        cfg = MagicMock()
        cfg.stage = _STAGE
        with pytest.raises(ValueError, match="base_dir or output_layout required"):
            run_fl_training(cfg, {}, seed=0)


class TestRunFlTrainingRouting:
    """run_fl_training must forward the correct ckpt_dir and score_base to run_fl_simulation."""

    def _capture_sim_calls(self, monkeypatch: pytest.MonkeyPatch) -> list[dict]:
        captured: list[dict] = []
        import datp.federated.protocols.fedavg as fedavg_mod

        def fake_sim(*args: object, **kwargs: object) -> object:
            captured.append({"_positional": args, **kwargs})
            raise RuntimeError("stop-in-sim")

        monkeypatch.setattr(fedavg_mod, "run_fl_simulation", fake_sim)
        return captured

    def _make_cfg(self, stage: ExperimentStage = _STAGE) -> MagicMock:
        from datp.config.compose import BASE_CONFIG

        return BASE_CONFIG.model_copy(update={"stage": stage})

    def test_with_output_layout_uses_layout_ckpt_dir(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        seed = 3
        cfg = self._make_cfg()
        layout = ArtifactLayout(base_dir=tmp_path, stage=_STAGE)
        cell = TrainingCellId(stage=_STAGE, seed=seed)
        captured = self._capture_sim_calls(monkeypatch)

        with pytest.raises(RuntimeError, match="stop-in-sim"):
            run_fl_training(cfg, {}, seed, output_layout=layout)

        assert len(captured) == 1
        assert captured[0]["ckpt_dir"] == layout.checkpoint_dir(cell)

    def test_with_output_layout_uses_layout_score_dir(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        seed = 5
        cfg = self._make_cfg()
        layout = ArtifactLayout(base_dir=tmp_path, stage=_STAGE)
        cell = TrainingCellId(stage=_STAGE, seed=seed)
        captured = self._capture_sim_calls(monkeypatch)

        with pytest.raises(RuntimeError, match="stop-in-sim"):
            run_fl_training(cfg, {}, seed, output_layout=layout)

        expected_score = layout.score_cell(cell).score_dir
        assert captured[0]["score_base"] == expected_score

    def test_with_base_dir_builds_layout_correctly(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        seed = 7
        cfg = self._make_cfg()
        expected_layout = ArtifactLayout(base_dir=tmp_path, stage=_STAGE)
        cell = TrainingCellId(stage=_STAGE, seed=seed)
        captured = self._capture_sim_calls(monkeypatch)

        with pytest.raises(RuntimeError, match="stop-in-sim"):
            run_fl_training(cfg, {}, seed, base_dir=tmp_path)

        assert captured[0]["ckpt_dir"] == expected_layout.checkpoint_dir(cell)
        assert captured[0]["score_base"] == expected_layout.score_cell(cell).score_dir

    def test_output_layout_takes_precedence_over_base_dir(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        seed = 2
        cfg = self._make_cfg()
        layout = ArtifactLayout(base_dir=tmp_path / "layout", stage=_STAGE)
        cell = TrainingCellId(stage=_STAGE, seed=seed)
        captured = self._capture_sim_calls(monkeypatch)

        with pytest.raises(RuntimeError, match="stop-in-sim"):
            run_fl_training(
                cfg, {}, seed, base_dir=tmp_path / "base", output_layout=layout
            )

        assert captured[0]["ckpt_dir"] == layout.checkpoint_dir(cell)
