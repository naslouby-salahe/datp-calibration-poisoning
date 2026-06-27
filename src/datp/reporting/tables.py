"""LaTeX and CSV table generators with main-body-policy validation."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from datp.config.models import StyleConfig
from datp.core.enums import MAIN_BODY_POLICIES, ThresholdPolicy
from datp.evaluation.metrics import EvaluationResult

MANDATORY_FOOTNOTE = "† Eligible clients only."


def validate_main_body_role(policies: list[ThresholdPolicy]) -> None:
    """Raise ValueError if any policy is not in the allowed main-body policy set."""
    for p in policies:
        if p not in MAIN_BODY_POLICIES:
            raise ValueError(
                f"Policy '{p}' not permitted. Allowed: {[p.value for p in MAIN_BODY_POLICIES]}"
            )


def format_mean_std(mean: float, std: float, bold: bool = False) -> str:
    """Format a mean-plus-minus-std pair as a LaTeX string, with NaN fallback."""
    if np.isnan(mean):
        return "---"
    text = f"{mean:.3f} ± {std:.3f}"
    return f"\\textbf{{{text}}}" if bold else text


@dataclass(frozen=True, slots=True)
class TableRow:
    """A single row in a results table aggregating evaluation metrics for one threshold policy."""

    policy: ThresholdPolicy
    cv_fpr_mean: float
    cv_fpr_std: float
    cv_tpr_mean: float
    cv_tpr_std: float
    worst_ba_mean: float
    worst_ba_std: float
    macro_f1_mean: float
    macro_f1_std: float
    eligible_count: int
    pending_count: int
    coverage_ratio: float


@dataclass(slots=True)
class ResultTable:
    """LaTeX/CSV results table with styled rows and main-body-policy validation."""

    title: str
    style: StyleConfig
    rows: list[TableRow] = field(default_factory=list)
    footnote: str = MANDATORY_FOOTNOTE

    def to_latex(self) -> str:
        """Render the table as a LaTeX tabular with bold-best highlighting."""
        best_cv_fpr = (
            min(self.rows, key=lambda r: r.cv_fpr_mean).policy if self.rows else None
        )
        best_cv_tpr = (
            min(self.rows, key=lambda r: r.cv_tpr_mean).policy if self.rows else None
        )
        labels = self.style.policy_labels

        rows_tex = []
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
        """Write the table to a CSV file and return the path."""
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


def _mean_std(values: list[float]) -> tuple[float, float]:
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

    cv_fpr_mean, cv_fpr_std = _mean_std([r.cv_fpr for r in results])
    cv_tpr_mean, cv_tpr_std = _mean_std([r.cv_tpr for r in results])
    worst_ba_mean, worst_ba_std = _mean_std([r.worst_ba for r in results])
    macro_f1_mean, macro_f1_std = _mean_std([r.p10_macro_f1 for r in results])
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
    """Generate Table 3 (N-BaIoT main results) as LaTeX and CSV."""
    validate_main_body_role(list(results_by_policy.keys()))
    table = ResultTable(title="Table 3: N-BaIoT Main Results", style=style)

    for policy, results in sorted(results_by_policy.items()):
        table.rows.append(_build_table_row(policy, results))

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = output_dir / "table3_nbaiot"
    stem.with_suffix(".tex").write_text(table.to_latex(), encoding="utf-8")
    table.to_csv(stem.with_suffix(".csv"))
    return stem.with_suffix(".tex")
