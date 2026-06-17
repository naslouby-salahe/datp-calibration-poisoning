from __future__ import annotations

import csv
import dataclasses
import json
import math
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from datp.artifacts.io import write_json_atomic
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactDir, ArtifactFile
from datp.checkpointing.enums import EvidenceRole
from datp.config.models import DatpConfig
from datp.core.enums import (
    REGIME_BASELINES,
    STATS_REPORTING_BASELINES,
    Baseline,
    Regime,
    RunKind,
    ScoringStage,
    SeedScope,
)
from datp.core.identity import (
    AlphaLabel,
    BaselineRunId,
    TrainingCellId,
    alpha_from_label,
    alpha_label,
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
    generate_figure4,
)
from datp.reporting.tables import generate_table3, generate_table4
from datp.scoring.loading import ScoreProvider
from datp.scoring.schema import SCORE_COLUMN
from datp.statistics.bootstrap import bootstrap_ci
from datp.statistics.effect_size import cliffs_delta
from datp.statistics.enums import BootstrapField, StatsField
from datp.statistics.wilcoxon import bonferroni_correct, wilcoxon_test
from datp.validation.enums import AuditStatus

_REPORTING_SOURCES: set[str] = set()

# Figures whose sidecars must declare representative_seed scope.
_REPRESENTATIVE_SEED_FIGURES: frozenset[str] = frozenset(
    {FigureName.FIGURE_1.value, FigureName.FIGURE_2.value}
)


@dataclass(frozen=True, slots=True)
class BuildOutputs:
    paths: list[Path]


def _result_path(
    base_dir: Path,
    regime: Regime,
    baseline: Baseline,
    seed: int,
    alpha: str | None = None,
) -> Path:
    alpha_float = alpha_from_label(alpha)
    run = BaselineRunId(
        cell=TrainingCellId(regime=regime, seed=seed, alpha=alpha_float),
        baseline=baseline,
    )
    return (
        ArtifactLayout(base_dir=base_dir, regime=regime).baseline_run(run).result_dir
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


def _payload_alpha(value: Any) -> float | None:
    if value is None:
        return None
    from datp.core.identity import AlphaLabel

    if isinstance(value, str) and value.lower() in {AlphaLabel.IID, "inf"}:
        return math.inf
    return float(value)


def _client_records_from_payload(
    payload: dict[str, Any],
) -> tuple[ClientEvaluationRecord, ...]:
    records: list[ClientEvaluationRecord] = []
    for client_id, row in client_rows(payload):
        confusion = row[PayloadKey.CONFUSION_MATRIX]
        missing = [
            key
            for key in (ConfusionKey.TP, ConfusionKey.FP, ConfusionKey.TN, ConfusionKey.FN)
            if key not in confusion
        ]
        if missing:
            raise ValueError(
                f"[reporting] Missing confusion counts. Expected: tp/fp/tn/fn for {client_id}. Got: missing={missing}."
            )
        tp = int(confusion[ConfusionKey.TP])
        fp = int(confusion[ConfusionKey.FP])
        tn = int(confusion[ConfusionKey.TN])
        fn = int(confusion[ConfusionKey.FN])
        if PayloadKey.N_BENIGN in row and int(row[PayloadKey.N_BENIGN]) != fp + tn:
            raise ValueError(
                f"[reporting] Benign denominator mismatch. Expected: fp+tn={fp + tn} for {client_id}. Got: {row[PayloadKey.N_BENIGN]}."
            )
        if PayloadKey.N_ATTACK in row and int(row[PayloadKey.N_ATTACK]) != tp + fn:
            raise ValueError(
                f"[reporting] Attack denominator mismatch. Expected: tp+fn={tp + fn} for {client_id}. Got: {row[PayloadKey.N_ATTACK]}."
            )
        bm = recompute_binary_metrics(tp, fp, tn, fn)
        cid_str = str(client_id)
        cal_pending = bool(row.get(PayloadKey.CALIBRATION_PENDING, False))
        threshold_val = float(row.get(PayloadKey.THRESHOLD_VALUE, 0.0))
        records.append(
            ClientEvaluationRecord(
                client_id=cid_str,
                metrics=bm,
                confusion=ConfusionCounts(tp=tp, fp=fp, tn=tn, fn=fn),
                n_benign=fp + tn,
                n_attack=tp + fn,
                threshold=ClientThreshold(
                    client_id=cid_str,
                    threshold=threshold_val,
                    calibration_pending=cal_pending,
                    strategy=Baseline(payload[PayloadKey.BASELINE]),
                ),
                evaluation_incomplete=bool(row.get(PayloadKey.EVALUATION_INCOMPLETE, False)),
            )
        )
    return tuple(records)


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
    saved = float(saved_raw)
    if np.isnan(saved) and np.isnan(value):
        return
    if np.isnan(saved) != np.isnan(value):
        raise ValueError(
            f"[reporting] Metric schema mismatch. Expected: {key}={value}. Got: {saved}."
        )
    if abs(saved - value) > metric_tol:
        raise ValueError(
            f"[reporting] Metric schema mismatch. Expected: {key}={value:.12g} from canonical counts. Got: {saved:.12g}."
        )


def _evaluation_from_payload(
    payload: dict[str, Any], metric_tol: float
) -> EvaluationResult:
    clients = _client_records_from_payload(payload)
    eligible_ids = tuple(str(client_id) for client_id in payload[PayloadKey.ELIGIBLE_IDS])
    pending_ids = tuple(str(client_id) for client_id in payload[PayloadKey.PENDING_IDS])
    incomplete_ids = tuple(
        str(client_id) for client_id in payload[PayloadKey.EVAL_INCOMPLETE_IDS]
    )
    result = build_evaluation_result(
        baseline=Baseline(payload[PayloadKey.BASELINE]),
        regime=Regime(payload[PayloadKey.REGIME]),
        seed=int(payload[PayloadKey.SEED]),
        alpha=_payload_alpha(payload.get(PayloadKey.ALPHA)),
        clients=clients,
        eligible_ids=eligible_ids,
        pending_ids=pending_ids,
        incomplete_ids=incomplete_ids,
    )
    _assert_metric_matches(payload, PayloadKey.COVERAGE_RATIO, result.coverage_ratio, metric_tol)
    _assert_metric_matches(payload, MetricName.CV_FPR.value, result.cv_fpr, metric_tol)
    _assert_metric_matches(payload, MetricName.MEAN_FPR.value, result.mean_fpr, metric_tol)
    _assert_metric_matches(payload, MetricName.STD_FPR.value, result.std_fpr, metric_tol)
    _assert_metric_matches(payload, MetricName.CV_TPR.value, result.cv_tpr, metric_tol)
    _assert_metric_matches(payload, MetricName.IQR_FPR.value, result.iqr_fpr, metric_tol)
    _assert_metric_matches(payload, MetricName.IQR_TPR.value, result.iqr_tpr, metric_tol)
    _assert_metric_matches(
        payload, MetricName.WORST_CLIENT_FPR.value, result.worst_client_fpr, metric_tol
    )
    _assert_metric_matches(payload, MetricName.WORST_BA.value, result.worst_ba, metric_tol)
    _assert_metric_matches(payload, MetricName.P10_MACRO_F1.value, result.p10_macro_f1, metric_tol)
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
    base_dir: Path,
    regime: Regime,
    baselines: tuple[Baseline, ...],
    alpha: str | None = None,
    *,
    seeds: tuple[int, ...],
    metric_tol: float,
) -> dict[Baseline, list[EvaluationResult]]:
    loaded: dict[Baseline, list[EvaluationResult]] = {}
    for baseline in baselines:
        loaded[baseline] = []
        for seed in seeds:
            path = _result_path(base_dir, regime, baseline, seed, alpha)
            try:
                loaded[baseline].append(
                    _evaluation_from_payload(_load_json(path), metric_tol)
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
            f"[reporting] No eligible-client intersection. Expected: shared eligible clients for {left.baseline} vs {right.baseline}. Got: empty."
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
    results: dict[Baseline, list[EvaluationResult]],
    left: Baseline,
    right: Baseline,
) -> np.ndarray:
    return np.array(
        [
            _cv_fpr(results[left][idx]) - _cv_fpr(results[right][idx])
            for idx in range(len(results[left]))
        ]
    )


