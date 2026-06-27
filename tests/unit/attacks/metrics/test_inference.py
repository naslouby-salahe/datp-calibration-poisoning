"""Tests verifying inference metric calculations, bootstrap intervals, sign consistency, and Holm adjustments."""

from __future__ import annotations

import math

import pytest

from datp.attacks.constants import SIGN_CONSISTENCY_THRESHOLD
from datp.attacks.enums import AttackerObjective
from datp.attacks.metrics.inference import (
    BootstrapConfig,
    HolmConfig,
    HolmResult,
    InferenceInput,
    InferenceResult,
    PairedDeltas,
    SeedDelta,
    bootstrap_seed_aggregates,
    collect_paired_deltas,
    compute_inference,
    compute_seed_aggregates,
    holm_adjust,
    sign_test,
)
from datp.statistics.bootstrap import BootstrapResult

SEEDS: tuple[int, ...] = tuple(range(100, 110))


def _make_paired(
    victims: dict[str, dict[int, float]],
    feasible_seeds: set[int] | None = None,
) -> PairedDeltas:
    """Helper to build PairedDeltas structures from raw victim dict mappings."""
    deltas: dict[str, dict[int, SeedDelta]] = {}
    for vid, seed_map in victims.items():
        deltas[vid] = collect_paired_deltas(
            victim_id=vid,
            seed_deltas=seed_map,
            feasible_seeds=feasible_seeds,
        )
    return PairedDeltas(deltas=deltas)


def _uniform_paired(n_victims: int = 3, delta: float = 0.05) -> PairedDeltas:
    """Helper to build uniform PairedDeltas structures."""
    victims: dict[str, dict[int, float]] = {
        f"v{i}": dict.fromkeys(SEEDS, delta) for i in range(n_victims)
    }
    return _make_paired(victims)


class TestCollectPairedDeltas:
    """Tests verifying collection and filtering of paired seeds deltas."""

    def test_all_seeds_present(self) -> None:
        """Verify that all target seeds are present in collected paired deltas."""
        result = collect_paired_deltas(
            victim_id="v0",
            seed_deltas=dict.fromkeys(SEEDS, 0.1),
        )
        assert set(result.keys()) == set(SEEDS)

    def test_default_all_feasible(self) -> None:
        """Verify that all seeds default to feasible status when no filters are applied."""
        result = collect_paired_deltas(
            victim_id="v0",
            seed_deltas=dict.fromkeys(SEEDS, 0.1),
        )
        assert all(sd.feasible for sd in result.values())

    def test_feasible_filter(self) -> None:
        """Verify that only specified seeds are flagged as feasible."""
        result = collect_paired_deltas(
            victim_id="v0",
            seed_deltas=dict.fromkeys(SEEDS, 0.1),
            feasible_seeds={100, 101},
        )
        assert result[100].feasible
        assert result[101].feasible
        assert not result[102].feasible

    def test_victim_id_recorded(self) -> None:
        """Verify that the victim client ID is recorded on each SeedDelta entry."""
        result = collect_paired_deltas(
            victim_id="myVictim",
            seed_deltas={100: 0.2},
        )
        assert result[100].victim_id == "myVictim"

    def test_delta_tau_preserved(self) -> None:
        """Verify that delta_tau values are successfully recorded on each seed delta."""
        result = collect_paired_deltas(
            victim_id="v0",
            seed_deltas={100: 0.123},
        )
        assert result[100].delta_tau == pytest.approx(0.123)


