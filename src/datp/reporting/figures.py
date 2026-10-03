from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, cast

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

from datp.config import StyleConfig
from datp.enums import (
    MAIN_BODY_POLICIES,
    FigureName,
    MetricName,
    NBaIoTDevice,
    ReportTerm,
    ThresholdPolicy,
)
from datp.evaluation import EvaluationResult
from datp.types import (
    ClassificationScore,
    ClientId,
    FalsePositiveRate,
    NarrativeText,
    PoisonFraction,
    Ratio,
    RecordKey,
    SampleCount,
    SchemaVersion,
    ScoreValue,
    ScoreVector,
    SignedCount,
    Threshold,
    TruePositiveRate,
)

NBAIOT_DEVICE_SHORT_LABELS: dict[NBaIoTDevice, NarrativeText] = {
    NBaIoTDevice.DANMINI_DOORBELL: "Danmini DB",
    NBaIoTDevice.ECOBEE_THERMOSTAT: "Ecobee Tstat",
    NBaIoTDevice.ENNIO_DOORBELL: "Ennio DB",
    NBaIoTDevice.PHILIPS_B120N10_BABY_MONITOR: "Philips B120N10",
    NBaIoTDevice.PROVISION_PT_737E_SECURITY_CAMERA: "Prov. PT-737E",
    NBaIoTDevice.PROVISION_PT_838_SECURITY_CAMERA: "Prov. PT-838",
    NBaIoTDevice.SAMSUNG_SNH_1011_N_WEBCAM: "Samsung SNH",
    NBaIoTDevice.SIMPLEHOME_XCS7_1002_WHT_SECURITY_CAMERA: "SH XCS7-1002",
    NBaIoTDevice.SIMPLEHOME_XCS7_1003_WHT_SECURITY_CAMERA: "SH XCS7-1003",
}


REPORTING_AUDIT_SCHEMA_VERSION: SchemaVersion = "1"


SEED_SELECTION_RULE: NarrativeText = (
    "training seed whose GLOBAL_THRESHOLD CV(FPR) is the lower median across all training seeds"
)


CLIENT_SELECTION_RULE: NarrativeText = (
    "clients with the lowest, median and highest GLOBAL_THRESHOLD FPR in the representative seed"
)


POISONING_FIGURE_FRACTION: PoisonFraction = 0.40


NOT_CONFIRMATORY_WARNING: NarrativeText = (
    "Representative seed only; descriptive evidence, not confirmatory."
)


METRIC_DEFINITIONS: dict[MetricName | ReportTerm, NarrativeText] = {
    MetricName.WORST_BA: "Minimum per-client balanced accuracy, (TPR + TNR) / 2, over eligible clients with complete evaluation.",
    MetricName.P10_MACRO_F1: "10th percentile of per-client macro-F1 (mean of benign-class and attack-class F1) over eligible clients with complete evaluation.",
    MetricName.CV_FPR: "Population coefficient of variation (std with ddof=0 divided by mean) of per-client FPR over eligible clients.",
    MetricName.DELTA_CV_FPR: "CV(FPR) under the poisoned thresholds minus CV(FPR) under the clean thresholds, same fleet and seed.",
    MetricName.VICTIM_DELTA_TPR: "Victim TPR under the poisoned threshold minus TPR under the clean threshold.",
    MetricName.VICTIM_DELTA_FPR: "Victim FPR under the poisoned threshold minus FPR under the clean threshold.",
    MetricName.VICTIM_DELTA_FP: "Victim count of benign test samples above the threshold, poisoned minus clean.",
    MetricName.VICTIM_DELTA_FN: "Victim count of attack test samples at or below the threshold, poisoned minus clean.",
    MetricName.NONVICTIM_MEAN_DELTA_TPR: "Mean over eligible non-victim clients of TPR change under the poisoned thresholds.",
    MetricName.NONVICTIM_WORST_DELTA_TPR: "Most negative per-client TPR change among eligible non-victim clients.",
    MetricName.NONVICTIM_MEAN_DELTA_FPR: "Mean over eligible non-victim clients of FPR change under the poisoned thresholds.",
    MetricName.NONVICTIM_WORST_DELTA_FPR: "Most positive per-client FPR change among eligible non-victim clients.",
    MetricName.NONVICTIM_DELTA_FP_TOTAL: "Total change in false-positive count over eligible non-victim clients.",
    MetricName.NONVICTIM_DELTA_FN_TOTAL: "Total change in missed-detection count over eligible non-victim clients.",
    ReportTerm.FIXED_CLUSTER: "CLUSTER_THRESHOLD thresholds where clean cluster assignments stay frozen and per-cluster means are taken over poisoned per-client quantiles.",
    MetricName.DELTA_TAU_BOUND_UTILIZATION: "Threshold shift divided by the distance from the clean threshold to the extreme victim-local benign calibration score in the attack direction.",
    MetricName.CAL_DUPLICATE_RATE: "Fraction of calibration entries repeating an earlier value.",
    ReportTerm.CELL: "One (policy, objective, source, fraction, victim, training seed) row of the bounded sweep; rows sharing a training seed are not independent.",
    ReportTerm.SEED_AGGREGATE: "Mean over victims of a row metric within one training seed; the inferential unit.",
}


