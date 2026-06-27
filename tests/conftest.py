"""Global test configurations and fixtures."""

from __future__ import annotations

import contextlib
import ctypes
import gc
import os

import pytest


os.environ.setdefault("RAY_memory_monitor_refresh_ms", "0")


os.environ.setdefault("RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO", "0")


def _release_heap() -> None:
    """Release heap memory by collecting garbage and trimming malloc."""
    gc.collect()
    with contextlib.suppress(OSError, AttributeError):
        ctypes.CDLL("libc.so.6").malloc_trim(0)


@pytest.fixture(autouse=True)
def _ray_teardown_after_each_test():
    """Clean up Ray cluster and tracking states after each test."""

    yield
    try:
        import ray

        if ray.is_initialized():
            ray.shutdown()
    except Exception:
        pass

    try:
        import mlflow

        mlflow.end_run()
    except Exception:
        pass

    try:
        import datp.core.tracking as _tracking

        _tracking._TRACKING_ENABLED = False
    except Exception:
        pass
    _release_heap()
