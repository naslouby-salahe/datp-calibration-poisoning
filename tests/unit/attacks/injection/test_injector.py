"""Tests verifying poisoning sample injection execution, budget calculations, and stream child index mappings."""

from __future__ import annotations

import math

import numpy as np
import pytest

from datp.attacks.enums import AttackerObjective, PoisoningSourceStrategy
from datp.attacks.execution.cell_runner import cell_child_index
from datp.attacks.injection.injector import inject_fixed_budget
from datp.attacks.reservoirs.reservoir import (
    ReservoirResult,
    ReservoirStatus,
    build_reservoir,
)
from datp.core.seeds import SeedPair, SeedRecord, make_seed_rng
from datp.testsupport.synthetic_scores import (
    make_degenerate_tail_client,
    make_eligible_client,
)


def _rng(seed: int = 100) -> np.random.Generator:
    """Helper to build a numpy Generator for testing."""
    return make_seed_rng(
        SeedRecord(
            pair=SeedPair(training_seed=0, poisoning_seed=seed),
            client_idx=0,
            scope_idx=0,
        )
    )


def _reservoir(client_cal: np.ndarray) -> ReservoirResult:
    """Helper to build a benign reservoir from calibration scores."""
    return build_reservoir(
        clean_cal=client_cal,
        source=PoisoningSourceStrategy.RANDOM_BENIGN,
        tail_mass=0.10,
    )


class TestFractionZero:
    """Tests verifying zero fraction injection edge cases."""

    def test_zero_fraction_returns_exact_copy(self) -> None:
        """Verify that zero fraction returns an exact score copy and zero replaced count."""
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
        """Verify that zero fraction does not share memory/reference with original array."""
        c = make_eligible_client()
        res = inject_fixed_budget(
            clean_cal=c.cal,
            reservoir=_reservoir(c.cal),
            fraction=0.0,
            rng=_rng(),
        )
        assert not np.shares_memory(res.poisoned_cal, c.cal)


class TestCardinalityPreserved:
    """Tests verifying that array length is not changed by injection."""

    @pytest.mark.parametrize("fraction", [0.10, 0.20, 0.40])
    def test_cardinality_unchanged(self, fraction: float) -> None:
        """Verify that poisoned output shape matches clean shape exactly."""
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
    """Tests verifying poisoning replacement budget count formulas."""

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
        """Verify that max(1, round(fraction * n_cal)) gives expected integer budget."""
        assert max(1, round(fraction * n_cal)) == expected_m

    @pytest.mark.parametrize("fraction", [0.10, 0.20, 0.40])
    def test_n_replaced_matches_budget(self, fraction: float) -> None:
        """Verify that the actual count of replaced values matches budget formula."""
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
    """Tests verifying that original inputs are not mutated in-place."""

    @pytest.mark.parametrize("fraction", [0.0, 0.10, 0.40])
    def test_clean_unchanged(self, fraction: float) -> None:
        """Verify that clean calibration array remains unmodified after execution."""
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
    """Tests verifying deterministic selection under fixed seeds."""

    def test_same_seed_same_result(self) -> None:
        """Verify that calling injection with identical seed results in identical replacements."""
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
        """Verify that calling injection with different seeds results in different replacements."""
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
    """Tests verifying error handling for infeasible degenerate tail reservoirs."""

    def test_raises_on_infeasible(self) -> None:
        """Verify that trying to inject from an infeasible reservoir raises ValueError."""
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
    """Tests verifying bounds checking on fraction inputs."""

    def test_negative_fraction(self) -> None:
        """Verify that negative fractions raise ValueError."""
        c = make_eligible_client()
        with pytest.raises(ValueError, match="fraction"):
            inject_fixed_budget(
                clean_cal=c.cal,
                reservoir=_reservoir(c.cal),
                fraction=-0.1,
                rng=_rng(),
            )

    def test_fraction_above_one(self) -> None:
        """Verify that fractions greater than 1.0 raise ValueError."""
        c = make_eligible_client()
        with pytest.raises(ValueError, match="fraction"):
            inject_fixed_budget(
                clean_cal=c.cal,
                reservoir=_reservoir(c.cal),
                fraction=1.5,
                rng=_rng(),
            )


