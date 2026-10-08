from __future__ import annotations

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

from datp.artifacts import nbaiot_main_manifest_path, sensitivity_manifest_path
from datp.attacks.manifests import (
    BoundedSweepManifest,
    BoundedSweepResultRow,
    SensitivityManifest,
)
from datp.attacks.metrics import materiality_scale
from datp.core import get_logger
from datp.config import (
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
from datp.enums import (
    Workflow,
    AnalysisColumn,
    SYNTHESIZED_DRAWS,
    AnalysisReportStem,
    ArtifactDir,
    AttackerObjective,
    ClaimClassification,
    control_source_for,
    is_random_control,
    DatasetID,
    MetricName,
    PoisoningSourceStrategy,
    ReportTerm,
    SeedAggregationMethod,
    ThresholdPolicy,
)
from datp.reporting.figures import METRIC_DEFINITIONS, RobustnessCell
from datp.statistics import (
    binomial_greater_p_value,
    bootstrap_ci,
    count_of,
    iqr,
    mean_of,
    median_of,
    nanmean_of,
    sign_flip_p_value,
    std_of,
)
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

T = TypeVar("T")
K = TypeVar("K", bound=Hashable)

logger = get_logger(__name__)


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
    random_control_unstable_directional: bool
    claim_class: ClaimClassification
    claim_class_absolute: ClaimClassification
    cluster_fixed_gate1_pass: bool | None


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
    directional_count: SampleCount
    directional_unstable: bool


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
        AnalysisColumn.DATASET: identity.dataset,
        AnalysisColumn.POLICY: identity.policy,
        AnalysisColumn.OBJECTIVE: identity.objective,
        AnalysisColumn.SOURCE: identity.source,
        AnalysisColumn.FRACTION: identity.fraction,
    }


def _bootstrap_summary_payload(summary: _BootstrapSummary) -> JsonRecord:
    return {
        AnalysisColumn.BOOTSTRAP_CI_LOWER: summary.ci_lower,
        AnalysisColumn.BOOTSTRAP_CI_UPPER: summary.ci_upper,
        AnalysisColumn.BOOTSTRAP_MEAN: summary.mean,
        AnalysisColumn.BOOTSTRAP_N_SEED_AGGREGATES: summary.seed_aggregates,
    }


def _exact_support_payload(summary: _ExactSupportSummary) -> JsonRecord:
    return {
        AnalysisColumn.EXACT_SUPPORT_COUNT: summary.support_count,
        AnalysisColumn.EXACT_SUPPORT_N: summary.seed_count,
        AnalysisColumn.EXACT_BINOMIAL_P: summary.binomial_p,
    }


def _threshold_shift_payload(summary: _ThresholdShiftSummary) -> JsonRecord:
    return {
        **_summary_identity_payload(summary.identity),
        AnalysisColumn.CLAIM_BEARING: summary.claim_bearing,
        AnalysisColumn.MEAN_DELTA_TAU: summary.mean_delta_tau,
        AnalysisColumn.MEDIAN_DELTA_TAU: summary.median_delta_tau,
        AnalysisColumn.IQR_DELTA_TAU: summary.iqr_delta_tau,
        AnalysisColumn.MATERIAL_SIGNED_RATE: summary.material_signed_rate,
        AnalysisColumn.SEED_SIGN_COUNT: summary.seed_sign_count,
        AnalysisColumn.VICTIM_MAJORITY_COUNT: summary.victim_majority_count,
        **_bootstrap_summary_payload(summary.bootstrap),
        **_exact_support_payload(summary.exact_support),
    }


def _directional_excess_payload(summary: _DirectionalExcessSummary) -> JsonRecord:
    return {
        **_summary_identity_payload(summary.identity),
        AnalysisColumn.CONTROL_SOURCE: summary.control_source,
        AnalysisColumn.CONTROL_OBJECTIVE: summary.control_objective,
        AnalysisColumn.DIRECTIONAL_EXCESS_SEED_SUPPORT: summary.seed_support,
        AnalysisColumn.MEDIAN_DIRECTIONAL_EXCESS: summary.median_excess,
        AnalysisColumn.MEAN_DIRECTIONAL_EXCESS: summary.mean_excess,
        AnalysisColumn.PER_SEED_DIRECTIONAL_EXCESS: {
            str(seed): value for seed, value in summary.per_seed_excess.items()
        },
        AnalysisColumn.PERMUTATION_P: summary.permutation_p,
        AnalysisColumn.GATE2_PASS: summary.gate_pass,
        **_bootstrap_summary_payload(summary.bootstrap),
        **_exact_support_payload(summary.exact_support),
    }


def _random_instability_payload(summary: _RandomInstabilitySummary) -> JsonRecord:
    return {
        **_summary_identity_payload(summary.identity),
        AnalysisColumn.RANDOM_CONTROL_INSTABILITY_COUNT: summary.instability_count,
        AnalysisColumn.RANDOM_CONTROL_UNSTABLE: summary.unstable,
        AnalysisColumn.RANDOM_CONTROL_DIRECTIONAL_COUNT: summary.directional_count,
        AnalysisColumn.RANDOM_CONTROL_UNSTABLE_DIRECTIONAL: summary.directional_unstable,
    }


