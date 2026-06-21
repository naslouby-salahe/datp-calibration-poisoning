from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

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
from datp.config.stages import ExperimentStage
from datp.core.enums import (
    CONTROLLED_POLICIES,
    RunKind,
    ScoringStage,
    SeedScope,
)
from datp.core.identity import (
    PolicyRunId,
    TrainingCellId,
)
from datp.core.metric_enums import (
    AuditField,
    ConfusionKey,
    MetricName,
    PayloadKey,
    ValidationField,
)
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
from datp.reporting.figures import (
    generate_figure1,
    generate_figure2,
    generate_figure3,
)
from datp.reporting.tables import generate_table3, generate_table4
from datp.scoring.loading import ScoreProvider
from datp.scoring.schema import SCORE_COLUMN
from datp.statistics.bootstrap import bootstrap_ci
from datp.statistics.enums import BootstrapField, StatsField
from datp.validation.enums import AuditStatus

_REPORTING_SOURCES: set[str] = set()

# Figures whose sidecars must declare representative_seed scope.
_REPRESENTATIVE_SEED_FIGURES: frozenset[str] = frozenset(
    {FigureName.FIGURE_1.value, FigureName.FIGURE_2.value}
)


@dataclass(frozen=True, slots=True)
class BuildOutputs:
    paths: list[Path]


@dataclass(frozen=True, slots=True)
class _ResultPathKey:
    base_dir: Path
    stage: ExperimentStage
    policy: ThresholdPolicy
    seed: int


@dataclass(frozen=True, slots=True)
class _LoadResultsParams:
    base_dir: Path
    stage: ExperimentStage
    policies: tuple[ThresholdPolicy, ...]
    seeds: tuple[int, ...]
    metric_tol: float


@dataclass(frozen=True, slots=True)
class _CalibrationErrorsParams:
    base_dir: Path
    seed: int
    device_ids: list[str]
    max_points: int
    rng_seed: int


@dataclass(frozen=True, slots=True)
class _DenominatorCheckParams:
    client_id: str
    row: Mapping[str, Any]
    tp: int
    fp: int
    tn: int
    fn: int


@dataclass(frozen=True, slots=True)
class _Figure1SidecarParams:
    base_dir: Path
    seed0_global: EvaluationResult
    seed0_local: EvaluationResult
    figure1_ids: list[str]
    global_seed0_fpr: np.ndarray
    local_seed0_fpr: np.ndarray


@dataclass(frozen=True, slots=True)
class _Figure2SidecarParams:
    base_dir: Path
    seed0_global: EvaluationResult
    rep_seed: int
    representative: list[str]
    figure2_max_points: int
    tau_global: float


@dataclass(frozen=True, slots=True)
class _AuditPayloadParams:
    base_dir: Path
    cfg: DatpConfig
    paths: list[Path]
    failures: list[str]
    conv_warnings: list[str]


def _result_path(key: _ResultPathKey) -> Path:
    run = PolicyRunId(
        cell=TrainingCellId(stage=key.stage, seed=key.seed),
        policy=key.policy,
    )
    return (
        ArtifactLayout(base_dir=key.base_dir, stage=key.stage)
        .policy_run(run)
        .result_dir
        / ArtifactFile.METRICS
    )


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"[reporting] Missing metrics artifact. Expected: {path}. Got: absent."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))

    run_kind = payload.get(PayloadKey.RUN_KIND)
    if run_kind != RunKind.CORE_LADDER.value:
        raise ValueError(
            f"[reporting] RunKind separation violation. Expected: {RunKind.CORE_LADDER.value}. "
            f"Got: {run_kind}. Artifact: {path}."
        )

    _REPORTING_SOURCES.add(str(path))
    failures = validate_metrics_payload(payload, module="reporting")
    if failures:
        raise ValueError("; ".join(failures) + f". Artifact: {path}.")
    return payload


def _extract_confusion_counts(
    client_id: str, confusion: Mapping[str, Any]
) -> tuple[int, int, int, int]:
    """Parse and validate tp/fp/tn/fn from a confusion dict. Raises ValueError on missing keys."""
    missing = [
        k
        for k in (ConfusionKey.TP, ConfusionKey.FP, ConfusionKey.TN, ConfusionKey.FN)
        if k not in confusion
    ]
    if missing:
        raise ValueError(
            f"[reporting] Missing confusion counts. Expected: tp/fp/tn/fn for {client_id}. Got: missing={missing}."
        )
    return (
        int(confusion[ConfusionKey.TP]),
        int(confusion[ConfusionKey.FP]),
        int(confusion[ConfusionKey.TN]),
        int(confusion[ConfusionKey.FN]),
    )


def _validate_denominator_row(params: _DenominatorCheckParams) -> None:
    """Check n_benign / n_attack denominators against recomputed counts."""
    if (
        PayloadKey.N_BENIGN in params.row
        and int(params.row[PayloadKey.N_BENIGN]) != params.fp + params.tn
    ):
        raise ValueError(
            f"[reporting] Benign denominator mismatch. Expected: fp+tn={params.fp + params.tn} for {params.client_id}. Got: {params.row[PayloadKey.N_BENIGN]}."
        )
    if (
        PayloadKey.N_ATTACK in params.row
        and int(params.row[PayloadKey.N_ATTACK]) != params.tp + params.fn
    ):
        raise ValueError(
            f"[reporting] Attack denominator mismatch. Expected: tp+fn={params.tp + params.fn} for {params.client_id}. Got: {params.row[PayloadKey.N_ATTACK]}."
        )


def _client_records_from_payload(
    payload: dict[str, Any],
) -> tuple[ClientEvaluationRecord, ...]:
    records: list[ClientEvaluationRecord] = []
    policy = ThresholdPolicy(payload[PayloadKey.POLICY])
    for client_id, row in client_rows(payload):
        tp, fp, tn, fn = _extract_confusion_counts(
            client_id, row[PayloadKey.CONFUSION_MATRIX]
        )
        _validate_denominator_row(
            _DenominatorCheckParams(
                client_id=client_id,
                row=row,
                tp=tp,
                fp=fp,
                tn=tn,
                fn=fn,
            )
        )
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