def _pooled_intersection_fprs(
    results: dict[Baseline, list[EvaluationResult]],
    left: Baseline,
    right: Baseline,
) -> tuple[np.ndarray, np.ndarray]:
    left_arrays: list[np.ndarray] = []
    right_arrays: list[np.ndarray] = []
    for idx in range(len(results[left])):
        left_arr, right_arr, _ = _eligible_intersection_fprs(
            results[left][idx], results[right][idx]
        )
        left_arrays.append(left_arr)
        right_arrays.append(right_arr)
    return np.concatenate(left_arrays), np.concatenate(right_arrays)


def _common_eligible_fprs(
    results: dict[Baseline, list[EvaluationResult]], baselines: tuple[Baseline, ...]
) -> dict[Baseline, list[np.ndarray]]:
    out: dict[Baseline, list[np.ndarray]] = {baseline: [] for baseline in baselines}
    n_seeds = len(results[baselines[0]])
    for idx in range(n_seeds):
        maps = {
            baseline: _eligible_fprs(results[baseline][idx]) for baseline in baselines
        }
        ids = sorted(set.intersection(*(set(maps[baseline]) for baseline in baselines)))
        if not ids:
            raise ValueError(
                f"[reporting] No eligible-client intersection. Expected: shared eligible clients for {baselines}. Got: empty."
            )
        for baseline in baselines:
            missing = sorted(set(maps[baseline]) - set(ids))
            if missing:
                raise ValueError(
                    f"[reporting] Eligible-client set mismatch. Expected: identical eligible-client sets for {baselines}. Got: baseline={baseline} extra={missing}."
                )
            out[baseline].append(
                np.array([maps[baseline][cid] for cid in ids], dtype=np.float64)
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


def _check_heterogeneity_context(
    bootstrap_payload: dict[str, Any],
    regime_a: dict[Baseline, list[EvaluationResult]],
    base_dir: Path,
    practical_significance_threshold: float,
    seeds: tuple[int, ...],
    metric_tol: float,
) -> dict[str, Any]:
    """Evaluate Regime C IID context; the primary endpoint is Regime A B1-minus-B2 CV(FPR) bootstrap CI."""
    primary_ci_excludes_zero: bool = bool(
        bootstrap_payload[StatsField.PRIMARY_ENDPOINT][BootstrapField.EXCLUDES_ZERO]
    )
    b1_natural_mean = (
        float(np.mean([_cv_fpr(r) for r in regime_a[Baseline.B1]]))
        if regime_a.get(Baseline.B1)
        else float("nan")
    )

    b1_iid_mean: float | None = None
    iid_data_available = False
    try:
        iid_results = _load_results(
            base_dir,
            Regime.C,
            (Baseline.B1,),
            alpha=AlphaLabel.IID,
            seeds=seeds,
            metric_tol=metric_tol,
        )
        b1_iid_cv_fprs = [_cv_fpr(r) for r in iid_results[Baseline.B1]]
        if b1_iid_cv_fprs:
            b1_iid_mean = float(np.mean(b1_iid_cv_fprs))
            iid_data_available = True
    except (FileNotFoundError, ValueError):
        pass

    if b1_iid_mean is None:
        natural_minus_iid: float | None = None
        practical_significance_met = False
    else:
        natural_minus_iid = b1_natural_mean - b1_iid_mean
        practical_significance_met = (
            natural_minus_iid >= practical_significance_threshold
        )

    if primary_ci_excludes_zero and practical_significance_met:
        context_result = HeterogeneityContextResult.CONTEXT_SUPPORTS.value
    elif primary_ci_excludes_zero or practical_significance_met:
        context_result = HeterogeneityContextResult.PARTIAL_CONTEXT.value
    else:
        context_result = HeterogeneityContextResult.CONTEXT_NOT_AVAILABLE.value

    return {
        StatsField.CONDITION: (
            "Regime C and IID comparisons are heterogeneity context/support checks, "
            "not the confirmatory endpoint."
        ),
        StatsField.B1_CV_FPR_REGIME_A_MEAN: b1_natural_mean,
        StatsField.B1_CV_FPR_IID_MEAN: b1_iid_mean,
        StatsField.NATURAL_MINUS_IID: natural_minus_iid,
        StatsField.PRACTICAL_SIGNIFICANCE_THRESHOLD: practical_significance_threshold,
        StatsField.PRACTICAL_SIGNIFICANCE_MET: practical_significance_met,
        StatsField.IID_DATA_AVAILABLE: iid_data_available,
        StatsField.PRIMARY_ENDPOINT_CI_EXCLUDES_ZERO: primary_ci_excludes_zero,
        StatsField.CONTEXT_RESULT: context_result,
        StatsField.NOTE: (
            "Primary endpoint: Regime A, B1 vs B2, CV(FPR), per-seed bootstrap CI. "
            "Regime C and IID comparisons are heterogeneity context/support checks, not the confirmatory endpoint."
        ),
    }


def _convergence_summary_warnings(base_dir: Path, seeds: tuple[int, ...]) -> list[str]:
    warnings_list: list[str] = []
    for regime in (Regime.A, Regime.B):
        layout = ArtifactLayout(base_dir=base_dir, regime=regime)
        for seed in seeds:
            ckpt_dir = layout.checkpoint_dir(
                TrainingCellId(regime=regime, seed=seed, alpha=None)
            )
            model_pt = ckpt_dir / ArtifactFile.MODEL_CHECKPOINT
            summary = ckpt_dir / ArtifactFile.CONVERGENCE_SUMMARY
            if model_pt.exists() and not summary.exists():
                warnings_list.append(
                    f"[reporting] Missing {ArtifactFile.CONVERGENCE_SUMMARY} for {regime.value} seed {seed}. "
                    f"Expected: {summary}. Got: absent."
                )
    return warnings_list


def build_stats(base_dir: Path, cfg: DatpConfig) -> BuildOutputs:
    seeds = tuple(cfg.experiment.seeds)
    regime_c_alphas = tuple(
        alpha_label(alpha) or "" for alpha in cfg.experiment.regime_c_alphas
    )
    n_bootstrap = cfg.statistics.n_bootstrap
    bootstrap_seed = cfg.statistics.bootstrap_seed
    ci = cfg.statistics.ci_level
    metric_tol = cfg.reporting.metric_tol

    analysis_dir = base_dir / ArtifactDir.ANALYSIS
    analysis_dir.mkdir(parents=True, exist_ok=True)

    stats_baselines_a = tuple(sorted(STATS_REPORTING_BASELINES[Regime.A]))
    stats_baselines_b = tuple(sorted(STATS_REPORTING_BASELINES[Regime.B]))
    regime_c_baselines = tuple(sorted(REGIME_BASELINES[Regime.C]))

    regime_a = _load_results(
        base_dir, Regime.A, stats_baselines_a, seeds=seeds, metric_tol=metric_tol
    )
    regime_b = _load_results(
        base_dir, Regime.B, stats_baselines_b, seeds=seeds, metric_tol=metric_tol
    )

    payload: dict[str, Any] = {
        StatsField.PRIMARY_ENDPOINT: {
            StatsField.CONDITION: "Primary endpoint: Regime A, B1 vs B2, CV(FPR), per-seed bootstrap CI.",
            **_bootstrap_payload(
                _paired_deltas(regime_a, Baseline.B1, Baseline.B2),
                n_bootstrap,
                ci,
                bootstrap_seed,
            ),
        },
        StatsField.SECONDARY_REGIME_A: {
            ComparisonLabel.B1_VS_B4.value: _bootstrap_payload(
                _paired_deltas(regime_a, Baseline.B1, Baseline.B4),
                n_bootstrap,
                ci,
                bootstrap_seed,
            ),
            ComparisonLabel.B4_VS_B2.value: _bootstrap_payload(
                _paired_deltas(regime_a, Baseline.B4, Baseline.B2),
                n_bootstrap,
                ci,
                bootstrap_seed,
            ),
        },
        StatsField.SECONDARY_REGIME_B: {
            ComparisonLabel.B1_VS_B2.value: _bootstrap_payload(
                _paired_deltas(regime_b, Baseline.B1, Baseline.B2),
                n_bootstrap,
                ci,
                bootstrap_seed,
            ),
            ComparisonLabel.B1_VS_B4.value: _bootstrap_payload(
                _paired_deltas(regime_b, Baseline.B1, Baseline.B4),
                n_bootstrap,
                ci,
                bootstrap_seed,
            ),
        },
        StatsField.REGIME_C: {},
    }

    regime_c_p_values: list[float] = []
    for alpha in regime_c_alphas:
        results = _load_results(
            base_dir,
            Regime.C,
            regime_c_baselines,
            alpha=alpha,
            seeds=seeds,
            metric_tol=metric_tol,
        )
        b1_b2 = _paired_deltas(results, Baseline.B1, Baseline.B2)
        b1_b4 = _paired_deltas(results, Baseline.B1, Baseline.B4)
        b1_fpr, b2_fpr = _pooled_intersection_fprs(
            results, Baseline.B1, Baseline.B2
        )
        wilcoxon = wilcoxon_test(b1_fpr, b2_fpr)
        regime_c_p_values.append(wilcoxon.p_value)
        cliff = cliffs_delta(b1_fpr, b2_fpr)
        payload[StatsField.REGIME_C][alpha] = {
            ComparisonLabel.B1_VS_B2.value: _bootstrap_payload(b1_b2, n_bootstrap, ci, bootstrap_seed),
            ComparisonLabel.B1_VS_B4.value: _bootstrap_payload(b1_b4, n_bootstrap, ci, bootstrap_seed),
            StatsField.PAIRED_CLIENT_FPR_POLICY: "eligible-client intersection within each seed, pooled across seeds",
            StatsField.WILCOXON_B1_VS_B2: dataclasses.asdict(wilcoxon),
            StatsField.CLIFFS_DELTA_B1_VS_B2: dataclasses.asdict(cliff),
        }

    bonferroni = bonferroni_correct(
        regime_c_p_values, alpha=cfg.statistics.significance_alpha
    )
    payload[StatsField.REGIME_C_BONFERRONI] = dataclasses.asdict(bonferroni)

    payload[StatsField.HETEROGENEITY_CONTEXT_CHECK] = _check_heterogeneity_context(
        payload,
        regime_a,
        base_dir,
        practical_significance_threshold=cfg.statistics.dispersion_threshold,
        seeds=seeds,
        metric_tol=metric_tol,
    )

    json_path = write_json_atomic(analysis_dir / ArtifactFile.BOOTSTRAP_CIS_JSON, payload)
    csv_path = analysis_dir / ArtifactFile.BOOTSTRAP_CIS_CSV
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
                ComparisonLabel.B1_VS_B2.value,
                payload[StatsField.PRIMARY_ENDPOINT][BootstrapField.MEAN_DELTA],
                payload[StatsField.PRIMARY_ENDPOINT][BootstrapField.CI_LOWER],
                payload[StatsField.PRIMARY_ENDPOINT][BootstrapField.CI_UPPER],
                payload[StatsField.PRIMARY_ENDPOINT][BootstrapField.EXCLUDES_ZERO],
            ]
        )
        for scope in (StatsField.SECONDARY_REGIME_A, StatsField.SECONDARY_REGIME_B):
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
        for alpha, stats_by_comparison in payload[StatsField.REGIME_C].items():
            for comparison in (ComparisonLabel.B1_VS_B2.value, ComparisonLabel.B1_VS_B4.value):
                stats = stats_by_comparison[comparison]
                writer.writerow(
                    [
                        f"regime_c_alpha_{alpha}",
                        comparison,
                        stats[BootstrapField.MEAN_DELTA],
                        stats[BootstrapField.CI_LOWER],
                        stats[BootstrapField.CI_UPPER],
                        stats[BootstrapField.EXCLUDES_ZERO],
                    ]
                )

    return BuildOutputs(paths=[json_path, csv_path])


