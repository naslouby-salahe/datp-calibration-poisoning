"""Tests verifying custom strategy checkpointing milestones, parameter disk exports, and failure diagnostics."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from flwr.common import Code, FitRes, Status, ndarrays_to_parameters

from datp.artifacts.names import ArtifactFile
from datp.checkpointing.enums import CheckpointConvergenceMode
from datp.federated.checkpoints import load_params_snapshot
from datp.federated.convergence import ConvergenceMonitor
from datp.federated.strategies import DatpFedAvg, FedAvgConfig


def _make_strategy(
    milestones: tuple[int, ...] = (),
    checkpoint_disk_dirs: dict[int, Path] | None = None,
) -> DatpFedAvg:
    """Helper to build a DatpFedAvg strategy instance with preset monitoring config."""
    monitor = ConvergenceMonitor(
        rounds_initial=1,
        rounds_max=10,
        relative_threshold=0.05,
        window=2,
    )
    params = np.zeros((2, 2), dtype=np.float32)
    return DatpFedAvg(
        FedAvgConfig(
            convergence_monitor=monitor,
            round_timeout_s=300.0,
            fraction_fit=1.0,
            fraction_evaluate=1.0,
            min_fit_clients=1,
            min_evaluate_clients=1,
            min_available_clients=1,
            initial_parameters=ndarrays_to_parameters([params]),
            checkpoint_milestones=milestones,
            convergence_mode=CheckpointConvergenceMode.LOG_ONLY,
            checkpoint_disk_dirs=checkpoint_disk_dirs,
        )
    )


def _make_fit_result(params: np.ndarray) -> tuple[MagicMock, FitRes]:
    """Helper to package weight parameters as Flower fit results."""
    proxy = MagicMock()
    fit_res = FitRes(
        status=Status(code=Code.OK, message=""),
        parameters=ndarrays_to_parameters([params]),
        num_examples=10,
        metrics={},
    )
    return proxy, fit_res


class TestCheckpointDiskDirsDefault:
    """Tests verifying default config mapping of milestone target folders."""

    def test_no_disk_dirs_when_not_provided(self) -> None:
        """Verify default directory mapping is empty when not set."""
        strategy = _make_strategy(milestones=(5,))
        assert strategy._checkpoint_disk_dirs == {}

    def test_empty_dict_when_none(self) -> None:
        """Verify target folders mapping is empty when None is passed."""
        strategy = _make_strategy(milestones=(5,), checkpoint_disk_dirs=None)
        assert strategy._checkpoint_disk_dirs == {}


class TestAggregateFitDiskWrite:
    """Tests verifying parameters serialization at configured milestones."""

    def test_params_snapshot_written_at_milestone(self, tmp_path: Path) -> None:
        """Verify parameter NPZ snapshot is exported to disk when milestone round matches."""
        round_dir = tmp_path / "round_5"
        strategy = _make_strategy(
            milestones=(5,),
            checkpoint_disk_dirs={5: round_dir},
        )
        params = np.ones((2, 2), dtype=np.float32) * 2.0
        proxy, fit_res = _make_fit_result(params)

        strategy.aggregate_fit(5, [(proxy, fit_res)], [])

        snap = round_dir / ArtifactFile.PARAMS_SNAPSHOT
        assert snap.exists(), "params.npz should be written at milestone round"

    def test_snapshot_content_matches_aggregated_params(self, tmp_path: Path) -> None:
        """Verify serialized parameter snapshot matches aggregated model weights."""
        round_dir = tmp_path / "round_3"
        strategy = _make_strategy(
            milestones=(3,),
            checkpoint_disk_dirs={3: round_dir},
        )
        expected = np.array([[7.0, 8.0], [9.0, 10.0]], dtype=np.float32)
        proxy, fit_res = _make_fit_result(expected)

        strategy.aggregate_fit(3, [(proxy, fit_res)], [])

        loaded = load_params_snapshot(round_dir)
        assert loaded is not None
        np.testing.assert_array_almost_equal(loaded[0], expected)

    def test_no_disk_write_on_non_milestone_round(self, tmp_path: Path) -> None:
        """Verify no disk export is triggered on non-milestone rounds."""
        round_dir = tmp_path / "round_5"
        strategy = _make_strategy(
            milestones=(5,),
            checkpoint_disk_dirs={5: round_dir},
        )
        params = np.ones((2, 2), dtype=np.float32)
        proxy, fit_res = _make_fit_result(params)

        strategy.aggregate_fit(3, [(proxy, fit_res)], [])

        assert not (round_dir / ArtifactFile.PARAMS_SNAPSHOT).exists()

    def test_disk_dir_not_required_for_milestone(self, tmp_path: Path) -> None:
        """Verify milestone registers in-memory even if target directory is empty."""
        strategy = _make_strategy(
            milestones=(5,),
            checkpoint_disk_dirs={},
        )
        params = np.ones((2, 2), dtype=np.float32)
        proxy, fit_res = _make_fit_result(params)

        strategy.aggregate_fit(5, [(proxy, fit_res)], [])

        assert 5 in strategy.parameter_snapshots

    def test_in_memory_snapshot_always_stored(self, tmp_path: Path) -> None:
        """Verify memory caches aggregated weights at milestone rounds."""
        round_dir = tmp_path / "round_2"
        strategy = _make_strategy(
            milestones=(2,),
            checkpoint_disk_dirs={2: round_dir},
        )
        params = np.array([[3.0, 4.0]], dtype=np.float32)
        proxy, fit_res = _make_fit_result(params)

        strategy.aggregate_fit(2, [(proxy, fit_res)], [])

        assert 2 in strategy.parameter_snapshots

    def test_multiple_milestones_all_written(self, tmp_path: Path) -> None:
        """Verify multiple milestones successfully write parameter snapshots to corresponding dirs."""
        dirs = {r: tmp_path / f"round_{r}" for r in (2, 4)}
        strategy = _make_strategy(
            milestones=(2, 4),
            checkpoint_disk_dirs=dirs,
        )
        params = np.ones((2,), dtype=np.float32)
        proxy2, fit2 = _make_fit_result(params)
        proxy4, fit4 = _make_fit_result(params * 2)

        strategy.aggregate_fit(2, [(proxy2, fit2)], [])
        strategy.aggregate_fit(4, [(proxy4, fit4)], [])

        assert (dirs[2] / ArtifactFile.PARAMS_SNAPSHOT).exists()
        assert (dirs[4] / ArtifactFile.PARAMS_SNAPSHOT).exists()


class TestFullParticipationDiagnostics:
    """Tests verifying aggregate crash reporting and exception messages."""

    def test_aggregate_fit_reports_successful_and_failed_client_ids(self) -> None:
        """Ensure strategy raises error containing failed client IDs on aggregation crash."""
        strategy = _make_strategy()
        ok_proxy, ok_res = _make_fit_result(np.zeros((2, 2), dtype=np.float32))
        ok_proxy.cid = "c0"
        bad_proxy = MagicMock()
        bad_proxy.cid = "c3"
        bad_res = FitRes(
            status=Status(code=Code.FIT_NOT_IMPLEMENTED, message="trainer crashed"),
            parameters=ndarrays_to_parameters([np.zeros((2, 2), dtype=np.float32)]),
            num_examples=0,
            metrics={},
        )

        with pytest.raises(RuntimeError) as exc:
            strategy.aggregate_fit(7, [(ok_proxy, ok_res)], [(bad_proxy, bad_res)])

        message = str(exc.value)
        assert "round 7" in message
        assert "fit" in message
        assert "c3" in message

    def test_aggregate_evaluate_reports_exception_failures(self) -> None:
        """Ensure strategy raises error detailing client evaluate process exceptions."""
        strategy = _make_strategy()

        with pytest.raises(RuntimeError) as exc:
            strategy.aggregate_evaluate(4, [], [RuntimeError("client process died")])

        message = str(exc.value)
        assert "evaluate" in message
        assert "round 4" in message
