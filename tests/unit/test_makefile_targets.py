from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _makefile_text() -> str:
    return (ROOT / "Makefile").read_text(encoding="utf-8")


def _command_reference_text() -> str:
    return (ROOT / "COMMANDS.md").read_text(encoding="utf-8")


def _registered_root_commands() -> set[str]:
    cli_text = (ROOT / "src/datp/app/cli/__init__.py").read_text(encoding="utf-8")
    typer_groups = set(re.findall(r"add_typer\([^,\n]+,\s*name=\"([^\"]+)\"", cli_text))
    direct_commands = set(re.findall(r"app\.command\(\"([^\"]+)\"\)", cli_text))
    return typer_groups | direct_commands


def _make_targets() -> set[str]:
    return set(
        re.findall(r"^([A-Za-z0-9_.-]+):(?:\s|$)", _makefile_text(), re.MULTILINE)
    )


def test_command_reference_make_targets_exist() -> None:
    documented = set(
        re.findall(r"\bmake\s+([A-Za-z0-9_.-]+)", _command_reference_text())
    )
    targets = _make_targets()
    assert documented - targets == set()


def test_makefile_datp_commands_are_registered() -> None:
    makefile_commands = set(
        re.findall(r"\$\(DATP\)\s+([A-Za-z0-9_.-]+)", _makefile_text())
    )
    assert makefile_commands - _registered_root_commands() == set()


def test_removed_diagnostic_cli_targets_do_not_return() -> None:
    makefile = _makefile_text()
    assert "$(DATP) diagnostic" not in makefile
    assert "diagnostic-regime-" not in makefile
