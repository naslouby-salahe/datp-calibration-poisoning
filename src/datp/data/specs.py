from __future__ import annotations

from datp.types import (
    ColumnName,
    FeatureCount,
    NarrativeText,
    Ratio,
    SampleCount,
)


import enum
from dataclasses import dataclass
from typing import Mapping

from datp.core.enums import (
    DatasetID,
    NBaIoTAttackFamily,
    NBaIoTDevice,
    NBaIoTDeviceFamily,
)


class SplitPolicyRole(enum.StrEnum):

    TRAIN = "train"
    GAP1 = "gap1"
    CAL = "cal"
    GAP2 = "gap2"
    TEST_BENIGN = "test_benign"


@dataclass(frozen=True, slots=True)
class SplitPolicy:

    ratios: Mapping[SplitPolicyRole, Ratio]


@dataclass(frozen=True, slots=True)
class DatasetSpec:

    id: DatasetID
    display_name: NarrativeText
    processed_slug: NarrativeText
    feature_count: FeatureCount
    feature_columns: tuple[ColumnName, ...] | None
    label_column: ColumnName | None
    benign_label: NarrativeText | None
    raw_root_slug: NarrativeText
    split_policy: SplitPolicy
    family_map: Mapping[NBaIoTDevice, NBaIoTDeviceFamily] | None = None
    device_ids: tuple[NBaIoTDevice, ...] = ()
    attack_family_dirs: tuple[NBaIoTAttackFamily, ...] = ()
    expected_client_count: SampleCount | None = None
