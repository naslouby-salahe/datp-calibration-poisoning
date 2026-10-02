from __future__ import annotations

from datp.types import (
    ArtifactName,
    ColumnName,
    ExperimentName,
    JsonValue,
    NarrativeText,
    RecordKey,
    ScoreValue,
    SignedCount,
    TrackingNumber,
    TrackingUri,
    TrackingValue,
)


import contextlib
import enum
import importlib
import math
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from contextvars import ContextVar
from types import ModuleType
from typing import Generator, Mapping, Protocol, Sequence, cast

from datp.artifacts.names import ArtifactDir
from datp.core.enums import MetricName, ThresholdPolicy
from datp.core.logging import get_logger

logger = get_logger(__name__)

_TRACKING_ENABLED = ContextVar("tracking_enabled", default=False)


class TrackingMetricKey(enum.StrEnum):

    TAU_GLOBAL = "tau_global"
    SWEEP_TOTAL = "sweep_total"
    SWEEP_COMPLETED = "sweep_completed"
    SWEEP_SKIPPED = "sweep_skipped"
    SWEEP_FAILED = "sweep_failed"
    SWEEP_ELAPSED_S = "sweep_elapsed_s"
    CONVERGED_ROUND = "converged_round"
    TOTAL_ROUNDS = "total_rounds"
    ELIGIBLE = "eligible"
    PENDING = "pending"


class TrackingParamKey(enum.StrEnum):

    STAGE = "stage"
    SEED = "seed"
    ROUNDS_MAX = "rounds_max"
    LABEL = "label"


@dataclass(frozen=True, slots=True)
class PolicyTrackingMetricKey:

    policy: ThresholdPolicy
    key: TrackingMetricKey


@dataclass(frozen=True, slots=True)
class TrackingMetric:

    key: TrackingMetricKey | MetricName | PolicyTrackingMetricKey
    value: TrackingNumber

    @classmethod
    def for_policy(
        cls, policy: ThresholdPolicy, key: TrackingMetricKey, value: TrackingNumber
    ) -> "TrackingMetric":
        return cls(key=PolicyTrackingMetricKey(policy=policy, key=key), value=value)


@dataclass(frozen=True, slots=True)
class TrackingParam:

    key: TrackingParamKey
    value: TrackingValue


class _MlflowRun(Protocol):

    def __enter__(self) -> _MlflowRun: ...
    def __exit__(self, *args: JsonValue) -> None: ...


class _MlflowModule(Protocol):

    def set_tracking_uri(self, uri: TrackingUri) -> None: ...
    def set_experiment(self, experiment_name: ExperimentName) -> None: ...
    def start_run(self, *, run_name: ExperimentName, nested: bool) -> _MlflowRun: ...
    def active_run(self) -> _MlflowRun | None: ...
    def log_metrics(
        self, metrics: Mapping[ColumnName, ScoreValue], step: SignedCount | None = ...
    ) -> None: ...
    def log_params(self, params: Mapping[RecordKey, NarrativeText]) -> None: ...
    def set_tags(self, tags: Mapping[RecordKey, NarrativeText]) -> None: ...
    def log_artifact(
        self, local_path: ArtifactName, artifact_path: ArtifactName | None = ...
    ) -> None: ...


@cache
def _import_mlflow() -> _MlflowModule | None:
    try:
        module: ModuleType = importlib.import_module("mlflow")
    except ImportError:
        return None
    return cast(_MlflowModule, module)


def _active_mlflow() -> _MlflowModule | None:
    return _import_mlflow() if _TRACKING_ENABLED.get() else None


def _external_text(value: TrackingValue) -> NarrativeText:
    if isinstance(value, enum.Enum):
        return str(value.value)
    return str(value or "none")


def _str_mapping_from_payload(
    items: Sequence[TrackingParam],
) -> dict[RecordKey, NarrativeText]:
    return {str(item.key): _external_text(item.value) for item in items}


def init_tracking(*, experiment_name: ExperimentName, tracking_uri: TrackingUri) -> None:
    mlflow = _import_mlflow()
    if mlflow is None:
        _TRACKING_ENABLED.set(False)
        logger.debug("mlflow unavailable; tracking disabled")
        return

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)
    _TRACKING_ENABLED.set(True)
    logger.info(
        "tracking initialized",
        experiment_name=experiment_name,
        tracking_uri=tracking_uri,
    )


@contextlib.contextmanager
def tracking_run(
    *,
    run_name: ExperimentName,
    params: Sequence[TrackingParam] | None,
) -> Generator[None, None, None]:
    mlflow = _active_mlflow()
    if mlflow is None:
        yield
        return

    with mlflow.start_run(run_name=run_name, nested=mlflow.active_run() is not None):
        if params and (payload := _str_mapping_from_payload(params)):
            mlflow.log_params(payload)
        yield


def log_metrics(
    metrics: Sequence[TrackingMetric],
    *,
    step: SignedCount | None,
    prefix: NarrativeText | enum.Enum | None,
) -> None:
    if not (mlflow := _active_mlflow()):
        return

    payload: dict[str, float] = {}
    if prefix:
        pfx_str = str(prefix.value) if isinstance(prefix, enum.Enum) else str(prefix)
    else:
        pfx_str = ""

    for metric in metrics:
        value = _finite_metric_value(metric.value)
        if value is None:
            continue
        if isinstance(metric.key, PolicyTrackingMetricKey):
            k = f"{metric.key.policy}_{metric.key.key}"
        else:
            k = str(metric.key)
        payload[f"{pfx_str}.{k}" if prefix else k] = value

    if payload:
        mlflow.log_metrics(payload, step=step)


def _finite_metric_value(value: TrackingValue) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    numeric_value = float(value)
    return numeric_value if math.isfinite(numeric_value) else None


def log_params(params: Sequence[TrackingParam]) -> None:
    if (mlflow := _active_mlflow()) and (payload := _str_mapping_from_payload(params)):
        mlflow.log_params(payload)


def log_artifact(path: Path, *, artifact_path: ArtifactName | ArtifactDir | None) -> None:
    if mlflow := _active_mlflow():
        if artifact_path:
            p = str(artifact_path.value) if isinstance(artifact_path, enum.Enum) else str(artifact_path)
        else:
            p = None
        mlflow.log_artifact(str(path), artifact_path=p)
