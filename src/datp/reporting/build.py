"""Report artifact builder: loads persisted metrics, validates, and generates figures/tables."""

from __future__ import annotations

import csv
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from datp.artifacts.io import write_json_atomic
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactDir, ArtifactFile
from datp.checkpointing.enums import EvidenceRole
from datp.config.models import DatpConfig
from datp.config.models import ExperimentStage
from datp.core.enums import (
    CONTROLLED_POLICIES,
    AuditField,
    ConfusionKey,
    MetricName,
    PayloadKey,
    RunKind,
    ScoringStage,
    SeedScope,
    ThresholdPolicy,
    ValidationField,
)
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.types import ClientThreshold
from datp.data.catalog import DatasetID
from datp.evaluation.artifact_validation import client_rows, validate_metrics_payload
from datp.evaluation.metrics import (
    ClientEvaluationRecord,
    ConfusionCounts,
    EvaluationResult,
    build_evaluation_result,
    recompute_binary_metrics,
)
from datp.reporting.constants import (
    NOT_CONFIRMATORY_WARNING,
    REPORTING_AUDIT_SCHEMA_VERSION,
)
from datp.reporting.enums import (
    ComparisonLabel,
    FigureName,
    HeterogeneityContextResult,
    SidecarField,
)
from datp.reporting.figures import generate_figure1, generate_figure2, generate_figure3
from datp.reporting.tables import generate_table3
from datp.scoring.loading import ScoreProvider
from datp.scoring.manifest import SCORE_COLUMN
from datp.statistics.bootstrap import bootstrap_ci
from datp.statistics.constants import BootstrapField, StatsField
from datp.validation.enums import AuditStatus

_REPORTING_SOURCES: set[str] = set()
_REPRESENTATIVE_SEED_FIGURES: frozenset[str] = frozenset(
    {FigureName.FIGURE_1.value, FigureName.FIGURE_2.value}
)


@dataclass(frozen=True, slots=True)
class BuildOutputs:
    """Container for artifact file paths produced by a report build step."""

    paths: list[Path]


def _result_path(
    base_dir: Path, stage: ExperimentStage, policy: ThresholdPolicy, seed: int
) -> Path:
    """Return the metrics JSON path for a given stage, policy, and seed under base_dir."""
    return (
        ArtifactLayout(base_dir=base_dir, stage=stage)
        .policy_run(
            PolicyRunId(cell=TrainingCellId(stage=stage, seed=seed), policy=policy)
        )
        .result_dir
        / ArtifactFile.METRICS
    )


def _load_json(path: Path) -> dict[str, Any]:
    """Load and schema-validate a metrics JSON artifact, registering it in the reporting-sources set."""
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}")
    payload = json.loads(path.read_text())
    if payload.get(PayloadKey.RUN_KIND) != RunKind.CORE_LADDER.value:
        raise ValueError(f"RunKind separation violation: {path}")
    _REPORTING_SOURCES.add(str(path))
    if failures := validate_metrics_payload(payload, module="reporting"):
        raise ValueError("; ".join(failures) + f" Artifact: {path}")
    return payload


def _extract_confusion_counts(
    client_id: str, confusion: Mapping[str, Any]
) -> tuple[int, int, int, int]:
    """Extract (TP, FP, TN, FN) integers from a per-client confusion mapping, raising on missing keys."""
    if missing := [
        k
        for k in (ConfusionKey.TP, ConfusionKey.FP, ConfusionKey.TN, ConfusionKey.FN)
        if k not in confusion
    ]:
        raise ValueError(f"Missing counts for {client_id}: {missing}")
    return (
        int(confusion[ConfusionKey.TP]),
        int(confusion[ConfusionKey.FP]),
        int(confusion[ConfusionKey.TN]),
        int(confusion[ConfusionKey.FN]),
    )


