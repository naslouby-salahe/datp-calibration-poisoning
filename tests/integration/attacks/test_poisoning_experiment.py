from __future__ import annotations

import numpy as np

from datp.attacks.calibration_poisoning import PoisoningObjective
from datp.attacks.poisoning_config import CalibrationPoisoningConfig
from datp.attacks.poisoning_metrics import PoisoningExperimentResult
from datp.config.compose import BASE_CONFIG
from datp.core.enums import Baseline, Regime
from datp.experiments.calibration_poisoning import run_poisoning_experiment

_THRESHOLD_CFG = BASE_CONFIG.threshold
_N_SAMPLES = 200
_N_CLIENTS = 4


def _make_client_errors(n_clients: int = _N_CLIENTS, n_samples: int = _N_SAMPLES, seed: int = 0) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    return {
        f"client_{i}": rng.exponential(scale=0.5, size=n_samples).astype(np.float64)
        for i in range(n_clients)
    }


class TestRunPoisoningExperimentRaiseThreshold:
    def test_returns_result_type(self) -> None:
        client_errors = _make_client_errors()
        config = CalibrationPoisoningConfig(
            attack_rate=0.1,
            objective=PoisoningObjective.RAISE_THRESHOLD,
            shift_magnitude=5.0,
        )
        result = run_poisoning_experiment(
            client_errors, config, _THRESHOLD_CFG, Regime.A
        )
        assert isinstance(result, PoisoningExperimentResult)

    def test_effects_cover_b1_b2_b4(self) -> None:
        client_errors = _make_client_errors()
        config = CalibrationPoisoningConfig(
            attack_rate=0.2,
            objective=PoisoningObjective.RAISE_THRESHOLD,
            shift_magnitude=5.0,
        )
        result = run_poisoning_experiment(
            client_errors, config, _THRESHOLD_CFG, Regime.A
        )
        baselines_present = {e.baseline for e in result.effects}
        assert Baseline.B1 in baselines_present
        assert Baseline.B2 in baselines_present
        assert Baseline.B4 in baselines_present

    def test_raise_threshold_increases_b1_mean_shift(self) -> None:
        client_errors = _make_client_errors()
        config = CalibrationPoisoningConfig(
            attack_rate=0.3,
            objective=PoisoningObjective.RAISE_THRESHOLD,
            shift_magnitude=10.0,
        )
        result = run_poisoning_experiment(
            client_errors, config, _THRESHOLD_CFG, Regime.A
        )
        assert result.mean_absolute_shift(Baseline.B1) > 0


class TestRunPoisoningExperimentLowerThreshold:
    def test_lower_threshold_decreases_b1_mean_shift(self) -> None:
        client_errors = _make_client_errors()
        config = CalibrationPoisoningConfig(
            attack_rate=0.3,
            objective=PoisoningObjective.LOWER_THRESHOLD,
            shift_magnitude=0.5,
        )
        result = run_poisoning_experiment(
            client_errors, config, _THRESHOLD_CFG, Regime.A
        )
        assert result.mean_absolute_shift(Baseline.B1) < 0

    def test_zero_shift_has_no_effect(self) -> None:
        client_errors = _make_client_errors()
        config = CalibrationPoisoningConfig(
            attack_rate=0.5,
            objective=PoisoningObjective.RAISE_THRESHOLD,
            shift_magnitude=0.0,
        )
        result = run_poisoning_experiment(
            client_errors, config, _THRESHOLD_CFG, Regime.A
        )
        for effect in result.effects:
            assert abs(effect.absolute_shift) < 1e-9

    def test_result_metadata_matches_config(self) -> None:
        client_errors = _make_client_errors()
        config = CalibrationPoisoningConfig(
            attack_rate=0.15,
            objective=PoisoningObjective.LOWER_THRESHOLD,
            shift_magnitude=0.3,
        )
        result = run_poisoning_experiment(
            client_errors, config, _THRESHOLD_CFG, Regime.A
        )
        assert result.attack_rate == config.attack_rate
        assert result.shift_magnitude == config.shift_magnitude
        assert result.objective == config.objective
