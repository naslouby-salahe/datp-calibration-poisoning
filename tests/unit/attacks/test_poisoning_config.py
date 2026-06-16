from __future__ import annotations

import pytest

from datp.attacks.poison_enums import AttackerObjective
from datp.attacks.poisoning_config import CalibrationPoisoningConfig


class TestCalibrationPoisoningConfig:
    def test_valid_config(self) -> None:
        cfg = CalibrationPoisoningConfig(
            attack_rate=0.1,
            objective=AttackerObjective.THRESHOLD_RAISE,
            shift_magnitude=2.0,
        )
        assert cfg.attack_rate == 0.1
        assert cfg.objective == AttackerObjective.THRESHOLD_RAISE
        assert cfg.shift_magnitude == 2.0
        assert cfg.seed == 0

    def test_attack_rate_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="attack_rate"):
            CalibrationPoisoningConfig(
                attack_rate=0.0,
                objective=AttackerObjective.THRESHOLD_RAISE,
                shift_magnitude=1.0,
            )

    def test_attack_rate_over_one_raises(self) -> None:
        with pytest.raises(ValueError, match="attack_rate"):
            CalibrationPoisoningConfig(
                attack_rate=1.01,
                objective=AttackerObjective.THRESHOLD_RAISE,
                shift_magnitude=1.0,
            )

    def test_negative_shift_magnitude_raises(self) -> None:
        with pytest.raises(ValueError, match="shift_magnitude"):
            CalibrationPoisoningConfig(
                attack_rate=0.1,
                objective=AttackerObjective.THRESHOLD_RAISE,
                shift_magnitude=-0.1,
            )

    def test_boundary_attack_rate_one(self) -> None:
        cfg = CalibrationPoisoningConfig(
            attack_rate=1.0,
            objective=AttackerObjective.THRESHOLD_LOWER,
            shift_magnitude=0.5,
        )
        assert cfg.attack_rate == 1.0

    def test_zero_shift_magnitude_is_valid(self) -> None:
        cfg = CalibrationPoisoningConfig(
            attack_rate=0.5,
            objective=AttackerObjective.THRESHOLD_RAISE,
            shift_magnitude=0.0,
        )
        assert cfg.shift_magnitude == 0.0
