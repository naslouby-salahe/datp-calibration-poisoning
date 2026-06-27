"""MLflow-based experiment tracking with typed metric, param, and tag payloads."""

from __future__ import annotations

import contextlib
import enum
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Generic, Mapping, Protocol, TypeVar

from datp.artifacts.names import ArtifactDir
from datp.core.enums import MetricName, ThresholdPolicy
from datp.core.logging import get_logger

logger = get_logger(__name__)

_TRACKING_ENABLED = False
_MLFLOW: _MlflowModule | None = None
_PayloadItemT = TypeVar("_PayloadItemT")
TrackingValue = str | int | float | bool | enum.Enum | None


class TrackingMetricKey(enum.StrEnum):
    """Well-known metric keys for MLflow tracking."""

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
    """Well-known parameter keys for MLflow tracking."""

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
    """Well-known tag keys for MLflow tracking."""

    POLICY = "policy"
    PIPELINE = "pipeline"


@dataclass(frozen=True, slots=True)
class PolicyTrackingMetricKey:
    """A composite metric key scoped to a specific threshold policy."""

    policy: ThresholdPolicy
    key: TrackingMetricKey


@dataclass(frozen=True, slots=True)
class TrackingMetric:
    """A named metric value for MLflow logging, optionally scoped to a threshold policy."""

    key: TrackingMetricKey | MetricName | PolicyTrackingMetricKey
    value: float | int

    @classmethod
    def for_policy(
        cls, policy: ThresholdPolicy, key: TrackingMetricKey, value: float | int
    ) -> "TrackingMetric":
        """Create a policy-scoped tracking metric."""
        return cls(key=PolicyTrackingMetricKey(policy=policy, key=key), value=value)


@dataclass(frozen=True, slots=True)
class TrackingParam:
    """A named parameter key-value pair for MLflow logging."""

    key: TrackingParamKey
    value: TrackingValue


@dataclass(frozen=True, slots=True)
class TrackingTag:
    """A named tag key-value pair for MLflow logging."""

    key: TrackingTagKey
    value: TrackingValue


@dataclass(frozen=True, slots=True)
class _TrackingPayload(Generic[_PayloadItemT]):
    """Generic wrapper holding a tuple of typed tracking items for batch submission."""

    payload: tuple[_PayloadItemT, ...] = ()


@dataclass(frozen=True, slots=True)
class TrackingMetrics(_TrackingPayload[TrackingMetric]):
    """A batch of TrackingMetric items for MLflow metric logging."""


@dataclass(frozen=True, slots=True)
class TrackingParams(_TrackingPayload[TrackingParam]):
    """A batch of TrackingParam items for MLflow parameter logging."""


@dataclass(frozen=True, slots=True)
class TrackingTags(_TrackingPayload[TrackingTag]):
    """A batch of TrackingTag items for MLflow tag logging."""


class _MlflowRun(Protocol):
    """Protocol describing the MLflow run context manager interface."""

    def __enter__(self) -> _MlflowRun: ...
    def __exit__(self, *args: object) -> None: ...


class _MlflowModule(Protocol):
    """Protocol describing the minimal MLflow module surface used by the tracking layer."""

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
    """Lazily import and cache the mlflow module."""
    global _MLFLOW  # noqa: PLW0603
    if _MLFLOW is not None:
        return _MLFLOW
    try:
        import mlflow  # type: ignore[import-untyped]

        _MLFLOW = mlflow  # type: ignore[assignment]
        return _MLFLOW
    except ImportError:
        return None


def _active_mlflow() -> _MlflowModule | None:
    """Return the mlflow module only when tracking is enabled."""
    return _import_mlflow() if _TRACKING_ENABLED else None


def _str_mapping_from_payload(
    items: tuple[TrackingParam, ...] | tuple[TrackingTag, ...],
) -> dict[str, str]:
    """Convert a payload of params or tags to a string-to-string mapping."""
    return {
        item.key.value: str(
            item.value.value
            if isinstance(item.value, enum.Enum)
            else (item.value or "none")
        )
        for item in items
    }


def init_tracking(*, experiment_name: str, tracking_uri: str) -> None:
    """Initialize MLflow tracking; silently disable if mlflow is not importable."""
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
    *, run_name: str, params: TrackingParams | None, tags: TrackingTags | None
) -> Generator[None, None, None]:
    """Context manager that starts an MLflow run with optional params and tags."""
    mlflow = _active_mlflow()
    if mlflow is None:
        yield
        return

    with mlflow.start_run(run_name=run_name, nested=mlflow.active_run() is not None):
        if tags and (payload := _str_mapping_from_payload(tags.payload)):
            mlflow.set_tags(payload)
        if params and (payload := _str_mapping_from_payload(params.payload)):
            mlflow.log_params(payload)
        yield


def log_metrics(
    metrics: TrackingMetrics, *, step: int | None, prefix: str | enum.Enum | None
) -> None:
    """Log a batch of tracking metrics to MLflow, filtering non-finite values."""
    if not (mlflow := _active_mlflow()):
        return

    payload: dict[str, float] = {}
    if prefix:
        pfx_str = str(prefix.value) if isinstance(prefix, enum.Enum) else str(prefix)
    else:
        pfx_str = ""

    for metric in metrics.payload:
        if not isinstance(metric.value, (int, float)) or not math.isfinite(
            float(metric.value)
        ):
            continue
        k = (
            f"{metric.key.policy.value}_{metric.key.key.value}"
            if isinstance(metric.key, PolicyTrackingMetricKey)
            else metric.key.value
        )
        payload[f"{pfx_str}.{k}" if prefix else k] = float(metric.value)

    if payload:
        mlflow.log_metrics(payload, step=step)


def log_params(params: TrackingParams) -> None:
    """Log a batch of tracking parameters to MLflow."""
    if (mlflow := _active_mlflow()) and (
        payload := _str_mapping_from_payload(params.payload)
    ):
        mlflow.log_params(payload)


def log_artifact(path: Path, *, artifact_path: str | ArtifactDir | None) -> None:
    """Log a file artifact to the active MLflow run."""
    if mlflow := _active_mlflow():
        if artifact_path:
            p: str | None = (
                str(artifact_path.value)
                if isinstance(artifact_path, enum.Enum)
                else str(artifact_path)
            )
        else:
            p = None
        mlflow.log_artifact(str(path), artifact_path=p)
