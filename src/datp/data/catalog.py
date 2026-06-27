"""Dataset catalog: spec lookup and stage-to-dataset mapping."""

from __future__ import annotations

from functools import cache

from datp.config.models import ExperimentStage
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


@cache
def dataset_spec(dataset_id: DatasetID) -> DatasetSpec:
    """Return the cached DatasetSpec for a known dataset."""
    from datp.data.datasets.nbaiot.spec import NBAIOT_SPEC

    return {DatasetID.NBAIOT: NBAIOT_SPEC}[dataset_id]


def dataset_display_name(dataset_id: DatasetID) -> str:
    """Return the human-readable display name for a dataset."""
    return dataset_spec(dataset_id).display_name


def dataset_processed_slug(dataset_id: DatasetID) -> str:
    """Return the filesystem slug for a processed dataset."""
    return dataset_spec(dataset_id).processed_slug


_STAGE_DATASET = {
    ExperimentStage.NBAIOT_MAIN: DatasetID.NBAIOT,
    ExperimentStage.NBAIOT_FULL_OPTIONAL: DatasetID.NBAIOT,
    ExperimentStage.SYNTHETIC_SMOKE: DatasetID.NBAIOT,
    ExperimentStage.FINAL_AUDIT: DatasetID.NBAIOT,
}


def dataset_for_stage(stage: ExperimentStage) -> DatasetID:
    """Map an experiment stage to its canonical dataset."""
    return _STAGE_DATASET[stage]


def spec_for_stage(stage: ExperimentStage) -> DatasetSpec:
    """Return the full DatasetSpec for an experiment stage."""
    return dataset_spec(dataset_for_stage(stage))
