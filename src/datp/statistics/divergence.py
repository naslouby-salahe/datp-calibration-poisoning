"""Jensen-Shannon divergence over calibration-score histograms with pooling."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
from scipy.spatial.distance import jensenshannon

from datp.statistics.constants import (
    EXTREME_PERCENTILE,
    JS_BIN_EPSILON,
    JS_LAPLACE_SMOOTHING,
)


@dataclass(frozen=True, slots=True)
class JSSummary:
    """Summary statistics for a set of pairwise Jensen-Shannon divergences."""

    n_compared: int
    n_pairs: int
    n_bins: int
    mean: float | None
    std: float | None
    p50: float | None
    p95: float | None
    max: float | None


def histogram_distribution(arr: np.ndarray, bin_edges: np.ndarray) -> np.ndarray:
    """Return a Laplace-smoothed probability distribution from a histogram of arr."""
    counts, _ = np.histogram(arr, bins=bin_edges)
    smoothed = counts.astype(np.float64) + JS_LAPLACE_SMOOTHING
    return smoothed / smoothed.sum()


def pairwise_js_divergence(probs: list[np.ndarray]) -> np.ndarray:
    """Compute squared Jensen-Shannon divergences for all pairs of distributions."""
    if len(probs) < 2:
        return np.array([], dtype=np.float64)
    return np.array(
        [jensenshannon(p, q) ** 2 for p, q in combinations(probs, 2)],
        dtype=np.float64,
    )


def _js_array_to_summary(js: np.ndarray, n_compared: int, n_bins: int) -> JSSummary:
    if js.size == 0:
        return JSSummary(n_compared, 0, n_bins, None, None, None, None, None)
    return JSSummary(
        n_compared=n_compared,
        n_pairs=int(js.size),
        n_bins=n_bins,
        mean=float(js.mean()),
        std=float(js.std(ddof=1)) if js.size > 1 else 0.0,
        p50=float(np.percentile(js, 50)),
        p95=float(np.percentile(js, EXTREME_PERCENTILE)),
        max=float(js.max()),
    )


def _get_bin_edges(arrays: list[np.ndarray], n_bins: int) -> np.ndarray:
    pooled = np.concatenate(arrays)
    upper, lower = float(np.percentile(pooled, 99.0)), float(np.min(pooled))
    return np.linspace(lower, max(upper, lower + JS_BIN_EPSILON), n_bins + 1)


def pairwise_js_summary(arrays: list[np.ndarray], *, n_bins: int) -> JSSummary:
    """Bin raw score arrays into histograms and return a JS-divergence summary."""
    non_empty = [arr for arr in arrays if arr.size > 0]
    if len(non_empty) < 2:
        return _js_array_to_summary(np.array([]), len(non_empty), n_bins)

    bin_edges = _get_bin_edges(non_empty, n_bins)
    probs = [histogram_distribution(arr, bin_edges) for arr in non_empty]
    return _js_array_to_summary(pairwise_js_divergence(probs), len(non_empty), n_bins)


def pairwise_js_from_distributions(distributions: list[np.ndarray]) -> JSSummary:
    """Compute pairwise JS divergence summary from pre-binned probability distributions."""
    n, n_bins = len(distributions), distributions[0].shape[0] if distributions else 0
    return _js_array_to_summary(pairwise_js_divergence(distributions), n, n_bins)


def js_divergence_to_pool(
    client_arrays: dict[str, np.ndarray], *, n_bins: int
) -> dict[str, float]:
    """Compute per-client JS divergence against a pooled distribution from all arrays."""
    if not client_arrays:
        return {}

    arrs = list(client_arrays.values())
    bin_edges = _get_bin_edges(arrs, n_bins)
    pooled_prob = histogram_distribution(np.concatenate(arrs), bin_edges)

    return {
        cid: float(
            jensenshannon(histogram_distribution(arr, bin_edges), pooled_prob) ** 2
        )
        for cid, arr in client_arrays.items()
    }
