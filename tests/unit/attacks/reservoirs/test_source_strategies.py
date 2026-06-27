"""Unit tests for reservoir source strategies (RANDOM_BENIGN, HIGH_SCORE_BENIGN, LOW_SCORE_BENIGN)."""

from __future__ import annotations

import numpy as np
import pytest

from datp.attacks.enums import (
    PoisoningSourceStrategy,
    ReservoirStatus,
    is_diagnostic_source,
)
from datp.attacks.reservoirs.reservoir import build_reservoir
from datp.testsupport.synthetic_scores import make_eligible_client

_TAIL_MASS = 0.10


class TestIsDiagnosticSource:
    """Diagnostic source detection."""

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
    """Reservoir source selection for bounded sweep."""

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
        res = build_reservoir(clean_cal=c.cal, source=source, tail_mass=_TAIL_MASS)
        assert res.status == ReservoirStatus.FEASIBLE
        assert res.source == source

    def test_does_not_mutate_clean(self) -> None:
        c = make_eligible_client()
        original = c.cal.copy()
        build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            tail_mass=_TAIL_MASS,
        )
        np.testing.assert_array_equal(c.cal, original)


class TestDirectionalEffects:
    """HIGH_SCORE_BENIGN raises and LOW_SCORE_BENIGN lowers threshold."""

    def _inject_and_threshold(
        self,
        source: PoisoningSourceStrategy,
        fraction: float = 0.40,
        q: float = 0.95,
    ) -> tuple[float, float]:

        from datp.attacks.injection.injector import inject_fixed_budget
        from datp.core.seeds import SeedRecord, make_seed_rng
        from datp.core.seeds import SeedPair

        c = make_eligible_client(client_idx=0)
        rng = make_seed_rng(
            SeedRecord(
                pair=SeedPair(training_seed=0, poisoning_seed=100),
                client_idx=0,
                scope_idx=0,
            )
        )
        reservoir = build_reservoir(
            clean_cal=c.cal, source=source, tail_mass=_TAIL_MASS
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

        tau_clean, tau_pois = self._inject_and_threshold(
            PoisoningSourceStrategy.RANDOM_BENIGN
        )
        delta = abs(tau_pois - tau_clean)

        assert delta <= 0.20 * abs(tau_clean) + 1e-6, (
            f"RANDOM_BENIGN should be near-null; delta={delta:.6f}, "
            f"tau_clean={tau_clean:.4f}"
        )
