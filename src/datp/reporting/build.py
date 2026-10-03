from __future__ import annotations

import csv
import json
import math
import shutil
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

import numpy as np

from datp.artifacts import (
    ArtifactLayout,
    nbaiot_main_manifest_path,
    sensitivity_manifest_path,
    write_json_atomic,
)
from datp.attacks.manifests import BoundedSweepResultRow
from datp.config import DatpConfig, ExperimentStage, write_resolved_config
from datp.core import ClientThreshold, PolicyRunId, TrainingCellId, get_logger
from datp.enums import (
    CONTROLLED_POLICIES,
    ArtifactDir,
    ArtifactFile,
    AttackerObjective,
    AuditDir,
    AuditField,
    AuditStatus,
    ClientStatus,
    ComparisonLabel,
    DatasetID,
    EvidenceRole,
    FigureName,
    HeterogeneityContextResult,
    MetricName,
    PackageDir,
    PathToken,
    PayloadKey,
    PoisoningSourceStrategy,
    RunKind,
    ScoringStage,
    SeedScope,
    SidecarField,
    ThresholdPolicy,
    ValidationField,
)
from datp.evaluation import (
    ClientEvaluationRecord,
    ConfusionCounts,
    EvaluationResult,
    build_evaluation_result,
    recompute_binary_metrics,
)
from datp.reporting.figures import (
    CLIENT_SELECTION_RULE,
    NOT_CONFIRMATORY_WARNING,
    POISONING_FIGURE_FRACTION,
    REPORTING_AUDIT_SCHEMA_VERSION,
    SEED_SELECTION_RULE,
    generate_figure1,
    generate_figure2,
    generate_figure3,
    generate_figure5,
    generate_figure6,
    generate_table3,
)
from datp.reporting.poisoning import (
    build_poisoning_summaries,
    build_sensitivity_summaries,
    load_poisoning_manifest,
)
from datp.scoring import ScoreProvider, ScoringColumn
from datp.statistics import BootstrapField, BootstrapReport, StatsField, bootstrap_ci
from datp.thresholding import SweepMetrics
from datp.types import (
    BootstrapCount,
    ClientId,
    FalsePositiveRate,
    IntervalBound,
    JsonRecord,
    JsonValue,
    NarrativeText,
    RandomSeed,
    ScoreValue,
    ScoreVector,
    SignedCount,
    Threshold,
    Tolerance,
)
from datp.validation import AuditOutputPaths, run_results_audit

_REPORTING_SOURCES: set[NarrativeText] = set()


_REPRESENTATIVE_SEED_FIGURES: frozenset[NarrativeText] = frozenset(
    {FigureName.FIGURE_1, FigureName.FIGURE_2}
)


def _result_path(
    base_dir: Path, stage: ExperimentStage, policy: ThresholdPolicy, seed: RandomSeed
) -> Path:
    return (
        ArtifactLayout(base_dir=base_dir, stage=stage)
        .policy_run(
            PolicyRunId(
                cell=TrainingCellId(stage=stage, seed=seed), policy=policy
            )
        )
        .result_dir
        / ArtifactFile.METRICS
    )


def _load_json(path: Path) -> SweepMetrics:
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}")
    payload = SweepMetrics.model_validate_json(path.read_text())
    if payload.run_kind is not RunKind.CORE_LADDER:
        raise ValueError(f"RunKind separation violation: {path}")
    _REPORTING_SOURCES.add(path.as_posix())
    return payload


def _client_records_from_payload(
    payload: SweepMetrics,
) -> tuple[ClientEvaluationRecord, ...]:
    records: list[ClientEvaluationRecord] = []
    for row in payload.per_client:
        client_id = row.client_id
        confusion = row.confusion_matrix
        tp, fp, tn, fn = confusion.tp, confusion.fp, confusion.tn, confusion.fn
        if row.n_benign != fp + tn:
            raise ValueError(f"Benign denominator mismatch for {client_id}.")
        if row.n_attack != tp + fn:
            raise ValueError(f"Attack denominator mismatch for {client_id}.")

        records.append(
            ClientEvaluationRecord(
                client_id=client_id,
                metrics=recompute_binary_metrics(tp, fp, tn, fn),
                confusion=ConfusionCounts(tp=tp, fp=fp, tn=tn, fn=fn),
                n_benign=fp + tn,
                n_attack=tp + fn,
                threshold=ClientThreshold(
                    client_id=client_id,
                    threshold=row.threshold_value,
                    status=(
                        ClientStatus.CALIBRATION_PENDING
                        if row.calibration_pending
                        else ClientStatus.ELIGIBLE
                    ),
                    strategy=payload.policy,
                ),
                evaluation_incomplete=row.evaluation_incomplete,
            )
        )
    return tuple(records)


def _assert_metric_matches(
    key: MetricName | PayloadKey,
    saved: ScoreValue | None,
    value: ScoreValue,
    tol: Tolerance,
) -> None:
    if saved is None:
        raise ValueError(f"Metric schema mismatch: required saved metric {key} is missing")
    if np.isnan(saved) and np.isnan(value):
        return
    if np.isnan(saved) != np.isnan(value) or abs(saved - value) > tol:
        raise ValueError(f"Metric schema mismatch: {key}={value} vs {saved}")


