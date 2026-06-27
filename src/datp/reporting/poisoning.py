"""Poisoning analysis summaries: threshold shifts, excess over random, and claim gates."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
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
    SIGN_CONSISTENCY_THRESHOLD,
)
from datp.attacks.enums import AttackerObjective, PoisoningSourceStrategy
from datp.attacks.manifests.bounded_sweep_manifest import (
    BoundedSweepManifest,
    BoundedSweepResultRow,
)
from datp.core.enums import ThresholdPolicy
from datp.statistics.aggregates import iqr
from datp.statistics.bootstrap import bootstrap_ci

_VICTIM_MAJORITY = 5


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
    manifest = _load_manifest(base_dir)
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
    ]

    paths = [
        p for stem, recs in outputs for p in _write_records(analysis_dir, stem, recs)
    ]
    paths.append(
        _write_json(analysis_dir / "manifest_summary.json", _manifest_summary(manifest))
    )
    return BuildPoisoningSummariesResult(paths=paths)


def _load_manifest(base_dir: Path) -> BoundedSweepManifest:
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
    finite = [v for v in seed_values.values() if math.isfinite(v)]
    if len(finite) < BOOTSTRAP_MIN_FINITE:
        return {
            "bootstrap_ci_lower": math.nan,
            "bootstrap_ci_upper": math.nan,
            "bootstrap_mean": math.nan,
            "bootstrap_n_seed_aggregates": len(finite),
        }
    res = bootstrap_ci(
        np.array(finite, dtype=np.float64),
        n_bootstrap=BOOTSTRAP_N,
        ci=BOOTSTRAP_CI,
        seed=analysis_seed,
    )
    return {
        "bootstrap_ci_lower": res.ci_lower,
        "bootstrap_ci_upper": res.ci_upper,
        "bootstrap_mean": res.mean_delta,
        "bootstrap_n_seed_aggregates": res.n_seeds,
    }


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


def _victim_majority_count(rows: list[BoundedSweepResultRow], absolute: bool) -> int:
    """Count seeds where at least _VICTIM_MAJORITY victims show a significant shift in the expected direction."""
    by_seed = defaultdict(list)
    for r in rows:
        by_seed[r.training_seed].append(r)
    return sum(
        1
        for s_rows in by_seed.values()
        if sum(
            1
            for r in s_rows
            if r.is_victim_significant
            and (
                absolute
                or (1 if r.objective == AttackerObjective.THRESHOLD_RAISE else -1)
                * r.delta_tau
                > 0.0
            )
        )
        >= _VICTIM_MAJORITY
    )


def _threshold_shift_summary(manifest: BoundedSweepManifest) -> list[dict[str, Any]]:
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
                    len([r for r in rows if r.is_victim_significant and sign * r.delta_tau > 0.0])
                    / len(rows)
                    if rows
                    else math.nan
                ),
                "seed_sign_count": s_count,
                "victim_majority_count": _victim_majority_count(rows, absolute=False),
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


def _directional_excess_summary(manifest: BoundedSweepManifest) -> list[dict[str, Any]]:
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
                    "directional_excess_seed_support": s_count,
                    "median_directional_excess": _median(s_vals.values()),
                    "gate2_pass": s_count >= SIGN_CONSISTENCY_THRESHOLD
                    and _median(s_vals.values()) > 0.0,
                    **_bootstrap_payload(s_vals, manifest.analysis_seeds[0]),
                    **_exact_support(s_count, len(s_vals)),
                }
            )
    return records


def _random_instability_summary(manifest: BoundedSweepManifest) -> list[dict[str, Any]]:
    """Summarize random-control instability count and flag for each RANDOM_BENIGN group."""
    return [
        {
            "dataset": manifest.dataset.value,
            "policy": pol,
            "objective": obj,
            "source": src,
            "fraction": frac,
            "random_control_instability_count": (
                cnt := _victim_majority_count(rows, absolute=True)
            ),
            "random_control_unstable": cnt >= SIGN_CONSISTENCY_THRESHOLD,
        }
        for (pol, obj, src, frac), rows in sorted(_group_rows(manifest.results).items())
        if src == PoisoningSourceStrategy.RANDOM_BENIGN.value
    ]


def _leave_one_victim_out_summary(
    manifest: BoundedSweepManifest,
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
            if _support_count(s_vals) >= SIGN_CONSISTENCY_THRESHOLD and med > 0.0:
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


def _downstream_metric_record(
    analysis_seed: int, ctx: _DownstreamContext, metric: str, transform: float, agg: str
) -> dict[str, Any]:
    """Build a single downstream harm record for one metric, sign transform, and seed aggregation method."""
    by_seed = defaultdict(list)
    for r in ctx.rows:
        if math.isfinite(v := transform * float(getattr(r, metric))):
            by_seed[r.training_seed].append(v)
    s_vals = {
        s: max(v) if agg == "max" else float(np.mean(v)) for s, v in by_seed.items()
    }
    return {
        "objective": ctx.objective.value,
        "source": ctx.source.value,
        "metric": metric,
        "expected_sign_seed_support": (s_cnt := _support_count(s_vals)),
        "median_harm": _median(s_vals.values()),
        "gate3_metric_pass": s_cnt >= SIGN_CONSISTENCY_THRESHOLD
        and _median(s_vals.values()) > 0.0,
        **_bootstrap_payload(s_vals, analysis_seed),
        **_exact_support(s_cnt, len(s_vals)),
    }


def _downstream_raising_summary(manifest: BoundedSweepManifest) -> list[dict[str, Any]]:
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
    manifest: BoundedSweepManifest,
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


def _claim_gate_decisions(manifest: BoundedSweepManifest) -> list[dict[str, Any]]:
    """Apply the three-gate claim logic and classify each claim-bearing group into a claim class."""
    excess = {
        (r["policy"], r["objective"], r["source"], r["fraction"]): r
        for r in _directional_excess_summary(manifest)
    }
    r_instab = {
        (r["policy"], r["objective"], r["fraction"]): r["random_control_unstable"]
        for r in _random_instability_summary(manifest)
    }
    d_pass: defaultdict[tuple[str, str, str, float], bool] = defaultdict(bool)
    for r in _downstream_raising_summary(manifest) + _downstream_lowering_summary(
        manifest
    ):
        d_pass[(r["policy"], r["objective"], r["source"], r["fraction"])] |= bool(
            r["gate3_metric_pass"]
        )

    records = []
    for t_rec in _threshold_shift_summary(manifest):
        if not t_rec["claim_bearing"]:
            continue
        pol, obj, src, frac = t_rec["policy"], t_rec["objective"], t_rec["source"], t_rec["fraction"]
        key = (pol, obj, src, frac)
        g1 = (
            t_rec["seed_sign_count"] >= SIGN_CONSISTENCY_THRESHOLD
            and t_rec["victim_majority_count"] >= SIGN_CONSISTENCY_THRESHOLD
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