matplotlib.use("Agg")


plt.rcParams.update(
    {
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.family": "serif",
        "font.serif": [
            "Times New Roman",
            "Times",
            "Nimbus Roman No9 L",
            "DejaVu Serif",
        ],
        "mathtext.fontset": "stix",
    }
)


_FONT_SIZE_KEY = "font.size"


class _Patch(Protocol):
    def set_facecolor(self, color: str) -> None: ...
    def set_alpha(self, alpha: float) -> None: ...


class _BoxplotOutput(Protocol):
    def __getitem__(self, key: Literal["boxes"]) -> list[_Patch]: ...


class _Axes(Protocol):
    def bar(self, x: NDArray[np.generic], height: Sequence[float], width: float, *, label: str, color: str) -> None: ...
    def set(self, **kwargs: str) -> None: ...
    def set_xticks(self, ticks: NDArray[np.generic], labels: Sequence[str] | None = None) -> None: ...
    def set_xticklabels(self, labels: Sequence[str], **kwargs: str | float | int) -> None: ...
    def legend(self, **kwargs: str | float | int) -> None: ...
    def plot(self, x: NDArray[np.generic], y: NDArray[np.generic], **kwargs: str | float | int) -> None: ...
    def axvline(self, x: float, **kwargs: str | float | int) -> None: ...
    def boxplot(self, data: Sequence[NDArray[np.generic]], **kwargs: bool | Sequence[str]) -> _BoxplotOutput: ...
    def tick_params(self, *, axis: str, **kwargs: str | float | int) -> None: ...
    def fill_between(self, x: NDArray[np.generic], y1: NDArray[np.generic], y2: NDArray[np.generic], **kwargs: str | float | int) -> None: ...
    def errorbar(self, x: Sequence[float], y: Sequence[float], **kwargs: str | float | int | Sequence[Sequence[float]]) -> None: ...
    def axhline(self, y: float, **kwargs: str | float | int) -> None: ...
    def scatter(self, x: NDArray[np.generic], y: NDArray[np.generic], **kwargs: str | float | int) -> None: ...
    def hlines(self, y: float, xmin: float, xmax: float, **kwargs: str | float | int) -> None: ...


class _Figure(Protocol):
    def savefig(
        self, fname: Path, *, dpi: int | None = None, bbox_inches: str | None = None
    ) -> None: ...
    def tight_layout(self) -> None: ...


def _save_figs(fig: plt.Figure, base_path: Path, dpi: SignedCount) -> Path:
    figure = cast(_Figure, fig)
    figure.savefig(base_path.with_suffix(".png"), dpi=dpi, bbox_inches="tight")
    figure.savefig(base_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)
    return base_path.with_suffix(".png")


