from pathlib import Path

import typer

from datp.core.logging import configure_logging

app = typer.Typer(
    name="datp",
    help="DATP: Device-Aware Threshold Personalization CLI",
    invoke_without_command=True,
)


@app.callback()
def _main_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=1)


from datp.app.cli.audit import app as audit_app  # noqa: E402
from datp.app.cli.checkpoint_protocol import app as checkpoint_protocol_app  # noqa: E402
from datp.app.cli.config import app as config_app  # noqa: E402
from datp.app.cli.poison import app as cp2_app  # noqa: E402
from datp.app.cli.report import app as report_app  # noqa: E402

app.add_typer(audit_app, name="audit")
app.add_typer(checkpoint_protocol_app, name="checkpoint-protocol")
app.add_typer(config_app, name="config")
app.add_typer(cp2_app, name="cp2")
app.add_typer(report_app, name="report")

from datp.app.cli.status import status  # noqa: E402
from datp.app.cli.sweep import sweep  # noqa: E402

app.command("status")(status)
app.command("sweep")(sweep)


def main(argv: list[str] | None = None) -> int:
    """Programmatic entry point (for testing). Returns exit code."""
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(app, argv)
    return result.exit_code


def cli_entry() -> None:  # pragma: no cover
    """Console-script entry point (calls sys.exit)."""
    from datp.artifacts.names import ArtifactDir
    from datp.config.compose import BASE_CONFIG

    configure_logging(
        BASE_CONFIG.logging,
        log_dir=Path.cwd() / ArtifactDir.OUTPUTS / ArtifactDir.LOGS,
    )
    app()
