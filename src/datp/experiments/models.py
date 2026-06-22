from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from pydantic import BaseModel, ConfigDict

from datp.config.models import DatpConfig
from datp.core.identity import TrainingCellId
from datp.experiments.enums import ContingencyDecision
from datp.thresholding.eligibility import ClientThresholdsCollection

if TYPE_CHECKING:
    from datp.scoring.loading import ScoreProvider


@dataclass(frozen=True, slots=True)
class PipelineRequest:
    key: TrainingCellId
    policy: ThresholdPolicy
    cfg: DatpConfig
    base_dir: Path
    prepared_dir: Path
    checkpoint_round: int | None


@dataclass(slots=True)
class SharedPipelineContext:
    """All threshold policies share this context within one (stage, seed) group; all policies read from the same ScoreProvider."""

    key: TrainingCellId
    client_errors: dict[str, np.ndarray]
    eligible: list[str]
    pending: list[str]
    client_taus: ClientThresholdsCollection | Mapping[str, float]
    tau_global: float
    score_provider: ScoreProvider
    checkpoint_round: int | None


class ContingencyRecord(BaseModel):
    """Preliminary single-seed diagnostic result; final primary endpoint is GLOBAL_THRESHOLD vs LOCAL_THRESHOLD CV(FPR) bootstrap CI."""

    model_config = ConfigDict(frozen=True)
    decision: ContingencyDecision
    cv_fpr_global: float
    cv_fpr_local: float
    delta_cv_fpr: float
    dispersion_threshold: float
    rationale: str
    is_preliminary_diagnostic: bool = True
