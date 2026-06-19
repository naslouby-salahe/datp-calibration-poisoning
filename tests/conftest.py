from __future__ import annotations

import contextlib
import ctypes
import gc
import os

import pytest

# Disable Ray's periodic memory monitor during tests.
# RAY_memory_monitor_refresh_ms=0 disables the monitor; safe because each test
# calls ray.shutdown() via _ray_teardown_after_each_test().
# Note: RAY_memory_usage_threshold must stay <= 0.90 — enforced by resources.py.
os.environ.setdefault("RAY_memory_monitor_refresh_ms", "0")
# Opt into Ray's future default: do not override GPU visibility env vars when
# num_gpus=0 or None. Silences the FutureWarning emitted by ray.init().
os.environ.setdefault("RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO", "0")


def _release_heap() -> None:
    gc.collect()
    with contextlib.suppress(OSError, AttributeError):
        ctypes.CDLL("libc.so.6").malloc_trim(0)


@pytest.fixture(autouse=True)
def _ray_teardown_after_each_test():
    """Shut down Ray after every test, reset MLflow state, and release heap."""
    yield
    try:
        import ray

        if ray.is_initialized():
            ray.shutdown()
    except Exception:
        pass
    # End any active MLflow run left open by tracking-enabled tests (e.g. sweep
    # unit tests that call init_tracking() without a tracking_run() context).
    try:
        import mlflow

        mlflow.end_run()
    except Exception:
        pass
    # Reset datp's tracking-enabled flag so integration tests that do not call
    # init_tracking() do not inherit tracking state from earlier tests.
    try:
        import datp.core.tracking as _tracking

        _tracking._TRACKING_ENABLED = False  # noqa: SLF001
    except Exception:
        pass
    _release_heap()
