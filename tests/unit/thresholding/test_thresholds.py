"""Tests verifying low-level percentile and mean threshold arithmetic functions."""

from __future__ import annotations

import numpy as np
import pytest

from datp.attacks.constants import THRESHOLD_QUANTILE
from datp.thresholding.thresholds import (
    arithmetic_mean_threshold,
    percentile_threshold,
)


class TestPercentileThreshold:
    """Tests verifying percentile-based threshold computations and bound checks."""

    def test_known_uniform(self) -> None:
        """Verify percentile calculations for uniform arrays."""
        errors = np.arange(1.0, 101.0)
        result = percentile_threshold(errors, q=THRESHOLD_QUANTILE)
        expected = float(np.percentile(errors, THRESHOLD_QUANTILE))
        assert result == pytest.approx(expected)

    def test_known_exact(self) -> None:
        """Verify percentile calculations for small exact arrays."""
        errors = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        result = percentile_threshold(errors, q=50)
        expected = float(np.percentile(errors, 50))
        assert result == pytest.approx(expected)

    def test_q_zero(self) -> None:
        """Verify that setting percentile q=0.0 returns the minimum element."""
        errors = np.array([3.0, 1.0, 2.0])
        assert percentile_threshold(errors, q=0.0) == pytest.approx(1.0)

    def test_q_one(self) -> None:
        """Verify that setting percentile q=100.0 returns the maximum element."""
        errors = np.array([3.0, 1.0, 2.0])
        assert percentile_threshold(errors, q=100) == pytest.approx(3.0)

    def test_single_element(self) -> None:
        """Verify that percentile threshold returns the element itself if length is 1."""
        errors = np.array([42.0])
        assert percentile_threshold(errors, q=THRESHOLD_QUANTILE) == pytest.approx(42.0)

    def test_empty_array_raises(self) -> None:
        """Verify ValueError is raised if input errors array is empty."""
        with pytest.raises(ValueError, match="empty"):
            percentile_threshold(np.array([]), q=THRESHOLD_QUANTILE)


class TestArithmeticMeanThreshold:
    """Tests verifying unweighted arithmetic mean calculations for threshold values."""

    def test_unweighted_not_weighted(self) -> None:
        """Verify that mean is unweighted by client sample sizes."""
        tau_values = [0.1, 0.9]
        sample_sizes = [1000, 10]

        unweighted = arithmetic_mean_threshold(tau_values)
        weighted = float(np.average(tau_values, weights=sample_sizes))

        assert unweighted != pytest.approx(weighted, abs=1e-6)
        assert unweighted == pytest.approx(0.5)

    def test_known_values(self) -> None:
        """Verify arithmetic mean threshold on known list of values."""
        assert arithmetic_mean_threshold([2.0, 4.0, 6.0]) == pytest.approx(4.0)

    def test_single_value(self) -> None:
        """Verify arithmetic mean threshold on a single value."""
        assert arithmetic_mean_threshold([7.5]) == pytest.approx(7.5)

    def test_equal_values(self) -> None:
        """Verify arithmetic mean threshold on a list of identical values."""
        assert arithmetic_mean_threshold([3.0, 3.0, 3.0]) == pytest.approx(3.0)

    def test_numpy_input(self) -> None:
        """Verify arithmetic mean threshold accepts numpy arrays."""
        arr = np.array([1.0, 2.0, 3.0])
        assert arithmetic_mean_threshold(arr) == pytest.approx(2.0)

    def test_empty_raises(self) -> None:
        """Verify ValueError is raised if input list is empty."""
        with pytest.raises(ValueError, match="empty"):
            arithmetic_mean_threshold([])
