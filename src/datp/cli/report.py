"""Report CLI: stats, validation, figures, tables, and poisoning summaries."""

from pathlib import Path
from typing import Callable

import typer
from rich.console import Console

from datp.cli.enums import CliExitCode, ReportCommand
from datp.config.compose import BASE_CONFIG
from datp.config.models import DatpConfig
from datp.reporting.build import (
    BuildOutputs,
    build_all,
    build_figures,
    build_stats,
    build_tables,
    validate_results,
)
from datp.reporting.poisoning import build_poisoning_summaries

app = typer.Typer()
console = Console()


def _run_report_step(
    fn: Callable[[Path, DatpConfig], BuildOutputs], base_dir: Path
) -> None:
    """Run a reporting function and print each output path, exiting on error."""
    try:
        result = fn(base_dir, BASE_CONFIG)
        for path in result.paths:
            console.print(f"[green]wrote[/green] {path}")
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=CliExitCode.ERROR.value) from exc


@app.command(ReportCommand.STATS.value)
def stats(base_dir: Path = typer.Option(...)) -> None:
    """Build and write statistical summaries."""
    _run_report_step(build_stats, base_dir)


@app.command(ReportCommand.VALIDATE.value)
def validate(base_dir: Path = typer.Option(...)) -> None:
    """Validate results and write validation artifacts."""
    _run_report_step(validate_results, base_dir)


@app.command(ReportCommand.FIGURES.value)
def figures(base_dir: Path = typer.Option(...)) -> None:
    """Build and write figures."""
    _run_report_step(build_figures, base_dir)


@app.command(ReportCommand.TABLES.value)
def tables(base_dir: Path = typer.Option(...)) -> None:
    """Build and write tables."""
    _run_report_step(build_tables, base_dir)


@app.command(ReportCommand.POISONING.value)
def poisoning(base_dir: Path = typer.Option(...)) -> None:
    """Build and write poisoning summaries."""
    try:
        result = build_poisoning_summaries(base_dir)
        for path in result.paths:
            console.print(f"[green]wrote[/green] {path}")
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=CliExitCode.ERROR.value) from exc


@app.command(ReportCommand.ALL.value)
def all_outputs(base_dir: Path = typer.Option(...)) -> None:
    """Build and write all report outputs."""
    _run_report_step(build_all, base_dir)
