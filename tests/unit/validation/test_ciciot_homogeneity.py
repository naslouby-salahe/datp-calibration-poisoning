from __future__ import annotations

import numpy as np
import pytest

from datp.config.compose import BASE_CONFIG
from datp.validation.datasets import compute_ciciot_homogeneity
from datp.validation.enums import HomogeneityVerdict


def _uniform(low: float, high: float, n: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).uniform(low, high, n).astype(np.float64)


def test_identical_distributions_produce_homogeneous() -> None:
    rng = np.random.default_rng(0)
    shared = rng.uniform(0.0, 0.5, 200).astype(np.float64)
    cal = {f"c{i}": shared.copy() for i in range(5)}
    result = compute_ciciot_homogeneity(
        cal,
        n_bins=BASE_CONFIG.quality_gates.js_divergence_n_bins,
        threshold=BASE_CONFIG.quality_gates.ciciot_homogeneity_threshold,
    )
    assert result.verdict == HomogeneityVerdict.HOMOGENEOUS
    assert result.js_summary.mean is not None
    assert (
        result.js_summary.mean < BASE_CONFIG.quality_gates.ciciot_homogeneity_threshold
    )


def test_separated_distributions_produce_heterogeneous() -> None:
    low_clients = {f"low_{i}": _uniform(0.0, 0.1, 300, i) for i in range(3)}
    high_clients = {f"high_{i}": _uniform(0.9, 1.0, 300, i + 10) for i in range(3)}
    cal = {**low_clients, **high_clients}
    result = compute_ciciot_homogeneity(
        cal,
        n_bins=BASE_CONFIG.quality_gates.js_divergence_n_bins,
        threshold=BASE_CONFIG.quality_gates.ciciot_homogeneity_threshold,
    )
    assert result.verdict == HomogeneityVerdict.HETEROGENEOUS
    assert result.js_summary.mean is not None
    assert (
        result.js_summary.mean
        >= BASE_CONFIG.quality_gates.ciciot_homogeneity_threshold
    )


def test_fewer_than_two_clients_blocked() -> None:
    cal: dict[str, np.ndarray] = {"c0": np.array([0.1, 0.2, 0.3])}
    result = compute_ciciot_homogeneity(
        cal,
        n_bins=BASE_CONFIG.quality_gates.js_divergence_n_bins,
        threshold=BASE_CONFIG.quality_gates.ciciot_homogeneity_threshold,
    )
    assert result.verdict == HomogeneityVerdict.BLOCKED_PENDING_RUN
    assert result.js_summary.mean is None
    assert result.js_summary.n_compared == 1
    assert result.js_summary.n_pairs == 0


def test_empty_arrays_dropped_safely() -> None:
    cal: dict[str, np.ndarray] = {
        "c_empty": np.array([], dtype=np.float64),
        "c0": _uniform(0.0, 0.5, 200, 1),
    }
    result = compute_ciciot_homogeneity(
        cal,
        n_bins=BASE_CONFIG.quality_gates.js_divergence_n_bins,
        threshold=BASE_CONFIG.quality_gates.ciciot_homogeneity_threshold,
    )
    assert result.verdict == HomogeneityVerdict.BLOCKED_PENDING_RUN
    assert result.js_summary.n_compared == 1


def test_two_identical_clients_js_zero() -> None:
    arr = np.linspace(0.0, 1.0, 200)
    cal = {"c0": arr, "c1": arr.copy()}
    result = compute_ciciot_homogeneity(
        cal,
        n_bins=BASE_CONFIG.quality_gates.js_divergence_n_bins,
        threshold=BASE_CONFIG.quality_gates.ciciot_homogeneity_threshold,
    )
    assert result.verdict == HomogeneityVerdict.HOMOGENEOUS
    assert result.js_summary.mean is not None
    assert result.js_summary.mean == pytest.approx(0.0, abs=1e-6)
    assert result.js_summary.n_pairs == 1


def test_threshold_from_config() -> None:
    threshold = BASE_CONFIG.quality_gates.ciciot_homogeneity_threshold
    assert isinstance(threshold, float)
    assert 0.0 < threshold < 1.0
    arr = np.linspace(0.0, 1.0, 500)
    cal = {"c0": arr, "c1": arr + 1e-5}
    result = compute_ciciot_homogeneity(
        cal,
        n_bins=BASE_CONFIG.quality_gates.js_divergence_n_bins,
        threshold=BASE_CONFIG.quality_gates.ciciot_homogeneity_threshold,
    )
    if result.js_summary.mean is not None:
        expected = (
            HomogeneityVerdict.HOMOGENEOUS
            if result.js_summary.mean < threshold
            else HomogeneityVerdict.HETEROGENEOUS
        )
        assert result.verdict == expected


def test_all_summary_fields_populated() -> None:
    cal = {f"c{i}": _uniform(0.0, 0.5, 150, i) for i in range(4)}
    result = compute_ciciot_homogeneity(
        cal,
        n_bins=BASE_CONFIG.quality_gates.js_divergence_n_bins,
        threshold=BASE_CONFIG.quality_gates.ciciot_homogeneity_threshold,
    )
    assert result.js_summary.n_compared == 4
    assert result.js_summary.n_pairs == 6 # C(4,2)
    assert result.js_summary.mean is not None
    assert result.js_summary.std is not None
    assert result.js_summary.p50 is not None
    assert result.js_summary.p95 is not None
    assert result.js_summary.max is not None
