from __future__ import annotations

from typing import Annotated, NewType, TypeAlias

import enum
import math
import numpy as np
from pydantic import BeforeValidator, Field


class _Concept:
    def __init__(self, name: str) -> None:
        self.name = name


def _manifest_metric_input(value: JsonValue) -> JsonValue:
    return math.nan if value is None else value


JsonValue: TypeAlias = (
    str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
)
JsonRecord: TypeAlias = dict[str, JsonValue]

NonNegativeInt = Annotated[int, Field(ge=0)]
PositiveInt = Annotated[int, Field(gt=0)]
SignedInt = Annotated[int, _Concept("signed integer")]
NonNegativeFloat = Annotated[float, Field(ge=0)]
PositiveFloat = Annotated[float, Field(gt=0)]
UnitInterval = Annotated[float, Field(ge=0.0, le=1.0, allow_inf_nan=False)]
OpenUnitInterval = Annotated[float, Field(gt=0.0, lt=1.0, allow_inf_nan=False)]

ClientId = NewType("ClientId", str)
ClusterId = NewType("ClusterId", str)
RunId = NewType("RunId", str)
RepositoryName = NewType("RepositoryName", str)
CoverageLabel = NewType("CoverageLabel", str)
RandomSeed = NewType("RandomSeed", int)
ContentHash = Annotated[str, _Concept("content hash")]
SchemaVersion = Annotated[str, _Concept("schema version")]
ExperimentName = Annotated[str, _Concept("experiment name")]
TrackingUri = Annotated[str, _Concept("tracking uri")]
ColumnName = Annotated[str, _Concept("column name")]
RecordKey = Annotated[str, _Concept("record key")]
ArtifactName = Annotated[str, _Concept("artifact name")]
NarrativeText = Annotated[str, _Concept("narrative text")]

SampleCount = NonNegativeInt
ClientCount = NonNegativeInt
RoundCount = PositiveInt
RoundIndex = NonNegativeInt
EpochCount = PositiveInt
BatchSize = PositiveInt
FeatureCount = PositiveInt
ClusterCount = PositiveInt
ClusterIndex = NonNegativeInt
BootstrapCount = PositiveInt
BinCount = PositiveInt
IterationCount = PositiveInt
ByteCount = NonNegativeInt
Index = NonNegativeInt
WorkerCount = PositiveInt
SeedCount = NonNegativeInt
Patience = NonNegativeInt
Quantile = PositiveFloat
SignedCount = SignedInt

PoisonFraction = UnitInterval
ConfidenceLevel = UnitInterval
SignificanceLevel = OpenUnitInterval
LearningRate = PositiveFloat
DurationSeconds = NonNegativeFloat
Tolerance = NonNegativeFloat
MemoryAmount = NonNegativeFloat
GpuShare = UnitInterval
Threshold = NonNegativeFloat

FalsePositiveRate = Annotated[float, _Concept("false positive rate")]
TruePositiveRate = Annotated[float, _Concept("true positive rate")]
FalseNegativeRate = Annotated[float, _Concept("false negative rate")]
TrueNegativeRate = Annotated[float, _Concept("true negative rate")]
ClassificationScore = Annotated[float, _Concept("classification score")]
SignedDelta = Annotated[float, _Concept("signed delta")]
Probability = Annotated[float, _Concept("probability")]
IntervalBound = Annotated[float, _Concept("interval bound")]
ScoreValue = Annotated[float, _Concept("score")]
Ratio = Annotated[float, _Concept("ratio")]

ScoreVector: TypeAlias = np.ndarray
FeatureMatrix: TypeAlias = np.ndarray
ParameterVector: TypeAlias = np.ndarray

ManifestMetricValue = Annotated[float, BeforeValidator(_manifest_metric_input)]
TrackingNumber: TypeAlias = int | float
TrackingValue: TypeAlias = str | int | float | bool | enum.Enum | None
