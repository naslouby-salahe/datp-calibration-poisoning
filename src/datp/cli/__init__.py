"""CLI entry point: Typer app assembly, callback, and runner."""

from pathlib import Path

import typer
from typer.testing import CliRunner

from datp.cli.audit import app as audit_app
from datp.cli.checkpoint_protocol import app as checkpoint_protocol_app
from datp.cli.commands import status, sweep
from datp.cli.config import app as config_app
from datp.cli.enums import CliExitCode
from datp.cli.poison import app as poison_app
from datp.cli.report import app as report_app
from datp.core.logging import configure_logging

app = typer.Typer(
    name="datp",
    invoke_without_command=True,
)

app.add_typer(audit_app, name="audit")
app.add_typer(checkpoint_protocol_app, name="checkpoint-protocol")
app.add_typer(config_app, name="config")
app.add_typer(poison_app, name="poison")
app.add_typer(report_app, name="report")

app.command("status")(status)
app.command("sweep")(sweep)


@app.callback()
def _main_callback(ctx: typer.Context) -> None:
    """Print help when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=CliExitCode.ERROR.value)


def main(argv: list[str] | None = None) -> int:
    """Invoke the CLI app with the given args and return the exit code."""
    return CliRunner().invoke(app, argv).exit_code


def cli_entry() -> None:
    """Configure logging and run the CLI app."""
    from datp.artifacts.names import ArtifactDir
    from datp.config.compose import BASE_CONFIG

    configure_logging(
        BASE_CONFIG.logging,
        log_dir=Path.cwd() / ArtifactDir.OUTPUTS / ArtifactDir.LOGS,
    )
    app()
