"""Two-layer statistical inference.

Two-layer design (never 9×5=45 independent replicates):
  Layer 1: per-victim paired seed deltas (Δτ_{v,s} per poisoning seed s and victim v).
  Layer 2: seed-level aggregates δ_s = mean(Δτ_{v,s} for feasible victims).

Statistical inference is on the 5 seed-level aggregates:
  - Bootstrap CI (percentile; BCa available): primary evidence.
  - Sign test: supporting evidence only (≥4/5 = strict majority).
  - Holm-adjusted p-values: descriptive only; not inferential.

Rules:
  - Do NOT treat 9 clients × 5 seeds = 45 data points as 45 independent samples.
  - Bootstrap CI is on the 5 aggregates.
  - Sign test: ≥4/5 sign consistency among eligible feasible victims.
  - Holm: descriptive; never used to claim significance alone.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

import numpy as np
from statsmodels.stats.multitest import multipletests

from datp.statistics.bootstrap import BootstrapResult, bootstrap_ci

# Locked inference parameters.
_N_POISONING_SEEDS: int = 5
_SIGN_CONSISTENCY_THRESHOLD: int = 4  # ≥4/5
_DEFAULT_CI: float = 0.95
_DEFAULT_N_BOOTSTRAP: int = 10_000
_DEFAULT_ANALYSIS_SEED: int = 300


# ---------------------------------------------------------------------------
# Layer 1: per-victim seed deltas
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SeedDelta:
    """One (victim, seed) delta in the two-layer structure."""

    victim_id: str
    poisoning_seed: int
    delta_tau: float
    feasible: bool


@dataclass(frozen=True, slots=True)
class PairedDeltas:
    """All (victim, seed) deltas for one (policy, fraction, source, objective) cell.

    structured as deltas[victim_id][poisoning_seed] = SeedDelta.
    Only feasible (victim, seed) pairs contribute to seed-level aggregates.
    """

    deltas: dict[str, dict[int, SeedDelta]]


def collect_paired_deltas(
    *,
    victim_id: str,
    seed_deltas: dict[int, float],
    feasible_seeds: set[int] | None = None,
) -> dict[int, SeedDelta]:
    """Build the Layer-1 dict for one victim."""
    if feasible_seeds is None:
        feasible_seeds = set(seed_deltas.keys())
    return {
        s: SeedDelta(
            victim_id=victim_id,
            poisoning_seed=s,
            delta_tau=dt,
            feasible=(s in feasible_seeds),
        )
        for s, dt in seed_deltas.items()
    }


# ---------------------------------------------------------------------------
# Layer 2: seed-level aggregates
# ---------------------------------------------------------------------------

def compute_seed_aggregates(
    paired: PairedDeltas,
    poisoning_seeds: tuple[int, ...],
) -> dict[int, float]:
    """Layer 2: aggregate feasible victim deltas per seed.

    For each poisoning seed s:
      δ_s = mean(Δτ_{v,s} for v where paired.deltas[v][s].feasible).

    Returns dict[seed → aggregate delta].
    If no feasible victims for a seed, returns nan for that seed.
    """
    result: dict[int, float] = {}
    for s in poisoning_seeds:
        feasible_deltas = [
            victim_dict[s].delta_tau
            for victim_dict in paired.deltas.values()
            if s in victim_dict and victim_dict[s].feasible
        ]
        result[s] = float(np.mean(feasible_deltas)) if feasible_deltas else float("nan")
    return result


# ---------------------------------------------------------------------------
# Sign test (supporting evidence)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SignTestResult:
    """Sign test on seed-level aggregates.

    Supporting evidence only. ≥4/5 sign consistency in the expected direction
    is the threshold for 'consistent' (not 'significant').
    """

    n_positive: int
    n_negative: int
    n_zero: int
    n_nan: int
    n_total: int
    direction: Literal["raise", "lower"]
    consistent: bool
    sign_consistency_threshold: int


def sign_test(
    seed_aggregates: dict[int, float],
    *,
    direction: Literal["raise", "lower"],
) -> SignTestResult:
    """Supporting sign test on seed-level aggregates.

    'raise' direction: count seeds where δ_s > 0.
    'lower' direction: count seeds where δ_s < 0.
    consistent = True when ≥4/5 sign consistency in expected direction.
    """
    values = list(seed_aggregates.values())
    n_nan = sum(1 for v in values if math.isnan(v))
    finite = [v for v in values if not math.isnan(v)]
    n_positive = sum(1 for v in finite if v > 0)
    n_negative = sum(1 for v in finite if v < 0)
    n_zero = sum(1 for v in finite if math.isclose(v, 0.0, abs_tol=0.0))

    if direction == "raise":
        n_consistent = n_positive
    else:
        n_consistent = n_negative

    return SignTestResult(
        n_positive=n_positive,
        n_negative=n_negative,
        n_zero=n_zero,
        n_nan=n_nan,
        n_total=len(values),
        direction=direction,
        consistent=n_consistent >= _SIGN_CONSISTENCY_THRESHOLD,
        sign_consistency_threshold=_SIGN_CONSISTENCY_THRESHOLD,
    )


# ---------------------------------------------------------------------------
# Holm adjustment (descriptive only)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class HolmResult:
    """Holm-adjusted p-values for seed-level aggregates.

    DESCRIPTIVE ONLY — never used to claim significance.
    p-values here come from a one-sample t-test (H0: mean=0) applied to
    the seed-level aggregates. The Holm correction adjusts for multiple
    comparisons across policies/fractions.

    This is a reporting convenience, not a substitute for the primary
    bootstrap CI.
    """

    raw_p_values: tuple[float, ...]
    holm_p_values: tuple[float, ...]
    reject_h0: tuple[bool, ...]
    alpha: float
    descriptive_only: bool = True


def holm_adjust(
    raw_p_values: list[float],
    *,
    alpha: float = 0.05,
) -> HolmResult:
    """Apply Holm correction to raw p-values. DESCRIPTIVE ONLY.

    Any nan p-values are passed through as nan; only finite values are corrected.
    """
    reject_arr, pvals_corrected, _, _ = multipletests(
        raw_p_values, alpha=alpha, method="holm"
    )
    assert pvals_corrected is not None  # statsmodels type stubs are imprecise
    return HolmResult(
        raw_p_values=tuple(float(p) for p in raw_p_values),
        holm_p_values=tuple(float(p) for p in pvals_corrected),
        reject_h0=tuple(bool(r) for r in reject_arr),
        alpha=alpha,
    )


# ---------------------------------------------------------------------------
# Bootstrap CI (primary evidence)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BootstrapConfig:
    """Bootstrap hyperparameters that are constant across inference calls."""

    ci: float = _DEFAULT_CI
    n_bootstrap: int = _DEFAULT_N_BOOTSTRAP
    analysis_seed: int = _DEFAULT_ANALYSIS_SEED


def bootstrap_seed_aggregates(
    seed_aggregates: dict[int, float],
    *,
    poisoning_seeds: tuple[int, ...] | None = None,
    config: BootstrapConfig = BootstrapConfig(),
) -> BootstrapResult:
    """Percentile bootstrap CI on the 5 seed-level aggregates.

    Only finite aggregates contribute. If fewer than 2 finite seeds remain,
    raises ValueError.

    This is the PRIMARY inferential tool (not the sign test, not Holm).
    """
    if poisoning_seeds is not None:
        values = [seed_aggregates[s] for s in poisoning_seeds]
    else:
        values = list(seed_aggregates.values())

    finite_values = [v for v in values if not math.isnan(v)]
    if len(finite_values) < 2:
        raise ValueError(
            f"Need at least 2 finite seed aggregates for bootstrap CI; "
            f"got {len(finite_values)} (total seeds: {len(values)})"
        )

    arr = np.array(finite_values, dtype=np.float64)
    return bootstrap_ci(
        arr,
        n_bootstrap=config.n_bootstrap,
        ci=config.ci,
        seed=config.analysis_seed,
    )


# ---------------------------------------------------------------------------
# Combined inference result
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class HolmConfig:
    """Holm adjustment parameters.  DESCRIPTIVE ONLY."""
    p_values: list[float]
    alpha: float = 0.05


@dataclass(frozen=True, slots=True)
class InferenceResult:
    """Full two-layer inference result for one (policy, fraction, source, objective)
    cell.

    bootstrap_ci: PRIMARY evidence — CI on 5 seed-level aggregates.
    sign_test: SUPPORTING evidence — ≥4/5 sign consistency.
    holm: DESCRIPTIVE only — never used alone to claim significance.
    seed_aggregates: the 5 aggregates, one per poisoning seed.
    n_feasible_victims: number of eligible feasible victims that contributed.
    """

    seed_aggregates: dict[int, float]
    bootstrap_ci: BootstrapResult
    sign_test: SignTestResult
    holm: HolmResult | None
    n_feasible_victims: int


@dataclass(frozen=True, slots=True)
class InferenceInput:
    """Bundled inputs for full two-layer inference."""
    paired: PairedDeltas
    poisoning_seeds: tuple[int, ...]
    direction: Literal["raise", "lower"]
    bootstrap_config: BootstrapConfig = BootstrapConfig()
    holm_config: HolmConfig | None = None


def compute_inference(inputs: InferenceInput) -> InferenceResult:
    """Compute full two-layer inference."""
    seed_aggregates = compute_seed_aggregates(inputs.paired, inputs.poisoning_seeds)
    boot = bootstrap_seed_aggregates(
        seed_aggregates, poisoning_seeds=inputs.poisoning_seeds, config=inputs.bootstrap_config
    )
    sign = sign_test(seed_aggregates, direction=inputs.direction)

    holm = None
    if inputs.holm_config is not None:
        holm = holm_adjust(inputs.holm_config.p_values, alpha=inputs.holm_config.alpha)

    n_feasible = sum(
        1 for victim_dict in inputs.paired.deltas.values()
        if any(sd.feasible for sd in victim_dict.values())
    )

    return InferenceResult(
        seed_aggregates=seed_aggregates,
        bootstrap_ci=boot,
        sign_test=sign,
        holm=holm,
        n_feasible_victims=n_feasible,
    )
