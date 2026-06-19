from __future__ import annotations

import numpy as np
import pytest

from datp.statistics.divergence import (
    pairwise_js_divergence,
    pairwise_js_from_distributions,
    pairwise_js_summary,
)


class TestPairwiseJsDivergence:
    def test_identical_distributions_zero(self) -> None:
        p = np.array([0.5, 0.5])
        js = pairwise_js_divergence([p, p])
        assert js.shape == (1,)
        assert js[0] == pytest.approx(0.0, abs=1e-9)

    def test_separated_distributions_positive(self) -> None:
        p = np.array([1.0, 0.0])
        q = np.array([0.0, 1.0])
        js = pairwise_js_divergence([p, q])
        assert js[0] > 0.0

    def test_returns_n_pairs(self) -> None:
        probs = [np.array([0.25, 0.75])] * 4
        js = pairwise_js_divergence(probs)
        assert js.shape == (6,)

    def test_symmetry(self) -> None:
        p = np.array([0.8, 0.2])
        q = np.array([0.3, 0.7])
        js_pq = pairwise_js_divergence([p, q])
        js_qp = pairwise_js_divergence([q, p])
        assert js_pq[0] == pytest.approx(js_qp[0])

    def test_bounded_zero_to_log2(self) -> None:
        rng = np.random.default_rng(0)
        for _ in range(20):
            k = rng.integers(2, 8)
            vecs = [rng.dirichlet(np.ones(k)) for _ in range(4)]
            js = pairwise_js_divergence(vecs)
            assert np.all(js >= -1e-12)
            assert np.all(js <= np.log(2) + 1e-9)


class TestPairwiseJsSummary:
    def test_returns_none_stats_for_single_array(self) -> None:
        s = pairwise_js_summary([np.array([1.0, 2.0, 3.0])], n_bins=32)
        assert s.n_compared == 1
        assert s.mean is None
        assert s.std is None
        assert s.p50 is None
        assert s.p95 is None
        assert s.max is None

    def test_empty_list(self) -> None:
        s = pairwise_js_summary([], n_bins=32)
        assert s.n_compared == 0
        assert s.mean is None

    def test_skips_empty_arrays(self) -> None:
        s = pairwise_js_summary([np.array([]), np.array([1.0, 2.0])], n_bins=32)
        assert s.n_compared == 1
        assert s.mean is None

    def test_two_identical_arrays(self) -> None:
        arr = np.random.default_rng(42).exponential(size=200)
        s = pairwise_js_summary([arr, arr], n_bins=32)
        assert s.mean is not None
        assert s.mean == pytest.approx(0.0, abs=1e-6)

    def test_heterogeneous_arrays_positive(self) -> None:
        rng = np.random.default_rng(7)
        a = rng.exponential(scale=0.1, size=300)
        b = rng.exponential(scale=5.0, size=300)
        s = pairwise_js_summary([a, b], n_bins=32)
        assert s.mean is not None
        assert s.mean > 0.01

    def test_summary_fields_complete(self) -> None:
        rng = np.random.default_rng(1)
        arrays = [rng.exponential(scale=float(i + 1), size=100) for i in range(4)]
        s = pairwise_js_summary(arrays, n_bins=32)
        for field in (s.mean, s.std, s.p50, s.p95, s.max):
            assert field is not None

    def test_custom_n_bins(self) -> None:
        rng = np.random.default_rng(3)
        arrays = [rng.exponential(size=200) for _ in range(3)]
        s = pairwise_js_summary(arrays, n_bins=64)
        assert s.n_bins == 64


class TestPairwiseJsFromDistributions:
    def test_identical_vectors_zero(self) -> None:
        d = np.array([0.25, 0.25, 0.25, 0.25])
        s = pairwise_js_from_distributions([d, d])
        assert s.mean == pytest.approx(0.0, abs=1e-9)

    def test_orthogonal_vectors_max_divergence(self) -> None:
        d0 = np.array([1.0, 0.0])
        d1 = np.array([0.0, 1.0])
        s = pairwise_js_from_distributions([d0, d1])
        assert s.mean is not None
        assert s.mean > 0.3

    def test_single_distribution_no_stats(self) -> None:
        d = np.array([0.5, 0.5])
        s = pairwise_js_from_distributions([d])
        assert s.n_compared == 1
        assert s.mean is None

    def test_n_bins_equals_vector_length(self) -> None:
        dists = [np.array([0.3, 0.4, 0.3]), np.array([0.1, 0.8, 0.1])]
        s = pairwise_js_from_distributions(dists)
        assert s.n_bins == 3

    def test_n_pairs_correct(self) -> None:
        dists = [np.array([0.5, 0.5])] * 5
        s = pairwise_js_from_distributions(dists)
        assert s.n_pairs == 10
