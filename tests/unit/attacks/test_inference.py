"""Tests for two-layer statistical inference ."""

from __future__ import annotations

import math

import pytest

from datp.attacks.inference import (
    InferenceInput,
    BootstrapConfig,
    HolmConfig,
    HolmResult,
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

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SEEDS: tuple[int, ...] = (100, 101, 102, 103, 104)


def _make_paired(
    victims: dict[str, dict[int, float]],
    feasible_seeds: set[int] | None = None,
) -> PairedDeltas:
    """Build a PairedDeltas from victim_id → {seed: delta_tau}."""
    deltas: dict[str, dict[int, SeedDelta]] = {}
    for vid, seed_map in victims.items():
        deltas[vid] = collect_paired_deltas(
            victim_id=vid,
            seed_deltas=seed_map,
            feasible_seeds=feasible_seeds,
        )
    return PairedDeltas(deltas=deltas)


def _uniform_paired(n_victims: int = 3, delta: float = 0.05) -> PairedDeltas:
    """All victims, all seeds, same positive delta_tau — fully feasible."""
    victims: dict[str, dict[int, float]] = {
        f"v{i}": dict.fromkeys(SEEDS, delta) for i in range(n_victims)
    }
    return _make_paired(victims)


# ---------------------------------------------------------------------------
# collect_paired_deltas
# ---------------------------------------------------------------------------


class TestCollectPairedDeltas:
    def test_all_seeds_present(self) -> None:
        result = collect_paired_deltas(
            victim_id="v0",
            seed_deltas=dict.fromkeys(SEEDS, 0.1),
        )
        assert set(result.keys()) == set(SEEDS)

    def test_default_all_feasible(self) -> None:
        result = collect_paired_deltas(
            victim_id="v0",
            seed_deltas=dict.fromkeys(SEEDS, 0.1),
        )
        assert all(sd.feasible for sd in result.values())

    def test_feasible_filter(self) -> None:
        result = collect_paired_deltas(
            victim_id="v0",
            seed_deltas=dict.fromkeys(SEEDS, 0.1),
            feasible_seeds={100, 101},
        )
        assert result[100].feasible
        assert result[101].feasible
        assert not result[102].feasible

    def test_victim_id_recorded(self) -> None:
        result = collect_paired_deltas(
            victim_id="myVictim",
            seed_deltas={100: 0.2},
        )
        assert result[100].victim_id == "myVictim"

    def test_delta_tau_preserved(self) -> None:
        result = collect_paired_deltas(
            victim_id="v0",
            seed_deltas={100: 0.123},
        )
        assert result[100].delta_tau == pytest.approx(0.123)


# ---------------------------------------------------------------------------
# compute_seed_aggregates
# ---------------------------------------------------------------------------


class TestComputeSeedAggregates:
    def test_uniform_delta_aggregates_to_same(self) -> None:
        paired = _uniform_paired(n_victims=3, delta=0.05)
        agg = compute_seed_aggregates(paired, SEEDS)
        for s in SEEDS:
            assert agg[s] == pytest.approx(0.05)

    def test_all_seeds_in_result(self) -> None:
        paired = _uniform_paired()
        agg = compute_seed_aggregates(paired, SEEDS)
        assert set(agg.keys()) == set(SEEDS)

    def test_missing_seed_in_victim_gives_nan(self) -> None:
        # One victim has no entry for seed 104.
        victims = {
            "v0": {100: 0.1, 101: 0.1, 102: 0.1, 103: 0.1},  # no 104
        }
        paired = _make_paired(victims)
        agg = compute_seed_aggregates(paired, SEEDS)
        assert math.isnan(agg[104])

    def test_infeasible_victims_excluded(self) -> None:
        # v0: all infeasible (delta=0.9); v1: all feasible (delta=0.1)
        paired = PairedDeltas(
            deltas={
                "v0": collect_paired_deltas(
                    victim_id="v0",
                    seed_deltas=dict.fromkeys(SEEDS, 0.9),
                    feasible_seeds=set(),  # none feasible
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
        # v0: 0.0, v1: 0.2 → mean 0.1
        victims = {
            "v0": dict.fromkeys(SEEDS, 0.0),
            "v1": dict.fromkeys(SEEDS, 0.2),
        }
        paired = _make_paired(victims)
        agg = compute_seed_aggregates(paired, SEEDS)
        for s in SEEDS:
            assert agg[s] == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# sign_test
# ---------------------------------------------------------------------------


class TestSignTest:
    def test_all_positive_raise_consistent(self) -> None:
        agg = dict.fromkeys(SEEDS, 0.05)  # 5/5 positive
        result = sign_test(agg, direction="raise")
        assert result.consistent
        assert result.n_positive == 5

    def test_all_negative_lower_consistent(self) -> None:
        agg = dict.fromkeys(SEEDS, -0.05)
        result = sign_test(agg, direction="lower")
        assert result.consistent

    def test_3_positive_raise_not_consistent(self) -> None:
        agg = {100: 0.1, 101: 0.1, 102: 0.1, 103: -0.1, 104: -0.1}
        result = sign_test(agg, direction="raise")
        assert not result.consistent  # 3/5 < threshold 4

    def test_4_positive_raise_consistent(self) -> None:
        agg = {100: 0.1, 101: 0.1, 102: 0.1, 103: 0.1, 104: -0.1}
        result = sign_test(agg, direction="raise")
        assert result.consistent

    def test_nan_excluded_from_counts(self) -> None:
        agg = {100: 0.1, 101: 0.1, 102: float("nan"), 103: 0.1, 104: 0.1}
        result = sign_test(agg, direction="raise")
        assert result.n_nan == 1
        assert result.n_positive == 4

    def test_zero_counted_separately(self) -> None:
        agg = {100: 0.0, 101: 0.1, 102: 0.1, 103: 0.1, 104: 0.1}
        result = sign_test(agg, direction="raise")
        assert result.n_zero == 1

    def test_threshold_in_result(self) -> None:
        agg = dict.fromkeys(SEEDS, 0.1)
        result = sign_test(agg, direction="raise")
        assert result.sign_consistency_threshold == 4

    def test_n_total_correct(self) -> None:
        agg = dict.fromkeys(SEEDS, 0.1)
        result = sign_test(agg, direction="raise")
        assert result.n_total == 5


# ---------------------------------------------------------------------------
# holm_adjust
# ---------------------------------------------------------------------------


class TestHolmAdjust:
    def test_returns_holm_result(self) -> None:
        result = holm_adjust([0.01, 0.05, 0.10])
        assert isinstance(result, HolmResult)

    def test_descriptive_only_flag(self) -> None:
        result = holm_adjust([0.01, 0.05])
        assert result.descriptive_only is True

    def test_raw_p_values_preserved(self) -> None:
        ps = [0.01, 0.05, 0.10]
        result = holm_adjust(ps)
        assert result.raw_p_values == tuple(ps)

    def test_holm_ge_raw(self) -> None:
        """Holm-adjusted p-values ≥ raw (more conservative)."""
        ps = [0.01, 0.02, 0.03]
        result = holm_adjust(ps)
        for raw, holm in zip(result.raw_p_values, result.holm_p_values):
            assert holm >= raw - 1e-12  # allow tiny float error

    def test_single_p_value(self) -> None:
        result = holm_adjust([0.03])
        assert result.holm_p_values[0] == pytest.approx(0.03)

    def test_reject_at_alpha_01(self) -> None:
        result = holm_adjust([0.001, 0.001, 0.001], alpha=0.01)
        assert any(result.reject_h0)


# ---------------------------------------------------------------------------
# bootstrap_seed_aggregates
# ---------------------------------------------------------------------------


class TestBootstrapSeedAggregates:
    def test_returns_bootstrap_result(self) -> None:
        agg = {s: 0.05 + 0.01 * i for i, s in enumerate(SEEDS)}
        result = bootstrap_seed_aggregates(agg)
        assert isinstance(result, BootstrapResult)

    def test_ci_covers_positive_mean(self) -> None:
        agg = dict.fromkeys(SEEDS, 0.05)
        result = bootstrap_seed_aggregates(
            agg, config=BootstrapConfig(n_bootstrap=1_000, analysis_seed=300)
        )
        assert result.ci_lower > 0.0
        assert result.ci_upper > 0.0

    def test_raises_with_too_few_finite(self) -> None:
        agg = {
            100: float("nan"),
            101: float("nan"),
            102: float("nan"),
            103: 0.1,
            104: float("nan"),
        }
        with pytest.raises(ValueError, match="at least 2 finite"):
            bootstrap_seed_aggregates(agg)

    def test_seed_filter(self) -> None:
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
        # Different input → potentially different CI
        assert isinstance(r1, BootstrapResult)
        assert isinstance(r2, BootstrapResult)

    def test_reproducible_with_same_seed(self) -> None:
        agg = {s: 0.05 + 0.01 * i for i, s in enumerate(SEEDS)}
        r1 = bootstrap_seed_aggregates(
            agg, config=BootstrapConfig(n_bootstrap=500, analysis_seed=300)
        )
        r2 = bootstrap_seed_aggregates(
            agg, config=BootstrapConfig(n_bootstrap=500, analysis_seed=300)
        )
        assert r1.ci_lower == pytest.approx(r2.ci_lower)
        assert r1.ci_upper == pytest.approx(r2.ci_upper)


# ---------------------------------------------------------------------------
# compute_inference
# ---------------------------------------------------------------------------


class TestComputeInference:
    def test_returns_inference_result(self) -> None:
        paired = _uniform_paired(delta=0.05)
        result = compute_inference(
            InferenceInput(
                paired=paired,
                poisoning_seeds=SEEDS,
                direction="raise",
            )
        )
        assert isinstance(result, InferenceResult)

    def test_seed_aggregates_populated(self) -> None:
        paired = _uniform_paired(delta=0.05)
        result = compute_inference(
            InferenceInput(
                paired=paired,
                poisoning_seeds=SEEDS,
                direction="raise",
            )
        )
        assert set(result.seed_aggregates.keys()) == set(SEEDS)

    def test_sign_test_consistent_for_uniform_raise(self) -> None:
        paired = _uniform_paired(delta=0.05)
        result = compute_inference(
            InferenceInput(
                paired=paired,
                poisoning_seeds=SEEDS,
                direction="raise",
            )
        )
        assert result.sign_test.consistent

    def test_bootstrap_ci_excludes_zero_for_clear_raise(self) -> None:
        paired = _uniform_paired(n_victims=5, delta=0.10)
        result = compute_inference(
            InferenceInput(
                paired=paired,
                poisoning_seeds=SEEDS,
                direction="raise",
                bootstrap_config=BootstrapConfig(n_bootstrap=2_000),
            )
        )
        assert result.bootstrap_ci.ci_lower > 0.0

    def test_holm_none_by_default(self) -> None:
        paired = _uniform_paired()
        result = compute_inference(
            InferenceInput(
                paired=paired,
                poisoning_seeds=SEEDS,
                direction="raise",
            )
        )
        assert result.holm is None

    def test_holm_populated_when_requested(self) -> None:
        paired = _uniform_paired()
        result = compute_inference(
            InferenceInput(
                paired=paired,
                poisoning_seeds=SEEDS,
                direction="raise",
                holm_config=HolmConfig(p_values=[0.01, 0.02, 0.03]),
            )
        )
        assert result.holm is not None
        assert isinstance(result.holm, HolmResult)

    def test_n_feasible_victims_correct(self) -> None:
        paired = _uniform_paired(n_victims=3)
        result = compute_inference(
            InferenceInput(
                paired=paired,
                poisoning_seeds=SEEDS,
                direction="raise",
            )
        )
        assert result.n_feasible_victims == 3

    def test_infeasible_victim_excluded_from_count(self) -> None:
        # v0 fully infeasible; v1, v2 feasible
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
                direction="raise",
            )
        )
        assert result.n_feasible_victims == 2
