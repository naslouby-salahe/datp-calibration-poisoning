from __future__ import annotations

from datp.types import (
    ClientId,
    SampleCount,
    SignedCount,
    RoundIndex,
    ScoreValue,
    ScoreVector,
    Threshold,
)


import enum
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from datp.config.models import DatpConfig
from datp.core.enums import ThresholdPolicy
from datp.core.identity import TrainingCellId
from datp.thresholding.eligibility import ClientThresholdsCollection

if TYPE_CHECKING:
    from datp.scoring.loading import ScoreProvider


class SweepStep(enum.StrEnum):

    BUILD_MATRIX = "build_matrix"
    VALIDATE_MATRIX = "validate_matrix"
    CHECK_CHECKPOINT = "check_checkpoint"
    TRAIN_FL = "train_fl"
    LOAD_CAL_SCORES = "load_cal_scores"
    COMPUTE_ELIGIBILITY = "compute_eligibility"
    COMPUTE_TAU_GLOBAL = "compute_tau_global"
    INIT_SCORE_PROVIDER = "init_score_provider"
    DERIVE_THRESHOLD = "derive_threshold"
    EVALUATE = "evaluate"
    WRITE_METRICS = "write_metrics"
    SWEEP_COMPLETE = "sweep_complete"


class PolicyRunStatus(enum.StrEnum):

    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(slots=True)
class SweepResult:

    total: SampleCount = 0
    completed: SignedCount = 0
    skipped: SignedCount = 0
    failed: SignedCount = 0


@dataclass(frozen=True, slots=True)
class PipelineRequest:

    key: TrainingCellId
    policy: ThresholdPolicy
    cfg: DatpConfig
    base_dir: Path
    prepared_dir: Path
    checkpoint_round: RoundIndex | None


@dataclass(slots=True)
class SharedPipelineContext:

    key: TrainingCellId
    client_errors: dict[ClientId, ScoreVector]
    eligible: tuple[ClientId, ...]
    pending: tuple[ClientId, ...]
    client_taus: ClientThresholdsCollection | Mapping[ClientId, ScoreValue]
    tau_global: Threshold
    score_provider: ScoreProvider
    checkpoint_round: RoundIndex | None
