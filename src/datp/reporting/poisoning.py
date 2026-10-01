"""Poisoning analysis summaries: threshold shifts, excess over random, and claim gates."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import binomtest

from datp.artifacts.names import ArtifactDir
from datp.artifacts.poison_layout import PoisonLayout
from datp.attacks.constants import (
    BOOTSTRAP_CI,
    BOOTSTRAP_MIN_FINITE,
    BOOTSTRAP_N,
    IQR_FLOOR_FACTOR,
    MATERIALITY_FACTOR,
    SENSITIVITY_IQR_FLOOR_GRID,
    SENSITIVITY_MATERIALITY_GRID,
    SENSITIVITY_SIGN_CONSISTENCY_GRID,
    SENSITIVITY_VICTIM_MAJORITY_GRID,
    SIGN_CONSISTENCY_THRESHOLD,
    VICTIM_MAJORITY_THRESHOLD,
)
from datp.attacks.enums import (
    SYNTHESIZED_DRAWS,
    AttackerObjective,
    PoisoningSourceStrategy,
)
from datp.attacks.manifests.bounded_sweep_manifest import (
    BoundedSweepManifest,
    BoundedSweepResultRow,
)
from datp.attacks.manifests.sensitivity_manifest import SensitivityManifest
from datp.attacks.metrics.delta_tau import materiality_scale
from datp.core.enums import ThresholdPolicy
from datp.reporting.constants import METRIC_DEFINITIONS
from datp.statistics.aggregates import iqr
from datp.statistics.bootstrap import bootstrap_ci
from datp.statistics.permutation import sign_flip_p_value


@dataclass(frozen=True, slots=True)
class GateParams:
    """Operational thresholds behind the claim gates."""

    sign_consistency: int
    victim_majority: int
    materiality_factor: float
    iqr_floor_factor: float


DEFAULT_GATE = GateParams(
    sign_consistency=SIGN_CONSISTENCY_THRESHOLD,
    victim_majority=VICTIM_MAJORITY_THRESHOLD,
    materiality_factor=MATERIALITY_FACTOR,
    iqr_floor_factor=IQR_FLOOR_FACTOR,
)


@dataclass(frozen=True, slots=True)
class BuildPoisoningSummariesResult:
    """Paths to all generated poisoning summary JSON and CSV files."""

    paths: list[Path]


@dataclass(frozen=True, slots=True)
class _DownstreamContext:
    """Context bundle for downstream harm analysis: result rows, attacker objective, and source strategy."""

    rows: list[BoundedSweepResultRow]
    objective: AttackerObjective
    source: PoisoningSourceStrategy


def build_poisoning_summaries(base_dir: Path) -> BuildPoisoningSummariesResult:
    """Load the bounded-sweep manifest and generate all poisoning analysis summaries."""
    manifest = load_poisoning_manifest(base_dir)
    analysis_dir = base_dir / ArtifactDir.ANALYSIS
    analysis_dir.mkdir(parents=True, exist_ok=True)

    outputs = [
        ("threshold_shift_summary", _threshold_shift_summary(manifest)),
        ("directional_excess_over_random", _directional_excess_summary(manifest)),
        ("random_control_instability", _random_instability_summary(manifest)),
        ("leave_one_victim_out_sensitivity", _leave_one_victim_out_summary(manifest)),
        ("downstream_harm_raising", _downstream_raising_summary(manifest)),
        ("downstream_harm_lowering", _downstream_lowering_summary(manifest)),
        ("cluster_diagnostics_summary", _cluster_diagnostics_summary(manifest)),
        ("claim_gate_decisions", _claim_gate_decisions(manifest)),
        ("downstream_extended", _downstream_extended_summary(manifest)),
        ("client_level_effects", _client_level_effects(manifest)),
        ("cluster_stability_summary", _cluster_stability_summary(manifest)),
        ("duplicate_and_bound_summary", _duplicate_and_bound_summary(manifest)),
        ("gate_sensitivity", _gate_sensitivity_summary(manifest)),
    ]

    paths = [
        p for stem, recs in outputs for p in _write_records(analysis_dir, stem, recs)
    ]
    paths.append(
        _write_json(analysis_dir / "manifest_summary.json", _manifest_summary(manifest))
    )
    paths.append(
        _write_json(analysis_dir / "metric_definitions.json", METRIC_DEFINITIONS)
    )
    return BuildPoisoningSummariesResult(paths=paths)


def build_sensitivity_summaries(base_dir: Path) -> BuildPoisoningSummariesResult:
    """Load the sensitivity manifest and generate cluster, scale-normalization and distinct-draw summaries."""
    if not (path := PoisonLayout(base_dir=base_dir).sensitivity_manifest()).exists():
        raise FileNotFoundError(f"Missing sensitivity manifest: {path}")
    manifest = SensitivityManifest.model_validate_json(path.read_text())
    analysis_dir = base_dir / ArtifactDir.ANALYSIS
    analysis_dir.mkdir(parents=True, exist_ok=True)
    outputs = [
        ("cluster_stability_sensitivity", _cluster_sensitivity_summary(manifest)),
        ("scale_normalization_summary", _scale_normalization_summary(manifest)),
        ("draw_variant_summary", _draw_variant_summary(manifest)),
        ("trust_boundary_summary", _trust_boundary_summary(manifest)),
    ]
    return BuildPoisoningSummariesResult(
        paths=[
            p for stem, recs in outputs for p in _write_records(analysis_dir, stem, recs)
        ]
    )


def _group_by(
    rows: Iterable[Any], keys: tuple[str, ...]
) -> dict[tuple[Any, ...], list[Any]]:
    """Group rows by the values of the named attributes, rendering enums as their values."""
    grouped = defaultdict(list)
    for r in rows:
        grouped[
            tuple(getattr(v := getattr(r, k), "value", v) for k in keys)
        ].append(r)
    return dict(grouped)


def _cluster_sensitivity_summary(manifest: SensitivityManifest) -> list[dict[str, Any]]:
    """Summarize victim threshold shift and assignment transitions across K, initialization and seeds."""
    records = []
    for (src, obj, frac, k, n_init), rows in sorted(
        _group_by(
            manifest.cluster_stability,
            ("source", "objective", "fraction", "k", "n_init"),
        ).items()
    ):
        by_cell = defaultdict(list)
        for r in rows:
            by_cell[(r.training_seed, r.victim_id)].append(r.victim_delta_tau)
        init_sd = [float(np.std(v, ddof=1)) for v in by_cell.values() if len(v) > 1]
        records.append(
            {
                "source": src,
                "objective": obj,
                "fraction": frac,
                "k": k,
                "n_init": n_init,
                "n_rows": len(rows),
                "mean_victim_delta_tau": _finite_mean(r.victim_delta_tau for r in rows),
                "mean_fixed_victim_delta_tau": _finite_mean(
                    r.fixed_victim_delta_tau for r in rows
                ),
                "mean_init_sd_victim_delta_tau": _finite_mean(init_sd),
                "victim_singleton_poisoned_rate": float(
                    np.mean([r.victim_size_poisoned == 1 for r in rows])
                ),
                "reassignment_rate": float(np.mean([r.n_reassigned > 0 for r in rows])),
                "mean_n_reassigned": float(np.mean([r.n_reassigned for r in rows])),
                "mean_silhouette_clean": _finite_mean(r.silhouette_clean for r in rows),
                "mean_silhouette_poisoned": _finite_mean(
                    r.silhouette_poisoned for r in rows
                ),
            }
        )
    return records


def _scale_normalization_summary(manifest: SensitivityManifest) -> list[dict[str, Any]]:
    """Summarize raw versus normalized GLOBAL_THRESHOLD effects and clean per-client scale dispersion."""
    records = []
    for (src, obj, frac), rows in sorted(
        _group_by(manifest.scale_normalization, ("source", "objective", "fraction")).items()
    ):
        def mean_of(attr: str) -> float:
            return _finite_mean(float(getattr(r, attr)) for r in rows)

        records.append(
            {
                "source": src,
                "objective": obj,
                "fraction": frac,
                "n_rows": len(rows),
                "mean_tau_local_cv_clean": mean_of("tau_local_cv_clean"),
                "mean_tau_local_max_min_ratio_clean": mean_of(
                    "tau_local_max_min_ratio_clean"
                ),
                "mean_score_scale_cv_clean": mean_of("score_scale_cv_clean"),
                "raw_global_victim_delta_tau": mean_of("raw_global_victim_delta_tau"),
                "normalized_global_victim_delta_tau": mean_of(
                    "normalized_global_victim_delta_tau"
                ),
                "raw_global_victim_delta_fpr": mean_of("raw_global_victim_delta_fpr"),
                "normalized_global_victim_delta_fpr": mean_of(
                    "normalized_global_victim_delta_fpr"
                ),
                "raw_global_cv_fpr_clean": mean_of("raw_global_cv_fpr_clean"),
                "normalized_global_cv_fpr_clean": mean_of(
                    "normalized_global_cv_fpr_clean"
                ),
                "raw_global_cv_fpr_poisoned": mean_of("raw_global_cv_fpr_poisoned"),
                "normalized_global_cv_fpr_poisoned": mean_of(
                    "normalized_global_cv_fpr_poisoned"
                ),
            }
        )
    return records


def _draw_variant_summary(manifest: SensitivityManifest) -> list[dict[str, Any]]:
    """Summarize threshold shift and duplicate rates for each alternative draw mode against with-replacement."""
    records = []
    for (pol, src, obj, frac, draw), rows in sorted(
        _group_by(
            manifest.draw_variants,
            ("policy", "source", "objective", "fraction", "draw"),
        ).items()
    ):
        base = _finite_mean(r.delta_tau_with_replacement for r in rows)
        variant = _finite_mean(r.delta_tau_variant for r in rows)
        records.append(
            {
                "policy": pol,
                "source": src,
                "objective": obj,
                "fraction": frac,
                "draw": draw,
                "synthesized_values": draw in {d.value for d in SYNTHESIZED_DRAWS},
                "n_rows": len(rows),
                "mean_requested_n_replaced": float(
                    np.mean([r.requested_n_replaced for r in rows])
                ),
                "mean_effective_n_replaced": float(
                    np.mean([r.effective_n_replaced for r in rows])
                ),
                "mean_pool_size": float(np.mean([r.pool_size for r in rows])),
                "full_budget_feasible_rate": float(
                    np.mean(
                        [r.effective_n_replaced == r.requested_n_replaced for r in rows]
                    )
                ),
                "mean_delta_tau_with_replacement": base,
                "mean_delta_tau_variant": variant,
                "variant_to_baseline_ratio": variant / base
                if math.isfinite(base) and base != 0.0
                else math.nan,
                "mean_duplicate_rate_with_replacement": _finite_mean(
                    r.duplicate_rate_with_replacement for r in rows
                ),
                "mean_duplicate_rate_variant": _finite_mean(
                    r.duplicate_rate_variant for r in rows
                ),
            }
        )
    return records


def _trust_boundary_summary(manifest: SensitivityManifest) -> list[dict[str, Any]]:
    """Summarize the buffer attack against trimmed-calibration defenses and the direct-overwrite reference."""
    records = []
    for (pol, src, obj, frac), rows in sorted(
        _group_by(
            manifest.trust_boundary, ("policy", "source", "objective", "fraction")
        ).items()
    ):
        def mean_of(attr: str) -> float:
            return _finite_mean(float(getattr(r, attr)) for r in rows)

        undefended = mean_of("delta_tau_undefended")
        records.append(
            {
                "policy": pol,
                "source": src,
                "objective": obj,
                "fraction": frac,
                "n_rows": len(rows),
                "mean_delta_tau_undefended": undefended,
                "mean_delta_tau_trim_primary": mean_of("delta_tau_trim_primary"),
                "mean_delta_tau_trim_appendix": mean_of("delta_tau_trim_appendix"),
                "mean_residual_vs_clean_trim_primary": mean_of(
                    "residual_vs_clean_trim_primary"
                ),
                "mean_residual_vs_clean_trim_appendix": mean_of(
                    "residual_vs_clean_trim_appendix"
                ),
                "mean_overwrite_reference_shift": mean_of("overwrite_reference_shift"),
                "mean_buffer_to_overwrite_ratio": mean_of("buffer_to_overwrite_ratio"),
                "trim_primary_reduction": 1.0
                - mean_of("delta_tau_trim_primary") / undefended
                if math.isfinite(undefended) and undefended != 0.0
                else math.nan,
            }
        )
    return records


def load_poisoning_manifest(base_dir: Path) -> BoundedSweepManifest:
    """Load and parse the bounded-sweep manifest from the N-BaIoT main poison layout path."""
    if not (path := PoisonLayout(base_dir=base_dir).nbaiot_main_manifest()).exists():
        raise FileNotFoundError(f"Missing bounded 10-seed manifest: {path}")
    return BoundedSweepManifest.model_validate_json(path.read_text())


def _write_json(path: Path, payload: Any) -> Path:
    """Serialize payload as NaN-safe JSON and write it to path, returning the path."""
    path.write_text(json.dumps(_json_safe(payload), indent=2, allow_nan=False))
    return path


def _json_safe(payload: Any) -> Any:
    """Recursively replace non-finite floats with None for safe JSON serialization."""
    if isinstance(payload, float):
        return payload if math.isfinite(payload) else None
    if isinstance(payload, dict):
        return {k: _json_safe(v) for k, v in payload.items()}
    if isinstance(payload, (list, tuple)):
        return [_json_safe(v) for v in payload]
    return payload


def _write_records(
    output_dir: Path, stem: str, records: list[dict[str, Any]]
) -> list[Path]:
    """Write a list of record dicts to both JSON and CSV files under output_dir/{stem}.*."""
    json_path = _write_json(output_dir / f"{stem}.json", records)
    csv_path = output_dir / f"{stem}.csv"
    if records:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=sorted({k for r in records for k in r})
            )
            writer.writeheader()
            writer.writerows(records)
    return [json_path, csv_path]


def _group_rows(
    rows: Iterable[BoundedSweepResultRow],
) -> dict[tuple[str, str, str, float], list[BoundedSweepResultRow]]:
    """Group manifest result rows by (policy, objective, source, fraction) key."""
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r.policy.value, r.objective.value, r.source.value, r.fraction)].append(
            r
        )
    return dict(grouped)


def _seed_values(
    rows: Iterable[BoundedSweepResultRow], value: str, transform: float = 1.0
) -> dict[int, float]:
    """Aggregate finite per-row attribute values by training seed, applying an optional sign transform."""
    by_seed = defaultdict(list)
    for r in rows:
        if math.isfinite(v := float(getattr(r, value))):
            by_seed[r.training_seed].append(transform * v)
    return {s: float(np.mean(vals)) for s, vals in sorted(by_seed.items()) if vals}


def _support_count(seed_values: dict[int, float]) -> int:
    """Count seeds with a strictly positive finite value."""
    return sum(1 for v in seed_values.values() if math.isfinite(v) and v > 0.0)


def _finite_mean(values: Iterable[float]) -> float:
    """Return the mean of finite values, or NaN if none are finite."""
    return (
        float(np.mean(f))
        if (f := [v for v in values if math.isfinite(v)])
        else math.nan
    )


def _median(values: Iterable[float]) -> float:
    """Return the median of finite values, or NaN if none are finite."""
    return (
        float(np.median(f))
        if (f := [v for v in values if math.isfinite(v)])
        else math.nan
    )


def _bootstrap_payload(
    seed_values: dict[int, float], analysis_seed: int
) -> dict[str, Any]:
    """Compute bootstrap CI for seed-aggregated values and return a stats dict, or NaN placeholders if too few seeds."""
    return dict(
        _cached_bootstrap(
            tuple(v for v in seed_values.values() if math.isfinite(v)), analysis_seed
        )
    )


@lru_cache(maxsize=None)
def _cached_bootstrap(
    finite: tuple[float, ...], analysis_seed: int
) -> tuple[tuple[str, float | int], ...]:
    """Cache bootstrap payloads keyed on the finite seed values and analysis seed."""
    if len(finite) < BOOTSTRAP_MIN_FINITE:
        return (
            ("bootstrap_ci_lower", math.nan),
            ("bootstrap_ci_upper", math.nan),
            ("bootstrap_mean", math.nan),
            ("bootstrap_n_seed_aggregates", len(finite)),
        )
    res = bootstrap_ci(
        np.array(finite, dtype=np.float64),
        n_bootstrap=BOOTSTRAP_N,
        ci=BOOTSTRAP_CI,
        seed=analysis_seed,
    )
    return (
        ("bootstrap_ci_lower", res.ci_lower),
        ("bootstrap_ci_upper", res.ci_upper),
        ("bootstrap_mean", res.mean_delta),
        ("bootstrap_n_seed_aggregates", res.n_seeds),
    )


def _exact_support(seed_support: int, n_seeds: int) -> dict[str, Any]:
    """Return exact support count, total seeds, and one-sided binomial p-value dict."""
    return {
        "exact_support_count": seed_support,
        "exact_support_n": n_seeds,
        "exact_binomial_p": float(
            binomtest(seed_support, n_seeds, p=0.5, alternative="greater").pvalue
        )
        if n_seeds
        else math.nan,
    }


def _is_significant(r: BoundedSweepResultRow, gate: GateParams) -> bool:
    """Return the victim materiality flag, recomputed when gate parameters differ from the defaults."""
    if (
        gate.materiality_factor == MATERIALITY_FACTOR
        and gate.iqr_floor_factor == IQR_FLOOR_FACTOR
    ):
        return r.is_victim_significant
    scale = materiality_scale(
        r.victim_delta_tau_scale_base,
        r.iqr_median_clean,
        gate.materiality_factor,
        gate.iqr_floor_factor,
    )
    return not math.isnan(scale) and abs(r.delta_tau) >= scale


def _victim_majority_count(
    rows: list[BoundedSweepResultRow],
    absolute: bool,
    gate: GateParams = DEFAULT_GATE,
) -> int:
    """Count seeds where at least gate.victim_majority victims show a significant shift in the expected direction."""
    by_seed = defaultdict(list)
    for r in rows:
        by_seed[r.training_seed].append(r)
    return sum(
        1
        for s_rows in by_seed.values()
        if sum(
            1
            for r in s_rows
            if _is_significant(r, gate)
            and (
                absolute
                or (1 if r.objective == AttackerObjective.THRESHOLD_RAISE else -1)
                * r.delta_tau
                > 0.0
            )
        )
        >= gate.victim_majority
    )


def _threshold_shift_summary(
    manifest: BoundedSweepManifest, gate: GateParams = DEFAULT_GATE
) -> list[dict[str, Any]]:
    """Summarize threshold-shift statistics for every (policy, objective, source, fraction) group."""
    records = []
    for (pol, obj, src, frac), rows in sorted(_group_rows(manifest.results).items()):
        sign = 1.0 if obj == AttackerObjective.THRESHOLD_RAISE else -1.0
        s_vals = _seed_values(rows, "delta_tau", sign)
        s_count = _support_count(s_vals)
        records.append(
            {
                "dataset": manifest.dataset.value,
                "policy": pol,
                "objective": obj,
                "source": src,
                "fraction": frac,
                "claim_bearing": frac > 0.0
                and src != PoisoningSourceStrategy.RANDOM_BENIGN.value,
                "mean_delta_tau": float(np.mean([r.delta_tau for r in rows])),
                "median_delta_tau": _median(r.delta_tau for r in rows),
                "iqr_delta_tau": iqr(np.array([r.delta_tau for r in rows])),
                "material_signed_rate": (
                    len([r for r in rows if _is_significant(r, gate) and sign * r.delta_tau > 0.0])
                    / len(rows)
                    if rows
                    else math.nan
                ),
                "seed_sign_count": s_count,
                "victim_majority_count": _victim_majority_count(rows, False, gate),
                **_bootstrap_payload(s_vals, manifest.analysis_seeds[0]),
                **_exact_support(s_count, len(s_vals)),
            }
        )
    return records


def _excess_by_seed(
    att_rows: list[Any], random_rows: dict[Any, Any], obj: AttackerObjective
) -> dict[int, float]:
    """Compute per-seed directional excess of the targeted strategy over the random baseline."""
    bucket: defaultdict[int, list[float]] = defaultdict(list)
    for att in att_rows:
        rnd = random_rows.get(
            (
                att.policy.value,
                att.fraction,
                att.victim_id,
                att.training_seed,
                att.poisoning_seed,
            )
        )
        if rnd:
            delta = (
                att.delta_tau - rnd.delta_tau
                if obj == AttackerObjective.THRESHOLD_RAISE
                else rnd.delta_tau - att.delta_tau
            )
            bucket[att.training_seed].append(delta)
    return {s: float(np.mean(v)) for s, v in sorted(bucket.items())}


def _directional_excess_summary(
    manifest: BoundedSweepManifest, gate: GateParams = DEFAULT_GATE
) -> list[dict[str, Any]]:
    """Summarize directional excess of targeted strategies over the random baseline for each group."""
    records = []
    for obj, src_tgt in [
        (AttackerObjective.THRESHOLD_RAISE, PoisoningSourceStrategy.HIGH_SCORE_BENIGN),
        (AttackerObjective.THRESHOLD_LOWER, PoisoningSourceStrategy.LOW_SCORE_BENIGN),
    ]:
        random_rows = {
            (
                r.policy.value,
                r.fraction,
                r.victim_id,
                r.training_seed,
                r.poisoning_seed,
            ): r
            for r in manifest.results
            if r.objective == obj and r.source == PoisoningSourceStrategy.RANDOM_BENIGN
        }
        for (pol, _, src, frac), att_rows in sorted(
            _group_rows(
                r
                for r in manifest.results
                if r.objective == obj and r.source == src_tgt and r.fraction > 0.0
            ).items()
        ):
            s_vals = _excess_by_seed(att_rows, random_rows, obj)
            s_count = _support_count(s_vals)
            records.append(
                {
                    "dataset": manifest.dataset.value,
                    "policy": pol,
                    "objective": obj.value,
                    "source": src,
                    "fraction": frac,
                    "control_source": PoisoningSourceStrategy.RANDOM_BENIGN.value,
                    "control_objective": obj.value,
                    "directional_excess_seed_support": s_count,
                    "median_directional_excess": _median(s_vals.values()),
                    "mean_directional_excess": _finite_mean(s_vals.values()),
                    "per_seed_directional_excess": {
                        str(k): v for k, v in s_vals.items()
                    },
                    "permutation_p": sign_flip_p_value(
                        np.array(list(s_vals.values()), dtype=np.float64)
                    ),
                    "gate2_pass": s_count >= gate.sign_consistency
                    and _median(s_vals.values()) > 0.0,
                    **_bootstrap_payload(s_vals, manifest.analysis_seeds[0]),
                    **_exact_support(s_count, len(s_vals)),
                }
            )
    return records


def _random_instability_summary(
    manifest: BoundedSweepManifest, gate: GateParams = DEFAULT_GATE
) -> list[dict[str, Any]]:
    """Summarize random-control instability count and flag for each RANDOM_BENIGN group."""
    return [
        {
            "dataset": manifest.dataset.value,
            "policy": pol,
            "objective": obj,
            "source": src,
            "fraction": frac,
            "random_control_instability_count": (
                cnt := _victim_majority_count(rows, True, gate)
            ),
            "random_control_unstable": cnt >= gate.sign_consistency,
        }
        for (pol, obj, src, frac), rows in sorted(_group_rows(manifest.results).items())
        if src == PoisoningSourceStrategy.RANDOM_BENIGN.value
    ]


def _leave_one_victim_out_summary(
    manifest: BoundedSweepManifest, gate: GateParams = DEFAULT_GATE
) -> list[dict[str, Any]]:
    """Summarize leave-one-victim-out sensitivity of the threshold-shift signal per group."""
    records = []
    main_sources = {
        PoisoningSourceStrategy.HIGH_SCORE_BENIGN.value,
        PoisoningSourceStrategy.LOW_SCORE_BENIGN.value,
    }
    for (pol, obj, src, frac), rows in sorted(_group_rows(manifest.results).items()):
        if src not in main_sources or math.isclose(frac, 0.0, abs_tol=1e-12):
            continue
        victims = sorted({r.victim_id for r in rows})
        sign = 1.0 if obj == AttackerObjective.THRESHOLD_RAISE else -1.0
        excl_means = []
        stable = 0
        for excl in victims:
            s_vals = _seed_values(
                [r for r in rows if r.victim_id != excl], "delta_tau", transform=sign
            )
            med = _median(s_vals.values())
            excl_means.append(med)
            if _support_count(s_vals) >= gate.sign_consistency and med > 0.0:
                stable += 1
        records.append(
            {
                "dataset": manifest.dataset.value,
                "policy": pol,
                "objective": obj,
                "source": src,
                "fraction": frac,
                "leave_one_victim_out_min": min(excl_means),
                "leave_one_victim_out_median": _median(excl_means),
                "leave_one_victim_out_max": max(excl_means),
                "sign_stable_exclusions": stable,
                "n_exclusions": len(victims),
            }
        )
    return records


def _metric_value(r: BoundedSweepResultRow, metric: str) -> float:
    """Return a row metric, resolving derived absolute error-count deltas."""
    match metric:
        case "victim_delta_fp":
            return float(r.victim_fp_poisoned - r.victim_fp_clean)
        case "victim_delta_fn":
            return float(r.victim_fn_poisoned - r.victim_fn_clean)
        case _:
            return float(getattr(r, metric))


def _downstream_metric_record(
    analysis_seed: int,
    ctx: _DownstreamContext,
    metric: str,
    transform: float,
    agg: str,
    gate: GateParams = DEFAULT_GATE,
) -> dict[str, Any]:
    """Build a single downstream record for one metric, sign transform, and seed aggregation method."""
    by_seed = defaultdict(list)
    for r in ctx.rows:
        if math.isfinite(v := transform * _metric_value(r, metric)):
            by_seed[r.training_seed].append(v)
    s_vals = {
        s: max(v) if agg == "max" else float(np.mean(v)) for s, v in by_seed.items()
    }
    arr = np.array(list(s_vals.values()), dtype=np.float64)
    return {
        "objective": ctx.objective.value,
        "source": ctx.source.value,
        "metric": metric,
        "expected_sign_seed_support": (s_cnt := _support_count(s_vals)),
        "n_seeds_negative": int(np.sum(arr < 0.0)),
        "median_harm": _median(s_vals.values()),
        "mean_effect": _finite_mean(s_vals.values()),
        "per_seed_values": {str(k): v for k, v in sorted(s_vals.items())},
        "permutation_p": sign_flip_p_value(arr),
        "gate3_metric_pass": s_cnt >= gate.sign_consistency
        and _median(s_vals.values()) > 0.0,
        **_bootstrap_payload(s_vals, analysis_seed),
        **_exact_support(s_cnt, len(s_vals)),
    }


def _downstream_raising_summary(
    manifest: BoundedSweepManifest, gate: GateParams = DEFAULT_GATE
) -> list[dict[str, Any]]:
    """Summarize downstream TPR/BA/macro-F1 harm for HIGH_SCORE_BENIGN THRESHOLD_RAISE groups."""
    metrics = [
        ("victim_delta_tpr", -1.0, "mean"),
        ("victim_delta_ba", -1.0, "mean"),
        ("victim_delta_macro_f1", -1.0, "mean"),
        ("victim_delta_tpr", -1.0, "max"),
    ]
    return [
        {
            **_downstream_metric_record(
                manifest.analysis_seeds[0],
                _DownstreamContext(
                    rows,
                    AttackerObjective.THRESHOLD_RAISE,
                    PoisoningSourceStrategy(src),
                ),
                m,
                t,
                a,
                gate,
            ),
            "dataset": manifest.dataset.value,
            "policy": pol,
            "fraction": frac,
            "summary_metric": "worst_victim_drop" if a == "max" else m,
        }
        for (pol, _, src, frac), rows in sorted(
            _group_rows(
                r
                for r in manifest.results
                if r.objective == AttackerObjective.THRESHOLD_RAISE
                and r.source == PoisoningSourceStrategy.HIGH_SCORE_BENIGN
                and r.fraction > 0.0
            ).items()
        )
        for m, t, a in metrics
    ]


def _downstream_lowering_summary(
    manifest: BoundedSweepManifest, gate: GateParams = DEFAULT_GATE
) -> list[dict[str, Any]]:
    """Summarize downstream FPR-dispersion harm metrics for LOW_SCORE_BENIGN THRESHOLD_LOWER groups."""
    metrics = [
        "delta_mean_fpr",
        "delta_cv_fpr",
        "delta_iqr_fpr",
        "delta_max_min_fpr",
        "delta_worst_client_fpr",
    ]
    return [
        {
            **_downstream_metric_record(
                manifest.analysis_seeds[0],
                _DownstreamContext(
                    rows,
                    AttackerObjective.THRESHOLD_LOWER,
                    PoisoningSourceStrategy(src),
                ),
                m,
                1.0,
                "mean",
                gate,
            ),
            "dataset": manifest.dataset.value,
            "policy": pol,
            "fraction": frac,
            "summary_metric": m,
        }
        for (pol, _, src, frac), rows in sorted(
            _group_rows(
                r
                for r in manifest.results
                if r.objective == AttackerObjective.THRESHOLD_LOWER
                and r.source == PoisoningSourceStrategy.LOW_SCORE_BENIGN
                and r.fraction > 0.0
            ).items()
        )
        for m in metrics
    ]


def _cluster_diagnostics_summary(
    manifest: BoundedSweepManifest,
) -> list[dict[str, Any]]:
    """Summarize CLUSTER_THRESHOLD-specific diagnostics: churn, spillover, victim/non-victim effects, normalization gap."""
    return [
        {
            "dataset": manifest.dataset.value,
            "policy": pol,
            "objective": obj,
            "source": src,
            "fraction": frac,
            "cluster_churn": float(
                np.nanmean([r.cluster_delta_tau_churn for r in rows])
            ),
            "spillover_count": float(np.nanmean([r.n_spillover for r in rows])),
            "victim_effect": float(np.nanmean([r.cluster_victim_effect for r in rows])),
            "non_victim_effect": float(
                np.nanmean([r.cluster_non_victim_effect for r in rows])
            ),
            "frozen_scaler_effect": float(
                np.nanmean([r.cluster_delta_tau_frozen_scaler for r in rows])
            ),
            "refit_minus_frozen_scaler": float(
                np.nanmean([r.cluster_delta_tau_normalization_gap for r in rows])
            ),
        }
        for (pol, obj, src, frac), rows in sorted(
            _group_rows(
                r
                for r in manifest.results
                if r.policy == ThresholdPolicy.CLUSTER_THRESHOLD
            ).items()
        )
    ]


def _claim_gate_decisions(
    manifest: BoundedSweepManifest, gate: GateParams = DEFAULT_GATE
) -> list[dict[str, Any]]:
    """Apply the three-gate claim logic and classify each claim-bearing group into a claim class."""
    excess = {
        (r["policy"], r["objective"], r["source"], r["fraction"]): r
        for r in _directional_excess_summary(manifest, gate)
    }
    r_instab = {
        (r["policy"], r["objective"], r["fraction"]): r["random_control_unstable"]
        for r in _random_instability_summary(manifest, gate)
    }
    d_pass: defaultdict[tuple[str, str, str, float], bool] = defaultdict(bool)
    for r in _downstream_raising_summary(manifest, gate) + _downstream_lowering_summary(
        manifest, gate
    ):
        d_pass[(r["policy"], r["objective"], r["source"], r["fraction"])] |= bool(
            r["gate3_metric_pass"]
        )

    records = []
    for t_rec in _threshold_shift_summary(manifest, gate):
        if not t_rec["claim_bearing"]:
            continue
        pol, obj, src, frac = t_rec["policy"], t_rec["objective"], t_rec["source"], t_rec["fraction"]
        key = (pol, obj, src, frac)
        g1 = (
            t_rec["seed_sign_count"] >= gate.sign_consistency
            and t_rec["victim_majority_count"] >= gate.sign_consistency
        )
        g2, g3 = bool(excess.get(key, {}).get("gate2_pass", False)), d_pass[key]
        r_unstable = bool(r_instab.get((pol, obj, frac), False))
        if r_unstable or not g2:
            c_class = "calibration_instability"
        elif g1 and g3:
            c_class = "full_vulnerability"
        elif g1:
            c_class = "mechanism_only"
        else:
            c_class = "null_or_conditional"
        records.append(
            {
                "dataset": manifest.dataset.value,
                "policy": pol,
                "objective": obj,
                "source": src,
                "fraction": frac,
                "gate1_pass": g1,
                "gate2_pass": g2,
                "gate3_pass": g3,
                "random_control_unstable": r_unstable,
                "claim_class": c_class,
            }
        )
    return records


_EXTENDED_METRICS: tuple[str, ...] = (
    "victim_delta_tpr",
    "victim_delta_fpr",
    "victim_delta_fn",
    "victim_delta_fp",
    "victim_delta_ba",
    "victim_delta_macro_f1",
    "nonvictim_mean_delta_tpr",
    "nonvictim_worst_delta_tpr",
    "nonvictim_mean_delta_fpr",
    "nonvictim_worst_delta_fpr",
    "nonvictim_mean_delta_ba",
    "nonvictim_mean_delta_macro_f1",
    "nonvictim_delta_fn_total",
    "nonvictim_delta_fp_total",
    "delta_mean_fpr",
    "delta_cv_fpr",
)

_FIXED_CLUSTER_METRICS: tuple[str, ...] = (
    "fixed_cluster_victim_delta_tau",
    "fixed_cluster_victim_delta_tpr",
    "fixed_cluster_victim_delta_fpr",
    "fixed_cluster_delta_cv_fpr",
    "fixed_cluster_delta_mean_fpr",
    "fixed_cluster_nonvictim_mean_delta_tpr",
    "fixed_cluster_nonvictim_mean_delta_fpr",
)


def _downstream_extended_summary(
    manifest: BoundedSweepManifest, gate: GateParams = DEFAULT_GATE
) -> list[dict[str, Any]]:
    """Summarize signed victim, non-victim, absolute-burden and fixed-cluster effects with seed-level CIs."""
    records = []
    for (pol, obj, src, frac), rows in sorted(
        _group_rows(r for r in manifest.results if r.fraction > 0.0).items()
    ):
        ctx = _DownstreamContext(
            rows, AttackerObjective(obj), PoisoningSourceStrategy(src)
        )
        metrics = _EXTENDED_METRICS + (
            _FIXED_CLUSTER_METRICS if pol == ThresholdPolicy.CLUSTER_THRESHOLD.value else ()
        )
        records.extend(
            {
                **_downstream_metric_record(
                    manifest.analysis_seeds[0], ctx, m, 1.0, "mean", gate
                ),
                "dataset": manifest.dataset.value,
                "policy": pol,
                "fraction": frac,
                "summary_metric": m,
            }
            for m in metrics
        )
    return records


_CLIENT_LEVEL_METRICS: tuple[str, ...] = (
    "delta_tau",
    "victim_delta_tpr",
    "victim_delta_fpr",
    "delta_cv_fpr",
    "nonvictim_mean_delta_tpr",
    "nonvictim_mean_delta_fpr",
)


def _client_level_effects(manifest: BoundedSweepManifest) -> list[dict[str, Any]]:
    """Summarize per-victim effects across training seeds for every claim-bearing and control group."""
    records = []
    for (pol, obj, src, frac), rows in sorted(
        _group_rows(r for r in manifest.results if r.fraction > 0.0).items()
    ):
        by_victim = defaultdict(list)
        for r in rows:
            by_victim[r.victim_id].append(r)
        for victim, v_rows in sorted(by_victim.items()):
            record: dict[str, Any] = {
                "dataset": manifest.dataset.value,
                "policy": pol,
                "objective": obj,
                "source": src,
                "fraction": frac,
                "victim_id": victim,
                "n_seeds": len({r.training_seed for r in v_rows}),
            }
            for m in _CLIENT_LEVEL_METRICS:
                vals = [
                    v for r in v_rows if math.isfinite(v := _metric_value(r, m))
                ]
                record[f"{m}_mean"] = float(np.mean(vals)) if vals else math.nan
                record[f"{m}_std"] = (
                    float(np.std(vals, ddof=1)) if len(vals) > 1 else math.nan
                )
                record[f"{m}_min"] = min(vals) if vals else math.nan
                record[f"{m}_max"] = max(vals) if vals else math.nan
            records.append(record)
    return records


def _cluster_stability_summary(manifest: BoundedSweepManifest) -> list[dict[str, Any]]:
    """Compare attack-time recomputed clusters with fixed clean assignments and report assignment transitions."""
    records = []
    for (pol, obj, src, frac), rows in sorted(
        _group_rows(
            r
            for r in manifest.results
            if r.policy == ThresholdPolicy.CLUSTER_THRESHOLD and r.fraction > 0.0
        ).items()
    ):
        def mean_of(attr: str) -> float:
            return _finite_mean(float(getattr(r, attr)) for r in rows)

        records.append(
            {
                "dataset": manifest.dataset.value,
                "policy": pol,
                "objective": obj,
                "source": src,
                "fraction": frac,
                "n_rows": len(rows),
                "mean_n_reassigned": mean_of("cluster_n_reassigned"),
                "max_n_reassigned": max(r.cluster_n_reassigned for r in rows),
                "reassignment_rate": float(
                    np.mean([r.cluster_n_reassigned > 0 for r in rows])
                ),
                "victim_singleton_clean_rate": float(
                    np.mean([r.cluster_victim_size_clean == 1 for r in rows])
                ),
                "victim_singleton_poisoned_rate": float(
                    np.mean([r.cluster_victim_size_poisoned == 1 for r in rows])
                ),
                "mean_victim_size_clean": mean_of("cluster_victim_size_clean"),
                "mean_victim_size_poisoned": mean_of("cluster_victim_size_poisoned"),
                "mean_silhouette_clean": mean_of("cluster_silhouette_clean"),
                "mean_silhouette_poisoned": mean_of("cluster_silhouette_poisoned"),
                "modal_sizes_clean": list(
                    max(
                        {r.cluster_sizes_clean for r in rows},
                        key=[r.cluster_sizes_clean for r in rows].count,
                    )
                ),
                "modal_sizes_poisoned": list(
                    max(
                        {r.cluster_sizes_poisoned for r in rows},
                        key=[r.cluster_sizes_poisoned for r in rows].count,
                    )
                ),
                "recomputed_victim_delta_tau": mean_of("cluster_victim_effect"),
                "fixed_victim_delta_tau": mean_of("fixed_cluster_victim_delta_tau"),
                "recomputed_victim_delta_tpr": mean_of("victim_delta_tpr"),
                "fixed_victim_delta_tpr": mean_of("fixed_cluster_victim_delta_tpr"),
                "recomputed_victim_delta_fpr": mean_of("victim_delta_fpr"),
                "fixed_victim_delta_fpr": mean_of("fixed_cluster_victim_delta_fpr"),
                "recomputed_delta_cv_fpr": mean_of("delta_cv_fpr"),
                "fixed_delta_cv_fpr": mean_of("fixed_cluster_delta_cv_fpr"),
                "recomputed_nonvictim_delta_tpr": mean_of("nonvictim_mean_delta_tpr"),
                "fixed_nonvictim_delta_tpr": mean_of(
                    "fixed_cluster_nonvictim_mean_delta_tpr"
                ),
                "recomputed_nonvictim_delta_fpr": mean_of("nonvictim_mean_delta_fpr"),
                "fixed_nonvictim_delta_fpr": mean_of(
                    "fixed_cluster_nonvictim_mean_delta_fpr"
                ),
            }
        )
    return records


def _duplicate_and_bound_summary(manifest: BoundedSweepManifest) -> list[dict[str, Any]]:
    """Summarize duplicate-score rates after injection and the share of reachable threshold range consumed."""
    records = []
    for (pol, obj, src, frac), rows in sorted(
        _group_rows(r for r in manifest.results if r.fraction > 0.0).items()
    ):
        bound = [
            r.delta_tau_bound_utilization
            for r in rows
            if math.isfinite(r.delta_tau_bound_utilization)
        ]
        records.append(
            {
                "dataset": manifest.dataset.value,
                "policy": pol,
                "objective": obj,
                "source": src,
                "fraction": frac,
                "mean_n_replaced": float(np.mean([r.n_replaced for r in rows])),
                "mean_duplicate_rate_clean": _finite_mean(
                    r.cal_duplicate_rate_clean for r in rows
                ),
                "mean_duplicate_rate_poisoned": _finite_mean(
                    r.cal_duplicate_rate_poisoned for r in rows
                ),
                "mean_bound_utilization": float(np.mean(bound)) if bound else math.nan,
                "max_bound_utilization": max(bound) if bound else math.nan,
            }
        )
    return records


def _gate_sensitivity_summary(manifest: BoundedSweepManifest) -> list[dict[str, Any]]:
    """Re-evaluate claim classes over a grid of gate parameters and report class counts and flips."""
    default = {
        (r["policy"], r["objective"], r["source"], r["fraction"]): r["claim_class"]
        for r in _claim_gate_decisions(manifest, DEFAULT_GATE)
    }
    records = []
    for sc, vm, mf, fl in product(
        SENSITIVITY_SIGN_CONSISTENCY_GRID,
        SENSITIVITY_VICTIM_MAJORITY_GRID,
        SENSITIVITY_MATERIALITY_GRID,
        SENSITIVITY_IQR_FLOOR_GRID,
    ):
        decisions = _claim_gate_decisions(manifest, GateParams(
                sign_consistency=sc,
                victim_majority=vm,
                materiality_factor=mf,
                iqr_floor_factor=fl,
            ))
        classes = [d["claim_class"] for d in decisions]
        records.append(
            {
                "dataset": manifest.dataset.value,
                "sign_consistency": sc,
                "victim_majority": vm,
                "materiality_factor": mf,
                "iqr_floor_factor": fl,
                "n_groups": len(decisions),
                "n_full_vulnerability": classes.count("full_vulnerability"),
                "n_mechanism_only": classes.count("mechanism_only"),
                "n_null_or_conditional": classes.count("null_or_conditional"),
                "n_calibration_instability": classes.count("calibration_instability"),
                "n_changed_vs_default": sum(
                    d["claim_class"]
                    != default[(d["policy"], d["objective"], d["source"], d["fraction"])]
                    for d in decisions
                ),
            }
        )
    return records


def _manifest_summary(manifest: BoundedSweepManifest) -> dict[str, Any]:
    """Return a summary dict of manifest metadata, configuration, and row counts."""
    return {
        "schema_version": manifest.schema_version,
        "dataset": manifest.dataset.value,
        "stage": manifest.stage.value,
        "config_hash": manifest.config_hash,
        "code_commit": manifest.provenance.code_commit,
        "training_seeds": list(manifest.training_seeds),
        "poisoning_seeds": list(manifest.poisoning_seeds),
        "analysis_seeds": list(manifest.analysis_seeds),
        "policies": [p.value for p in manifest.policies],
        "sources": [s.value for s in manifest.sources],
        "source_objective_pairs": list(manifest.source_objective_pairs),
        "fractions": list(manifest.fractions),
        "n_reporting_rows": manifest.n_cells,
        "reporting_row_count_semantics": "objective-labeled rows; not independent statistical evidence",
        "artifact_provenance": manifest.artifact_provenance,
    }
