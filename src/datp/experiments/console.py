"""Rich console pretty-printing for sweep progress banners and result summaries."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.experiments.models import PolicyRunStatus, SweepStep

if TYPE_CHECKING:
    from datp.experiments.sweep import SweepResult

console = Console()

_SWEEP_STEP_LABELS = {
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

_STATUS_SYMBOLS = {
    PolicyRunStatus.DONE: "[green]✓[/green]",
    PolicyRunStatus.SKIPPED: "[dim]→[/dim]",
    PolicyRunStatus.FAILED: "[red]✗[/red]",
}


def print_sweep_banner(cell_count: int, base_dir: str) -> None:
    """Print a Rich panel banner announcing the sweep stage and cell count."""
    lines = [
        f"Stage: [cyan]NBAIOT_MAIN[/cyan] Cells: [cyan]{cell_count}[/cyan]",
        f"Output: [dim]{base_dir}[/dim]",
    ]
    console.print(
        Panel("\n".join(lines), title="[bold]datp-cp Sweep[/bold]", border_style="cyan")
    )


def print_dry_run_summary(total_cells: int) -> None:
    """Print a table summarizing the sweep matrix for dry-run mode."""
    table = Table(title="Sweep Matrix", border_style="cyan")
    table.add_column("Cells", justify="right")
    table.add_row(str(total_cells), style="bold")
    console.print(table)
    console.print("[dim]Dry run only. No training launched.[/dim]")


def print_step(step: SweepStep, detail: str) -> None:
    """Print a labelled sweep step with optional detail text."""
    detail_str = f" [dim]{detail}[/dim]" if detail else ""
    console.print(
        f" [dim][{step.value}][/dim] [bold]{_SWEEP_STEP_LABELS[step]}[/bold]{detail_str}"
    )


def print_group_header(
    stage: ExperimentStage, seed: int, group_size: int, current: int, total: int
) -> None:
    """Print a formatted group header with stage, seed, and progress indicator."""
    progress = f"[{current}/{total}]"
    console.print(
        f"\n[bold yellow]{'─' * 56}[/bold yellow]\n[bold yellow] Group {progress}[/bold yellow] stage={stage.value} seed={seed} [dim]({group_size} cells)[/dim]"
    )


def print_policy_result(
    policy: ThresholdPolicy, status: PolicyRunStatus, elapsed_s: float
) -> None:
    """Print a single policy's result with status symbol and elapsed time."""
    elapsed_str = f"[dim]({elapsed_s:.1f}s)[/dim]" if elapsed_s > 0 else ""
    console.print(
        f" {_STATUS_SYMBOLS[status]} [bold]{policy.upper()}[/bold] {elapsed_str}"
    )


def print_checkpoint_status(found: bool, ckpt_path: Path) -> None:
    """Print whether a FL checkpoint was found or needs training."""
    if found:
        console.print(f" [green]✓ checkpoint found[/green] [dim]{ckpt_path}[/dim]")
    else:
        console.print(
            f" [yellow]○ no checkpoint — will train[/yellow] [dim]{ckpt_path}[/dim]"
        )


def print_sweep_summary(result: SweepResult, elapsed_s: float) -> None:
    """Print a summary table of sweep totals, completed, skipped, and failed cells."""
    table = Table(title="Sweep Summary", border_style="green")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Total", str(result.total))
    table.add_row("Completed", f"[green]{result.completed}[/green]")
    table.add_row("Skipped", f"[dim]{result.skipped}[/dim]")
    failed_style = "red" if result.failed > 0 else ""
    table.add_row(
        "Failed",
        f"[{failed_style}]{result.failed}[/{failed_style}]"
        if failed_style
        else str(result.failed),
    )
    table.add_row("Duration", f"{elapsed_s:.1f}s")
    console.print(table)
