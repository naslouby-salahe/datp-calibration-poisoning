from pathlib import Path

import typer

from datp.experiments.sweep import run_sweep


def sweep(
    dry_run: bool = typer.Option(
        False, "--dry-run/--no-dry-run", help="Enumerate and validate without launching"
    ),
    base_dir: Path = typer.Option(..., help="Root output directory"),
    data_root: Path = typer.Option(
        Path.cwd(), help="Project data root (where data/raw/ lives)"
    ),
) -> None:
    """Enumerate, validate, and run experiment cells."""
    run_sweep(dry_run=dry_run, base_dir=base_dir, data_root=data_root)