def _check_float_agreement(key: str, saved: float, value: float, tol: float) -> None:
    """Raise ValueError if saved and value disagree, accounting for NaN parity."""
    if np.isnan(saved) and np.isnan(value):
        return
    if np.isnan(saved) != np.isnan(value):
        raise ValueError(
            f"[reporting] Metric schema mismatch. Expected: {key}={value}. Got: {saved}."
        )
    if abs(saved - value) > tol:
        raise ValueError(
            f"[reporting] Metric schema mismatch. Expected: {key}={value:.12g} from canonical counts. Got: {saved:.12g}."
        )


def _assert_metric_matches(
    payload: dict[str, Any],
    key: str,
    value: float,
    metric_tol: float,
) -> None:
    saved_raw = payload.get(key)
    if saved_raw is None:
        raise ValueError(
            f"[reporting] Missing metric field. Expected: {key}. Got: absent."
        )
    _check_float_agreement(key, float(saved_raw), value, metric_tol)


def _evaluation_from_payload(
    payload: dict[str, Any], metric_tol: float
) -> EvaluationResult:
    clients = _client_records_from_payload(payload)
    eligible_ids = tuple(
        str(client_id) for client_id in payload[PayloadKey.ELIGIBLE_IDS]
    )
    pending_ids = tuple(str(client_id) for client_id in payload[PayloadKey.PENDING_IDS])
    incomplete_ids = tuple(
        str(client_id) for client_id in payload[PayloadKey.EVAL_INCOMPLETE_IDS]
    )
    result = build_evaluation_result(
        policy=ThresholdPolicy(payload[PayloadKey.POLICY]),
        stage=ExperimentStage(
            payload.get(PayloadKey.STAGE, ExperimentStage.NBAIOT_MAIN.value)
        ),
        seed=int(payload[PayloadKey.SEED]),
        clients=clients,
        eligible_ids=eligible_ids,
        pending_ids=pending_ids,
        incomplete_ids=incomplete_ids,
    )
    _assert_metric_matches(
        payload, PayloadKey.COVERAGE_RATIO, result.coverage_ratio, metric_tol
    )
    _assert_metric_matches(payload, MetricName.CV_FPR.value, result.cv_fpr, metric_tol)
    _assert_metric_matches(
        payload, MetricName.MEAN_FPR.value, result.mean_fpr, metric_tol
    )
    _assert_metric_matches(
        payload, MetricName.STD_FPR.value, result.std_fpr, metric_tol
    )
    _assert_metric_matches(payload, MetricName.CV_TPR.value, result.cv_tpr, metric_tol)
    _assert_metric_matches(
        payload, MetricName.IQR_FPR.value, result.iqr_fpr, metric_tol
    )
    _assert_metric_matches(
        payload, MetricName.IQR_TPR.value, result.iqr_tpr, metric_tol
    )
    _assert_metric_matches(
        payload, MetricName.WORST_CLIENT_FPR.value, result.worst_client_fpr, metric_tol
    )
    _assert_metric_matches(
        payload, MetricName.WORST_BA.value, result.worst_ba, metric_tol
    )
    _assert_metric_matches(
        payload, MetricName.P10_MACRO_F1.value, result.p10_macro_f1, metric_tol
    )
    if int(payload[PayloadKey.ELIGIBLE_COUNT]) != result.eligible_count:
        raise ValueError(
            f"[reporting] Eligibility count mismatch. Expected: {result.eligible_count}. Got: {payload[PayloadKey.ELIGIBLE_COUNT]}."
        )
    if int(payload[PayloadKey.CLIENT_COUNT]) != result.client_count:
        raise ValueError(
            f"[reporting] Client count mismatch. Expected: {result.client_count}. Got: {payload[PayloadKey.CLIENT_COUNT]}."
        )
    return result


def _load_results(
    params: _LoadResultsParams,
) -> dict[ThresholdPolicy, list[EvaluationResult]]:
    loaded: dict[ThresholdPolicy, list[EvaluationResult]] = {}
    for policy in params.policies:
        loaded[policy] = []
        for seed in params.seeds:
            key = _ResultPathKey(
                base_dir=params.base_dir,
                stage=params.stage,
                policy=policy,
                seed=seed,
            )
            path = _result_path(key)
            try:
                loaded[policy].append(
                    _evaluation_from_payload(_load_json(path), params.metric_tol)
                )
            except ValueError as exc:
                raise ValueError(f"{exc} Artifact: {path}.") from exc
    return loaded


def _cv_fpr(result: EvaluationResult) -> float:
    return float(result.cv_fpr)


def _eligible_fprs(result: EvaluationResult) -> dict[str, float]:
    eligible = set(result.eligible_ids)
    return {
        c.client_id: c.metrics.fpr for c in result.clients if c.client_id in eligible
    }


