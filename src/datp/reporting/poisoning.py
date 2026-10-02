from __future__ import annotations

from datp.types import (
    ClientId,
    JsonRecord,
    JsonValue,
    NarrativeText,
    PoisonFraction,
    RandomSeed,
    RecordKey,
    SampleCount,
    ScoreValue,
    SeedCount,
    SignedCount,
)


import csv
import json
import math
from collections import defaultdict
from collections.abc import Callable, Hashable, Iterable
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from pathlib import Path
from typing import TypeVar

import numpy as np
from scipy.stats import binomtest

from datp.artifacts.names import ArtifactDir
from datp.artifacts.layout import nbaiot_main_manifest_path, sensitivity_manifest_path
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
    ClaimClassification,
    PoisoningSourceStrategy,
    SeedAggregationMethod,
)
from datp.attacks.manifests.bounded_sweep_manifest import (
    BoundedSweepManifest,
    BoundedSweepResultRow,
)
from datp.attacks.manifests.sensitivity_manifest import SensitivityManifest
from datp.attacks.metrics.delta_tau import materiality_scale
from datp.core.enums import MetricName, ThresholdPolicy
from datp.data.catalog import DatasetID
from datp.reporting.constants import METRIC_DEFINITIONS
from datp.reporting.enums import AnalysisReportStem, ReportTerm
from datp.statistics.aggregates import iqr
from datp.statistics.bootstrap import bootstrap_ci
from datp.statistics.permutation import sign_flip_p_value

T = TypeVar("T")
K = TypeVar("K", bound=Hashable)


@dataclass(frozen=True, slots=True)
class GateParams:

    sign_consistency: SignedCount
    victim_majority: SignedCount
    materiality_factor: ScoreValue
    iqr_floor_factor: ScoreValue


@dataclass(frozen=True, slots=True)
class _ClaimGateDecision:

    dataset: DatasetID
    policy: ThresholdPolicy
    objective: AttackerObjective
    source: PoisoningSourceStrategy
    fraction: PoisonFraction
    gate1_pass: bool
    gate2_pass: bool
    gate3_pass: bool
    random_control_unstable: bool
    claim_class: ClaimClassification


@dataclass(frozen=True, slots=True)
class _SummaryIdentity:

    dataset: DatasetID
    policy: ThresholdPolicy
    objective: AttackerObjective
    source: PoisoningSourceStrategy
    fraction: PoisonFraction


@dataclass(frozen=True, slots=True)
class _BootstrapSummary:

    ci_lower: ScoreValue
    ci_upper: ScoreValue
    mean: ScoreValue
    seed_aggregates: SampleCount


@dataclass(frozen=True, slots=True)
class _ExactSupportSummary:

    support_count: SignedCount
    seed_count: SeedCount
    binomial_p: ScoreValue


@dataclass(frozen=True, slots=True)
class _ThresholdShiftSummary:

    identity: _SummaryIdentity
    claim_bearing: bool
    mean_delta_tau: ScoreValue
    median_delta_tau: ScoreValue
    iqr_delta_tau: ScoreValue
    material_signed_rate: ScoreValue
    seed_sign_count: SignedCount
    victim_majority_count: SampleCount
    bootstrap: _BootstrapSummary
    exact_support: _ExactSupportSummary


@dataclass(frozen=True, slots=True)
class _DirectionalExcessSummary:

    identity: _SummaryIdentity
    control_source: PoisoningSourceStrategy
    control_objective: AttackerObjective
    seed_support: SignedCount
    median_excess: ScoreValue
    mean_excess: ScoreValue
    per_seed_excess: dict[RandomSeed, ScoreValue]
    permutation_p: ScoreValue
    gate_pass: bool
    bootstrap: _BootstrapSummary
    exact_support: _ExactSupportSummary


@dataclass(frozen=True, slots=True)
class _RandomInstabilitySummary:

    identity: _SummaryIdentity
    instability_count: SampleCount
    unstable: bool


@dataclass(frozen=True, slots=True)
class _DownstreamMetricSummary:

    metric: MetricName
    seed_support: SignedCount
    negative_seed_count: SampleCount
    median_harm: ScoreValue
    mean_effect: ScoreValue
    per_seed_values: dict[RandomSeed, ScoreValue]
    permutation_p: ScoreValue
    gate_pass: bool
    bootstrap: _BootstrapSummary
    exact_support: _ExactSupportSummary


@dataclass(frozen=True, slots=True)
class _DownstreamHarmSummary:

    identity: _SummaryIdentity
    metric_summary: _DownstreamMetricSummary
    summary_metric: MetricName


def _summary_identity_payload(identity: _SummaryIdentity) -> JsonRecord:
    return {
        "dataset": identity.dataset,
        "policy": identity.policy,
        "objective": identity.objective,
        "source": identity.source,
        "fraction": identity.fraction,
    }


def _bootstrap_summary_payload(summary: _BootstrapSummary) -> JsonRecord:
    return {
        "bootstrap_ci_lower": summary.ci_lower,
        "bootstrap_ci_upper": summary.ci_upper,
        "bootstrap_mean": summary.mean,
        "bootstrap_n_seed_aggregates": summary.seed_aggregates,
    }


def _exact_support_payload(summary: _ExactSupportSummary) -> JsonRecord:
    return {
        "exact_support_count": summary.support_count,
        "exact_support_n": summary.seed_count,
        "exact_binomial_p": summary.binomial_p,
    }