def _evaluation_from_payload(
    payload: SweepMetrics, metric_tol: Tolerance
) -> EvaluationResult:
    result = build_evaluation_result(
        policy=payload.policy,
        stage=payload.stage,
        seed=payload.seed,
        clients=_client_records_from_payload(payload),
        eligible_ids=payload.eligible_ids,
        pending_ids=payload.pending_ids,
        incomplete_ids=payload.eval_incomplete_ids,
    )
    _assert_metric_matches(
        PayloadKey.COVERAGE_RATIO,
        payload.coverage_ratio,
        result.coverage_ratio,
        metric_tol,
    )
    _assert_metric_matches(MetricName.CV_FPR, payload.cv_fpr, result.dispersion.cv_fpr, metric_tol)
    _assert_metric_matches(MetricName.MEAN_FPR, payload.mean_fpr, result.dispersion.mean_fpr, metric_tol)
    _assert_metric_matches(MetricName.STD_FPR, payload.std_fpr, result.dispersion.std_fpr, metric_tol)
    _assert_metric_matches(MetricName.CV_TPR, payload.cv_tpr, result.dispersion.cv_tpr, metric_tol)
    _assert_metric_matches(MetricName.IQR_FPR, payload.iqr_fpr, result.dispersion.iqr_fpr, metric_tol)
    _assert_metric_matches(MetricName.IQR_TPR, payload.iqr_tpr, result.dispersion.iqr_tpr, metric_tol)
    _assert_metric_matches(
        MetricName.WORST_CLIENT_FPR,
        payload.worst_client_fpr,
        result.dispersion.worst_client_fpr,
        metric_tol,
    )
    _assert_metric_matches(MetricName.WORST_BA, payload.worst_ba, result.dispersion.worst_ba, metric_tol)
    _assert_metric_matches(
        MetricName.P10_MACRO_F1,
        payload.p10_macro_f1,
        result.dispersion.p10_macro_f1,
        metric_tol,
    )
    if payload.eligible_count != result.dispersion.eligible_count:
        raise ValueError("Eligibility count mismatch")
    if payload.client_count != result.dispersion.client_count:
        raise ValueError("Client count mismatch")
    return result


def _load_results(
    base_dir: Path,
    stage: ExperimentStage,
    policies: tuple[ThresholdPolicy, ...],
    seeds: tuple[RandomSeed, ...],
    tol: Tolerance,
) -> dict[ThresholdPolicy, list[EvaluationResult]]:
    return {
        p: [
            _evaluation_from_payload(
                _load_json(_result_path(base_dir, stage, p, s)), tol
            )
            for s in seeds
        ]
        for p in policies
    }


def _eligible_fprs(result: EvaluationResult) -> dict[ClientId, FalsePositiveRate]:
    el = set(result.eligible_ids)
    return {c.client_id: c.metrics.fpr for c in result.clients if c.client_id in el}


def _eligible_intersection_fprs(
    left: EvaluationResult, right: EvaluationResult
) -> tuple[ScoreVector, ScoreVector, list[ClientId]]:
    l_map, r_map = _eligible_fprs(left), _eligible_fprs(right)
    if not (ids := sorted(set(l_map) & set(r_map))):
        raise ValueError("No eligible-client intersection")
    if set(l_map) - set(ids) or set(r_map) - set(ids):
        raise ValueError("Eligible-client set mismatch")
    return (
        np.array([l_map[c] for c in ids], dtype=np.float64),
        np.array([r_map[c] for c in ids], dtype=np.float64),
        ids,
    )


def _bootstrap_payload(
    deltas: ScoreVector, n_bootstrap: BootstrapCount, ci: IntervalBound, seed: RandomSeed
) -> BootstrapReport:
    return BootstrapReport(
        result=bootstrap_ci(deltas, n_bootstrap=n_bootstrap, ci=ci, seed=seed),
        confidence_level=ci,
        per_seed_deltas=tuple(float(value) for value in deltas),
    )


def _paired_deltas(
    results: dict[ThresholdPolicy, list[EvaluationResult]],
    left: ThresholdPolicy,
    right: ThresholdPolicy,
) -> ScoreVector:
    return np.array(
        [
            results[left][i].dispersion.cv_fpr
            - results[right][i].dispersion.cv_fpr
            for i in range(len(results[left]))
        ]
    )


def _common_eligible_fprs(
    results: dict[ThresholdPolicy, list[EvaluationResult]],
    policies: tuple[ThresholdPolicy, ...],
) -> dict[ThresholdPolicy, list[ScoreVector]]:
    out: dict[ThresholdPolicy, list[ScoreVector]] = {p: [] for p in policies}
    for i in range(len(results[policies[0]])):
        maps = {p: _eligible_fprs(results[p][i]) for p in policies}
        common_ids = set(maps[policies[0]])
        for policy in policies[1:]:
            common_ids.intersection_update(maps[policy])
        ids = sorted(common_ids)
        for p in policies:
            out[p].append(np.array([maps[p][c] for c in ids], dtype=np.float64))
    return out


def _figure_files(png_path: Path) -> list[Path]:
    return [png_path, png_path.with_suffix(".pdf")]