def _downstream_metric_payload(summary: _DownstreamMetricSummary) -> JsonRecord:
    return {
        AnalysisColumn.METRIC: summary.metric,
        AnalysisColumn.EXPECTED_SIGN_SEED_SUPPORT: summary.seed_support,
        AnalysisColumn.N_SEEDS_NEGATIVE: summary.negative_seed_count,
        AnalysisColumn.MEDIAN_HARM: summary.median_harm,
        AnalysisColumn.MEAN_EFFECT: summary.mean_effect,
        AnalysisColumn.PER_SEED_VALUES: {
            str(seed): value for seed, value in summary.per_seed_values.items()
        },
        AnalysisColumn.PERMUTATION_P: summary.permutation_p,
        AnalysisColumn.GATE3_METRIC_PASS: summary.gate_pass,
        **_bootstrap_summary_payload(summary.bootstrap),
        **_exact_support_payload(summary.exact_support),
    }


def _downstream_harm_payload(summary: _DownstreamHarmSummary) -> JsonRecord:
    return {
        **_summary_identity_payload(summary.identity),
        **_downstream_metric_payload(summary.metric_summary),
        AnalysisColumn.SUMMARY_METRIC: summary.summary_metric,
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
    logger.info("workflow started", workflow=Workflow.POISONING_SUMMARIES)
    manifest = load_poisoning_manifest(base_dir)
    analysis_dir = base_dir / ArtifactDir.ANALYSIS
    analysis_dir.mkdir(parents=True, exist_ok=True)

    grid = _gate_grid_decisions(manifest)
    outputs = [
        (
            AnalysisReportStem.THRESHOLD_SHIFT_SUMMARY,
            [
                _threshold_shift_payload(row)
                for row in _threshold_shift_summary(manifest)
            ],
        ),
        (
            AnalysisReportStem.DIRECTIONAL_EXCESS_OVER_RANDOM,
            [
                _directional_excess_payload(row)
                for row in _directional_excess_summary(manifest)
            ],
        ),
        (
            AnalysisReportStem.RANDOM_CONTROL_INSTABILITY,
            [
                _random_instability_payload(row)
                for row in _random_instability_summary(manifest)
            ],
        ),
        (
            AnalysisReportStem.LEAVE_ONE_VICTIM_OUT_SENSITIVITY,
            _leave_one_victim_out_summary(manifest),
        ),
        (
            AnalysisReportStem.DOWNSTREAM_HARM_RAISING,
            [
                _downstream_harm_payload(row)
                for row in _downstream_raising_summary(manifest)
            ],
        ),
        (
            AnalysisReportStem.DOWNSTREAM_HARM_LOWERING,
            [
                _downstream_harm_payload(row)
                for row in _downstream_lowering_summary(manifest)
            ],
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
        (
            AnalysisReportStem.DOWNSTREAM_EXTENDED,
            _downstream_extended_summary(manifest),
        ),
        (AnalysisReportStem.CLIENT_LEVEL_EFFECTS, _client_level_effects(manifest)),
        (
            AnalysisReportStem.CLUSTER_STABILITY_SUMMARY,
            _cluster_stability_summary(manifest),
        ),
        (
            AnalysisReportStem.DUPLICATE_AND_BOUND_SUMMARY,
            _duplicate_and_bound_summary(manifest),
        ),
        (
            AnalysisReportStem.GATE_SENSITIVITY,
            _gate_sensitivity_summary(manifest, grid),
        ),
        (
            AnalysisReportStem.CLAIM_ROBUSTNESS,
            [
                _claim_robustness_payload(c)
                for c in claim_robustness_cells(manifest, grid)
            ],
        ),
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
    workflow_result = tuple(paths)
    logger.info("workflow completed", workflow=Workflow.POISONING_SUMMARIES)
    return workflow_result


def build_sensitivity_summaries(base_dir: Path) -> tuple[Path, ...]:
    logger.info("workflow started", workflow=Workflow.SENSITIVITY_SUMMARIES)
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
    workflow_result = tuple(
        p for stem, recs in outputs for p in _write_records(analysis_dir, stem, recs)
    )
    logger.info("workflow completed", workflow=Workflow.SENSITIVITY_SUMMARIES)
    return workflow_result


def _group_by(rows: Iterable[T], key: Callable[[T], K]) -> dict[K, list[T]]:
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
        by_cell: defaultdict[tuple[RandomSeed, ClientId], list[ScoreValue]] = (
            defaultdict(list)
        )
        for r in rows:
            by_cell[(r.training_seed, r.victim_id)].append(r.victim_delta_tau)
        init_sd = [std_of(v, ddof=1) for v in by_cell.values() if len(v) > 1]
        records.append(
            {
                AnalysisColumn.SOURCE: src,
                AnalysisColumn.OBJECTIVE: obj,
                AnalysisColumn.FRACTION: frac,
                AnalysisColumn.K: k,
                AnalysisColumn.N_INIT: n_init,
                AnalysisColumn.N_ROWS: len(rows),
                AnalysisColumn.MEAN_VICTIM_DELTA_TAU: _finite_mean(
                    r.victim_delta_tau for r in rows
                ),
                AnalysisColumn.MEAN_FIXED_VICTIM_DELTA_TAU: _finite_mean(
                    r.fixed_victim_delta_tau for r in rows
                ),
                AnalysisColumn.MEAN_INIT_SD_VICTIM_DELTA_TAU: _finite_mean(init_sd),
                AnalysisColumn.VICTIM_SINGLETON_POISONED_RATE: mean_of(
                    [r.victim_size_poisoned == 1 for r in rows]
                ),
                AnalysisColumn.REASSIGNMENT_RATE: mean_of(
                    [r.n_reassigned > 0 for r in rows]
                ),
                AnalysisColumn.MEAN_N_REASSIGNED: mean_of(
                    [r.n_reassigned for r in rows]
                ),
                AnalysisColumn.MEAN_SILHOUETTE_CLEAN: _finite_mean(
                    r.silhouette_clean for r in rows
                ),
                AnalysisColumn.MEAN_SILHOUETTE_POISONED: _finite_mean(
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
                AnalysisColumn.SOURCE: src,
                AnalysisColumn.OBJECTIVE: obj,
                AnalysisColumn.FRACTION: frac,
                AnalysisColumn.N_ROWS: len(rows),
                AnalysisColumn.MEAN_TAU_LOCAL_CV_CLEAN: _finite_mean(
                    r.tau_local_cv_clean for r in rows
                ),
                AnalysisColumn.MEAN_TAU_LOCAL_MAX_MIN_RATIO_CLEAN: _finite_mean(
                    r.tau_local_max_min_ratio_clean for r in rows
                ),
                AnalysisColumn.MEAN_SCORE_SCALE_CV_CLEAN: _finite_mean(
                    r.score_scale_cv_clean for r in rows
                ),
                AnalysisColumn.RAW_GLOBAL_VICTIM_DELTA_TAU: _finite_mean(
                    r.raw_global_victim_delta_tau for r in rows
                ),
                AnalysisColumn.NORMALIZED_GLOBAL_VICTIM_DELTA_TAU: _finite_mean(
                    r.normalized_global_victim_delta_tau for r in rows
                ),
                AnalysisColumn.RAW_GLOBAL_VICTIM_DELTA_FPR: _finite_mean(
                    r.raw_global_victim_delta_fpr for r in rows
                ),
                AnalysisColumn.NORMALIZED_GLOBAL_VICTIM_DELTA_FPR: _finite_mean(
                    r.normalized_global_victim_delta_fpr for r in rows
                ),
                AnalysisColumn.RAW_GLOBAL_CV_FPR_CLEAN: _finite_mean(
                    r.raw_global_cv_fpr_clean for r in rows
                ),
                AnalysisColumn.NORMALIZED_GLOBAL_CV_FPR_CLEAN: _finite_mean(
                    r.normalized_global_cv_fpr_clean for r in rows
                ),
                AnalysisColumn.RAW_GLOBAL_CV_FPR_POISONED: _finite_mean(
                    r.raw_global_cv_fpr_poisoned for r in rows
                ),
                AnalysisColumn.NORMALIZED_GLOBAL_CV_FPR_POISONED: _finite_mean(
                    r.normalized_global_cv_fpr_poisoned for r in rows
                ),
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
                AnalysisColumn.POLICY: pol,
                AnalysisColumn.SOURCE: src,
                AnalysisColumn.OBJECTIVE: obj,
                AnalysisColumn.FRACTION: frac,
                AnalysisColumn.DRAW: draw,
                AnalysisColumn.SYNTHESIZED_VALUES: draw
                in {d for d in SYNTHESIZED_DRAWS},
                AnalysisColumn.N_ROWS: len(rows),
                AnalysisColumn.MEAN_REQUESTED_N_REPLACED: mean_of(
                    [r.requested_n_replaced for r in rows]
                ),
                AnalysisColumn.MEAN_EFFECTIVE_N_REPLACED: mean_of(
                    [r.effective_n_replaced for r in rows]
                ),
                AnalysisColumn.MEAN_POOL_SIZE: mean_of([r.pool_size for r in rows]),
                AnalysisColumn.FULL_BUDGET_FEASIBLE_RATE: mean_of(
                    [r.effective_n_replaced == r.requested_n_replaced for r in rows]
                ),
                AnalysisColumn.MEAN_DELTA_TAU_WITH_REPLACEMENT: base,
                AnalysisColumn.MEAN_DELTA_TAU_VARIANT: variant,
                AnalysisColumn.VARIANT_TO_BASELINE_RATIO: variant / base
                if math.isfinite(base) and base != 0.0
                else math.nan,
                AnalysisColumn.MEAN_DUPLICATE_RATE_WITH_REPLACEMENT: _finite_mean(
                    r.duplicate_rate_with_replacement for r in rows
                ),
                AnalysisColumn.MEAN_DUPLICATE_RATE_VARIANT: _finite_mean(
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
                AnalysisColumn.POLICY: pol,
                AnalysisColumn.SOURCE: src,
                AnalysisColumn.OBJECTIVE: obj,
                AnalysisColumn.FRACTION: frac,
                AnalysisColumn.N_ROWS: len(rows),
                AnalysisColumn.MEAN_DELTA_TAU_UNDEFENDED: undefended,
                AnalysisColumn.MEAN_DELTA_TAU_TRIM_PRIMARY: _finite_mean(
                    r.delta_tau_trim_primary for r in rows
                ),
                AnalysisColumn.MEAN_DELTA_TAU_TRIM_APPENDIX: _finite_mean(
                    r.delta_tau_trim_appendix for r in rows
                ),
                AnalysisColumn.MEAN_RESIDUAL_VS_CLEAN_TRIM_PRIMARY: _finite_mean(
                    r.residual_vs_clean_trim_primary for r in rows
                ),
                AnalysisColumn.MEAN_RESIDUAL_VS_CLEAN_TRIM_APPENDIX: _finite_mean(
                    r.residual_vs_clean_trim_appendix for r in rows
                ),
                AnalysisColumn.MEAN_OVERWRITE_REFERENCE_SHIFT: _finite_mean(
                    r.overwrite_reference_shift for r in rows
                ),
                AnalysisColumn.MEAN_BUFFER_TO_OVERWRITE_RATIO: _finite_mean(
                    r.buffer_to_overwrite_ratio for r in rows
                ),
                AnalysisColumn.TRIM_PRIMARY_REDUCTION: 1.0
                - _finite_mean(r.delta_tau_trim_primary for r in rows) / undefended
                if math.isfinite(undefended) and undefended != 0.0
                else math.nan,
            }
        )
    return records


def load_poisoning_manifest(base_dir: Path) -> BoundedSweepManifest:
    if not (path := nbaiot_main_manifest_path(base_dir)).exists():
        raise FileNotFoundError(f"Missing bounded sweep manifest: {path}")
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
                handle,
                fieldnames=sorted({k for r in records for k in r}),
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(records)
    logger.debug("analysis records written", stem=stem, record_count=len(records))
    return [json_path, csv_path]


def _group_rows(
    rows: Iterable[BoundedSweepResultRow],
) -> dict[
    tuple[ThresholdPolicy, AttackerObjective, PoisoningSourceStrategy, PoisonFraction],
    list[BoundedSweepResultRow],
]:
    grouped: defaultdict[
        tuple[
            ThresholdPolicy, AttackerObjective, PoisoningSourceStrategy, PoisonFraction
        ],
        list[BoundedSweepResultRow],
    ] = defaultdict(list)
    for r in rows:
        grouped[(r.policy, r.objective, r.source, r.fraction)].append(r)
    return dict(grouped)


def _seed_values(
    rows: Iterable[BoundedSweepResultRow], transform: ScoreValue = 1.0
) -> dict[RandomSeed, ScoreValue]:
    by_seed: defaultdict[RandomSeed, list[ScoreValue]] = defaultdict(list)
    for r in rows:
        if math.isfinite(v := r.delta_tau):
            by_seed[r.training_seed].append(transform * v)
    return {s: mean_of(vals) for s, vals in sorted(by_seed.items()) if vals}


def _support_count(seed_values: dict[RandomSeed, ScoreValue]) -> SampleCount:
    return sum(1 for v in seed_values.values() if math.isfinite(v) and v > 0.0)


def _finite_mean(values: Iterable[ScoreValue]) -> ScoreValue:
    return mean_of(f) if (f := [v for v in values if math.isfinite(v)]) else math.nan


def _median(values: Iterable[ScoreValue]) -> ScoreValue:
    return median_of(f) if (f := [v for v in values if math.isfinite(v)]) else math.nan


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
    return _BootstrapSummary(res.ci_lower, res.ci_upper, res.mean_delta, res.n_seeds)


def _exact_support(
    seed_support: SignedCount, n_seeds: SeedCount
) -> _ExactSupportSummary:
    return _ExactSupportSummary(
        seed_support,
        n_seeds,
        binomial_greater_p_value(seed_support, n_seeds) if n_seeds else math.nan,
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


def _fixed_assignment_gate1(
    rows: list[BoundedSweepResultRow], gate: GateParams
) -> bool:
    by_seed: defaultdict[RandomSeed, list[BoundedSweepResultRow]] = defaultdict(list)
    for r in rows:
        by_seed[r.training_seed].append(r)
    supported = 0
    for seed_rows in by_seed.values():
        sign = (
            1.0 if seed_rows[0].objective == AttackerObjective.THRESHOLD_RAISE else -1.0
        )
        shifts = [(sign * r.fixed_cluster_victim_delta_tau, r) for r in seed_rows]
        material = sum(
            1
            for shift, r in shifts
            if math.isfinite(shift)
            and shift
            >= materiality_scale(
                r.victim_delta_tau_scale_base,
                r.iqr_median_clean,
                gate.materiality_factor,
                gate.iqr_floor_factor,
            )
        )
        mean_shift = _finite_mean(shift for shift, _ in shifts)
        supported += material >= gate.victim_majority and mean_shift > 0.0
    return supported >= gate.sign_consistency


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
                claim_bearing=frac > 0.0 and not is_random_control(src),
                mean_delta_tau=mean_of([r.delta_tau for r in rows]),
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
    return {s: mean_of(v) for s, v in sorted(bucket.items())}


def _directional_excess_summary(
    manifest: BoundedSweepManifest, gate: GateParams = DEFAULT_GATE
) -> list[_DirectionalExcessSummary]:
    records: list[_DirectionalExcessSummary] = []
    for obj, src_tgt, control_source in [
        (
            AttackerObjective.THRESHOLD_RAISE,
            PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            PoisoningSourceStrategy.RANDOM_BENIGN,
        ),
        (
            AttackerObjective.THRESHOLD_LOWER,
            PoisoningSourceStrategy.LOW_SCORE_BENIGN,
            PoisoningSourceStrategy.RANDOM_BENIGN,
        ),
        (
            AttackerObjective.THRESHOLD_RAISE,
            PoisoningSourceStrategy.HIGH_SCORE_TRAIN_FEATURE_BENIGN,
            PoisoningSourceStrategy.RANDOM_TRAIN_FEATURE_BENIGN,
        ),
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
            if r.objective == obj and r.source == control_source
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
                    control_source=control_source,
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
            directional_count=(dcnt := _victim_majority_count(rows, False, gate)),
            directional_unstable=dcnt >= gate.sign_consistency,
        )
        for (pol, obj, src, frac), rows in sorted(_group_rows(manifest.results).items())
        if is_random_control(src)
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
                AnalysisColumn.DATASET: manifest.dataset,
                AnalysisColumn.POLICY: pol,
                AnalysisColumn.OBJECTIVE: obj,
                AnalysisColumn.SOURCE: src,
                AnalysisColumn.FRACTION: frac,
                AnalysisColumn.LEAVE_ONE_VICTIM_OUT_MIN: min(excl_means),
                AnalysisColumn.LEAVE_ONE_VICTIM_OUT_MEDIAN: _median(excl_means),
                AnalysisColumn.LEAVE_ONE_VICTIM_OUT_MAX: max(excl_means),
                AnalysisColumn.SIGN_STABLE_EXCLUSIONS: stable,
                AnalysisColumn.N_EXCLUSIONS: len(victims),
            }
        )
    return records


def _victim_metric_value(
    row: BoundedSweepResultRow, metric: MetricName
) -> ScoreValue | None:
    match metric:
        case MetricName.VICTIM_DELTA_FP:
            return row.victim_fp_poisoned - row.victim_fp_clean
        case MetricName.VICTIM_DELTA_FN:
            return row.victim_fn_poisoned - row.victim_fn_clean
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
        s: max(v) if aggregation is SeedAggregationMethod.MAXIMUM else mean_of(v)
        for s, v in by_seed.items()
    }
    arr = np.array(list(s_vals.values()), dtype=np.float64)
    support_count = _support_count(s_vals)
    return _DownstreamMetricSummary(
        metric=metric,
        seed_support=support_count,
        negative_seed_count=count_of(arr < 0.0),
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
                and not is_random_control(r.source)
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
                and not is_random_control(r.source)
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
            AnalysisColumn.DATASET: manifest.dataset,
            AnalysisColumn.POLICY: pol,
            AnalysisColumn.OBJECTIVE: obj,
            AnalysisColumn.SOURCE: src,
            AnalysisColumn.FRACTION: frac,
            AnalysisColumn.CLUSTER_CHURN: nanmean_of(
                [r.cluster_delta_tau_churn for r in rows]
            ),
            AnalysisColumn.SPILLOVER_COUNT: nanmean_of([r.n_spillover for r in rows]),
            AnalysisColumn.VICTIM_EFFECT: nanmean_of(
                [r.cluster_victim_effect for r in rows]
            ),
            AnalysisColumn.NON_VICTIM_EFFECT: nanmean_of(
                [r.cluster_non_victim_effect for r in rows]
            ),
            AnalysisColumn.FROZEN_SCALER_EFFECT: nanmean_of(
                [r.cluster_delta_tau_frozen_scaler for r in rows]
            ),
            AnalysisColumn.REFIT_MINUS_FROZEN_SCALER: nanmean_of(
                [r.cluster_delta_tau_normalization_gap for r in rows]
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


def _classify_claim(
    control_unstable: bool, g1: bool, g2: bool, g3: bool
) -> ClaimClassification:
    if control_unstable or not g2:
        return ClaimClassification.CALIBRATION_INSTABILITY
    if g1 and g3:
        return ClaimClassification.FULL_VULNERABILITY
    if g1:
        return ClaimClassification.MECHANISM_ONLY
    return ClaimClassification.NULL_OR_CONDITIONAL


def _claim_gate_decisions(
    manifest: BoundedSweepManifest, gate: GateParams = DEFAULT_GATE
) -> list[_ClaimGateDecision]:
    excess = {
        _claim_key(r.identity): r.gate_pass
        for r in _directional_excess_summary(manifest, gate)
    }
    instability = _random_instability_summary(manifest, gate)
    r_instab = {_claim_key(r.identity): r.unstable for r in instability}
    r_instab_directional = {
        _claim_key(r.identity): r.directional_unstable for r in instability
    }
    d_pass: defaultdict[_ClaimKey, bool] = defaultdict(bool)
    for r in _downstream_raising_summary(manifest, gate) + _downstream_lowering_summary(
        manifest, gate
    ):
        d_pass[_claim_key(r.identity)] |= r.metric_summary.gate_pass

    grouped = _group_rows(manifest.results)
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
        control = control_source_for(identity.source)
        control_key = (
            _ClaimKey(identity.policy, identity.objective, control, identity.fraction)
            if control is not None
            else None
        )
        r_unstable = control_key is not None and r_instab.get(control_key) is True
        r_unstable_directional = (
            control_key is not None and r_instab_directional.get(control_key) is True
        )
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
                random_control_unstable_directional=r_unstable_directional,
                claim_class=_classify_claim(r_unstable_directional, g1, g2, g3),
                claim_class_absolute=_classify_claim(r_unstable, g1, g2, g3),
                cluster_fixed_gate1_pass=(
                    _fixed_assignment_gate1(
                        grouped[
                            (
                                identity.policy,
                                identity.objective,
                                identity.source,
                                identity.fraction,
                            )
                        ],
                        gate,
                    )
                    if identity.policy == ThresholdPolicy.CLUSTER_THRESHOLD
                    else None
                ),
            )
        )
    return records


def _claim_gate_decision_payload(decision: _ClaimGateDecision) -> JsonRecord:
    return {
        AnalysisColumn.DATASET: decision.dataset,
        AnalysisColumn.POLICY: decision.policy,
        AnalysisColumn.OBJECTIVE: decision.objective,
        AnalysisColumn.SOURCE: decision.source,
        AnalysisColumn.FRACTION: decision.fraction,
        AnalysisColumn.GATE1_PASS: decision.gate1_pass,
        AnalysisColumn.GATE2_PASS: decision.gate2_pass,
        AnalysisColumn.GATE3_PASS: decision.gate3_pass,
        AnalysisColumn.RANDOM_CONTROL_UNSTABLE: decision.random_control_unstable,
        AnalysisColumn.RANDOM_CONTROL_UNSTABLE_DIRECTIONAL: (
            decision.random_control_unstable_directional
        ),
        AnalysisColumn.CLAIM_CLASS: decision.claim_class,
        AnalysisColumn.CLAIM_CLASS_ABSOLUTE: decision.claim_class_absolute,
        AnalysisColumn.CLUSTER_FIXED_GATE1_PASS: decision.cluster_fixed_gate1_pass,
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
                AnalysisColumn.DATASET: manifest.dataset,
                AnalysisColumn.POLICY: pol,
                AnalysisColumn.FRACTION: frac,
                AnalysisColumn.SUMMARY_METRIC: m,
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
        by_victim: defaultdict[RecordKey, list[BoundedSweepResultRow]] = defaultdict(
            list
        )
        for r in rows:
            by_victim[r.victim_id].append(r)
        for victim, v_rows in sorted(by_victim.items()):
            record: JsonRecord = {
                AnalysisColumn.DATASET: manifest.dataset,
                AnalysisColumn.POLICY: pol,
                AnalysisColumn.OBJECTIVE: obj,
                AnalysisColumn.SOURCE: src,
                AnalysisColumn.FRACTION: frac,
                AnalysisColumn.VICTIM_ID: victim,
                AnalysisColumn.N_SEEDS: len({r.training_seed for r in v_rows}),
            }
            for m in _CLIENT_LEVEL_METRICS:
                vals = [v for r in v_rows if math.isfinite(v := _metric_value(r, m))]
                record[f"{m}_mean"] = mean_of(vals) if vals else math.nan
                record[f"{m}_std"] = std_of(vals, ddof=1) if len(vals) > 1 else math.nan
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
                AnalysisColumn.DATASET: manifest.dataset,
                AnalysisColumn.POLICY: pol,
                AnalysisColumn.OBJECTIVE: obj,
                AnalysisColumn.SOURCE: src,
                AnalysisColumn.FRACTION: frac,
                AnalysisColumn.N_ROWS: len(rows),
                AnalysisColumn.MEAN_N_REASSIGNED: _finite_mean(
                    r.cluster_n_reassigned for r in rows
                ),
                AnalysisColumn.MAX_N_REASSIGNED: max(
                    r.cluster_n_reassigned for r in rows
                ),
                AnalysisColumn.REASSIGNMENT_RATE: mean_of(
                    [r.cluster_n_reassigned > 0 for r in rows]
                ),
                AnalysisColumn.VICTIM_SINGLETON_CLEAN_RATE: mean_of(
                    [r.cluster_victim_size_clean == 1 for r in rows]
                ),
                AnalysisColumn.VICTIM_SINGLETON_POISONED_RATE: mean_of(
                    [r.cluster_victim_size_poisoned == 1 for r in rows]
                ),
                AnalysisColumn.MEAN_VICTIM_SIZE_CLEAN: _finite_mean(
                    r.cluster_victim_size_clean for r in rows
                ),
                AnalysisColumn.MEAN_VICTIM_SIZE_POISONED: _finite_mean(
                    r.cluster_victim_size_poisoned for r in rows
                ),
                AnalysisColumn.MEAN_SILHOUETTE_CLEAN: _finite_mean(
                    r.cluster_silhouette_clean for r in rows
                ),
                AnalysisColumn.MEAN_SILHOUETTE_POISONED: _finite_mean(
                    r.cluster_silhouette_poisoned for r in rows
                ),
                AnalysisColumn.MODAL_SIZES_CLEAN: list(
                    max(
                        {r.cluster_sizes_clean for r in rows},
                        key=[r.cluster_sizes_clean for r in rows].count,
                    )
                ),
                AnalysisColumn.MODAL_SIZES_POISONED: list(
                    max(
                        {r.cluster_sizes_poisoned for r in rows},
                        key=[r.cluster_sizes_poisoned for r in rows].count,
                    )
                ),
                AnalysisColumn.RECOMPUTED_VICTIM_DELTA_TAU: _finite_mean(
                    r.cluster_victim_effect for r in rows
                ),
                AnalysisColumn.FIXED_VICTIM_DELTA_TAU: _finite_mean(
                    r.fixed_cluster_victim_delta_tau for r in rows
                ),
                AnalysisColumn.RECOMPUTED_VICTIM_DELTA_TPR: _finite_mean(
                    r.victim_delta_tpr for r in rows
                ),
                AnalysisColumn.FIXED_VICTIM_DELTA_TPR: _finite_mean(
                    r.fixed_cluster_victim_delta_tpr for r in rows
                ),
                AnalysisColumn.RECOMPUTED_VICTIM_DELTA_FPR: _finite_mean(
                    r.victim_delta_fpr for r in rows
                ),
                AnalysisColumn.FIXED_VICTIM_DELTA_FPR: _finite_mean(
                    r.fixed_cluster_victim_delta_fpr for r in rows
                ),
                AnalysisColumn.RECOMPUTED_DELTA_CV_FPR: _finite_mean(
                    r.delta_cv_fpr for r in rows
                ),
                AnalysisColumn.FIXED_DELTA_CV_FPR: _finite_mean(
                    r.fixed_cluster_delta_cv_fpr for r in rows
                ),
                AnalysisColumn.RECOMPUTED_NONVICTIM_DELTA_TPR: _finite_mean(
                    r.nonvictim_mean_delta_tpr for r in rows
                ),
                AnalysisColumn.FIXED_NONVICTIM_DELTA_TPR: _finite_mean(
                    r.fixed_cluster_nonvictim_mean_delta_tpr for r in rows
                ),
                AnalysisColumn.RECOMPUTED_NONVICTIM_DELTA_FPR: _finite_mean(
                    r.nonvictim_mean_delta_fpr for r in rows
                ),
                AnalysisColumn.FIXED_NONVICTIM_DELTA_FPR: _finite_mean(
                    r.fixed_cluster_nonvictim_mean_delta_fpr for r in rows
                ),
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
                AnalysisColumn.DATASET: manifest.dataset,
                AnalysisColumn.POLICY: pol,
                AnalysisColumn.OBJECTIVE: obj,
                AnalysisColumn.SOURCE: src,
                AnalysisColumn.FRACTION: frac,
                AnalysisColumn.MEAN_N_REPLACED: mean_of([r.n_replaced for r in rows]),
                AnalysisColumn.MEAN_DUPLICATE_RATE_CLEAN: _finite_mean(
                    r.cal_duplicate_rate_clean for r in rows
                ),
                AnalysisColumn.MEAN_DUPLICATE_RATE_POISONED: _finite_mean(
                    r.cal_duplicate_rate_poisoned for r in rows
                ),
                AnalysisColumn.MEAN_BOUND_UTILIZATION: mean_of(bound)
                if bound
                else math.nan,
                AnalysisColumn.MAX_BOUND_UTILIZATION: max(bound) if bound else math.nan,
            }
        )
    return records


@dataclass(frozen=True, slots=True)
class _GateGridPoint:
    gate: GateParams
    decisions: list[_ClaimGateDecision]


def _gate_grid_decisions(manifest: BoundedSweepManifest) -> list[_GateGridPoint]:
    return [
        _GateGridPoint(gate, _claim_gate_decisions(manifest, gate))
        for gate in (
            GateParams(
                sign_consistency=sc,
                victim_majority=vm,
                materiality_factor=mf,
                iqr_floor_factor=fl,
            )
            for sc, vm, mf, fl in product(
                SENSITIVITY_SIGN_CONSISTENCY_GRID,
                SENSITIVITY_VICTIM_MAJORITY_GRID,
                SENSITIVITY_MATERIALITY_GRID,
                SENSITIVITY_IQR_FLOOR_GRID,
            )
        )
    ]


def _gate_sensitivity_summary(
    manifest: BoundedSweepManifest, grid: list[_GateGridPoint]
) -> list[JsonRecord]:
    default = {
        (r.policy, r.objective, r.source, r.fraction): r.claim_class
        for r in _claim_gate_decisions(manifest, DEFAULT_GATE)
    }
    records: list[JsonRecord] = []
    for point in grid:
        gate, decisions = point.gate, point.decisions
        classes = [d.claim_class for d in decisions]
        records.append(
            {
                AnalysisColumn.DATASET: manifest.dataset,
                AnalysisColumn.SIGN_CONSISTENCY: gate.sign_consistency,
                AnalysisColumn.VICTIM_MAJORITY: gate.victim_majority,
                AnalysisColumn.MATERIALITY_FACTOR: gate.materiality_factor,
                AnalysisColumn.IQR_FLOOR_FACTOR: gate.iqr_floor_factor,
                AnalysisColumn.N_GROUPS: len(decisions),
                AnalysisColumn.N_FULL_VULNERABILITY: classes.count(
                    ClaimClassification.FULL_VULNERABILITY
                ),
                AnalysisColumn.N_MECHANISM_ONLY: classes.count(
                    ClaimClassification.MECHANISM_ONLY
                ),
                AnalysisColumn.N_NULL_OR_CONDITIONAL: classes.count(
                    ClaimClassification.NULL_OR_CONDITIONAL
                ),
                AnalysisColumn.N_CALIBRATION_INSTABILITY: classes.count(
                    ClaimClassification.CALIBRATION_INSTABILITY
                ),
                AnalysisColumn.N_CHANGED_VS_DEFAULT: sum(
                    d.claim_class
                    != default[(d.policy, d.objective, d.source, d.fraction)]
                    for d in decisions
                ),
            }
        )
    return records


def claim_robustness_cells(
    manifest: BoundedSweepManifest, grid: list[_GateGridPoint] | None = None
) -> list[RobustnessCell]:
    grid = grid if grid is not None else _gate_grid_decisions(manifest)
    labels: defaultdict[
        tuple[
            ThresholdPolicy, AttackerObjective, PoisoningSourceStrategy, PoisonFraction
        ],
        list[_ClaimGateDecision],
    ] = defaultdict(list)
    for point in grid:
        for d in point.decisions:
            labels[(d.policy, d.objective, d.source, d.fraction)].append(d)
    full = ClaimClassification.FULL_VULNERABILITY
    return [
        RobustnessCell(
            source=source,
            policy=policy,
            fraction=fraction,
            primary=sum(d.claim_class == full for d in ds) / len(ds),
            absolute=sum(d.claim_class_absolute == full for d in ds) / len(ds),
        )
        for (policy, _, source, fraction), ds in sorted(labels.items())
    ]


def _claim_robustness_payload(cell: RobustnessCell) -> JsonRecord:
    return {
        AnalysisColumn.POLICY: cell.policy,
        AnalysisColumn.SOURCE: cell.source,
        AnalysisColumn.FRACTION: cell.fraction,
        AnalysisColumn.SHARE_FULL_VULNERABILITY: cell.primary,
        AnalysisColumn.SHARE_FULL_VULNERABILITY_ABSOLUTE_CONTROL_GATE: cell.absolute,
    }


def _manifest_summary(manifest: BoundedSweepManifest) -> JsonRecord:
    return {
        AnalysisColumn.SCHEMA_VERSION: manifest.schema_version,
        AnalysisColumn.DATASET: manifest.dataset,
        AnalysisColumn.STAGE: manifest.stage,
        AnalysisColumn.CONFIG_HASH: manifest.config_hash,
        AnalysisColumn.CODE_COMMIT: manifest.provenance.code_commit,
        AnalysisColumn.TRAINING_SEEDS: list(manifest.training_seeds),
        AnalysisColumn.POISONING_SEEDS: list(manifest.poisoning_seeds),
        AnalysisColumn.ANALYSIS_SEEDS: list(manifest.analysis_seeds),
        AnalysisColumn.POLICIES: [p for p in manifest.policies],
        AnalysisColumn.SOURCES: [s for s in manifest.sources],
        AnalysisColumn.SOURCE_OBJECTIVE_PAIRS: list(manifest.source_objective_pairs),
        AnalysisColumn.FRACTIONS: list(manifest.fractions),
        AnalysisColumn.N_REPORTING_ROWS: manifest.n_cells,
        AnalysisColumn.REPORTING_ROW_COUNT_SEMANTICS: "objective-labeled rows; not independent statistical evidence",
        AnalysisColumn.ARTIFACT_PROVENANCE: manifest.artifact_provenance.model_dump(
            mode="json"
        ),
    }