def _eligible_intersection_fprs(
    left: EvaluationResult, right: EvaluationResult
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    left_map = _eligible_fprs(left)
    right_map = _eligible_fprs(right)
    ids = sorted(set(left_map) & set(right_map))
    if not ids:
        raise ValueError(
            f"[reporting] No eligible-client intersection. Expected: shared eligible clients for {left.policy} vs {right.policy}. Got: empty."
        )
    left_missing = sorted(set(left_map) - set(ids))
    right_missing = sorted(set(right_map) - set(ids))
    if left_missing or right_missing:
        raise ValueError(
            f"[reporting] Eligible-client set mismatch. Expected: identical eligible-client sets for controlled comparison. Got: left_only={left_missing}, right_only={right_missing}."
        )
    return (
        np.array([left_map[cid] for cid in ids], dtype=np.float64),
        np.array([right_map[cid] for cid in ids], dtype=np.float64),
        ids,
    )


def _bootstrap_payload(
    deltas: np.ndarray, n_bootstrap: int, ci: float, bootstrap_seed: int
) -> dict[str, Any]:
    result = bootstrap_ci(deltas, n_bootstrap=n_bootstrap, ci=ci, seed=bootstrap_seed)
    return {
        BootstrapField.PER_SEED_DELTAS: [float(x) for x in deltas],
        BootstrapField.MEAN_DELTA: result.mean_delta,
        BootstrapField.CI_LOWER: result.ci_lower,
        BootstrapField.CI_UPPER: result.ci_upper,
        BootstrapField.CI: ci,
        BootstrapField.EXCLUDES_ZERO: result.excludes_zero,
        BootstrapField.N_BOOTSTRAP: result.n_bootstrap,
        BootstrapField.N_SEEDS: result.n_seeds,
    }


def _paired_deltas(
    results: dict[ThresholdPolicy, list[EvaluationResult]],
    left: ThresholdPolicy,
    right: ThresholdPolicy,
) -> np.ndarray:
    return np.array(
        [
            _cv_fpr(results[left][idx]) - _cv_fpr(results[right][idx])
            for idx in range(len(results[left]))
        ]
    )


def _intersect_eligible_ids(
    maps: dict[ThresholdPolicy, dict[str, float]], policies: tuple[ThresholdPolicy, ...]
) -> list[str]:
    """Return sorted common eligible-client IDs across policies; raise on empty or asymmetric sets."""
    ids = sorted(set.intersection(*(set(maps[p]) for p in policies)))
    if not ids:
        raise ValueError(
            f"[reporting] No eligible-client intersection. Expected: shared eligible clients for {policies}. Got: empty."
        )
    for policy in policies:
        missing = sorted(set(maps[policy]) - set(ids))
        if missing:
            raise ValueError(
                f"[reporting] Eligible-client set mismatch. Expected: identical eligible-client sets for {policies}. Got: policy={policy} extra={missing}."
            )
    return ids


def _common_eligible_fprs(
    results: dict[ThresholdPolicy, list[EvaluationResult]],
    policies: tuple[ThresholdPolicy, ...],
) -> dict[ThresholdPolicy, list[np.ndarray]]:
    out: dict[ThresholdPolicy, list[np.ndarray]] = {policy: [] for policy in policies}
    for idx in range(len(results[policies[0]])):
        maps = {p: _eligible_fprs(results[p][idx]) for p in policies}
        ids = _intersect_eligible_ids(maps, policies)
        for policy in policies:
            out[policy].append(
                np.array([maps[policy][cid] for cid in ids], dtype=np.float64)
            )
    return out


def _write_figure_data(output_dir: Path, stem: str, payload: dict[str, Any]) -> Path:
    return write_json_atomic(output_dir / f"{stem}_data.json", payload)


def _save_figure_copies(
    figures_dir: Path, figure_stem: str, generated_png: Path
) -> list[Path]:
    """Save canonical .png and .pdf copies of a generated figure alongside the original."""
    png_path = figures_dir / f"{figure_stem}.png"
    pdf_path = figures_dir / f"{figure_stem}.pdf"
    shutil.copyfile(generated_png, png_path)
    shutil.copyfile(generated_png.with_suffix(".pdf"), pdf_path)
    return [generated_png, png_path, pdf_path]


@dataclass(frozen=True, slots=True)
class _HeterogeneityContextParams:
    bootstrap_payload: dict[str, Any]
    nbaiot_results: dict[ThresholdPolicy, list[EvaluationResult]]
    base_dir: Path
    practical_significance_threshold: float
    seeds: tuple[int, ...]
    metric_tol: float


def _load_iid_global_mean() -> tuple[float | None, bool]:
    """IID comparison is out of scope; returns (None, False)."""
    return None, False


def _practical_significance(
    global_natural_mean: float,
    global_iid_mean: float | None,
    threshold: float,
) -> tuple[float | None, bool]:
    """Return (natural_minus_iid, practical_significance_met)."""
    if global_iid_mean is None:
        return None, False
    delta = global_natural_mean - global_iid_mean
    return delta, delta >= threshold


def _heterogeneity_context_label(
    primary_ci_excludes_zero: bool, practical_significance_met: bool
) -> str:
    if primary_ci_excludes_zero and practical_significance_met:
        return HeterogeneityContextResult.CONTEXT_SUPPORTS.value
    if primary_ci_excludes_zero or practical_significance_met:
        return HeterogeneityContextResult.PARTIAL_CONTEXT.value
    return HeterogeneityContextResult.CONTEXT_NOT_AVAILABLE.value


def _check_heterogeneity_context(params: _HeterogeneityContextParams) -> dict[str, Any]:
    """IID and CICIoT comparisons are out of scope; returns heterogeneity context based on N-BaIoT only."""
    primary_ci_excludes_zero: bool = bool(
        params.bootstrap_payload[StatsField.PRIMARY_ENDPOINT][
            BootstrapField.EXCLUDES_ZERO
        ]
    )
    global_natural_mean = (
        float(
            np.mean(
                [
                    _cv_fpr(r)
                    for r in params.nbaiot_results[ThresholdPolicy.GLOBAL_THRESHOLD]
                ]
            )
        )
        if params.nbaiot_results.get(ThresholdPolicy.GLOBAL_THRESHOLD)
        else float("nan")
    )
    global_iid_mean, iid_data_available = _load_iid_global_mean()
    natural_minus_iid, practical_significance_met = _practical_significance(
        global_natural_mean, global_iid_mean, params.practical_significance_threshold
    )
    context_result = _heterogeneity_context_label(
        primary_ci_excludes_zero, practical_significance_met
    )

    return {
        StatsField.CONDITION: (
            "IID and CICIoT comparisons are heterogeneity context/support checks, "
            "not the confirmatory endpoint."
        ),
        StatsField.GLOBAL_CV_FPR_MEAN: global_natural_mean,
        StatsField.NATURAL_MINUS_IID: natural_minus_iid,
        StatsField.PRACTICAL_SIGNIFICANCE_THRESHOLD: params.practical_significance_threshold,
        StatsField.PRACTICAL_SIGNIFICANCE_MET: practical_significance_met,
        StatsField.IID_DATA_AVAILABLE: iid_data_available,
        StatsField.PRIMARY_ENDPOINT_CI_EXCLUDES_ZERO: primary_ci_excludes_zero,
        StatsField.CONTEXT_RESULT: context_result,
        StatsField.NOTE: (
            "Primary endpoint: NBAIOT_MAIN, GLOBAL_THRESHOLD vs LOCAL_THRESHOLD, CV(FPR), per-seed bootstrap CI. "
            "IID and CICIoT comparisons are heterogeneity context/support checks, not the confirmatory endpoint."
        ),
    }


def _convergence_summary_warnings(base_dir: Path, seeds: tuple[int, ...]) -> list[str]:
    warnings_list: list[str] = []
    for stage in (ExperimentStage.NBAIOT_MAIN,):
        layout = ArtifactLayout(base_dir=base_dir, stage=stage)
        for seed in seeds:
            ckpt_dir = layout.checkpoint_dir(TrainingCellId(stage=stage, seed=seed))
            model_pt = ckpt_dir / ArtifactFile.MODEL_CHECKPOINT
            summary = ckpt_dir / ArtifactFile.CONVERGENCE_SUMMARY
            if model_pt.exists() and not summary.exists():
                warnings_list.append(
                    f"[reporting] Missing {ArtifactFile.CONVERGENCE_SUMMARY} for {stage.value} seed {seed}. "
                    f"Expected: {summary}. Got: absent."
                )
    return warnings_list


def _build_stats_payload(
    nbaiot_results: dict[ThresholdPolicy, list[EvaluationResult]],
    n_bootstrap: int,
    ci: float,
    bootstrap_seed: int,
) -> dict[str, Any]:
    return {
        StatsField.PRIMARY_ENDPOINT: {
            StatsField.CONDITION: "Primary endpoint: NBAIOT_MAIN, GLOBAL_THRESHOLD vs LOCAL_THRESHOLD, CV(FPR), per-seed bootstrap CI.",
            **_bootstrap_payload(
                _paired_deltas(
                    nbaiot_results,
                    ThresholdPolicy.GLOBAL_THRESHOLD,
                    ThresholdPolicy.LOCAL_THRESHOLD,
                ),
                n_bootstrap,
                ci,
                bootstrap_seed,
            ),
        },
        "secondary_nbaiot": {
            ComparisonLabel.GLOBAL_VS_CLUSTER.value: _bootstrap_payload(
                _paired_deltas(
                    nbaiot_results,
                    ThresholdPolicy.GLOBAL_THRESHOLD,
                    ThresholdPolicy.CLUSTER_THRESHOLD,
                ),
                n_bootstrap,
                ci,
                bootstrap_seed,
            ),
            ComparisonLabel.CLUSTER_VS_LOCAL.value: _bootstrap_payload(
                _paired_deltas(
                    nbaiot_results,
                    ThresholdPolicy.CLUSTER_THRESHOLD,
                    ThresholdPolicy.LOCAL_THRESHOLD,
                ),
                n_bootstrap,
                ci,
                bootstrap_seed,
            ),
        },
        "secondary_nbaiot_additional": {
            ComparisonLabel.GLOBAL_VS_LOCAL.value: _bootstrap_payload(
                _paired_deltas(
                    nbaiot_results,
                    ThresholdPolicy.GLOBAL_THRESHOLD,
                    ThresholdPolicy.LOCAL_THRESHOLD,
                ),
                n_bootstrap,
                ci,
                bootstrap_seed,
            ),
            ComparisonLabel.GLOBAL_VS_CLUSTER.value: _bootstrap_payload(
                _paired_deltas(
                    nbaiot_results,
                    ThresholdPolicy.GLOBAL_THRESHOLD,
                    ThresholdPolicy.CLUSTER_THRESHOLD,
                ),
                n_bootstrap,
                ci,
                bootstrap_seed,
            ),
        },
    }


def _write_stats_csv(csv_path: Path, payload: dict[str, Any]) -> None:
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
        for scope in ("secondary_nbaiot", "secondary_nbaiot_additional"):
            for comparison, stats in payload[scope].items():
                writer.writerow(
                    [
                        scope,
                        comparison,
                        stats[BootstrapField.MEAN_DELTA],
                        stats[BootstrapField.CI_LOWER],
                        stats[BootstrapField.CI_UPPER],
                        stats[BootstrapField.EXCLUDES_ZERO],
                    ]
                )


def build_stats(base_dir: Path, cfg: DatpConfig) -> BuildOutputs:
    seeds = tuple(cfg.experiment.seeds)
    n_bootstrap = cfg.statistics.n_bootstrap
    bootstrap_seed = cfg.statistics.bootstrap_seed
    ci = cfg.statistics.ci_level
    metric_tol = cfg.reporting.metric_tol

    analysis_dir = base_dir / ArtifactDir.ANALYSIS
    analysis_dir.mkdir(parents=True, exist_ok=True)

    nbaiot_policies = tuple(sorted(CONTROLLED_POLICIES))

    nbaiot_results = _load_results(
        _LoadResultsParams(
            base_dir=base_dir,
            stage=ExperimentStage.NBAIOT_MAIN,
            policies=nbaiot_policies,
            seeds=seeds,
            metric_tol=metric_tol,
        )
    )

    payload = _build_stats_payload(nbaiot_results, n_bootstrap, ci, bootstrap_seed)
    payload[StatsField.HETEROGENEITY_CONTEXT_CHECK] = _check_heterogeneity_context(
        _HeterogeneityContextParams(
            bootstrap_payload=payload,
            nbaiot_results=nbaiot_results,
            base_dir=base_dir,
            practical_significance_threshold=cfg.statistics.dispersion_threshold,
            seeds=seeds,
            metric_tol=metric_tol,
        )
    )

    json_path = write_json_atomic(
        analysis_dir / ArtifactFile.BOOTSTRAP_CIS_JSON, payload
    )
    csv_path = analysis_dir / ArtifactFile.BOOTSTRAP_CIS_CSV
    _write_stats_csv(csv_path, payload)

    return BuildOutputs(paths=[json_path, csv_path])


def _calibration_errors_for_devices(
    params: _CalibrationErrorsParams,
) -> dict[str, np.ndarray]:
    errors: dict[str, np.ndarray] = {}
    rng = np.random.default_rng(params.rng_seed)
    layout = ArtifactLayout(base_dir=params.base_dir, stage=ExperimentStage.NBAIOT_MAIN)
    cell = TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=params.seed)
    score_provider = ScoreProvider(layout.score_cell(cell).score_dir)
    for device_id in params.device_ids:
        values = score_provider.load(device_id, ScoringStage.CAL)
        if values.size > params.max_points:
            values = rng.choice(values, size=params.max_points, replace=False)
        errors[device_id] = values
    return errors


