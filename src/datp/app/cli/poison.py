"""Calibration-poisoning CLI commands.

Preview commands are read-only. Execution commands refuse to run unless the
selected stage has its own gate authorized in the stage registry.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import typer
from rich.console import Console

from datp.attacks.bounded_sweep_run import write_nbaiot_bounded_sweep_manifest
from datp.config.stages import (
    ExperimentStage,
    ExperimentStageConfig,
    all_stage_configs,
    get_stage_config,
)

app = typer.Typer(help="Calibration-channel poisoning commands.")

_stdout = Console()
_stderr = Console(stderr=True)

_EXECUTION_GATE_NOTICE = (
    "NOTE: Experiment execution is blocked until this stage's own gate "
    "(see below) is authorized. This command is preview/dry-run only."
)


def _stage_config_as_dict(cfg: ExperimentStageConfig) -> dict[str, object]:
    d = dataclasses.asdict(cfg)
    # Convert enum values to their string representations.
    d["stage"] = str(cfg.stage)
    d["scale"] = str(cfg.scale) if cfg.scale is not None else None
    d["dataset"] = cfg.dataset.value if cfg.dataset is not None else None
    return d


@app.command("preview")
def preview(
    stage: ExperimentStage = typer.Option(
        ExperimentStage.NBAIOT_BOUNDED, help="stage to preview"
    ),
) -> None:
    """Print the stage configuration as JSON; does not execute any run."""
    cfg = get_stage_config(stage)
    _stdout.print_json(json.dumps(_stage_config_as_dict(cfg), indent=2))
    if cfg.gate and not cfg.allow_run:
        _stderr.print(
            f"[yellow]Gate required:[/yellow] {cfg.gate!r} must be resolved "
            "before this stage can run."
        )


@app.command("dry-run")
def dry_run(
    stage: ExperimentStage = typer.Option(
        ExperimentStage.NBAIOT_BOUNDED, help="stage to enumerate"
    ),
) -> None:
    """Enumerate cells for the stage without executing any experiment."""
    cfg = get_stage_config(stage)
    _stdout.print(f"[bold]dry-run[/bold]: stage={stage!r}")
    _stdout.print(f" scale : {cfg.scale}")
    _stdout.print(f" dataset : {cfg.dataset.value if cfg.dataset else 'none'}")
    _stdout.print(f" allow_run : {cfg.allow_run}")
    _stdout.print(f" gate : {cfg.gate or 'none'}")
    _stdout.print(f" description: {cfg.description}")
    if not cfg.allow_run:
        _stderr.print(f"[yellow]{_EXECUTION_GATE_NOTICE}[/yellow]")
        if cfg.gate:
            _stderr.print(
                f"[yellow]Gate[/yellow] {cfg.gate!r} must be resolved before execution."
            )


@app.command("smoke")
def smoke() -> None:
    """Show the smoke stage config; no experiment is launched."""
    cfg = get_stage_config(ExperimentStage.NBAIOT_SMOKE)
    _stdout.print(f"[bold]smoke stage[/bold]: {cfg.description}")
    _stdout.print(f" scale : {cfg.scale}")
    _stdout.print(f" dataset: {cfg.dataset.value if cfg.dataset else 'none'}")
    _stderr.print(f"[yellow]{_EXECUTION_GATE_NOTICE}[/yellow]")


@app.command("run-bounded-sweep")
def run_bounded_sweep(
    base_dir: Path = typer.Option(
        ..., help="Root output directory (contains real N-BaIoT score artifacts)"
    ),
) -> None:
    """Execute the locked bounded N-BaIoT matrix and write its manifest.

    This is the single CLI run path for ``ExperimentStage.NBAIOT_BOUNDED``: it refuses
    to run unless that stage's ``allow_run`` is True (bounded-run gate
    satisfied), and it only ever produces ``nbaiot_bounded_sweep_manifest.json`` —
    nothing outside the locked 1620-cell matrix.
    """
    cfg = get_stage_config(ExperimentStage.NBAIOT_BOUNDED)
    if not cfg.allow_run:
        _stderr.print(
            f"[red]Refusing to run:[/red] {ExperimentStage.NBAIOT_BOUNDED!r} allow_run is "
            f"False (gate {cfg.gate!r} not satisfied)."
        )
        raise typer.Exit(code=1)
    out_path = write_nbaiot_bounded_sweep_manifest(base_dir)
    _stdout.print(f"[bold green]Wrote bounded-sweep manifest:[/bold green] {out_path}")


@app.command("stages")
def stages() -> None:
    """List all stages with their gate and allow_run status."""
    all_cfgs = all_stage_configs()
    for cfg in all_cfgs:
        gate_label = f"gate={cfg.gate!r}" if cfg.gate else "no gate"
        run_label = "BLOCKED" if not cfg.allow_run else "RUNNABLE"
        _stdout.print(
            f" {str(cfg.stage):<22} scale={str(cfg.scale) if cfg.scale else 'N/A':<8}"
            f" {run_label:<8} {gate_label}"
        )
