from __future__ import annotations

import sys
from typing import Any

import pytest

import datp.cli as cli_module
from datp.cli.enums import CliCommand


class _LogRecorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, str, dict[str, Any]]] = []

    def info(self, event: str, **fields: Any) -> None:
        self.events.append(("info", event, fields))

    def error(self, event: str, **fields: Any) -> None:
        self.events.append(("error", event, fields))

    def exception(self, event: str, **fields: Any) -> None:
        self.events.append(("exception", event, fields))


def test_cli_command_resolution_uses_the_registered_command_enum() -> None:
    assert CliCommand.resolve(["report", "stats", "--base-dir", "/private/path"]) is (
        CliCommand.REPORT_STATS
    )
    assert CliCommand.resolve(["--help"]) is None
    assert CliCommand.resolve(["unregistered", "value"]) is None


def test_cli_entry_logs_start_and_success(monkeypatch: pytest.MonkeyPatch) -> None:
    recorder = _LogRecorder()
    monkeypatch.setattr(cli_module, "logger", recorder)
    monkeypatch.setattr(cli_module, "configure_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_module, "app", lambda: None)
    monkeypatch.setattr(sys, "argv", ["datp", "poison", "dry-run"])

    cli_module.cli_entry()

    assert [event for _, event, _ in recorder.events] == [
        "CLI invocation started",
        "CLI invocation completed",
    ]
    assert all(fields["command"] is CliCommand.POISON_DRY_RUN for _, _, fields in recorder.events)


def test_cli_entry_logs_failure_and_preserves_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = _LogRecorder()
    failure = RuntimeError("command failed")
    monkeypatch.setattr(cli_module, "logger", recorder)
    monkeypatch.setattr(cli_module, "configure_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(cli_module, "app", lambda: (_ for _ in ()).throw(failure))
    monkeypatch.setattr(sys, "argv", ["datp", "sweep"])

    with pytest.raises(RuntimeError, match="command failed"):
        cli_module.cli_entry()

    assert [event for _, event, _ in recorder.events] == [
        "CLI invocation started",
        "CLI invocation failed",
    ]
    assert recorder.events[-1][0] == "exception"