def _client_records_from_payload(
    payload: dict[str, Any],
) -> tuple[ClientEvaluationRecord, ...]:
    """Parse per-client evaluation records from a metrics payload, validating denominator counts."""
    records, policy = [], ThresholdPolicy(payload[PayloadKey.POLICY])
    for client_id, row in client_rows(payload):
        tp, fp, tn, fn = _extract_confusion_counts(
            client_id, row[PayloadKey.CONFUSION_MATRIX]
        )
        if PayloadKey.N_BENIGN in row and int(row[PayloadKey.N_BENIGN]) != fp + tn:
            raise ValueError(f"Benign denominator mismatch for {client_id}.")
        if PayloadKey.N_ATTACK in row and int(row[PayloadKey.N_ATTACK]) != tp + fn:
            raise ValueError(f"Attack denominator mismatch for {client_id}.")

        cid_str = str(client_id)
        records.append(
            ClientEvaluationRecord(
                client_id=cid_str,
                metrics=recompute_binary_metrics(tp, fp, tn, fn),
                confusion=ConfusionCounts(tp=tp, fp=fp, tn=tn, fn=fn),
                n_benign=fp + tn,
                n_attack=tp + fn,
                threshold=ClientThreshold(
                    client_id=cid_str,
                    threshold=float(row.get(PayloadKey.THRESHOLD_VALUE, 0.0)),
                    calibration_pending=bool(
                        row.get(PayloadKey.CALIBRATION_PENDING, False)
                    ),
                    strategy=policy,
                ),
                evaluation_incomplete=bool(
                    row.get(PayloadKey.EVALUATION_INCOMPLETE, False)
                ),
            )
        )
    return tuple(records)


def _assert_metric_matches(
    payload: dict[str, Any], key: str, value: float, tol: float
) -> None:
    """Raise ValueError if the stored metric at key differs from value by more than tol."""
    if (saved_raw := payload.get(key)) is None:
        raise ValueError(f"Missing {key}")
    saved = float(saved_raw)
    if np.isnan(saved) and np.isnan(value):
        return
    if np.isnan(saved) != np.isnan(value) or abs(saved - value) > tol:
        raise ValueError(f"Metric schema mismatch: {key}={value} vs {saved}")


def _evaluation_from_payload(
    payload: dict[str, Any], metric_tol: float
) -> EvaluationResult:
    """Build an EvaluationResult from a metrics payload and verify stored scalar metrics are consistent."""
    result = build_evaluation_result(
        policy=ThresholdPolicy(payload[PayloadKey.POLICY]),
        stage=ExperimentStage(
            payload.get(PayloadKey.STAGE, ExperimentStage.NBAIOT_MAIN.value)
        ),
        seed=int(payload[PayloadKey.SEED]),
        clients=_client_records_from_payload(payload),
        eligible_ids=tuple(str(c) for c in payload[PayloadKey.ELIGIBLE_IDS]),
        pending_ids=tuple(str(c) for c in payload[PayloadKey.PENDING_IDS]),
        incomplete_ids=tuple(str(c) for c in payload[PayloadKey.EVAL_INCOMPLETE_IDS]),
    )
    for k, v in {
        PayloadKey.COVERAGE_RATIO: result.coverage_ratio,
        MetricName.CV_FPR.value: result.cv_fpr,
        MetricName.MEAN_FPR.value: result.mean_fpr,
        MetricName.STD_FPR.value: result.std_fpr,
        MetricName.CV_TPR.value: result.cv_tpr,
        MetricName.IQR_FPR.value: result.iqr_fpr,
        MetricName.IQR_TPR.value: result.iqr_tpr,
        MetricName.WORST_CLIENT_FPR.value: result.worst_client_fpr,
        MetricName.WORST_BA.value: result.worst_ba,
        MetricName.P10_MACRO_F1.value: result.p10_macro_f1,
    }.items():
        _assert_metric_matches(payload, k, v, metric_tol)
    if int(payload[PayloadKey.ELIGIBLE_COUNT]) != result.eligible_count:
        raise ValueError("Eligibility count mismatch")
    if int(payload[PayloadKey.CLIENT_COUNT]) != result.client_count:
        raise ValueError("Client count mismatch")
    return result


def _load_results(
    base_dir: Path,
    stage: ExperimentStage,
    policies: tuple[ThresholdPolicy, ...],
    seeds: tuple[int, ...],
    tol: float,
) -> dict[ThresholdPolicy, list[EvaluationResult]]:
    """Load and validate evaluation results for every requested policy/seed combination."""
    return {
        p: [
            _evaluation_from_payload(
                _load_json(_result_path(base_dir, stage, p, s)), tol
            )
            for s in seeds
        ]
        for p in policies
    }


def _eligible_fprs(result: EvaluationResult) -> dict[str, float]:
    """Return a {client_id: fpr} map restricted to eligible clients in the result."""
    el = set(result.eligible_ids)
    return {c.client_id: c.metrics.fpr for c in result.clients if c.client_id in el}


