from __future__ import annotations

from datp.attacks.calibration_poisoning import PoisoningObjective
from datp.attacks.poisoning_metrics import PoisoningEffect, PoisoningExperimentResult
from datp.core.enums import Baseline


class TestPoisoningEffect:
    def test_absolute_shift_positive(self) -> None:
        effect = PoisoningEffect(
            baseline=Baseline.B1,
            client_id="c1",
            clean_threshold=0.5,
            poisoned_threshold=0.8,
            objective=PoisoningObjective.RAISE_THRESHOLD,
        )
        assert abs(effect.absolute_shift - 0.3) < 1e-9

    def test_absolute_shift_negative(self) -> None:
        effect = PoisoningEffect(
            baseline=Baseline.B2,
            client_id="c1",
            clean_threshold=0.5,
            poisoned_threshold=0.3,
            objective=PoisoningObjective.LOWER_THRESHOLD,
        )
        assert abs(effect.absolute_shift - (-0.2)) < 1e-9

    def test_relative_shift(self) -> None:
        effect = PoisoningEffect(
            baseline=Baseline.B1,
            client_id="c1",
            clean_threshold=1.0,
            poisoned_threshold=1.5,
            objective=PoisoningObjective.RAISE_THRESHOLD,
        )
        assert abs(effect.relative_shift - 0.5) < 1e-9

    def test_relative_shift_zero_clean_threshold(self) -> None:
        effect = PoisoningEffect(
            baseline=Baseline.B1,
            client_id="c1",
            clean_threshold=0.0,
            poisoned_threshold=1.0,
            objective=PoisoningObjective.RAISE_THRESHOLD,
        )
        assert effect.relative_shift == float("inf")


class TestPoisoningExperimentResult:
    def _make_result(self, effects: list[PoisoningEffect]) -> PoisoningExperimentResult:
        return PoisoningExperimentResult(
            attack_rate=0.1,
            shift_magnitude=1.0,
            objective=PoisoningObjective.RAISE_THRESHOLD,
            effects=effects,
        )

    def test_mean_absolute_shift_single(self) -> None:
        effect = PoisoningEffect(
            baseline=Baseline.B1,
            client_id="c1",
            clean_threshold=0.5,
            poisoned_threshold=1.0,
            objective=PoisoningObjective.RAISE_THRESHOLD,
        )
        result = self._make_result([effect])
        assert abs(result.mean_absolute_shift(Baseline.B1) - 0.5) < 1e-9

    def test_mean_absolute_shift_empty_baseline(self) -> None:
        result = self._make_result([])
        assert result.mean_absolute_shift(Baseline.B2) == 0.0

    def test_mean_absolute_shift_filters_by_baseline(self) -> None:
        effects = [
            PoisoningEffect(
                baseline=Baseline.B1, client_id="c1",
                clean_threshold=1.0, poisoned_threshold=2.0,
                objective=PoisoningObjective.RAISE_THRESHOLD,
            ),
            PoisoningEffect(
                baseline=Baseline.B2, client_id="c1",
                clean_threshold=1.0, poisoned_threshold=3.0,
                objective=PoisoningObjective.RAISE_THRESHOLD,
            ),
        ]
        result = self._make_result(effects)
        assert abs(result.mean_absolute_shift(Baseline.B1) - 1.0) < 1e-9
        assert abs(result.mean_absolute_shift(Baseline.B2) - 2.0) < 1e-9
