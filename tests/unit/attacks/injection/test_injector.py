"""Tests for the fixed-budget replacement injector ."""

from __future__ import annotations

import numpy as np
import pytest

from datp.attacks.injection.injector import inject_fixed_budget
from datp.attacks.reservoirs.reservoir import ReservoirResult, ReservoirStatus, build_reservoir
from datp.attacks.enums import PoisoningSourceStrategy
from datp.core.seed_sequence import make_seed_rng
from datp.testsupport.synthetic_scores import (
    make_degenerate_tail_client,
    make_eligible_client,
)


def _rng(seed: int = 100) -> np.random.Generator:
    return make_seed_rng(
        training_seed=0, poisoning_seed=seed, client_idx=0, scope_idx=0
    )


def _reservoir(client_cal: np.ndarray) -> ReservoirResult:
    return build_reservoir(
        clean_cal=client_cal,
        source=PoisoningSourceStrategy.RANDOM_BENIGN,
        tail_mass=0.10,
    )


class TestFractionZero:
    def test_zero_fraction_returns_exact_copy(self) -> None:
        c = make_eligible_client()
        res = inject_fixed_budget(
            clean_cal=c.cal,
            reservoir=_reservoir(c.cal),
            fraction=0.0,
            rng=_rng(),
        )
        np.testing.assert_array_equal(res.poisoned_cal, c.cal)
        assert res.n_replaced == 0
        assert res.positions_replaced.shape[0] == 0

    def test_zero_fraction_does_not_share_memory(self) -> None:
        c = make_eligible_client()
        res = inject_fixed_budget(
            clean_cal=c.cal,
            reservoir=_reservoir(c.cal),
            fraction=0.0,
            rng=_rng(),
        )
        assert not np.shares_memory(res.poisoned_cal, c.cal)


class TestCardinalityPreserved:
    @pytest.mark.parametrize("fraction", [0.10, 0.20, 0.40])
    def test_cardinality_unchanged(self, fraction: float) -> None:
        c = make_eligible_client()
        res = inject_fixed_budget(
            clean_cal=c.cal,
            reservoir=_reservoir(c.cal),
            fraction=fraction,
            rng=_rng(),
        )
        assert res.poisoned_cal.shape == c.cal.shape
        assert res.n_total == c.n_cal


class TestBudgetFormula:
    @pytest.mark.parametrize(
        "fraction, n_cal, expected_m",
        [
            (0.10, 200, 20),
            (0.20, 200, 40),
            (0.40, 200, 80),
            (0.10, 100, 10),
            (0.01, 100, 1),
        ],
    )
    def test_m_formula(self, fraction: float, n_cal: int, expected_m: int) -> None:
        assert max(1, round(fraction * n_cal)) == expected_m

    @pytest.mark.parametrize("fraction", [0.10, 0.20, 0.40])
    def test_n_replaced_matches_budget(self, fraction: float) -> None:
        c = make_eligible_client()
        res = inject_fixed_budget(
            clean_cal=c.cal,
            reservoir=_reservoir(c.cal),
            fraction=fraction,
            rng=_rng(),
        )
        expected = max(1, round(fraction * c.n_cal))
        assert res.n_replaced == expected


class TestNoInPlaceMutation:
    @pytest.mark.parametrize("fraction", [0.0, 0.10, 0.40])
    def test_clean_unchanged(self, fraction: float) -> None:
        c = make_eligible_client()
        original = c.cal.copy()
        inject_fixed_budget(
            clean_cal=c.cal,
            reservoir=_reservoir(c.cal),
            fraction=fraction,
            rng=_rng(),
        )
        np.testing.assert_array_equal(c.cal, original)


class TestDeterminism:
    def test_same_seed_same_result(self) -> None:
        c = make_eligible_client()
        reservoir = _reservoir(c.cal)
        res1 = inject_fixed_budget(
            clean_cal=c.cal, reservoir=reservoir, fraction=0.20, rng=_rng(100)
        )
        res2 = inject_fixed_budget(
            clean_cal=c.cal, reservoir=reservoir, fraction=0.20, rng=_rng(100)
        )
        np.testing.assert_array_equal(res1.poisoned_cal, res2.poisoned_cal)
        np.testing.assert_array_equal(res1.positions_replaced, res2.positions_replaced)

    def test_different_seed_different_result(self) -> None:
        c = make_eligible_client()
        reservoir = _reservoir(c.cal)
        res1 = inject_fixed_budget(
            clean_cal=c.cal, reservoir=reservoir, fraction=0.20, rng=_rng(100)
        )
        res2 = inject_fixed_budget(
            clean_cal=c.cal, reservoir=reservoir, fraction=0.20, rng=_rng(101)
        )
        assert not np.array_equal(res1.poisoned_cal, res2.poisoned_cal)


class TestInfeasibleReservoir:
    def test_raises_on_infeasible(self) -> None:
        c = make_degenerate_tail_client()
        reservoir = build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            tail_mass=0.10,
        )
        assert reservoir.status == ReservoirStatus.INFEASIBLE_DEGENERATE_TAIL
        with pytest.raises(ValueError, match="INFEASIBLE"):
            inject_fixed_budget(
                clean_cal=c.cal,
                reservoir=reservoir,
                fraction=0.20,
                rng=_rng(),
            )


class TestInvalidFraction:
    def test_negative_fraction(self) -> None:
        c = make_eligible_client()
        with pytest.raises(ValueError, match="fraction"):
            inject_fixed_budget(
                clean_cal=c.cal,
                reservoir=_reservoir(c.cal),
                fraction=-0.1,
                rng=_rng(),
            )

    def test_fraction_above_one(self) -> None:
        c = make_eligible_client()
        with pytest.raises(ValueError, match="fraction"):
            inject_fixed_budget(
                clean_cal=c.cal,
                reservoir=_reservoir(c.cal),
                fraction=1.5,
                rng=_rng(),
            )
