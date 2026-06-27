"""Bootstrap confidence intervals (percentile and BCa) over paired seed-level deltas."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats as sp_stats

from datp.statistics.constants import BCA_MIN_PAIRED_SEEDS, BootstrapMethod


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    """Bootstrap confidence interval with delta mean and zero-exclusion flag."""

    ci_lower: float
    ci_upper: float
    mean_delta: float
    excludes_zero: bool
    n_seeds: int
    n_bootstrap: int
    method: BootstrapMethod


def _validate_deltas(deltas: np.ndarray, method: BootstrapMethod) -> np.ndarray:
    values = np.asarray(deltas, dtype=np.float64)
    if values.size == 0:
        raise ValueError(f"{method.value}: deltas array is empty")
    if not np.isfinite(values).all():
        bad_count = int(np.sum(~np.isfinite(values)))
        raise ValueError(
            f"{method.value}: deltas contains {bad_count} non-finite value(s); "
            "resolve undefined CV(FPR) values before computing bootstrap CI"
        )
    return values


def _bootstrap_means(deltas: np.ndarray, n_bootstrap: int, seed: int) -> np.ndarray:
    n = len(deltas)
    rng = np.random.default_rng(seed)
    boot_means = np.empty(n_bootstrap, dtype=np.float64)
    for i in range(n_bootstrap):
        sample = rng.choice(deltas, size=n, replace=True)
        boot_means[i] = sample.mean()
    return boot_means


def bootstrap_ci(
    deltas: np.ndarray,
    n_bootstrap: int,
    ci: float,
    seed: int,
) -> BootstrapResult:
    """Percentile bootstrap CI over paired seed-level aggregate deltas."""
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
    deltas: np.ndarray,
    n_bootstrap: int,
    ci: float,
    seed: int,
) -> BootstrapResult:
    """BCa bootstrap CI over paired seed-level aggregate deltas."""
    values = _validate_deltas(deltas, BootstrapMethod.BCA)
    n = values.size
    if n < BCA_MIN_PAIRED_SEEDS:
        raise ValueError(
            f"{BootstrapMethod.BCA.value}: need at least {BCA_MIN_PAIRED_SEEDS} "
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

    def _adjusted_percentile(z_quantile: float) -> float:
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
