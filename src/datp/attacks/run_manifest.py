"""run manifest schema.

Every experiment cell writes one manifest that records provenance (E=1,
split semantics, checkpoint round), reservoir mode, locked mu_flag_threshold,
and the SeedSequence entropy so any run can be reproduced exactly.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from datp.attacks.poison_enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    ExperimentScale,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)
from datp.core.seed_sequence import SeedRecord

# Canonical split description — do not vary; this locks split semantics.
SPLIT_SEMANTICS: str = "chronological_benign_only_60_1_20_1_18"

# Canonical reservoir description for source-precedence rule 2.
RESERVOIR_MODE: str = "victim_local_benign_cal_source_precedence_rule_2"


class ProvenanceRecord(BaseModel):
    """Provenance fields recorded in every manifest.

    E=1 is enforced; E=5 is rejected at validation time.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    local_epochs: int
    pipeline_generated: bool = True
    repository: str
    checkpoint_round: int | None = None
    split_semantics: str = SPLIT_SEMANTICS

    @field_validator("local_epochs")
    @classmethod
    def enforce_e1(cls, v: int) -> int:
        if v != 1:
            raise ValueError(
                f"provenance.local_epochs must be 1; got {v} — E={v} rejected"
            )
        return v


class SeedRecordModel(BaseModel):
    """Pydantic-serializable mirror of SeedRecord for manifest embedding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    training_seed: int
    poisoning_seed: int
    client_idx: int
    scope_idx: int
    entropy: tuple[int, int, int, int]

    @classmethod
    def from_record(cls, record: SeedRecord) -> "SeedRecordModel":
        return cls(
            training_seed=record.training_seed,
            poisoning_seed=record.poisoning_seed,
            client_idx=record.client_idx,
            scope_idx=record.scope_idx,
            entropy=record.entropy,
        )

    def to_record(self) -> SeedRecord:
        return SeedRecord(
            training_seed=self.training_seed,
            poisoning_seed=self.poisoning_seed,
            client_idx=self.client_idx,
            scope_idx=self.scope_idx,
        )


class RunManifest(BaseModel):
    """Manifest for one experiment cell.

    Written before any poisoned run begins. Records all parameters needed to
    reproduce the run and verify provenance.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1"

    # Cell identification
    dataset: str
    scale: ExperimentScale
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

    # Provenance — E=1 enforced, E=5 rejected inside ProvenanceRecord.
    provenance: ProvenanceRecord

    # Reservoir mode — must be victim-local.
    reservoir_mode: str = RESERVOIR_MODE

    # mu_flag_threshold — None until computed from clean artifacts; must be
    # locked (non-None) before any poisoned run reads results.
    mu_flag_threshold: float | None

    # Every derived child seed recorded for reproducibility.
    seed_record: SeedRecordModel

    # ISO-8601 UTC timestamp.
    generated_at_utc: str