class TestCellChildIndex:
    """Tests verifying deterministic child index mapping functionality."""

    def test_none_objective_returns_zero(self) -> None:
        """Verify that a None objective defaults to index zero."""
        idx = cell_child_index(PoisoningSourceStrategy.RANDOM_BENIGN, None, 0.20)
        assert idx == 0

    def test_different_objectives_give_different_indices(self) -> None:
        """Verify that raise vs lower objectives map to distinct indices."""
        idx_raise = cell_child_index(
            PoisoningSourceStrategy.RANDOM_BENIGN,
            AttackerObjective.THRESHOLD_RAISE,
            0.20,
        )
        idx_lower = cell_child_index(
            PoisoningSourceStrategy.RANDOM_BENIGN,
            AttackerObjective.THRESHOLD_LOWER,
            0.20,
        )
        assert idx_raise != idx_lower

    def test_different_sources_give_different_indices(self) -> None:
        """Verify that distinct poisoning sources map to distinct indices."""
        idx_high = cell_child_index(
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            AttackerObjective.THRESHOLD_RAISE,
            0.20,
        )
        idx_random = cell_child_index(
            PoisoningSourceStrategy.RANDOM_BENIGN,
            AttackerObjective.THRESHOLD_RAISE,
            0.20,
        )
        assert idx_high != idx_random

    def test_different_fractions_give_different_indices(self) -> None:
        """Verify that distinct fractions map to distinct indices."""
        idx_10 = cell_child_index(
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            AttackerObjective.THRESHOLD_RAISE,
            0.10,
        )
        idx_40 = cell_child_index(
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            AttackerObjective.THRESHOLD_RAISE,
            0.40,
        )
        assert idx_10 != idx_40

    def test_deterministic(self) -> None:
        """Verify that cell_child_index is deterministic."""
        idx_a = cell_child_index(
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
            AttackerObjective.THRESHOLD_LOWER,
            0.10,
        )
        idx_b = cell_child_index(
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
            AttackerObjective.THRESHOLD_LOWER,
            0.10,
        )
        assert idx_a == idx_b

    def test_all_main_pairs_have_unique_indices(self) -> None:
        """Verify that all source/objective/fraction main sweep combinations map to unique indices."""
        from datp.attacks.constants import (
            NBAIOT_MAIN_SOURCE_OBJECTIVE_PAIRS,
            NBAIOT_MAIN_SWEEP_FRACTIONS,
        )

        indices: list[int] = []
        for source, objective in NBAIOT_MAIN_SOURCE_OBJECTIVE_PAIRS:
            for fraction in NBAIOT_MAIN_SWEEP_FRACTIONS:
                if math.isclose(fraction, 0.0, abs_tol=1e-12):
                    continue
                idx = cell_child_index(source, objective, fraction)
                indices.append(idx)
        assert len(indices) == len(set(indices)), (
            "cell_child_index must produce unique indices for every "
            "(source, objective, fraction) main cell"
        )


class TestInjectionStreamIndependence:
    """Tests verifying independence of random generators across target sub-indices."""

    def _rng_for_cell(
        self,
        source: PoisoningSourceStrategy,
        objective: AttackerObjective,
        fraction: float,
        *,
        training_seed: int = 0,
        poisoning_seed: int = 100,
    ) -> np.random.Generator:
        """Helper to derive SeedRecord random generator."""
        return make_seed_rng(
            SeedRecord(
                pair=SeedPair(
                    training_seed=training_seed, poisoning_seed=poisoning_seed
                ),
                client_idx=0,
                scope_idx=0,
            ),
            child_index=cell_child_index(source, objective, fraction),
        )

    def test_different_objectives_give_different_positions(self) -> None:
        """Verify that raise vs lower objectives select distinct replacement indices."""
        c = make_eligible_client()
        reservoir = _reservoir(c.cal)
        res_raise = inject_fixed_budget(
            clean_cal=c.cal,
            reservoir=reservoir,
            fraction=0.20,
            rng=self._rng_for_cell(
                PoisoningSourceStrategy.RANDOM_BENIGN,
                AttackerObjective.THRESHOLD_RAISE,
                0.20,
            ),
        )
        res_lower = inject_fixed_budget(
            clean_cal=c.cal,
            reservoir=reservoir,
            fraction=0.20,
            rng=self._rng_for_cell(
                PoisoningSourceStrategy.RANDOM_BENIGN,
                AttackerObjective.THRESHOLD_LOWER,
                0.20,
            ),
        )
        assert not np.array_equal(
            np.sort(res_raise.positions_replaced),
            np.sort(res_lower.positions_replaced),
        ), "Different objectives must select different replacement positions"

    def test_different_sources_give_different_positions(self) -> None:
        """Verify that high-score vs random sources select distinct replacement indices."""
        c = make_eligible_client()
        res_high = inject_fixed_budget(
            clean_cal=c.cal,
            reservoir=_reservoir(c.cal),
            fraction=0.20,
            rng=self._rng_for_cell(
                PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
                AttackerObjective.THRESHOLD_RAISE,
                0.20,
            ),
        )
        res_random = inject_fixed_budget(
            clean_cal=c.cal,
            reservoir=_reservoir(c.cal),
            fraction=0.20,
            rng=self._rng_for_cell(
                PoisoningSourceStrategy.RANDOM_BENIGN,
                AttackerObjective.THRESHOLD_RAISE,
                0.20,
            ),
        )
        assert not np.array_equal(
            np.sort(res_high.positions_replaced),
            np.sort(res_random.positions_replaced),
        ), "Different sources must select different replacement positions"

    def test_different_fractions_give_different_positions(self) -> None:
        """Verify that distinct fractions select distinct replacement indices."""
        c = make_eligible_client()
        reservoir = _reservoir(c.cal)
        res_10 = inject_fixed_budget(
            clean_cal=c.cal,
            reservoir=reservoir,
            fraction=0.10,
            rng=self._rng_for_cell(
                PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
                AttackerObjective.THRESHOLD_RAISE,
                0.10,
            ),
        )
        res_40 = inject_fixed_budget(
            clean_cal=c.cal,
            reservoir=reservoir,
            fraction=0.40,
            rng=self._rng_for_cell(
                PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
                AttackerObjective.THRESHOLD_RAISE,
                0.40,
            ),
        )

        assert res_10.n_replaced != res_40.n_replaced or not np.array_equal(
            np.sort(res_10.positions_replaced),
            np.sort(res_40.positions_replaced),
        )