def _threshold_shift_payload(summary: _ThresholdShiftSummary) -> JsonRecord:
    return {
        **_summary_identity_payload(summary.identity),
        "claim_bearing": summary.claim_bearing,
        "mean_delta_tau": summary.mean_delta_tau,
        "median_delta_tau": summary.median_delta_tau,
        "iqr_delta_tau": summary.iqr_delta_tau,
        "material_signed_rate": summary.material_signed_rate,
        "seed_sign_count": summary.seed_sign_count,
        "victim_majority_count": summary.victim_majority_count,
        **_bootstrap_summary_payload(summary.bootstrap),
        **_exact_support_payload(summary.exact_support),
    }


def _directional_excess_payload(summary: _DirectionalExcessSummary) -> JsonRecord:
    return {
        **_summary_identity_payload(summary.identity),
        "control_source": summary.control_source,
        "control_objective": summary.control_objective,
        "directional_excess_seed_support": summary.seed_support,
        "median_directional_excess": summary.median_excess,
        "mean_directional_excess": summary.mean_excess,
        "per_seed_directional_excess": {
            str(seed): value for seed, value in summary.per_seed_excess.items()
        },
        "permutation_p": summary.permutation_p,
        "gate2_pass": summary.gate_pass,
        **_bootstrap_summary_payload(summary.bootstrap),
        **_exact_support_payload(summary.exact_support),
    }


def _random_instability_payload(summary: _RandomInstabilitySummary) -> JsonRecord:
    return {
        **_summary_identity_payload(summary.identity),
        "random_control_instability_count": summary.instability_count,
        "random_control_unstable": summary.unstable,
    }


def _downstream_metric_payload(summary: _DownstreamMetricSummary) -> JsonRecord:
    return {
        "metric": summary.metric,
        "expected_sign_seed_support": summary.seed_support,
        "n_seeds_negative": summary.negative_seed_count,
        "median_harm": summary.median_harm,
        "mean_effect": summary.mean_effect,
        "per_seed_values": {
            str(seed): value for seed, value in summary.per_seed_values.items()
        },
        "permutation_p": summary.permutation_p,
        "gate3_metric_pass": summary.gate_pass,
        **_bootstrap_summary_payload(summary.bootstrap),
        **_exact_support_payload(summary.exact_support),
    }


def _downstream_harm_payload(summary: _DownstreamHarmSummary) -> JsonRecord:
    return {
        **_summary_identity_payload(summary.identity),
        **_downstream_metric_payload(summary.metric_summary),
        "summary_metric": summary.summary_metric,
    }


DEFAULT_GATE = GateParams(
    sign_consistency=SIGN_CONSISTENCY_THRESHOLD,
    victim_majority=VICTIM_MAJORITY_THRESHOLD,
    materiality_factor=MATERIALITY_FACTOR,
    iqr_floor_factor=IQR_FLOOR_FACTOR,
)


@dataclass(frozen=True, slots=True)
class _DownstreamContext:

    rows: list[BoundedSweepResultRow]
    objective: AttackerObjective
    source: PoisoningSourceStrategy


@dataclass(frozen=True, slots=True)
class _ClaimKey:

    policy: ThresholdPolicy
    objective: AttackerObjective
    source: PoisoningSourceStrategy
    fraction: PoisonFraction


def _claim_key(identity: _SummaryIdentity) -> _ClaimKey:
    return _ClaimKey(
        identity.policy,
        identity.objective,
        identity.source,
        identity.fraction,
    )


