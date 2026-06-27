"""Unit tests for statistical summary computation utilities."""

from __future__ import annotations

import math
import subprocess

import numpy as np
import pytest

from datp.reporting.enums import MechanismWording
from datp.statistics.aggregates import cv
from datp.statistics.bootstrap import BootstrapResult, bca_ci, bootstrap_ci
from datp.statistics.constants import BootstrapMethod, EffectMagnitude
from datp.statistics.effect_size import CliffsDeltaResult, cliffs_delta
from datp.statistics.spearman import SpearmanResult, spearman_correlation
from datp.statistics.wilcoxon import (
    BonferroniResult,
    WilcoxonResult,
    bonferroni_correct,
    wilcoxon_test,
)


class TestCV:
    """Coefficient of variation computation."""

    def test_known_values(self) -> None:
        arr = np.array([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0])
        expected = float(arr.std(ddof=1) / arr.mean())
        assert cv(arr, ddof=1) == pytest.approx(expected)

    def test_ddof_0_vs_ddof_1(self) -> None:

        arr = np.array([1.0, 3.0])
        cv_sample = cv(arr, ddof=1)
        cv_pop = cv(arr, ddof=0)
        assert cv_sample != pytest.approx(cv_pop, abs=1e-9)

    def test_ddof_0_known(self) -> None:
        arr = np.array([10.0, 20.0, 30.0])
        expected = float(arr.std(ddof=0) / arr.mean())
        assert cv(arr, ddof=0) == pytest.approx(expected)

    def test_constant_array(self) -> None:
        arr = np.array([5.0, 5.0, 5.0])
        assert cv(arr, ddof=1) == pytest.approx(0.0)

    def test_mean_zero_returns_nan(self) -> None:
        arr = np.array([-1.0, 1.0])
        assert math.isnan(cv(arr, ddof=1))

    def test_near_zero_positive_mean_is_finite(self) -> None:

        arr = np.array([0.0, 2e-12])
        result = cv(arr, ddof=1)
        assert math.isfinite(result)
        assert result == pytest.approx(float(arr.std(ddof=1) / arr.mean()))

    def test_single_element_returns_nan(self) -> None:
        arr = np.array([42.0])
        assert math.isnan(cv(arr, ddof=1))

    def test_empty_array_returns_nan(self) -> None:
        arr = np.array([])
        assert math.isnan(cv(arr, ddof=1))

    def test_returns_float(self) -> None:
        result = cv(np.array([1.0, 2.0, 3.0]), ddof=1)
        assert isinstance(result, float)


class TestSingleCVImplementation:
    """Single-value CV implementation details."""

    def test_no_duplicate_cv_def(self) -> None:
        result = subprocess.run(
            [
                "grep",
                "-r",
                "--include=*.py",
                "-l",
                "def cv(",
                "src/",
            ],
            capture_output=True,
            text=True,
            cwd=str(__import__("pathlib").Path(__file__).resolve().parents[3]),
        )
        files = [f for f in result.stdout.strip().splitlines() if f]
        assert len(files) == 1, (
            f"Expected exactly 1 file defining cv(), found {len(files)}: {files}"
        )
        assert files[0].endswith("statistics/aggregates.py")


class TestBootstrapCI:
    """Bootstrap confidence interval computation."""

    def test_bootstrap_ci_known_positive_deltas(self) -> None:
        deltas = np.array([0.1, 0.2, 0.15, 0.12, 0.18])
        result = bootstrap_ci(deltas, n_bootstrap=10_000, ci=0.95, seed=42)
        assert isinstance(result, BootstrapResult)
        assert result.excludes_zero is True
        assert result.ci_lower > 0.0
        assert result.n_seeds == 5
        assert result.n_bootstrap == 10_000

    def test_bootstrap_ci_mixed_sign_deltas(self) -> None:
        deltas = np.array([0.1, -0.05, 0.02, -0.08, 0.03])
        result = bootstrap_ci(deltas, n_bootstrap=10_000, ci=0.95, seed=42)
        assert isinstance(result, BootstrapResult)
        assert result.ci_lower < result.ci_upper

    def test_bootstrap_ci_deterministic_with_seed(self) -> None:
        deltas = np.array([0.1, 0.2, 0.15, 0.12, 0.18])
        r1 = bootstrap_ci(deltas, n_bootstrap=10_000, ci=0.95, seed=123)
        r2 = bootstrap_ci(deltas, n_bootstrap=10_000, ci=0.95, seed=123)
        assert r1.ci_lower == r2.ci_lower
        assert r1.ci_upper == r2.ci_upper
        assert r1.mean_delta == r2.mean_delta

    def test_bootstrap_ci_empty_array_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            bootstrap_ci(np.array([]), n_bootstrap=1000, ci=0.95, seed=42)

    def test_bootstrap_ci_nan_delta_raises(self) -> None:
        deltas = np.array([0.1, float("nan"), 0.15, 0.12, 0.18])
        with pytest.raises(ValueError, match="non-finite"):
            bootstrap_ci(deltas, n_bootstrap=1000, ci=0.95, seed=42)

    def test_bootstrap_ci_inf_delta_raises(self) -> None:
        deltas = np.array([0.1, float("inf"), 0.15])
        with pytest.raises(ValueError, match="non-finite"):
            bootstrap_ci(deltas, n_bootstrap=1000, ci=0.95, seed=42)


