from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from datp.core.enums import Regime, ScoringStage
from datp.scoring.cal_loading import load_main_cal_errors
from tests.unit.conftest import _write_score_artifact


# ── load_main_cal_errors ──────────────────────────────────────────────────


class TestLoadMainCalErrors:
    def test_loads_calibration_errors(self, tmp_path: Path) -> None:
        regime = Regime.A
        seed = 42
        # Build the canonical cal score path for regime a / seed 42 / no alpha
        score_dir = tmp_path / "scores" / regime.value / f"seed_{seed}"
        cal_dir = score_dir / ScoringStage.CAL.value
        _write_score_artifact(cal_dir / "c1.parquet", [0.01, 0.02])
        _write_score_artifact(cal_dir / "c2.parquet", [0.03])

        result = load_main_cal_errors(
            regime, seed, None, tmp_path, checkpoint_round=None
        )
        assert set(result.keys()) == {"c1", "c2"}
        np.testing.assert_allclose(result["c1"], [0.01, 0.02])
        np.testing.assert_allclose(result["c2"], [0.03])

    def test_loads_with_alpha(self, tmp_path: Path) -> None:
        regime = Regime.C
        seed = 7
        alpha = 1.0
        score_dir = (
            tmp_path / "scores" / regime.value / f"seed_{seed}" / f"alpha_{alpha:g}"
        )
        cal_dir = score_dir / ScoringStage.CAL.value
        _write_score_artifact(cal_dir / "c1.parquet", [0.05])

        result = load_main_cal_errors(
            regime, seed, alpha, tmp_path, checkpoint_round=None
        )
        assert list(result.keys()) == ["c1"]

    def test_missing_cal_directory(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="score directory"):
            load_main_cal_errors(Regime.A, 1, None, tmp_path, checkpoint_round=None)

    def test_empty_cal_directory(self, tmp_path: Path) -> None:
        regime = Regime.A
        seed = 1
        score_dir = tmp_path / "scores" / regime.value / f"seed_{seed}"
        cal_dir = score_dir / ScoringStage.CAL.value
        cal_dir.mkdir(parents=True)
        with pytest.raises(FileNotFoundError, match="No parquet score artifacts"):
            load_main_cal_errors(regime, seed, None, tmp_path, checkpoint_round=None)
