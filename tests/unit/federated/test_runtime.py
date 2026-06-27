"""Tests verifying Ray cluster memory safety checks, system resources, and worker allocation algorithms."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from datp.config.compose import BASE_CONFIG
from datp.core.device import resolve_device
from datp.core.enums import DeviceType
from datp.federated.runtime import (
    RayClientResourceRequest,
    check_object_store_capacity,
    derive_client_resources,
    ensure_ray_memory_threshold,
    get_available_ram_gb,
)


class TestObjectStoreCapacity:
    """Tests verifying validation on Ray's object store memory capacity bounds."""

    def test_fits_returns_observed_facts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify that check_object_store_capacity returns correct observed memory facts."""
        monkeypatch.setattr("datp.federated.runtime.get_available_ram_gb", lambda: 8.0)
        result = check_object_store_capacity(1024)
        assert result["object_store_mb"] == 1024
        assert result["available_ram_mb"] == 8 * 1024

    def test_exceeds_available_ram_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ensure check_object_store_capacity raises RuntimeError if request exceeds RAM limits."""
        monkeypatch.setattr("datp.federated.runtime.get_available_ram_gb", lambda: 1.0)
        with pytest.raises(RuntimeError, match="exceeds available RAM"):
            check_object_store_capacity(4096)

    def test_equal_to_available_ram_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify check_object_store_capacity allows capacity equal to available RAM."""
        monkeypatch.setattr("datp.federated.runtime.get_available_ram_gb", lambda: 2.0)
        result = check_object_store_capacity(2 * 1024)
        assert result["object_store_mb"] == 2 * 1024


class TestRayMemoryThreshold:
    """Tests verifying memory threshold environment settings inside Ray clusters."""

    def test_ray_memory_threshold_value(self) -> None:
        """Verify that the default configuration value of ray_memory_threshold is 0.9."""
        assert BASE_CONFIG.runtime.ray_memory_threshold == pytest.approx(0.90)

    def test_ray_memory_threshold_enforced(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify that ensure_ray_memory_threshold sets the target environment variable."""
        monkeypatch.delenv("RAY_memory_usage_threshold", raising=False)
        ensure_ray_memory_threshold(BASE_CONFIG.runtime.ray_memory_threshold)
        assert os.environ["RAY_memory_usage_threshold"] == "0.9"

    def test_ray_memory_threshold_rejects_high(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify that error is raised if environment setting is higher than configured threshold."""
        monkeypatch.setenv("RAY_memory_usage_threshold", "0.99")
        with pytest.raises(RuntimeError, match="too high"):
            ensure_ray_memory_threshold(BASE_CONFIG.runtime.ray_memory_threshold)

    def test_ray_memory_threshold_accepts_lower(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify that environment setting remains unchanged if lower than configured threshold."""
        monkeypatch.setenv("RAY_memory_usage_threshold", "0.85")
        ensure_ray_memory_threshold(BASE_CONFIG.runtime.ray_memory_threshold)
        assert os.environ["RAY_memory_usage_threshold"] == "0.85"

    def test_ray_memory_threshold_rejects_invalid(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify that ensure_ray_memory_threshold raises RuntimeError on non-float settings."""
        monkeypatch.setenv("RAY_memory_usage_threshold", "not-a-number")
        with pytest.raises(RuntimeError, match="invalid float"):
            ensure_ray_memory_threshold(BASE_CONFIG.runtime.ray_memory_threshold)


class TestGetAvailableRamGb:
    """Tests verifying retrieval of available system RAM."""

    def test_returns_positive_float(self) -> None:
        """Verify that get_available_ram_gb returns a positive float value under standard systems."""
        result = get_available_ram_gb()
        assert isinstance(result, float)
        assert result > 0

    def test_falls_back_to_proc_meminfo(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Verify fallback parser parses /proc/meminfo when psutil package is not importable."""
        meminfo = tmp_path / "meminfo"
        meminfo.write_text("MemAvailable: 16777216 kB\n")
        monkeypatch.setattr("datp.federated.runtime._MEMINFO_PATH", meminfo)
        monkeypatch.setitem(sys.modules, "psutil", None)
        assert get_available_ram_gb() == pytest.approx(16.0)

    def test_raises_when_neither_available(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Verify get_available_ram_gb raises RuntimeError when both psutil and meminfo are absent."""
        monkeypatch.setitem(sys.modules, "psutil", None)
        monkeypatch.setattr(
            "datp.federated.runtime._MEMINFO_PATH", tmp_path / "no_meminfo"
        )
        with pytest.raises(RuntimeError, match="Cannot determine available RAM"):
            get_available_ram_gb()


class TestDeriveClientResources:
    """Tests verifying allocation of concurrent worker slots and CPU/GPU shares."""

    @pytest.fixture(autouse=True)
    def _mock_system(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Fixture to mock available system RAM and CPU core count."""
        monkeypatch.setattr("datp.federated.runtime.get_available_ram_gb", lambda: 16.0)
        monkeypatch.setattr("os.cpu_count", lambda: 8)

    def test_returns_typed_client_resources(self) -> None:
        """Verify result includes correct CPU/GPU shares in CUDA mode."""
        result = derive_client_resources(
            RayClientResourceRequest(
                per_client_ram_gb=1.5,
                reserve_ram_gb=3.5,
                max_concurrent_override=None,
                require_cuda=True,
                num_gpus_per_client=0.5,
            )
        )
        assert isinstance(result, dict)
        assert result["num_gpus"] == pytest.approx(0.5)
        assert "num_cpus" in result

    def test_num_gpus_zero_when_cpu_mode(self) -> None:
        """Verify GPU share is 0 when requirement is set to CPU mode."""
        result = derive_client_resources(
            RayClientResourceRequest(
                per_client_ram_gb=1.5,
                reserve_ram_gb=3.5,
                max_concurrent_override=None,
                require_cuda=False,
                num_gpus_per_client=0.5,
            )
        )
        assert result["num_gpus"] == pytest.approx(0.0)

    def test_honours_max_concurrent_override(self) -> None:
        """Verify concurrent resource override bounds the per-client CPU cores fraction."""
        result = derive_client_resources(
            RayClientResourceRequest(
                per_client_ram_gb=1.5,
                reserve_ram_gb=3.5,
                max_concurrent_override=4,
                require_cuda=False,
                num_gpus_per_client=0.0,
            )
        )
        assert result["num_cpus"] == pytest.approx(2.0)

    def test_rejects_zero_per_client_ram(self) -> None:
        """Verify ValueError is raised if requested worker RAM is less than or equal to zero."""
        with pytest.raises(ValueError, match="per_client_ram_gb must be > 0"):
            derive_client_resources(
                RayClientResourceRequest(
                    per_client_ram_gb=0.0,
                    reserve_ram_gb=3.5,
                    max_concurrent_override=None,
                    require_cuda=False,
                    num_gpus_per_client=0.0,
                )
            )

    def test_device_and_resources_agree_cuda(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify resolve_device and derive_client_resources agree on GPU usage in CUDA environments."""
        monkeypatch.setattr("datp.core.device.torch.cuda.is_available", lambda: True)
        device = resolve_device(require_cuda=True)
        resources = derive_client_resources(
            RayClientResourceRequest(
                per_client_ram_gb=1.5,
                reserve_ram_gb=3.5,
                max_concurrent_override=None,
                require_cuda=True,
                num_gpus_per_client=0.5,
            )
        )
        assert device.type == DeviceType.CUDA
        assert resources["num_gpus"] > 0

    def test_device_and_resources_agree_cpu(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify resolve_device and derive_client_resources agree on CPU usage in CPU-only environments."""
        monkeypatch.setattr("datp.core.device.torch.cuda.is_available", lambda: False)
        device = resolve_device(require_cuda=False)
        resources = derive_client_resources(
            RayClientResourceRequest(
                per_client_ram_gb=1.5,
                reserve_ram_gb=3.5,
                max_concurrent_override=None,
                require_cuda=False,
                num_gpus_per_client=0.5,
            )
        )
        assert device.type == DeviceType.CPU
        assert resources["num_gpus"] == pytest.approx(0.0)
