from __future__ import annotations

from datp.types import NarrativeText


from functools import cache

from datp.config.models import ExperimentStage
from datp.core.enums import DatasetID
from datp.data.specs import DatasetSpec, SplitPolicy, SplitPolicyRole

__all__ = [
    "DatasetID",
    "DatasetSpec",
    "SplitPolicy",
    "SplitPolicyRole",
    "dataset_display_name",
    "dataset_for_stage",
    "dataset_processed_slug",
    "dataset_spec",
    "spec_for_stage",
]


@cache
def dataset_spec(dataset_id: DatasetID) -> DatasetSpec:
    from datp.data.datasets.nbaiot.spec import NBAIOT_SPEC

    return {DatasetID.NBAIOT: NBAIOT_SPEC}[dataset_id]


def dataset_display_name(dataset_id: DatasetID) -> NarrativeText:
    return dataset_spec(dataset_id).display_name


def dataset_processed_slug(dataset_id: DatasetID) -> NarrativeText:
    return dataset_spec(dataset_id).processed_slug


_STAGE_DATASET = {
    ExperimentStage.NBAIOT_MAIN: DatasetID.NBAIOT,
    ExperimentStage.NBAIOT_FULL_OPTIONAL: DatasetID.NBAIOT,
    ExperimentStage.SYNTHETIC_SMOKE: DatasetID.NBAIOT,
    ExperimentStage.FINAL_AUDIT: DatasetID.NBAIOT,
}


def dataset_for_stage(stage: ExperimentStage) -> DatasetID:
    return _STAGE_DATASET[stage]


def spec_for_stage(stage: ExperimentStage) -> DatasetSpec:
    return dataset_spec(dataset_for_stage(stage))
