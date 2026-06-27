"""Run lifecycle context manager writing sentinel files around experiment runs."""

from __future__ import annotations

import contextlib
import traceback
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING

from datp.artifacts.names import ArtifactFile, RunState
from datp.core.enums import ThresholdPolicy

if TYPE_CHECKING:
    from datp.core.logging import _LoggerProtocol


def _get_logger() -> _LoggerProtocol:
    """Return the structlog logger for this module."""
    from datp.core.logging import get_logger

    return get_logger(__name__)


def check_run_state(run_dir: Path) -> RunState:
    """Return the state of a run by inspecting sentinel files, or CORRUPT if ambiguous."""
    markers = {
        RunState.IN_PROGRESS: run_dir / ArtifactFile.RUN_IN_PROGRESS,
        RunState.DONE: run_dir / ArtifactFile.RUN_DONE,
        RunState.ABORTED: run_dir / ArtifactFile.RUN_ABORTED,
    }
    active = [state for state, path in markers.items() if path.exists()]
    return active[0] if len(active) == 1 else RunState.CORRUPT


class RunLifecycle:
    """Context manager that writes IN_PROGRESS/DONE/ABORTED sentinel files around a run."""

    def __init__(
        self,
        run_dir: Path,
        *,
        policy: ThresholdPolicy | None = None,
        seed: int | None = None,
    ) -> None:
        """Initialize with the run directory and optional policy/seed for abort logging."""
        self.run_dir = run_dir
        self.policy = policy
        self.seed = seed
        self.last_completed_round: int | None = None
        self._in_progress = run_dir / ArtifactFile.RUN_IN_PROGRESS
        self._done = run_dir / ArtifactFile.RUN_DONE
        self._aborted = run_dir / ArtifactFile.RUN_ABORTED

    def __enter__(self) -> RunLifecycle:
        """Create the run directory and write the IN_PROGRESS sentinel."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._aborted.unlink(missing_ok=True)
        self._in_progress.touch()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Remove IN_PROGRESS, then write DONE on success or ABORTED with traceback on exception."""
        self._in_progress.unlink(missing_ok=True)

        if exc_type is None:
            self._done.write_text("Run completed successfully.\n")
            return

        try:
            tb_str = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
            self._aborted.write_text(
                f"last_completed_round: {self.last_completed_round}\n"
                f"policy: {self.policy}\n"
                f"seed: {self.seed}\n"
                f"traceback:\n{tb_str}"
            )
        except Exception as e:
            with contextlib.suppress(Exception):
                _get_logger().error(
                    "artifacts.abort_marker_write_failed",
                    run_dir=str(self.run_dir),
                    error=str(e),
                )
