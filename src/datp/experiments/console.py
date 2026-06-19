# SPDX-License-Identifier: Proprietary
"""Rich console utilities for diagnostic and sweep experiment output."""

from __future__ import annotations

import enum
import time
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from datp.core.enums import Baseline, BaselineRunStatus, Regime
from datp.experiments.enums import ContingencyDecision, DiagnosticStep, SweepStep

if TYPE_CHECKING:
    from datp.experiments.sweep import SweepResult

console = Console()

# ── display enums ─────────────────────────────────────────────────────────
# View-layer enums for Rich markup / console formatting, not domain types.


class _Symbol(enum.StrEnum):
    CHECK = "\u2713"
    CROSS = "\u2717"
    CIRCLE = "\u25cb"
    ARROW = "\u2192"


class _Label(enum.StrEnum):
    COVERAGE = "coverage"
    METRIC = "Metric"
    VALUE = "Value"
    REGIME = "Regime"
    CELLS = "Cells"
    TOTAL = "Total"
    COMPLETED = "Completed"
    SKIPPED = "Skipped"
    FAILED = "Failed"
    DURATION = "Duration"
    OUTPUT = "Output"
    OVERALL = "Overall"
    CONTINGENCY = "Contingency"
    B1_CV_FPR = "B1 CV(FPR)"
    B2_CV_FPR = "B2 CV(FPR)"
    DELTA_CV_FPR = "\u0394 CV(FPR)"
    REGIME_ALL = "ALL"


class _Title(enum.StrEnum):
    DIAGNOSTIC = "[bold]DATP Diagnostic[/bold]"
    SWEEP = "[bold]DATP Sweep[/bold]"
    SWEEP_MATRIX = "Sweep Matrix"
    SWEEP_SUMMARY = "Sweep Summary"


class _Message(enum.StrEnum):
    DRY_RUN = "[dim]Dry run only. No training launched.[/dim]"
    CHECKPOINT_FOUND = "checkpoint found"
    CHECKPOINT_MISSING = "no checkpoint — will train"
    FAILED = "FAILED"


class _Style(enum.StrEnum):
    CYAN = "cyan"
    GREEN = "green"


_DIVIDER_WIDTH = 56

# ---------------------------------------------------------------------------
# Diagnostic step labels and helpers
# ---------------------------------------------------------------------------

_DIAGNOSTIC_STEP_LABELS: dict[DiagnosticStep, str] = {
    DiagnosticStep.COMPOSE_CONFIG: "Compose config",
    DiagnosticStep.VALIDATE_CONFIG: "Validate config",
    DiagnosticStep.PREPARE_DATA: "Prepare data",
    DiagnosticStep.SET_SEEDS: "Set seeds",
    DiagnosticStep.FL_TRAINING: "FL training",
    DiagnosticStep.LOAD_SCORES: "Load score artifacts",
    DiagnosticStep.DERIVE_THRESHOLDS: "Derive thresholds (B1 + B2)",
    DiagnosticStep.EVALUATE: "Evaluate baselines",
    DiagnosticStep.WRITE_METRICS: "Write metrics",
    DiagnosticStep.CONTINGENCY_DECISION: "Contingency decision",
    DiagnosticStep.SUMMARY: "Summary",
}


def print_banner(
    regime: Regime,
    seed: int,
    output_dir: str,
    *,
    alpha: float | None = None,
) -> None:
    lines = [f"Regime: [cyan]{regime.value.upper()}[/cyan] Seed: [cyan]{seed}[/cyan]"]
    if alpha is not None:
        lines.append(f"Alpha: [cyan]{alpha:g}[/cyan]")
    lines.append(f"Output: [dim]{output_dir}[/dim]")
    console.print(
        Panel("\n".join(lines), title=_Title.DIAGNOSTIC, border_style=_Style.CYAN)
    )


@contextmanager
def step_context(step: DiagnosticStep) -> Iterator[None]:
    label = _DIAGNOSTIC_STEP_LABELS[step]
    ordinal = list(DiagnosticStep).index(step) + 1
    console.print(f" [dim][{ordinal:>2}][/dim] [bold]{label}[/bold] ...", end="")
    t0 = time.monotonic()
    try:
        yield
    except Exception:
        elapsed = time.monotonic() - t0
        console.print(
            f" [red]{_Symbol.CROSS} {_Message.FAILED}[/red] [dim]({elapsed:.1f}s)[/dim]"
        )
        raise
    elapsed = time.monotonic() - t0
    console.print(f" [green]{_Symbol.CHECK}[/green] [dim]({elapsed:.1f}s)[/dim]")


def print_summary(
    regime: Regime,
    seed: int,
    b1_cv_fpr: float,
    b2_cv_fpr: float,
    coverage: tuple[int, int],
    output_dir: str,
    total_elapsed: float,
    *,
    alpha: float | None = None,
    contingency: ContingencyDecision | None = None,
) -> None:
    title = f"Regime {regime.value.upper()}"
    if alpha is not None:
        title += f" (\u03b1={alpha:g})"
    title += f", seed {seed}"

    delta = b1_cv_fpr - b2_cv_fpr
    eligible, total = coverage

    table = Table(title=title, border_style=_Style.GREEN)
    table.add_column(_Label.METRIC, style="bold")
    table.add_column(_Label.VALUE)
    table.add_row(
        _Label.B1_CV_FPR, f"{b1_cv_fpr:.4f} ({_Label.COVERAGE}: {eligible}/{total})"
    )
    table.add_row(
        _Label.B2_CV_FPR, f"{b2_cv_fpr:.4f} ({_Label.COVERAGE}: {eligible}/{total})"
    )
    table.add_row(_Label.DELTA_CV_FPR, f"{delta:.4f}")
    if contingency is not None:
        table.add_row(_Label.CONTINGENCY, contingency.value.upper())
    table.add_row(_Label.DURATION, f"{total_elapsed:.1f}s")
    table.add_row(_Label.OUTPUT, f"{output_dir}/")
    console.print(table)


