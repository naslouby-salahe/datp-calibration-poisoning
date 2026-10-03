from __future__ import annotations

import math

import numpy as np
import pytest

from datp.attacks.injection import (
    GuardrailError,
    ReservoirResult,
    ScoreCollection,
    assert_bounded_scale_requires_single_client,
    assert_fractions_in_locked_grid,
    assert_no_inplace_mutation,
    assert_reservoir_not_test_or_training,
    assert_valid_source_objective_pair,
    build_reservoir,
    build_score_collection,
    enumerate_bounded_sweep_matrix,
    inject_fixed_budget,
)
from datp.attacks.sweep import cell_child_index
from datp.config import (
    CLUSTER_K_NBAIOT,
    CLUSTER_MAX_ITER,
    CLUSTER_N_INIT,
    CLUSTER_RANDOM_STATE,
    DEFAULT_POLICIES,
    MATERIALITY_FACTOR,
    N_MIN,
    NBAIOT_MAIN_SWEEP_FRACTIONS,
    NBAIOT_MAIN_SWEEP_OBJECTIVES,
    NBAIOT_MAIN_SWEEP_SOURCES,
    TAIL_MASS,
    CalibrationPoisoningConfig,
    ExperimentStage,
)
from datp.core import SeedPair, SeedRecord, make_seed_rng
from datp.enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    PoisoningDefense,
    PoisoningKnowledge,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ReservoirDraw,
    ReservoirStatus,
    ScoringStage,
    ThresholdPolicy,
    is_diagnostic_source,
)
from datp.scoring import ScoringColumn
from tests_support.synthetic_scores import (
    StandardScoreSetRequest,
    SyntheticClientSpec,
    make_degenerate_tail_client,
    make_eligible_client,
    make_pending_client,
    make_standard_score_set,
    make_synthetic_client,
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
        assert res.n_total == c.cal.size


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
        expected = max(1, round(fraction * c.cal.size))
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
        from datp.config import (
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


class TestWithoutReplacement:
    """Distinct-draw injection mode."""

    def test_draws_are_distinct_when_pool_suffices(self) -> None:
        """Without-replacement injection never repeats a reservoir value."""
        c = make_eligible_client()
        reservoir = _reservoir(c.cal)
        result = inject_fixed_budget(
            clean_cal=c.cal,
            reservoir=reservoir,
            fraction=0.10,
            rng=_rng(),
            draw=ReservoirDraw.WITHOUT_REPLACEMENT,
        )
        replaced = result.poisoned_cal[result.positions_replaced]
        assert len(np.unique(replaced)) == len(replaced)

    def test_oversized_budget_is_rejected(self) -> None:
        """A budget larger than the pool cannot be drawn without replacement."""
        c = make_eligible_client()
        reservoir = build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            tail_mass=0.10,
        )
        with pytest.raises(ValueError, match="without replacement"):
            inject_fixed_budget(
                clean_cal=c.cal,
                reservoir=reservoir,
                fraction=0.40,
                rng=_rng(),
                draw=ReservoirDraw.WITHOUT_REPLACEMENT,
            )

    def test_default_draw_matches_explicit_with_replacement(self) -> None:
        """The default mode equals explicit with-replacement for the same RNG stream."""
        c = make_eligible_client()
        reservoir = _reservoir(c.cal)
        default = inject_fixed_budget(
            clean_cal=c.cal, reservoir=reservoir, fraction=0.20, rng=_rng()
        )
        explicit = inject_fixed_budget(
            clean_cal=c.cal,
            reservoir=reservoir,
            fraction=0.20,
            rng=_rng(),
            draw=ReservoirDraw.WITH_REPLACEMENT,
        )
        assert np.array_equal(default.poisoned_cal, explicit.poisoned_cal)


class TestInterpolatedTail:
    """Distribution-constrained synthesis from the reservoir hull."""

    def test_values_stay_inside_pool_range_and_are_new(self) -> None:
        c = make_eligible_client()
        reservoir = build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            tail_mass=0.10,
        )
        result = inject_fixed_budget(
            clean_cal=c.cal,
            reservoir=reservoir,
            fraction=0.40,
            rng=_rng(),
            draw=ReservoirDraw.INTERPOLATED_TAIL,
        )
        injected = result.poisoned_cal[result.positions_replaced]
        assert injected.min() >= reservoir.pool.min()
        assert injected.max() <= reservoir.pool.max()
        assert len(np.unique(injected)) == len(injected)
        assert result.n_replaced == round(0.40 * c.cal.size)

    def test_degenerate_pool_is_rejected(self) -> None:
        reservoir = ReservoirResult(
            pool=np.array([1.0]),
            status=ReservoirStatus.FEASIBLE,
            source=PoisoningSourceStrategy.RANDOM_BENIGN,
            n_pool=1,
            n_distinct=1,
        )
        with pytest.raises(ValueError, match="at least 2"):
            inject_fixed_budget(
                clean_cal=np.arange(200.0),
                reservoir=reservoir,
                fraction=0.10,
                rng=_rng(),
                draw=ReservoirDraw.INTERPOLATED_TAIL,
            )


