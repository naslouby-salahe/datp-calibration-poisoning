from __future__ import annotations

import numpy as np
import pytest

from datp.thresholding.thresholds import (
    arithmetic_mean_threshold,
    conformal_threshold,
    percentile_threshold,
)


class TestPercentileThreshold:
    def test_known_uniform(self) -> None:
        errors = np.arange(1.0, 101.0)  # 1..100
        result = percentile_threshold(errors, q=0.95)
        expected = float(np.percentile(errors, 95))
        assert result == pytest.approx(expected)

    def test_known_exact(self) -> None:
        errors = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        result = percentile_threshold(errors, q=0.5)
        expected = float(np.percentile(errors, 50))
        assert result == pytest.approx(expected)

    def test_q_zero(self) -> None:
        errors = np.array([3.0, 1.0, 2.0])
        assert percentile_threshold(errors, q=0.0) == pytest.approx(1.0)

    def test_q_one(self) -> None:
        errors = np.array([3.0, 1.0, 2.0])
        assert percentile_threshold(errors, q=1.0) == pytest.approx(3.0)

    def test_single_element(self) -> None:
        errors = np.array([42.0])
        assert percentile_threshold(errors, q=0.95) == pytest.approx(42.0)

    def test_empty_array_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            percentile_threshold(np.array([]), q=0.95)

    def test_returns_float(self) -> None:
        result = percentile_threshold(np.array([1.0, 2.0, 3.0]), q=0.95)
        assert isinstance(result, float)


class TestArithmeticMeanThreshold:
    def test_unweighted_not_weighted(self) -> None:
        tau_values = [0.1, 0.9]
        sample_sizes = [1000, 10]

        unweighted = arithmetic_mean_threshold(tau_values)
        weighted = float(np.average(tau_values, weights=sample_sizes))

        assert unweighted != pytest.approx(weighted, abs=1e-6)
        assert unweighted == pytest.approx(0.5)

    def test_known_values(self) -> None:
        assert arithmetic_mean_threshold([2.0, 4.0, 6.0]) == pytest.approx(4.0)

    def test_single_value(self) -> None:
        assert arithmetic_mean_threshold([7.5]) == pytest.approx(7.5)

    def test_equal_values(self) -> None:
        assert arithmetic_mean_threshold([3.0, 3.0, 3.0]) == pytest.approx(3.0)

    def test_numpy_input(self) -> None:
        arr = np.array([1.0, 2.0, 3.0])
        assert arithmetic_mean_threshold(arr) == pytest.approx(2.0)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            arithmetic_mean_threshold([])

    def test_returns_float(self) -> None:
        result = arithmetic_mean_threshold([1.0, 2.0])
        assert isinstance(result, float)


class TestConformalThreshold:
    def test_known_array(self) -> None:
        errors = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        # alpha=0.05: k = ceil(11 * 0.95) = ceil(10.45) = 11 > n=10, fallback to max
        tau = conformal_threshold(errors, 0.05)
        assert tau == pytest.approx(10.0)

    def test_k_not_exceeding_n(self) -> None:
        errors = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        # alpha=0.5: k = ceil(6 * 0.5) = 3 → sorted[2] = 3.0
        tau = conformal_threshold(errors, 0.5)
        assert tau == pytest.approx(3.0)

    def test_alpha_zero(self) -> None:
        errors = np.array([1.0, 2.0, 3.0])
        # alpha=0: k = ceil(4 * 1.0) = 4 > 3, fallback to max
        tau = conformal_threshold(errors, 0.0)
        assert tau == pytest.approx(3.0)

    def test_alpha_near_one_conservative(self) -> None:
        errors = np.array([100.0, 1.0, 50.0])
        # alpha=0.99: k = ceil(4 * 0.01) = 1 → sorted[0] = 1.0
        tau = conformal_threshold(errors, 0.99)
        assert tau == pytest.approx(1.0)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            conformal_threshold(np.array([]), 0.05)

    def test_single_element(self) -> None:
        errors = np.array([42.0])
        # k = ceil(2 * 0.95) = 2 > 1, fallback to max = 42.0
        tau = conformal_threshold(errors, 0.05)
        assert tau == pytest.approx(42.0)

    def test_returns_float(self) -> None:
        result = conformal_threshold(np.array([1.0, 2.0, 3.0, 4.0, 5.0]), 0.2)
        assert isinstance(result, float)

    def test_no_hardcoded_alpha(self) -> None:
        """Conformal alpha must come from config, not be hardcoded."""
        errors = np.arange(1.0, 101.0)  # 100 elements
        tau_05 = conformal_threshold(errors, 0.05)
        tau_10 = conformal_threshold(errors, 0.10)
        # Different alpha values produce different thresholds
        assert tau_05 != pytest.approx(tau_10)
