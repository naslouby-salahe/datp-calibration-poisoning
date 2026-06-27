"""Tests verifying project artifact output lifecycle managers, run markers, and atomic file writers."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from pydantic import BaseModel, ConfigDict

from datp.artifacts.io import write_csv, write_metrics_atomic
from datp.artifacts.lifecycle import RunLifecycle, check_run_state
from datp.artifacts.names import RunState
from datp.core.enums import ThresholdPolicy


class TestCheckRunState:
    """Tests verifying directory run status inspection code."""

    def test_empty_directory_is_corrupt(self, tmp_path: Path) -> None:
        """Verify that an empty directory is classified as CORRUPT state."""
        assert check_run_state(tmp_path) == RunState.CORRUPT

    def test_in_progress_only(self, tmp_path: Path) -> None:
        """Verify that containing only the IN_PROGRESS file resolves to IN_PROGRESS state."""
        (tmp_path / "IN_PROGRESS").touch()
        assert check_run_state(tmp_path) == RunState.IN_PROGRESS

    def test_done_only(self, tmp_path: Path) -> None:
        """Verify that containing only the DONE.txt marker resolves to DONE state."""
        (tmp_path / "DONE.txt").write_text("ok\n")
        assert check_run_state(tmp_path) == RunState.DONE

    def test_aborted_only(self, tmp_path: Path) -> None:
        """Verify that containing only the ABORTED.txt marker resolves to ABORTED state."""
        (tmp_path / "ABORTED.txt").write_text("err\n")
        assert check_run_state(tmp_path) == RunState.ABORTED

    def test_conflicting_markers_are_corrupt(self, tmp_path: Path) -> None:
        """Verify that containing multiple contradictory markers resolves to CORRUPT state."""
        (tmp_path / "IN_PROGRESS").touch()
        (tmp_path / "DONE.txt").write_text("ok\n")
        assert check_run_state(tmp_path) == RunState.CORRUPT


class TestRunLifecycleMarkers:
    """Tests verifying lifecycle block context managers and their state outputs."""

    def test_run_lifecycle_markers_success(self, tmp_path: Path) -> None:
        """Verify successful block execution creates DONE.txt and removes IN_PROGRESS."""
        run_dir = tmp_path / "run_ok"
        with RunLifecycle(
            run_dir, policy=ThresholdPolicy.GLOBAL_THRESHOLD, seed=42
        ) as rl:
            assert (run_dir / "IN_PROGRESS").exists()
            rl.last_completed_round = 5

        assert not (run_dir / "IN_PROGRESS").exists()
        assert (run_dir / "DONE.txt").exists()
        assert not (run_dir / "ABORTED.txt").exists()

    def test_run_lifecycle_retry_clears_stale_abort(self, tmp_path: Path) -> None:
        """Verify that starting a new run clears previous ABORTED.txt files."""
        run_dir = tmp_path / "run_retry"
        (run_dir).mkdir()
        (run_dir / "ABORTED.txt").write_text("previous failure\n")

        with RunLifecycle(run_dir, policy=ThresholdPolicy.GLOBAL_THRESHOLD, seed=42):
            assert not (run_dir / "ABORTED.txt").exists()

        assert (run_dir / "DONE.txt").exists()
        assert not (run_dir / "ABORTED.txt").exists()

    def test_run_lifecycle_markers_failure(self, tmp_path: Path) -> None:
        """Verify that error raising within block creates ABORTED.txt and removes IN_PROGRESS."""
        run_dir = tmp_path / "run_fail"
        with pytest.raises(RuntimeError, match="boom"):
            with RunLifecycle(
                run_dir, policy=ThresholdPolicy.LOCAL_THRESHOLD, seed=7
            ) as rl:
                assert (run_dir / "IN_PROGRESS").exists()
                rl.last_completed_round = 3
                raise RuntimeError("boom")

        assert not (run_dir / "IN_PROGRESS").exists()
        assert not (run_dir / "DONE.txt").exists()
        assert (run_dir / "ABORTED.txt").exists()

    def test_run_state_after_success(self, tmp_path: Path) -> None:
        """Verify check_run_state resolves to DONE after run context completes successfully."""
        run_dir = tmp_path / "state_ok"
        with RunLifecycle(run_dir):
            assert (run_dir / "IN_PROGRESS").exists()
        assert check_run_state(run_dir) == RunState.DONE

    def test_run_state_after_failure(self, tmp_path: Path) -> None:
        """Verify check_run_state resolves to ABORTED after run context exits via raise."""
        run_dir = tmp_path / "state_fail"
        with pytest.raises(ValueError):
            with RunLifecycle(run_dir):
                raise ValueError("oops")
        assert check_run_state(run_dir) == RunState.ABORTED


class TestAbortedMarker:
    """Tests verifying contents of the generated ABORTED.txt error log."""

    def test_aborted_marker_contains_round_info(self, tmp_path: Path) -> None:
        """Verify that ABORTED.txt records details on last completed round and traceback."""
        run_dir = tmp_path / "abort_info"
        with pytest.raises(RuntimeError):
            with RunLifecycle(
                run_dir, policy=ThresholdPolicy.GLOBAL_THRESHOLD, seed=42
            ) as rl:
                rl.last_completed_round = 10
                raise RuntimeError("OOM at round 11")

        content = (run_dir / "ABORTED.txt").read_text()
        assert "last_completed_round: 10" in content
        assert "policy: global_threshold" in content
        assert "seed: 42" in content
        assert "RuntimeError" in content
        assert "OOM at round 11" in content

    def test_aborted_marker_with_no_round(self, tmp_path: Path) -> None:
        """Verify that ABORTED.txt records round as None if no round completed."""
        run_dir = tmp_path / "abort_no_rnd"
        with pytest.raises(KeyError):
            with RunLifecycle(
                run_dir, policy=ThresholdPolicy.CLUSTER_THRESHOLD, seed=1
            ):
                raise KeyError("missing key")

        content = (run_dir / "ABORTED.txt").read_text()
        assert "last_completed_round: None" in content
        assert "policy: cluster_threshold" in content

    def test_aborted_marker_not_written_on_success(self, tmp_path: Path) -> None:
        """Verify that successful runs do not create ABORTED.txt."""
        run_dir = tmp_path / "no_abort"
        with RunLifecycle(run_dir):
            assert (run_dir / "IN_PROGRESS").exists()
        assert not (run_dir / "ABORTED.txt").exists()


class TestMetricsAtomicRename:
    """Tests verifying atomic writer guarantees for metrics.json."""

    def test_metrics_atomic_rename_writes_valid_json(self, tmp_path: Path) -> None:
        """Verify that write_metrics_atomic writes correct values and leaves no temp files."""
        run_dir = tmp_path / "metrics_ok"
        metrics = {"auc_roc": 0.95, "cv_fpr": 0.12}
        final = write_metrics_atomic(run_dir, metrics)

        assert final.name == "metrics.json"
        assert final.exists()
        assert not (run_dir / "metrics.json.tmp").exists()

        loaded = json.loads(final.read_text())
        assert loaded == metrics

    def test_metrics_atomic_rename_no_placeholder(self, tmp_path: Path) -> None:
        """Verify that files do not exist prior to calling write_metrics_atomic."""
        run_dir = tmp_path / "no_placeholder"
        run_dir.mkdir()
        assert not (run_dir / "metrics.json").exists()
        assert not (run_dir / "metrics.json.tmp").exists()

    def test_metrics_atomic_rename_overwrites_previous(self, tmp_path: Path) -> None:
        """Verify that write_metrics_atomic successfully overwrites existing files."""
        run_dir = tmp_path / "overwrite"
        write_metrics_atomic(run_dir, {"v": 1})
        write_metrics_atomic(run_dir, {"v": 2})
        loaded = json.loads((run_dir / "metrics.json").read_text())
        assert loaded == {"v": 2}


def test_clean_run_has_metrics_and_done(tmp_path: Path) -> None:
    """Verify that a normal run creates both metrics.json and DONE.txt."""
    run_dir = tmp_path / "full_run"
    with RunLifecycle(run_dir, policy=ThresholdPolicy.GLOBAL_THRESHOLD, seed=0) as rl:
        rl.last_completed_round = 40
        write_metrics_atomic(run_dir, {"auc": 0.99})

    assert (run_dir / "metrics.json").exists()
    assert (run_dir / "DONE.txt").exists()
    assert not (run_dir / "ABORTED.txt").exists()
    assert not (run_dir / "IN_PROGRESS").exists()


def test_no_zero_byte_placeholders(tmp_path: Path) -> None:
    """Verify that starting lifecycle doesn't pre-create empty metrics or MLflow files."""
    run_dir = tmp_path / "no_placeholders"
    with RunLifecycle(run_dir):
        assert not (run_dir / "metrics.json").exists()
        assert not (run_dir / "mlflow_run.json").exists()


