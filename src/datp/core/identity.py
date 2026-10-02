from __future__ import annotations

from datp.types import (
    NarrativeText,
    RandomSeed,
    RunId,
)


from dataclasses import dataclass

from datp.config.models import ExperimentStage
from datp.core.enums import PathToken, ThresholdPolicy

def seed_segment(seed: RandomSeed) -> NarrativeText:
    return f"{PathToken.SEED_PREFIX}{seed}"


@dataclass(frozen=True, slots=True)
class TrainingCellId:

    stage: ExperimentStage
    seed: RandomSeed

    def label(self) -> NarrativeText:
        return f"stage={self.stage} seed={self.seed}"


@dataclass(frozen=True, slots=True)
class PolicyRunId:

    cell: TrainingCellId
    policy: ThresholdPolicy

    @property
    def stage(self) -> ExperimentStage:
        return self.cell.stage

    @property
    def seed(self) -> RandomSeed:
        return self.cell.seed

    def audit_id(self) -> RunId:
        return RunId(f"{self.stage}_{self.policy}_seed{self.seed}")

    def label(self) -> NarrativeText:
        return f"stage={self.stage} policy={self.policy} seed={self.seed}"
