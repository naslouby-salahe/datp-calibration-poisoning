from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from pydantic import BaseModel, ConfigDict

from datp.artifacts.io import write_csv, write_metrics_atomic
from datp.artifacts.lifecycle import RunLifecycle, check_run_state
from datp.artifacts.names import RunState
from datp.core.enums import Baseline


class TestCheckRunState:
    def test_empty_directory_is_corrupt(self, tmp_path: Path) -> None:
        assert check_run_state(tmp_path) == RunState.CORRUPT

    def test_in_progress_only(self, tmp_path: Path) -> None:
        (tmp_path / "IN_PROGRESS").touch()
        assert check_run_state(tmp_path) == RunState.IN_PROGRESS

    def test_done_only(self, tmp_path: Path) -> None:
        (tmp_path / "DONE.txt").write_text("ok\n")
        assert check_run_state(tmp_path) == RunState.DONE

    def test_aborted_only(self, tmp_path: Path) -> None:
        (tmp_path / "ABORTED.txt").write_text("err\n")
        assert check_run_state(tmp_path) == RunState.ABORTED

    def test_conflicting_markers_are_corrupt(self, tmp_path: Path) -> None:
        (tmp_path / "IN_PROGRESS").touch()
        (tmp_path / "DONE.txt").write_text("ok\n")
        assert check_run_state(tmp_path) == RunState.CORRUPT


class TestRunLifecycleMarkers:
    def test_run_lifecycle_markers_success(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run_ok"
        with RunLifecycle(run_dir, baseline=Baseline.B1, seed=42) as rl:
            assert (run_dir / "IN_PROGRESS").exists()
            rl.last_completed_round = 5

        assert not (run_dir / "IN_PROGRESS").exists()
        assert (run_dir / "DONE.txt").exists()
        assert not (run_dir / "ABORTED.txt").exists()

    def test_run_lifecycle_retry_clears_stale_abort(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run_retry"
        (run_dir).mkdir()
        (run_dir / "ABORTED.txt").write_text("previous failure\n")

        with RunLifecycle(run_dir, baseline=Baseline.B1, seed=42):
            assert not (run_dir / "ABORTED.txt").exists()

        assert (run_dir / "DONE.txt").exists()
        assert not (run_dir / "ABORTED.txt").exists()

    def test_run_lifecycle_markers_failure(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "run_fail"
        with pytest.raises(RuntimeError, match="boom"):
            with RunLifecycle(run_dir, baseline=Baseline.B2, seed=7) as rl:
                assert (run_dir / "IN_PROGRESS").exists()
                rl.last_completed_round = 3
                raise RuntimeError("boom")

        assert not (run_dir / "IN_PROGRESS").exists()
        assert not (run_dir / "DONE.txt").exists()
        assert (run_dir / "ABORTED.txt").exists()

    def test_run_state_after_success(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "state_ok"
        with RunLifecycle(run_dir):
            pass
        assert check_run_state(run_dir) == RunState.DONE

    def test_run_state_after_failure(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "state_fail"
        with pytest.raises(ValueError):
            with RunLifecycle(run_dir):
                raise ValueError("oops")
        assert check_run_state(run_dir) == RunState.ABORTED


class TestAbortedMarker:
    def test_aborted_marker_contains_round_info(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "abort_info"
        with pytest.raises(RuntimeError):
            with RunLifecycle(run_dir, baseline=Baseline.B1, seed=42) as rl:
                rl.last_completed_round = 10
                raise RuntimeError("OOM at round 11")

        content = (run_dir / "ABORTED.txt").read_text()
        assert "last_completed_round: 10" in content
        assert "baseline: b1" in content
        assert "seed: 42" in content
        assert "RuntimeError" in content
        assert "OOM at round 11" in content

    def test_aborted_marker_with_no_round(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "abort_no_rnd"
        with pytest.raises(KeyError):
            with RunLifecycle(run_dir, baseline=Baseline.B3, seed=1):
                raise KeyError("missing key")

        content = (run_dir / "ABORTED.txt").read_text()
        assert "last_completed_round: None" in content
        assert "baseline: b3" in content

    def test_aborted_marker_not_written_on_success(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "no_abort"
        with RunLifecycle(run_dir):
            pass
        assert not (run_dir / "ABORTED.txt").exists()


class TestMetricsAtomicRename:
    def test_metrics_atomic_rename_writes_valid_json(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "metrics_ok"
        metrics = {"auc_roc": 0.95, "cv_fpr": 0.12}
        final = write_metrics_atomic(run_dir, metrics)

        assert final.name == "metrics.json"
        assert final.exists()
        assert not (run_dir / "metrics.json.tmp").exists()

        loaded = json.loads(final.read_text())
        assert loaded == metrics

    def test_metrics_atomic_rename_no_placeholder(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "no_placeholder"
        run_dir.mkdir()
        assert not (run_dir / "metrics.json").exists()
        assert not (run_dir / "metrics.json.tmp").exists()

    def test_metrics_atomic_rename_overwrites_previous(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "overwrite"
        write_metrics_atomic(run_dir, {"v": 1})
        write_metrics_atomic(run_dir, {"v": 2})
        loaded = json.loads((run_dir / "metrics.json").read_text())
        assert loaded == {"v": 2}


def test_clean_run_has_metrics_and_done(tmp_path: Path) -> None:
    run_dir = tmp_path / "full_run"
    with RunLifecycle(run_dir, baseline=Baseline.B1, seed=0) as rl:
        rl.last_completed_round = 40
        write_metrics_atomic(run_dir, {"auc": 0.99})

    assert (run_dir / "metrics.json").exists()
    assert (run_dir / "DONE.txt").exists()
    assert not (run_dir / "ABORTED.txt").exists()
    assert not (run_dir / "IN_PROGRESS").exists()


def test_no_zero_byte_placeholders(tmp_path: Path) -> None:
    run_dir = tmp_path / "no_placeholders"
    with RunLifecycle(run_dir):
        assert not (run_dir / "metrics.json").exists()
        assert not (run_dir / "mlflow_run.json").exists()


class _FakeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    value: int


class TestWriteCsv:
    def test_writes_valid_csv(self, tmp_path: Path) -> None:
        records = [_FakeRecord(name="a", value=1), _FakeRecord(name="b", value=2)]
        path = tmp_path / "out.csv"
        write_csv(path, records)

        assert path.exists()
        df = pd.read_csv(path)
        assert list(df.columns) == ["name", "value"]
        assert df.to_dict("records") == [{"name": "a", "value": 1}, {"name": "b", "value": 2}]

    def test_atomic_rename_no_tmp_remains(self, tmp_path: Path) -> None:
        records = [_FakeRecord(name="x", value=99)]
        path = tmp_path / "data.csv"
        write_csv(path, records)

        assert path.exists()
        assert not (tmp_path / "data.csv.tmp").exists()

    def test_no_placeholder_before_write(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        assert not path.exists()
        assert not (tmp_path / "out.csv.tmp").exists()

    def test_overwrites_previous(self, tmp_path: Path) -> None:
        path = tmp_path / "out.csv"
        write_csv(path, [_FakeRecord(name="old", value=1)])
        write_csv(path, [_FakeRecord(name="new", value=2)])

        df = pd.read_csv(path)
        assert df.to_dict("records") == [{"name": "new", "value": 2}]

    def test_empty_records_does_not_crash(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.csv"
        write_csv(path, [])
        assert path.exists()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "out.csv"
        write_csv(path, [_FakeRecord(name="d", value=1)])
        assert path.exists()