class TestDisjointReservoir:
    """Separate reservoir built only from entries that are not replaced."""

    def test_replacement_values_come_from_untouched_entries(self) -> None:
        from datp.attacks.injection import inject_disjoint_reservoir

        c = make_eligible_client()
        result, reservoir = inject_disjoint_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.RANDOM_BENIGN,
            tail_mass=0.10,
            fraction=0.20,
            rng=_rng(),
        )
        keep = np.ones(c.cal.size, dtype=bool)
        keep[result.positions_replaced] = False
        injected = result.poisoned_cal[result.positions_replaced]
        assert np.isin(injected, c.cal[keep]).all()
        assert len(reservoir.pool) == int(keep.sum())
        assert np.array_equal(result.poisoned_cal[keep], c.cal[keep])

    def test_tail_budget_is_capped_by_disjoint_pool(self) -> None:
        from datp.attacks.injection import disjoint_budget, inject_disjoint_reservoir

        c = make_eligible_client()
        n = c.cal.size
        result, _ = inject_disjoint_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            tail_mass=0.10,
            fraction=0.40,
            rng=_rng(),
        )
        assert result.n_replaced == disjoint_budget(
            n, round(0.40 * n), 0.10, PoisoningSourceStrategy.HIGH_SCORE_BENIGN
        )
        assert result.n_replaced < round(0.40 * n)

    def test_zero_fraction_changes_nothing(self) -> None:
        from datp.attacks.injection import inject_disjoint_reservoir

        c = make_eligible_client()
        result, _ = inject_disjoint_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.RANDOM_BENIGN,
            tail_mass=0.10,
            fraction=0.0,
            rng=_rng(),
        )
        assert result.n_replaced == 0
        assert np.array_equal(result.poisoned_cal, c.cal)


class TestBuildReservoirRandom:
    """Reservoir built with RANDOM_BENIGN source."""

    def test_pool_is_full_cal(self) -> None:
        c = make_eligible_client()
        res = build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.RANDOM_BENIGN,
            tail_mass=0.10,
        )
        np.testing.assert_array_equal(res.pool, c.cal)
        assert res.status == ReservoirStatus.FEASIBLE
        assert res.n_pool == c.cal.size

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
    """Reservoir built with HIGH_SCORE_BENIGN source."""

    def test_pool_is_upper_tail(self) -> None:
        c = make_eligible_client()
        res = build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            tail_mass=0.10,
        )
        n_tail = max(1, int(0.10 * c.cal.size))
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
    """Reservoir built with LOW_SCORE_BENIGN source."""

    def test_pool_is_lower_tail(self) -> None:
        c = make_eligible_client()
        res = build_reservoir(
            clean_cal=c.cal,
            source=PoisoningSourceStrategy.LOW_SCORE_BENIGN,
            tail_mass=0.10,
        )
        n_tail = max(1, int(0.10 * c.cal.size))
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
    """Degenerate and tail-edge reservoir cases."""

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
    """Reservoir construction never mutates the source array."""

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
    """ReservoirResult field integrity."""

    def test_source_recorded(self) -> None:
        c = make_eligible_client()
        for source in [
            PoisoningSourceStrategy.RANDOM_BENIGN,
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        ]:
            res = build_reservoir(clean_cal=c.cal, source=source, tail_mass=0.10)
            assert res.source == source


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

        from datp.attacks.injection import inject_fixed_budget
        from datp.core import SeedPair, SeedRecord, make_seed_rng

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


