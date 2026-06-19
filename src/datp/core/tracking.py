from __future__ import annotations

import contextlib
import math
from pathlib import Path
from typing import Generator, Protocol

from datp.core.logging import get_logger

logger = get_logger(__name__)

_TRACKING_ENABLED = False
_MLFLOW: _MlflowModule | None = None


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
        self, metrics: dict[str, float], step: int | None = ...
    ) -> None: ...
    def log_params(self, params: dict[str, str]) -> None: ...
    def set_tags(self, tags: dict[str, str]) -> None: ...
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
    params: dict[str, str] | None,
    tags: dict[str, str] | None,
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
        if tags:
            mlflow.set_tags(tags)
        if params:
            mlflow.log_params(params)
        yield


def log_metrics(
    metrics: dict[str, float | int],
    *,
    step: int | None,
    prefix: str | None,
) -> None:
    if not _TRACKING_ENABLED:
        return
    mlflow = _import_mlflow()
    if mlflow is None:
        return

    payload: dict[str, float] = {}
    for key, value in metrics.items():
        if not isinstance(value, (int, float)):
            continue
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            continue
        metric_key = f"{prefix}.{key}" if prefix else key
        payload[metric_key] = numeric_value

    if payload:
        mlflow.log_metrics(payload, step=step)


def log_params(params: dict[str, str]) -> None:
    if not _TRACKING_ENABLED:
        return
    mlflow = _import_mlflow()
    if mlflow is None:
        return
    mlflow.log_params(params)


def log_artifact(
    path: str | Path,
    *,
    artifact_path: str | None,
) -> None:
    if not _TRACKING_ENABLED:
        return
    mlflow = _import_mlflow()
    if mlflow is None:
        return
    mlflow.log_artifact(str(path), artifact_path=artifact_path)
