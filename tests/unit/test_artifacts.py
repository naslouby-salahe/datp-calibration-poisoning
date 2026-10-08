from __future__ import annotations

import json
from pathlib import Path

import pytest

from datp.artifacts import (
    ArtifactLayout,
    RunLifecycle,
    check_run_state,
    write_json_atomic,
)
from datp.config import ExperimentStage
from datp.core import PolicyRunId, TrainingCellId
from datp.enums import (
    ProvenanceSentinel,
    ArtifactDir,
    ArtifactFile,
    RunState,
    ScoringStage,
    ThresholdPolicy,
)
from datp.thresholding import results_exist
from tests.fixtures import valid_metrics_dict


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
        """Verify that ABORTED.txt records policy, seed and traceback."""
        run_dir = tmp_path / "abort_info"
        with pytest.raises(RuntimeError):
            with RunLifecycle(
                run_dir, policy=ThresholdPolicy.GLOBAL_THRESHOLD, seed=42
            ):
                raise RuntimeError("OOM at round 11")

        content = (run_dir / "ABORTED.txt").read_text()
        assert "policy: global_threshold" in content
        assert "seed: 42" in content
        assert "RuntimeError" in content
        assert "OOM at round 11" in content

    def test_aborted_marker_with_no_round(self, tmp_path: Path) -> None:
        """Verify that ABORTED.txt records policy for a failure without a seed."""
        run_dir = tmp_path / "abort_no_rnd"
        with pytest.raises(KeyError):
            with RunLifecycle(
                run_dir, policy=ThresholdPolicy.CLUSTER_THRESHOLD, seed=1
            ):
                raise KeyError("missing key")

        content = (run_dir / "ABORTED.txt").read_text()
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
        """Verify that the atomic JSON writer writes metrics and leaves no temp files."""
        run_dir = tmp_path / "metrics_ok"
        metrics = {"auc_roc": 0.95, "cv_fpr": 0.12}
        final = write_json_atomic(run_dir / ArtifactFile.METRICS, metrics)

        assert final.name == "metrics.json"
        assert final.exists()
        assert not (run_dir / "metrics.json.tmp").exists()

        loaded = json.loads(final.read_text())
        assert loaded == metrics

    def test_metrics_atomic_rename_no_placeholder(self, tmp_path: Path) -> None:
        """Verify that files do not exist before the atomic JSON writer runs."""
        run_dir = tmp_path / "no_placeholder"
        run_dir.mkdir()
        assert not (run_dir / "metrics.json").exists()
        assert not (run_dir / "metrics.json.tmp").exists()

    def test_metrics_atomic_rename_overwrites_previous(self, tmp_path: Path) -> None:
        """Verify that the atomic JSON writer overwrites existing metrics."""
        run_dir = tmp_path / "overwrite"
        write_json_atomic(run_dir / ArtifactFile.METRICS, {"v": 1})
        write_json_atomic(run_dir / ArtifactFile.METRICS, {"v": 2})
        loaded = json.loads((run_dir / "metrics.json").read_text())
        assert loaded == {"v": 2}


def test_clean_run_has_metrics_and_done(tmp_path: Path) -> None:
    """Verify that a normal run creates both metrics.json and DONE.txt."""
    run_dir = tmp_path / "full_run"
    with RunLifecycle(run_dir, policy=ThresholdPolicy.GLOBAL_THRESHOLD, seed=0) as rl:
        rl.last_completed_round = 40
        write_json_atomic(run_dir / ArtifactFile.METRICS, {"auc": 0.99})

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


_OUTPUTS = Path(ArtifactDir.OUTPUTS)


_STAGE = ExperimentStage.NBAIOT_MAIN


def _run(stage: ExperimentStage, policy: ThresholdPolicy, seed: int) -> PolicyRunId:
    """Helper to build PolicyRunId instances."""
    return PolicyRunId(
        cell=TrainingCellId(stage=stage, seed=seed),
        policy=policy,
    )


def _cell(stage: ExperimentStage, seed: int) -> TrainingCellId:
    """Helper to build TrainingCellId instances."""
    return TrainingCellId(stage=stage, seed=seed)


class TestCanonicalResultPath:
    """Tests verifying the results and logging layouts across policies."""

    def test_canonical_result_path_global_threshold(self) -> None:
        """Verify canonical result path for global threshold policy matches layout."""
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.GLOBAL_THRESHOLD, 0))
            .result_dir
        )
        assert p == Path("outputs/results/nbaiot_main/global_threshold/seed_0")

    def test_canonical_result_path_local_threshold(self) -> None:
        """Verify canonical result path for local threshold policy matches layout."""
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.LOCAL_THRESHOLD, 3))
            .result_dir
        )
        assert p == Path("outputs/results/nbaiot_main/local_threshold/seed_3")

    def test_canonical_result_path_custom_base(self, tmp_path: Path) -> None:
        """Verify that layouts respect custom base directory override paths."""
        p = (
            ArtifactLayout(base_dir=tmp_path / "out", stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.CLUSTER_THRESHOLD, 1))
            .result_dir
        )
        assert p == tmp_path / "out/results/nbaiot_main/cluster_threshold/seed_1"

    def test_canonical_result_path_includes_cluster_threshold(self) -> None:
        """Verify that cluster threshold result paths include the policy name."""
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.CLUSTER_THRESHOLD, 5))
            .result_dir
        )
        assert "cluster_threshold" in p.parts

    def test_log_path(self) -> None:
        """Verify canonical log directory path matches the expected layout."""
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.GLOBAL_THRESHOLD, 0))
            .log_dir
        )
        assert p == Path("outputs/logs/nbaiot_main/global_threshold/seed_0")

    def test_log_path_includes_cluster_threshold(self) -> None:
        """Verify log directory paths for cluster threshold include the policy name."""
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .policy_run(_run(_STAGE, ThresholdPolicy.CLUSTER_THRESHOLD, 1))
            .log_dir
        )
        assert "cluster_threshold" in p.parts