_VICTIMS: tuple[str, ...] = ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8")


_VICTIMS_BY_SEED: dict[int, tuple[str, ...]] = dict.fromkeys(tuple(range(10)), _VICTIMS)


def _bounded_config() -> CalibrationPoisoningConfig:
    """Helper to build a default bounded sweep CalibrationPoisoningConfig."""
    return CalibrationPoisoningConfig.for_bounded_sweep()


def test_matrix_size_is_exactly_4320() -> None:
    """Verify that the default bounded sweep matrix contains exactly 4,320 evaluation cells."""
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert len(cells) == 10 * 9 * 3 * 4 * 4


def test_matrix_policies_are_exactly_default_three() -> None:
    """Verify that the sweep matrix includes all three threshold policies exactly."""
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert {c.policy for c in cells} == {
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    }


def test_matrix_excludes_fraction_005() -> None:
    """Verify that the bounded sweep matrix excludes the 0.05 fraction grid points."""
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert all(not math.isclose(c.fraction, 0.05, abs_tol=0.0) for c in cells)


def test_matrix_fractions_are_exactly_locked_grid() -> None:
    """Verify that fractions used in the sweep map exactly to main grid fractions."""
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert sorted({c.fraction for c in cells}) == pytest.approx([0.0, 0.10, 0.20, 0.40])


def test_matrix_sources_are_exactly_bounded_three() -> None:
    """Verify that sources sweep covers the three core client strategies."""
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert {c.source for c in cells} == {
        PoisoningSourceStrategy.RANDOM_BENIGN,
        PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        PoisoningSourceStrategy.LOW_SCORE_BENIGN,
    }


def test_matrix_source_objective_pairs_are_exactly_main_four() -> None:
    """Verify that the sweep combines sources and objectives according to design rules."""
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert {(c.source, c.objective) for c in cells} == {
        (
            PoisoningSourceStrategy.RANDOM_BENIGN,
            AttackerObjective.THRESHOLD_RAISE,
        ),
        (
            PoisoningSourceStrategy.RANDOM_BENIGN,
            AttackerObjective.THRESHOLD_LOWER,
        ),
        (
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            AttackerObjective.THRESHOLD_RAISE,
        ),
        (
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
            AttackerObjective.THRESHOLD_LOWER,
        ),
    }


def test_matrix_seed_pairs_are_exactly_the_locked_ten() -> None:
    """Verify that training and poisoning seed combinations map exactly to range indices."""
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    pairs = {(c.training_seed, c.poisoning_seed) for c in cells}
    assert pairs == {(seed, seed + 100) for seed in range(10)}


def test_matrix_target_scope_is_always_single_client() -> None:
    """Verify that target_scope is SINGLE_CLIENT for all sweep configurations."""
    cells = enumerate_bounded_sweep_matrix(_VICTIMS_BY_SEED, _bounded_config())
    assert all(c.target_scope == PoisoningTargetScope.SINGLE_CLIENT for c in cells)


def test_matrix_missing_seed_raises_keyerror() -> None:
    """Verify that passing an incomplete training seeds mapping raises KeyError."""
    incomplete = {0: _VICTIMS}
    with pytest.raises(KeyError):
        enumerate_bounded_sweep_matrix(incomplete, _bounded_config())


