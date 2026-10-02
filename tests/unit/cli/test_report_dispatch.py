import pytest

from datp.cli import report
from datp.cli.enums import ReportCommand


@pytest.mark.parametrize(
    ("command", "expected_calls"),
    (
        (ReportCommand.STATS, ("stats",)),
        (ReportCommand.VALIDATE, ("validate",)),
        (ReportCommand.FIGURES, ("figures",)),
        (ReportCommand.TABLES, ("tables",)),
        (ReportCommand.ALL, ("all",)),
        (ReportCommand.POISONING, ("poisoning", "poisoning_figures")),
        (ReportCommand.SENSITIVITY, ("sensitivity",)),
    ),
)
def test_report_command_dispatches_to_its_workflow(
    command: ReportCommand,
    expected_calls: tuple[str, ...],
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def build(name: str):
        def run(*args, **kwargs) -> tuple[()]:
            calls.append(name)
            return ()

        return run

    monkeypatch.setattr(report, "build_stats", build("stats"))
    monkeypatch.setattr(report, "validate_results", build("validate"))
    monkeypatch.setattr(report, "build_figures", build("figures"))
    monkeypatch.setattr(report, "build_tables", build("tables"))
    monkeypatch.setattr(report, "build_all", build("all"))

    def poisoning(*args, **kwargs) -> tuple[()]:
        calls.append("poisoning")
        return ()

    monkeypatch.setattr(report, "build_poisoning_summaries", poisoning)
    monkeypatch.setattr(report, "build_poisoning_figures", build("poisoning_figures"))
    monkeypatch.setattr(report, "build_sensitivity_summaries", build("sensitivity"))

    report._run_report_step(command, tmp_path)

    assert tuple(calls) == expected_calls
