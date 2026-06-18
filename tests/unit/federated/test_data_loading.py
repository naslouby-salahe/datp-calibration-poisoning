# SPDX-License-Identifier: Proprietary
"""Tests for datp.federated.data_loading — client discovery, artifact loading, tensor conversion."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
import pytest
import torch

from datp.core.enums import DeviceType
from datp.data.common.storage import write_artifact
from datp.data.splits import Split, split_path
from datp.federated.data_loading import (
    ALL_SPLITS,
    TRAINING_SPLITS,
    df_to_tensor,
    discover_client_dirs,
    load_client_artifact,
    load_client_data,
    load_single_client_training_data,
    release_freed_heap,
)

_MODULE = "federated.data_loading"


def _write_client_splits(
    client_dir: Path,
    splits: tuple[Split, ...] = (Split.TRAIN, Split.CAL),
    n_features: int = 4,
    n_rows: int = 20,
) -> None:
    client_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.RandomState(42)
    arr = rng.randn(n_rows, n_features)
    for split in splits:
        df = pl.DataFrame({f"f{i}": arr[:, i] for i in range(n_features)})
        write_artifact(df, split_path(client_dir, split))


class TestReleaseFreedHeap:
    def test_smoke(self) -> None:
        """release_freed_heap should not raise."""
        release_freed_heap()


class TestTrainingSplits:
    def test_only_train_and_cal(self) -> None:
        assert TRAINING_SPLITS == (Split.TRAIN, Split.CAL)

    def test_test_splits_not_in_training(self) -> None:
        assert Split.TEST_BENIGN not in TRAINING_SPLITS
        assert Split.TEST_ATTACK not in TRAINING_SPLITS


class TestAllSplits:
    def test_all_four_splits(self) -> None:
        assert set(ALL_SPLITS) == {
            Split.TRAIN,
            Split.CAL,
            Split.TEST_BENIGN,
            Split.TEST_ATTACK,
        }

    def test_all_splits_is_superset_of_training(self) -> None:
        assert set(TRAINING_SPLITS).issubset(set(ALL_SPLITS))


class TestDiscoverClientDirs:
    def test_finds_client_directories(self, tmp_path: Path) -> None:
        for name in ("client_a", "client_b"):
            _write_client_splits(tmp_path / name)

        dirs = discover_client_dirs(tmp_path)
        assert {d.name for d in dirs} == {"client_a", "client_b"}

    def test_skips_directories_without_train(self, tmp_path: Path) -> None:
        _write_client_splits(tmp_path / "good")
        (tmp_path / "bad").mkdir()
        (tmp_path / "bad" / "other.parquet").write_bytes(b"x")

        dirs = discover_client_dirs(tmp_path)
        assert {d.name for d in dirs} == {"good"}

    def test_empty_directory_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="No client directories"):
            discover_client_dirs(tmp_path)

    def test_no_directories_raises(self, tmp_path: Path) -> None:
        (tmp_path / "not_a_dir.txt").write_text("")
        with pytest.raises(FileNotFoundError, match="No client directories"):
            discover_client_dirs(tmp_path)

    def test_sorts_output(self, tmp_path: Path) -> None:
        for name in ("zebra", "alpha", "middle"):
            _write_client_splits(tmp_path / name)
        dirs = discover_client_dirs(tmp_path)
        names = [d.name for d in dirs]
        assert names == sorted(names)


class TestLoadClientArtifact:
    def test_loads_parquet(self, tmp_path: Path) -> None:
        client_dir = tmp_path / "c1"
        client_dir.mkdir()
        df_in = pl.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        write_artifact(df_in, split_path(client_dir, Split.TRAIN))

        df_out = load_client_artifact(client_dir, Split.TRAIN)
        assert df_out.shape == (2, 2)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        client_dir = tmp_path / "c1"
        client_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="Missing"):
            load_client_artifact(client_dir, Split.CAL)


class TestDfToTensor:
    def test_from_polars(self) -> None:
        df = pl.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        t = df_to_tensor(df, torch.device(DeviceType.CPU))
        assert t.shape == (2, 2)
        assert t.dtype == torch.float32
        assert torch.allclose(t, torch.tensor([[1.0, 3.0], [2.0, 4.0]]))

    def test_from_numpy(self) -> None:
        arr = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64)
        t = df_to_tensor(arr, torch.device(DeviceType.CPU))
        assert t.shape == (2, 2)
        assert t.dtype == torch.float32

    def test_empty_dataframe(self) -> None:
        df = pl.DataFrame({"a": [], "b": []}, schema={"a": pl.Float64, "b": pl.Float64})
        t = df_to_tensor(df, torch.device(DeviceType.CPU))
        assert t.shape == (0, 2)


class TestLoadSingleClientTrainingData:
    def test_loads_train_and_cal(self, tmp_path: Path) -> None:
        _write_client_splits(tmp_path, splits=(Split.TRAIN, Split.CAL))
        train_t, cal_t = load_single_client_training_data(
            tmp_path, torch.device(DeviceType.CPU)
        )
        assert train_t.shape == (20, 4)
        assert cal_t.shape == (20, 4)
        assert train_t.dtype == torch.float32

    def test_missing_cal_raises(self, tmp_path: Path) -> None:
        _write_client_splits(tmp_path, splits=(Split.TRAIN,))
        with pytest.raises(FileNotFoundError):
            load_single_client_training_data(tmp_path, torch.device(DeviceType.CPU))


class TestLoadClientData:
    def test_loads_training_splits(self, tmp_path: Path) -> None:
        for name in ("c1", "c2"):
            _write_client_splits(tmp_path / name, splits=TRAINING_SPLITS)

        data = load_client_data(
            tmp_path, device=torch.device(DeviceType.CPU), splits=TRAINING_SPLITS
        )
        assert sorted(data.keys()) == ["c1", "c2"]
        for cd in data.values():
            assert cd.train.shape == (20, 4)
            assert cd.val.shape == (20, 4)
            assert cd.test_benign.numel() == 0
            assert cd.test_attack.numel() == 0

    def test_loads_all_splits(self, tmp_path: Path) -> None:
        all_splits = (Split.TRAIN, Split.CAL, Split.TEST_BENIGN, Split.TEST_ATTACK)
        _write_client_splits(tmp_path / "c1", splits=all_splits)

        data = load_client_data(
            tmp_path, device=torch.device(DeviceType.CPU), splits=ALL_SPLITS
        )
        cd = data["c1"]
        assert cd.train.shape == (20, 4)
        assert cd.val.shape == (20, 4)
        assert cd.test_benign.shape == (20, 4)
        assert cd.test_attack.shape == (20, 4)

    def test_loads_subset_of_splits(self, tmp_path: Path) -> None:
        _write_client_splits(
            tmp_path / "c1", splits=(Split.TRAIN, Split.CAL, Split.TEST_BENIGN)
        )

        data = load_client_data(
            tmp_path, device=torch.device(DeviceType.CPU), splits=(Split.TRAIN, Split.CAL)
        )
        cd = data["c1"]
        assert cd.train.shape == (20, 4)
        assert cd.val.shape == (20, 4)
        assert cd.test_benign.numel() == 0

    def test_empty_features_raises(self, tmp_path: Path) -> None:
        client_dir = tmp_path / "c1"
        client_dir.mkdir()
        df = pl.DataFrame({})
        write_artifact(df, split_path(client_dir, Split.TRAIN))

        with pytest.raises(ValueError, match="0 columns"):
            load_client_data(
                tmp_path, device=torch.device(DeviceType.CPU), splits=TRAINING_SPLITS
            )

    def test_device_is_respected(self, tmp_path: Path) -> None:
        _write_client_splits(tmp_path / "c1", splits=TRAINING_SPLITS)

        data = load_client_data(
            tmp_path, device=torch.device(DeviceType.CPU), splits=TRAINING_SPLITS
        )
        cd = data["c1"]
        assert cd.train.device.type == DeviceType.CPU
        assert cd.val.device.type == DeviceType.CPU