def _build_figure1_sidecar(params: _Figure1SidecarParams) -> dict[str, Any]:
    return {
        SidecarField.FIGURE: FigureName.FIGURE_1.value,
        SidecarField.TITLE: "Per-device FPR: GLOBAL_THRESHOLD vs LOCAL_THRESHOLD, NBAIOT_MAIN — representative seed, descriptive only",
        SidecarField.DATASET: DatasetID.NBAIOT.value,
        SidecarField.STAGE: ExperimentStage.NBAIOT_MAIN.value,
        SidecarField.SEED: params.seed0_global.seed,
        SidecarField.SEEDS: [params.seed0_global.seed],
        SidecarField.SOURCE_METRICS_FILES: [
            str(
                _result_path(
                    _ResultPathKey(
                        params.base_dir,
                        ExperimentStage.NBAIOT_MAIN,
                        ThresholdPolicy.GLOBAL_THRESHOLD,
                        params.seed0_global.seed,
                    )
                )
            ),
            str(
                _result_path(
                    _ResultPathKey(
                        params.base_dir,
                        ExperimentStage.NBAIOT_MAIN,
                        ThresholdPolicy.LOCAL_THRESHOLD,
                        params.seed0_local.seed,
                    )
                )
            ),
        ],
        SidecarField.RUN_IDS: [
            f"{ExperimentStage.NBAIOT_MAIN.value}_global_threshold_seed{params.seed0_global.seed}",
            f"{ExperimentStage.NBAIOT_MAIN.value}_local_threshold_seed{params.seed0_local.seed}",
        ],
        SidecarField.ALPHAS: [],
        SidecarField.ELIGIBLE_COUNTS: {
            ThresholdPolicy.GLOBAL_THRESHOLD.value: params.seed0_global.eligible_count,
            ThresholdPolicy.LOCAL_THRESHOLD.value: params.seed0_local.eligible_count,
        },
        SidecarField.CLIENT_COUNTS: {
            ThresholdPolicy.GLOBAL_THRESHOLD.value: params.seed0_global.client_count,
            ThresholdPolicy.LOCAL_THRESHOLD.value: params.seed0_local.client_count,
        },
        SidecarField.COVERAGE_RATIOS: {
            ThresholdPolicy.GLOBAL_THRESHOLD.value: params.seed0_global.coverage_ratio,
            ThresholdPolicy.LOCAL_THRESHOLD.value: params.seed0_local.coverage_ratio,
        },
        SidecarField.METRIC_NAMES: [MetricName.FPR.value],
        SidecarField.EVIDENCE_ROLE: EvidenceRole.DESCRIPTIVE.value,
        SidecarField.SEED_SCOPE: SeedScope.REPRESENTATIVE_SEED.value,
        SidecarField.NOT_CONFIRMATORY_WARNING: NOT_CONFIRMATORY_WARNING,
        SidecarField.VALIDATION_STATUS: AuditStatus.PASS.value,
        SidecarField.POLICIES: [
            ThresholdPolicy.GLOBAL_THRESHOLD.value,
            ThresholdPolicy.LOCAL_THRESHOLD.value,
        ],
        SidecarField.POLICY_ORDER: [
            ThresholdPolicy.GLOBAL_THRESHOLD.value,
            ThresholdPolicy.LOCAL_THRESHOLD.value,
        ],
        SidecarField.ELIGIBILITY_POLICY: "eligible-client intersection",
        SidecarField.AXIS_LABELS: {"x": "Device", "y": "FPR"},
        SidecarField.CLIENTS: [
            {
                SidecarField.CLIENT_ID: cid,
                ThresholdPolicy.GLOBAL_THRESHOLD.value: float(global_val),
                ThresholdPolicy.LOCAL_THRESHOLD.value: float(local_val),
            }
            for cid, global_val, local_val in zip(
                params.figure1_ids,
                params.global_seed0_fpr,
                params.local_seed0_fpr,
                strict=True,
            )
        ],
    }


