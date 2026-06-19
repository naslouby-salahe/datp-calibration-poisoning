from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
import torch

from datp.data.datasets.nbaiot import prepare_nbaiot
from datp.data.datasets.nbaiot.spec import NBAIOT_SPEC
from datp.federated.data_loading import (
    ALL_SPLITS,
    discover_client_dirs,
    load_client_data,
)
from tests.fixtures.nbaiot_raw import DEVICES, N_FEATURES, make_synthetic_raw


class TestPrepareLoadPathConsistency:
    @pytest.fixture()
    def prepared_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        raw_dir = make_synthetic_raw(tmp_path)
        output_dir = tmp_path / "processed"

        import datp.data.datasets.nbaiot.prepare as nbaiot_mod

        monkeypatch.setattr(nbaiot_mod, "DEVICE_DIRS", DEVICES)
        monkeypatch.setattr(
            nbaiot_mod,
            "NBAIOT_SPEC",
            dataclasses.replace(NBAIOT_SPEC, feature_count=N_FEATURES),
        )

        prepare_nbaiot(raw_dir, output_dir, n_min=100, seed=42, balanced_test=False)
        return output_dir

    def test_discover_client_dirs_finds_devices(self, prepared_dir: Path) -> None:
        client_dirs = discover_client_dirs(prepared_dir)
        found_names = sorted(d.name for d in client_dirs)
        assert found_names == sorted(DEVICES)

    def test_load_client_data_succeeds(self, prepared_dir: Path) -> None:
        client_data = load_client_data(
            prepared_dir, device=torch.device("cpu"), splits=ALL_SPLITS
        )
        assert sorted(client_data.keys()) == sorted(DEVICES)
        for splits in client_data.values():
            assert splits.train is not None
            assert splits.val is not None # cal → val

    def test_no_extra_nesting(self, prepared_dir: Path) -> None:
        nested = prepared_dir / "nbaiot"
        assert not nested.exists(), (
            f"Unexpected nbaiot/ nesting under {prepared_dir}. "
            f"prepare_nbaiot should write device dirs directly into output_dir."
        )