class TestNoInplaceMutation:
    """Guardrail: injection never mutates the original collection in place."""

    def test_identical_arrays_pass(self) -> None:
        arr = np.array([1.0, 2.0, 3.0])
        copy = arr.copy()
        assert_no_inplace_mutation(copy, arr)

    def test_mutated_array_raises(self) -> None:
        original = np.array([1.0, 2.0, 3.0])
        original_copy = original.copy()
        original[0] = 99.0
        with pytest.raises(GuardrailError, match="mutated in place"):
            assert_no_inplace_mutation(original_copy, original)

    def test_label_appears_in_error(self) -> None:
        before = np.array([1.0])
        after = np.array([2.0])
        with pytest.raises(GuardrailError, match="threshold_scores"):
            assert_no_inplace_mutation(before, after, label="threshold_scores")

    def test_empty_arrays_pass(self) -> None:
        assert_no_inplace_mutation(np.array([]), np.array([]))


class TestReservoirNotTestOrTraining:
    """Guardrail: reservoir contains only calibration scores, not test or training data."""

    def test_calibration_label_passes(self) -> None:
        assert_reservoir_not_test_or_training(ScoringStage.CAL)

    def test_test_benign_label_raises(self) -> None:
        with pytest.raises(GuardrailError, match="test"):
            assert_reservoir_not_test_or_training(ScoringStage.TEST_BENIGN)

    def test_test_attack_label_raises(self) -> None:
        with pytest.raises(GuardrailError, match="test"):
            assert_reservoir_not_test_or_training(ScoringStage.TEST_ATTACK)


class TestFractionsInLockedGrid:
    """Fraction values must belong to the locked grid."""

    def test_bounded_fractions_all_pass(self) -> None:
        assert_fractions_in_locked_grid(
            NBAIOT_MAIN_SWEEP_FRACTIONS
        )

    def test_zero_fraction_passes(self) -> None:
        assert_fractions_in_locked_grid([0.0])

    def test_010_fraction_passes(self) -> None:
        assert_fractions_in_locked_grid([0.10])

    def test_invalid_fraction_raises(self) -> None:
        with pytest.raises(GuardrailError, match="0.3"):
            assert_fractions_in_locked_grid([0.3])

    def test_005_not_in_bounded_grid(self) -> None:
        with pytest.raises(GuardrailError, match="0.05"):
            assert_fractions_in_locked_grid([0.05])

    def test_empty_fractions_pass(self) -> None:
        assert_fractions_in_locked_grid([])

    def test_error_message_includes_allowed_grid(self) -> None:
        with pytest.raises(GuardrailError, match="locked grid"):
            assert_fractions_in_locked_grid([0.99])


class TestBoundedScaleRequiresSingleClient:
    """Bounded-scale sweep requires single-client target scope."""

    def test_bounded_with_single_client_passes(self) -> None:
        assert_bounded_scale_requires_single_client(PoisoningTargetScope.SINGLE_CLIENT)

    def test_bounded_with_multi_client_raises(self) -> None:
        with pytest.raises(GuardrailError, match="SINGLE_CLIENT"):
            assert_bounded_scale_requires_single_client(PoisoningTargetScope.MULTI_CLIENT)


class TestValidSourceObjectivePair:
    """Only valid source-objective pairs pass validation."""

    def test_high_score_with_raise_passes(self) -> None:
        assert_valid_source_objective_pair(
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            AttackerObjective.THRESHOLD_RAISE,
        )

    def test_low_score_with_lower_passes(self) -> None:
        assert_valid_source_objective_pair(
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
            AttackerObjective.THRESHOLD_LOWER,
        )

    def test_random_benign_with_raise_passes(self) -> None:
        assert_valid_source_objective_pair(
            PoisoningSourceStrategy.RANDOM_BENIGN,
            AttackerObjective.THRESHOLD_RAISE,
        )

    def test_random_benign_with_lower_passes(self) -> None:
        assert_valid_source_objective_pair(
            PoisoningSourceStrategy.RANDOM_BENIGN,
            AttackerObjective.THRESHOLD_LOWER,
        )

    def test_high_score_with_lower_raises(self) -> None:
        with pytest.raises(GuardrailError, match="THRESHOLD_RAISE"):
            assert_valid_source_objective_pair(
                PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
                AttackerObjective.THRESHOLD_LOWER,
            )

    def test_low_score_with_raise_raises(self) -> None:
        with pytest.raises(GuardrailError, match="THRESHOLD_LOWER"):
            assert_valid_source_objective_pair(
                PoisoningSourceStrategy.LOW_SCORE_BENIGN,
                AttackerObjective.THRESHOLD_RAISE,
            )

    def test_error_message_includes_source_and_objective(self) -> None:
        with pytest.raises(GuardrailError, match="HIGH_SCORE_BENIGN"):
            assert_valid_source_objective_pair(
                PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
                AttackerObjective.THRESHOLD_LOWER,
            )


