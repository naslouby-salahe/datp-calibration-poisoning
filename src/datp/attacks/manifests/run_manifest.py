"""Run-manifest model for individual poisoning-run provenance."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from datp.attacks.constants import DDOF_CV, EPS_NUM, THRESHOLD_QUANTILE
from datp.attacks.enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.provenance import git_commit
from datp.core.seeds import SeedRecord

SPLIT_SEMANTICS = "chronological_benign_only_60_1_20_1_18"  # train/val/cal/test split ratios encoded as pct_pct_pct_pct
RESERVOIR_MODE = "victim_local_benign_cal_source_precedence_rule_2"  # Reservoir draws from victim-local benign calibration scores


class ProvenanceRecord(BaseModel):
    """Provenance metadata for a single poisoning run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    local_epochs: int
    pipeline_generated: bool = True
    repository: str
    code_commit: str = Field(default_factory=git_commit)
    checkpoint_round: int | None = None
    split_semantics: str = SPLIT_SEMANTICS

    @field_validator("local_epochs")
    @classmethod
    def enforce_e1(cls, v: int) -> int:
        """Validate that local_epochs equals 1."""
        if v != 1:
            raise ValueError(
                f"provenance.local_epochs must be 1; got {v} — E={v} rejected"
            )
        return v


class RunManifest(BaseModel):
    """Provenance-bearing manifest for a single poisoning run with full configuration trace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1"
    dataset: str
    stage: ExperimentStage
    policy: ThresholdPolicy
    objective: AttackerObjective
    source: PoisoningSourceStrategy
    injection_rule: CalibrationInjectionRule = (
        CalibrationInjectionRule.REPLACE_FIXED_BUDGET
    )
    fraction: float
    target_scope: PoisoningTargetScope
    training_seed: int
    poisoning_seed: int
    client_idx: int
    scope_idx: int

    provenance: ProvenanceRecord
    reservoir_mode: str = RESERVOIR_MODE
    mu_flag_threshold: float | None
    seed_record: SeedRecord

    threshold_quantile_q: float = THRESHOLD_QUANTILE
    eps_num: float = EPS_NUM
    ddof: int = DDOF_CV
    generated_at_utc: str
