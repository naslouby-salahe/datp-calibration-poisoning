"""Run and cell identity types for experiment tracking."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from datp.config.models import ExperimentStage
from datp.core.enums import PathToken, ThresholdPolicy

if TYPE_CHECKING:
    from typing import TypeAlias

TrainingKey: "TypeAlias" = "TrainingCellId"


def seed_segment(seed: int) -> str:
    """Return the path segment string for a given seed number."""
    return f"{PathToken.SEED_PREFIX}{seed}"


def make_run_id(stage: ExperimentStage, seed: int) -> str:
    """Generate a unique run identifier from stage, seed, and current timestamp."""
    return f"{stage.value}_seed{seed}_{int(time.time() * 1000)}"


@dataclass(frozen=True, slots=True)
class TrainingCellId:
    """Identity of one training cell: stage and training seed."""

    stage: ExperimentStage
    seed: int

    def label(self) -> str:
        """Return a human-readable label for this training cell."""
        return f"stage={self.stage} seed={self.seed}"


@dataclass(frozen=True, slots=True)
class PolicyRunId:
    """Identity of one policy run: training cell plus threshold policy."""

    cell: TrainingCellId
    policy: ThresholdPolicy

    @property
    def stage(self) -> ExperimentStage:
        """Experiment stage from the underlying training cell."""
        return self.cell.stage

    @property
    def seed(self) -> int:
        """Training seed from the underlying training cell."""
        return self.cell.seed

    def audit_id(self) -> str:
        """Return a stable audit identifier string."""
        return f"{self.stage}_{self.policy}_seed{self.seed}"

    def shared_training_key(self) -> TrainingKey:
        """Return the training cell key shared across policies."""
        return self.cell

    def label(self) -> str:
        """Return a human-readable label for this policy run."""
        return f"stage={self.stage} policy={self.policy} seed={self.seed}"

    def tracking_name(self) -> str:
        """Return a file-system-safe name for artifact tracking."""
        return f"{self.stage.value}_{self.policy.value}_seed{self.seed}"
