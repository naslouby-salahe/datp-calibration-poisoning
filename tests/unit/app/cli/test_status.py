from __future__ import annotations

import re

from datp.app.cli.status import get_status
from datp.artifacts.layout import ArtifactLayout
from datp.core.enums import (
    Baseline,
    Regime,
)
from datp.core.identity import BaselineRunId, TrainingCellId
from tests.fixtures.payloads import valid_metrics_json

_TOTAL_CELLS = 135
_REGIME_A_CELLS = 25
_REGIME_B_CELLS = 20
_REGIME_C_CELLS = 90


class TestAllMissingFreshDir:
    def test_all_missing_fresh_dir(self, tmp_path):
        report = get_status(regime=None, base_dir=tmp_path)
        total_missing = sum(rr.missing_count for rr in report.regime_reports.values())
        total_complete = sum(rr.complete_count for rr in report.regime_reports.values())
        total_aborted = sum(rr.aborted_count for rr in report.regime_reports.values())

        assert total_missing == _TOTAL_CELLS
        assert total_complete == 0
        assert total_aborted == 0


class TestCompleteDetected:
    def test_complete_detected(self, tmp_path):
        run = BaselineRunId(
            cell=TrainingCellId(regime=Regime.A, seed=0, alpha=None),
            baseline=Baseline.B1,
        )
        rp = (
            ArtifactLayout(base_dir=tmp_path, regime=Regime.A)
            .baseline_run(run)
            .result_dir
        )
        rp.mkdir(parents=True, exist_ok=True)
        (rp / "metrics.json").write_text(valid_metrics_json("b1", "a", 0))

        report = get_status(regime=Regime.A, base_dir=tmp_path)
        rr = report.regime_reports[Regime.A]

        assert rr.complete_count == 1
        assert rr.complete[0] == BaselineRunId(
            cell=TrainingCellId(regime=Regime.A, seed=0, alpha=None),
            baseline=Baseline.B1,
        )
        assert rr.missing_count == _REGIME_A_CELLS - 1
        assert rr.aborted_count == 0


class TestAbortedDetected:
    def test_aborted_detected(self, tmp_path):
        run = BaselineRunId(
            cell=TrainingCellId(regime=Regime.B, seed=1, alpha=None),
            baseline=Baseline.B2,
        )
        rp = (
            ArtifactLayout(base_dir=tmp_path, regime=Regime.B)
            .baseline_run(run)
            .result_dir
        )
        rp.mkdir(parents=True, exist_ok=True)
        (rp / "ABORTED.txt").write_text("round=5; OOM error")

        report = get_status(regime=Regime.B, base_dir=tmp_path)
        rr = report.regime_reports[Regime.B]

        assert rr.aborted_count == 1
        assert rr.aborted[0] == BaselineRunId(
            cell=TrainingCellId(regime=Regime.B, seed=1, alpha=None),
            baseline=Baseline.B2,
        )
        assert rr.missing_count == _REGIME_B_CELLS - 1
        assert rr.complete_count == 0


class TestRegimeFilter:
    def test_regime_filter(self, tmp_path):
        report = get_status(regime=Regime.A, base_dir=tmp_path)

        assert list(report.regime_reports.keys()) == [Regime.A]
        rr = report.regime_reports[Regime.A]
        assert rr.total == _REGIME_A_CELLS
        assert all(c.regime == Regime.A for c in rr.missing)


class TestSummaryLinesFormat:
    def test_summary_lines_format(self, tmp_path):
        report = get_status(regime=None, base_dir=tmp_path)
        lines = report.summary_lines()

        assert len(lines) == 4

        pattern = re.compile(
            r"^(Regime [ABC]|Overall):?\s+"
            r"complete=\d+\s+"
            r"missing=\d+\s+"
            r"aborted=\d+\s+"
            r"\(total=\d+\)$"
        )
        for line in lines:
            assert pattern.match(line), f"Line did not match expected format: {line!r}"

        assert f"total={_REGIME_A_CELLS}" in lines[0]
        assert f"total={_REGIME_B_CELLS}" in lines[1]
        assert f"total={_REGIME_C_CELLS}" in lines[2]
        assert f"total={_TOTAL_CELLS}" in lines[3]