def _build_figure2_sidecar(params: _Figure2SidecarParams) -> dict[str, Any]:
    return {
        SidecarField.FIGURE: FigureName.FIGURE_2.value,
        SidecarField.TITLE: "Calibration-error ECDF for three representative N-BaIoT clients with GLOBAL_THRESHOLD client-averaged threshold — representative seed, descriptive only",
        SidecarField.DATASET: DatasetID.NBAIOT.value,
        SidecarField.STAGE: ExperimentStage.NBAIOT_MAIN.value,
        SidecarField.SEED: params.rep_seed,
        SidecarField.SEEDS: [params.rep_seed],
        SidecarField.SOURCE_METRICS_FILES: [
            str(
                _result_path(
                    _ResultPathKey(
                        params.base_dir,
                        ExperimentStage.NBAIOT_MAIN,
                        ThresholdPolicy.GLOBAL_THRESHOLD,
                        params.rep_seed,
                    )
                )
            )
        ],
        SidecarField.SOURCE_SCORE_MANIFESTS: [
            str(
                ArtifactLayout(
                    base_dir=params.base_dir, stage=ExperimentStage.NBAIOT_MAIN
                )
                .score_cell(
                    TrainingCellId(
                        stage=ExperimentStage.NBAIOT_MAIN, seed=params.rep_seed
                    )
                )
                .manifest_path
            )
        ],
        SidecarField.RUN_IDS: [
            f"{ExperimentStage.NBAIOT_MAIN.value}_global_threshold_seed{params.rep_seed}"
        ],
        SidecarField.ALPHAS: [],
        SidecarField.ELIGIBLE_COUNTS: {
            ThresholdPolicy.GLOBAL_THRESHOLD.value: params.seed0_global.eligible_count
        },
        SidecarField.CLIENT_COUNTS: {
            ThresholdPolicy.GLOBAL_THRESHOLD.value: params.seed0_global.client_count
        },
        SidecarField.COVERAGE_RATIOS: {
            ThresholdPolicy.GLOBAL_THRESHOLD.value: params.seed0_global.coverage_ratio
        },
        SidecarField.METRIC_NAMES: [SCORE_COLUMN, PayloadKey.THRESHOLD_VALUE],
        SidecarField.EVIDENCE_ROLE: EvidenceRole.DESCRIPTIVE.value,
        SidecarField.SEED_SCOPE: SeedScope.REPRESENTATIVE_SEED.value,
        SidecarField.NOT_CONFIRMATORY_WARNING: NOT_CONFIRMATORY_WARNING,
        SidecarField.VALIDATION_STATUS: AuditStatus.PASS.value,
        SidecarField.POLICIES: [ThresholdPolicy.GLOBAL_THRESHOLD.value],
        SidecarField.POLICY_ORDER: [ThresholdPolicy.GLOBAL_THRESHOLD.value],
        SidecarField.ELIGIBILITY_POLICY: f"selected eligible clients from GLOBAL_THRESHOLD seed {params.rep_seed}",
        SidecarField.AXIS_LABELS: {"x": "Reconstruction Error", "y": "Density"},
        SidecarField.TAU_GLOBAL: params.tau_global,
        SidecarField.CLIENT_IDS: params.representative,
        SidecarField.MAX_POINTS_PER_CLIENT: params.figure2_max_points,
    }