def _validate_figure_sidecars(fig_dir: Path) -> list[NarrativeText]:
    failures: list[NarrativeText] = []
    for fig in _REPRESENTATIVE_SEED_FIGURES:
        sidecar = fig_dir / f"{fig}_data.json"
        if not sidecar.exists():
            failures.append(f"Missing figure sidecar: {sidecar}")
            continue
        try:
            data = json.loads(sidecar.read_text())
        except Exception as exc:
            failures.append(f"Unreadable sidecar {sidecar}: {exc}")
            continue
        if data.get(SidecarField.SEED_SCOPE) != SeedScope.REPRESENTATIVE_SEED:
            failures.append(f"{fig} sidecar missing {SidecarField.SEED_SCOPE}")
        if data.get(SidecarField.EVIDENCE_ROLE) != EvidenceRole.DESCRIPTIVE:
            failures.append(f"{fig} sidecar missing {SidecarField.EVIDENCE_ROLE}")
        if not data.get(SidecarField.NOT_CONFIRMATORY_WARNING):
            failures.append(f"{fig} missing {SidecarField.NOT_CONFIRMATORY_WARNING}")
        if "representative seed" not in data.get(SidecarField.TITLE, "").lower():
            failures.append(f"{fig} title does not include 'representative seed'")
    return failures


def _check_heterogeneity_context(
    primary: BootstrapReport,
    nbaiot: dict[ThresholdPolicy, list[EvaluationResult]],
    p_thresh: ScoreValue,
) -> JsonRecord:
    g_mean = (
        float(np.mean([r.dispersion.cv_fpr for r in nbaiot[ThresholdPolicy.GLOBAL_THRESHOLD]]))
        if nbaiot.get(ThresholdPolicy.GLOBAL_THRESHOLD)
        else math.nan
    )
    ci_excl = primary.result.excludes_zero
    return {
        StatsField.CONDITION: "N-BaIoT heterogeneity context: CV(FPR) disparity under GLOBAL_THRESHOLD.",
        StatsField.GLOBAL_CV_FPR_MEAN: g_mean,
        StatsField.PRACTICAL_SIGNIFICANCE_THRESHOLD: p_thresh,
        StatsField.PRACTICAL_SIGNIFICANCE_MET: False,
        StatsField.PRIMARY_ENDPOINT_CI_EXCLUDES_ZERO: ci_excl,
        StatsField.CONTEXT_RESULT: HeterogeneityContextResult.PARTIAL_CONTEXT
        if ci_excl
        else HeterogeneityContextResult.CONTEXT_NOT_AVAILABLE,
        StatsField.NOTE: "Primary endpoint: NBAIOT_MAIN",
    }


def build_stats(base_dir: Path, cfg: DatpConfig) -> tuple[Path, ...]:
    nbaiot = _load_results(
        base_dir,
        ExperimentStage.NBAIOT_MAIN,
        tuple(sorted(CONTROLLED_POLICIES)),
        tuple(cfg.experiment.seeds),
        cfg.reporting.metric_tol,
    )
    primary: BootstrapReport = _bootstrap_payload(
        _paired_deltas(
            nbaiot,
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
        ),
        cfg.statistics.n_bootstrap,
        cfg.statistics.ci_level,
        cfg.statistics.bootstrap_seed,
    )
    secondary: dict[StatsField, dict[ComparisonLabel, BootstrapReport]] = {
        StatsField.SECONDARY_NBAIOT: {
            ComparisonLabel.GLOBAL_VS_CLUSTER: _bootstrap_payload(
                _paired_deltas(
                    nbaiot,
                    ThresholdPolicy.GLOBAL_THRESHOLD,
                    ThresholdPolicy.CLUSTER_THRESHOLD,
                ),
                cfg.statistics.n_bootstrap,
                cfg.statistics.ci_level,
                cfg.statistics.bootstrap_seed,
            ),
            ComparisonLabel.CLUSTER_VS_LOCAL: _bootstrap_payload(
                _paired_deltas(
                    nbaiot,
                    ThresholdPolicy.CLUSTER_THRESHOLD,
                    ThresholdPolicy.LOCAL_THRESHOLD,
                ),
                cfg.statistics.n_bootstrap,
                cfg.statistics.ci_level,
                cfg.statistics.bootstrap_seed,
            ),
        },
        StatsField.SECONDARY_NBAIOT_ADDITIONAL: {
            ComparisonLabel.GLOBAL_VS_LOCAL: _bootstrap_payload(
                _paired_deltas(
                    nbaiot,
                    ThresholdPolicy.GLOBAL_THRESHOLD,
                    ThresholdPolicy.LOCAL_THRESHOLD,
                ),
                cfg.statistics.n_bootstrap,
                cfg.statistics.ci_level,
                cfg.statistics.bootstrap_seed,
            ),
            ComparisonLabel.GLOBAL_VS_CLUSTER: _bootstrap_payload(
                _paired_deltas(
                    nbaiot,
                    ThresholdPolicy.GLOBAL_THRESHOLD,
                    ThresholdPolicy.CLUSTER_THRESHOLD,
                ),
                cfg.statistics.n_bootstrap,
                cfg.statistics.ci_level,
                cfg.statistics.bootstrap_seed,
            ),
        },
    }
    secondary_payload: dict[str, JsonValue] = {}
    for scope, comparisons in secondary.items():
        comparison_payload: dict[str, JsonValue] = {}
        for comparison, summary in comparisons.items():
            summary_report: BootstrapReport = summary
            comparison_payload[comparison.value] = summary_report.to_payload()
        secondary_payload[scope.value] = comparison_payload

    payload: JsonRecord = {
        StatsField.PRIMARY_ENDPOINT: {
            StatsField.CONDITION: "Primary endpoint",
            **primary.to_payload(),
        },
        **secondary_payload,
    }
    payload[StatsField.HETEROGENEITY_CONTEXT_CHECK] = (
        _check_heterogeneity_context(
            primary, nbaiot, cfg.statistics.dispersion_threshold
        )
    )
    out_dir = base_dir / ArtifactDir.ANALYSIS
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = write_json_atomic(out_dir / ArtifactFile.BOOTSTRAP_CIS_JSON, payload)
    csv_path = out_dir / ArtifactFile.BOOTSTRAP_CIS_CSV
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                BootstrapField.SCOPE,
                BootstrapField.COMPARISON,
                BootstrapField.MEAN_DELTA,
                BootstrapField.CI_LOWER,
                BootstrapField.CI_UPPER,
                BootstrapField.EXCLUDES_ZERO,
            ]
        )
        writer.writerow(
            [
                StatsField.PRIMARY_ENDPOINT,
                ComparisonLabel.GLOBAL_VS_LOCAL,
                primary.result.mean_delta,
                primary.result.ci_lower,
                primary.result.ci_upper,
                primary.result.excludes_zero,
            ]
        )
        for scope, comparisons in secondary.items():
            for comp, summary in comparisons.items():
                writer.writerow(
                    [
                        scope,
                        comp,
                        summary.result.mean_delta,
                        summary.result.ci_lower,
                        summary.result.ci_upper,
                        summary.result.excludes_zero,
                    ]
                )
    return (json_path, csv_path)


