"""Global test configurations and fixtures."""

from __future__ import annotations

import gc
import os
import sys

import pytest

os.environ.setdefault("RAY_memory_monitor_refresh_ms", "0")


os.environ.setdefault("RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO", "0")


@pytest.fixture(autouse=True)
def _ray_teardown_after_each_test():
    """Shut the Ray cluster down after tests that started one."""

    yield
    ray = sys.modules.get("ray")
    if ray is not None and ray.is_initialized():
        ray.shutdown()
        gc.collect()
