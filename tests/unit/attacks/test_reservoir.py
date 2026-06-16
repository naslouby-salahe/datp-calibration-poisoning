"""Tests for victim-local reservoir selection ."""

from __future__ import annotations

import numpy as np

from datp.attacks.poison_enums import PoisoningSourceStrategy
from datp.attacks.reservoir import (
    ReservoirStatus,
    build_reservoir,
)
from datp.testsupport.synthetic_scores import (
    make_degenerate_tail_client,
    make_eligible_client,
)


class TestBuildReservoirRandom:
    def test_pool_is_full_cal(self) -> None:
        c = make_eligible_client()
        res = build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.RANDOM_BENIGN,
            tail_mass=0.10,
        )
        np.testing.assert_array_equal(res.pool, c.cal)
        assert res.status == ReservoirStatus.FEASIBLE
        assert res.n_pool == c.n_cal

    def test_does_not_mutate_clean(self) -> None:
        c = make_eligible_client()
        original = c.cal.copy()
        build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.RANDOM_BENIGN,
            tail_mass=0.10,
        )
        np.testing.assert_array_equal(c.cal, original)


class TestBuildReservoirHigh:
    def test_pool_is_upper_tail(self) -> None:
        c = make_eligible_client()
        res = build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            tail_mass=0.10,
        )
        n_tail = max(1, int(0.10 * c.n_cal))
        assert res.n_pool == n_tail
        sorted_cal = np.sort(c.cal)
        expected = sorted_cal[-n_tail:]
        np.testing.assert_array_equal(res.pool, expected)
        assert res.status == ReservoirStatus.FEASIBLE

    def test_all_pool_values_gte_threshold(self) -> None:
        c = make_eligible_client()
        res = build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            tail_mass=0.10,
        )
        p90 = np.percentile(c.cal, 90)
        assert np.all(res.pool >= p90 - 1e-10)


class TestBuildReservoirLow:
    def test_pool_is_lower_tail(self) -> None:
        c = make_eligible_client()
        res = build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.LOW_SCORE_BENIGN,
            tail_mass=0.10,
        )
        n_tail = max(1, int(0.10 * c.n_cal))
        assert res.n_pool == n_tail
        sorted_cal = np.sort(c.cal)
        expected = sorted_cal[:n_tail]
        np.testing.assert_array_equal(res.pool, expected)
        assert res.status == ReservoirStatus.FEASIBLE

    def test_all_pool_values_lte_threshold(self) -> None:
        c = make_eligible_client()
        res = build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.LOW_SCORE_BENIGN,
            tail_mass=0.10,
        )
        p10 = np.percentile(c.cal, 10)
        assert np.all(res.pool <= p10 + 1e-10)


class TestDegenerateTail:
    def test_degenerate_high_is_infeasible(self) -> None:
        c = make_degenerate_tail_client()
        res = build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            tail_mass=0.10,
        )
        assert res.status == ReservoirStatus.INFEASIBLE_DEGENERATE_TAIL
        assert res.n_distinct < 2

    def test_degenerate_low_is_infeasible(self) -> None:
        c = make_degenerate_tail_client()
        res = build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.LOW_SCORE_BENIGN,
            tail_mass=0.10,
        )
        assert res.status == ReservoirStatus.INFEASIBLE_DEGENERATE_TAIL
        assert res.n_distinct < 2

    def test_degenerate_random_is_still_feasible(self) -> None:
        c = make_degenerate_tail_client()
        res = build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.RANDOM_BENIGN,
            tail_mass=0.10,
        )
        assert res.status == ReservoirStatus.FEASIBLE


class TestNoMutation:
    def test_high_does_not_mutate(self) -> None:
        c = make_eligible_client()
        original = c.cal.copy()
        build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            tail_mass=0.10,
        )
        np.testing.assert_array_equal(c.cal, original)

    def test_low_does_not_mutate(self) -> None:
        c = make_eligible_client()
        original = c.cal.copy()
        build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.LOW_SCORE_BENIGN,
            tail_mass=0.10,
        )
        np.testing.assert_array_equal(c.cal, original)


class TestReservoirResult:
    def test_source_recorded(self) -> None:
        c = make_eligible_client()
        for source in [
            PoisoningSourceStrategy.RANDOM_BENIGN,
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        ]:
            res = build_reservoir(clean_cal=c.cal, source=source, tail_mass=0.10)
            assert res.source == source
