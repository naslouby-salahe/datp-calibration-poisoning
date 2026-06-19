import pytest

from datp.core.enums import Baseline, Regime
from datp.core.identity import BaselineRunId, TrainingCellId
from datp.core.regime import enforce_regime


@enforce_regime(Regime.A)
def _dummy_regime_a(*, regime: Regime) -> str:
    return f"ran with regime={regime}"


@enforce_regime(Regime.A, Regime.B)
def _dummy_regime_ab(*, regime: Regime) -> str:
    return f"ran with regime={regime}"


class TestEnforceRegimeDecorator:
    def test_allowed_regime_passes(self) -> None:
        assert _dummy_regime_a(regime=Regime.A) == "ran with regime=a"

    def test_disallowed_regime_raises(self) -> None:
        with pytest.raises(ValueError, match="restricted to"):
            _dummy_regime_a(regime=Regime.B)

    def test_disallowed_regime_c_raises(self) -> None:
        with pytest.raises(ValueError, match="restricted to"):
            _dummy_regime_a(regime=Regime.C)

    def test_missing_regime_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="requires 'regime'"):
            _dummy_regime_a()  # type: ignore[call-arg]

    def test_multiple_allowed_regimes(self) -> None:
        assert _dummy_regime_ab(regime=Regime.A) == "ran with regime=a"
        assert _dummy_regime_ab(regime=Regime.B) == "ran with regime=b"
        with pytest.raises(ValueError, match="restricted to"):
            _dummy_regime_ab(regime=Regime.C)


class TestB3RegimeRestriction:
    @staticmethod
    def _run(regime: Regime) -> BaselineRunId:
        return BaselineRunId(
            cell=TrainingCellId(regime=regime, seed=0, alpha=None),
            baseline=Baseline.B3,
        )

    def test_b3_excluded_regime_c(self) -> None:
        import numpy as np

        from datp.thresholding.strategies.b3_family import compute

        errors = {"c1": np.array([0.1, 0.2, 0.3] * 50, dtype=np.float32)}
        with pytest.raises(ValueError, match="restricted to"):
            compute(
                client_errors=errors,
                n_min=100,
                tau_global=0.5,
                family_map={"c1": "cameras"},
                q=0.95,
                regime=Regime.C,
                run=self._run(Regime.C),
            )

    def test_b3_excluded_regime_b(self) -> None:
        import numpy as np

        from datp.thresholding.strategies.b3_family import compute

        errors = {"c1": np.array([0.1, 0.2, 0.3] * 50, dtype=np.float32)}
        with pytest.raises(ValueError, match="restricted to"):
            compute(
                client_errors=errors,
                n_min=100,
                tau_global=0.5,
                family_map={"c1": "cameras"},
                q=0.95,
                regime=Regime.B,
                run=self._run(Regime.B),
            )

    def test_b3_allowed_regime_a(self) -> None:
        import numpy as np

        from datp.thresholding.strategies.b3_family import compute

        errors = {
            "c1": np.array([0.1, 0.2, 0.3] * 50, dtype=np.float32),
            "c2": np.array([0.4, 0.5, 0.6] * 50, dtype=np.float32),
        }
        result = compute(
            client_errors=errors,
            n_min=100,
            tau_global=0.5,
            family_map={"c1": "camera", "c2": "doorbell"},
            q=0.95,
            regime=Regime.A,
            run=self._run(Regime.A),
        )
        assert result.run.baseline.value == "b3"
