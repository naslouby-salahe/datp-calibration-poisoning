from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from datp.config.stages import ExperimentStage
from datp.core.enums import ScoringStage
from datp.scoring.cal_loading import load_main_cal_errors
from tests.unit.conftest import _write_score_artifact

_STAGE = ExperimentStage.NBAIOT_MAIN


class TestLoadMainCalErrors:
    def test_loads_calibration_errors(self, tmp_path: Path) -> None:
        seed = 42
        score_dir = tmp_path / "scores" / _STAGE.value / f"seed_{seed}"
        cal_dir = score_dir / ScoringStage.CAL.value
        _write_score_artifact(cal_dir / "c1.parquet", [0.01, 0.02])
        _write_score_artifact(cal_dir / "c2.parquet", [0.03])

        result = load_main_cal_errors(_STAGE, seed, tmp_path, checkpoint_round=None)
        assert set(result.keys()) == {"c1", "c2"}
        np.testing.assert_allclose(result["c1"], [0.01, 0.02])
        np.testing.assert_allclose(result["c2"], [0.03])

    def test_missing_cal_directory(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="score directory"):
            load_main_cal_errors(_STAGE, 1, tmp_path, checkpoint_round=None)

    def test_empty_cal_directory(self, tmp_path: Path) -> None:
        seed = 1
        score_dir = tmp_path / "scores" / _STAGE.value / f"seed_{seed}"
        cal_dir = score_dir / ScoringStage.CAL.value
        cal_dir.mkdir(parents=True)
        with pytest.raises(FileNotFoundError, match="No parquet score artifacts"):
            load_main_cal_errors(_STAGE, seed, tmp_path, checkpoint_round=None)
