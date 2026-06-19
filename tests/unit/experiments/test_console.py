"""Tests for datp.experiments.console — Rich console output helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from datp.core.enums import Baseline, BaselineRunStatus, Regime
from datp.experiments.console import (
    _DIAGNOSTIC_STEP_LABELS,
    _STATUS_SYMBOLS,
    _SWEEP_STEP_LABELS,
    _Label,
    _Message,
    _Style,
    _Symbol,
    _Title,
    console,
    print_banner,
    print_baseline_result,
    print_checkpoint_status,
    print_dry_run_summary,
    print_group_header,
    print_step,
    print_summary,
    print_sweep_banner,
    print_sweep_summary,
    step_context,
)
from datp.experiments.enums import ContingencyDecision, DiagnosticStep, SweepStep

# ── label coverage ────────────────────────────────────────────────────────


def test_diagnostic_step_labels_cover_all_enum_values() -> None:
    for step in DiagnosticStep:
        assert step in _DIAGNOSTIC_STEP_LABELS, f"missing label for {step}"
        assert isinstance(_DIAGNOSTIC_STEP_LABELS[step], str)


def test_sweep_step_labels_cover_all_enum_values() -> None:
    for step in SweepStep:
        assert step in _SWEEP_STEP_LABELS, f"missing label for {step}"
        assert isinstance(_SWEEP_STEP_LABELS[step], str)


def test_status_symbols_cover_all_enum_values() -> None:
    for status in BaselineRunStatus:
        assert status in _STATUS_SYMBOLS, f"missing symbol for {status}"
        assert isinstance(_STATUS_SYMBOLS[status], str)


def test_display_enums_are_non_empty() -> None:
    for cls in (_Symbol, _Label, _Title, _Message, _Style):
        members = list(cls)
        assert len(members) > 0, f"{cls.__name__} has no members"
        for m in members:
            assert isinstance(m.value, str)
            assert len(m.value) > 0, f"{cls.__name__}.{m.name} has empty value"


# ── print_banner ──────────────────────────────────────────────────────────


def test_print_banner_basic(tmp_path: Path) -> None:
    with patch.object(console, "print") as mock_print:
        print_banner(Regime.A, 42, str(tmp_path / "out"))
    assert mock_print.called


def test_print_banner_with_alpha(tmp_path: Path) -> None:
    with patch.object(console, "print") as mock_print:
        print_banner(Regime.C, 7, str(tmp_path / "out"), alpha=0.5)
    assert mock_print.called


# ── print_summary ─────────────────────────────────────────────────────────


def test_print_summary_basic(tmp_path: Path) -> None:
    with patch.object(console, "print") as mock_print:
        print_summary(Regime.A, 1, 0.1, 0.05, (8, 10), str(tmp_path / "out"), 12.3)
    assert mock_print.called


def test_print_summary_with_contingency(tmp_path: Path) -> None:
    with patch.object(console, "print") as mock_print:
        print_summary(
            Regime.A, 1, 0.1, 0.05, (8, 10), str(tmp_path / "out"), 12.3, contingency=ContingencyDecision.GO
        )
    assert mock_print.called


def test_print_summary_with_alpha(tmp_path: Path) -> None:
    with patch.object(console, "print") as mock_print:
        print_summary(Regime.C, 1, 0.1, 0.05, (8, 10), str(tmp_path / "out"), 12.3, alpha=0.5)
    assert mock_print.called


# ── step_context ──────────────────────────────────────────────────────────


def test_step_context_success() -> None:
    with patch.object(console, "print") as mock_print:
        with step_context(DiagnosticStep.SET_SEEDS):
            assert mock_print.called
    assert mock_print.call_count >= 2


def test_step_context_failure_reraises() -> None:
    import pytest

    with pytest.raises(ValueError, match="test error"):
        with step_context(DiagnosticStep.FL_TRAINING):
            raise ValueError("test error")


# ── print_baseline_result ─────────────────────────────────────────────────


def test_print_baseline_result_done() -> None:
    with patch.object(console, "print") as mock_print:
        print_baseline_result(Baseline.B1, BaselineRunStatus.DONE, 1.5)
    assert mock_print.called


def test_print_baseline_result_skipped() -> None:
    with patch.object(console, "print") as mock_print:
        print_baseline_result(Baseline.B2, BaselineRunStatus.SKIPPED, 0.0)
    assert mock_print.called


def test_print_baseline_result_failed() -> None:
    with patch.object(console, "print") as mock_print:
        print_baseline_result(Baseline.B0, BaselineRunStatus.FAILED, 0.0)
    assert mock_print.called


# ── print_sweep_banner ────────────────────────────────────────────────────


def test_print_sweep_banner_all_regimes(tmp_path: Path) -> None:
    with patch.object(console, "print") as mock_print:
        print_sweep_banner(None, 10, str(tmp_path / "base"))
    assert mock_print.called


def test_print_sweep_banner_specific_regime(tmp_path: Path) -> None:
    with patch.object(console, "print") as mock_print:
        print_sweep_banner(Regime.A, 5, str(tmp_path / "base"))
    assert mock_print.called


# ── print_dry_run_summary ─────────────────────────────────────────────────


def test_print_dry_run_summary() -> None:
    with patch.object(console, "print") as mock_print:
        print_dry_run_summary({Regime.A: 3, Regime.B: 2}, 5)
    assert mock_print.call_count >= 2


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
        print_group_header(Regime.A, 42, None, 5, 1, 10)
    assert mock_print.called


def test_print_group_header_with_alpha() -> None:
    with patch.object(console, "print") as mock_print:
        print_group_header(Regime.C, 7, 0.5, 3, 2, 5)
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
