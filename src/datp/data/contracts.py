from __future__ import annotations

from datp.types import (
    NarrativeText,
    SampleCount,
    SignedCount,
)


from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from datp.core.enums import ClientStatus
from datp.data.specs import SplitPolicyRole


class PartitionResult(BaseModel):

    model_config = ConfigDict(frozen=True)
    benign_train_count: SampleCount
    benign_cal_count: SampleCount
    test_benign_count: SampleCount
    test_attack_count: SampleCount
    status: ClientStatus
    evaluation_incomplete: bool = False
    attack_classes: list[NarrativeText] = Field(default_factory=list)
    attack_categories: list[NarrativeText] = Field(default_factory=list)
    total_benign_pre_cap: Optional[SignedCount] = None
    total_attack_pre_cap: Optional[SignedCount] = None
    split_indices: Optional[dict[SplitPolicyRole, tuple[SignedCount, SignedCount]]] = None
