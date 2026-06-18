from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

from datp.core.enums import DeviceType
from datp.data.datasets.nbaiot import prepare_nbaiot
from datp.data.datasets.nbaiot.spec import NBAIOT_SPEC
from datp.federated.data_loading import (
    ALL_SPLITS,
    discover_client_dirs,
    load_client_data,
)

_N_FEATURES = 10
_N_BENIGN = 300 # Enough for all splits above n_min=100
_N_ATTACK = 50
_DEVICES = ["TestDev_A", "TestDev_B"]


def _make_synthetic_raw(base: Path) -> Path:
    raw = base / "raw"
    rng = np.random.RandomState(42)
    cols = [f"feat_{i}" for i in range(_N_FEATURES)]

    for dev in _DEVICES:
        dev_dir = raw / dev
        dev_dir.mkdir(parents=True)
        pd.DataFrame(rng.randn(_N_BENIGN, _N_FEATURES), columns=cols).to_csv( # type: ignore
            dev_dir / "benign_traffic.csv",
            index=False,
        )
        atk_dir = dev_dir / "gafgyt_attacks"
        atk_dir.mkdir()
        pd.DataFrame(rng.randn(_N_ATTACK, _N_FEATURES), columns=cols).to_csv( # type: ignore
            atk_dir / "combo.csv",
            index=False,
        )
    return raw


class TestPrepareLoadPathConsistency:
    @pytest.fixture()
    def prepared_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        raw_dir = _make_synthetic_raw(tmp_path)
        output_dir = tmp_path / "processed"

        import datp.data.datasets.nbaiot.prepare as nbaiot_mod

        monkeypatch.setattr(nbaiot_mod, "DEVICE_DIRS", _DEVICES)
        monkeypatch.setattr(
            nbaiot_mod,
            "NBAIOT_SPEC",
            dataclasses.replace(NBAIOT_SPEC, feature_count=_N_FEATURES),
        )

        prepare_nbaiot(raw_dir, output_dir, n_min=100, seed=42, balanced_test=False)
        return output_dir

    def test_discover_client_dirs_finds_devices(self, prepared_dir: Path) -> None:
        client_dirs = discover_client_dirs(prepared_dir)
        found_names = sorted(d.name for d in client_dirs)
        assert found_names == sorted(_DEVICES)

    def test_load_client_data_succeeds(self, prepared_dir: Path) -> None:
        client_data = load_client_data(prepared_dir, device=torch.device(DeviceType.CPU), splits=ALL_SPLITS)
        assert sorted(client_data.keys()) == sorted(_DEVICES)
        for cid, splits in client_data.items():
            assert splits.train is not None
            assert splits.val is not None # cal → val

    def test_no_extra_nesting(self, prepared_dir: Path) -> None:
        nested = prepared_dir / "nbaiot"
        assert not nested.exists(), (
            f"Unexpected nbaiot/ nesting under {prepared_dir}. "
            f"prepare_nbaiot should write device dirs directly into output_dir."
        )
