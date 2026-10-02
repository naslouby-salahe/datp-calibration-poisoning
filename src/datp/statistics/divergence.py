from __future__ import annotations

from datp.types import (
    BinCount,
    ClientId,
    RecordKey,
    SampleCount,
    ScoreValue,
    ScoreVector,
)


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

    n_compared: SampleCount
    n_pairs: SampleCount
    n_bins: BinCount
    mean: ScoreValue | None
    std: ScoreValue | None
    p50: ScoreValue | None
    p95: ScoreValue | None
    max: ScoreValue | None


def histogram_distribution(arr: ScoreVector, bin_edges: ScoreVector) -> ScoreVector:
    counts, _ = np.histogram(arr, bins=bin_edges)
    smoothed = counts.astype(np.float64) + JS_LAPLACE_SMOOTHING
    return smoothed / smoothed.sum()


def pairwise_js_divergence(probs: list[ScoreVector]) -> ScoreVector:
    if len(probs) < 2:
        return np.array([], dtype=np.float64)
    return np.array(
        [jensenshannon(p, q) ** 2 for p, q in combinations(probs, 2)],
        dtype=np.float64,
    )


def _js_array_to_summary(js: ScoreVector, n_compared: SampleCount, n_bins: BinCount) -> JSSummary:
    if js.size == 0:
        return JSSummary(n_compared, 0, n_bins, None, None, None, None, None)
    return JSSummary(
        n_compared=n_compared,
        n_pairs=js.size,
        n_bins=n_bins,
        mean=float(js.mean()),
        std=float(js.std(ddof=1)) if js.size > 1 else 0.0,
        p50=float(np.percentile(js, 50)),
        p95=float(np.percentile(js, EXTREME_PERCENTILE)),
        max=float(js.max()),
    )


def _get_bin_edges(arrays: list[ScoreVector], n_bins: BinCount) -> ScoreVector:
    pooled = np.concatenate(arrays)
    upper, lower = float(np.percentile(pooled, 99.0)), float(np.min(pooled))
    return np.linspace(lower, max(upper, lower + JS_BIN_EPSILON), n_bins + 1)


def pairwise_js_summary(arrays: list[ScoreVector], *, n_bins: BinCount) -> JSSummary:
    non_empty = [arr for arr in arrays if arr.size > 0]
    if len(non_empty) < 2:
        return _js_array_to_summary(np.array([]), len(non_empty), n_bins)

    bin_edges = _get_bin_edges(non_empty, n_bins)
    probs = [histogram_distribution(arr, bin_edges) for arr in non_empty]
    return _js_array_to_summary(pairwise_js_divergence(probs), len(non_empty), n_bins)


def pairwise_js_from_distributions(distributions: list[ScoreVector]) -> JSSummary:
    n, n_bins = len(distributions), distributions[0].shape[0] if distributions else 0
    return _js_array_to_summary(pairwise_js_divergence(distributions), n, n_bins)


def js_divergence_to_pool(
    client_arrays: dict[ClientId, ScoreVector], *, n_bins: BinCount
) -> dict[RecordKey, ScoreValue]:
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
