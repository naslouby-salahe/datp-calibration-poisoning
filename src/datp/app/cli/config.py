from datp.attacks.enums import ThresholdPolicy
from pathlib import Path

import typer
from rich.console import Console

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactDir
from datp.config.compose import ComposeError, compose_config, write_resolved_config
from datp.config.stages import ExperimentStage
from datp.core.identity import PolicyRunId, TrainingCellId

app = typer.Typer(help="Configuration commands.")

_stdout = Console()
_stderr = Console(stderr=True)


def _build_output_path(cfg) -> Path:
    run = PolicyRunId(
        cell=TrainingCellId(stage=cfg.stage, seed=cfg.seed),
        policy=cfg.policy,
    )
    return (
        ArtifactLayout(base_dir=Path(ArtifactDir.OUTPUTS), stage=cfg.stage)
        .policy_run(run)
        .result_dir
    )


def preview_config(
    *,
    stage: ExperimentStage,
    policy: ThresholdPolicy,
    seed: int,
    output_dir: Path | None = None,
) -> Path:
    cfg = compose_config(
        stage=stage,
        policy=policy,
        seed=seed,
    )

    if output_dir is None:
        output_dir = _build_output_path(cfg)

    return write_resolved_config(cfg, output_dir)


@app.command("preview")
def preview(
    stage: ExperimentStage = typer.Option(..., help="Experiment stage (nbaiot_main, synthetic_smoke, ...)"),
    policy: ThresholdPolicy = typer.Option(..., help="ThresholdPolicy (global_threshold, local_threshold, cluster_threshold)"),
    seed: int = typer.Option(..., help="Random seed"),
    output_dir: Path | None = typer.Option(None, help="Override output directory"),
) -> None:
    """Write resolved_config.yaml without launching training."""
    try:
        dest = preview_config(
            stage=stage,
            policy=policy,
            seed=seed,
            output_dir=output_dir,
        )
    except ComposeError as exc:
        _stderr.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    _stdout.print(dest.read_text(), end="", highlight=False)
    _stderr.print(f"[dim]# Written to: {dest}[/dim]")
