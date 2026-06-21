from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PartitionResult(BaseModel):
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


class CiciotClientSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    client_id: str
    train_count: int
    cal_count: int
    test_benign_count: int
    test_attack_count: int
    calibration_pending: bool
    device_mixture_proportions: dict[str, float] = Field(default_factory=dict)


class CiciotResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    alpha: float
    seed: int
    n_clients: int
    js_divergence: float | None
    n_eligible: int
    n_calibration_pending: int
    coverage: str
    clients: list[CiciotClientSummary]
