from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from datp.app.cli.status import get_status
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile
from datp.config.stages import ExperimentStage
from datp.core.identity import PolicyRunId, TrainingCellId
from tests.fixtures.payloads import valid_metrics_json

_TOTAL_CELLS = 15  # 3 policies × 5 seeds, NBAIOT_MAIN only
_NBAIOT_MAIN_CELLS = 15


class TestAllMissingFreshDir:
    def test_all_missing_fresh_dir(self, tmp_path):
        report = get_status(base_dir=tmp_path)
        total_missing = sum(rr.missing_count for rr in report.stage_reports.values())
        total_complete = sum(rr.complete_count for rr in report.stage_reports.values())
        total_aborted = sum(rr.aborted_count for rr in report.stage_reports.values())

        assert total_missing == _TOTAL_CELLS
        assert total_complete == 0
        assert total_aborted == 0


class TestCompleteDetected:
    def test_complete_detected(self, tmp_path):
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

        assert rr.complete_count == 1
        assert rr.missing_count == _NBAIOT_MAIN_CELLS - 1
        assert rr.aborted_count == 0


class TestAbortedDetected:
    def test_aborted_detected(self, tmp_path):
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

        assert rr.aborted_count == 1
        assert rr.missing_count == _NBAIOT_MAIN_CELLS - 1
        assert rr.complete_count == 0


class TestSummaryLinesFormat:
    def test_summary_lines_format(self, tmp_path):
        report = get_status(base_dir=tmp_path)
        lines = report.summary_lines()

        assert len(lines) == 2  # 1 stage + Overall

        assert f"total={_NBAIOT_MAIN_CELLS}" in lines[0]
        assert f"total={_TOTAL_CELLS}" in lines[1]