class TestBCaCI:
    """Bias-corrected and accelerated confidence intervals."""

    def test_bca_ci_known_positive_deltas(self) -> None:
        deltas = np.array([0.1, 0.2, 0.15, 0.12, 0.18, 0.14, 0.16, 0.13, 0.17, 0.11])
        result = bca_ci(deltas, n_bootstrap=10_000, ci=0.95, seed=42)
        assert isinstance(result, BootstrapResult)
        assert result.method == BootstrapMethod.BCA
        assert result.n_seeds == 10
        assert result.n_bootstrap == 10_000
        assert result.ci_lower < result.mean_delta < result.ci_upper

    def test_bca_ci_positive_excludes_zero(self) -> None:
        deltas = np.array([0.5, 0.6, 0.55, 0.52, 0.58, 0.54, 0.56, 0.53, 0.57, 0.51])
        result = bca_ci(deltas, n_bootstrap=10_000, ci=0.95, seed=42)
        assert result.excludes_zero is True
        assert result.ci_lower > 0.0

    def test_bca_ci_mixed_sign_includes_zero(self) -> None:
        deltas = np.array(
            [0.3, -0.1, 0.05, -0.15, 0.02, -0.08, 0.1, -0.05, 0.01, -0.02]
        )
        result = bca_ci(deltas, n_bootstrap=10_000, ci=0.95, seed=42)
        assert result.ci_lower < result.ci_upper

    def test_bca_ci_deterministic_with_seed(self) -> None:
        deltas = np.array([0.1, 0.2, 0.15, 0.12, 0.18, 0.14, 0.16, 0.13, 0.17, 0.11])
        r1 = bca_ci(deltas, n_bootstrap=10_000, ci=0.95, seed=123)
        r2 = bca_ci(deltas, n_bootstrap=10_000, ci=0.95, seed=123)
        assert r1.ci_lower == r2.ci_lower
        assert r1.ci_upper == r2.ci_upper
        assert r1.mean_delta == r2.mean_delta

    def test_bca_ci_fewer_than_3_seeds_raises(self) -> None:
        deltas = np.array([0.1, 0.2])
        with pytest.raises(ValueError, match="at least 3 seeds"):
            bca_ci(deltas, n_bootstrap=1000, ci=0.95, seed=42)

    def test_bca_ci_empty_array_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            bca_ci(np.array([]), n_bootstrap=1000, ci=0.95, seed=42)

    def test_bca_ci_nan_delta_raises(self) -> None:
        deltas = np.array([0.1, 0.2, float("nan"), 0.12, 0.18, 0.14])
        with pytest.raises(ValueError, match="non-finite"):
            bca_ci(deltas, n_bootstrap=1000, ci=0.95, seed=42)

    def test_bca_ci_constant_deltas(self) -> None:

        deltas = np.array([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
        result = bca_ci(deltas, n_bootstrap=10_000, ci=0.95, seed=42)
        assert result.method == BootstrapMethod.BCA
        assert result.mean_delta == pytest.approx(0.5)

        assert result.ci_lower == pytest.approx(result.ci_upper, abs=1e-6)

    def test_bca_ci_with_ten_deltas(self) -> None:

        deltas = np.array([0.1, 0.2, 0.15, 0.12, 0.18, 0.22, 0.08, 0.14, 0.19, 0.11])
        result = bca_ci(deltas, n_bootstrap=10_000, ci=0.95, seed=42)
        assert result.n_seeds == 10
        assert result.method == BootstrapMethod.BCA
        assert result.ci_lower < result.ci_upper

    def test_bca_vs_percentile_on_skewed_data(self) -> None:

        deltas = np.array([0.01, 0.02, 0.01, 0.03, 0.01, 0.02, 0.01, 0.01, 0.02, 0.9])
        bca_result = bca_ci(deltas, n_bootstrap=10_000, ci=0.95, seed=42)
        pct_result = bootstrap_ci(deltas, n_bootstrap=10_000, ci=0.95, seed=42)

        assert bca_result.method == BootstrapMethod.BCA
        assert pct_result.method == BootstrapMethod.PERCENTILE
        assert bca_result.mean_delta == pytest.approx(pct_result.mean_delta)

        assert bca_result.ci_upper != pytest.approx(pct_result.ci_upper, abs=1e-2)


class TestWilcoxon:
    """Wilcoxon signed-rank test."""

    def test_wilcoxon_identical_arrays(self) -> None:
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = wilcoxon_test(x, y)
        assert result.statistic == pytest.approx(0.0)
        assert result.p_value == pytest.approx(1.0)

    def test_wilcoxon_different_arrays(self) -> None:
        x = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0])
        y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        result = wilcoxon_test(x, y)
        assert isinstance(result, WilcoxonResult)
        assert result.p_value < 0.05
        assert result.n == 8

    def test_wilcoxon_empty_array_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            wilcoxon_test(np.array([]), np.array([]))

    def test_wilcoxon_nan_raises(self) -> None:
        x = np.array([1.0, float("nan"), 3.0])
        y = np.array([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="finite"):
            wilcoxon_test(x, y)

    def test_bonferroni_correction(self) -> None:
        p_values = [0.001, 0.01, 0.04, 0.06, 0.10, 0.50]
        result = bonferroni_correct(p_values, alpha=0.05)
        assert isinstance(result, BonferroniResult)
        assert result.corrected_alpha == pytest.approx(0.05 / 6)
        assert len(result.significant) == 6

        assert result.significant[0] is True

        assert result.significant[1] is False
        assert result.original_p_values == tuple(p_values)


class TestCliffsDelta:
    """Cliff's delta effect size."""

    def test_perfect_separation_x_greater(self) -> None:
        x = np.array([10.0, 20.0, 30.0])
        y = np.array([1.0, 2.0, 3.0])
        result = cliffs_delta(x, y)
        assert isinstance(result, CliffsDeltaResult)
        assert result.delta == pytest.approx(1.0)
        assert result.magnitude == EffectMagnitude.LARGE

    def test_perfect_separation_x_less(self) -> None:
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([10.0, 20.0, 30.0])
        result = cliffs_delta(x, y)
        assert result.delta == pytest.approx(-1.0)
        assert result.magnitude == EffectMagnitude.LARGE

    def test_identical_arrays(self) -> None:
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([1.0, 2.0, 3.0])
        result = cliffs_delta(x, y)
        assert result.delta == pytest.approx(0.0)
        assert result.magnitude == EffectMagnitude.NEGLIGIBLE

    def test_partial_overlap(self) -> None:
        x = np.array([1.0, 3.0, 5.0])
        y = np.array([2.0, 4.0, 6.0])
        result = cliffs_delta(x, y)

        assert result.delta == pytest.approx(-1.0 / 3.0)
        assert result.magnitude == EffectMagnitude.MEDIUM

    def test_different_sizes(self) -> None:
        x = np.array([10.0, 20.0])
        y = np.array([1.0, 2.0, 3.0, 4.0])
        result = cliffs_delta(x, y)

        assert result.delta == pytest.approx(1.0)
        assert result.magnitude == EffectMagnitude.LARGE

    def test_empty_x_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            cliffs_delta(np.array([]), np.array([1.0, 2.0]))

    def test_empty_y_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            cliffs_delta(np.array([1.0, 2.0]), np.array([]))

    def test_nan_in_x_raises(self) -> None:
        x = np.array([1.0, float("nan"), 3.0])
        y = np.array([1.0, 2.0, 3.0])
        with pytest.raises(ValueError, match="finite"):
            cliffs_delta(x, y)

    def test_nan_in_y_raises(self) -> None:
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([1.0, float("nan"), 3.0])
        with pytest.raises(ValueError, match="finite"):
            cliffs_delta(x, y)

    def test_inf_raises(self) -> None:
        x = np.array([1.0, float("inf")])
        y = np.array([1.0, 2.0])
        with pytest.raises(ValueError, match="finite"):
            cliffs_delta(x, y)

    def test_small_magnitude_boundary(self) -> None:

        x = np.array([10.0] * 66 + [1.0] * 34)
        y = np.array([2.0] * 100)
        result = cliffs_delta(x, y)
        assert result.delta == pytest.approx(0.32)
        assert result.magnitude == EffectMagnitude.SMALL

    def test_medium_magnitude(self) -> None:

        x = np.array([10.0] * 70 + [1.0] * 30)
        y = np.array([2.0] * 100)
        result = cliffs_delta(x, y)
        assert result.magnitude == EffectMagnitude.MEDIUM

    def test_negligible_boundary(self) -> None:

        x = np.array([10.0] * 55 + [1.0] * 45)
        y = np.array([2.0] * 100)
        result = cliffs_delta(x, y)
        assert result.magnitude == EffectMagnitude.NEGLIGIBLE


class TestSpearman:
    """Spearman rank correlation."""

    def test_spearman_perfect_positive(self) -> None:
        divergences = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        fpr_values = np.array([0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08])
        result = spearman_correlation(divergences, fpr_values, significance_alpha=0.05)
        assert isinstance(result, SpearmanResult)
        assert result.rho == pytest.approx(1.0, abs=1e-6)
        assert result.mechanism_wording == MechanismWording.EMPIRICAL
        assert result.n == 8

    def test_spearman_random_uncorrelated(self) -> None:
        rng = np.random.default_rng(42)
        divergences = rng.standard_normal(50)
        fpr_values = rng.standard_normal(50)
        result = spearman_correlation(divergences, fpr_values, significance_alpha=0.05)
        assert isinstance(result, SpearmanResult)
        assert result.mechanism_wording == MechanismWording.HYPOTHESIS
