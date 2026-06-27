"""Statistical inference: sign tests, bootstrap CI, and Holm-adjusted p-values."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

import numpy as np
from statsmodels.stats.multitest import multipletests

from datp.attacks.constants import (
    BOOTSTRAP_CI,
    BOOTSTRAP_MIN_FINITE,
    BOOTSTRAP_N,
    HOLM_ALPHA,
    SIGN_CONSISTENCY_THRESHOLD,
)
from datp.attacks.enums import AttackerObjective
from datp.statistics.bootstrap import BootstrapResult, bootstrap_ci


@dataclass(frozen=True, slots=True)
class SeedDelta:
    """Per-seed delta-tau for one victim."""

    victim_id: str
    poisoning_seed: int
    delta_tau: float
    feasible: bool


@dataclass(frozen=True, slots=True)
class PairedDeltas:
    """Nested mapping: {victim_id: {poisoning_seed: SeedDelta}}."""

    deltas: dict[str, dict[int, SeedDelta]]


def collect_paired_deltas(
    *,
    victim_id: str,
    seed_deltas: dict[int, float],
    feasible_seeds: set[int] | None = None,
) -> dict[int, SeedDelta]:
    """Wrap per-seed delta-tau values into SeedDelta records for one victim."""
    feasible = feasible_seeds if feasible_seeds is not None else set(seed_deltas)
    return {
        s: SeedDelta(victim_id, s, dt, s in feasible) for s, dt in seed_deltas.items()
    }


def compute_seed_aggregates(
    paired: PairedDeltas, poisoning_seeds: tuple[int, ...]
) -> dict[int, float]:
    """Compute per-seed mean delta-tau across all victims."""
    return {
        s: float(np.mean(f))
        if (
            f := [
                vd[s].delta_tau
                for vd in paired.deltas.values()
                if s in vd and vd[s].feasible
            ]
        )
        else float("nan")
        for s in poisoning_seeds
    }


@dataclass(frozen=True, slots=True)
class SignTestResult:
    """Outcome of the sign-consistency test on seed-aggregate deltas."""

    n_positive: int
    n_negative: int
    n_zero: int
    n_nan: int
    n_total: int
    direction: AttackerObjective
    consistent: bool
    sign_consistency_threshold: int


def sign_test(
    seed_aggregates: dict[int, float], *, direction: AttackerObjective
) -> SignTestResult:
    """Apply the sign-consistency test to seed-aggregate delta-tau values."""
    arr = np.array(list(seed_aggregates.values()), dtype=np.float64)
    finite = arr[~np.isnan(arr)]

    n_pos = int((finite > 0).sum())
    n_neg = int((finite < 0).sum())

    return SignTestResult(
        n_positive=n_pos,
        n_negative=n_neg,
        n_zero=len(finite) - n_pos - n_neg,
        n_nan=len(arr) - len(finite),
        n_total=len(arr),
        direction=direction,
        consistent=(n_pos if direction == AttackerObjective.THRESHOLD_RAISE else n_neg)
        >= SIGN_CONSISTENCY_THRESHOLD,
        sign_consistency_threshold=SIGN_CONSISTENCY_THRESHOLD,
    )


@dataclass(frozen=True, slots=True)
class HolmResult:
    """Holm-Bonferroni adjusted p-values and rejection decisions."""

    raw_p_values: tuple[float, ...]
    holm_p_values: tuple[float, ...]
    reject_h0: tuple[bool, ...]
    alpha: float
    descriptive_only: bool = True


def holm_adjust(raw_p_values: list[float], *, alpha: float = HOLM_ALPHA) -> HolmResult:
    """Apply Holm-Bonferroni correction to a list of raw p-values."""
    rej, pvals, _, _ = multipletests(raw_p_values, alpha=alpha, method="holm")
    adjusted_p_values = cast(Sequence[float], pvals)
    rejections = cast(Sequence[bool], rej)
    return HolmResult(
        raw_p_values=tuple(float(p) for p in raw_p_values),
        holm_p_values=tuple(float(p) for p in adjusted_p_values),
        reject_h0=tuple(bool(r) for r in rejections),
        alpha=alpha,
    )


@dataclass(frozen=True, slots=True)
class BootstrapConfig:
    """Configuration for bootstrap confidence-interval computation."""

    ci: float = BOOTSTRAP_CI
    n_bootstrap: int = BOOTSTRAP_N
    analysis_seed: int = 300


def bootstrap_seed_aggregates(
    seed_aggregates: dict[int, float],
    *,
    poisoning_seeds: tuple[int, ...] | None = None,
    config: BootstrapConfig = BootstrapConfig(),
) -> BootstrapResult:
    """Compute bootstrap confidence intervals over seed-aggregate delta-tau values."""
    vals = (
        [seed_aggregates[s] for s in poisoning_seeds]
        if poisoning_seeds
        else list(seed_aggregates.values())
    )
    arr = np.array(vals, dtype=np.float64)
    finite = arr[~np.isnan(arr)]

    if len(finite) < BOOTSTRAP_MIN_FINITE:
        raise ValueError(
            f"Need at least {BOOTSTRAP_MIN_FINITE} finite seed aggregates for bootstrap CI; "
            f"got {len(finite)} (total seeds: {len(vals)})"
        )

    return bootstrap_ci(
        finite,
        n_bootstrap=config.n_bootstrap,
        ci=config.ci,
        seed=config.analysis_seed,
    )


@dataclass(frozen=True, slots=True)
class HolmConfig:
    """Input for Holm-Bonferroni correction: raw p-values and alpha level."""

    p_values: list[float]
    alpha: float = HOLM_ALPHA


@dataclass(frozen=True, slots=True)
class InferenceResult:
    """Full statistical-inference output: aggregates, bootstrap CI, sign test, and Holm correction."""

    seed_aggregates: dict[int, float]
    bootstrap_ci: BootstrapResult
    sign_test: SignTestResult
    holm: HolmResult | None
    n_feasible_victims: int


@dataclass(frozen=True, slots=True)
class InferenceInput:
    """Input bundle for the compute_inference pipeline."""

    paired: PairedDeltas
    poisoning_seeds: tuple[int, ...]
    direction: AttackerObjective
    bootstrap_config: BootstrapConfig = BootstrapConfig()
    holm_config: HolmConfig | None = None


def compute_inference(inputs: InferenceInput) -> InferenceResult:
    """Compute full inference: seed aggregates, bootstrap CI, sign test, and Holm correction."""
    aggs = compute_seed_aggregates(inputs.paired, inputs.poisoning_seeds)

    return InferenceResult(
        seed_aggregates=aggs,
        bootstrap_ci=bootstrap_seed_aggregates(
            aggs, poisoning_seeds=inputs.poisoning_seeds, config=inputs.bootstrap_config
        ),
        sign_test=sign_test(aggs, direction=inputs.direction),
        holm=holm_adjust(inputs.holm_config.p_values, alpha=inputs.holm_config.alpha)
        if inputs.holm_config
        else None,
        n_feasible_victims=sum(
            any(sd.feasible for sd in vd.values())
            for vd in inputs.paired.deltas.values()
        ),
    )