def build_poisoning_summaries(base_dir: Path) -> tuple[Path, ...]:
    manifest = load_poisoning_manifest(base_dir)
    analysis_dir = base_dir / ArtifactDir.ANALYSIS
    analysis_dir.mkdir(parents=True, exist_ok=True)

    outputs = [
        (
            AnalysisReportStem.THRESHOLD_SHIFT_SUMMARY,
            [_threshold_shift_payload(row) for row in _threshold_shift_summary(manifest)],
        ),
        (
            AnalysisReportStem.DIRECTIONAL_EXCESS_OVER_RANDOM,
            [_directional_excess_payload(row) for row in _directional_excess_summary(manifest)],
        ),
        (
            AnalysisReportStem.RANDOM_CONTROL_INSTABILITY,
            [_random_instability_payload(row) for row in _random_instability_summary(manifest)],
        ),
        (
            AnalysisReportStem.LEAVE_ONE_VICTIM_OUT_SENSITIVITY,
            _leave_one_victim_out_summary(manifest),
        ),
        (
            AnalysisReportStem.DOWNSTREAM_HARM_RAISING,
            [_downstream_harm_payload(row) for row in _downstream_raising_summary(manifest)],
        ),
        (
            AnalysisReportStem.DOWNSTREAM_HARM_LOWERING,
            [_downstream_harm_payload(row) for row in _downstream_lowering_summary(manifest)],
        ),
        (
            AnalysisReportStem.CLUSTER_DIAGNOSTICS_SUMMARY,
            _cluster_diagnostics_summary(manifest),
        ),
        (
            AnalysisReportStem.CLAIM_GATE_DECISIONS,
            [
                _claim_gate_decision_payload(decision)
                for decision in _claim_gate_decisions(manifest)
            ],
        ),
        (AnalysisReportStem.DOWNSTREAM_EXTENDED, _downstream_extended_summary(manifest)),
        (AnalysisReportStem.CLIENT_LEVEL_EFFECTS, _client_level_effects(manifest)),
        (
            AnalysisReportStem.CLUSTER_STABILITY_SUMMARY,
            _cluster_stability_summary(manifest),
        ),
        (
            AnalysisReportStem.DUPLICATE_AND_BOUND_SUMMARY,
            _duplicate_and_bound_summary(manifest),
        ),
        (AnalysisReportStem.GATE_SENSITIVITY, _gate_sensitivity_summary(manifest)),
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
    return tuple(paths)


def build_sensitivity_summaries(base_dir: Path) -> tuple[Path, ...]:
    if not (path := sensitivity_manifest_path(base_dir)).exists():
        raise FileNotFoundError(f"Missing sensitivity manifest: {path}")
    manifest = SensitivityManifest.model_validate_json(path.read_text())
    analysis_dir = base_dir / ArtifactDir.ANALYSIS
    analysis_dir.mkdir(parents=True, exist_ok=True)
    outputs = [
        (
            AnalysisReportStem.CLUSTER_STABILITY_SENSITIVITY,
            _cluster_sensitivity_summary(manifest),
        ),
        (
            AnalysisReportStem.SCALE_NORMALIZATION_SUMMARY,
            _scale_normalization_summary(manifest),
        ),
        (AnalysisReportStem.DRAW_VARIANT_SUMMARY, _draw_variant_summary(manifest)),
        (AnalysisReportStem.TRUST_BOUNDARY_SUMMARY, _trust_boundary_summary(manifest)),
    ]
    return tuple(
        p for stem, recs in outputs for p in _write_records(analysis_dir, stem, recs)
    )


def _group_by(
    rows: Iterable[T], key: Callable[[T], K]
) -> dict[K, list[T]]:
    grouped: defaultdict[K, list[T]] = defaultdict(list)
    for r in rows:
        grouped[key(r)].append(r)
    return dict(grouped)


def _cluster_sensitivity_summary(manifest: SensitivityManifest) -> list[JsonRecord]:
    records: list[JsonRecord] = []
    for (src, obj, frac, k, n_init), rows in sorted(
        _group_by(
            manifest.cluster_stability,
            lambda row: (
                row.source,
                row.objective,
                row.fraction,
                row.k,
                row.n_init,
            ),
        ).items()
    ):
        by_cell: defaultdict[tuple[RandomSeed, ClientId], list[ScoreValue]] = defaultdict(list)
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


def _scale_normalization_summary(manifest: SensitivityManifest) -> list[JsonRecord]:
    records: list[JsonRecord] = []
    for (src, obj, frac), rows in sorted(
        _group_by(
            manifest.scale_normalization,
            lambda row: (row.source, row.objective, row.fraction),
        ).items()
    ):

        records.append(
            {
                "source": src,
                "objective": obj,
                "fraction": frac,
                "n_rows": len(rows),
                "mean_tau_local_cv_clean": _finite_mean(r.tau_local_cv_clean for r in rows),
                "mean_tau_local_max_min_ratio_clean": _finite_mean(r.tau_local_max_min_ratio_clean for r in rows),
                "mean_score_scale_cv_clean": _finite_mean(r.score_scale_cv_clean for r in rows),
                "raw_global_victim_delta_tau": _finite_mean(r.raw_global_victim_delta_tau for r in rows),
                "normalized_global_victim_delta_tau": _finite_mean(r.normalized_global_victim_delta_tau for r in rows),
                "raw_global_victim_delta_fpr": _finite_mean(r.raw_global_victim_delta_fpr for r in rows),
                "normalized_global_victim_delta_fpr": _finite_mean(r.normalized_global_victim_delta_fpr for r in rows),
                "raw_global_cv_fpr_clean": _finite_mean(r.raw_global_cv_fpr_clean for r in rows),
                "normalized_global_cv_fpr_clean": _finite_mean(r.normalized_global_cv_fpr_clean for r in rows),
                "raw_global_cv_fpr_poisoned": _finite_mean(r.raw_global_cv_fpr_poisoned for r in rows),
                "normalized_global_cv_fpr_poisoned": _finite_mean(r.normalized_global_cv_fpr_poisoned for r in rows),
            }
        )
    return records


def _draw_variant_summary(manifest: SensitivityManifest) -> list[JsonRecord]:
    records: list[JsonRecord] = []
    for (pol, src, obj, frac, draw), rows in sorted(
        _group_by(
            manifest.draw_variants,
            lambda row: (
                row.policy,
                row.source,
                row.objective,
                row.fraction,
                row.draw,
            ),
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
                "synthesized_values": draw in {d for d in SYNTHESIZED_DRAWS},
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


def _trust_boundary_summary(manifest: SensitivityManifest) -> list[JsonRecord]:
    records: list[JsonRecord] = []
    for (pol, src, obj, frac), rows in sorted(
        _group_by(
            manifest.trust_boundary,
            lambda row: (row.policy, row.source, row.objective, row.fraction),
        ).items()
    ):

        undefended = _finite_mean(r.delta_tau_undefended for r in rows)
        records.append(
            {
                "policy": pol,
                "source": src,
                "objective": obj,
                "fraction": frac,
                "n_rows": len(rows),
                "mean_delta_tau_undefended": undefended,
                "mean_delta_tau_trim_primary": _finite_mean(r.delta_tau_trim_primary for r in rows),
                "mean_delta_tau_trim_appendix": _finite_mean(r.delta_tau_trim_appendix for r in rows),
                "mean_residual_vs_clean_trim_primary": _finite_mean(r.residual_vs_clean_trim_primary for r in rows),
                "mean_residual_vs_clean_trim_appendix": _finite_mean(r.residual_vs_clean_trim_appendix for r in rows),
                "mean_overwrite_reference_shift": _finite_mean(r.overwrite_reference_shift for r in rows),
                "mean_buffer_to_overwrite_ratio": _finite_mean(r.buffer_to_overwrite_ratio for r in rows),
                "trim_primary_reduction": 1.0
                - _finite_mean(r.delta_tau_trim_primary for r in rows) / undefended
                if math.isfinite(undefended) and undefended != 0.0
                else math.nan,
            }
        )
    return records


def load_poisoning_manifest(base_dir: Path) -> BoundedSweepManifest:
    if not (path := nbaiot_main_manifest_path(base_dir)).exists():
        raise FileNotFoundError(f"Missing bounded 10-seed manifest: {path}")
    return BoundedSweepManifest.model_validate_json(path.read_text())


def _write_json(
    path: Path,
    payload: JsonValue
    | JsonRecord
    | list[JsonRecord]
    | dict[MetricName | ReportTerm, NarrativeText],
) -> Path:
    path.write_text(json.dumps(_json_safe(payload), indent=2, allow_nan=False))
    return path


def _json_safe(
    payload: JsonValue
    | JsonRecord
    | list[JsonRecord]
    | dict[MetricName | ReportTerm, NarrativeText],
) -> JsonValue:
    if isinstance(payload, float):
        return payload if math.isfinite(payload) else None
    if isinstance(payload, dict):
        return {str(key): _json_safe(value) for key, value in payload.items()}
    if isinstance(payload, (list, tuple)):
        return [_json_safe(v) for v in payload]
    return payload


def _write_records(
    output_dir: Path, stem: AnalysisReportStem, records: list[JsonRecord]
) -> list[Path]:
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
) -> dict[
    tuple[ThresholdPolicy, AttackerObjective, PoisoningSourceStrategy, PoisonFraction],
    list[BoundedSweepResultRow],
]:
    grouped: defaultdict[
        tuple[ThresholdPolicy, AttackerObjective, PoisoningSourceStrategy, PoisonFraction],
        list[BoundedSweepResultRow],
    ] = defaultdict(list)
    for r in rows:
        grouped[(r.policy, r.objective, r.source, r.fraction)].append(
            r
        )
    return dict(grouped)


def _seed_values(
    rows: Iterable[BoundedSweepResultRow], transform: ScoreValue = 1.0
) -> dict[RandomSeed, ScoreValue]:
    by_seed: defaultdict[RandomSeed, list[ScoreValue]] = defaultdict(list)
    for r in rows:
        if math.isfinite(v := r.delta_tau):
            by_seed[r.training_seed].append(transform * v)
    return {s: float(np.mean(vals)) for s, vals in sorted(by_seed.items()) if vals}


def _support_count(seed_values: dict[RandomSeed, ScoreValue]) -> SampleCount:
    return sum(1 for v in seed_values.values() if math.isfinite(v) and v > 0.0)


def _finite_mean(values: Iterable[ScoreValue]) -> ScoreValue:
    return (
        float(np.mean(f))
        if (f := [v for v in values if math.isfinite(v)])
        else math.nan
    )


def _median(values: Iterable[ScoreValue]) -> ScoreValue:
    return (
        float(np.median(f))
        if (f := [v for v in values if math.isfinite(v)])
        else math.nan
    )


def _bootstrap_payload(
    seed_values: dict[RandomSeed, ScoreValue], analysis_seed: RandomSeed
) -> _BootstrapSummary:
    return _cached_bootstrap(
        tuple(v for v in seed_values.values() if math.isfinite(v)), analysis_seed
    )


@lru_cache(maxsize=None)
def _cached_bootstrap(
    finite: tuple[ScoreValue, ...], analysis_seed: RandomSeed
) -> _BootstrapSummary:
    if len(finite) < BOOTSTRAP_MIN_FINITE:
        return _BootstrapSummary(math.nan, math.nan, math.nan, len(finite))
    res = bootstrap_ci(
        np.array(finite, dtype=np.float64),
        n_bootstrap=BOOTSTRAP_N,
        ci=BOOTSTRAP_CI,
        seed=analysis_seed,
    )
    return _BootstrapSummary(
        res.ci_lower, res.ci_upper, res.mean_delta, res.n_seeds
    )


def _exact_support(seed_support: SignedCount, n_seeds: SeedCount) -> _ExactSupportSummary:
    return _ExactSupportSummary(
        seed_support,
        n_seeds,
        float(
            binomtest(seed_support, n_seeds, p=0.5, alternative="greater").pvalue
        )
        if n_seeds
        else math.nan,
    )


def _is_significant(r: BoundedSweepResultRow, gate: GateParams) -> bool:
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
) -> SampleCount:
    by_seed: defaultdict[RandomSeed, list[BoundedSweepResultRow]] = defaultdict(list)
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
) -> list[_ThresholdShiftSummary]:
    records: list[_ThresholdShiftSummary] = []
    for (pol, obj, src, frac), rows in sorted(_group_rows(manifest.results).items()):
        sign = 1.0 if obj == AttackerObjective.THRESHOLD_RAISE else -1.0
        s_vals = _seed_values(rows, sign)
        s_count = _support_count(s_vals)
        records.append(
            _ThresholdShiftSummary(
                identity=_SummaryIdentity(manifest.dataset, pol, obj, src, frac),
                claim_bearing=frac > 0.0
                and src != PoisoningSourceStrategy.RANDOM_BENIGN,
                mean_delta_tau=float(np.mean([r.delta_tau for r in rows])),
                median_delta_tau=_median(r.delta_tau for r in rows),
                iqr_delta_tau=iqr(np.array([r.delta_tau for r in rows])),
                material_signed_rate=(
                    len(
                        [
                            r
                            for r in rows
                            if _is_significant(r, gate) and sign * r.delta_tau > 0.0
                        ]
                    )
                    / len(rows)
                    if rows
                    else math.nan
                ),
                seed_sign_count=s_count,
                victim_majority_count=_victim_majority_count(rows, False, gate),
                bootstrap=_bootstrap_payload(s_vals, manifest.analysis_seeds[0]),
                exact_support=_exact_support(s_count, len(s_vals)),
            )
        )
    return records