def _collection_from_synthetics() -> ScoreCollection:
    """Helper to build a ScoreCollection instance populated with standard synthetic client scores."""
    ss = make_standard_score_set(StandardScoreSetRequest(n_eligible=3, n_pending=1))
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    return build_score_collection(raw)


class TestScoreCollection:
    """Tests verifying sorting, formatting, and coverage ratio methods of ScoreCollection."""

    def test_eligible_pending_partition(self) -> None:
        """Verify that ScoreCollection partitions clients into eligible/pending arrays based on N_MIN sample count."""
        col = _collection_from_synthetics()
        assert len(col.eligibility.eligible_ids) == 3
        assert len(col.eligibility.pending_ids) == 1
        assert set(col.eligibility.eligible_ids) | set(col.eligibility.pending_ids) == set(col.all_ids)

    def test_eligible_ids_sorted(self) -> None:
        """Verify that the list of eligible client IDs is returned sorted alphabetically."""
        col = _collection_from_synthetics()
        assert col.eligibility.eligible_ids == tuple(sorted(col.eligibility.eligible_ids))

    def test_calibration_errors_include_all_clients(self) -> None:
        """Calibration error values retain each client's domain identity."""
        col = _collection_from_synthetics()
        calibration_errors = col.calibration_errors
        assert len(calibration_errors.clients) == 4

    def test_eligible_calibration_errors(self) -> None:
        """Eligible calibration errors contain only clients above the sample minimum."""
        col = _collection_from_synthetics()
        ecal = col.eligible_calibration_errors
        assert len(ecal.clients) == 3
        for client in ecal.clients:
            cid = client.client_id
            assert cid in col.eligibility.eligible_ids

    def test_coverage_ratio(self) -> None:
        """Verify that coverage_ratio computes correct fraction (eligible count / total count)."""
        col = _collection_from_synthetics()
        assert col.coverage_ratio == pytest.approx(3 / 4)

    def test_coverage_ratio_empty(self) -> None:
        """Verify that coverage_ratio returns 0.0 if the collection is empty."""
        col = build_score_collection({})
        assert col.coverage_ratio == pytest.approx(0.0)

    def test_n_min_boundary(self) -> None:
        """Verify partitioning boundary conditions around minimum calibration sample count N_MIN."""
        e = make_eligible_client(client_id="e0")
        p = make_pending_client(client_id="p0")
        raw = {
            e.client_id: (e.cal, e.test_benign, e.test_attack),
            p.client_id: (p.cal, p.test_benign, p.test_attack),
        }
        col = build_score_collection(raw)
        assert e.client_id in col.eligibility.eligible_ids
        assert p.client_id in col.eligibility.pending_ids


def test_score_collection_survives_pickle_round_trip() -> None:
    """Collections must pickle so process-based workers can receive them."""
    import pickle

    import numpy as np

    from datp.attacks.injection import build_score_collection

    collection = build_score_collection(
        {
            "a": (np.arange(200.0), np.zeros(5), np.ones(5)),
            "b": (np.arange(150.0), np.zeros(4), np.ones(4)),
        }
    )
    restored = pickle.loads(pickle.dumps(collection))
    assert restored.all_ids == collection.all_ids
    assert restored.eligibility.eligible_ids == collection.eligibility.eligible_ids
    assert np.array_equal(restored.clients["a"].cal, collection.clients["a"].cal)


