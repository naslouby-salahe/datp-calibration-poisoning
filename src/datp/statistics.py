from __future__ import annotations

import enum
import math
from dataclasses import dataclass
from itertools import product

import numpy as np
from numpy.typing import NDArray

from datp.config import PERMUTATION_MAX_EXACT_SEEDS
from datp.types import (
    BootstrapCount,
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

EXTREME_PERCENTILE = 95


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


def cv(arr: ScoreVector, ddof: SignedCount = 0) -> ScoreValue:
    a = np.asarray(arr, dtype=np.float64)
    if a.size < 2:
        return math.nan
    m = float(a.mean())
    if not m:
        return math.nan
    return float(a.std(ddof=ddof) / m)


def iqr(arr: ScoreVector) -> ScoreValue:
    a = np.asarray(arr, dtype=np.float64)
    if a.size < 2:
        return math.nan
    p25, p75 = np.percentile(a, [25.0, 75.0])
    return float(p75 - p25)


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
        mean=float(arr.mean()),
        std=float(arr.std(ddof=1)) if n >= 2 else math.nan,
        iqr=iqr(arr),
        max_min_gap=float(arr.max() - arr.min()),
        worst_value=float(arr[worst_idx]),
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
        bad_count = int(np.sum(~np.isfinite(values)))
        raise ValueError(
            f"bootstrap_ci: deltas contains {bad_count} non-finite value(s); "
            "resolve undefined CV(FPR) values before computing bootstrap CI"
        )
    return values


def _bootstrap_means(deltas: ScoreVector, n_bootstrap: BootstrapCount, seed: RandomSeed) -> ScoreVector:
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
    ci_lower = float(np.percentile(boot_means, 100 * alpha / 2))
    ci_upper = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))
    mean_delta = float(values.mean())
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
    signs: NDArray[np.float64] = np.array(
        list(product((-1.0, 1.0), repeat=n)), dtype=np.float64
    )
    means = np.abs((signs * arr).mean(axis=1))
    observed = abs(float(arr.mean()))
    extreme: NDArray[np.bool_] = means >= observed - 1e-15
    return float(np.count_nonzero(extreme) / extreme.size)
