from __future__ import annotations

import numpy as np
import pytest

from datp.attacks.calibration_poisoning import PoisoningObjective, poison_calibration_errors


def _make_errors(n: int = 100, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.uniform(0.0, 1.0, size=n).astype(np.float64)


class TestPoisoningObjectives:
    def test_raise_threshold_increases_mean(self) -> None:
        errors = _make_errors()
        rng = np.random.default_rng(42)
        poisoned = poison_calibration_errors(
            errors, attack_rate=0.2, objective=PoisoningObjective.RAISE_THRESHOLD,
            shift_magnitude=10.0, rng=rng,
        )
        assert poisoned.mean() > errors.mean()

    def test_lower_threshold_decreases_mean(self) -> None:
        errors = _make_errors()
        rng = np.random.default_rng(42)
        poisoned = poison_calibration_errors(
            errors, attack_rate=0.2, objective=PoisoningObjective.LOWER_THRESHOLD,
            shift_magnitude=0.5, rng=rng,
        )
        assert poisoned.mean() < errors.mean()

    def test_lower_threshold_clips_at_zero(self) -> None:
        errors = np.array([0.1, 0.2, 0.3])
        rng = np.random.default_rng(0)
        poisoned = poison_calibration_errors(
            errors, attack_rate=1.0, objective=PoisoningObjective.LOWER_THRESHOLD,
            shift_magnitude=100.0, rng=rng,
        )
        assert (poisoned >= 0.0).all()


class TestPoisonedArrayProperties:
    def test_output_shape_matches_input(self) -> None:
        errors = _make_errors(50)
        rng = np.random.default_rng(0)
        poisoned = poison_calibration_errors(
            errors, attack_rate=0.1, objective=PoisoningObjective.RAISE_THRESHOLD,
            shift_magnitude=1.0, rng=rng,
        )
        assert poisoned.shape == errors.shape

    def test_original_not_mutated(self) -> None:
        errors = _make_errors(50)
        original = errors.copy()
        rng = np.random.default_rng(0)
        poison_calibration_errors(
            errors, attack_rate=0.5, objective=PoisoningObjective.RAISE_THRESHOLD,
            shift_magnitude=5.0, rng=rng,
        )
        np.testing.assert_array_equal(errors, original)

    def test_zero_shift_magnitude_leaves_values_unchanged(self) -> None:
        errors = _make_errors(50)
        rng = np.random.default_rng(0)
        poisoned = poison_calibration_errors(
            errors, attack_rate=0.5, objective=PoisoningObjective.RAISE_THRESHOLD,
            shift_magnitude=0.0, rng=rng,
        )
        np.testing.assert_array_equal(poisoned, errors)

    def test_full_attack_rate_poisons_all(self) -> None:
        errors = np.zeros(10, dtype=np.float64)
        rng = np.random.default_rng(0)
        poisoned = poison_calibration_errors(
            errors, attack_rate=1.0, objective=PoisoningObjective.RAISE_THRESHOLD,
            shift_magnitude=1.0, rng=rng,
        )
        assert (poisoned == 1.0).all()


class TestPoisoningValidation:
    def test_invalid_attack_rate_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="attack_rate"):
            poison_calibration_errors(
                np.zeros(10), attack_rate=0.0,
                objective=PoisoningObjective.RAISE_THRESHOLD,
                shift_magnitude=1.0, rng=np.random.default_rng(0),
            )

    def test_invalid_attack_rate_over_one_raises(self) -> None:
        with pytest.raises(ValueError, match="attack_rate"):
            poison_calibration_errors(
                np.zeros(10), attack_rate=1.1,
                objective=PoisoningObjective.RAISE_THRESHOLD,
                shift_magnitude=1.0, rng=np.random.default_rng(0),
            )