class TestComputeSeedAggregates:
    """Tests verifying average seed aggregates computations across victim devices."""

    def test_uniform_delta_aggregates_to_same(self) -> None:
        """Verify that aggregating uniform delta inputs yields identical average outputs."""
        paired = _uniform_paired(n_victims=3, delta=0.05)
        agg = compute_seed_aggregates(paired, SEEDS)
        for s in SEEDS:
            assert agg[s] == pytest.approx(0.05)

    def test_all_seeds_in_result(self) -> None:
        """Verify that all target seeds are populated in seed aggregate output dict keys."""
        paired = _uniform_paired()
        agg = compute_seed_aggregates(paired, SEEDS)
        assert set(agg.keys()) == set(SEEDS)

    def test_missing_seed_in_victim_gives_nan(self) -> None:
        """Verify that seeds missing from victim outputs result in NaN averages."""
        victims = {
            "v0": {100: 0.1, 101: 0.1, 102: 0.1, 103: 0.1},
        }
        paired = _make_paired(victims)
        agg = compute_seed_aggregates(paired, SEEDS)
        assert math.isnan(agg[104])

    def test_infeasible_victims_excluded(self) -> None:
        """Verify that infeasible client seeds are excluded from average aggregates."""
        paired = PairedDeltas(
            deltas={
                "v0": collect_paired_deltas(
                    victim_id="v0",
                    seed_deltas=dict.fromkeys(SEEDS, 0.9),
                    feasible_seeds=set(),
                ),
                "v1": collect_paired_deltas(
                    victim_id="v1",
                    seed_deltas=dict.fromkeys(SEEDS, 0.1),
                ),
            }
        )
        agg = compute_seed_aggregates(paired, SEEDS)
        for s in SEEDS:
            assert agg[s] == pytest.approx(0.1)

    def test_average_across_victims(self) -> None:
        """Verify that seed aggregates reflect arithmetic average across victim devices."""
        victims = {
            "v0": dict.fromkeys(SEEDS, 0.0),
            "v1": dict.fromkeys(SEEDS, 0.2),
        }
        paired = _make_paired(victims)
        agg = compute_seed_aggregates(paired, SEEDS)
        for s in SEEDS:
            assert agg[s] == pytest.approx(0.1)


class TestSignTest:
    """Tests verifying direction-based sign tests and significance thresholds."""

    def test_all_positive_raise_consistent(self) -> None:
        """Verify that all positive changes are flagged consistent for raise objective."""
        agg = dict.fromkeys(SEEDS, 0.05)
        result = sign_test(agg, direction=AttackerObjective.THRESHOLD_RAISE)
        assert result.consistent
        assert result.n_positive == 10

    def test_all_negative_lower_consistent(self) -> None:
        """Verify that all negative changes are flagged consistent for lower objective."""
        agg = dict.fromkeys(SEEDS, -0.05)
        result = sign_test(agg, direction=AttackerObjective.THRESHOLD_LOWER)
        assert result.consistent

    def test_7_positive_raise_not_consistent(self) -> None:
        """Verify that 7 out of 10 positive changes fall below the consistency threshold."""
        agg = {seed: 0.1 if seed < 107 else -0.1 for seed in SEEDS}
        result = sign_test(agg, direction=AttackerObjective.THRESHOLD_RAISE)
        assert not result.consistent

    def test_8_positive_raise_consistent(self) -> None:
        """Verify that 8 out of 10 positive changes satisfy the consistency threshold."""
        agg = {seed: 0.1 if seed < 108 else -0.1 for seed in SEEDS}
        result = sign_test(agg, direction=AttackerObjective.THRESHOLD_RAISE)
        assert result.consistent

    def test_nan_excluded_from_counts(self) -> None:
        """Verify that NaN values are ignored and reported under separate nan counter."""
        agg = dict.fromkeys(SEEDS, 0.1)
        agg[102] = float("nan")
        result = sign_test(agg, direction=AttackerObjective.THRESHOLD_RAISE)
        assert result.n_nan == 1
        assert result.n_positive == 9

    def test_zero_counted_separately(self) -> None:
        """Verify that exact zero changes are logged under zero counter."""
        agg = dict.fromkeys(SEEDS, 0.1)
        agg[100] = 0.0
        result = sign_test(agg, direction=AttackerObjective.THRESHOLD_RAISE)
        assert result.n_zero == 1

    def test_threshold_in_result(self) -> None:
        """Verify that sign consistency threshold matches the global constant setting."""
        agg = dict.fromkeys(SEEDS, 0.1)
        result = sign_test(agg, direction=AttackerObjective.THRESHOLD_RAISE)
        assert result.sign_consistency_threshold == SIGN_CONSISTENCY_THRESHOLD

    def test_n_total_correct(self) -> None:
        """Verify that total sample count matches length of target input map."""
        agg = dict.fromkeys(SEEDS, 0.1)
        result = sign_test(agg, direction=AttackerObjective.THRESHOLD_RAISE)
        assert result.n_total == 10


