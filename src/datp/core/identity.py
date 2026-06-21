from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from datp.attacks.enums import ThresholdPolicy
from datp.config.stages import ExperimentStage
from datp.core.enums import PathToken

if TYPE_CHECKING:
    from typing import TypeAlias

# ── Type aliases ───────────────────────────────────────────────────────────
# Shared training key: a TrainingCellId groups cells that share one FL encoder + score artifacts.
TrainingKey: "TypeAlias" = "TrainingCellId"


def seed_segment(seed: int) -> str:
    return f"{PathToken.SEED_PREFIX}{seed}"


def make_run_id(stage: ExperimentStage, seed: int) -> str:
    ts_ms = int(time.time() * 1000)
    parts = [stage.value, f"seed{seed}", str(ts_ms)]
    return "_".join(parts)


@dataclass(frozen=True, slots=True)
class TrainingCellId:
    """Shared training identity for one FL encoder and score-artifact cell."""

    stage: ExperimentStage
    seed: int

    def label(self) -> str:
        return f"stage={self.stage} seed={self.seed}"


@dataclass(frozen=True, slots=True)
class PolicyRunId:
    """Identity for one policy evaluation run within a shared training cell."""

    cell: TrainingCellId
    policy: ThresholdPolicy

    @property
    def stage(self) -> ExperimentStage:
        return self.cell.stage

    @property
    def seed(self) -> int:
        return self.cell.seed

    def audit_id(self) -> str:
        return f"{self.stage}_{self.policy}_seed{self.seed}"

    def shared_training_key(self) -> TrainingKey:
        return self.cell

    def label(self) -> str:
        return f"stage={self.stage} policy={self.policy} seed={self.seed}"

    def tracking_name(self) -> str:
        return f"{self.stage.value}_{self.policy.value}_seed{self.seed}"
