from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import csv
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from datp.config.models import StyleConfig
from datp.evaluation.metrics import EvaluationResult
from datp.reporting.engine import format_mean_std as _format_mean_std
from datp.reporting.engine import render
from datp.reporting.validation import validate_main_body_role

MANDATORY_FOOTNOTE = "† Eligible clients only."


@dataclass(frozen=True, slots=True)
class TableRow:
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


@dataclass(frozen=True, slots=True)
class LatexTableRow:
    label: str
    cv_fpr: str
    cv_tpr: str
    worst_ba: str
    macro_f1: str
    coverage: str


def _format_coverage_count(
    coverage_ratio: float, eligible_count: int, total_count: int
) -> str:
    return f"{coverage_ratio:.2f} ({eligible_count}/{total_count})"


@dataclass(slots=True)
class ResultTable:
    title: str
    style: StyleConfig
    rows: list[TableRow] = field(default_factory=list)
    footnote: str = MANDATORY_FOOTNOTE

    def to_latex(self) -> str:
        best_cv_fpr = (
            min(self.rows, key=lambda r: r.cv_fpr_mean).policy if self.rows else None
        )
        best_cv_tpr = (
            min(self.rows, key=lambda r: r.cv_tpr_mean).policy if self.rows else None
        )

        labels = self.style.policy_labels
        template_rows: list[LatexTableRow] = []
        for row in self.rows:
            label = labels[row.policy]
            template_rows.append(
                LatexTableRow(
                    label=label,
                    cv_fpr=_format_mean_std(
                        row.cv_fpr_mean,
                        row.cv_fpr_std,
                        bold=(row.policy == best_cv_fpr),
                    )
                    + f" ({row.eligible_count}/{row.eligible_count + row.pending_count})",
                    cv_tpr=_format_mean_std(
                        row.cv_tpr_mean,
                        row.cv_tpr_std,
                        bold=(row.policy == best_cv_tpr),
                    ),
                    worst_ba=_format_mean_std(
                        row.worst_ba_mean, row.worst_ba_std, bold=False
                    ),
                    macro_f1=_format_mean_std(
                        row.macro_f1_mean, row.macro_f1_std, bold=False
                    ),
                    coverage=_format_coverage_count(
                        row.coverage_ratio,
                        row.eligible_count,
                        row.eligible_count + row.pending_count,
                    ),
                )
            )

        eligible_counts = ", ".join(
            f"{labels[r.policy]}: {r.eligible_count}" for r in self.rows
        )
        pending_counts = ", ".join(
            f"{labels[r.policy]}: {r.pending_count}" for r in self.rows
        )

        return render(
            "table_main.tex.j2",
            title=self.title,
            caption=self.title,
            header=(
                "ThresholdPolicy & CV(FPR)$\\dagger$ & CV(TPR)$\\dagger$ "
                "& Worst BA & P10 client Macro-F1 & Coverage"
            ),
            rows=template_rows,
            footnote=self.footnote,
            comments=[
                f"Eligible counts: {eligible_counts}",
                f"Calibration-Pending counts: {pending_counts}",
            ],
        )

    def to_csv(self, path: Path) -> Path:
        labels = self.style.policy_labels
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as f:
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
            for row in self.rows:
                label = labels[row.policy]
                writer.writerow(
                    [
                        label,
                        f"{row.cv_fpr_mean:.4f}",
                        f"{row.cv_fpr_std:.4f}",
                        f"{row.cv_tpr_mean:.4f}",
                        f"{row.cv_tpr_std:.4f}",
                        f"{row.worst_ba_mean:.4f}",
                        f"{row.worst_ba_std:.4f}",
                        f"{row.macro_f1_mean:.4f}",
                        f"{row.macro_f1_std:.4f}",
                        row.eligible_count,
                        row.pending_count,
                        f"{row.coverage_ratio:.4f}",
                    ]
                )
            writer.writerow([f"# {self.footnote}"])
        return path


def _mean_std(values: list[float]) -> tuple[float, float]:
    """Return (mean, sample std) for a list; std is 0.0 for a single element."""
    return float(np.mean(values)), float(np.std(values, ddof=1)) if len(
        values
    ) > 1 else 0.0


def _validate_coverage_stability(
    policy: ThresholdPolicy,
    results: list[EvaluationResult],
    expected_eligible: int,
    expected_pending: int,
) -> None:
    """Raise if any result has non-finite coverage or mismatched eligible/pending counts."""
    for result in results:
        if not np.isfinite(result.coverage_ratio):
            raise ValueError(
                f"[reporting] Coverage ratio missing. Expected: finite coverage for {policy}. Got: {result.coverage_ratio}."
            )
        if (
            len(result.eligible_ids) != expected_eligible
            or len(result.pending_ids) != expected_pending
        ):
            raise ValueError(
                f"[reporting] Coverage count mismatch. Expected: stable eligible/pending counts for {policy}. Got: seed={result.seed} eligible={len(result.eligible_ids)} pending={len(result.pending_ids)}."
            )


def _build_table_row(
    policy: ThresholdPolicy,
    results: list[EvaluationResult],
) -> TableRow:
    eligible_count = len(results[0].eligible_ids)
    pending_count = len(results[0].pending_ids)
    _validate_coverage_stability(policy, results, eligible_count, pending_count)

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


def _generate_table(
    title: str,
    results_by_policy: dict[ThresholdPolicy, list[EvaluationResult]],
    output_dir: Path,
    filename_stem: str,
    style: StyleConfig,
) -> Path:
    validate_main_body_role(list(results_by_policy.keys()))

    table = ResultTable(title=title, style=style)
    for policy in sorted(results_by_policy.keys()):
        table.rows.append(_build_table_row(policy, results_by_policy[policy]))

    output_dir.mkdir(parents=True, exist_ok=True)

    tex_path = output_dir / f"{filename_stem}.tex"
    tex_path.write_text(table.to_latex(), encoding="utf-8")

    csv_path = output_dir / f"{filename_stem}.csv"
    table.to_csv(csv_path)

    return tex_path


def generate_table3(
    results_by_policy: dict[ThresholdPolicy, list[EvaluationResult]],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    return _generate_table(
        title="Table 3: N-BaIoT Main Results",
        results_by_policy=results_by_policy,
        output_dir=output_dir,
        filename_stem="table3_nbaiot",
        style=style,
    )


def generate_table4(
    results_by_policy: dict[ThresholdPolicy, list[EvaluationResult]],
    output_dir: Path,
    style: StyleConfig,
) -> Path:
    return _generate_table(
        title="Table 4: CICIoT2023 External Validation Results",
        results_by_policy=results_by_policy,
        output_dir=output_dir,
        filename_stem="table4_ciciot",
        style=style,
    )
