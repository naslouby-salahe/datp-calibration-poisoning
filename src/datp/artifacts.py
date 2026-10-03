from __future__ import annotations

import contextlib
import traceback
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

import orjson
import pandas as pd
from pydantic import BaseModel
from pydantic_core import to_jsonable_python

from datp.config import ExperimentStage
from datp.core import PolicyRunId, TrainingCellId, get_logger, seed_segment
from datp.enums import (
    ArtifactDir,
    ArtifactFile,
    PathToken,
    RunState,
    ScoringStage,
    ThresholdPolicy,
)
from datp.types import ClientId, JsonValue, RandomSeed

OUTPUTS_DIR: Path = Path(ArtifactDir.OUTPUTS)


RESULTS_PACKAGE_DIR: Path = Path(ArtifactDir.RESULTS)


DATA_ROOT: Path = Path(".")


def nbaiot_main_manifest_path(base_dir: Path) -> Path:
    return (
        poisoning_output_root(base_dir)
        / ArtifactFile.NBAIOT_MAIN_MANIFEST
    )


def poisoning_output_root(base_dir: Path) -> Path:
    return Path(base_dir) / ArtifactDir.CALIBRATION_POISONING


def sensitivity_manifest_path(base_dir: Path) -> Path:
    return poisoning_output_root(base_dir) / ArtifactFile.SENSITIVITY_MANIFEST


@dataclass(frozen=True, slots=True)
class ScoreCellPaths:

    cell: TrainingCellId
    score_dir: Path
    manifest_path: Path


@dataclass(frozen=True, slots=True)
class PolicyRunPaths:

    run: PolicyRunId
    result_dir: Path
    log_dir: Path
    metrics_path: Path


@dataclass(frozen=True, slots=True)
class ArtifactLayout:

    base_dir: Path
    stage: ExperimentStage

    def _root(self, artifact_dir: ArtifactDir) -> Path:
        return self.base_dir / artifact_dir / self.stage

    def score_cell(self, cell: TrainingCellId) -> ScoreCellPaths:
        score_dir = self._root(ArtifactDir.SCORES) / seed_segment(cell.seed)
        return ScoreCellPaths(
            cell=cell,
            score_dir=score_dir,
            manifest_path=score_dir / ArtifactFile.SCORING_MANIFEST,
        )

    def score_file(
        self, cell: TrainingCellId, stage: ScoringStage, client_id: ClientId
    ) -> Path:
        return (
            self.score_cell(cell).score_dir
            / stage
            / f"{client_id}{PathToken.PARQUET_EXT}"
        )

    def policy_run(self, run: PolicyRunId) -> PolicyRunPaths:
        seg = seed_segment(run.seed)
        result_dir = self._root(ArtifactDir.RESULTS) / run.policy / seg
        return PolicyRunPaths(
            run=run,
            result_dir=result_dir,
            metrics_path=result_dir / ArtifactFile.METRICS,
            log_dir=self._root(ArtifactDir.LOGS) / run.policy / seg,
        )


def write_json_atomic(
    path: Path,
    data: JsonValue
    | BaseModel
    | Sequence[BaseModel]
    | Mapping[str, JsonValue | BaseModel | Sequence[BaseModel]],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_bytes(
        orjson.dumps(
            data,
            default=to_jsonable_python,
            option=orjson.OPT_INDENT_2
            | orjson.OPT_SORT_KEYS
            | orjson.OPT_NON_STR_KEYS
            | orjson.OPT_APPEND_NEWLINE,
        )
    )
    tmp.replace(path)
    return path


def write_csv(path: Path, records: Sequence[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    pd.DataFrame([to_jsonable_python(r) for r in records]).to_csv(tmp, index=False)
    tmp.replace(path)


logger = get_logger(__name__)


def check_run_state(run_dir: Path) -> RunState:
    markers = {
        RunState.IN_PROGRESS: run_dir / ArtifactFile.RUN_IN_PROGRESS,
        RunState.DONE: run_dir / ArtifactFile.RUN_DONE,
        RunState.ABORTED: run_dir / ArtifactFile.RUN_ABORTED,
    }
    active = [state for state, path in markers.items() if path.exists()]
    return active[0] if len(active) == 1 else RunState.CORRUPT


class RunLifecycle:

    def __init__(
        self,
        run_dir: Path,
        *,
        policy: ThresholdPolicy | None = None,
        seed: RandomSeed | None = None,
    ) -> None:
        self.run_dir = run_dir
        self.policy = policy
        self.seed = seed
        self._in_progress = run_dir / ArtifactFile.RUN_IN_PROGRESS
        self._done = run_dir / ArtifactFile.RUN_DONE
        self._aborted = run_dir / ArtifactFile.RUN_ABORTED

    def __enter__(self) -> RunLifecycle:
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
        self._in_progress.unlink(missing_ok=True)

        if exc_type is None:
            self._done.write_text("Run completed successfully.\n")
            return

        try:
            tb_str = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
            self._aborted.write_text(
                f"policy: {self.policy}\n"
                f"seed: {self.seed}\n"
                f"traceback:\n{tb_str}"
            )
        except Exception as e:
            with contextlib.suppress(Exception):
                logger.error(
                    "artifacts.abort_marker_write_failed",
                    run_dir=str(self.run_dir),
                    error=str(e),
                )
