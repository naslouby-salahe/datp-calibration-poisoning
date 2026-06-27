"""Audit CLI: results audit with table output."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from datp.cli.enums import AuditColumn, AuditCommand
from datp.validation.results import run_results_audit

app = typer.Typer()
console = Console()


@app.command(AuditCommand.RESULTS.value)
def results(
    base_dir: Path = typer.Option(...),
    audit_dir: Path | None = typer.Option(None),
    data_root: Path = typer.Option(Path(".")),
) -> None:
    """Run the results audit and print a table of generated artifact paths."""
    from datp.config.compose import BASE_CONFIG
    from datp.validation.enums import AuditDir

    paths = run_results_audit(
        base_dir=base_dir,
        audit_dir=audit_dir or (Path("artifacts") / AuditDir.AUDIT),
        cfg=BASE_CONFIG,
        data_root=data_root,
    )

    table = Table(title="datp-cp Results Audit", border_style="cyan")
    table.add_column(AuditColumn.ARTIFACT.value, style="bold")
    table.add_column(AuditColumn.PATH.value)

    for name, path in paths.items():
        table.add_row(name, str(path))

    console.print(table)
