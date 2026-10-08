from __future__ import annotations

import os

from datp.enums import EnvironmentVariable


def configure_runtime_env() -> None:
    os.environ.setdefault(EnvironmentVariable.RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO, "0")
