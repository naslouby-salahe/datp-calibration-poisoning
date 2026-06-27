"""Structured result types for data partitioning."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PartitionResult(BaseModel):
    """Counts and flags produced after partitioning a single client's data."""

    model_config = ConfigDict(frozen=True)
    benign_train_count: int
    benign_cal_count: int
    test_benign_count: int
    test_attack_count: int
    calibration_pending: bool
    evaluation_incomplete: bool = False
    attack_classes: list[str] = Field(default_factory=list)
    attack_categories: list[str] = Field(default_factory=list)
    total_benign_pre_cap: Optional[int] = None
    total_attack_pre_cap: Optional[int] = None
    split_indices: Optional[dict[str, tuple[int, int]]] = None