def _figure1_sidecar_data(
    base_dir: Path,
    s0g: EvaluationResult,
    s0l: EvaluationResult,
    ids1: list[ClientId],
    g_fpr: ScoreVector,
    l_fpr: ScoreVector,
) -> JsonRecord:
    return {
        SidecarField.FIGURE: FigureName.FIGURE_1,
        SidecarField.TITLE: "Per-device FPR: GLOBAL_THRESHOLD vs LOCAL_THRESHOLD, NBAIOT_MAIN — representative seed, descriptive only",
        SidecarField.DATASET: DatasetID.NBAIOT,
        SidecarField.STAGE: ExperimentStage.NBAIOT_MAIN,
        SidecarField.SEED: s0g.run.seed,
        SidecarField.SEEDS: [s0g.run.seed],
        SidecarField.SOURCE_METRICS_FILES: [
            str(_result_path(base_dir, ExperimentStage.NBAIOT_MAIN, ThresholdPolicy.GLOBAL_THRESHOLD, s0g.run.seed)),
            str(_result_path(base_dir, ExperimentStage.NBAIOT_MAIN, ThresholdPolicy.LOCAL_THRESHOLD, s0l.run.seed)),
        ],
        SidecarField.RUN_IDS: [
            f"{ExperimentStage.NBAIOT_MAIN}_global_threshold_seed{s0g.run.seed}",
            f"{ExperimentStage.NBAIOT_MAIN}_local_threshold_seed{s0l.run.seed}",
        ],
        SidecarField.ALPHAS: [],
        SidecarField.ELIGIBLE_COUNTS: {
            ThresholdPolicy.GLOBAL_THRESHOLD: s0g.dispersion.eligible_count,
            ThresholdPolicy.LOCAL_THRESHOLD: s0l.dispersion.eligible_count,
        },
        SidecarField.CLIENT_COUNTS: {
            ThresholdPolicy.GLOBAL_THRESHOLD: s0g.dispersion.client_count,
            ThresholdPolicy.LOCAL_THRESHOLD: s0l.dispersion.client_count,
        },
        SidecarField.COVERAGE_RATIOS: {
            ThresholdPolicy.GLOBAL_THRESHOLD: s0g.coverage_ratio,
            ThresholdPolicy.LOCAL_THRESHOLD: s0l.coverage_ratio,
        },
        SidecarField.METRIC_NAMES: [MetricName.FPR],
        SidecarField.EVIDENCE_ROLE: EvidenceRole.DESCRIPTIVE,
        SidecarField.SEED_SCOPE: SeedScope.REPRESENTATIVE_SEED,
        SidecarField.SEED_SELECTION_RULE: SEED_SELECTION_RULE,
        SidecarField.NOT_CONFIRMATORY_WARNING: NOT_CONFIRMATORY_WARNING,
        SidecarField.VALIDATION_STATUS: AuditStatus.PASS,
        SidecarField.POLICIES: [ThresholdPolicy.GLOBAL_THRESHOLD, ThresholdPolicy.LOCAL_THRESHOLD],
        SidecarField.POLICY_ORDER: [ThresholdPolicy.GLOBAL_THRESHOLD, ThresholdPolicy.LOCAL_THRESHOLD],
        SidecarField.ELIGIBILITY_POLICY: "eligible-client intersection",
        SidecarField.AXIS_LABELS: {"x": "Device", "y": "FPR"},
        SidecarField.CLIENTS: [
            {
                SidecarField.CLIENT_ID: cid,
                ThresholdPolicy.GLOBAL_THRESHOLD: float(gv),
                ThresholdPolicy.LOCAL_THRESHOLD: float(lv),
            }
            for cid, gv, lv in zip(ids1, g_fpr, l_fpr)
        ],
    }


