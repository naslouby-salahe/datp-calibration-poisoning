from __future__ import annotations

import numpy as np
import pytest

from datp.thresholding.thresholds import (
    arithmetic_mean_threshold,
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