def test_calibration_constants() -> None:
    assert N_MIN == 100
    assert abs(TAIL_MASS - 0.10) < 1e-9
    assert abs(MATERIALITY_FACTOR - 0.1) < 1e-9


def test_cluster_constants() -> None:
    assert CLUSTER_K_NBAIOT == 3
    assert CLUSTER_N_INIT == 10
    assert CLUSTER_MAX_ITER == 300
    assert CLUSTER_RANDOM_STATE == 42


def test_bounded_fraction_grid() -> None:
    assert NBAIOT_MAIN_SWEEP_FRACTIONS == (0.0, 0.10, 0.20, 0.40)


class TestCanonicalEnumVocabulary:
    """Tests verifying spelling and keys of all core poisoning policy enums."""

    def test_threshold_policy(self) -> None:
        """Verify that ThresholdPolicy values map exactly to their expected lower-case strings."""
        assert {p.name: p.value for p in ThresholdPolicy} == {
            "GLOBAL_THRESHOLD": "global_threshold",
            "LOCAL_THRESHOLD": "local_threshold",
            "CLUSTER_THRESHOLD": "cluster_threshold",
        }

    def test_attacker_objective(self) -> None:
        """Verify that AttackerObjective values match design definitions."""
        assert {o.name: o.value for o in AttackerObjective} == {
            "THRESHOLD_RAISE": "threshold_raise",
            "THRESHOLD_LOWER": "threshold_lower",
        }

    def test_poisoning_source_strategy(self) -> None:
        """Verify that PoisoningSourceStrategy options match core strategies."""
        assert {s.name: s.value for s in PoisoningSourceStrategy} == {
            "RANDOM_BENIGN": "random_benign",
            "HIGH_SCORE_BENIGN": "high_score_benign",
            "LOW_SCORE_BENIGN": "low_score_benign",
            "LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY": (
                "low_score_targeted_removal_diagnostic_only"
            ),
        }

    def test_calibration_injection_rule(self) -> None:
        """Verify that CalibrationInjectionRule values conform to design vocabs."""
        assert {r.name: r.value for r in CalibrationInjectionRule} == {
            "REPLACE_FIXED_BUDGET": "replace_fixed_budget",
        }

    def test_poisoning_knowledge(self) -> None:
        """Verify that PoisoningKnowledge keys map to their proper values."""
        assert {k.name: k.value for k in PoisoningKnowledge} == {
            "GRAY_BOX_SCORE_ACCESS": "gray_box_score_access",
        }

    def test_poisoning_target_scope(self) -> None:
        """Verify that PoisoningTargetScope settings match target definitions."""
        assert {t.name: t.value for t in PoisoningTargetScope} == {
            "SINGLE_CLIENT": "single_client",
            "MULTI_CLIENT": "multi_client",
        }

    def test_poisoning_defense(self) -> None:
        """Verify that PoisoningDefense names and string values are correct."""
        assert {d.name: d.value for d in PoisoningDefense} == {
            "NONE": "none",
            "TRIMMED_CALIBRATION": "trimmed_calibration",
        }

    def test_experiment_stage(self) -> None:
        """Verify that ExperimentStage contains only the runnable N-BaIoT main stage."""
        assert {s.name: s.value for s in ExperimentStage} == {
            "NBAIOT_MAIN": "nbaiot_main",
        }