def _figure2_sidecar_data(
    base_dir: Path,
    s0g: EvaluationResult,
    tau_g: Threshold,
    max_points: SignedCount,
    rep: list[ClientId],
) -> JsonRecord:
    client_ids: list[JsonValue] = []
    client_ids.extend(rep)
    return {
        SidecarField.FIGURE: FigureName.FIGURE_2,
        SidecarField.TITLE: "Calibration-error ECDF for three representative N-BaIoT clients with GLOBAL_THRESHOLD client-averaged threshold — representative seed, descriptive only",
        SidecarField.DATASET: DatasetID.NBAIOT,
        SidecarField.STAGE: ExperimentStage.NBAIOT_MAIN,
        SidecarField.SEED: s0g.run.seed,
        SidecarField.SEEDS: [s0g.run.seed],
        SidecarField.SOURCE_METRICS_FILES: [
            str(_result_path(base_dir, ExperimentStage.NBAIOT_MAIN, ThresholdPolicy.GLOBAL_THRESHOLD, s0g.run.seed))
        ],
        SidecarField.SOURCE_SCORE_MANIFESTS: [
            str(
                ArtifactLayout(base_dir=base_dir, stage=ExperimentStage.NBAIOT_MAIN)
                .score_cell(TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=s0g.run.seed))
                .manifest_path
            )
        ],
        SidecarField.RUN_IDS: [f"{ExperimentStage.NBAIOT_MAIN}_global_threshold_seed{s0g.run.seed}"],
        SidecarField.ALPHAS: [],
        SidecarField.ELIGIBLE_COUNTS: {ThresholdPolicy.GLOBAL_THRESHOLD: s0g.dispersion.eligible_count},
        SidecarField.CLIENT_COUNTS: {ThresholdPolicy.GLOBAL_THRESHOLD: s0g.dispersion.client_count},
        SidecarField.COVERAGE_RATIOS: {ThresholdPolicy.GLOBAL_THRESHOLD: s0g.coverage_ratio},
        SidecarField.METRIC_NAMES: [ScoringColumn.RECONSTRUCTION_ERROR, PayloadKey.THRESHOLD_VALUE],
        SidecarField.EVIDENCE_ROLE: EvidenceRole.DESCRIPTIVE,
        SidecarField.SEED_SCOPE: SeedScope.REPRESENTATIVE_SEED,
        SidecarField.SEED_SELECTION_RULE: SEED_SELECTION_RULE,
        SidecarField.NOT_CONFIRMATORY_WARNING: NOT_CONFIRMATORY_WARNING,
        SidecarField.VALIDATION_STATUS: AuditStatus.PASS,
        SidecarField.POLICIES: [ThresholdPolicy.GLOBAL_THRESHOLD],
        SidecarField.POLICY_ORDER: [ThresholdPolicy.GLOBAL_THRESHOLD],
        SidecarField.ELIGIBILITY_POLICY: f"selected eligible clients from GLOBAL_THRESHOLD seed {s0g.run.seed}",
        SidecarField.AXIS_LABELS: {"x": "Reconstruction Error", "y": "Density"},
        SidecarField.TAU_GLOBAL: tau_g,
        SidecarField.CLIENT_IDS: client_ids,
        SidecarField.CLIENT_SELECTION_RULE: CLIENT_SELECTION_RULE,
        SidecarField.MAX_POINTS_PER_CLIENT: max_points,
    }


def _figure3_sidecar_data(
    base_dir: Path,
    nbaiot: dict[ThresholdPolicy, list[EvaluationResult]],
    fpr_pol: dict[ThresholdPolicy, list[ScoreVector]],
    b_enums: tuple[ThresholdPolicy, ...],
    seeds: tuple[RandomSeed, ...],
) -> JsonRecord:
    return {
        SidecarField.FIGURE: FigureName.FIGURE_3,
        SidecarField.TITLE: "Per-client FPR distribution, N-BaIoT main",
        SidecarField.DATASET: DatasetID.NBAIOT,
        SidecarField.STAGE: ExperimentStage.NBAIOT_MAIN,
        SidecarField.SOURCE_METRICS_FILES: [
            str(_result_path(base_dir, ExperimentStage.NBAIOT_MAIN, b, s))
            for b in b_enums
            for s in seeds
        ],
        SidecarField.RUN_IDS: [
            f"{ExperimentStage.NBAIOT_MAIN}_{b}_seed{s}"
            for b in [e for e in b_enums]
            for s in seeds
        ],
        SidecarField.SEEDS: list(seeds),
        SidecarField.ALPHAS: [],
        SidecarField.ELIGIBLE_COUNTS: {b: [r.dispersion.eligible_count for r in nbaiot[b]] for b in b_enums},
        SidecarField.CLIENT_COUNTS: {b: [r.dispersion.client_count for r in nbaiot[b]] for b in b_enums},
        SidecarField.COVERAGE_RATIOS: {b: [r.coverage_ratio for r in nbaiot[b]] for b in b_enums},
        SidecarField.METRIC_NAMES: [
            MetricName.FPR,
            MetricName.CV_FPR_DELTA_GLOBAL_MINUS_LOCAL,
        ],
        SidecarField.EVIDENCE_ROLE: EvidenceRole.DESCRIPTIVE_WITH_CONFIRMATORY_SIDECAR_DELTA,
        SidecarField.SEED_SCOPE: SeedScope.ALL_SEEDS,
        SidecarField.VALIDATION_STATUS: AuditStatus.PASS,
        SidecarField.POLICIES: [e for e in b_enums],
        SidecarField.PAIRED_SEED_CV_FPR_DELTA: [
            float(x)
            for x in _paired_deltas(nbaiot, ThresholdPolicy.GLOBAL_THRESHOLD, ThresholdPolicy.LOCAL_THRESHOLD)
        ],
        SidecarField.SEED_AGGREGATION_POLICY: "eligible-client FPR values pooled across configured seeds after intersection",
        SidecarField.POLICY_ORDER: [e for e in b_enums],
        SidecarField.ELIGIBILITY_POLICY: "eligible-client intersection within each seed",
        SidecarField.AXIS_LABELS: {"x": "ThresholdPolicy", "y": "FPR"},
        SidecarField.VALUES: {
            pol: [[float(x) for x in arr] for arr in arrays]
            for pol, arrays in fpr_pol.items()
        },
    }