def _eligible_intersection_fprs(
    left: EvaluationResult, right: EvaluationResult
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return aligned FPR arrays and client IDs for the eligible-client intersection of two results."""
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
    deltas: np.ndarray, n_bootstrap: int, ci: float, seed: int
) -> dict[str, Any]:
    """Run a bootstrap CI on per-seed deltas and return a dict of bootstrap fields."""
    res = bootstrap_ci(deltas, n_bootstrap=n_bootstrap, ci=ci, seed=seed)
    return {
        BootstrapField.PER_SEED_DELTAS: [float(x) for x in deltas],
        BootstrapField.MEAN_DELTA: res.mean_delta,
        BootstrapField.CI_LOWER: res.ci_lower,
        BootstrapField.CI_UPPER: res.ci_upper,
        BootstrapField.CI: ci,
        BootstrapField.EXCLUDES_ZERO: res.excludes_zero,
        BootstrapField.N_BOOTSTRAP: res.n_bootstrap,
        BootstrapField.N_SEEDS: res.n_seeds,
    }


def _paired_deltas(
    results: dict[ThresholdPolicy, list[EvaluationResult]],
    left: ThresholdPolicy,
    right: ThresholdPolicy,
) -> np.ndarray:
    """Return per-seed CV-FPR differences (left minus right) as a numpy array."""
    return np.array(
        [
            float(results[left][i].cv_fpr) - float(results[right][i].cv_fpr)
            for i in range(len(results[left]))
        ]
    )


def _common_eligible_fprs(
    results: dict[ThresholdPolicy, list[EvaluationResult]],
    policies: tuple[ThresholdPolicy, ...],
) -> dict[ThresholdPolicy, list[np.ndarray]]:
    """Return per-policy, per-seed FPR arrays restricted to the common eligible-client intersection."""
    out: dict[ThresholdPolicy, list[np.ndarray]] = {p: [] for p in policies}
    for i in range(len(results[policies[0]])):
        maps = {p: _eligible_fprs(results[p][i]) for p in policies}
        ids = sorted(set.intersection(*(set(maps[p]) for p in policies)))
        for p in policies:
            out[p].append(np.array([maps[p][c] for c in ids], dtype=np.float64))
    return out


def _save_figure_copies(fig_dir: Path, stem: str, gen_png: Path) -> list[Path]:
    """Copy the generated PNG and its PDF sibling to fig_dir and return all three paths."""
    png_path, pdf_path = fig_dir / f"{stem}.png", fig_dir / f"{stem}.pdf"
    shutil.copyfile(gen_png, png_path)
    shutil.copyfile(gen_png.with_suffix(".pdf"), pdf_path)
    return [gen_png, png_path, pdf_path]


def _validate_figure_sidecars(fig_dir: Path) -> list[str]:
    """Validate required metadata fields in representative-seed figure sidecar JSONs."""
    failures: list[str] = []
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
        if data.get(SidecarField.SEED_SCOPE) != SeedScope.REPRESENTATIVE_SEED.value:
            failures.append(f"{fig} sidecar missing {SidecarField.SEED_SCOPE}")
        if data.get(SidecarField.EVIDENCE_ROLE) != EvidenceRole.DESCRIPTIVE.value:
            failures.append(f"{fig} sidecar missing {SidecarField.EVIDENCE_ROLE}")
        if not data.get(SidecarField.NOT_CONFIRMATORY_WARNING):
            failures.append(f"{fig} missing {SidecarField.NOT_CONFIRMATORY_WARNING}")
        if "representative seed" not in data.get(SidecarField.TITLE, "").lower():
            failures.append(f"{fig} title does not include 'representative seed'")
    return failures


def _check_heterogeneity_context(
    payload: dict[str, Any],
    nbaiot: dict[ThresholdPolicy, list[EvaluationResult]],
    p_thresh: float,
) -> dict[str, Any]:
    """Build the heterogeneity-context check dict for GLOBAL_THRESHOLD CV(FPR) disparity."""
    g_mean = (
        float(
            np.mean([float(r.cv_fpr) for r in nbaiot[ThresholdPolicy.GLOBAL_THRESHOLD]])
        )
        if nbaiot.get(ThresholdPolicy.GLOBAL_THRESHOLD)
        else float("nan")
    )
    ci_excl = bool(payload[StatsField.PRIMARY_ENDPOINT][BootstrapField.EXCLUDES_ZERO])
    return {
        StatsField.CONDITION: "N-BaIoT heterogeneity context: CV(FPR) disparity under GLOBAL_THRESHOLD.",
        StatsField.GLOBAL_CV_FPR_MEAN: g_mean,
        StatsField.PRACTICAL_SIGNIFICANCE_THRESHOLD: p_thresh,
        StatsField.PRACTICAL_SIGNIFICANCE_MET: False,
        StatsField.PRIMARY_ENDPOINT_CI_EXCLUDES_ZERO: ci_excl,
        StatsField.CONTEXT_RESULT: HeterogeneityContextResult.PARTIAL_CONTEXT.value
        if ci_excl
        else HeterogeneityContextResult.CONTEXT_NOT_AVAILABLE.value,
        StatsField.NOTE: "Primary endpoint: NBAIOT_MAIN",
    }


def build_stats(base_dir: Path, cfg: DatpConfig) -> BuildOutputs:
    """Compute bootstrap CIs for primary and secondary endpoints and write JSON/CSV."""
    nbaiot = _load_results(
        base_dir,
        ExperimentStage.NBAIOT_MAIN,
        tuple(sorted(CONTROLLED_POLICIES)),
        tuple(cfg.experiment.seeds),
        cfg.reporting.metric_tol,
    )
    payload = {
        StatsField.PRIMARY_ENDPOINT: {
            StatsField.CONDITION: "Primary endpoint",
            **_bootstrap_payload(
                _paired_deltas(
                    nbaiot,
                    ThresholdPolicy.GLOBAL_THRESHOLD,
                    ThresholdPolicy.LOCAL_THRESHOLD,
                ),
                cfg.statistics.n_bootstrap,
                cfg.statistics.ci_level,
                cfg.statistics.bootstrap_seed,
            ),
        },
        "secondary_nbaiot": {
            ComparisonLabel.GLOBAL_VS_CLUSTER.value: _bootstrap_payload(
                _paired_deltas(
                    nbaiot,
                    ThresholdPolicy.GLOBAL_THRESHOLD,
                    ThresholdPolicy.CLUSTER_THRESHOLD,
                ),
                cfg.statistics.n_bootstrap,
                cfg.statistics.ci_level,
                cfg.statistics.bootstrap_seed,
            ),
            ComparisonLabel.CLUSTER_VS_LOCAL.value: _bootstrap_payload(
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
        "secondary_nbaiot_additional": {
            ComparisonLabel.GLOBAL_VS_LOCAL.value: _bootstrap_payload(
                _paired_deltas(
                    nbaiot,
                    ThresholdPolicy.GLOBAL_THRESHOLD,
                    ThresholdPolicy.LOCAL_THRESHOLD,
                ),
                cfg.statistics.n_bootstrap,
                cfg.statistics.ci_level,
                cfg.statistics.bootstrap_seed,
            ),
            ComparisonLabel.GLOBAL_VS_CLUSTER.value: _bootstrap_payload(
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
    payload[StatsField.HETEROGENEITY_CONTEXT_CHECK] = _check_heterogeneity_context(
        payload, nbaiot, cfg.statistics.dispersion_threshold
    )
    out_dir = base_dir / ArtifactDir.ANALYSIS
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = write_json_atomic(out_dir / ArtifactFile.BOOTSTRAP_CIS_JSON, payload)
    csv_path = out_dir / ArtifactFile.BOOTSTRAP_CIS_CSV
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "scope",
                "comparison",
                BootstrapField.MEAN_DELTA,
                BootstrapField.CI_LOWER,
                BootstrapField.CI_UPPER,
                BootstrapField.EXCLUDES_ZERO,
            ]
        )
        writer.writerow(
            [
                StatsField.PRIMARY_ENDPOINT,
                ComparisonLabel.GLOBAL_VS_LOCAL.value,
                payload[StatsField.PRIMARY_ENDPOINT][BootstrapField.MEAN_DELTA],
                payload[StatsField.PRIMARY_ENDPOINT][BootstrapField.CI_LOWER],
                payload[StatsField.PRIMARY_ENDPOINT][BootstrapField.CI_UPPER],
                payload[StatsField.PRIMARY_ENDPOINT][BootstrapField.EXCLUDES_ZERO],
            ]
        )
        for s in ("secondary_nbaiot", "secondary_nbaiot_additional"):
            for comp, st in payload[s].items():
                writer.writerow(
                    [
                        s,
                        comp,
                        st[BootstrapField.MEAN_DELTA],
                        st[BootstrapField.CI_LOWER],
                        st[BootstrapField.CI_UPPER],
                        st[BootstrapField.EXCLUDES_ZERO],
                    ]
                )
    return BuildOutputs([json_path, csv_path])


def _figure1_sidecar_data(
    base_dir: Path,
    s0g: EvaluationResult,
    s0l: EvaluationResult,
    ids1: list[str],
    g_fpr: np.ndarray,
    l_fpr: np.ndarray,
) -> dict[str, Any]:
    """Return the sidecar metadata dict for Figure 1 (per-device FPR: GLOBAL vs LOCAL, representative seed)."""
    return {
        SidecarField.FIGURE: FigureName.FIGURE_1.value,
        SidecarField.TITLE: "Per-device FPR: GLOBAL_THRESHOLD vs LOCAL_THRESHOLD, NBAIOT_MAIN — representative seed, descriptive only",
        SidecarField.DATASET: DatasetID.NBAIOT.value,
        SidecarField.STAGE: ExperimentStage.NBAIOT_MAIN.value,
        SidecarField.SEED: s0g.seed,
        SidecarField.SEEDS: [s0g.seed],
        SidecarField.SOURCE_METRICS_FILES: [
            str(_result_path(base_dir, ExperimentStage.NBAIOT_MAIN, ThresholdPolicy.GLOBAL_THRESHOLD, s0g.seed)),
            str(_result_path(base_dir, ExperimentStage.NBAIOT_MAIN, ThresholdPolicy.LOCAL_THRESHOLD, s0l.seed)),
        ],
        SidecarField.RUN_IDS: [
            f"{ExperimentStage.NBAIOT_MAIN.value}_global_threshold_seed{s0g.seed}",
            f"{ExperimentStage.NBAIOT_MAIN.value}_local_threshold_seed{s0l.seed}",
        ],
        SidecarField.ALPHAS: [],
        SidecarField.ELIGIBLE_COUNTS: {
            ThresholdPolicy.GLOBAL_THRESHOLD.value: s0g.eligible_count,
            ThresholdPolicy.LOCAL_THRESHOLD.value: s0l.eligible_count,
        },
        SidecarField.CLIENT_COUNTS: {
            ThresholdPolicy.GLOBAL_THRESHOLD.value: s0g.client_count,
            ThresholdPolicy.LOCAL_THRESHOLD.value: s0l.client_count,
        },
        SidecarField.COVERAGE_RATIOS: {
            ThresholdPolicy.GLOBAL_THRESHOLD.value: s0g.coverage_ratio,
            ThresholdPolicy.LOCAL_THRESHOLD.value: s0l.coverage_ratio,
        },
        SidecarField.METRIC_NAMES: [MetricName.FPR.value],
        SidecarField.EVIDENCE_ROLE: EvidenceRole.DESCRIPTIVE.value,
        SidecarField.SEED_SCOPE: SeedScope.REPRESENTATIVE_SEED.value,
        SidecarField.NOT_CONFIRMATORY_WARNING: NOT_CONFIRMATORY_WARNING,
        SidecarField.VALIDATION_STATUS: AuditStatus.PASS.value,
        SidecarField.POLICIES: [ThresholdPolicy.GLOBAL_THRESHOLD.value, ThresholdPolicy.LOCAL_THRESHOLD.value],
        SidecarField.POLICY_ORDER: [ThresholdPolicy.GLOBAL_THRESHOLD.value, ThresholdPolicy.LOCAL_THRESHOLD.value],
        SidecarField.ELIGIBILITY_POLICY: "eligible-client intersection",
        SidecarField.AXIS_LABELS: {"x": "Device", "y": "FPR"},
        SidecarField.CLIENTS: [
            {
                SidecarField.CLIENT_ID: cid,
                ThresholdPolicy.GLOBAL_THRESHOLD.value: float(gv),
                ThresholdPolicy.LOCAL_THRESHOLD.value: float(lv),
            }
            for cid, gv, lv in zip(ids1, g_fpr, l_fpr)
        ],
    }


def _figure2_sidecar_data(
    base_dir: Path,
    s0g: EvaluationResult,
    tau_g: float,
    max_points: int,
    rep: list[str],
) -> dict[str, Any]:
    """Return the sidecar metadata dict for Figure 2 (calibration-error ECDF, representative seed)."""
    return {
        SidecarField.FIGURE: FigureName.FIGURE_2.value,
        SidecarField.TITLE: "Calibration-error ECDF for three representative N-BaIoT clients with GLOBAL_THRESHOLD client-averaged threshold — representative seed, descriptive only",
        SidecarField.DATASET: DatasetID.NBAIOT.value,
        SidecarField.STAGE: ExperimentStage.NBAIOT_MAIN.value,
        SidecarField.SEED: s0g.seed,
        SidecarField.SEEDS: [s0g.seed],
        SidecarField.SOURCE_METRICS_FILES: [
            str(_result_path(base_dir, ExperimentStage.NBAIOT_MAIN, ThresholdPolicy.GLOBAL_THRESHOLD, s0g.seed))
        ],
        SidecarField.SOURCE_SCORE_MANIFESTS: [
            str(
                ArtifactLayout(base_dir=base_dir, stage=ExperimentStage.NBAIOT_MAIN)
                .score_cell(TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=s0g.seed))
                .manifest_path
            )
        ],
        SidecarField.RUN_IDS: [f"{ExperimentStage.NBAIOT_MAIN.value}_global_threshold_seed{s0g.seed}"],
        SidecarField.ALPHAS: [],
        SidecarField.ELIGIBLE_COUNTS: {ThresholdPolicy.GLOBAL_THRESHOLD.value: s0g.eligible_count},
        SidecarField.CLIENT_COUNTS: {ThresholdPolicy.GLOBAL_THRESHOLD.value: s0g.client_count},
        SidecarField.COVERAGE_RATIOS: {ThresholdPolicy.GLOBAL_THRESHOLD.value: s0g.coverage_ratio},
        SidecarField.METRIC_NAMES: [SCORE_COLUMN, PayloadKey.THRESHOLD_VALUE],
        SidecarField.EVIDENCE_ROLE: EvidenceRole.DESCRIPTIVE.value,
        SidecarField.SEED_SCOPE: SeedScope.REPRESENTATIVE_SEED.value,
        SidecarField.NOT_CONFIRMATORY_WARNING: NOT_CONFIRMATORY_WARNING,
        SidecarField.VALIDATION_STATUS: AuditStatus.PASS.value,
        SidecarField.POLICIES: [ThresholdPolicy.GLOBAL_THRESHOLD.value],
        SidecarField.POLICY_ORDER: [ThresholdPolicy.GLOBAL_THRESHOLD.value],
        SidecarField.ELIGIBILITY_POLICY: f"selected eligible clients from GLOBAL_THRESHOLD seed {s0g.seed}",
        SidecarField.AXIS_LABELS: {"x": "Reconstruction Error", "y": "Density"},
        SidecarField.TAU_GLOBAL: tau_g,
        SidecarField.CLIENT_IDS: rep,
        SidecarField.MAX_POINTS_PER_CLIENT: max_points,
    }


def _figure3_sidecar_data(
    base_dir: Path,
    nbaiot: dict[ThresholdPolicy, list[EvaluationResult]],
    fpr_pol: dict[ThresholdPolicy, list[np.ndarray]],
    b_enums: tuple[ThresholdPolicy, ...],
    seeds: tuple[int, ...],
) -> dict[str, Any]:
    """Return the sidecar metadata dict for Figure 3 (per-client FPR distribution across all seeds)."""
    return {
        SidecarField.FIGURE: FigureName.FIGURE_3.value,
        SidecarField.TITLE: "Per-client FPR distribution, N-BaIoT main",
        SidecarField.DATASET: DatasetID.NBAIOT.value,
        SidecarField.STAGE: ExperimentStage.NBAIOT_MAIN.value,
        SidecarField.SOURCE_METRICS_FILES: [
            str(_result_path(base_dir, ExperimentStage.NBAIOT_MAIN, ThresholdPolicy(b), s))
            for b in [e.value for e in b_enums]
            for s in seeds
        ],
        SidecarField.RUN_IDS: [
            f"{ExperimentStage.NBAIOT_MAIN.value}_{b}_seed{s}"
            for b in [e.value for e in b_enums]
            for s in seeds
        ],
        SidecarField.SEEDS: list(seeds),
        SidecarField.ALPHAS: [],
        SidecarField.ELIGIBLE_COUNTS: {b.value: [r.eligible_count for r in nbaiot[b]] for b in b_enums},
        SidecarField.CLIENT_COUNTS: {b.value: [r.client_count for r in nbaiot[b]] for b in b_enums},
        SidecarField.COVERAGE_RATIOS: {b.value: [r.coverage_ratio for r in nbaiot[b]] for b in b_enums},
        SidecarField.METRIC_NAMES: [MetricName.FPR.value, "cv_fpr_delta_global_minus_local"],
        SidecarField.EVIDENCE_ROLE: EvidenceRole.DESCRIPTIVE_WITH_CONFIRMATORY_SIDECAR_DELTA.value,
        SidecarField.SEED_SCOPE: SeedScope.ALL_SEEDS.value,
        SidecarField.VALIDATION_STATUS: AuditStatus.PASS.value,
        SidecarField.POLICIES: [e.value for e in b_enums],
        SidecarField.PAIRED_SEED_CV_FPR_DELTA: [
            float(x)
            for x in _paired_deltas(nbaiot, ThresholdPolicy.GLOBAL_THRESHOLD, ThresholdPolicy.LOCAL_THRESHOLD)
        ],
        SidecarField.SEED_AGGREGATION_POLICY: "eligible-client FPR values pooled across configured seeds after intersection",
        SidecarField.POLICY_ORDER: [e.value for e in b_enums],
        SidecarField.ELIGIBILITY_POLICY: "eligible-client intersection within each seed",
        SidecarField.AXIS_LABELS: {"x": "ThresholdPolicy", "y": "FPR"},
        SidecarField.VALUES: {
            pol: [[float(x) for x in arr] for arr in arrays]
            for pol, arrays in fpr_pol.items()
        },
    }


def _convergence_summary_warnings(base_dir: Path, seeds: tuple[int, ...]) -> list[str]:
    """Return warnings for seeds that have a model checkpoint but no convergence summary."""
    layout = ArtifactLayout(base_dir=base_dir, stage=ExperimentStage.NBAIOT_MAIN)
    warnings = []
    for s in seeds:
        c_dir = layout.checkpoint_dir(TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=s))
        if (c_dir / ArtifactFile.MODEL_CHECKPOINT).exists():
            sum_f = c_dir / ArtifactFile.CONVERGENCE_SUMMARY
            if not sum_f.exists():
                warnings.append(f"Missing summary {sum_f}")
    return warnings


def build_figures(base_dir: Path, cfg: DatpConfig) -> BuildOutputs:
    """Generate figures 1-3 with sidecar JSON metadata from evaluation results."""
    fig_dir = base_dir / ArtifactDir.FIGURES
    fig_dir.mkdir(parents=True, exist_ok=True)
    nbaiot = _load_results(
        base_dir,
        ExperimentStage.NBAIOT_MAIN,
        tuple(sorted(CONTROLLED_POLICIES)),
        tuple(cfg.experiment.seeds),
        cfg.reporting.metric_tol,
    )

    s0g = nbaiot[ThresholdPolicy.GLOBAL_THRESHOLD][0]
    s0l = nbaiot[ThresholdPolicy.LOCAL_THRESHOLD][0]
    g_fpr, l_fpr, ids1 = _eligible_intersection_fprs(s0g, s0l)
    sc1 = write_json_atomic(
        fig_dir / f"{FigureName.FIGURE_1.value}_data.json",
        _figure1_sidecar_data(base_dir, s0g, s0l, ids1, g_fpr, l_fpr),
    )
    p1 = _save_figure_copies(
        fig_dir,
        FigureName.FIGURE_1.value,
        generate_figure1(dict(zip(ids1, g_fpr)), dict(zip(ids1, l_fpr)), fig_dir, s0g.seed, cfg.reporting.style),
    )

    s0g_fprs = _eligible_fprs(s0g)
    s_devs = sorted(s0g_fprs, key=lambda d: s0g_fprs[d])
    rep = [s_devs[0], s_devs[len(s_devs) // 2], s_devs[-1]]
    cal_errs: dict[str, np.ndarray] = {}
    rng = np.random.default_rng(cfg.reporting.figure2_rng_seed)
    sp = ScoreProvider(
        ArtifactLayout(base_dir=base_dir, stage=ExperimentStage.NBAIOT_MAIN)
        .score_cell(TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=s0g.seed))
        .score_dir
    )
    for dev in rep:
        v = sp.load(dev, ScoringStage.CAL)
        cal_errs[dev] = (
            rng.choice(v, size=cfg.reporting.figure2_max_points, replace=False)
            if v.size > cfg.reporting.figure2_max_points
            else v
        )
    tau_g = float(
        _load_json(
            _result_path(base_dir, ExperimentStage.NBAIOT_MAIN, ThresholdPolicy.GLOBAL_THRESHOLD, s0g.seed)
        )[MetricName.TAU_GLOBAL.value]
    )
    sc2 = write_json_atomic(
        fig_dir / f"{FigureName.FIGURE_2.value}_data.json",
        _figure2_sidecar_data(base_dir, s0g, tau_g, cfg.reporting.figure2_max_points, rep),
    )
    p2 = _save_figure_copies(
        fig_dir,
        FigureName.FIGURE_2.value,
        generate_figure2(cal_errs, tau_g, rep, fig_dir, cfg.reporting.style),
    )

    b_enums = (
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    )
    fpr_pol = _common_eligible_fprs(nbaiot, b_enums)
    sc3 = write_json_atomic(
        fig_dir / f"{FigureName.FIGURE_3.value}_data.json",
        _figure3_sidecar_data(base_dir, nbaiot, fpr_pol, b_enums, tuple(cfg.experiment.seeds)),
    )
    p3 = _save_figure_copies(
        fig_dir,
        FigureName.FIGURE_3.value,
        generate_figure3(fpr_pol, fig_dir, cfg.reporting.style),
    )

    return BuildOutputs([sc1, *p1, sc2, *p2, sc3, *p3])


def build_tables(base_dir: Path, cfg: DatpConfig) -> BuildOutputs:
    """Generate Table 3 LaTeX/CSV from N-BaIoT main evaluation results."""
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
    return BuildOutputs([t3, t3.with_suffix(".csv")])


def validate_results(base_dir: Path, cfg: DatpConfig) -> BuildOutputs:
    """Load and validate all metrics artifacts, writing a schema-validation JSON."""
    _load_results(
        base_dir,
        ExperimentStage.NBAIOT_MAIN,
        tuple(sorted(CONTROLLED_POLICIES)),
        tuple(cfg.experiment.seeds),
        cfg.reporting.metric_tol,
    )
    return BuildOutputs(
        [
            write_json_atomic(
                base_dir
                / ArtifactDir.ANALYSIS
                / ArtifactFile.METRICS_SCHEMA_VALIDATION,
                {
                    ValidationField.STATUS: AuditStatus.PASS.value,
                    ValidationField.SOURCE: "canonical per-client confusion-count reconstruction",
                    ValidationField.VALIDATED_STAGES: [
                        ExperimentStage.NBAIOT_MAIN.value,
                        ExperimentStage.SYNTHETIC_SMOKE.value,
                    ],
                    ValidationField.SEEDS: list(cfg.experiment.seeds),
                },
            )
        ]
    )


def build_all(base_dir: Path, cfg: DatpConfig) -> BuildOutputs:
    """Run all build steps (validate, stats, figures, tables) and write an audit report."""
    _REPORTING_SOURCES.clear()
    paths, failures = [], []
    for step in (validate_results, build_stats, build_figures, build_tables):
        try:
            paths.extend(step(base_dir, cfg).paths)
        except Exception as exc:
            failures.append(str(exc))
            break

    fig_dir = base_dir / ArtifactDir.FIGURES
    failures.extend(_validate_figure_sidecars(fig_dir))
    warnings = _convergence_summary_warnings(base_dir, tuple(cfg.experiment.seeds))

    paths.append(
        write_json_atomic(
            base_dir / ArtifactDir.ANALYSIS / ArtifactFile.REPORTING_AUDIT,
            {
                AuditField.SCHEMA_VERSION: REPORTING_AUDIT_SCHEMA_VERSION,
                AuditField.GENERATED_TABLES: [
                    str(p)
                    for p in paths
                    if p.suffix in {".tex", ".csv"}
                    and ArtifactDir.TABLES.value in p.parts
                ],
                AuditField.GENERATED_FIGURES: [
                    str(p)
                    for p in paths
                    if p.suffix in {".pdf", ".png", ".json"}
                    and ArtifactDir.FIGURES.value in p.parts
                ],
                AuditField.SOURCE_METRICS_FILES: sorted(_REPORTING_SOURCES),
                AuditField.SOURCE_SCORE_MANIFESTS: sorted(
                    str(
                        ArtifactLayout(
                            base_dir=base_dir, stage=ExperimentStage.NBAIOT_MAIN
                        )
                        .score_cell(
                            TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=s)
                        )
                        .manifest_path
                    )
                    for s in cfg.experiment.seeds
                ),
                AuditField.SOURCE_RUN_IDS: sorted(_REPORTING_SOURCES),
                AuditField.VALIDATION_RESULTS: AuditStatus.FAIL.value
                if failures
                else AuditStatus.PASS.value,
                AuditField.RECOMPUTATION_CHECKS: "canonical confusion-matrix recomputation during load",
                AuditField.COVERAGE_CHECKS: "explicit eligible_ids/pending_ids/eval_incomplete_ids required",
                AuditField.MISSING_FIELD_CHECKS: "validate_metrics_payload",
                AuditField.STALE_ARTIFACT_CHECKS: "schema/provenance/sidecar checks",
                AuditField.DESCRIPTIVE_FIGURE_CHECKS: f"representative-seed sidecar validation for {sorted(_REPRESENTATIVE_SEED_FIGURES)}",
                AuditField.CONVERGENCE_METADATA_CHECKS: "warn if absent alongside model.pt",
                AuditField.FIGURE_TABLE_OUTPUT_PATHS: [str(p) for p in paths],
                AuditField.WARNINGS: warnings,
                AuditField.FAILURES: failures,
            },
        )
    )

    if failures:
        raise ValueError(f"reporting_audit contains failures: {failures}")
    return BuildOutputs(paths)