def _excess_by_seed(
    att_rows: list[BoundedSweepResultRow],
    random_rows: dict[
        tuple[ThresholdPolicy, PoisonFraction, ClientId, RandomSeed, RandomSeed],
        BoundedSweepResultRow,
    ],
    obj: AttackerObjective,
) -> dict[RandomSeed, ScoreValue]:
    bucket: defaultdict[RandomSeed, list[ScoreValue]] = defaultdict(list)
    for att in att_rows:
        rnd = random_rows.get(
            (
                att.policy,
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
) -> list[_DirectionalExcessSummary]:
    records: list[_DirectionalExcessSummary] = []
    for obj, src_tgt in [
        (AttackerObjective.THRESHOLD_RAISE, PoisoningSourceStrategy.HIGH_SCORE_BENIGN),
        (AttackerObjective.THRESHOLD_LOWER, PoisoningSourceStrategy.LOW_SCORE_BENIGN),
    ]:
        random_rows = {
            (
                r.policy,
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
                _DirectionalExcessSummary(
                    identity=_SummaryIdentity(manifest.dataset, pol, obj, src, frac),
                    control_source=PoisoningSourceStrategy.RANDOM_BENIGN,
                    control_objective=obj,
                    seed_support=s_count,
                    median_excess=_median(s_vals.values()),
                    mean_excess=_finite_mean(s_vals.values()),
                    per_seed_excess=s_vals,
                    permutation_p=sign_flip_p_value(
                        np.array(list(s_vals.values()), dtype=np.float64)
                    ),
                    gate_pass=s_count >= gate.sign_consistency
                    and _median(s_vals.values()) > 0.0,
                    bootstrap=_bootstrap_payload(s_vals, manifest.analysis_seeds[0]),
                    exact_support=_exact_support(s_count, len(s_vals)),
                )
            )
    return records


def _random_instability_summary(
    manifest: BoundedSweepManifest, gate: GateParams = DEFAULT_GATE
) -> list[_RandomInstabilitySummary]:
    return [
        _RandomInstabilitySummary(
            identity=_SummaryIdentity(manifest.dataset, pol, obj, src, frac),
            instability_count=(cnt := _victim_majority_count(rows, True, gate)),
            unstable=cnt >= gate.sign_consistency,
        )
        for (pol, obj, src, frac), rows in sorted(_group_rows(manifest.results).items())
        if src == PoisoningSourceStrategy.RANDOM_BENIGN
    ]


def _leave_one_victim_out_summary(
    manifest: BoundedSweepManifest, gate: GateParams = DEFAULT_GATE
) -> list[JsonRecord]:
    records: list[JsonRecord] = []
    main_sources = {
        PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        PoisoningSourceStrategy.LOW_SCORE_BENIGN,
    }
    for (pol, obj, src, frac), rows in sorted(_group_rows(manifest.results).items()):
        if src not in main_sources or math.isclose(frac, 0.0, abs_tol=1e-12):
            continue
        victims = sorted({r.victim_id for r in rows})
        sign = 1.0 if obj == AttackerObjective.THRESHOLD_RAISE else -1.0
        excl_means: list[ScoreValue] = []
        stable = 0
        for excl in victims:
            s_vals = _seed_values(
                [r for r in rows if r.victim_id != excl], transform=sign
            )
            med = _median(s_vals.values())
            excl_means.append(med)
            if _support_count(s_vals) >= gate.sign_consistency and med > 0.0:
                stable += 1
        records.append(
            {
                "dataset": manifest.dataset,
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


def _victim_metric_value(
    row: BoundedSweepResultRow, metric: MetricName
) -> ScoreValue | None:
    match metric:
        case MetricName.VICTIM_DELTA_FP:
            return float(row.victim_fp_poisoned - row.victim_fp_clean)
        case MetricName.VICTIM_DELTA_FN:
            return float(row.victim_fn_poisoned - row.victim_fn_clean)
        case MetricName.VICTIM_DELTA_TAU:
            return row.delta_tau
        case MetricName.VICTIM_DELTA_TPR:
            return row.victim_delta_tpr
        case MetricName.VICTIM_DELTA_FPR:
            return row.victim_delta_fpr
        case MetricName.VICTIM_DELTA_BA:
            return row.victim_delta_ba
        case MetricName.VICTIM_DELTA_MACRO_F1:
            return row.victim_delta_macro_f1
        case _:
            return None


def _nonvictim_metric_value(
    row: BoundedSweepResultRow, metric: MetricName
) -> ScoreValue | None:
    match metric:
        case MetricName.NONVICTIM_MEAN_DELTA_TPR:
            return row.nonvictim_mean_delta_tpr
        case MetricName.NONVICTIM_WORST_DELTA_TPR:
            return row.nonvictim_worst_delta_tpr
        case MetricName.NONVICTIM_MEAN_DELTA_FPR:
            return row.nonvictim_mean_delta_fpr
        case MetricName.NONVICTIM_WORST_DELTA_FPR:
            return row.nonvictim_worst_delta_fpr
        case MetricName.NONVICTIM_MEAN_DELTA_BA:
            return row.nonvictim_mean_delta_ba
        case MetricName.NONVICTIM_MEAN_DELTA_MACRO_F1:
            return row.nonvictim_mean_delta_macro_f1
        case MetricName.NONVICTIM_DELTA_FN_TOTAL:
            return row.nonvictim_delta_fn_total
        case MetricName.NONVICTIM_DELTA_FP_TOTAL:
            return row.nonvictim_delta_fp_total
        case _:
            return None


def _dispersion_metric_value(
    row: BoundedSweepResultRow, metric: MetricName
) -> ScoreValue | None:
    match metric:
        case MetricName.DELTA_MEAN_FPR:
            return row.delta_mean_fpr
        case MetricName.DELTA_CV_FPR:
            return row.delta_cv_fpr
        case MetricName.DELTA_IQR_FPR:
            return row.delta_iqr_fpr
        case MetricName.DELTA_MAX_MIN_FPR:
            return row.delta_max_min_fpr
        case MetricName.DELTA_WORST_CLIENT_FPR:
            return row.delta_worst_client_fpr
        case _:
            return None


def _fixed_cluster_metric_value(
    row: BoundedSweepResultRow, metric: MetricName
) -> ScoreValue | None:
    match metric:
        case MetricName.FIXED_CLUSTER_VICTIM_DELTA_TAU:
            return row.fixed_cluster_victim_delta_tau
        case MetricName.FIXED_CLUSTER_VICTIM_DELTA_TPR:
            return row.fixed_cluster_victim_delta_tpr
        case MetricName.FIXED_CLUSTER_VICTIM_DELTA_FPR:
            return row.fixed_cluster_victim_delta_fpr
        case MetricName.FIXED_CLUSTER_DELTA_CV_FPR:
            return row.fixed_cluster_delta_cv_fpr
        case MetricName.FIXED_CLUSTER_DELTA_MEAN_FPR:
            return row.fixed_cluster_delta_mean_fpr
        case MetricName.FIXED_CLUSTER_NONVICTIM_MEAN_DELTA_TPR:
            return row.fixed_cluster_nonvictim_mean_delta_tpr
        case MetricName.FIXED_CLUSTER_NONVICTIM_MEAN_DELTA_FPR:
            return row.fixed_cluster_nonvictim_mean_delta_fpr
        case _:
            return None


def _metric_value(r: BoundedSweepResultRow, metric: MetricName) -> ScoreValue:
    if (value := _victim_metric_value(r, metric)) is not None:
        return value
    if (value := _nonvictim_metric_value(r, metric)) is not None:
        return value
    if (value := _dispersion_metric_value(r, metric)) is not None:
        return value
    if (value := _fixed_cluster_metric_value(r, metric)) is not None:
        return value
    raise ValueError(f"Unsupported downstream report metric: {metric!r}")


def _downstream_metric_record(
    analysis_seed: RandomSeed,
    ctx: _DownstreamContext,
    metric: MetricName,
    transform: ScoreValue,
    aggregation: SeedAggregationMethod,
    gate: GateParams = DEFAULT_GATE,
) -> _DownstreamMetricSummary:
    by_seed: defaultdict[RandomSeed, list[ScoreValue]] = defaultdict(list)
    for r in ctx.rows:
        if math.isfinite(v := transform * _metric_value(r, metric)):
            by_seed[r.training_seed].append(v)
    s_vals = {
        s: max(v)
        if aggregation is SeedAggregationMethod.MAXIMUM
        else float(np.mean(v))
        for s, v in by_seed.items()
    }
    arr = np.array(list(s_vals.values()), dtype=np.float64)
    support_count = _support_count(s_vals)
    return _DownstreamMetricSummary(
        metric=metric,
        seed_support=support_count,
        negative_seed_count=int(np.sum(arr < 0.0)),
        median_harm=_median(s_vals.values()),
        mean_effect=_finite_mean(s_vals.values()),
        per_seed_values=dict(sorted(s_vals.items())),
        permutation_p=sign_flip_p_value(arr),
        gate_pass=support_count >= gate.sign_consistency
        and _median(s_vals.values()) > 0.0,
        bootstrap=_bootstrap_payload(s_vals, analysis_seed),
        exact_support=_exact_support(support_count, len(s_vals)),
    )


def _downstream_raising_summary(
    manifest: BoundedSweepManifest, gate: GateParams = DEFAULT_GATE
) -> list[_DownstreamHarmSummary]:
    metrics = [
        (MetricName.VICTIM_DELTA_TPR, -1.0, SeedAggregationMethod.MEAN),
        (MetricName.VICTIM_DELTA_BA, -1.0, SeedAggregationMethod.MEAN),
        (MetricName.VICTIM_DELTA_MACRO_F1, -1.0, SeedAggregationMethod.MEAN),
        (MetricName.VICTIM_DELTA_TPR, -1.0, SeedAggregationMethod.MAXIMUM),
    ]
    return [
        _DownstreamHarmSummary(
            identity=_SummaryIdentity(
                manifest.dataset,
                pol,
                AttackerObjective.THRESHOLD_RAISE,
                PoisoningSourceStrategy(src),
                frac,
            ),
            metric_summary=_downstream_metric_record(
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
            summary_metric=(
                MetricName.WORST_VICTIM_DROP
                if a is SeedAggregationMethod.MAXIMUM
                else m
            ),
        )
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
) -> list[_DownstreamHarmSummary]:
    metrics = [
        MetricName.DELTA_MEAN_FPR,
        MetricName.DELTA_CV_FPR,
        MetricName.DELTA_IQR_FPR,
        MetricName.DELTA_MAX_MIN_FPR,
        MetricName.DELTA_WORST_CLIENT_FPR,
    ]
    return [
        _DownstreamHarmSummary(
            identity=_SummaryIdentity(
                manifest.dataset,
                pol,
                AttackerObjective.THRESHOLD_LOWER,
                PoisoningSourceStrategy(src),
                frac,
            ),
            metric_summary=_downstream_metric_record(
                manifest.analysis_seeds[0],
                _DownstreamContext(
                    rows,
                    AttackerObjective.THRESHOLD_LOWER,
                    PoisoningSourceStrategy(src),
                ),
                m,
                1.0,
                SeedAggregationMethod.MEAN,
                gate,
            ),
            summary_metric=m,
        )
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
) -> list[JsonRecord]:
    return [
        {
            "dataset": manifest.dataset,
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
) -> list[_ClaimGateDecision]:
    excess = {
        _claim_key(r.identity): r.gate_pass
        for r in _directional_excess_summary(manifest, gate)
    }
    r_instab = {
        _claim_key(r.identity): r.unstable
        for r in _random_instability_summary(manifest, gate)
    }
    d_pass: defaultdict[_ClaimKey, bool] = defaultdict(bool)
    for r in _downstream_raising_summary(manifest, gate) + _downstream_lowering_summary(
        manifest, gate
    ):
        d_pass[_claim_key(r.identity)] |= r.metric_summary.gate_pass

    records: list[_ClaimGateDecision] = []
    for t_rec in _threshold_shift_summary(manifest, gate):
        if not t_rec.claim_bearing:
            continue
        identity = t_rec.identity
        key = _claim_key(identity)
        sign_count = t_rec.seed_sign_count
        majority_count = t_rec.victim_majority_count
        g1 = (
            sign_count >= gate.sign_consistency
            and majority_count >= gate.sign_consistency
        )
        g2, g3 = excess.get(key, False), d_pass[key]
        random_key = _ClaimKey(
            identity.policy,
            identity.objective,
            PoisoningSourceStrategy.RANDOM_BENIGN,
            identity.fraction,
        )
        r_unstable = r_instab.get(random_key) is True
        if r_unstable or not g2:
            c_class = ClaimClassification.CALIBRATION_INSTABILITY
        elif g1 and g3:
            c_class = ClaimClassification.FULL_VULNERABILITY
        elif g1:
            c_class = ClaimClassification.MECHANISM_ONLY
        else:
            c_class = ClaimClassification.NULL_OR_CONDITIONAL
        records.append(
            _ClaimGateDecision(
                dataset=identity.dataset,
                policy=identity.policy,
                objective=identity.objective,
                source=identity.source,
                fraction=identity.fraction,
                gate1_pass=g1,
                gate2_pass=g2,
                gate3_pass=g3,
                random_control_unstable=r_unstable,
                claim_class=c_class,
            )
        )
    return records


def _claim_gate_decision_payload(decision: _ClaimGateDecision) -> JsonRecord:
    return {
        "dataset": decision.dataset,
        "policy": decision.policy,
        "objective": decision.objective,
        "source": decision.source,
        "fraction": decision.fraction,
        "gate1_pass": decision.gate1_pass,
        "gate2_pass": decision.gate2_pass,
        "gate3_pass": decision.gate3_pass,
        "random_control_unstable": decision.random_control_unstable,
        "claim_class": decision.claim_class,
    }


_EXTENDED_METRICS: tuple[MetricName, ...] = (
    MetricName.VICTIM_DELTA_TPR,
    MetricName.VICTIM_DELTA_FPR,
    MetricName.VICTIM_DELTA_FN,
    MetricName.VICTIM_DELTA_FP,
    MetricName.VICTIM_DELTA_BA,
    MetricName.VICTIM_DELTA_MACRO_F1,
    MetricName.NONVICTIM_MEAN_DELTA_TPR,
    MetricName.NONVICTIM_WORST_DELTA_TPR,
    MetricName.NONVICTIM_MEAN_DELTA_FPR,
    MetricName.NONVICTIM_WORST_DELTA_FPR,
    MetricName.NONVICTIM_MEAN_DELTA_BA,
    MetricName.NONVICTIM_MEAN_DELTA_MACRO_F1,
    MetricName.NONVICTIM_DELTA_FN_TOTAL,
    MetricName.NONVICTIM_DELTA_FP_TOTAL,
    MetricName.DELTA_MEAN_FPR,
    MetricName.DELTA_CV_FPR,
)

_FIXED_CLUSTER_METRICS: tuple[MetricName, ...] = (
    MetricName.FIXED_CLUSTER_VICTIM_DELTA_TAU,
    MetricName.FIXED_CLUSTER_VICTIM_DELTA_TPR,
    MetricName.FIXED_CLUSTER_VICTIM_DELTA_FPR,
    MetricName.FIXED_CLUSTER_DELTA_CV_FPR,
    MetricName.FIXED_CLUSTER_DELTA_MEAN_FPR,
    MetricName.FIXED_CLUSTER_NONVICTIM_MEAN_DELTA_TPR,
    MetricName.FIXED_CLUSTER_NONVICTIM_MEAN_DELTA_FPR,
)


def _downstream_extended_summary(
    manifest: BoundedSweepManifest, gate: GateParams = DEFAULT_GATE
) -> list[JsonRecord]:
    records: list[JsonRecord] = []
    for (pol, obj, src, frac), rows in sorted(
        _group_rows(r for r in manifest.results if r.fraction > 0.0).items()
    ):
        ctx = _DownstreamContext(
            rows, AttackerObjective(obj), PoisoningSourceStrategy(src)
        )
        metrics = _EXTENDED_METRICS + (
            _FIXED_CLUSTER_METRICS if pol == ThresholdPolicy.CLUSTER_THRESHOLD else ()
        )
        records.extend(
            {
                **_downstream_metric_payload(
                    _downstream_metric_record(
                        manifest.analysis_seeds[0],
                        ctx,
                        m,
                        1.0,
                        SeedAggregationMethod.MEAN,
                        gate,
                    )
                ),
                "dataset": manifest.dataset,
                "policy": pol,
                "fraction": frac,
                "summary_metric": m,
            }
            for m in metrics
        )
    return records


_CLIENT_LEVEL_METRICS: tuple[MetricName, ...] = (
    MetricName.VICTIM_DELTA_TAU,
    MetricName.VICTIM_DELTA_TPR,
    MetricName.VICTIM_DELTA_FPR,
    MetricName.DELTA_CV_FPR,
    MetricName.NONVICTIM_MEAN_DELTA_TPR,
    MetricName.NONVICTIM_MEAN_DELTA_FPR,
)


def _client_level_effects(manifest: BoundedSweepManifest) -> list[JsonRecord]:
    records: list[JsonRecord] = []
    for (pol, obj, src, frac), rows in sorted(
        _group_rows(r for r in manifest.results if r.fraction > 0.0).items()
    ):
        by_victim: defaultdict[RecordKey, list[BoundedSweepResultRow]] = defaultdict(list)
        for r in rows:
            by_victim[r.victim_id].append(r)
        for victim, v_rows in sorted(by_victim.items()):
            record: JsonRecord = {
                "dataset": manifest.dataset,
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


def _cluster_stability_summary(manifest: BoundedSweepManifest) -> list[JsonRecord]:
    records: list[JsonRecord] = []
    for (pol, obj, src, frac), rows in sorted(
        _group_rows(
            r
            for r in manifest.results
            if r.policy == ThresholdPolicy.CLUSTER_THRESHOLD and r.fraction > 0.0
        ).items()
    ):

        records.append(
            {
                "dataset": manifest.dataset,
                "policy": pol,
                "objective": obj,
                "source": src,
                "fraction": frac,
                "n_rows": len(rows),
                "mean_n_reassigned": _finite_mean(r.cluster_n_reassigned for r in rows),
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
                "mean_victim_size_clean": _finite_mean(r.cluster_victim_size_clean for r in rows),
                "mean_victim_size_poisoned": _finite_mean(r.cluster_victim_size_poisoned for r in rows),
                "mean_silhouette_clean": _finite_mean(r.cluster_silhouette_clean for r in rows),
                "mean_silhouette_poisoned": _finite_mean(r.cluster_silhouette_poisoned for r in rows),
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
                "recomputed_victim_delta_tau": _finite_mean(r.cluster_victim_effect for r in rows),
                "fixed_victim_delta_tau": _finite_mean(r.fixed_cluster_victim_delta_tau for r in rows),
                "recomputed_victim_delta_tpr": _finite_mean(r.victim_delta_tpr for r in rows),
                "fixed_victim_delta_tpr": _finite_mean(r.fixed_cluster_victim_delta_tpr for r in rows),
                "recomputed_victim_delta_fpr": _finite_mean(r.victim_delta_fpr for r in rows),
                "fixed_victim_delta_fpr": _finite_mean(r.fixed_cluster_victim_delta_fpr for r in rows),
                "recomputed_delta_cv_fpr": _finite_mean(r.delta_cv_fpr for r in rows),
                "fixed_delta_cv_fpr": _finite_mean(r.fixed_cluster_delta_cv_fpr for r in rows),
                "recomputed_nonvictim_delta_tpr": _finite_mean(r.nonvictim_mean_delta_tpr for r in rows),
                "fixed_nonvictim_delta_tpr": _finite_mean(r.fixed_cluster_nonvictim_mean_delta_tpr for r in rows),
                "recomputed_nonvictim_delta_fpr": _finite_mean(r.nonvictim_mean_delta_fpr for r in rows),
                "fixed_nonvictim_delta_fpr": _finite_mean(r.fixed_cluster_nonvictim_mean_delta_fpr for r in rows),
            }
        )
    return records


def _duplicate_and_bound_summary(manifest: BoundedSweepManifest) -> list[JsonRecord]:
    records: list[JsonRecord] = []
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
                "dataset": manifest.dataset,
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


def _gate_sensitivity_summary(manifest: BoundedSweepManifest) -> list[JsonRecord]:
    default = {
        (r.policy, r.objective, r.source, r.fraction): r.claim_class
        for r in _claim_gate_decisions(manifest, DEFAULT_GATE)
    }
    records: list[JsonRecord] = []
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
        classes = [d.claim_class for d in decisions]
        records.append(
            {
                "dataset": manifest.dataset,
                "sign_consistency": sc,
                "victim_majority": vm,
                "materiality_factor": mf,
                "iqr_floor_factor": fl,
                "n_groups": len(decisions),
                "n_full_vulnerability": classes.count(
                    ClaimClassification.FULL_VULNERABILITY
                ),
                "n_mechanism_only": classes.count(ClaimClassification.MECHANISM_ONLY),
                "n_null_or_conditional": classes.count(
                    ClaimClassification.NULL_OR_CONDITIONAL
                ),
                "n_calibration_instability": classes.count(
                    ClaimClassification.CALIBRATION_INSTABILITY
                ),
                "n_changed_vs_default": sum(
                    d.claim_class
                    != default[(d.policy, d.objective, d.source, d.fraction)]
                    for d in decisions
                ),
            }
        )
    return records


def _manifest_summary(manifest: BoundedSweepManifest) -> JsonRecord:
    return {
        "schema_version": manifest.schema_version,
        "dataset": manifest.dataset,
        "stage": manifest.stage,
        "config_hash": manifest.config_hash,
        "code_commit": manifest.provenance.code_commit,
        "training_seeds": list(manifest.training_seeds),
        "poisoning_seeds": list(manifest.poisoning_seeds),
        "analysis_seeds": list(manifest.analysis_seeds),
        "policies": [p for p in manifest.policies],
        "sources": [s for s in manifest.sources],
        "source_objective_pairs": list(manifest.source_objective_pairs),
        "fractions": list(manifest.fractions),
        "n_reporting_rows": manifest.n_cells,
        "reporting_row_count_semantics": "objective-labeled rows; not independent statistical evidence",
        "artifact_provenance": manifest.artifact_provenance.model_dump(mode="json"),
    }
