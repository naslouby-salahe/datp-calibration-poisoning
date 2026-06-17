from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from pydantic import BaseModel, ConfigDict

from datp.config.models import DatpConfig
from datp.core.enums import Baseline
from datp.core.identity import TrainingCellId
from datp.experiments.enums import ContingencyDecision

if TYPE_CHECKING:
    from datp.scoring.loading import ScoreProvider


@dataclass(frozen=True, slots=True)
class PipelineRequest:
    key: TrainingCellId
    baseline: Baseline
    cfg: DatpConfig
    base_dir: Path
    prepared_dir: Path
    checkpoint_round: int | None


@dataclass(slots=True)
class SharedPipelineContext:
    """B1/B2/B3/B4 share this context within one (regime, seed, alpha) group; all baselines read from the same ScoreProvider."""

    key: TrainingCellId
    client_errors: dict[str, np.ndarray]
    eligible: list[str]
    pending: list[str]
    client_taus: dict[str, float]
    tau_global: float
    score_provider: ScoreProvider
    checkpoint_round: int | None


class ContingencyRecord(BaseModel):
    """Preliminary single-seed diagnostic result; final primary endpoint is Regime A B1-vs-B2 CV(FPR) bootstrap CI."""

    model_config = ConfigDict(frozen=True)
    decision: ContingencyDecision
    cv_fpr_b1: float
    cv_fpr_b2: float
    delta_cv_fpr: float
    dispersion_threshold: float
    rationale: str
    is_preliminary_diagnostic: bool = True
