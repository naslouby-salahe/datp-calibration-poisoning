"""Shared experiment models: sweep steps, pipeline requests, and contingency records."""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from pydantic import BaseModel, ConfigDict

from datp.config.models import DatpConfig
from datp.core.enums import ThresholdPolicy
from datp.core.identity import TrainingCellId
from datp.thresholding.eligibility import ClientThresholdsCollection

if TYPE_CHECKING:
    from datp.scoring.loading import ScoreProvider


class SweepStep(enum.StrEnum):
    """Sweep pipeline steps from matrix building through completion."""

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


class ContingencyDecision(enum.StrEnum):
    """Contingency outcomes: go or fall back to contingency path."""

    GO = "go"
    CONTINGENCY = "contingency"


class PolicyRunStatus(enum.StrEnum):
    """Policy run status: done, skipped, or failed."""

    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PipelineRequest:
    """Immutable request carrying training cell key, policy, config, and directory paths."""

    key: TrainingCellId
    policy: ThresholdPolicy
    cfg: DatpConfig
    base_dir: Path
    prepared_dir: Path
    checkpoint_round: int | None


@dataclass(slots=True)
class SharedPipelineContext:
    """Mutable shared context holding per-cell calibration data, eligibility, and score provider."""

    key: TrainingCellId
    client_errors: dict[str, np.ndarray]
    eligible: list[str]
    pending: list[str]
    client_taus: ClientThresholdsCollection | Mapping[str, float]
    tau_global: float
    score_provider: ScoreProvider
    checkpoint_round: int | None


class ContingencyRecord(BaseModel):
    """Frozen record of a contingency decision with CV-FPR deltas and rationale."""

    model_config = ConfigDict(frozen=True)
    decision: ContingencyDecision
    cv_fpr_global: float
    cv_fpr_local: float
    delta_cv_fpr: float
    dispersion_threshold: float
    rationale: str
    is_preliminary_diagnostic: bool = True
