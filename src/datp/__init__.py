from __future__ import annotations

import os


def configure_runtime_env() -> None:
    os.environ.setdefault("RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO", "0")
