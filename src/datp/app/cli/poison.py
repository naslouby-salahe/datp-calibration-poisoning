"""CP2 CLI subcommands — stage preview, dry-run, and smoke gate.

No experiment execution. Heavy stages require explicit gate authorization
and are blocked until CP2-T056. All commands are read-only previews in
Phase B.
"""

from __future__ import annotations

import dataclasses
import json

import typer
from rich.console import Console

from datp.config.stages import Cp2Stage, Cp2StageConfig, all_stage_configs, get_stage_config

app = typer.Typer(help="CP2 calibration-channel poisoning commands.")

_stdout = Console()
_stderr = Console(stderr=True)

_PHASE_B_NOTICE = (
    "NOTE: Experiment execution is blocked until CP2-T056 authorization. "
    "This command is preview/dry-run only."
)


def _stage_config_as_dict(cfg: Cp2StageConfig) -> dict[str, object]:
    d = dataclasses.asdict(cfg)
    # Convert enum values to their string representations.
    d["stage"] = str(cfg.stage)
    d["scale"] = str(cfg.scale) if cfg.scale is not None else None
    return d


@app.command("preview")
def preview(
    stage: Cp2Stage = typer.Option(
        Cp2Stage.NBAIOT_MVP, help="CP2 stage to preview"
    ),
) -> None:
    """Print the stage configuration as JSON; does not execute any run."""
    cfg = get_stage_config(stage)
    _stdout.print_json(json.dumps(_stage_config_as_dict(cfg), indent=2))
    if cfg.gate:
        _stderr.print(
            f"[yellow]Gate required:[/yellow] {cfg.gate!r} must be resolved "
            "before this stage can run."
        )


@app.command("dry-run")
def dry_run(
    stage: Cp2Stage = typer.Option(
        Cp2Stage.NBAIOT_MVP, help="CP2 stage to enumerate"
    ),
) -> None:
    """Enumerate CP2 cells for the stage without executing any experiment."""
    cfg = get_stage_config(stage)
    _stdout.print(f"[bold]CP2 dry-run[/bold]: stage={stage!r}")
    _stdout.print(f"  scale     : {cfg.scale}")
    _stdout.print(f"  dataset   : {cfg.dataset}")
    _stdout.print(f"  allow_run : {cfg.allow_run}")
    _stdout.print(f"  gate      : {cfg.gate or 'none'}")
    _stdout.print(f"  description: {cfg.description}")
    if not cfg.allow_run:
        _stderr.print(f"[yellow]{_PHASE_B_NOTICE}[/yellow]")
    if cfg.gate:
        _stderr.print(
            f"[yellow]Gate[/yellow] {cfg.gate!r} must be resolved before execution."
        )


@app.command("smoke")
def smoke() -> None:
    """Show the CP2 smoke stage config; no experiment is launched in Phase B."""
    cfg = get_stage_config(Cp2Stage.NBAIOT_SMOKE)
    _stdout.print(f"[bold]CP2 smoke stage[/bold]: {cfg.description}")
    _stdout.print(f"  scale  : {cfg.scale}")
    _stdout.print(f"  dataset: {cfg.dataset}")
    _stderr.print(f"[yellow]{_PHASE_B_NOTICE}[/yellow]")


@app.command("stages")
def stages() -> None:
    """List all CP2 stages with their gate and allow_run status."""
    all_cfgs = all_stage_configs()
    for cfg in all_cfgs:
        gate_label = f"gate={cfg.gate!r}" if cfg.gate else "no gate"
        run_label = "BLOCKED" if not cfg.allow_run else "RUNNABLE"
        _stdout.print(
            f"  {str(cfg.stage):<22}  scale={str(cfg.scale) if cfg.scale else 'N/A':<8}"
            f"  {run_label:<8}  {gate_label}"
        )
