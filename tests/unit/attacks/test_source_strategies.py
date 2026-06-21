"""Tests for source strategy dispatch ."""

from __future__ import annotations

import numpy as np
import pytest

from datp.attacks.enums import (
    PoisoningSourceStrategy,
    ReservoirStatus,
    is_diagnostic_source,
)
from datp.attacks.source_strategies import (
    DiagnosticSourceError,
    near_null_criterion,
    _select_reservoir,
)
from datp.testsupport.synthetic_scores import make_eligible_client

_TAIL_MASS = 0.10


class TestIsDiagnosticSource:
    def test_bounded_sources_not_diagnostic(self) -> None:
        for source in [
            PoisoningSourceStrategy.RANDOM_BENIGN,
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        ]:
            assert not is_diagnostic_source(source)

    def test_diagnostic_source_flagged(self) -> None:
        assert is_diagnostic_source(
            PoisoningSourceStrategy.LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY
        )


class TestSelectReservoirBoundedSources:
    @pytest.mark.parametrize(
        "source",
        [
            PoisoningSourceStrategy.RANDOM_BENIGN,
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        ],
    )
    def test_bounded_sources_succeed(self, source: PoisoningSourceStrategy) -> None:
        c = make_eligible_client()
        res = _select_reservoir(source=source, clean_cal=c.cal, tail_mass=_TAIL_MASS)
        assert res.status == ReservoirStatus.FEASIBLE
        assert res.source == source

    def test_does_not_mutate_clean(self) -> None:
        c = make_eligible_client()
        original = c.cal.copy()
        _select_reservoir(
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            clean_cal=c.cal,
            tail_mass=_TAIL_MASS,
        )
        np.testing.assert_array_equal(c.cal, original)


class TestDiagnosticGate:
    def test_diagnostic_source_without_flag_raises(self) -> None:
        c = make_eligible_client()
        with pytest.raises(DiagnosticSourceError, match="diagnostic-only"):
            _select_reservoir(
                source=PoisoningSourceStrategy.LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY,
                clean_cal=c.cal,
                tail_mass=_TAIL_MASS,
                allow_diagnostic=False,
            )

    def test_diagnostic_source_with_flag_succeeds(self) -> None:
        c = make_eligible_client()
        res = _select_reservoir(
            source=PoisoningSourceStrategy.LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY,
            clean_cal=c.cal,
            tail_mass=_TAIL_MASS,
            allow_diagnostic=True,
        )
        assert (
            res.source
            == PoisoningSourceStrategy.LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY
        )

    def test_diagnostic_source_default_blocked(self) -> None:
        """Default allow_diagnostic=False blocks diagnostic source."""
        c = make_eligible_client()
        with pytest.raises(DiagnosticSourceError):
            _select_reservoir(
                source=PoisoningSourceStrategy.LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY,
                clean_cal=c.cal,
                tail_mass=_TAIL_MASS,
            )


class TestNearNullCriterion:
    def test_within_threshold_is_true(self) -> None:
        assert near_null_criterion(delta_tau=0.001, delta_tau_null_threshold=0.01)

    def test_outside_threshold_is_false(self) -> None:
        assert not near_null_criterion(delta_tau=0.05, delta_tau_null_threshold=0.01)

    def test_negative_delta_within_threshold(self) -> None:
        assert near_null_criterion(delta_tau=-0.005, delta_tau_null_threshold=0.01)

    def test_exact_boundary_is_true(self) -> None:
        assert near_null_criterion(delta_tau=0.01, delta_tau_null_threshold=0.01)

    def test_zero_delta_is_near_null(self) -> None:
        assert near_null_criterion(delta_tau=0.0, delta_tau_null_threshold=0.001)


class TestDirectionalEffects:
    """Verify that HIGH raises and LOW lowers the threshold on synthetic data.

    This is a directional sanity test: injecting HIGH_SCORE values into the
    calibration array should increase the quantile threshold; LOW_SCORE should
    decrease it.
    """

    def _inject_and_threshold(
        self,
        source: PoisoningSourceStrategy,
        fraction: float = 0.40,
        q: float = 0.95,
    ) -> tuple[float, float]:
        """Return (tau_clean, tau_pois) for one synthetic eligible client."""
        from datp.attacks.injector import inject_fixed_budget
        from datp.core.seed_sequence import SeedRecord, make_seed_rng
        from datp.core.seeds import SeedPair

        c = make_eligible_client(client_idx=0)
        rng = make_seed_rng(
            SeedRecord(
                pair=SeedPair(training_seed=0, poisoning_seed=100),
                client_idx=0,
                scope_idx=0,
            )
        )
        reservoir = _select_reservoir(
            source=source, clean_cal=c.cal, tail_mass=_TAIL_MASS
        )
        result = inject_fixed_budget(
            clean_cal=c.cal, reservoir=reservoir, fraction=fraction, rng=rng
        )
        tau_clean = float(np.quantile(c.cal, q))
        tau_pois = float(np.quantile(result.poisoned_cal, q))
        return tau_clean, tau_pois

    def test_high_score_raises_threshold(self) -> None:
        tau_clean, tau_pois = self._inject_and_threshold(
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN
        )
        assert tau_pois > tau_clean, (
            f"HIGH_SCORE_BENIGN should raise threshold; "
            f"clean={tau_clean:.4f}, pois={tau_pois:.4f}"
        )

    def test_low_score_lowers_threshold(self) -> None:
        tau_clean, tau_pois = self._inject_and_threshold(
            PoisoningSourceStrategy.LOW_SCORE_BENIGN
        )
        assert tau_pois < tau_clean, (
            f"LOW_SCORE_BENIGN should lower threshold; "
            f"clean={tau_clean:.4f}, pois={tau_pois:.4f}"
        )

    def test_random_near_null(self) -> None:
        """RANDOM_BENIGN should produce near-null threshold change (negative control)."""
        tau_clean, tau_pois = self._inject_and_threshold(
            PoisoningSourceStrategy.RANDOM_BENIGN
        )
        delta = abs(tau_pois - tau_clean)
        # Threshold change should be small relative to the overall scale.
        # We use 20% of tau_clean as a generous near-null bound for a
        # synthetic test; this verifies the negative-control property.
        assert delta <= 0.20 * abs(tau_clean) + 1e-6, (
            f"RANDOM_BENIGN should be near-null; delta={delta:.6f}, "
            f"tau_clean={tau_clean:.4f}"
        )
