from __future__ import annotations

from datp.types import RandomSeed


from contextlib import suppress
from pathlib import Path

from pydantic import ValidationError

from datp.artifacts.layout import ArtifactLayout
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.thresholding.metrics_serialization import SweepMetrics


def results_exist(
    policy: ThresholdPolicy,
    stage: ExperimentStage,
    seed: RandomSeed,
    *,
    base_dir: Path,
) -> bool:
    run = PolicyRunId(cell=TrainingCellId(stage=stage, seed=RandomSeed(seed)), policy=policy)
    path = ArtifactLayout(base_dir=base_dir, stage=stage).policy_run(run).metrics_path

    if not path.is_file() or path.stat().st_size == 0:
        return False

    with suppress(ValidationError):
        SweepMetrics.model_validate_json(path.read_text())
        return True
    return False