def _figure3_source_metrics_files(
    base_dir: Path,
    b_values: tuple[str, ...],
    seeds: tuple[int, ...],
) -> list[str]:
    return [
        str(
            _result_path(
                _ResultPathKey(
                    base_dir, ExperimentStage.NBAIOT_MAIN, ThresholdPolicy(b), seed
                )
            )
        )
        for b in b_values
        for seed in seeds
    ]


def _figure3_run_ids(b_values: tuple[str, ...], seeds: tuple[int, ...]) -> list[str]:
    return [
        f"{ExperimentStage.NBAIOT_MAIN.value}_{b}_seed{seed}"
        for b in b_values
        for seed in seeds
    ]


def _figure3_per_policy_counts(
    nbaiot_results: dict[ThresholdPolicy, list[EvaluationResult]],
    b_enums: tuple[ThresholdPolicy, ...],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    eligible_counts = {
        b.value: [r.eligible_count for r in nbaiot_results[b]] for b in b_enums
    }
    client_counts = {
        b.value: [r.client_count for r in nbaiot_results[b]] for b in b_enums
    }
    coverage_ratios = {
        b.value: [r.coverage_ratio for r in nbaiot_results[b]] for b in b_enums
    }
    return eligible_counts, client_counts, coverage_ratios


def _build_figure3_sidecar(
    base_dir: Path,
    nbaiot_results: dict[ThresholdPolicy, list[EvaluationResult]],
    fpr_by_policy: dict[ThresholdPolicy, list[Any]],
    seeds: tuple[int, ...],
) -> dict[str, Any]:
    b_values = (
        ThresholdPolicy.GLOBAL_THRESHOLD.value,
        ThresholdPolicy.LOCAL_THRESHOLD.value,
        ThresholdPolicy.CLUSTER_THRESHOLD.value,
    )
    b_enums = (
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    )
    eligible_counts, client_counts, coverage_ratios = _figure3_per_policy_counts(
        nbaiot_results, b_enums
    )
    return {
        SidecarField.FIGURE: FigureName.FIGURE_3.value,
        SidecarField.TITLE: "Per-client FPR distribution, N-BaIoT main",
        SidecarField.DATASET: DatasetID.NBAIOT.value,
        SidecarField.STAGE: ExperimentStage.NBAIOT_MAIN.value,
        SidecarField.SOURCE_METRICS_FILES: _figure3_source_metrics_files(
            base_dir, b_values, seeds
        ),
        SidecarField.RUN_IDS: _figure3_run_ids(b_values, seeds),
        SidecarField.SEEDS: list(seeds),
        SidecarField.ALPHAS: [],
        SidecarField.ELIGIBLE_COUNTS: eligible_counts,
        SidecarField.CLIENT_COUNTS: client_counts,
        SidecarField.COVERAGE_RATIOS: coverage_ratios,
        SidecarField.METRIC_NAMES: [
            MetricName.FPR.value,
            "cv_fpr_delta_global_minus_local",
        ],
        SidecarField.EVIDENCE_ROLE: EvidenceRole.DESCRIPTIVE_WITH_CONFIRMATORY_SIDECAR_DELTA.value,
        SidecarField.SEED_SCOPE: SeedScope.ALL_SEEDS.value,
        SidecarField.VALIDATION_STATUS: AuditStatus.PASS.value,
        SidecarField.POLICIES: list(b_values),
        SidecarField.PAIRED_SEED_CV_FPR_DELTA: [
            float(x)
            for x in _paired_deltas(
                nbaiot_results,
                ThresholdPolicy.GLOBAL_THRESHOLD,
                ThresholdPolicy.LOCAL_THRESHOLD,
            )
        ],
        SidecarField.SEED_AGGREGATION_POLICY: "eligible-client FPR values pooled across configured seeds after intersection",
        SidecarField.POLICY_ORDER: list(b_values),
        SidecarField.ELIGIBILITY_POLICY: "eligible-client intersection within each seed",
        SidecarField.AXIS_LABELS: {"x": "ThresholdPolicy", "y": "FPR"},
        SidecarField.VALUES: {
            policy: [[float(x) for x in arr] for arr in arrays]
            for policy, arrays in fpr_by_policy.items()
        },
    }


def _build_figure1(
    base_dir: Path,
    nbaiot_results: dict[ThresholdPolicy, list[EvaluationResult]],
    figures_dir: Path,
    style: Any,
) -> list[Path]:
    seed0_global = nbaiot_results[ThresholdPolicy.GLOBAL_THRESHOLD][0]
    seed0_local = nbaiot_results[ThresholdPolicy.LOCAL_THRESHOLD][0]
    global_seed0_fpr, local_seed0_fpr, figure1_ids = _eligible_intersection_fprs(
        seed0_global, seed0_local
    )
    sidecar_path = _write_figure_data(
        figures_dir,
        FigureName.FIGURE_1.value,
        _build_figure1_sidecar(
            _Figure1SidecarParams(
                base_dir=base_dir,
                seed0_global=seed0_global,
                seed0_local=seed0_local,
                figure1_ids=figure1_ids,
                global_seed0_fpr=global_seed0_fpr,
                local_seed0_fpr=local_seed0_fpr,
            )
        ),
    )
    fig1_png = generate_figure1(
        dict(zip(figure1_ids, global_seed0_fpr, strict=True)),
        dict(zip(figure1_ids, local_seed0_fpr, strict=True)),
        figures_dir,
        seed=seed0_global.seed,
        style=style,
    )
    return [
        sidecar_path,
        *_save_figure_copies(figures_dir, FigureName.FIGURE_1.value, fig1_png),
    ]


def _build_figure2(
    base_dir: Path,
    nbaiot_results: dict[ThresholdPolicy, list[EvaluationResult]],
    figures_dir: Path,
    style: Any,
    figure2_max_points: int,
    figure2_rng_seed: int,
) -> list[Path]:
    seed0_global = nbaiot_results[ThresholdPolicy.GLOBAL_THRESHOLD][0]
    seed0_global_fprs = _eligible_fprs(seed0_global)
    sorted_devices = sorted(
        seed0_global_fprs, key=lambda device_id: seed0_global_fprs[device_id]
    )
    representative = [
        sorted_devices[0],
        sorted_devices[len(sorted_devices) // 2],
        sorted_devices[-1],
    ]
    rep_seed = seed0_global.seed
    cal_errors = _calibration_errors_for_devices(
        _CalibrationErrorsParams(
            base_dir=base_dir,
            seed=rep_seed,
            device_ids=representative,
            max_points=figure2_max_points,
            rng_seed=figure2_rng_seed,
        )
    )
    tau_global = float(
        _load_json(
            _result_path(
                _ResultPathKey(
                    base_dir,
                    ExperimentStage.NBAIOT_MAIN,
                    ThresholdPolicy.GLOBAL_THRESHOLD,
                    rep_seed,
                )
            )
        )[MetricName.TAU_GLOBAL.value]
    )
    sidecar_path = _write_figure_data(
        figures_dir,
        FigureName.FIGURE_2.value,
        _build_figure2_sidecar(
            _Figure2SidecarParams(
                base_dir=base_dir,
                seed0_global=seed0_global,
                rep_seed=rep_seed,
                representative=representative,
                figure2_max_points=figure2_max_points,
                tau_global=tau_global,
            )
        ),
    )
    fig2_png = generate_figure2(
        cal_errors, tau_global, representative, figures_dir, style=style
    )
    return [
        sidecar_path,
        *_save_figure_copies(figures_dir, FigureName.FIGURE_2.value, fig2_png),
    ]


def _build_figure3(
    base_dir: Path,
    nbaiot_results: dict[ThresholdPolicy, list[EvaluationResult]],
    figures_dir: Path,
    style: Any,
    seeds: tuple[int, ...],
) -> list[Path]:
    fpr_by_policy = _common_eligible_fprs(
        nbaiot_results,
        (
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ),
    )
    sidecar_path = _write_figure_data(
        figures_dir,
        FigureName.FIGURE_3.value,
        _build_figure3_sidecar(base_dir, nbaiot_results, fpr_by_policy, seeds),
    )
    fig3_png = generate_figure3(fpr_by_policy, figures_dir, style=style)
    return [
        sidecar_path,
        *_save_figure_copies(figures_dir, FigureName.FIGURE_3.value, fig3_png),
    ]


def build_figures(base_dir: Path, cfg: DatpConfig) -> BuildOutputs:
    """Generate Figures 1–3 from completed result and score artifacts."""
    seeds = tuple(cfg.experiment.seeds)
    metric_tol = cfg.reporting.metric_tol
    figure2_max_points = cfg.reporting.figure2_max_points
    style = cfg.reporting.style

    figures_dir = base_dir / ArtifactDir.FIGURES
    figures_dir.mkdir(parents=True, exist_ok=True)

    nbaiot_policies = tuple(sorted(CONTROLLED_POLICIES))
    nbaiot_results = _load_results(
        _LoadResultsParams(
            base_dir=base_dir,
            stage=ExperimentStage.NBAIOT_MAIN,
            policies=nbaiot_policies,
            seeds=seeds,
            metric_tol=metric_tol,
        )
    )

    paths: list[Path] = []
    paths.extend(_build_figure1(base_dir, nbaiot_results, figures_dir, style))
    paths.extend(
        _build_figure2(
            base_dir,
            nbaiot_results,
            figures_dir,
            style,
            figure2_max_points,
            cfg.reporting.figure2_rng_seed,
        )
    )
    paths.extend(_build_figure3(base_dir, nbaiot_results, figures_dir, style, seeds))

    return BuildOutputs(paths=paths)


def build_tables(base_dir: Path, cfg: DatpConfig) -> BuildOutputs:
    """Generate Tables 3–4 from completed result artifacts."""
    seeds = tuple(cfg.experiment.seeds)
    metric_tol = cfg.reporting.metric_tol
    style = cfg.reporting.style
    tables_dir = base_dir / ArtifactDir.TABLES
    nbaiot_policies = tuple(sorted(CONTROLLED_POLICIES))
    nbaiot_results = _load_results(
        _LoadResultsParams(
            base_dir=base_dir,
            stage=ExperimentStage.NBAIOT_MAIN,
            policies=nbaiot_policies,
            seeds=seeds,
            metric_tol=metric_tol,
        )
    )
    table3 = generate_table3(nbaiot_results, tables_dir, style=style)
    table4 = generate_table4(nbaiot_results, tables_dir, style=style)
    return BuildOutputs(
        paths=[
            table3,
            table3.with_suffix(".csv"),
            table4,
            table4.with_suffix(".csv"),
        ]
    )


def validate_results(base_dir: Path, cfg: DatpConfig) -> BuildOutputs:
    seeds = tuple(cfg.experiment.seeds)
    metric_tol = cfg.reporting.metric_tol
    paths: list[Path] = []
    nbaiot_policies = tuple(sorted(CONTROLLED_POLICIES))
    _load_results(
        _LoadResultsParams(
            base_dir=base_dir,
            stage=ExperimentStage.NBAIOT_MAIN,
            policies=nbaiot_policies,
            seeds=seeds,
            metric_tol=metric_tol,
        )
    )
    validation_path = write_json_atomic(
        base_dir / ArtifactDir.ANALYSIS / ArtifactFile.METRICS_SCHEMA_VALIDATION,
        {
            ValidationField.STATUS: AuditStatus.PASS.value,
            ValidationField.SOURCE: "canonical per-client confusion-count reconstruction",
            ValidationField.VALIDATED_STAGES: [
                ExperimentStage.NBAIOT_MAIN.value,
                ExperimentStage.SYNTHETIC_SMOKE.value,
            ],
            ValidationField.SEEDS: list(seeds),
        },
    )
    paths.append(validation_path)
    return BuildOutputs(paths=paths)


def _validate_figure_sidecars(figures_dir: Path) -> list[str]:
    errors: list[str] = []
    for fig_name in _REPRESENTATIVE_SEED_FIGURES:
        sidecar = figures_dir / f"{fig_name}_data.json"
        if not sidecar.exists():
            errors.append(f"[reporting] Missing figure sidecar: {sidecar}")
            continue
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"[reporting] Unreadable figure sidecar {sidecar}: {exc}")
            continue
        if data.get(SidecarField.SEED_SCOPE) != SeedScope.REPRESENTATIVE_SEED.value:
            errors.append(
                f"[reporting] {fig_name} sidecar missing {SidecarField.SEED_SCOPE}={SeedScope.REPRESENTATIVE_SEED.value}. Got: {data.get(SidecarField.SEED_SCOPE)!r}."
            )
        if data.get(SidecarField.EVIDENCE_ROLE) != EvidenceRole.DESCRIPTIVE.value:
            errors.append(
                f"[reporting] {fig_name} sidecar missing {SidecarField.EVIDENCE_ROLE}={EvidenceRole.DESCRIPTIVE.value}. Got: {data.get(SidecarField.EVIDENCE_ROLE)!r}."
            )
        if not data.get(SidecarField.NOT_CONFIRMATORY_WARNING):
            errors.append(
                f"[reporting] {fig_name} sidecar missing {SidecarField.NOT_CONFIRMATORY_WARNING} field."
            )
        title = data[SidecarField.TITLE]
        if "representative seed" not in title.lower():
            errors.append(
                f"[reporting] {fig_name} sidecar title does not include 'representative seed'. Got: {title!r}."
            )
    return errors


def _build_audit_payload(params: _AuditPayloadParams) -> dict[str, Any]:
    return {
        AuditField.SCHEMA_VERSION: REPORTING_AUDIT_SCHEMA_VERSION,
        AuditField.GENERATED_TABLES: [
            str(p)
            for p in params.paths
            if p.suffix in {".tex", ".csv"} and ArtifactDir.TABLES in p.name
        ],
        AuditField.GENERATED_FIGURES: [
            str(p)
            for p in params.paths
            if p.suffix in {".pdf", ".png", ".json"} and ArtifactDir.FIGURES in p.name
        ],
        AuditField.SOURCE_METRICS_FILES: sorted(_REPORTING_SOURCES),
        AuditField.SOURCE_SCORE_MANIFESTS: sorted(
            str(
                ArtifactLayout(
                    base_dir=params.base_dir, stage=ExperimentStage.NBAIOT_MAIN
                )
                .score_cell(
                    TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=seed)
                )
                .manifest_path
            )
            for seed in params.cfg.experiment.seeds
        ),
        AuditField.SOURCE_RUN_IDS: sorted(_REPORTING_SOURCES),
        AuditField.VALIDATION_RESULTS: AuditStatus.FAIL.value
        if params.failures
        else AuditStatus.PASS.value,
        AuditField.RECOMPUTATION_CHECKS: "canonical confusion-matrix recomputation during load",
        AuditField.COVERAGE_CHECKS: "explicit eligible_ids/pending_ids/eval_incomplete_ids required",
        AuditField.MISSING_FIELD_CHECKS: "validate_metrics_payload",
        AuditField.STALE_ARTIFACT_CHECKS: "schema/provenance/sidecar checks",
        AuditField.DESCRIPTIVE_FIGURE_CHECKS: f"representative-seed sidecar validation for {sorted(_REPRESENTATIVE_SEED_FIGURES)}",
        AuditField.CONVERGENCE_METADATA_CHECKS: f"warn if {ArtifactFile.CONVERGENCE_SUMMARY} absent alongside model.pt",
        AuditField.FIGURE_TABLE_OUTPUT_PATHS: [str(p) for p in params.paths],
        AuditField.WARNINGS: params.conv_warnings,
        AuditField.FAILURES: params.failures,
    }


def build_all(base_dir: Path, cfg: DatpConfig) -> BuildOutputs:
    """Build analysis, figures, and tables."""
    _REPORTING_SOURCES.clear()
    paths: list[Path] = []
    failures: list[str] = []
    for step in (validate_results, build_stats, build_figures, build_tables):
        try:
            paths.extend(step(base_dir, cfg).paths)
        except Exception as exc:
            failures.append(str(exc))
            break
    failures.extend(_validate_figure_sidecars(base_dir / ArtifactDir.FIGURES))
    conv_warnings = _convergence_summary_warnings(base_dir, tuple(cfg.experiment.seeds))
    audit_path = write_json_atomic(
        base_dir / ArtifactDir.ANALYSIS / ArtifactFile.REPORTING_AUDIT,
        _build_audit_payload(
            _AuditPayloadParams(
                base_dir=base_dir,
                cfg=cfg,
                paths=paths,
                failures=failures,
                conv_warnings=conv_warnings,
            )
        ),
    )
    paths.append(audit_path)
    if failures:
        raise ValueError(
            f"[reporting] reporting_audit contains failures. Expected: none. Got: {failures}."
        )
    return BuildOutputs(paths=paths)
