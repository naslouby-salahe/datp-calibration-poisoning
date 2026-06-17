from __future__ import annotations

import contextlib
import traceback
from pathlib import Path
from types import TracebackType
from typing import Any

from datp.artifacts.names import ArtifactFile, RunState
from datp.core.enums import Baseline


def _get_logger() -> Any:
    """Lazy import to avoid circular dependency with logging setup."""
    from datp.core.logging import get_logger

    return get_logger(__name__)


def check_run_state(run_dir: Path) -> RunState:
    """No markers -> UNSTARTED. Conflicting markers (>1) -> CORRUPT."""
    has_in_progress = (run_dir / ArtifactFile.RUN_IN_PROGRESS).exists()
    has_done = (run_dir / ArtifactFile.RUN_DONE).exists()
    has_aborted = (run_dir / ArtifactFile.RUN_ABORTED).exists()

    marker_count = sum([has_in_progress, has_done, has_aborted])
    if marker_count == 0:
        return RunState.UNSTARTED
    if marker_count > 1:
        return RunState.CORRUPT

    if has_done:
        return RunState.DONE
    if has_aborted:
        return RunState.ABORTED
    return RunState.IN_PROGRESS


class RunLifecycle:
    def __init__(
        self,
        run_dir: Path,
        *,
        baseline: Baseline | None = None,
        seed: int | None = None,
    ) -> None:
        self.run_dir = run_dir
        self.baseline = baseline
        self.seed = seed
        self.last_completed_round: int | None = None

    def __enter__(self) -> "RunLifecycle":
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / ArtifactFile.RUN_ABORTED).unlink(missing_ok=True)
        (self.run_dir / ArtifactFile.RUN_IN_PROGRESS).touch()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        in_progress_path = self.run_dir / ArtifactFile.RUN_IN_PROGRESS
        if exc_type is None:
            if in_progress_path.exists():
                in_progress_path.unlink()

            (self.run_dir / ArtifactFile.RUN_DONE).write_text("Run completed successfully.\n")
        else:
            in_progress_path.unlink(missing_ok=True)
            try:
                self._write_aborted(exc_type, exc_val, exc_tb)
            except Exception as inner:  # noqa: BLE001 - best-effort abort marker
                with contextlib.suppress(Exception):
                    _get_logger().error(
                        "artifacts.abort_marker_write_failed",
                        run_dir=str(self.run_dir),
                        error=str(inner),
                    )

        return False

    def _write_aborted(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        lines = [
            f"last_completed_round: {self.last_completed_round}",
            f"baseline: {str(self.baseline) if self.baseline is not None else 'None'}",
            f"seed: {self.seed}",
            f"exception_type: {exc_type.__name__ if exc_type else 'None'}",
            f"exception_message: {exc_val}",
        ]
        if exc_tb is not None:
            tb_lines = traceback.format_tb(exc_tb)
            lines.append("traceback:")
            lines.extend(f" {line.rstrip()}" for line in tb_lines)

        (self.run_dir / ArtifactFile.RUN_ABORTED).write_text("\n".join(lines) + "\n")