def _convergence_summary_warnings(
    base_dir: Path, seeds: tuple[RandomSeed, ...]
) -> list[NarrativeText]:
    layout = ArtifactLayout(base_dir=base_dir, stage=ExperimentStage.NBAIOT_MAIN)
    warnings: list[NarrativeText] = []
    for s in seeds:
        score_dir = layout.score_cell(
            TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=s)
        ).score_dir
        sum_f = score_dir / ArtifactFile.CONVERGENCE_SUMMARY
        if not sum_f.exists():
            warnings.append(f"Missing summary {sum_f}")
    return warnings


def _json_text_values(values: Iterable[str]) -> list[JsonValue]:
    output: list[JsonValue] = []
    for value in values:
        output.append(value)
    return output


def build_figures(base_dir: Path, cfg: DatpConfig) -> tuple[Path, ...]:
    fig_dir = base_dir / ArtifactDir.FIGURES
    fig_dir.mkdir(parents=True, exist_ok=True)
    nbaiot = _load_results(
        base_dir,
        ExperimentStage.NBAIOT_MAIN,
        tuple(sorted(CONTROLLED_POLICIES)),
        tuple(cfg.experiment.seeds),
        cfg.reporting.metric_tol,
    )

    global_results = nbaiot[ThresholdPolicy.GLOBAL_THRESHOLD]
    rep_idx = sorted(range(len(global_results)), key=lambda i: global_results[i].dispersion.cv_fpr)[
        (len(global_results) - 1) // 2
    ]
    s0g = global_results[rep_idx]
    s0l = nbaiot[ThresholdPolicy.LOCAL_THRESHOLD][rep_idx]
    g_fpr, l_fpr, ids1 = _eligible_intersection_fprs(s0g, s0l)
    sc1 = write_json_atomic(
        fig_dir / f"{FigureName.FIGURE_1}_data.json",
        _figure1_sidecar_data(base_dir, s0g, s0l, ids1, g_fpr, l_fpr),
    )
    p1 = _figure_files(
        generate_figure1(dict(zip(ids1, g_fpr)), dict(zip(ids1, l_fpr)), fig_dir, cfg.reporting.style)
    )

    s0g_fprs = _eligible_fprs(s0g)
    s_devs = sorted(s0g_fprs, key=lambda d: s0g_fprs[d])
    rep = [ClientId(s_devs[0]), ClientId(s_devs[len(s_devs) // 2]), ClientId(s_devs[-1])]
    cal_errs: dict[ClientId, ScoreVector] = {}
    rng = np.random.default_rng(cfg.reporting.figure2_rng_seed)
    sp = ScoreProvider(
        ArtifactLayout(base_dir=base_dir, stage=ExperimentStage.NBAIOT_MAIN)
        .score_cell(TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=s0g.run.seed))
        .score_dir
    )
    for dev in rep:
        client_id = ClientId(dev)
        v = sp.load(client_id, ScoringStage.CAL)
        cal_errs[client_id] = (
            rng.choice(v, size=cfg.reporting.figure2_max_points, replace=False)
            if v.size > cfg.reporting.figure2_max_points
            else v
        )
    tau_g = _load_json(
        _result_path(
            base_dir,
            ExperimentStage.NBAIOT_MAIN,
            ThresholdPolicy.GLOBAL_THRESHOLD,
            s0g.run.seed,
        )
    ).tau_global
    sc2 = write_json_atomic(
        fig_dir / f"{FigureName.FIGURE_2}_data.json",
        _figure2_sidecar_data(base_dir, s0g, tau_g, cfg.reporting.figure2_max_points, rep),
    )
    p2 = _figure_files(
        generate_figure2(cal_errs, tau_g, rep, fig_dir, cfg.reporting.style)
    )

    b_enums = (
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    )
    fpr_pol = _common_eligible_fprs(nbaiot, b_enums)
    sc3 = write_json_atomic(
        fig_dir / f"{FigureName.FIGURE_3}_data.json",
        _figure3_sidecar_data(base_dir, nbaiot, fpr_pol, b_enums, tuple(cfg.experiment.seeds)),
    )
    p3 = _figure_files(
        generate_figure3(fpr_pol, fig_dir, cfg.reporting.style)
    )

    return (sc1, *p1, sc2, *p2, sc3, *p3)


_FIGURE_5_PANELS: tuple[
    tuple[AttackerObjective, PoisoningSourceStrategy, MetricName, NarrativeText], ...
] = (
    (
        AttackerObjective.THRESHOLD_RAISE,
        PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        MetricName.VICTIM_DELTA_TPR,
        r"Victim $\Delta$TPR",
    ),
    (
        AttackerObjective.THRESHOLD_LOWER,
        PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        MetricName.VICTIM_DELTA_FPR,
        r"Victim $\Delta$FPR",
    ),
)


_FIGURE_6_PANELS: tuple[
    tuple[AttackerObjective, PoisoningSourceStrategy, MetricName, NarrativeText], ...
] = (
    (
        AttackerObjective.THRESHOLD_RAISE,
        PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        MetricName.VICTIM_DELTA_TPR,
        r"RAISE: victim $\Delta$TPR",
    ),
    (
        AttackerObjective.THRESHOLD_LOWER,
        PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        MetricName.VICTIM_DELTA_FPR,
        r"LOWER: victim $\Delta$FPR",
    ),
    (
        AttackerObjective.THRESHOLD_LOWER,
        PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        MetricName.DELTA_CV_FPR,
        r"LOWER: $\Delta$CV(FPR)",
    ),
)


def build_poisoning_figures(base_dir: Path, cfg: DatpConfig) -> tuple[Path, ...]:
    manifest = load_poisoning_manifest(base_dir)
    fig_dir = base_dir / ArtifactDir.FIGURES
    fig_dir.mkdir(parents=True, exist_ok=True)
    rows = [r for r in manifest.results if r.fraction == POISONING_FIGURE_FRACTION]

    def select(objective: AttackerObjective, source: PoisoningSourceStrategy):
        return [r for r in rows if r.objective == objective and r.source == source]

    client_effects = {
        label: {
            pol: _per_victim_seed_values(
                [r for r in select(obj, src) if r.policy == pol], metric
            )
            for pol in manifest.policies
        }
        for obj, src, metric, label in _FIGURE_5_PANELS
    }
    seed_effects = {
        label: {
            pol: _seed_means([r for r in select(obj, src) if r.policy == pol], metric)
            for pol in manifest.policies
        }
    for obj, src, metric, label in _FIGURE_6_PANELS
    }

    sidecars: list[Path] = []
    figure5_values: JsonValue = {
        panel: {
            policy: {
                client_id: [float(value) for value in values]
                for client_id, values in by_client.items()
            }
            for policy, by_client in policies.items()
        }
        for panel, policies in client_effects.items()
    }
    figure6_values: JsonValue = {
        panel: {
            policy: [float(value) for value in values]
            for policy, values in policies.items()
        }
        for panel, policies in seed_effects.items()
    }
    for name, data in (
        (FigureName.FIGURE_5, figure5_values),
        (FigureName.FIGURE_6, figure6_values),
    ):
        sidecar: JsonRecord = {
            SidecarField.FIGURE: name,
            SidecarField.DATASET: DatasetID.NBAIOT,
            SidecarField.STAGE: ExperimentStage.NBAIOT_MAIN,
            SidecarField.SEEDS: list(manifest.training_seeds),
            SidecarField.SEED_SCOPE: SeedScope.ALL_TRAINING_SEEDS,
            SidecarField.EVIDENCE_ROLE: EvidenceRole.DESCRIPTIVE,
            SidecarField.VALUES: data,
            SidecarField.FRACTION: POISONING_FIGURE_FRACTION,
        }
        sidecars.append(
            write_json_atomic(
                fig_dir / f"{name}_data.json",
                sidecar,
            )
        )
    p5 = _figure_files(
        generate_figure5(client_effects, fig_dir, cfg.reporting.style)
    )
    p6 = _figure_files(
        generate_figure6(seed_effects, fig_dir, cfg.reporting.style)
    )
    return (*sidecars, *p5, *p6)


def _per_victim_seed_values(
    rows: list[BoundedSweepResultRow], metric: MetricName
) -> dict[ClientId, list[ScoreValue]]:
    out: dict[ClientId, list[ScoreValue]] = defaultdict(list)
    for r in rows:
        out[r.victim_id].append(_panel_metric_value(r, metric))
    return dict(out)


def _seed_means(
    rows: list[BoundedSweepResultRow], metric: MetricName
) -> list[ScoreValue]:
    by_seed: dict[RandomSeed, list[ScoreValue]] = defaultdict(list)
    for r in rows:
        by_seed[r.training_seed].append(_panel_metric_value(r, metric))
    return [float(np.nanmean(v)) for _, v in sorted(by_seed.items())]


def _panel_metric_value(row: BoundedSweepResultRow, metric: MetricName) -> ScoreValue:
    match metric:
        case MetricName.VICTIM_DELTA_TPR:
            return row.victim_delta_tpr
        case MetricName.VICTIM_DELTA_FPR:
            return row.victim_delta_fpr
        case MetricName.DELTA_CV_FPR:
            return row.delta_cv_fpr
        case _:
            raise ValueError(f"Metric {metric} is not supported in report panels")


def build_tables(base_dir: Path, cfg: DatpConfig) -> tuple[Path, ...]:
    t3 = generate_table3(
        _load_results(
            base_dir,
            ExperimentStage.NBAIOT_MAIN,
            tuple(sorted(CONTROLLED_POLICIES)),
            tuple(cfg.experiment.seeds),
            cfg.reporting.metric_tol,
        ),
        base_dir / ArtifactDir.TABLES,
        cfg.reporting.style,
    )
    return (t3, t3.with_suffix(".csv"))


def validate_results(base_dir: Path, cfg: DatpConfig) -> tuple[Path, ...]:
    _load_results(
        base_dir,
        ExperimentStage.NBAIOT_MAIN,
        tuple(sorted(CONTROLLED_POLICIES)),
        tuple(cfg.experiment.seeds),
        cfg.reporting.metric_tol,
    )
    return (
        write_json_atomic(
            base_dir
            / ArtifactDir.ANALYSIS
            / ArtifactFile.METRICS_SCHEMA_VALIDATION,
            {
                ValidationField.STATUS: AuditStatus.PASS,
                ValidationField.SOURCE: "canonical per-client confusion-count reconstruction",
                ValidationField.VALIDATED_STAGES: [ExperimentStage.NBAIOT_MAIN],
                ValidationField.SEEDS: list(cfg.experiment.seeds),
            },
        ),
    )


def build_all(base_dir: Path, cfg: DatpConfig) -> tuple[Path, ...]:
    _REPORTING_SOURCES.clear()
    paths: list[Path] = []
    failures: list[NarrativeText] = []
    try:
        paths.extend(validate_results(base_dir, cfg))
        paths.extend(build_stats(base_dir, cfg))
        paths.extend(build_figures(base_dir, cfg))
        paths.extend(build_tables(base_dir, cfg))
    except Exception as exc:
        failures.append(str(exc))

    fig_dir = base_dir / ArtifactDir.FIGURES
    failures.extend(_validate_figure_sidecars(fig_dir))
    warnings = _convergence_summary_warnings(base_dir, tuple(cfg.experiment.seeds))

    audit: JsonRecord = {
        AuditField.SCHEMA_VERSION: REPORTING_AUDIT_SCHEMA_VERSION,
        AuditField.GENERATED_TABLES: _json_text_values(
            str(p)
            for p in paths
            if p.suffix in {PathToken.TEX_EXT, PathToken.CSV_EXT}
            and ArtifactDir.TABLES in p.parts
        ),
        AuditField.GENERATED_FIGURES: _json_text_values(
            str(p)
            for p in paths
            if p.suffix
            in {PathToken.PDF_EXT, PathToken.PNG_EXT, PathToken.JSON_EXT}
            and ArtifactDir.FIGURES in p.parts
        ),
        AuditField.SOURCE_METRICS_FILES: _json_text_values(sorted(_REPORTING_SOURCES)),
        AuditField.SOURCE_SCORE_MANIFESTS: _json_text_values(
                    str(
                        ArtifactLayout(
                            base_dir=base_dir, stage=ExperimentStage.NBAIOT_MAIN
                        )
                        .score_cell(
                            TrainingCellId(
                                stage=ExperimentStage.NBAIOT_MAIN,
                                seed=s,
                            )
                        )
                        .manifest_path
                    )
                    for s in cfg.experiment.seeds
                ),
        AuditField.SOURCE_RUN_IDS: _json_text_values(sorted(_REPORTING_SOURCES)),
        AuditField.VALIDATION_RESULTS: AuditStatus.FAIL
                if failures
                else AuditStatus.PASS,
        AuditField.RECOMPUTATION_CHECKS: "canonical confusion-matrix recomputation during load",
        AuditField.COVERAGE_CHECKS: "explicit eligible_ids/pending_ids/eval_incomplete_ids required",
        AuditField.MISSING_FIELD_CHECKS: "validate_metrics_payload",
        AuditField.STALE_ARTIFACT_CHECKS: "schema/provenance/sidecar checks",
        AuditField.DESCRIPTIVE_FIGURE_CHECKS: f"representative-seed sidecar validation for {sorted(_REPRESENTATIVE_SEED_FIGURES)}",
        AuditField.CONVERGENCE_METADATA_CHECKS: "warn if a score cell has no convergence summary",
        AuditField.FIGURE_TABLE_OUTPUT_PATHS: _json_text_values(str(p) for p in paths),
        AuditField.WARNINGS: _json_text_values(warnings),
        AuditField.FAILURES: _json_text_values(failures),
    }
    paths.append(
        write_json_atomic(
            base_dir / ArtifactDir.ANALYSIS / ArtifactFile.REPORTING_AUDIT,
            audit,
        )
    )

    if failures:
        raise ValueError(f"reporting_audit contains failures: {failures}")
    return tuple(paths)


logger = get_logger(__name__)


def _reset_package_dir(base_dir: Path, results_dir: Path) -> None:
    resolved = results_dir.resolve()
    if resolved == Path.cwd().resolve() or base_dir.resolve().is_relative_to(resolved):
        raise ValueError(
            f"Refusing to clear results directory {results_dir}: it contains the run outputs."
        )
    shutil.rmtree(results_dir, ignore_errors=True)
    results_dir.mkdir(parents=True)


def _copy_into(source: Path, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    return Path(shutil.copy2(source, destination_dir / source.name))


def build_report_package(
    *, base_dir: Path, results_dir: Path, data_root: Path, cfg: DatpConfig
) -> tuple[Path, ...]:
    audit_dir = base_dir / AuditDir.AUDIT
    audit_outputs: AuditOutputPaths = run_results_audit(
        base_dir, audit_dir, cfg, data_root
    )
    audit_paths = tuple(path for _, path in audit_outputs.items())
    analysis_paths = (
        *build_all(base_dir, cfg),
        *build_poisoning_summaries(base_dir),
        *build_poisoning_figures(base_dir, cfg),
        *build_sensitivity_summaries(base_dir),
    )
    manifest_paths = (
        nbaiot_main_manifest_path(base_dir),
        sensitivity_manifest_path(base_dir),
    )

    _reset_package_dir(base_dir, results_dir)
    packaged = [
        write_resolved_config(cfg, results_dir / PackageDir.CONFIG),
        *(_copy_into(path, results_dir / PackageDir.AUDIT) for path in audit_paths),
        *(_copy_into(path, results_dir / PackageDir.MANIFESTS) for path in manifest_paths),
    ]
    for path in analysis_paths:
        packaged.append(
            _copy_into(path, results_dir / path.relative_to(base_dir).parent)
        )
    logger.info("report package written", results_dir=results_dir.as_posix(), file_count=len(packaged))
    return tuple(packaged)
