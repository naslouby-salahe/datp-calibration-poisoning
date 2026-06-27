"""Unit tests for the status-reporting logic that counts complete, missing, and aborted runs."""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from datp.cli.commands import get_status
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile
from datp.config.models import ExperimentStage
from datp.core.identity import PolicyRunId, TrainingCellId
from tests.fixtures.payloads import valid_metrics_json

_TOTAL_CELLS = 30
_NBAIOT_MAIN_CELLS = 30


class TestAllMissingFreshDir:
    """All cells are missing when the base directory is empty."""

    """All cells are missing when the base directory is empty."""

    def test_all_missing_fresh_dir(self, tmp_path):
        """Empty base directory reports all cells as missing and none complete or aborted."""
        report = get_status(base_dir=tmp_path)
        total_missing = sum(len(rr.missing) for rr in report.stage_reports.values())
        total_complete = sum(len(rr.complete) for rr in report.stage_reports.values())
        total_aborted = sum(len(rr.aborted) for rr in report.stage_reports.values())

        assert total_missing == _TOTAL_CELLS
        assert total_complete == 0
        assert total_aborted == 0


class TestCompleteDetected:
    """A completed metrics.json file is counted as complete."""

    def test_complete_detected(self, tmp_path):
        """Writing a valid metrics.json for one policy-run marks it complete."""
        stage = ExperimentStage.NBAIOT_MAIN
        run = PolicyRunId(
            cell=TrainingCellId(stage=stage, seed=0),
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        )
        rp = ArtifactLayout(base_dir=tmp_path, stage=stage).policy_run(run).result_dir
        rp.mkdir(parents=True, exist_ok=True)
        (rp / "metrics.json").write_text(
            valid_metrics_json("global_threshold", "nbaiot_main", 0)
        )

        report = get_status(base_dir=tmp_path)
        rr = report.stage_reports[ExperimentStage.NBAIOT_MAIN.value]

        assert len(rr.complete) == 1
        assert len(rr.missing) == _NBAIOT_MAIN_CELLS - 1
        assert len(rr.aborted) == 0


class TestAbortedDetected:
    """An aborted marker file is counted as aborted."""

    def test_aborted_detected(self, tmp_path):
        """Writing a run-aborted marker for one policy-run marks it aborted."""
        stage = ExperimentStage.NBAIOT_MAIN
        run = PolicyRunId(
            cell=TrainingCellId(stage=stage, seed=1),
            policy=ThresholdPolicy.LOCAL_THRESHOLD,
        )
        rp = ArtifactLayout(base_dir=tmp_path, stage=stage).policy_run(run).result_dir
        rp.mkdir(parents=True, exist_ok=True)
        (rp / ArtifactFile.RUN_ABORTED).write_text("OOM error")

        report = get_status(base_dir=tmp_path)
        rr = report.stage_reports[ExperimentStage.NBAIOT_MAIN.value]

        assert len(rr.aborted) == 1
        assert len(rr.missing) == _NBAIOT_MAIN_CELLS - 1
        assert len(rr.complete) == 0


class TestSummaryRows:
    """Summary rows aggregate per-stage and total counts."""

    def test_summary_rows_counts(self, tmp_path):
        """Summary contains two rows: nbaiot_main and total."""
        report = get_status(base_dir=tmp_path)
        rows = report.summary_rows()

        assert len(rows) == 2

        assert rows[0][4] == _NBAIOT_MAIN_CELLS
        assert rows[1][4] == _TOTAL_CELLS
