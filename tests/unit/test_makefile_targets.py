"""Tests verifying that CLI subcommands executed in the Makefile are properly registered and not deprecated."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _makefile_text() -> str:
    """Helper to read the top-level project Makefile content."""
    return (ROOT / "Makefile").read_text()


def _registered_root_commands() -> set[str]:
    """Helper to extract registered subcommand names from CLI entrypoints."""
    cli_text = (ROOT / "src/datp/cli/__init__.py").read_text()
    typer_groups = set(re.findall(r"add_typer\([^,\n]+,\s*name=\"([^\"]+)\"", cli_text))
    direct_commands = set(re.findall(r"app\.command\(\"([^\"]+)\"\)", cli_text))
    return typer_groups | direct_commands


def test_makefile_cli_commands_are_registered() -> None:
    """Verify that all DATP_CLI commands invoked in the Makefile are actually registered subcommands."""
    makefile_commands = set(
        re.findall(r"\$\(DATP_CLI\)\s+([A-Za-z0-9_.-]+)", _makefile_text())
    )
    assert makefile_commands - _registered_root_commands() == set()


def test_removed_diagnostic_cli_targets_do_not_return() -> None:
    """Verify that legacy diagnostics CLI targets remain removed from the Makefile."""
    makefile = _makefile_text()
    assert "$(DATP_CLI) diagnostic" not in makefile
    assert "diagnostic-regime-" not in makefile
