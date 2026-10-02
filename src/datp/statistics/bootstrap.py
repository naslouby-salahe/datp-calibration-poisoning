from __future__ import annotations

from datp.types import (
    BootstrapCount,
    ConfidenceLevel,
    IntervalBound,
    JsonValue,
    Quantile,
    RandomSeed,
    RecordKey,
    SeedCount,
    ScoreValue,
    ScoreVector,
    SignedDelta,
)


from dataclasses import dataclass

import numpy as np
from scipy import stats as sp_stats

from datp.statistics.constants import BCA_MIN_PAIRED_SEEDS, BootstrapMethod
from datp.statistics.constants import BootstrapField


@dataclass(frozen=True, slots=True)
class BootstrapResult:

    ci_lower: IntervalBound
    ci_upper: IntervalBound
    mean_delta: SignedDelta
    excludes_zero: bool
    n_seeds: SeedCount
    n_bootstrap: BootstrapCount
    method: BootstrapMethod


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


def _validate_deltas(deltas: ScoreVector, method: BootstrapMethod) -> ScoreVector:
    values = np.asarray(deltas, dtype=np.float64)
    if values.size == 0:
        raise ValueError(f"{method}: deltas array is empty")
    if not np.isfinite(values).all():
        bad_count = int(np.sum(~np.isfinite(values)))
        raise ValueError(
            f"{method}: deltas contains {bad_count} non-finite value(s); "
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
    values = _validate_deltas(deltas, BootstrapMethod.PERCENTILE)
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
        method=BootstrapMethod.PERCENTILE,
    )


def bca_ci(
    deltas: ScoreVector,
    n_bootstrap: BootstrapCount,
    ci: IntervalBound,
    seed: RandomSeed,
) -> BootstrapResult:
    values = _validate_deltas(deltas, BootstrapMethod.BCA)
    n = values.size
    if n < BCA_MIN_PAIRED_SEEDS:
        raise ValueError(
            f"{BootstrapMethod.BCA}: need at least {BCA_MIN_PAIRED_SEEDS} "
            f"seeds for jackknife acceleration, got {n}"
        )

    obs_mean = float(values.mean())
    boot_means = _bootstrap_means(values, n_bootstrap, seed)

    p0 = float(np.mean(boot_means < obs_mean))
    p0 = max(1.0 / (2 * n_bootstrap), min(p0, 1.0 - 1.0 / (2 * n_bootstrap)))
    z0 = float(sp_stats.norm.ppf(p0))

    total = float(values.sum())
    jack_means = np.empty(n, dtype=np.float64)
    for i in range(n):
        jack_means[i] = (total - float(values[i])) / (n - 1)
    jack_mean = float(jack_means.mean())
    centered = jack_mean - jack_means
    numerator = np.sum(centered**3)
    denominator = np.sum(centered**2)
    acceleration = (
        0.0 if denominator < 1e-15 else float(numerator / (6.0 * (denominator**1.5)))
    )

    alpha = 1.0 - ci
    z_alpha_2 = float(sp_stats.norm.ppf(alpha / 2.0))
    z_1_alpha_2 = float(sp_stats.norm.ppf(1.0 - alpha / 2.0))

    def _adjusted_percentile(z_quantile: Quantile) -> ScoreValue:
        numerator = z0 + z_quantile
        denominator = 1.0 - acceleration * numerator
        if denominator <= 0.0:
            return 0.0 if z_quantile < 0.0 else 100.0
        adjusted = z0 + numerator / denominator
        return float(sp_stats.norm.cdf(adjusted)) * 100.0

    ci_lower = float(np.percentile(boot_means, _adjusted_percentile(z_alpha_2)))
    ci_upper = float(np.percentile(boot_means, _adjusted_percentile(z_1_alpha_2)))
    excludes_zero = (ci_lower > 0.0) or (ci_upper < 0.0)

    return BootstrapResult(
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        mean_delta=obs_mean,
        excludes_zero=excludes_zero,
        n_seeds=n,
        n_bootstrap=n_bootstrap,
        method=BootstrapMethod.BCA,
    )
