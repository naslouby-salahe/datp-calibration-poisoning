"""datp-cp: calibration-channel poisoning of threshold policies."""

from __future__ import annotations

import importlib
import os

_REQUIRED_IMPORTS: tuple[str, ...] = (
    "flwr",
    "hydra",
    "jinja2",
    "joblib",
    "lightning",
    "matplotlib",
    "mlflow",
    "omegaconf",
    "pandas",
    "polars",
    "pyarrow",
    "pydantic",
    "ray",
    "rich",
    "scipy",
    "sklearn",
    "structlog",
    "torch",
    "numpy",
    "typer",
    "yaml",
)


def configure_runtime_env() -> None:
    """Apply process-wide runtime guards required by the training stack."""
    os.environ.setdefault("RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO", "0")


def check_imports() -> None:
    """Verify all required runtime dependencies are importable (Gate G0-1)."""
    for mod in _REQUIRED_IMPORTS:
        importlib.import_module(mod)