def _calibration_errors_for_devices(
    base_dir: Path, seed: int, device_ids: list[str], max_points: int, rng_seed: int
) -> dict[str, np.ndarray]:
    errors: dict[str, np.ndarray] = {}
    rng = np.random.default_rng(rng_seed)
    layout = ArtifactLayout(base_dir=base_dir, regime=Regime.A)
    cell = TrainingCellId(regime=Regime.A, seed=seed, alpha=None)
    score_provider = ScoreProvider(layout.score_cell(cell).score_dir)
    for device_id in device_ids:
        values = score_provider.load(device_id, ScoringStage.CAL)
        if values.size > max_points:
            values = rng.choice(values, size=max_points, replace=False)
        errors[device_id] = values
    return errors


def build_figures(base_dir: Path, cfg: DatpConfig) -> BuildOutputs:
    """Generate Figures 1–4 from completed result and score artifacts."""
    seeds = tuple(cfg.experiment.seeds)
    regime_c_alphas = tuple(
        alpha_label(alpha) or "" for alpha in cfg.experiment.regime_c_alphas
    )
    metric_tol = cfg.reporting.metric_tol
    figure2_max_points = cfg.reporting.figure2_max_points
    style = cfg.reporting.style

    figures_dir = base_dir / ArtifactDir.FIGURES
    figures_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    stats_baselines_a = tuple(sorted(STATS_REPORTING_BASELINES[Regime.A]))
    regime_c_baselines = tuple(sorted(REGIME_BASELINES[Regime.C]))

    regime_a = _load_results(
        base_dir, Regime.A, stats_baselines_a, seeds=seeds, metric_tol=metric_tol
    )
    seed0_b1 = regime_a[Baseline.B1][0]
    seed0_b2 = regime_a[Baseline.B2][0]
    b1_seed0_fpr, b2_seed0_fpr, figure1_ids = _eligible_intersection_fprs(
        seed0_b1, seed0_b2
    )
    figure1_payload: dict[str, Any] = {
        SidecarField.FIGURE: FigureName.FIGURE_1.value,
        SidecarField.TITLE: "Per-device FPR: B1 vs B2, Regime A — representative seed, descriptive only",
        SidecarField.DATASET: DatasetID.NBAIOT.value,
        SidecarField.REGIME: Regime.A.value,
        SidecarField.SEED: seed0_b1.seed,
        SidecarField.SEEDS: [seed0_b1.seed],
        SidecarField.SOURCE_METRICS_FILES: [
            str(_result_path(base_dir, Regime.A, Baseline.B1, seed0_b1.seed)),
            str(_result_path(base_dir, Regime.A, Baseline.B2, seed0_b2.seed)),
        ],
        SidecarField.RUN_IDS: [
            f"{Regime.A.value}_b1_seed{seed0_b1.seed}",
            f"{Regime.A.value}_b2_seed{seed0_b2.seed}",
        ],
        SidecarField.ALPHAS: [],
        SidecarField.ELIGIBLE_COUNTS: {
            Baseline.B1.value: seed0_b1.eligible_count,
            Baseline.B2.value: seed0_b2.eligible_count,
        },
        SidecarField.CLIENT_COUNTS: {
            Baseline.B1.value: seed0_b1.client_count,
            Baseline.B2.value: seed0_b2.client_count,
        },
        SidecarField.COVERAGE_RATIOS: {
            Baseline.B1.value: seed0_b1.coverage_ratio,
            Baseline.B2.value: seed0_b2.coverage_ratio,
        },
        SidecarField.METRIC_NAMES: [MetricName.FPR.value],
        SidecarField.EVIDENCE_ROLE: EvidenceRole.DESCRIPTIVE.value,
        SidecarField.SEED_SCOPE: SeedScope.REPRESENTATIVE_SEED.value,
        SidecarField.NOT_CONFIRMATORY_WARNING: NOT_CONFIRMATORY_WARNING,
        SidecarField.VALIDATION_STATUS: AuditStatus.PASS.value,
        SidecarField.BASELINES: [Baseline.B1.value, Baseline.B2.value],
        SidecarField.BASELINE_ORDER: [Baseline.B1.value, Baseline.B2.value],
        SidecarField.ELIGIBILITY_POLICY: "eligible-client intersection",
        SidecarField.AXIS_LABELS: {"x": "Device", "y": "FPR"},
        SidecarField.CLIENTS: [
            {
                SidecarField.CLIENT_ID: cid,
                Baseline.B1.value: float(b1),
                Baseline.B2.value: float(b2),
            }
            for cid, b1, b2 in zip(figure1_ids, b1_seed0_fpr, b2_seed0_fpr, strict=True)
        ],
    }
    paths.append(
        _write_figure_data(figures_dir, FigureName.FIGURE_1.value, figure1_payload)
    )

    fig1_png = generate_figure1(
        dict(zip(figure1_ids, b1_seed0_fpr, strict=True)),
        dict(zip(figure1_ids, b2_seed0_fpr, strict=True)),
        figures_dir,
        seed=seed0_b1.seed,
        style=style,
    )
    paths.extend(_save_figure_copies(figures_dir, FigureName.FIGURE_1.value, fig1_png))

    seed0_b1_fprs = _eligible_fprs(seed0_b1)
    sorted_devices = sorted(
        seed0_b1_fprs, key=lambda device_id: seed0_b1_fprs[device_id]
    )
    representative = [
        sorted_devices[0],
        sorted_devices[len(sorted_devices) // 2],
        sorted_devices[-1],
    ]
    rep_seed = seed0_b1.seed
    cal_errors = _calibration_errors_for_devices(
        base_dir,
        seed=rep_seed,
        device_ids=representative,
        max_points=figure2_max_points,
        rng_seed=cfg.reporting.figure2_rng_seed,
    )
    tau_global = float(
        _load_json(_result_path(base_dir, Regime.A, Baseline.B1, rep_seed))[
            MetricName.TAU_GLOBAL.value
        ]
    )
    paths.append(
        _write_figure_data(
            figures_dir,
            FigureName.FIGURE_2.value,
            dict[str, Any]({
                SidecarField.FIGURE: FigureName.FIGURE_2.value,
                SidecarField.TITLE: "Calibration-error ECDF for three representative N-BaIoT clients with B1 client-averaged threshold — representative seed, descriptive only",
                SidecarField.DATASET: DatasetID.NBAIOT.value,
                SidecarField.REGIME: Regime.A.value,
                SidecarField.SEED: rep_seed,
                SidecarField.SEEDS: [rep_seed],
                SidecarField.SOURCE_METRICS_FILES: [
                    str(_result_path(base_dir, Regime.A, Baseline.B1, rep_seed))
                ],
                SidecarField.SOURCE_SCORE_MANIFESTS: [
                    str(
                        ArtifactLayout(base_dir=base_dir, regime=Regime.A)
                        .score_cell(
                            TrainingCellId(
                                regime=Regime.A, seed=rep_seed, alpha=None
                            )
                        )
                        .manifest_path
                    )
                ],
                SidecarField.RUN_IDS: [f"{Regime.A.value}_b1_seed{rep_seed}"],
                SidecarField.ALPHAS: [],
                SidecarField.ELIGIBLE_COUNTS: {Baseline.B1.value: seed0_b1.eligible_count},
                SidecarField.CLIENT_COUNTS: {Baseline.B1.value: seed0_b1.client_count},
                SidecarField.COVERAGE_RATIOS: {Baseline.B1.value: seed0_b1.coverage_ratio},
                SidecarField.METRIC_NAMES: [SCORE_COLUMN, PayloadKey.THRESHOLD_VALUE],
                SidecarField.EVIDENCE_ROLE: EvidenceRole.DESCRIPTIVE.value,
                SidecarField.SEED_SCOPE: SeedScope.REPRESENTATIVE_SEED.value,
                SidecarField.NOT_CONFIRMATORY_WARNING: NOT_CONFIRMATORY_WARNING,
                SidecarField.VALIDATION_STATUS: AuditStatus.PASS.value,
                SidecarField.BASELINES: [Baseline.B1.value],
                SidecarField.BASELINE_ORDER: [Baseline.B1.value],
                SidecarField.ELIGIBILITY_POLICY: f"selected eligible clients from B1 seed {rep_seed}",
                SidecarField.AXIS_LABELS: {"x": "Reconstruction Error", "y": "Density"},
                SidecarField.TAU_GLOBAL: tau_global,
                SidecarField.CLIENT_IDS: representative,
                SidecarField.MAX_POINTS_PER_CLIENT: figure2_max_points,
            }),
        )
    )
    fig2_png = generate_figure2(
        cal_errors, tau_global, representative, figures_dir, style=style
    )
    paths.extend(_save_figure_copies(figures_dir, FigureName.FIGURE_2.value, fig2_png))

    fpr_by_baseline = _common_eligible_fprs(
        regime_a,
        (Baseline.B1, Baseline.B2, Baseline.B4),
    )
    paths.append(
        _write_figure_data(
            figures_dir,
            FigureName.FIGURE_3.value,
            dict[str, Any]({
                SidecarField.FIGURE: FigureName.FIGURE_3.value,
                SidecarField.TITLE: "Per-client FPR distribution, Regime A",
                SidecarField.DATASET: DatasetID.NBAIOT.value,
                SidecarField.REGIME: Regime.A.value,
                SidecarField.SOURCE_METRICS_FILES: [
                    str(_result_path(base_dir, Regime.A, Baseline(b), seed))
                    for b in (Baseline.B1.value, Baseline.B2.value, Baseline.B4.value)
                    for seed in seeds
                ],
                SidecarField.RUN_IDS: [
                    f"{Regime.A.value}_{b}_seed{seed}"
                    for b in (Baseline.B1.value, Baseline.B2.value, Baseline.B4.value)
                    for seed in seeds
                ],
                SidecarField.SEEDS: list(seeds),
                SidecarField.ALPHAS: [],
                SidecarField.ELIGIBLE_COUNTS: {
                    b.value: [r.eligible_count for r in regime_a[b]]
                    for b in (Baseline.B1, Baseline.B2, Baseline.B4)
                },
                SidecarField.CLIENT_COUNTS: {
                    b.value: [r.client_count for r in regime_a[b]]
                    for b in (Baseline.B1, Baseline.B2, Baseline.B4)
                },
                SidecarField.COVERAGE_RATIOS: {
                    b.value: [r.coverage_ratio for r in regime_a[b]]
                    for b in (Baseline.B1, Baseline.B2, Baseline.B4)
                },
                SidecarField.METRIC_NAMES: [MetricName.FPR.value, "cv_fpr_delta_b1_b2"],
                SidecarField.EVIDENCE_ROLE: EvidenceRole.DESCRIPTIVE_WITH_CONFIRMATORY_SIDECAR_DELTA.value,
                SidecarField.SEED_SCOPE: SeedScope.ALL_SEED.value,
                SidecarField.VALIDATION_STATUS: AuditStatus.PASS.value,
                SidecarField.BASELINES: [Baseline.B1.value, Baseline.B2.value, Baseline.B4.value],
                SidecarField.PAIRED_SEED_CV_FPR_DELTA: [
                    float(x)
                    for x in _paired_deltas(
                        regime_a, Baseline.B1, Baseline.B2
                    )
                ],
                SidecarField.SEED_AGGREGATION_POLICY: "eligible-client FPR values pooled across configured seeds after intersection",
                SidecarField.BASELINE_ORDER: [
                    Baseline.B1.value,
                    Baseline.B2.value,
                    Baseline.B4.value,
                ],
                SidecarField.ELIGIBILITY_POLICY: "eligible-client intersection within each seed",
                SidecarField.AXIS_LABELS: {"x": "Baseline", "y": "FPR"},
                SidecarField.VALUES: {
                    baseline: [[float(x) for x in arr] for arr in arrays]
                    for baseline, arrays in fpr_by_baseline.items()
                },
            }),
        )
    )
    fig3_png = generate_figure3(
        fpr_by_baseline, figures_dir, style=style
    )
    paths.extend(_save_figure_copies(figures_dir, FigureName.FIGURE_3.value, fig3_png))

    cv_fpr_by_baseline: dict[Baseline, dict[str, list[float]]] = {}
    regime_c_loaded: dict[Baseline, dict[str, list[EvaluationResult]]] = {}
    for baseline in regime_c_baselines:
        cv_fpr_by_baseline[baseline] = {}
        regime_c_loaded[baseline] = {}
        for alpha in regime_c_alphas:
            results = _load_results(
                base_dir,
                Regime.C,
                (baseline,),
                alpha=alpha,
                seeds=seeds,
                metric_tol=metric_tol,
            )[baseline]
            regime_c_loaded[baseline][alpha] = results
            cv_fpr_by_baseline[baseline][alpha] = [_cv_fpr(r) for r in results]
    paths.append(
        _write_figure_data(
            figures_dir,
            FigureName.FIGURE_4.value,
            dict[str, Any]({
                SidecarField.FIGURE: FigureName.FIGURE_4.value,
                SidecarField.TITLE: "CV(FPR) vs Dirichlet alpha, Regime C",
                SidecarField.DATASET: DatasetID.NBAIOT.value,
                SidecarField.REGIME: Regime.C.value,
                SidecarField.SOURCE_METRICS_FILES: [
                    str(_result_path(base_dir, Regime.C, Baseline(b), seed, alpha))
                    for b in regime_c_baselines
                    for alpha in regime_c_alphas
                    for seed in seeds
                ],
                SidecarField.RUN_IDS: [
                    f"{Regime.C.value}_{b}_seed{seed}_alpha{alpha}"
                    for b in regime_c_baselines
                    for alpha in regime_c_alphas
                    for seed in seeds
                ],
                SidecarField.SEEDS: list(seeds),
                SidecarField.ALPHAS: list(regime_c_alphas),
                SidecarField.ELIGIBLE_COUNTS: {
                    b: {
                        a: [r.eligible_count for r in regime_c_loaded[b][a]]
                        for a in regime_c_alphas
                    }
                    for b in regime_c_baselines
                },
                SidecarField.CLIENT_COUNTS: {
                    b: {
                        a: [r.client_count for r in regime_c_loaded[b][a]]
                        for a in regime_c_alphas
                    }
                    for b in regime_c_baselines
                },
                SidecarField.COVERAGE_RATIOS: {
                    b: {
                        a: [r.coverage_ratio for r in regime_c_loaded[b][a]]
                        for a in regime_c_alphas
                    }
                    for b in regime_c_baselines
                },
                SidecarField.METRIC_NAMES: [MetricName.CV_FPR.value],
                SidecarField.EVIDENCE_ROLE: EvidenceRole.SECONDARY.value,
                SidecarField.SEED_SCOPE: SeedScope.ALL_SEED.value,
                SidecarField.VALIDATION_STATUS: AuditStatus.PASS.value,
                SidecarField.BASELINES: list(regime_c_baselines),
                SidecarField.SEED_AGGREGATION_POLICY: "mean with one-standard-deviation band across configured seeds",
                SidecarField.BASELINE_ORDER: list(regime_c_baselines),
                SidecarField.ELIGIBILITY_POLICY: "eligible clients only per result row",
                SidecarField.AXIS_LABELS: {"x": "Dirichlet alpha", "y": "CV(FPR)"},
                SidecarField.VALUES: {
                    baseline: {
                        str(alpha): [float(x) for x in values]
                        for alpha, values in alpha_map.items()
                    }
                    for baseline, alpha_map in cv_fpr_by_baseline.items()
                },
            }),
        )
    )
    fig4_png = generate_figure4(
        cv_fpr_by_baseline,
        figures_dir,
        style=style,
    )
    paths.extend(_save_figure_copies(figures_dir, FigureName.FIGURE_4.value, fig4_png))
    return BuildOutputs(paths=paths)


def build_tables(base_dir: Path, cfg: DatpConfig) -> BuildOutputs:
    """Generate Tables 3–4 from completed result artifacts."""
    seeds = tuple(cfg.experiment.seeds)
    metric_tol = cfg.reporting.metric_tol
    style = cfg.reporting.style
    tables_dir = base_dir / ArtifactDir.TABLES
    regime_a_baselines = tuple(sorted(REGIME_BASELINES[Regime.A]))
    regime_b_baselines = tuple(sorted(REGIME_BASELINES[Regime.B]))
    regime_a = _load_results(
        base_dir, Regime.A, regime_a_baselines, seeds=seeds, metric_tol=metric_tol
    )
    regime_b = _load_results(
        base_dir, Regime.B, regime_b_baselines, seeds=seeds, metric_tol=metric_tol
    )
    table3 = generate_table3(regime_a, tables_dir, style=style)
    table4 = generate_table4(regime_b, tables_dir, style=style)
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
    regime_c_alphas = tuple(
        alpha_label(alpha) or "" for alpha in cfg.experiment.regime_c_alphas
    )
    metric_tol = cfg.reporting.metric_tol
    paths: list[Path] = []
    regime_a_baselines = tuple(sorted(REGIME_BASELINES[Regime.A]))
    regime_b_baselines = tuple(sorted(REGIME_BASELINES[Regime.B]))
    regime_c_baselines = tuple(sorted(REGIME_BASELINES[Regime.C]))
    _load_results(
        base_dir, Regime.A, regime_a_baselines, seeds=seeds, metric_tol=metric_tol
    )
    _load_results(
        base_dir, Regime.B, regime_b_baselines, seeds=seeds, metric_tol=metric_tol
    )
    for alpha in regime_c_alphas:
        _load_results(
            base_dir,
            Regime.C,
            regime_c_baselines,
            alpha=alpha,
            seeds=seeds,
            metric_tol=metric_tol,
        )
    validation_path = write_json_atomic(
        base_dir / ArtifactDir.ANALYSIS / ArtifactFile.METRICS_SCHEMA_VALIDATION,
        {
            ValidationField.STATUS: AuditStatus.PASS.value,
            ValidationField.SOURCE: "canonical per-client confusion-count reconstruction",
            ValidationField.VALIDATED_REGIMES: [Regime.A.value, Regime.B.value, Regime.C.value],
            ValidationField.SEEDS: list(seeds),
            ValidationField.REGIME_C_ALPHAS: list(regime_c_alphas),
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
    sidecar_errors = _validate_figure_sidecars(base_dir / ArtifactDir.FIGURES)
    failures.extend(sidecar_errors)
    conv_warnings = _convergence_summary_warnings(base_dir, tuple(cfg.experiment.seeds))
    audit_path = write_json_atomic(
        base_dir / ArtifactDir.ANALYSIS / ArtifactFile.REPORTING_AUDIT,
        {
            AuditField.SCHEMA_VERSION: REPORTING_AUDIT_SCHEMA_VERSION,
            AuditField.GENERATED_TABLES: [
                str(path)
                for path in paths
                if path.suffix in {".tex", ".csv"} and ArtifactDir.TABLES in path.name
            ],
            AuditField.GENERATED_FIGURES: [
                str(path)
                for path in paths
                if path.suffix in {".pdf", ".png", ".json"} and ArtifactDir.FIGURES in path.name
            ],
            AuditField.SOURCE_METRICS_FILES: sorted(_REPORTING_SOURCES),
            AuditField.SOURCE_SCORE_MANIFESTS: sorted(
                str(
                    ArtifactLayout(base_dir=base_dir, regime=Regime.A)
                    .score_cell(
                        TrainingCellId(regime=Regime.A, seed=seed, alpha=None)
                    )
                    .manifest_path
                )
                for seed in cfg.experiment.seeds
            ),
            AuditField.SOURCE_RUN_IDS: sorted(_REPORTING_SOURCES),
            AuditField.VALIDATION_RESULTS: AuditStatus.FAIL.value if failures else AuditStatus.PASS.value,
            AuditField.RECOMPUTATION_CHECKS: "canonical confusion-matrix recomputation during load",
            AuditField.COVERAGE_CHECKS: "explicit eligible_ids/pending_ids/eval_incomplete_ids required",
            AuditField.MISSING_FIELD_CHECKS: "validate_metrics_payload",
            AuditField.STALE_ARTIFACT_CHECKS: "schema/provenance/sidecar checks",
            AuditField.DESCRIPTIVE_FIGURE_CHECKS: f"representative-seed sidecar validation for {sorted(_REPRESENTATIVE_SEED_FIGURES)}",
            AuditField.CONVERGENCE_METADATA_CHECKS: f"warn if {ArtifactFile.CONVERGENCE_SUMMARY} absent alongside model.pt",
            AuditField.FIGURE_TABLE_OUTPUT_PATHS: [str(path) for path in paths],
            AuditField.WARNINGS: conv_warnings,
            AuditField.FAILURES: failures,
        },
    )
    paths.append(audit_path)
    if failures:
        raise ValueError(
            f"[reporting] reporting_audit contains failures. Expected: none. Got: {failures}."
        )
    return BuildOutputs(paths=paths)
