"""Tests for the exact sign-flip permutation test."""

from __future__ import annotations

import math

import numpy as np
import pytest

from datp.statistics.permutation import sign_flip_p_value


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
        sign_flip_p_value(np.ones(20))