def generate_figure1(
    per_device_fpr_global: dict[ClientId, FalsePositiveRate],
    per_device_fpr_local: dict[ClientId, FalsePositiveRate],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size
    devices = sorted(per_device_fpr_global.keys())
    x, width = np.arange(len(devices)), 0.35
    fig, ax = plt.subplots(figsize=style.figsize_double_col)
    ax = cast(_Axes, ax)

    for offset, data, pol in [
        (-width / 2, per_device_fpr_global, ThresholdPolicy.GLOBAL_THRESHOLD),
        (width / 2, per_device_fpr_local, ThresholdPolicy.LOCAL_THRESHOLD),
    ]:
        ax.bar(
            x + offset,
            [data[d] for d in devices],
            width,
            label=style.policy_labels[pol],
            color=style.policy_colors[pol],
        )

    ax.set(xlabel="Device", ylabel="FPR")
    ax.set_xticks(x)
    ax.set_xticklabels(
        [NBAIOT_DEVICE_SHORT_LABELS[NBaIoTDevice(d)] for d in devices],
        rotation=45,
        ha="right",
        fontsize=style.font_size - 1,
    )
    ax.legend()
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    return _save_figs(fig, output_dir / FigureName.FIGURE_1, style.dpi)


def generate_figure2(
    cal_errors: dict[ClientId, ScoreVector],
    tau_global: Threshold,
    device_ids: list[ClientId],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size
    fig, ax = plt.subplots(figsize=style.figsize_double_col)
    ax = cast(_Axes, ax)
    all_vals = np.concatenate([cal_errors[d] for d in device_ids if d in cal_errors])
    x_clip = float(np.percentile(all_vals, 99))

    for dev_id in device_ids:
        if dev_id not in cal_errors:
            continue
        errors = np.sort(cal_errors[dev_id])
        ecdf_y = np.arange(1, len(errors) + 1) / len(errors)
        mask = errors <= x_clip
        ax.plot(
            errors[mask],
            ecdf_y[mask],
            label=NBAIOT_DEVICE_SHORT_LABELS[NBaIoTDevice(dev_id)],
            linewidth=1.4,
        )

    ax.axvline(
        tau_global,
        color="black",
        linestyle="--",
        linewidth=1.2,
        label="GLOBAL_THRESHOLD client-averaged threshold",
    )
    ax.set(xlabel="Reconstruction Error", ylabel="ECDF")
    ax.legend(fontsize=style.font_size - 1)
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    return _save_figs(fig, output_dir / FigureName.FIGURE_2, style.dpi)


def generate_figure3(
    fpr_by_policy: dict[ThresholdPolicy, list[ScoreVector]],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size
    fig, ax = plt.subplots(figsize=style.figsize_single_col)
    ax = cast(_Axes, ax)
    policies = sorted(fpr_by_policy.keys())

    bp = ax.boxplot(
        [np.concatenate(fpr_by_policy[b]) for b in policies],
        tick_labels=[style.policy_labels[b] for b in policies],
        patch_artist=True,
    )
    for patch, color in zip(bp["boxes"], [style.policy_colors[b] for b in policies]):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.set(
        ylabel="FPR", title="Per-client FPR Distribution (eligible clients, 10 seeds)"
    )
    ax.tick_params(axis="x", labelrotation=30)
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    return _save_figs(fig, output_dir / FigureName.FIGURE_3, style.dpi)


def generate_figure5(
    client_effects: dict[NarrativeText, dict[ThresholdPolicy, dict[ClientId, list[ScoreValue]]]],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size
    panels = list(client_effects)
    fig, axes = plt.subplots(
        1, len(panels), figsize=style.figsize_double_col, squeeze=False
    )
    for raw_ax, label in zip(axes[0], panels):
        ax = cast(_Axes, raw_ax)
        by_policy = client_effects[label]
        victims = sorted({v for per in by_policy.values() for v in per})
        policies = sorted(by_policy)
        width = 0.8 / max(len(policies), 1)
        for i, pol in enumerate(policies):
            xs: list[ScoreValue] = []
            means: list[ScoreValue] = []
            lows: list[ScoreValue] = []
            highs: list[ScoreValue] = []
            for j, v in enumerate(victims):
                vals = by_policy[pol].get(v)
                if not vals:
                    continue
                xs.append(j + (i - (len(policies) - 1) / 2) * width)
                means.append(float(np.mean(vals)))
                lows.append(float(np.mean(vals)) - min(vals))
                highs.append(max(vals) - float(np.mean(vals)))
            ax.errorbar(
                xs,
                means,
                yerr=[lows, highs],
                fmt="o",
                markersize=3,
                capsize=2,
                linewidth=1.0,
                color=style.policy_colors[pol],
                label=style.policy_labels[pol],
            )
        ax.axhline(0.0, color="black", linewidth=0.6)
        ax.set_xticks(np.arange(len(victims)))
        ax.set_xticklabels(
            [NBAIOT_DEVICE_SHORT_LABELS[NBaIoTDevice(v)] for v in victims],
            rotation=60,
            ha="right",
            fontsize=style.font_size - 2,
        )
        ax.set(ylabel=label)
    cast(_Axes, axes[0][0]).legend(fontsize=style.font_size - 2)
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    return _save_figs(fig, output_dir / FigureName.FIGURE_5, style.dpi)


def generate_figure6(
    seed_effects: dict[RecordKey, dict[ThresholdPolicy, list[ScoreValue]]],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    plt.rcParams[_FONT_SIZE_KEY] = style.font_size
    panels = list(seed_effects)
    fig, axes = plt.subplots(
        1, len(panels), figsize=style.figsize_double_col, squeeze=False
    )
    rng = np.random.default_rng(0)
    for raw_ax, label in zip(axes[0], panels):
        ax = cast(_Axes, raw_ax)
        by_policy = seed_effects[label]
        policies = sorted(by_policy)
        for i, pol in enumerate(policies):
            vals = np.asarray(by_policy[pol], dtype=np.float64)
            ax.scatter(
                i + rng.uniform(-0.12, 0.12, vals.size),
                vals,
                s=14,
                color=style.policy_colors[pol],
                alpha=0.8,
            )
            ax.hlines(
                float(np.nanmean(vals)), i - 0.3, i + 0.3, color="black", linewidth=1.2
            )
        ax.axhline(0.0, color="black", linewidth=0.6, linestyle=":")
        ax.set_xticks(np.arange(len(policies)))
        ax.set_xticklabels(
            [style.policy_labels[p] for p in policies],
            rotation=30,
            ha="right",
            fontsize=style.font_size - 2,
        )
        ax.set(ylabel=label)
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    return _save_figs(fig, output_dir / FigureName.FIGURE_6, style.dpi)


MANDATORY_FOOTNOTE = (
    "† Eligible clients only. CV is the population standard deviation divided by the mean. "
    "Worst BA is the minimum per-client balanced accuracy, (TPR + TNR) / 2. "
    "P10 client Macro-F1 is the 10th percentile of per-client macro-F1, the mean of the benign-class and attack-class F1."
)


def validate_main_body_role(policies: list[ThresholdPolicy]) -> None:
    for p in policies:
        if p not in MAIN_BODY_POLICIES:
            raise ValueError(
                f"Policy '{p}' not permitted. Allowed: {[p for p in MAIN_BODY_POLICIES]}"
            )


def format_mean_std(mean: ScoreValue, std: ScoreValue, bold: bool = False) -> NarrativeText:
    if np.isnan(mean):
        return "---"
    text = f"{mean:.3f} ± {std:.3f}"
    return f"\\textbf{{{text}}}" if bold else text


@dataclass(frozen=True, slots=True)
class TableRow:

    policy: ThresholdPolicy
    cv_fpr_mean: FalsePositiveRate
    cv_fpr_std: FalsePositiveRate
    cv_tpr_mean: TruePositiveRate
    cv_tpr_std: TruePositiveRate
    worst_ba_mean: ScoreValue
    worst_ba_std: ScoreValue
    macro_f1_mean: ClassificationScore
    macro_f1_std: ClassificationScore
    eligible_count: SampleCount
    pending_count: SampleCount
    coverage_ratio: Ratio


@dataclass(slots=True)
class ResultTable:

    title: NarrativeText
    style: StyleConfig
    rows: list[TableRow] = field(default_factory=lambda: list[TableRow]())
    footnote: NarrativeText = MANDATORY_FOOTNOTE

    def to_latex(self) -> NarrativeText:
        best_cv_fpr = (
            min(self.rows, key=lambda r: r.cv_fpr_mean).policy if self.rows else None
        )
        best_cv_tpr = (
            min(self.rows, key=lambda r: r.cv_tpr_mean).policy if self.rows else None
        )
        labels = self.style.policy_labels

        rows_tex: list[NarrativeText] = []
        for r in self.rows:
            lbl = labels[r.policy]
            cov = f"{r.coverage_ratio:.2f} ({r.eligible_count}/{r.eligible_count + r.pending_count})"
            cv_fpr = (
                format_mean_std(r.cv_fpr_mean, r.cv_fpr_std, r.policy == best_cv_fpr)
                + f" ({r.eligible_count}/{r.eligible_count + r.pending_count})"
            )
            cv_tpr = format_mean_std(
                r.cv_tpr_mean, r.cv_tpr_std, r.policy == best_cv_tpr
            )
            wba = format_mean_std(r.worst_ba_mean, r.worst_ba_std)
            f1 = format_mean_std(r.macro_f1_mean, r.macro_f1_std)
            rows_tex.append(f"{lbl} & {cv_fpr} & {cv_tpr} & {wba} & {f1} & {cov} \\\\")

        rows_str = "\n".join(rows_tex)

        return f"""\\begin{{table}}[htbp]
\\caption{{{self.title}}}
\\centering
\\begin{{tabular}}{{l c c c c c}}
\\toprule
ThresholdPolicy & CV(FPR)$\\dagger$ & CV(TPR)$\\dagger$ & Worst BA & P10 client Macro-F1 & Coverage \\\\
\\midrule
{rows_str}
\\bottomrule
\\end{{tabular}}

\\footnotesize{{{self.footnote}}}
\\end{{table}}"""

    def to_csv(self, path: Path) -> Path:
        labels = self.style.policy_labels
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "ThresholdPolicy",
                    "CV(FPR) mean",
                    "CV(FPR) std",
                    "CV(TPR) mean",
                    "CV(TPR) std",
                    "Worst BA mean",
                    "Worst BA std",
                    "P10 client Macro-F1 mean",
                    "P10 client Macro-F1 std",
                    "Eligible",
                    "Pending",
                    "Coverage",
                ]
            )
            for r in self.rows:
                writer.writerow(
                    [
                        labels[r.policy],
                        f"{r.cv_fpr_mean:.4f}",
                        f"{r.cv_fpr_std:.4f}",
                        f"{r.cv_tpr_mean:.4f}",
                        f"{r.cv_tpr_std:.4f}",
                        f"{r.worst_ba_mean:.4f}",
                        f"{r.worst_ba_std:.4f}",
                        f"{r.macro_f1_mean:.4f}",
                        f"{r.macro_f1_std:.4f}",
                        r.eligible_count,
                        r.pending_count,
                        f"{r.coverage_ratio:.4f}",
                    ]
                )
            writer.writerow([f" {self.footnote}"])
        return path


def _mean_std(values: list[ScoreValue]) -> tuple[ScoreValue, ScoreValue]:
    return float(np.mean(values)), float(np.std(values, ddof=1)) if len(
        values
    ) > 1 else 0.0


def _build_table_row(
    policy: ThresholdPolicy, results: list[EvaluationResult]
) -> TableRow:
    eligible_count = len(results[0].eligible_ids)
    pending_count = len(results[0].pending_ids)
    if any(not np.isfinite(result.coverage_ratio) for result in results):
        raise ValueError(f"Coverage ratio missing for {policy}.")
    if any(
        len(result.eligible_ids) != eligible_count
        or len(result.pending_ids) != pending_count
        for result in results
    ):
        raise ValueError(f"Coverage count mismatch for {policy}.")

    cv_fpr_mean, cv_fpr_std = _mean_std([r.dispersion.cv_fpr for r in results])
    cv_tpr_mean, cv_tpr_std = _mean_std([r.dispersion.cv_tpr for r in results])
    worst_ba_mean, worst_ba_std = _mean_std(
        [r.dispersion.worst_ba for r in results]
    )
    macro_f1_mean, macro_f1_std = _mean_std(
        [r.dispersion.p10_macro_f1 for r in results]
    )
    return TableRow(
        policy=policy,
        cv_fpr_mean=cv_fpr_mean,
        cv_fpr_std=cv_fpr_std,
        cv_tpr_mean=cv_tpr_mean,
        cv_tpr_std=cv_tpr_std,
        worst_ba_mean=worst_ba_mean,
        worst_ba_std=worst_ba_std,
        macro_f1_mean=macro_f1_mean,
        macro_f1_std=macro_f1_std,
        eligible_count=eligible_count,
        pending_count=pending_count,
        coverage_ratio=results[0].coverage_ratio,
    )


def generate_table3(
    results_by_policy: dict[ThresholdPolicy, list[EvaluationResult]],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    validate_main_body_role(list(results_by_policy.keys()))
    table = ResultTable(title="Table 3: N-BaIoT Main Results", style=style)

    for policy, results in sorted(results_by_policy.items()):
        table.rows.append(_build_table_row(policy, results))

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = output_dir / "table3_nbaiot"
    stem.with_suffix(".tex").write_text(table.to_latex(), encoding="utf-8")
    table.to_csv(stem.with_suffix(".csv"))
    return stem.with_suffix(".tex")