class TestScorePath:
    """Tests verifying scores output directory layouts."""

    def test_score_path_base(self) -> None:
        """Verify the base score directory layout path matches expectations."""
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .score_cell(_cell(_STAGE, 0))
            .score_dir
        )
        assert p == Path("outputs/scores/nbaiot_main/seed_0")

    def test_score_path_with_stage(self) -> None:
        """Verify scoring stage subdirectory paths match layout definitions."""
        p = (
            ArtifactLayout(base_dir=_OUTPUTS, stage=_STAGE)
            .score_cell(_cell(_STAGE, 0))
            .score_dir
            / ScoringStage.CAL.value
        )
        assert p == Path("outputs/scores/nbaiot_main/seed_0/cal")


class TestResultsExist:
    """Tests verifying whether output metrics exist and validate against the schema constraints."""

    def test_completed_run(self, tmp_path: Path) -> None:
        """Verify that a completed run with a valid schema-abiding metrics file returns True."""
        rdir = tmp_path / "results" / "nbaiot_main" / "global_threshold" / "seed_42"
        rdir.mkdir(parents=True)
        (rdir / "metrics.json").write_text(json.dumps(valid_metrics_dict()))

        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is True
        )

    def test_stale_pre_schema_payload_returns_false(self, tmp_path: Path) -> None:
        """Verify that old/stale metrics payloads failing schema checks return False."""
        rdir = tmp_path / "results" / "nbaiot_main" / "global_threshold" / "seed_42"
        rdir.mkdir(parents=True)
        (rdir / "metrics.json").write_text(json.dumps({"auroc": 0.99}))

        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )

    def test_unknown_provenance_returns_false(self, tmp_path: Path) -> None:
        """Verify that metrics files with UNKNOWN provenance identities return False."""
        rdir = tmp_path / "results" / "nbaiot_main" / "global_threshold" / "seed_42"
        rdir.mkdir(parents=True)
        payload = valid_metrics_dict()
        payload["provenance"]["config_identity"] = "UNKNOWN"
        (rdir / "metrics.json").write_text(json.dumps(payload))

        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )

    def test_missing_hash_provenance_returns_false(self, tmp_path: Path) -> None:
        """Verify that metrics with missing score hash signatures return False."""
        rdir = tmp_path / "results" / "nbaiot_main" / "global_threshold" / "seed_42"
        rdir.mkdir(parents=True)
        payload = valid_metrics_dict()
        payload["provenance"]["score_artifact_identity"] = (
            ProvenanceSentinel.MISSING_MANIFEST_HASH
        )
        (rdir / "metrics.json").write_text(json.dumps(payload))

        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )

    @pytest.mark.parametrize(
        "missing_key",
        [
            "eligible_ids",
            "pending_ids",
            "eval_incomplete_ids",
        ],
    )
    def test_missing_required_id_list_returns_false(
        self, tmp_path: Path, missing_key: str
    ) -> None:
        """Verify that missing key lists like eligible_ids or pending_ids return False."""
        rdir = tmp_path / "results" / "nbaiot_main" / "global_threshold" / "seed_42"
        rdir.mkdir(parents=True)
        payload = valid_metrics_dict()
        del payload[missing_key]
        (rdir / "metrics.json").write_text(json.dumps(payload))

        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )

    def test_missing_metrics(self, tmp_path: Path) -> None:
        """Verify that when no metrics file exists, results_exist returns False."""
        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )

    def test_empty_metrics(self, tmp_path: Path) -> None:
        """Verify that an empty/zero-byte metrics.json file returns False."""
        rdir = tmp_path / "results" / "nbaiot_main" / "global_threshold" / "seed_42"
        rdir.mkdir(parents=True)
        (rdir / "metrics.json").touch()

        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )

    def test_tmp_placeholder_not_counted(self, tmp_path: Path) -> None:
        """Verify that temp files (metrics.json.tmp) do not count as completed results."""
        rdir = tmp_path / "results" / "nbaiot_main" / "global_threshold" / "seed_42"
        rdir.mkdir(parents=True)
        (rdir / "metrics.json.tmp").write_text('{"partial": true}')

        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )

    def test_different_policy_not_found(self, tmp_path: Path) -> None:
        """Verify that checking status of one policy doesn't mistakenly match other policy folders."""
        rdir = tmp_path / "results" / "nbaiot_main" / "global_threshold" / "seed_42"
        rdir.mkdir(parents=True)
        (rdir / "metrics.json").write_text(json.dumps(valid_metrics_dict()))

        assert (
            results_exist(
                ThresholdPolicy.GLOBAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is True
        )
        assert (
            results_exist(
                ThresholdPolicy.LOCAL_THRESHOLD, _STAGE, 42, base_dir=tmp_path
            )
            is False
        )