class TestHolmAdjust:
    """Tests verifying Holm multiplicity adjustment configurations."""

    def test_returns_holm_result(self) -> None:
        """Verify that holm_adjust returns a HolmResult instance."""
        result = holm_adjust([0.01, 0.05, 0.10])
        assert isinstance(result, HolmResult)

    def test_descriptive_only_flag(self) -> None:
        """Verify that descriptive_only is True if p-values array size is less than 3."""
        result = holm_adjust([0.01, 0.05])
        assert result.descriptive_only is True

    def test_raw_p_values_preserved(self) -> None:
        """Verify that raw p-values are stored inside result attributes."""
        ps = [0.01, 0.05, 0.10]
        result = holm_adjust(ps)
        assert result.raw_p_values == tuple(ps)

    def test_holm_ge_raw(self) -> None:
        """Verify that Holm-adjusted p-values are always greater than or equal to raw p-values."""
        ps = [0.01, 0.02, 0.03]
        result = holm_adjust(ps)
        for raw, holm in zip(result.raw_p_values, result.holm_p_values):
            assert holm >= raw - 1e-12

    def test_single_p_value(self) -> None:
        """Verify that a single input p-value is unmodified by Holm correction."""
        result = holm_adjust([0.03])
        assert result.holm_p_values[0] == pytest.approx(0.03)

    def test_reject_at_alpha_01(self) -> None:
        """Verify rejection flag outcomes under significance level alpha."""
        result = holm_adjust([0.001, 0.001, 0.001], alpha=0.01)
        assert any(result.reject_h0)


class TestBootstrapSeedAggregates:
    """Tests verifying Bootstrap confidence intervals on average seed aggregate metrics."""

    def test_returns_bootstrap_result(self) -> None:
        """Verify that bootstrap aggregates return a valid BootstrapResult."""
        agg = {s: 0.05 + 0.01 * i for i, s in enumerate(SEEDS)}
        result = bootstrap_seed_aggregates(agg)
        assert isinstance(result, BootstrapResult)

    def test_ci_covers_positive_mean(self) -> None:
        """Verify that positive constant changes result in confidence intervals above 0.0."""
        agg = dict.fromkeys(SEEDS, 0.05)
        result = bootstrap_seed_aggregates(
            agg, config=BootstrapConfig(n_bootstrap=1_000, analysis_seed=300)
        )
        assert result.ci_lower > 0.0
        assert result.ci_upper > 0.0

    def test_raises_with_too_few_finite(self) -> None:
        """Verify that bootstrap raises ValueError if fewer than 2 finite inputs exist."""
        agg = {
            **{seed: float("nan") for seed in SEEDS},
            103: 0.1,
        }
        with pytest.raises(ValueError, match="at least 2 finite"):
            bootstrap_seed_aggregates(agg)

    def test_seed_filter(self) -> None:
        """Verify that bootstrap aggregates support execution on filtered subsets of seeds."""
        agg = {s: float(i) * 0.01 for i, s in enumerate(SEEDS)}
        r1 = bootstrap_seed_aggregates(
            agg,
            poisoning_seeds=(100, 101),
            config=BootstrapConfig(n_bootstrap=500, analysis_seed=300),
        )
        r2 = bootstrap_seed_aggregates(
            agg,
            poisoning_seeds=SEEDS,
            config=BootstrapConfig(n_bootstrap=500, analysis_seed=300),
        )

        assert isinstance(r1, BootstrapResult)
        assert isinstance(r2, BootstrapResult)

    def test_reproducible_with_same_seed(self) -> None:
        """Verify that bootstrap output is reproducible when setting fixed analysis_seed."""
        agg = {s: 0.05 + 0.01 * i for i, s in enumerate(SEEDS)}
        r1 = bootstrap_seed_aggregates(
            agg, config=BootstrapConfig(n_bootstrap=500, analysis_seed=300)
        )
        r2 = bootstrap_seed_aggregates(
            agg, config=BootstrapConfig(n_bootstrap=500, analysis_seed=300)
        )
        assert r1.ci_lower == pytest.approx(r2.ci_lower)
        assert r1.ci_upper == pytest.approx(r2.ci_upper)


