from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Mapping

from datp.config.stages import ExperimentStage
from datp.core.enums import ClientIdentity, DatasetID


@dataclass(frozen=True, slots=True)
class RawLayout:
    root_slug: str


class SplitPolicyKind(enum.StrEnum):
    CHRONOLOGICAL_GAPPED = "chronological_gapped"
    STRATIFIED_RANDOM = "stratified_random"


class SplitPolicyRole(enum.StrEnum):
    TRAIN = "train"
    GAP1 = "gap1"
    CAL = "cal"
    GAP2 = "gap2"
    TEST_BENIGN = "test_benign"


class CapStrategy(enum.StrEnum):
    ATTACK_PRESERVING = "attack_preserving"


@dataclass(frozen=True, slots=True)
class SplitPolicy:
    name: SplitPolicyKind
    calibration_benign_only: bool
    chronological: bool
    contiguous_gaps: bool
    ratios: Mapping[SplitPolicyRole, float]


@dataclass(frozen=True, slots=True)
class CapPolicy:
    total: int
    attack_reserve: int
    strategy: CapStrategy


@dataclass(frozen=True, slots=True)
class DatasetSpec:
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


_DATASETS: dict[DatasetID, DatasetSpec] | None = None


def _get_datasets() -> Mapping[DatasetID, DatasetSpec]:
    global _DATASETS
    if _DATASETS is None:
        from datp.data.datasets.ciciot2023.spec import CICIOT2023_SPEC  # noqa: PLC0415
        from datp.data.datasets.nbaiot.spec import NBAIOT_SPEC  # noqa: PLC0415

        _DATASETS = {
            DatasetID.NBAIOT: NBAIOT_SPEC,
            DatasetID.CICIOT2023: CICIOT2023_SPEC,
        }
    return _DATASETS


def dataset_spec(dataset_id: DatasetID) -> DatasetSpec:
    return _get_datasets()[dataset_id]


def dataset_display_name(dataset_id: DatasetID) -> str:
    return dataset_spec(dataset_id).display_name


def dataset_processed_slug(dataset_id: DatasetID) -> str:
    return dataset_spec(dataset_id).processed_slug


_STAGE_DATASET: dict[ExperimentStage, DatasetID] = {
    ExperimentStage.NBAIOT_MAIN: DatasetID.NBAIOT,
    ExperimentStage.NBAIOT_FULL_OPTIONAL: DatasetID.NBAIOT,
    ExperimentStage.STRETCH_DIAGNOSTIC_ONLY: DatasetID.CICIOT2023,
    ExperimentStage.SYNTHETIC_SMOKE: DatasetID.NBAIOT,
    ExperimentStage.FINAL_AUDIT: DatasetID.NBAIOT,
}


def dataset_for_stage(stage: ExperimentStage) -> DatasetID:
    return _STAGE_DATASET[stage]


def spec_for_stage(stage: ExperimentStage) -> DatasetSpec:
    return dataset_spec(dataset_for_stage(stage))
