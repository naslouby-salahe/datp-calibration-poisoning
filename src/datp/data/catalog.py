from __future__ import annotations

from typing import Mapping

from datp.config.stages import ExperimentStage
from datp.core.enums import ClientIdentity, DatasetID
from datp.data.specs import (
    CapPolicy,
    CapStrategy,
    DatasetSpec,
    RawLayout,
    SplitPolicy,
    SplitPolicyKind,
    SplitPolicyRole,
)

__all__ = [
    "CapPolicy",
    "CapStrategy",
    "ClientIdentity",
    "DatasetID",
    "DatasetSpec",
    "RawLayout",
    "SplitPolicy",
    "SplitPolicyKind",
    "SplitPolicyRole",
    "dataset_display_name",
    "dataset_for_stage",
    "dataset_processed_slug",
    "dataset_spec",
    "spec_for_stage",
]


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
