from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import contextlib
import enum
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Generic, Protocol, TypeVar

from datp.artifacts.names import ArtifactDir
from datp.core.logging import get_logger
from datp.core.metric_enums import MetricName

logger = get_logger(__name__)

_TRACKING_ENABLED = False
_MLFLOW: _MlflowModule | None = None
_PayloadItemT = TypeVar("_PayloadItemT")
TrackingValue = str | int | float | bool | enum.Enum | None


class TrackingMetricKey(enum.StrEnum):
    TRAIN_LOSS = "train_loss"
    VAL_LOSS = "val_loss"
    BEST_VAL_LOSS = "best_val_loss"
    TAU = "tau"
    TAU_GLOBAL = "tau_global"
    N_CLIENTS = "n_clients"
    EPOCHS_RUN = "epochs_run"
    CALIBRATION_PENDING_COUNT = "calibration_pending_count"
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
    POLICY = "policy"
    STAGE = "stage"
    SEED = "seed"
    ALPHA = "alpha"
    EPOCHS = "epochs"
    PATIENCE = "patience"
    LEARNING_RATE = "learning_rate"
    BATCH_SIZE = "batch_size"
    Q = "q"
    N_MIN = "n_min"
    NORMALIZATION_MODE = "normalization_mode"
    ROUNDS_MAX = "rounds_max"
    LABEL = "label"


class TrackingTagKey(enum.StrEnum):
    POLICY = "policy"
    PIPELINE = "pipeline"


@dataclass(frozen=True, slots=True)
class PolicyTrackingMetricKey:
    policy: ThresholdPolicy
    key: TrackingMetricKey


@dataclass(frozen=True, slots=True)
class TrackingMetric:
    key: TrackingMetricKey | MetricName | PolicyTrackingMetricKey
    value: float | int

    @classmethod
    def for_policy(
        cls,
        policy: ThresholdPolicy,
        key: TrackingMetricKey,
        value: float | int,
    ) -> "TrackingMetric":
        return cls(key=PolicyTrackingMetricKey(policy=policy, key=key), value=value)


@dataclass(frozen=True, slots=True)
class TrackingParam:
    key: TrackingParamKey
    value: TrackingValue


@dataclass(frozen=True, slots=True)
class TrackingTag:
    key: TrackingTagKey
    value: TrackingValue


@dataclass(frozen=True, slots=True)
class _TrackingPayload(Generic[_PayloadItemT]):
    payload: tuple[_PayloadItemT, ...] = ()


@dataclass(frozen=True, slots=True)
class TrackingMetrics(_TrackingPayload[TrackingMetric]):
    pass


@dataclass(frozen=True, slots=True)
class TrackingParams(_TrackingPayload[TrackingParam]):
    pass


@dataclass(frozen=True, slots=True)
class TrackingTags(_TrackingPayload[TrackingTag]):
    pass


class _MlflowRun(Protocol):
    """Minimal protocol for the mlflow ActiveRun context manager."""

    def __enter__(self) -> _MlflowRun: ...
    def __exit__(self, *args: object) -> None: ...


class _MlflowModule(Protocol):
    """Minimal protocol for the mlflow module methods used by tracking."""

    def set_tracking_uri(self, uri: str) -> None: ...
    def set_experiment(self, experiment_name: str) -> None: ...
    def start_run(self, *, run_name: str, nested: bool) -> _MlflowRun: ...
    def active_run(self) -> _MlflowRun | None: ...
    def log_metrics(
        self, metrics: Mapping[str, float], step: int | None = ...
    ) -> None: ...
    def log_params(self, params: Mapping[str, str]) -> None: ...
    def set_tags(self, tags: Mapping[str, str]) -> None: ...
    def log_artifact(
        self, local_path: str, artifact_path: str | None = ...
    ) -> None: ...


def _import_mlflow() -> _MlflowModule | None:
    global _MLFLOW  # noqa: PLW0603
    if _MLFLOW is not None:
        return _MLFLOW
    try:
        import mlflow  # type: ignore[import-untyped]
    except ImportError:
        return None
    _MLFLOW = mlflow  # type: ignore[assignment]
    return _MLFLOW


def init_tracking(
    *,
    experiment_name: str,
    tracking_uri: str,
) -> None:
    global _TRACKING_ENABLED  # noqa: PLW0603

    mlflow = _import_mlflow()
    if mlflow is None:
        _TRACKING_ENABLED = False
        logger.debug("mlflow unavailable; tracking disabled")
        return

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)
    _TRACKING_ENABLED = True
    logger.info(
        "tracking initialized",
        experiment_name=experiment_name,
        tracking_uri=tracking_uri,
    )


@contextlib.contextmanager
def tracking_run(
    *,
    run_name: str,
    params: TrackingParams | None,
    tags: TrackingTags | None,
) -> Generator[None, None, None]:
    if not _TRACKING_ENABLED:
        yield
        return

    mlflow = _import_mlflow()
    if mlflow is None:
        yield
        return

    nested = mlflow.active_run() is not None
    with mlflow.start_run(run_name=run_name, nested=nested):
        if tags is not None:
            tag_payload = _tags_to_mapping(tags)
            if tag_payload:
                mlflow.set_tags(tag_payload)
        if params is not None:
            param_payload = _params_to_mapping(params)
            if param_payload:
                mlflow.log_params(param_payload)
        yield


def log_metrics(
    metrics: TrackingMetrics,
    *,
    step: int | None,
    prefix: str | enum.Enum | None,
) -> None:
    if not _TRACKING_ENABLED:
        return
    mlflow = _import_mlflow()
    if mlflow is None:
        return

    payload: dict[str, float] = {}
    for metric in metrics.payload:
        key = _metric_key_to_str(metric.key)
        value = metric.value
        if not isinstance(value, (int, float)):
            continue
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            continue
        metric_key = f"{_tracking_value_to_str(prefix)}.{key}" if prefix else key
        payload[metric_key] = numeric_value

    if payload:
        mlflow.log_metrics(payload, step=step)


def log_params(params: TrackingParams) -> None:
    if not _TRACKING_ENABLED:
        return
    mlflow = _import_mlflow()
    if mlflow is None:
        return
    payload = _params_to_mapping(params)
    if payload:
        mlflow.log_params(payload)


def log_artifact(
    path: str | Path,
    *,
    artifact_path: str | ArtifactDir | None,
) -> None:
    if not _TRACKING_ENABLED:
        return
    mlflow = _import_mlflow()
    if mlflow is None:
        return
    mlflow.log_artifact(
        str(path),
        artifact_path=None
        if artifact_path is None
        else _tracking_value_to_str(artifact_path),
    )


def _params_to_mapping(params: TrackingParams) -> dict[str, str]:
    return {
        item.key.value: _tracking_value_to_str(item.value) for item in params.payload
    }


def _tags_to_mapping(tags: TrackingTags) -> dict[str, str]:
    return {item.key.value: _tracking_value_to_str(item.value) for item in tags.payload}


def _metric_key_to_str(
    key: TrackingMetricKey | MetricName | PolicyTrackingMetricKey,
) -> str:
    if isinstance(key, PolicyTrackingMetricKey):
        return f"{key.policy.value}_{key.key.value}"
    return key.value


def _tracking_value_to_str(value: TrackingValue) -> str:
    if value is None:
        return "none"
    if isinstance(value, enum.Enum):
        return str(value.value)
    return str(value)
