"""Ray resource estimation and preflight checks for FL simulations."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

_BYTES_PER_GIB = 1024**3
_MIB_PER_GIB = 1024
_KIB_PER_GIB = 1024**2
_MEMINFO_PATH = Path("/proc/meminfo")
_RAY_MEMORY_ENV_KEY = "RAY_memory_usage_threshold"


class ObjectStorePreflight(TypedDict):
    """Result of an object-store capacity check: configured size and available RAM."""

    object_store_mb: int
    available_ram_mb: int


class ClientResources(TypedDict):
    """Per-actor resource allocations derived from available RAM and request parameters."""

    num_cpus: float
    num_gpus: float


@dataclass(frozen=True, slots=True)
class RayClientResourceRequest:
    """Parameters needed to estimate per-client resource requirements."""

    per_client_ram_gb: float
    reserve_ram_gb: float
    max_concurrent_override: int | None
    require_cuda: bool
    num_gpus_per_client: float


def ensure_ray_memory_threshold(threshold: float) -> None:
    """Set the Ray memory threshold env var if not already set lower."""
    current = os.environ.get(_RAY_MEMORY_ENV_KEY)
    if current is None:
        os.environ[_RAY_MEMORY_ENV_KEY] = str(threshold)
        return
    try:
        val = float(current)
    except ValueError as exc:
        raise RuntimeError(f"{_RAY_MEMORY_ENV_KEY} invalid float: {current}") from exc
    if val > threshold:
        raise RuntimeError(f"{_RAY_MEMORY_ENV_KEY} too high: {val} > {threshold}")


def get_available_ram_gb() -> float:
    """Return available system RAM in GiB via psutil or /proc/meminfo."""
    try:
        import psutil

        return psutil.virtual_memory().available / _BYTES_PER_GIB
    except ImportError:
        try:
            with _MEMINFO_PATH.open() as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        return int(line.split()[1]) / _KIB_PER_GIB
        except (OSError, ValueError, IndexError):
            pass
    raise RuntimeError(
        "Cannot determine available RAM (install psutil or ensure Linux /proc/meminfo)"
    )


def check_object_store_capacity(object_store_mb: int) -> ObjectStorePreflight:
    """Validate that the configured object store fits in available RAM."""
    available_ram_mb = int(get_available_ram_gb() * _MIB_PER_GIB)
    if object_store_mb > available_ram_mb:
        raise RuntimeError(
            f"Configured Ray object-store ({object_store_mb} MiB) exceeds available RAM ({available_ram_mb} MiB)"
        )
    return {"object_store_mb": object_store_mb, "available_ram_mb": available_ram_mb}


def derive_client_resources(request: RayClientResourceRequest) -> ClientResources:
    """Compute per-actor CPU/GPU allocations from available RAM and request params."""
    available_ram_gb = get_available_ram_gb()
    if request.max_concurrent_override is not None:
        max_concurrent = request.max_concurrent_override
    else:
        if request.per_client_ram_gb <= 0:
            raise ValueError("per_client_ram_gb must be > 0")
        max_concurrent = max(
            1,
            math.floor(
                (available_ram_gb - request.reserve_ram_gb) / request.per_client_ram_gb
            ),
        )

    cpu_count = os.cpu_count()
    if cpu_count is None:
        raise RuntimeError("Cannot determine CPU count")

    num_cpus_per_actor = max(1, math.ceil(max(cpu_count, 1) / max_concurrent))
    num_gpus = request.num_gpus_per_client if request.require_cuda else 0.0

    return {"num_cpus": float(num_cpus_per_actor), "num_gpus": num_gpus}