class _FakeRecord(BaseModel):
    """Mock Pydantic model for CSV writing tests."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    value: int


class TestWriteCsv:
    """Tests verifying CSV serialization and formatting functions."""

    def test_writes_valid_csv(self, tmp_path: Path) -> None:
        """Verify that write_csv serializes Pydantic records with correct header fields."""
        records = [_FakeRecord(name="a", value=1), _FakeRecord(name="b", value=2)]
        path = tmp_path / "out.csv"
        write_csv(path, records)

        assert path.exists()
        df = pd.read_csv(path)
        assert list(df.columns) == ["name", "value"]
        assert df.to_dict("records") == [
            {"name": "a", "value": 1},
            {"name": "b", "value": 2},
        ]

    def test_atomic_rename_no_tmp_remains(self, tmp_path: Path) -> None:
        """Verify that no temp csv files remain in target folders after write_csv."""
        records = [_FakeRecord(name="x", value=99)]
        path = tmp_path / "data.csv"
        write_csv(path, records)

        assert path.exists()
        assert not (tmp_path / "data.csv.tmp").exists()

    def test_no_placeholder_before_write(self, tmp_path: Path) -> None:
        """Verify that output files do not exist before write_csv runs."""
        path = tmp_path / "out.csv"
        assert not path.exists()
        assert not (tmp_path / "out.csv.tmp").exists()

    def test_overwrites_previous(self, tmp_path: Path) -> None:
        """Verify that write_csv successfully overwrites existing CSV files."""
        path = tmp_path / "out.csv"
        write_csv(path, [_FakeRecord(name="old", value=1)])
        write_csv(path, [_FakeRecord(name="new", value=2)])

        df = pd.read_csv(path)
        assert df.to_dict("records") == [{"name": "new", "value": 2}]

    def test_empty_records_does_not_crash(self, tmp_path: Path) -> None:
        """Verify that passing an empty list to write_csv runs successfully."""
        path = tmp_path / "empty.csv"
        write_csv(path, [])
        assert path.exists()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Verify that write_csv creates intermediate parent directories automatically."""
        path = tmp_path / "deep" / "nested" / "out.csv"
        write_csv(path, [_FakeRecord(name="d", value=1)])
        assert path.exists()
