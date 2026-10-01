"""Tests for materiality scale decomposition and bound utilization."""

from __future__ import annotations

import math

import numpy as np
import pytest

from datp.attacks.constants import IQR_FLOOR_FACTOR, MATERIALITY_FACTOR
from datp.attacks.enums import AttackerObjective
from datp.attacks.metrics.delta_tau import materiality_scale, per_client_scale_base
from datp.attacks.metrics.diagnostics import duplicate_rate, tau_bound_utilization


def test_scale_base_prefers_iqr() -> None:
    """A positive IQR is the base when available."""
    cal = np.arange(100, dtype=np.float64)
    assert per_client_scale_base(cal, 10.0) == 10.0


def test_scale_base_falls_back_to_min_spacing() -> None:
    """Zero IQR and zero MAD uses the smallest positive spacing."""
    cal = np.array([1.0, 1.0, 1.0, 1.0, 1.5])
    assert per_client_scale_base(cal, 0.0) == pytest.approx(0.5)


def test_scale_base_nan_when_degenerate() -> None:
    """A constant calibration array has no defined base."""
    assert math.isnan(per_client_scale_base(np.ones(10), 0.0))


def test_materiality_scale_applies_factor_and_floor() -> None:
    """The scale is the larger of the scaled base and the IQR floor."""
    assert materiality_scale(2.0, 1.0, MATERIALITY_FACTOR, IQR_FLOOR_FACTOR) == (
        pytest.approx(0.2)
    )
    assert materiality_scale(0.001, 1.0, 0.1, 0.01) == pytest.approx(0.01)
    assert math.isnan(materiality_scale(math.nan, 1.0, 0.1, 0.01))


def test_duplicate_rate() -> None:
    """Duplicate rate is the share of entries repeating an earlier value."""
    assert duplicate_rate(np.array([1.0, 2.0, 3.0, 4.0])) == 0.0
    assert duplicate_rate(np.array([1.0, 1.0, 1.0, 2.0])) == pytest.approx(0.5)


def test_bound_utilization_raise_and_lower() -> None:
    """Utilization is the shift divided by the reachable range in the attack direction."""
    cal = np.array([0.0, 1.0, 2.0, 3.0, 10.0])
    raised = tau_bound_utilization(
        clean_cal=cal,
        tau_clean=2.0,
        tau_pois=6.0,
        objective=AttackerObjective.THRESHOLD_RAISE,
    )
    lowered = tau_bound_utilization(
        clean_cal=cal,
        tau_clean=2.0,
        tau_pois=1.0,
        objective=AttackerObjective.THRESHOLD_LOWER,
    )
    assert raised == pytest.approx(0.5)
    assert lowered == pytest.approx(0.5)
