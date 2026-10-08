from __future__ import annotations

import enum
import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy import stats as sp_stats
from sklearn.metrics import average_precision_score, roc_auc_score, silhouette_score

from datp.config import PERMUTATION_MAX_EXACT_SEEDS
from datp.types import (
    BootstrapCount,
    ClassificationScore,
    FeatureMatrix,
    ConfidenceLevel,
    Index,
    IntervalBound,
    JsonValue,
    Probability,
    RandomSeed,
    RecordKey,
    SampleCount,
    ScoreValue,
    ScoreVector,
    SeedCount,
    SignedCount,
    SignedDelta,
)


class BootstrapField(enum.StrEnum):
    SCOPE = "scope"
    COMPARISON = "comparison"
    PER_SEED_DELTAS = "per_seed_deltas"
    MEAN_DELTA = "mean_delta"
    CI_LOWER = "ci_lower"
    CI_UPPER = "ci_upper"
    CI = "ci"
    EXCLUDES_ZERO = "excludes_zero"
    N_BOOTSTRAP = "n_bootstrap"
    N_SEEDS = "n_seeds"


class StatsField(enum.StrEnum):
    PRIMARY_ENDPOINT = "primary_endpoint"
    SECONDARY_NBAIOT = "secondary_nbaiot"
    SECONDARY_NBAIOT_ADDITIONAL = "secondary_nbaiot_additional"
    HETEROGENEITY_CONTEXT_CHECK = "heterogeneity_context_check"
    CONDITION = "condition"
    GLOBAL_CV_FPR_MEAN = "global_cv_fpr_mean"
    PRACTICAL_SIGNIFICANCE_THRESHOLD = "practical_significance_threshold"
    PRACTICAL_SIGNIFICANCE_MET = "practical_significance_met"
    PRIMARY_ENDPOINT_CI_EXCLUDES_ZERO = "primary_endpoint_ci_excludes_zero"
    CONTEXT_RESULT = "context_result"
    NOTE = "note"


def mean_of(values: Sequence[float] | ScoreVector) -> ScoreValue:
    return float(np.mean(values))


def nanmean_of(values: Sequence[float] | ScoreVector) -> ScoreValue:
    return float(np.nanmean(values))


def median_of(values: Sequence[float] | ScoreVector) -> ScoreValue:
    return float(np.median(values))


def std_of(values: Sequence[float] | ScoreVector, ddof: SignedCount = 0) -> ScoreValue:
    return float(np.std(values, ddof=ddof))


def percentile_of(
    values: Sequence[float] | ScoreVector, percentile: ScoreValue
) -> ScoreValue:
    return float(np.percentile(values, percentile))


def min_of(values: Sequence[float] | ScoreVector) -> ScoreValue:
    return float(np.min(values))


def max_of(values: Sequence[float] | ScoreVector) -> ScoreValue:
    return float(np.max(values))


def floats_of(values: Sequence[float] | ScoreVector) -> list[ScoreValue]:
    return [float(value) for value in values]


def ints_of(values: Sequence[int] | ScoreVector) -> list[SampleCount]:
    return [int(value) for value in values]


def skewness_of(values: ScoreVector) -> ScoreValue:
    return float(sp_stats.skew(values))


def silhouette_of(
    features: FeatureMatrix, labels: ScoreVector, random_state: RandomSeed
) -> ClassificationScore:
    return float(silhouette_score(features, labels, random_state=random_state))


def roc_auc_of(labels: ScoreVector, scores: ScoreVector) -> ScoreValue:
    return float(roc_auc_score(labels, scores))


def average_precision_of(labels: ScoreVector, scores: ScoreVector) -> ScoreValue:
    return float(average_precision_score(labels, scores))


def binomial_greater_p_value(
    successes: SampleCount, trials: SampleCount, probability: Probability = 0.5
) -> Probability:
    return float(
        sp_stats.binomtest(
            successes, trials, p=probability, alternative="greater"
        ).pvalue
    )


def count_of(mask: Sequence[bool] | ScoreVector) -> SampleCount:
    return int(np.sum(mask))


def cv(arr: ScoreVector, ddof: SignedCount = 0) -> ScoreValue:
    a = np.asarray(arr, dtype=np.float64)
    if a.size < 2:
        return math.nan
    m = mean_of(a)
    if not m:
        return math.nan
    return std_of(a, ddof=ddof) / m


def iqr(arr: ScoreVector) -> ScoreValue:
    a = np.asarray(arr, dtype=np.float64)
    if a.size < 2:
        return math.nan
    return percentile_of(a, 75.0) - percentile_of(a, 25.0)


@dataclass(frozen=True, slots=True)
class FprFleetStats:
    cv: ScoreValue
    mean: ScoreValue
    std: ScoreValue
    iqr: ScoreValue
    max_min_gap: ScoreValue
    worst_value: ScoreValue
    worst_index: Index | None
    n: SampleCount