class TestMainSweepConstants:
    """Tests verifying evaluation sweep ranges and bounds configuration constants."""

    def test_default_policies_are_all_three(self) -> None:
        """Verify that DEFAULT_POLICIES includes all three core threshold policies."""
        assert set(DEFAULT_POLICIES) == set(ThresholdPolicy)

    def test_main_objectives_cover_both(self) -> None:
        """Verify that main sweep objectives cover raise and lower."""
        assert set(NBAIOT_MAIN_SWEEP_OBJECTIVES) == set(AttackerObjective)

    def test_main_sources_exclude_diagnostic(self) -> None:
        """Verify that main sweep sources exclude diagnostic-only strategies."""
        assert len(NBAIOT_MAIN_SWEEP_SOURCES) == 3
        assert all("diagnostic" not in s.value for s in NBAIOT_MAIN_SWEEP_SOURCES)

    def test_main_fraction_grid(self) -> None:
        """Verify that main sweep fractions are set to default grid list."""
        assert NBAIOT_MAIN_SWEEP_FRACTIONS == (0.0, 0.10, 0.20, 0.40)


class TestMakeSyntheticClient:
    """Tests verifying formatting and reproducibility of make_synthetic_client."""

    def test_deterministic(self) -> None:
        """Verify that calling make_synthetic_client with identical parameters produces identical scores."""
        a = make_synthetic_client(SyntheticClientSpec(client_id="c0", client_idx=0))
        b = make_synthetic_client(SyntheticClientSpec(client_id="c0", client_idx=0))
        np.testing.assert_array_equal(a.cal, b.cal)
        np.testing.assert_array_equal(a.test_benign, b.test_benign)
        np.testing.assert_array_equal(a.test_attack, b.test_attack)

    def test_different_seeds_differ(self) -> None:
        """Verify that different seeds produce distinct synthetic scores."""
        a = make_synthetic_client(
            SyntheticClientSpec(client_id="c0", client_idx=0, training_seed=0)
        )
        b = make_synthetic_client(
            SyntheticClientSpec(client_id="c0", client_idx=0, training_seed=1)
        )
        assert not np.array_equal(a.cal, b.cal)

    def test_different_clients_differ(self) -> None:
        """Verify that distinct client IDs/indices result in distinct scores."""
        a = make_synthetic_client(SyntheticClientSpec(client_id="c0", client_idx=0))
        b = make_synthetic_client(SyntheticClientSpec(client_id="c1", client_idx=1))
        assert not np.array_equal(a.cal, b.cal)

    def test_shapes(self) -> None:
        """Verify that output shapes exactly match request sizes."""
        c = make_synthetic_client(
            SyntheticClientSpec(
                client_id="c0",
                n_cal=150,
                n_test_benign=30,
                n_test_attack=40,
            )
        )
        assert c.cal.shape == (150,)
        assert c.test_benign.shape == (30,)
        assert c.test_attack.shape == (40,)

    def test_non_negative(self) -> None:
        """Verify that all generated synthetic scores are non-negative values."""
        c = make_synthetic_client(SyntheticClientSpec(client_id="c0"))
        assert np.all(c.cal >= 0.0)
        assert np.all(c.test_benign >= 0.0)
        assert np.all(c.test_attack >= 0.0)

    def test_attack_scores_higher_than_benign(self) -> None:
        """Verify that attack score means are higher than benign score means."""
        c = make_synthetic_client(SyntheticClientSpec(client_id="c0"))
        assert np.mean(c.test_attack) > np.mean(c.test_benign)

    def test_score_column_attribute(self) -> None:
        """Verify that score_column attribute matches its enum member."""
        c = make_synthetic_client(SyntheticClientSpec(client_id="c0"))
        assert c.score_column == ScoringColumn.RECONSTRUCTION_ERROR


class TestEligibility:
    """Tests verifying client status classification based on calibration sample size."""

    def test_eligible_client_is_eligible(self) -> None:
        """Verify that make_eligible_client returns eligible clients exceeding N_MIN."""
        c = make_eligible_client()
        assert c.is_eligible
        assert c.cal.size >= N_MIN

    def test_pending_client_is_not_eligible(self) -> None:
        """Verify that make_pending_client returns pending clients below N_MIN."""
        c = make_pending_client()
        assert not c.is_eligible
        assert c.cal.size < N_MIN

    def test_boundary_eligible(self) -> None:
        """Verify that a sample count exactly at N_MIN is classified as eligible."""
        c = make_synthetic_client(SyntheticClientSpec(client_id="c0", n_cal=N_MIN))
        assert c.is_eligible

    def test_boundary_pending(self) -> None:
        """Verify that a sample count exactly one below N_MIN is classified as pending."""
        c = make_synthetic_client(SyntheticClientSpec(client_id="c0", n_cal=N_MIN - 1))
        assert not c.is_eligible


