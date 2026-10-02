from __future__ import annotations

from datp.types import NarrativeText, RepositoryName, RoundCount, RoundIndex


from pydantic import BaseModel, ConfigDict, Field, field_validator

from datp.attacks.enums import SplitSemantics
from datp.core.provenance import git_commit


class ProvenanceRecord(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True)

    local_epochs: RoundCount
    pipeline_generated: bool = True
    repository: RepositoryName
    code_commit: NarrativeText = Field(default_factory=git_commit)
    checkpoint_round: RoundIndex | None = None
    split_semantics: SplitSemantics = SplitSemantics.CHRONOLOGICAL_BENIGN_ONLY_60_1_20_1_18

    @field_validator("local_epochs")
    @classmethod
    def enforce_e1(cls, v: RoundCount) -> RoundCount:
        if v != 1:
            raise ValueError(
                f"provenance.local_epochs must be 1; got {v} — E={v} rejected"
            )
        return v
