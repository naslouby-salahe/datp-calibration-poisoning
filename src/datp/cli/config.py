"""Config CLI: compose and preview resolved configurations."""

from pathlib import Path

import typer
from rich.console import Console

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactDir
from datp.cli.enums import CliExitCode, ConfigCommand
from datp.config.compose import ComposeError, compose_config, write_resolved_config
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.identity import PolicyRunId, TrainingCellId

app = typer.Typer()
_stdout = Console()
_stderr = Console(stderr=True)


def preview_config(
    *,
    stage: ExperimentStage,
    policy: ThresholdPolicy,
    seed: int,
    output_dir: Path | None = None,
) -> Path:
    """Compose and write the resolved config for a stage/policy/seed triplet."""
    cfg = compose_config(stage=stage, policy=policy, seed=seed)
    if not output_dir:
        output_dir = (
            ArtifactLayout(base_dir=Path(ArtifactDir.OUTPUTS), stage=stage)
            .policy_run(
                PolicyRunId(cell=TrainingCellId(stage=stage, seed=seed), policy=policy)
            )
            .result_dir
        )

    return write_resolved_config(cfg, output_dir)


@app.command(ConfigCommand.PREVIEW.value)
def preview(
    stage: ExperimentStage = typer.Option(...),
    policy: ThresholdPolicy = typer.Option(...),
    seed: int = typer.Option(...),
    output_dir: Path | None = typer.Option(None),
) -> None:
    """CLI command to preview a resolved configuration."""
    try:
        dest = preview_config(
            stage=stage, policy=policy, seed=seed, output_dir=output_dir
        )
    except ComposeError as exc:
        _stderr.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=CliExitCode.ERROR.value) from exc

    _stdout.print(dest.read_text(), end="", highlight=False)
    _stderr.print(f"[dim]# Written to: {dest}[/dim]")