class TestDegenerateTailClient:
    """Tests verifying generation of tail-degenerate scores."""

    def test_is_eligible(self) -> None:
        """Verify that degenerate tail clients satisfy minimum sample count requirements."""
        c = make_degenerate_tail_client()
        assert c.is_eligible

    def test_cal_constant(self) -> None:
        """Verify that degenerate calibration contains only one unique value."""
        c = make_degenerate_tail_client()
        assert len(np.unique(c.cal)) == 1

    def test_upper_tail_degenerate(self) -> None:
        """Verify that upper tail contains only one unique degenerate value."""
        c = make_degenerate_tail_client()
        n_tail = max(1, int(0.10 * c.cal.size))
        upper_tail = np.sort(c.cal)[-n_tail:]
        assert len(np.unique(upper_tail)) < 2

    def test_lower_tail_degenerate(self) -> None:
        """Verify that lower tail contains only one unique degenerate value."""
        c = make_degenerate_tail_client()
        n_tail = max(1, int(0.10 * c.cal.size))
        lower_tail = np.sort(c.cal)[:n_tail]
        assert len(np.unique(lower_tail)) < 2


class TestStandardScoreSet:
    """Tests verifying the standard multi-client score sets."""

    def test_default_counts(self) -> None:
        """Verify default distribution of eligible and pending clients."""
        ss = make_standard_score_set()
        assert len(ss.eligible) == 9
        assert len(ss.pending) == 1
        assert len(ss.clients) == 10

    def test_eligible_ids(self) -> None:
        """Verify that eligible client IDs prefix with eligible_."""
        ss = make_standard_score_set()
        assert all(c.startswith("eligible_") for c in ss.eligible_ids)

    def test_pending_ids(self) -> None:
        """Verify that pending client IDs prefix with pending_."""
        ss = make_standard_score_set()
        assert all(c.startswith("pending_") for c in ss.pending_ids)

    def test_calibration_scores(self) -> None:
        """Verify structure of calibration_scores dict wrapper."""
        ss = make_standard_score_set()
        cal = ss.calibration_scores
        assert len(cal) == 10
        for client in cal.clients:
            assert isinstance(client.scores, np.ndarray)

    def test_client_by_id(self) -> None:
        """Verify retrieval of client by ID from standard set."""
        ss = make_standard_score_set()
        c = ss.client_by_id("eligible_0")
        assert c.client_id == "eligible_0"

    def test_client_by_id_missing(self) -> None:
        """Verify that requesting a missing ID raises a KeyError."""
        ss = make_standard_score_set()
        with pytest.raises(KeyError):
            ss.client_by_id("nonexistent")

    def test_with_degenerate(self) -> None:
        """Verify that including degenerate clients creates correct degenerate model."""
        ss = make_standard_score_set(StandardScoreSetRequest(include_degenerate=True))
        assert len(ss.clients) == 11
        degen = ss.client_by_id("degenerate_0")
        assert degen.is_eligible
        assert len(np.unique(degen.cal)) == 1

    def test_deterministic(self) -> None:
        """Verify that generated sets are deterministic across repeated calls."""
        a = make_standard_score_set()
        b = make_standard_score_set()
        for ca, cb in zip(a.clients, b.clients):
            np.testing.assert_array_equal(ca.cal, cb.cal)

    def test_custom_counts(self) -> None:
        """Verify custom eligible and pending client totals."""
        ss = make_standard_score_set(StandardScoreSetRequest(n_eligible=3, n_pending=2))
        assert len(ss.eligible) == 3
        assert len(ss.pending) == 2
