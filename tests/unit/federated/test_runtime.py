from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from datp.config.compose import BASE_CONFIG
from datp.core.device import resolve_device
from datp.core.enums import DeviceType
from datp.federated.runtime import (
    check_object_store_capacity,
    derive_client_resources,
    derive_max_concurrent,
    ensure_ray_memory_threshold,
    get_available_ram_gb,
)


class TestObjectStoreCapacity:
    def test_fits_returns_observed_facts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "datp.federated.runtime.get_available_ram_gb", lambda: 8.0
        )
        result = check_object_store_capacity(1024)
        assert result["object_store_mb"] == 1024
        assert result["available_ram_mb"] == 8 * 1024

    def test_exceeds_available_ram_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "datp.federated.runtime.get_available_ram_gb", lambda: 1.0
        )
        with pytest.raises(RuntimeError, match="exceeds available RAM"):
            check_object_store_capacity(4096)

    def test_equal_to_available_ram_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "datp.federated.runtime.get_available_ram_gb", lambda: 2.0
        )
        result = check_object_store_capacity(2 * 1024)
        assert result["object_store_mb"] == 2 * 1024


class TestRayMemoryThreshold:
    def test_ray_memory_threshold_value(self) -> None:
        assert BASE_CONFIG.runtime.ray_memory_threshold == 0.90

    def test_ray_memory_threshold_enforced(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("RAY_memory_usage_threshold", raising=False)
        ensure_ray_memory_threshold(BASE_CONFIG.runtime.ray_memory_threshold)
        assert os.environ["RAY_memory_usage_threshold"] == "0.9"

    def test_ray_memory_threshold_rejects_high(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("RAY_memory_usage_threshold", "0.99")
        with pytest.raises(RuntimeError, match="too high"):
            ensure_ray_memory_threshold(BASE_CONFIG.runtime.ray_memory_threshold)

    def test_ray_memory_threshold_accepts_lower(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("RAY_memory_usage_threshold", "0.85")
        ensure_ray_memory_threshold(BASE_CONFIG.runtime.ray_memory_threshold)
        assert os.environ["RAY_memory_usage_threshold"] == "0.85"

    def test_ray_memory_threshold_rejects_invalid(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("RAY_memory_usage_threshold", "not-a-number")
        with pytest.raises(RuntimeError, match="not a valid float"):
            ensure_ray_memory_threshold(BASE_CONFIG.runtime.ray_memory_threshold)


class TestDeriveMaxConcurrent:
    def test_derive_max_concurrent_from_ram(self) -> None:
        assert derive_max_concurrent(16.0, per_client_ram_gb=0.6, reserve_gb=2.0) == 23

    def test_derive_max_concurrent_low_ram(self) -> None:
        assert derive_max_concurrent(3.0, per_client_ram_gb=0.6, reserve_gb=2.0) == 1

    def test_derive_max_concurrent_never_zero(self) -> None:
        result = derive_max_concurrent(1.0, per_client_ram_gb=0.6, reserve_gb=2.0)
        assert result == 1
        assert result >= 1

    def test_derive_max_concurrent_zero_ram(self) -> None:
        assert derive_max_concurrent(0.0, per_client_ram_gb=0.6, reserve_gb=2.0) == 1

    def test_derive_max_concurrent_rejects_bad_per_client(self) -> None:
        with pytest.raises(ValueError, match="per_client_ram_gb must be > 0"):
            derive_max_concurrent(16.0, per_client_ram_gb=0.0, reserve_gb=2.0)


class TestGetAvailableRamGb:
    def test_returns_positive_float(self) -> None:
        result = get_available_ram_gb()
        assert isinstance(result, float)
        assert result > 0

    def test_falls_back_to_proc_meminfo(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        meminfo = tmp_path / "meminfo"
        meminfo.write_text("MemAvailable: 16777216 kB\n")
        monkeypatch.setattr("datp.federated.runtime._MEMINFO_PATH", meminfo)
        monkeypatch.setitem(sys.modules, "psutil", None)
        assert get_available_ram_gb() == pytest.approx(16.0)

    def test_raises_when_neither_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(sys.modules, "psutil", None)
        monkeypatch.setattr("datp.federated.runtime._read_meminfo_gib", lambda: None)
        with pytest.raises(RuntimeError, match="Cannot determine available RAM"):
            get_available_ram_gb()


class TestDeriveClientResources:
    @pytest.fixture(autouse=True)
    def _mock_system(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("datp.federated.runtime.get_available_ram_gb", lambda: 16.0)
        monkeypatch.setattr("os.cpu_count", lambda: 8)

    def test_returns_typed_client_resources(self) -> None:
        result = derive_client_resources(
            per_client_ram_gb=1.5,
            reserve_ram_gb=3.5,
            max_concurrent_override=None,
            require_cuda=True,
            ray_num_gpus_per_client=0.5,
        )
        assert isinstance(result, dict)
        assert result["num_gpus"] == 0.5
        assert "num_cpus" in result

    def test_num_gpus_zero_when_cpu_mode(self) -> None:
        result = derive_client_resources(
            per_client_ram_gb=1.5,
            reserve_ram_gb=3.5,
            max_concurrent_override=None,
            require_cuda=False,
            ray_num_gpus_per_client=0.5,
        )
        assert result["num_gpus"] == 0.0

    def test_honours_max_concurrent_override(self) -> None:
        result = derive_client_resources(
            per_client_ram_gb=1.5,
            reserve_ram_gb=3.5,
            max_concurrent_override=4,
            require_cuda=False,
            ray_num_gpus_per_client=0.0,
        )
        assert result["num_cpus"] == 2.0 # ceil(8 / 4)

    def test_device_and_resources_agree_cuda(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("datp.core.device.torch.cuda.is_available", lambda: True)
        device = resolve_device(require_cuda=True)
        resources = derive_client_resources(
            per_client_ram_gb=1.5,
            reserve_ram_gb=3.5,
            max_concurrent_override=None,
            require_cuda=True,
            ray_num_gpus_per_client=0.5,
        )
        assert device.type == DeviceType.CUDA
        assert resources["num_gpus"] > 0

    def test_device_and_resources_agree_cpu(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("datp.core.device.torch.cuda.is_available", lambda: False)
        device = resolve_device(require_cuda=False)
        resources = derive_client_resources(
            per_client_ram_gb=1.5,
            reserve_ram_gb=3.5,
            max_concurrent_override=None,
            require_cuda=False,
            ray_num_gpus_per_client=0.5,
        )
        assert device.type == DeviceType.CPU
        assert resources["num_gpus"] == 0.0
