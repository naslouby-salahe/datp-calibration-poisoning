
from pathlib import Path

import typer
from rich.console import Console

from datp.cli.enums import CliExitCode, ReportCommand
from datp.config.compose import BASE_CONFIG
from datp.reporting.build import (
    build_all,
    build_figures,
    build_poisoning_figures,
    build_stats,
    build_tables,
    validate_results,
)
from datp.reporting.poisoning import (
    build_poisoning_summaries,
    build_sensitivity_summaries,
)
from datp.core.logging import get_logger

app = typer.Typer()
console = Console()
logger = get_logger(__name__)


def _run_report_step(
    command: ReportCommand, base_dir: Path
) -> None:
    logger.info(
        "report command started",
        command=command,
        base_dir=base_dir.as_posix(),
    )
    try:
        output_paths: tuple[Path, ...]
        match command:
            case ReportCommand.STATS:
                output_paths = build_stats(base_dir, BASE_CONFIG)
            case ReportCommand.VALIDATE:
                output_paths = validate_results(base_dir, BASE_CONFIG)
            case ReportCommand.FIGURES:
                output_paths = build_figures(base_dir, BASE_CONFIG)
            case ReportCommand.TABLES:
                output_paths = build_tables(base_dir, BASE_CONFIG)
            case ReportCommand.ALL:
                output_paths = build_all(base_dir, BASE_CONFIG)
            case ReportCommand.POISONING:
                poisoning = build_poisoning_summaries(base_dir)
                figures = build_poisoning_figures(base_dir, BASE_CONFIG)
                output_paths = (*poisoning, *figures)
            case ReportCommand.SENSITIVITY:
                output_paths = build_sensitivity_summaries(base_dir)
            case _:
                raise ValueError(f"Unsupported report command: {command}")
        for path in output_paths:
            console.print(f"[green]wrote[/green] {path}")
    except (FileNotFoundError, ValueError) as exc:
        logger.exception(
            "report command failed",
            command=command,
            base_dir=base_dir.as_posix(),
        )
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=CliExitCode.ERROR) from exc
    logger.info(
        "report command completed",
        command=command,
        output_count=len(output_paths),
    )


@app.command(ReportCommand.STATS)
def stats(base_dir: Path = typer.Option(...)) -> None:
    """Build and write statistical summaries."""
    _run_report_step(ReportCommand.STATS, base_dir)


@app.command(ReportCommand.VALIDATE)
def validate(base_dir: Path = typer.Option(...)) -> None:
    """Validate results and write validation artifacts."""
    _run_report_step(ReportCommand.VALIDATE, base_dir)


@app.command(ReportCommand.FIGURES)
def figures(base_dir: Path = typer.Option(...)) -> None:
    """Build and write figures."""
    _run_report_step(ReportCommand.FIGURES, base_dir)


@app.command(ReportCommand.TABLES)
def tables(base_dir: Path = typer.Option(...)) -> None:
    """Build and write tables."""
    _run_report_step(ReportCommand.TABLES, base_dir)


@app.command(ReportCommand.POISONING)
def poisoning(base_dir: Path = typer.Option(...)) -> None:
    """Build and write poisoning summaries."""
    _run_report_step(ReportCommand.POISONING, base_dir)


@app.command(ReportCommand.SENSITIVITY)
def sensitivity(base_dir: Path = typer.Option(...)) -> None:
    """Build and write sensitivity summaries."""
    _run_report_step(ReportCommand.SENSITIVITY, base_dir)


@app.command(ReportCommand.ALL)
def all_outputs(base_dir: Path = typer.Option(...)) -> None:
    """Build and write all report outputs."""
    _run_report_step(ReportCommand.ALL, base_dir)
