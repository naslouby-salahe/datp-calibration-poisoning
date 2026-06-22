# SPDX-License-Identifier: Proprietary
"""Rich console utilities for sweep experiment output."""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import enum
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from datp.config.stages import ExperimentStage
from datp.experiments.enums import PolicyRunStatus, SweepStep

if TYPE_CHECKING:
    from datp.experiments.sweep import SweepResult

console = Console()

# ── display enums ─────────────────────────────────────────────────────────
# View-layer enums for Rich markup / console formatting, not domain types.


class _Symbol(enum.StrEnum):
    CHECK = "✓"
    CROSS = "✗"
    CIRCLE = "○"
    ARROW = "→"


class _Label(enum.StrEnum):
    COVERAGE = "coverage"
    METRIC = "Metric"
    VALUE = "Value"
    CELLS = "Cells"
    TOTAL = "Total"
    COMPLETED = "Completed"
    SKIPPED = "Skipped"
    FAILED = "Failed"
    DURATION = "Duration"
    OUTPUT = "Output"
    OVERALL = "Overall"
    CONTINGENCY = "Contingency"
    GLOBAL_CV_FPR = "GLOBAL_THRESHOLD CV(FPR)"
    LOCAL_CV_FPR = "LOCAL_THRESHOLD CV(FPR)"
    DELTA_CV_FPR = "Δ CV(FPR)"


class _Title(enum.StrEnum):
    SWEEP = "[bold]datp-cp Sweep[/bold]"
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
    SweepStep.EVALUATE: "Evaluate policy",
    SweepStep.WRITE_METRICS: "Write metrics",
    SweepStep.SWEEP_COMPLETE: "Sweep complete",
}

_STATUS_SYMBOLS: dict[PolicyRunStatus, str] = {
    PolicyRunStatus.DONE: f"[green]{_Symbol.CHECK}[/green]",
    PolicyRunStatus.SKIPPED: f"[dim]{_Symbol.ARROW}[/dim]",
    PolicyRunStatus.FAILED: f"[red]{_Symbol.CROSS}[/red]",
}


def print_sweep_banner(
    cell_count: int,
    base_dir: str,
) -> None:
    lines = [
        f"Stage: [cyan]NBAIOT_MAIN[/cyan] Cells: [cyan]{cell_count}[/cyan]",
        f"Output: [dim]{base_dir}[/dim]",
    ]
    console.print(Panel("\n".join(lines), title=_Title.SWEEP, border_style=_Style.CYAN))


def print_dry_run_summary(total_cells: int) -> None:
    table = Table(title=_Title.SWEEP_MATRIX, border_style=_Style.CYAN)
    table.add_column(_Label.CELLS, justify="right")

    table.add_row(str(total_cells), style="bold")
    console.print(table)
    console.print(_Message.DRY_RUN)


def print_step(step: SweepStep, detail: str) -> None:
    label = _SWEEP_STEP_LABELS[step]
    detail_str = f" [dim]{detail}[/dim]" if detail else ""
    console.print(f" [dim][{step.value}][/dim] [bold]{label}[/bold]{detail_str}")


def print_group_header(
    stage: ExperimentStage,
    seed: int,
    group_size: int,
    current: int,
    total: int,
) -> None:
    progress = f"[{current}/{total}]"
    console.print(
        f"\n[bold yellow]{'─' * _DIVIDER_WIDTH}[/bold yellow]\n"
        f"[bold yellow] Group {progress}[/bold yellow]"
        f" stage={stage.value} seed={seed}"
        f" [dim]({group_size} cells)[/dim]",
    )


def print_policy_result(
    policy: ThresholdPolicy,
    status: PolicyRunStatus,
    elapsed_s: float,
) -> None:
    symbol = _STATUS_SYMBOLS[status]
    elapsed_str = f"[dim]({elapsed_s:.1f}s)[/dim]" if elapsed_s > 0 else ""
    console.print(f" {symbol} [bold]{policy.upper()}[/bold] {elapsed_str}")


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
