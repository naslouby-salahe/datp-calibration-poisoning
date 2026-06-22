from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from datp.validation.results import run_results_audit

app = typer.Typer(help="Audit commands.")
console = Console()


@app.command("results")
def results(
    base_dir: Path = typer.Option(..., help="Root output directory"),
    audit_dir: Path | None = typer.Option(None, help="Audit output directory"),
    data_root: Path = typer.Option(
        Path("."), help="Project data root (where data/raw/ and data/processed/ live)"
    ),
) -> None:
    """Run the results audit and write audit artifacts."""
    from datp.config.compose import BASE_CONFIG
    from datp.validation.constants import AUDIT_DIR

    resolved_audit_dir = (
        audit_dir if audit_dir is not None else (Path("artifacts") / AUDIT_DIR)
    )
    paths = run_results_audit(
        base_dir=base_dir,
        audit_dir=resolved_audit_dir,
        cfg=BASE_CONFIG,
        data_root=data_root,
    )
    table = Table(title="datp-cp Results Audit", border_style="cyan")
    table.add_column("Artifact", style="bold")
    table.add_column("Path")
    for name, path in paths.items():
        table.add_row(name, str(path))
    console.print(table)