def compute_fpr_fleet_stats(fpr_arr: ScoreVector) -> FprFleetStats:
    arr = np.asarray(fpr_arr, dtype=np.float64)
    n = arr.size
    if n == 0:
        return FprFleetStats(
            math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, None, 0
        )

    worst_idx = int(np.argmax(arr))
    return FprFleetStats(
        cv=cv(arr),
        mean=mean_of(arr),
        std=std_of(arr, ddof=1) if n >= 2 else math.nan,
        iqr=iqr(arr),
        max_min_gap=max_of(arr) - min_of(arr),
        worst_value=arr[worst_idx].item(),
        worst_index=worst_idx,
        n=n,
    )


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    ci_lower: IntervalBound
    ci_upper: IntervalBound
    mean_delta: SignedDelta
    excludes_zero: bool
    n_seeds: SeedCount
    n_bootstrap: BootstrapCount


@dataclass(frozen=True, slots=True)
class BootstrapReport:
    result: BootstrapResult
    confidence_level: ConfidenceLevel
    per_seed_deltas: tuple[SignedDelta, ...]

    def to_payload(self) -> dict[RecordKey, JsonValue]:
        return {
            BootstrapField.PER_SEED_DELTAS: list(self.per_seed_deltas),
            BootstrapField.MEAN_DELTA: self.result.mean_delta,
            BootstrapField.CI_LOWER: self.result.ci_lower,
            BootstrapField.CI_UPPER: self.result.ci_upper,
            BootstrapField.CI: self.confidence_level,
            BootstrapField.EXCLUDES_ZERO: self.result.excludes_zero,
            BootstrapField.N_BOOTSTRAP: self.result.n_bootstrap,
            BootstrapField.N_SEEDS: self.result.n_seeds,
        }


def _validate_deltas(deltas: ScoreVector) -> ScoreVector:
    values = np.asarray(deltas, dtype=np.float64)
    if values.size == 0:
        raise ValueError("bootstrap_ci: deltas array is empty")
    if not np.isfinite(values).all():
        bad_count = count_of(~np.isfinite(values))
        raise ValueError(
            f"bootstrap_ci: deltas contains {bad_count} non-finite value(s); "
            "resolve undefined CV(FPR) values before computing bootstrap CI"
        )
    return values


def _bootstrap_means(
    deltas: ScoreVector, n_bootstrap: BootstrapCount, seed: RandomSeed
) -> ScoreVector:
    n = len(deltas)
    rng = np.random.default_rng(seed)
    boot_means = np.empty(n_bootstrap, dtype=np.float64)
    for i in range(n_bootstrap):
        sample = rng.choice(deltas, size=n, replace=True)
        boot_means[i] = sample.mean()
    return boot_means


def bootstrap_ci(
    deltas: ScoreVector,
    n_bootstrap: BootstrapCount,
    ci: IntervalBound,
    seed: RandomSeed,
) -> BootstrapResult:
    values = _validate_deltas(deltas)
    boot_means = _bootstrap_means(values, n_bootstrap, seed)

    alpha = 1.0 - ci
    ci_lower = percentile_of(boot_means, 100 * alpha / 2)
    ci_upper = percentile_of(boot_means, 100 * (1 - alpha / 2))
    mean_delta = mean_of(values)
    excludes_zero = (ci_lower > 0.0) or (ci_upper < 0.0)

    return BootstrapResult(
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        mean_delta=mean_delta,
        excludes_zero=excludes_zero,
        n_seeds=len(values),
        n_bootstrap=n_bootstrap,
    )


def sign_flip_p_value(values: ScoreVector) -> Probability:
    arr = np.asarray(values, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    n = arr.size
    if n == 0:
        return math.nan
    if n > PERMUTATION_MAX_EXACT_SEEDS:
        raise ValueError(
            f"exact sign-flip test supports at most {PERMUTATION_MAX_EXACT_SEEDS} seeds; got {n}"
        )
    observed = abs(mean_of(arr))
    if observed <= 1e-15:
        return 1.0

    threshold = n * (observed - 1e-15)
    split = n // 2
    left_sums = _signed_subset_sums(arr[:split])
    right_sums = np.sort(_signed_subset_sums(arr[split:]))
    low = np.searchsorted(right_sums, -threshold - left_sums, side="right")
    high = np.searchsorted(right_sums, threshold - left_sums, side="left")
    extreme_count = int(np.sum(low + right_sums.size - high))
    return extreme_count / (1 << n)


def _signed_subset_sums(values: ScoreVector) -> ScoreVector:
    n = values.size
    masks = np.arange(1 << n, dtype=np.int64)
    bits = np.arange(n, dtype=np.int64)
    signs = 2 * ((masks[:, None] >> bits) & 1) - 1
    return signs @ values
