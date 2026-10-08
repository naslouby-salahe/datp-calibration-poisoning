from __future__ import annotations

import math

import numpy as np
import pytest

from datp.statistics import BootstrapResult, bootstrap_ci, cv, sign_flip_p_value


def test_all_positive_gives_smallest_p() -> None:
    """Ten identical positive deltas give p = 2 / 2**10."""
    assert sign_flip_p_value(np.ones(10)) == pytest.approx(2 / 1024)


def test_symmetric_deltas_give_p_one() -> None:
    """Deltas symmetric about zero cannot be distinguished from noise."""
    assert sign_flip_p_value(np.array([1.0, -1.0, 2.0, -2.0])) == pytest.approx(1.0)


def test_non_finite_values_are_dropped() -> None:
    """NaN entries are ignored before enumeration."""
    assert sign_flip_p_value(np.array([1.0, math.nan, 1.0])) == pytest.approx(0.5)


def test_empty_is_nan() -> None:
    """No finite values yields NaN."""
    assert math.isnan(sign_flip_p_value(np.array([math.nan])))


def test_too_many_seeds_is_rejected() -> None:
    """Exact enumeration refuses large seed counts."""
    with pytest.raises(ValueError, match="at most"):
        sign_flip_p_value(np.ones(21))


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


class TestBootstrapCI:
    """Bootstrap confidence interval computation."""

    def test_bootstrap_ci_known_positive_deltas(self) -> None:
        deltas = np.array([0.1, 0.2, 0.15, 0.12, 0.18])
        result = bootstrap_ci(deltas, n_bootstrap=2_000, ci=0.95, seed=42)
        assert isinstance(result, BootstrapResult)
        assert result.excludes_zero is True
        assert result.ci_lower > 0.0
        assert result.n_seeds == 5
        assert result.n_bootstrap == 2_000

    def test_bootstrap_ci_mixed_sign_deltas(self) -> None:
        deltas = np.array([0.1, -0.05, 0.02, -0.08, 0.03])
        result = bootstrap_ci(deltas, n_bootstrap=2_000, ci=0.95, seed=42)
        assert isinstance(result, BootstrapResult)
        assert result.ci_lower < result.ci_upper

    def test_bootstrap_ci_deterministic_with_seed(self) -> None:
        deltas = np.array([0.1, 0.2, 0.15, 0.12, 0.18])
        r1 = bootstrap_ci(deltas, n_bootstrap=2_000, ci=0.95, seed=123)
        r2 = bootstrap_ci(deltas, n_bootstrap=2_000, ci=0.95, seed=123)
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
