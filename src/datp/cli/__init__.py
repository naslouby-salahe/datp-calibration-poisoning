from pathlib import Path
import sys

import typer

from datp.cli.audit import app as audit_app
from datp.cli.checkpoint_protocol import app as checkpoint_protocol_app
from datp.cli.commands import status, sweep
from datp.cli.config import app as config_app
from datp.cli.enums import CliCommand, CliExitCode
from datp.cli.poison import app as poison_app
from datp.cli.report import app as report_app
from datp.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


def _main_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=CliExitCode.ERROR)


app = typer.Typer(
    name="datp",
    invoke_without_command=True,
    callback=_main_callback,
)

app.add_typer(audit_app, name="audit")
app.add_typer(checkpoint_protocol_app, name="checkpoint-protocol")
app.add_typer(config_app, name="config")
app.add_typer(poison_app, name="poison")
app.add_typer(report_app, name="report")

app.command("status")(status)
app.command("sweep")(sweep)


def cli_entry() -> None:
    """Configure logging and run the CLI app."""
    from datp.artifacts.names import ArtifactDir
    from datp.config.compose import BASE_CONFIG

    configure_logging(
        BASE_CONFIG.logging,
        log_dir=Path.cwd() / ArtifactDir.OUTPUTS / ArtifactDir.LOGS,
    )
    command = CliCommand.resolve(sys.argv[1:])
    logger.info("CLI invocation started", command=command)
    try:
        app()
    except SystemExit as exc:
        if exc.code is None or exc.code == CliExitCode.SUCCESS:
            logger.info("CLI invocation completed", command=command)
        else:
            logger.error(
                "CLI invocation failed",
                command=command,
                outcome=CliExitCode.ERROR,
            )
        raise
    except Exception:
        logger.exception("CLI invocation failed", command=command)
        raise
    logger.info("CLI invocation completed", command=command)
