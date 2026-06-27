"""Dataset specification types: split policies, cap policies, and layout."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Mapping

from datp.core.enums import ClientIdentity, DatasetID


@dataclass(frozen=True, slots=True)
class RawLayout:
    """Filesystem layout descriptor for a raw dataset."""

    root_slug: str


class SplitPolicyKind(enum.StrEnum):
    """Kinds of split strategies."""

    CHRONOLOGICAL_GAPPED = "chronological_gapped"
    STRATIFIED_RANDOM = "stratified_random"


class SplitPolicyRole(enum.StrEnum):
    """Roles a split can serve in the data pipeline."""

    TRAIN = "train"
    GAP1 = "gap1"
    CAL = "cal"
    GAP2 = "gap2"
    TEST_BENIGN = "test_benign"


class CapStrategy(enum.StrEnum):
    """Strategies for capping dataset sizes."""

    ATTACK_PRESERVING = "attack_preserving"


@dataclass(frozen=True, slots=True)
class SplitPolicy:
    """Configuration governing how a dataset is split."""

    name: SplitPolicyKind
    calibration_benign_only: bool
    chronological: bool
    contiguous_gaps: bool
    ratios: Mapping[SplitPolicyRole, float]


@dataclass(frozen=True, slots=True)
class CapPolicy:
    """Policy for capping the total number of samples."""

    total: int
    attack_reserve: int
    strategy: CapStrategy


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    """Complete specification for a dataset used in experiments."""

    id: DatasetID
    display_name: str
    processed_slug: str
    feature_count: int
    feature_columns: tuple[str, ...] | None
    label_column: str | None
    benign_label: str | None
    client_identity: ClientIdentity
    raw_layout: RawLayout
    split_policy: SplitPolicy
    cap_policy: CapPolicy | None = None
    family_map: Mapping[str, str] | None = None
    device_ids: tuple[str, ...] = ()
    attack_family_dirs: tuple[str, ...] = ()
    expected_client_count: int | None = None