# ---------------------------------------------------------------------------
# Sweep step labels and helpers
# ---------------------------------------------------------------------------

_SWEEP_STEP_LABELS: dict[SweepStep, str] = {
    SweepStep.BUILD_MATRIX: "Build experiment matrix",
    SweepStep.VALIDATE_MATRIX: "Validate sweep matrix",
    SweepStep.CHECK_CHECKPOINT: "Check FL checkpoint",
    SweepStep.TRAIN_FL: "Train FL model",
    SweepStep.LOAD_CAL_SCORES: "Load calibration scores",
    SweepStep.COMPUTE_ELIGIBILITY: "Compute client eligibility",
    SweepStep.COMPUTE_TAU_GLOBAL: "Compute tau_global",
    SweepStep.INIT_SCORE_PROVIDER: "Initialize score provider",
    SweepStep.DERIVE_THRESHOLD: "Derive threshold",
    SweepStep.EVALUATE: "Evaluate baseline",
    SweepStep.WRITE_METRICS: "Write metrics",
    SweepStep.RUN_B0: "Run B0 (centralized reference)",
    SweepStep.SWEEP_COMPLETE: "Sweep complete",
}

_STATUS_SYMBOLS: dict[BaselineRunStatus, str] = {
    BaselineRunStatus.DONE: f"[green]{_Symbol.CHECK}[/green]",
    BaselineRunStatus.SKIPPED: f"[dim]{_Symbol.ARROW}[/dim]",
    BaselineRunStatus.FAILED: f"[red]{_Symbol.CROSS}[/red]",
}


def print_sweep_banner(
    regime: Regime | None,
    cell_count: int,
    base_dir: str,
) -> None:
    regime_display = _Label.REGIME_ALL if regime is None else regime.upper()
    lines = [
        f"Regime: [cyan]{regime_display}[/cyan] Cells: [cyan]{cell_count}[/cyan]",
        f"Output: [dim]{base_dir}[/dim]",
    ]
    console.print(Panel("\n".join(lines), title=_Title.SWEEP, border_style=_Style.CYAN))


def print_dry_run_summary(regime_counts: dict[Regime, int], total_cells: int) -> None:
    table = Table(title=_Title.SWEEP_MATRIX, border_style=_Style.CYAN)
    table.add_column(_Label.REGIME, style="bold")
    table.add_column(_Label.CELLS, justify="right")

    for regime in sorted(regime_counts):
        table.add_row(f"Regime {regime.upper()}", str(regime_counts[regime]))
    table.add_row(_Label.OVERALL, str(total_cells), style="bold")
    console.print(table)
    console.print(_Message.DRY_RUN)


def print_step(step: SweepStep, detail: str) -> None:
    label = _SWEEP_STEP_LABELS[step]
    detail_str = f" [dim]{detail}[/dim]" if detail else ""
    console.print(f" [dim][{step.value}][/dim] [bold]{label}[/bold]{detail_str}")


def print_group_header(
    regime: Regime,
    seed: int,
    alpha: float | None,
    group_size: int,
    current: int,
    total: int,
) -> None:
    alpha_str = f" \u03b1={alpha:g}" if alpha is not None else ""
    progress = f"[{current}/{total}]"
    console.print(
        f"\n[bold yellow]{'─' * _DIVIDER_WIDTH}[/bold yellow]\n"
        f"[bold yellow] Group {progress}[/bold yellow]"
        f" regime={regime.upper()} seed={seed}{alpha_str}"
        f" [dim]({group_size} cells)[/dim]",
    )


def print_baseline_result(
    baseline: Baseline,
    status: BaselineRunStatus,
    elapsed_s: float,
) -> None:
    symbol = _STATUS_SYMBOLS[status]
    elapsed_str = f"[dim]({elapsed_s:.1f}s)[/dim]" if elapsed_s > 0 else ""
    console.print(f" {symbol} [bold]{baseline.upper()}[/bold] {elapsed_str}")


def print_checkpoint_status(found: bool, ckpt_path: Path) -> None:
    if found:
        console.print(
            f" [green]{_Symbol.CHECK} {_Message.CHECKPOINT_FOUND}[/green] [dim]{ckpt_path}[/dim]"
        )
    else:
        console.print(
            f" [yellow]{_Symbol.CIRCLE} {_Message.CHECKPOINT_MISSING}[/yellow] [dim]{ckpt_path}[/dim]"
        )


def print_sweep_summary(result: "SweepResult", elapsed_s: float) -> None:
    table = Table(title=_Title.SWEEP_SUMMARY, border_style=_Style.GREEN)
    table.add_column(_Label.METRIC, style="bold")
    table.add_column(_Label.VALUE)
    table.add_row(_Label.TOTAL, str(result.total))
    table.add_row(_Label.COMPLETED, f"[green]{result.completed}[/green]")
    table.add_row(_Label.SKIPPED, f"[dim]{result.skipped}[/dim]")
    failed_style = "red" if result.failed > 0 else ""
    table.add_row(
        _Label.FAILED,
        f"[{failed_style}]{result.failed}[/{failed_style}]"
        if failed_style
        else str(result.failed),
    )
    table.add_row(_Label.DURATION, f"{elapsed_s:.1f}s")
    console.print(table)