class TestComputeInference:
    """Tests verifying the top-level inference engine calculations wrapper."""

    def test_returns_inference_result(self) -> None:
        """Verify that compute_inference returns an InferenceResult instance."""
        paired = _uniform_paired(delta=0.05)
        result = compute_inference(
            InferenceInput(
                paired=paired,
                poisoning_seeds=SEEDS,
                direction=AttackerObjective.THRESHOLD_RAISE,
            )
        )
        assert isinstance(result, InferenceResult)

    def test_seed_aggregates_populated(self) -> None:
        """Verify that average seed aggregates map is populated within the InferenceResult."""
        paired = _uniform_paired(delta=0.05)
        result = compute_inference(
            InferenceInput(
                paired=paired,
                poisoning_seeds=SEEDS,
                direction=AttackerObjective.THRESHOLD_RAISE,
            )
        )
        assert set(result.seed_aggregates.keys()) == set(SEEDS)

    def test_sign_test_consistent_for_uniform_raise(self) -> None:
        """Verify that sign_test is flagged consistent for uniform positive raise inputs."""
        paired = _uniform_paired(delta=0.05)
        result = compute_inference(
            InferenceInput(
                paired=paired,
                poisoning_seeds=SEEDS,
                direction=AttackerObjective.THRESHOLD_RAISE,
            )
        )
        assert result.sign_test.consistent

    def test_bootstrap_ci_excludes_zero_for_clear_raise(self) -> None:
        """Verify that bootstrap CI excludes zero for uniform clear raise inputs."""
        paired = _uniform_paired(n_victims=5, delta=0.10)
        result = compute_inference(
            InferenceInput(
                paired=paired,
                poisoning_seeds=SEEDS,
                direction=AttackerObjective.THRESHOLD_RAISE,
                bootstrap_config=BootstrapConfig(n_bootstrap=2_000),
            )
        )
        assert result.bootstrap_ci.ci_lower > 0.0

    def test_holm_none_by_default(self) -> None:
        """Verify that holm adjustment is None by default if no HolmConfig is provided."""
        paired = _uniform_paired()
        result = compute_inference(
            InferenceInput(
                paired=paired,
                poisoning_seeds=SEEDS,
                direction=AttackerObjective.THRESHOLD_RAISE,
            )
        )
        assert result.holm is None

    def test_holm_populated_when_requested(self) -> None:
        """Verify that holm results are populated when passing valid HolmConfig structures."""
        paired = _uniform_paired()
        result = compute_inference(
            InferenceInput(
                paired=paired,
                poisoning_seeds=SEEDS,
                direction=AttackerObjective.THRESHOLD_RAISE,
                holm_config=HolmConfig(p_values=[0.01, 0.02, 0.03]),
            )
        )
        assert result.holm is not None
        assert isinstance(result.holm, HolmResult)

    def test_n_feasible_victims_correct(self) -> None:
        """Verify that n_feasible_victims logs the correct count of active client devices."""
        paired = _uniform_paired(n_victims=3)
        result = compute_inference(
            InferenceInput(
                paired=paired,
                poisoning_seeds=SEEDS,
                direction=AttackerObjective.THRESHOLD_RAISE,
            )
        )
        assert result.n_feasible_victims == 3

    def test_infeasible_victim_excluded_from_count(self) -> None:
        """Verify that client devices with zero feasible seeds are excluded from victim count summaries."""
        paired = PairedDeltas(
            deltas={
                "v0": collect_paired_deltas(
                    victim_id="v0",
                    seed_deltas=dict.fromkeys(SEEDS, 0.05),
                    feasible_seeds=set(),
                ),
                "v1": collect_paired_deltas(
                    victim_id="v1", seed_deltas=dict.fromkeys(SEEDS, 0.05)
                ),
                "v2": collect_paired_deltas(
                    victim_id="v2", seed_deltas=dict.fromkeys(SEEDS, 0.05)
                ),
            }
        )
        result = compute_inference(
            InferenceInput(
                paired=paired,
                poisoning_seeds=SEEDS,
                direction=AttackerObjective.THRESHOLD_RAISE,
            )
        )
        assert result.n_feasible_victims == 2
