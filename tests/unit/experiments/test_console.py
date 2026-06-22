"""Tests for datp.experiments.console — Rich console output helpers."""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from pathlib import Path
from unittest.mock import patch

from datp.config.stages import ExperimentStage
from datp.experiments.console import (
    _STATUS_SYMBOLS,
    _SWEEP_STEP_LABELS,
    _Label,
    _Message,
    _Style,
    _Symbol,
    _Title,
    console,
    print_checkpoint_status,
    print_dry_run_summary,
    print_group_header,
    print_policy_result,
    print_step,
    print_sweep_banner,
    print_sweep_summary,
)
from datp.experiments.enums import PolicyRunStatus, SweepStep

_STAGE = ExperimentStage.NBAIOT_MAIN


# ── label coverage ────────────────────────────────────────────────────────


def test_sweep_step_labels_cover_all_enum_values() -> None:
    for step in SweepStep:
        assert step in _SWEEP_STEP_LABELS, f"missing label for {step}"
        assert isinstance(_SWEEP_STEP_LABELS[step], str)


def test_status_symbols_cover_all_enum_values() -> None:
    for status in PolicyRunStatus:
        assert status in _STATUS_SYMBOLS, f"missing symbol for {status}"
        assert isinstance(_STATUS_SYMBOLS[status], str)


def test_display_enums_are_non_empty() -> None:
    for cls in (_Symbol, _Label, _Title, _Message, _Style):
        members = list(cls)
        assert len(members) > 0, f"{cls.__name__} has no members"
        for m in members:
            assert isinstance(m.value, str)
            assert len(m.value) > 0, f"{cls.__name__}.{m.name} has empty value"


# ── print_policy_result ────────────────────────────────────────────────────


def test_print_policy_result_done() -> None:
    with patch.object(console, "print") as mock_print:
        print_policy_result(ThresholdPolicy.GLOBAL_THRESHOLD, PolicyRunStatus.DONE, 1.5)
    assert mock_print.called


def test_print_policy_result_skipped() -> None:
    with patch.object(console, "print") as mock_print:
        print_policy_result(
            ThresholdPolicy.LOCAL_THRESHOLD, PolicyRunStatus.SKIPPED, 0.0
        )
    assert mock_print.called


def test_print_policy_result_failed() -> None:
    with patch.object(console, "print") as mock_print:
        print_policy_result(
            ThresholdPolicy.GLOBAL_THRESHOLD, PolicyRunStatus.FAILED, 0.0
        )
    assert mock_print.called


# ── print_sweep_banner ────────────────────────────────────────────────────


def test_print_sweep_banner(tmp_path: Path) -> None:
    with patch.object(console, "print") as mock_print:
        print_sweep_banner(10, str(tmp_path / "base"))
    assert mock_print.called


# ── print_dry_run_summary ─────────────────────────────────────────────────


def test_print_dry_run_summary() -> None:
    with patch.object(console, "print") as mock_print:
        print_dry_run_summary(15)
    assert mock_print.call_count >= 1


# ── print_step ────────────────────────────────────────────────────────────


def test_print_step_with_detail() -> None:
    with patch.object(console, "print") as mock_print:
        print_step(SweepStep.BUILD_MATRIX, "some detail")
    assert mock_print.called


def test_print_step_empty_detail() -> None:
    with patch.object(console, "print") as mock_print:
        print_step(SweepStep.EVALUATE, "")
    assert mock_print.called


# ── print_group_header ────────────────────────────────────────────────────


def test_print_group_header() -> None:
    with patch.object(console, "print") as mock_print:
        print_group_header(_STAGE, 42, 5, 1, 10)
    assert mock_print.called


# ── print_checkpoint_status ───────────────────────────────────────────────


def test_print_checkpoint_status_found(tmp_path: Path) -> None:
    with patch.object(console, "print") as mock_print:
        print_checkpoint_status(True, tmp_path / "ckpt/model.pt")
    assert mock_print.called


def test_print_checkpoint_status_not_found(tmp_path: Path) -> None:
    with patch.object(console, "print") as mock_print:
        print_checkpoint_status(False, tmp_path / "ckpt/model.pt")
    assert mock_print.called


# ── print_sweep_summary ───────────────────────────────────────────────────


def test_print_sweep_summary_no_failures() -> None:
    from datp.experiments.sweep import SweepResult

    result = SweepResult(total=10, completed=8, skipped=2, failed=0)
    with patch.object(console, "print") as mock_print:
        print_sweep_summary(result, 42.0)
    assert mock_print.called


def test_print_sweep_summary_with_failures() -> None:
    from datp.experiments.sweep import SweepResult

    result = SweepResult(total=10, completed=5, skipped=2, failed=3)
    with patch.object(console, "print") as mock_print:
        print_sweep_summary(result, 99.0)
    assert mock_print.called
