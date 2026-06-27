"""Poisoning CLI: preview, dry-run, smoke, run, and stage listing."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import typer
from rich.console import Console

from datp.attacks.constants import NBAIOT_MAIN_SOURCE_OBJECTIVE_PAIRS
from datp.attacks.execution.bounded_sweep_run import write_nbaiot_main_manifest
from datp.cli.enums import (
    _EXECUTION_GATE_NOTICE,
    CliExitCode,
    PoisonCommand,
    PoisonOutputKey,
)
from datp.config.attack_config import CalibrationPoisoningConfig
from datp.config.models import (
    ExperimentStage,
    ExperimentStageConfig,
    all_stage_configs,
    get_stage_config,
)

app = typer.Typer()
_stdout = Console()
_stderr = Console(stderr=True)


def _stage_config_as_dict(cfg: ExperimentStageConfig) -> dict[str, object]:
    """Serialize an ExperimentStageConfig to a dict with stage and dataset keys."""
    return {
        **dataclasses.asdict(cfg),
        PoisonOutputKey.STAGE.value: str(cfg.stage),
        PoisonOutputKey.DATASET.value: cfg.dataset.value if cfg.dataset else None,
    }


@app.command(PoisonCommand.PREVIEW.value)
def preview(stage: ExperimentStage = typer.Option(ExperimentStage.NBAIOT_MAIN)) -> None:
    """Print the poisoning stage configuration and gate status."""
    cfg = get_stage_config(stage)
    _stdout.print_json(json.dumps(_stage_config_as_dict(cfg), indent=2))

    if cfg.gate and not cfg.allow_run:
        _stderr.print(
            f"[yellow]Gate required:[/yellow] {cfg.gate!r} must be resolved before this stage can run."
        )


@app.command(PoisonCommand.DRY_RUN.value)
def dry_run(stage: ExperimentStage = typer.Option(ExperimentStage.NBAIOT_MAIN)) -> None:
    """Print a detailed dry-run summary for a poisoning stage."""
    cfg = get_stage_config(stage)

    _stdout.print(f"[bold]dry-run[/bold]: stage={stage!r}")
    _stdout.print(
        f" {PoisonOutputKey.DATASET.value}     : {cfg.dataset.value if cfg.dataset else 'none'}"
    )
    _stdout.print(f" {PoisonOutputKey.ALLOW_RUN.value}   : {cfg.allow_run}")
    _stdout.print(f" {PoisonOutputKey.GATE.value}        : {cfg.gate or 'none'}")
    _stdout.print(f" {PoisonOutputKey.DESCRIPTION.value} : {cfg.description}")

    if stage == ExperimentStage.NBAIOT_MAIN:
        config = CalibrationPoisoningConfig.for_bounded_sweep()
        cells_per_victim = (
            len(config.policies)
            * len(NBAIOT_MAIN_SOURCE_OBJECTIVE_PAIRS)
            * len(config.fractions)
            * len(config.seeds)
        )

        _stdout.print(f" config_policies  : {[p.value for p in config.policies]}")
        _stdout.print(f" config_sources   : {[s.value for s in config.sources]}")
        _stdout.print(f" config_objectives: {[o.value for o in config.objectives]}")
        _stdout.print(f" config_fractions : {list(config.fractions)}")
        _stdout.print(f" config_seeds     : {len(config.seeds)} seed triplets")
        _stdout.print(f" cells/victim     : {cells_per_victim}")
        _stdout.print(
            " [dim]source/objective pairs: RANDOM_BENIGN+THRESHOLD_RAISE, RANDOM_BENIGN+THRESHOLD_LOWER, "
            "HIGH_SCORE_BENIGN+THRESHOLD_RAISE, LOW_SCORE_BENIGN+THRESHOLD_LOWER[/dim]"
        )

    if not cfg.allow_run:
        _stderr.print(f"[yellow]{_EXECUTION_GATE_NOTICE}[/yellow]")
        if cfg.gate:
            _stderr.print(
                f"[yellow]Gate[/yellow] {cfg.gate!r} must be resolved before execution."
            )


@app.command(PoisonCommand.SMOKE.value)
def smoke() -> None:
    """Print the synthetic smoke stage description."""
    cfg = get_stage_config(ExperimentStage.SYNTHETIC_SMOKE)
    _stdout.print(f"[bold]smoke stage[/bold]: {cfg.description}")
    _stdout.print(
        f" {PoisonOutputKey.DATASET.value}: {cfg.dataset.value if cfg.dataset else 'none'}"
    )
    _stderr.print(f"[yellow]{_EXECUTION_GATE_NOTICE}[/yellow]")


@app.command(PoisonCommand.RUN_BOUNDED_SWEEP.value)
def run_bounded_sweep(base_dir: Path = typer.Option(...)) -> None:
    """Execute the bounded sweep and write its manifest."""
    cfg = get_stage_config(ExperimentStage.NBAIOT_MAIN)

    if not cfg.allow_run:
        _stderr.print(
            f"[red]Refusing to run:[/red] {ExperimentStage.NBAIOT_MAIN!r} allow_run is False (gate {cfg.gate!r} not satisfied)."
        )
        raise typer.Exit(code=CliExitCode.ERROR.value)

    out_path = write_nbaiot_main_manifest(base_dir)
    _stdout.print(f"[bold green]Wrote bounded-sweep manifest:[/bold green] {out_path}")


@app.command(PoisonCommand.STAGES.value)
def stages() -> None:
    """List all experiment stages with their gate and run status."""
    for cfg in all_stage_configs():
        gate_label = f"gate={cfg.gate!r}" if cfg.gate else "no gate"
        run_label = "BLOCKED" if not cfg.allow_run else "RUNNABLE"
        _stdout.print(f" {str(cfg.stage):<30} {run_label:<8} {gate_label}")
