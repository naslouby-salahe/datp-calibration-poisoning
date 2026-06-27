"""Tests verifying data loading helpers, split discovery, and DataFrame-to-tensor conversions."""

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
    """Helper to write CSV parquet artifacts for various splits of a client."""
    client_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)
    arr = rng.standard_normal((n_rows, n_features))
    for split in splits:
        df = pl.DataFrame({f"f{i}": arr[:, i] for i in range(n_features)})
        write_artifact(df, split_path(client_dir, split))


class TestReleaseFreedHeap:
    """Tests verifying the memory garbage collection smoke test."""

    def test_smoke(self) -> None:
        """Verify that release_freed_heap executes without errors."""
        release_freed_heap()


class TestTrainingSplits:
    """Tests verifying definition of TRAINING_SPLITS."""

    def test_only_train_and_cal(self) -> None:
        """Confirm TRAINING_SPLITS consists exactly of train and cal splits."""
        assert TRAINING_SPLITS == (Split.TRAIN, Split.CAL)

    def test_test_splits_not_in_training(self) -> None:
        """Verify test splits are absent from training split definitions."""
        assert Split.TEST_BENIGN not in TRAINING_SPLITS
        assert Split.TEST_ATTACK not in TRAINING_SPLITS


class TestAllSplits:
    """Tests verifying the full set of split definitions."""

    def test_all_four_splits(self) -> None:
        """Verify that all four splits (train, cal, test_benign, test_attack) are present."""
        assert set(ALL_SPLITS) == {
            Split.TRAIN,
            Split.CAL,
            Split.TEST_BENIGN,
            Split.TEST_ATTACK,
        }

    def test_all_splits_is_superset_of_training(self) -> None:
        """Ensure all splits tuple contains the training splits subset."""
        assert set(TRAINING_SPLITS).issubset(set(ALL_SPLITS))


class TestDiscoverClientDirs:
    """Tests verifying discovery of client data directories."""

    def test_finds_client_directories(self, tmp_path: Path) -> None:
        """Verify client directories containing train split are found."""
        for name in ("client_a", "client_b"):
            _write_client_splits(tmp_path / name)

        dirs = discover_client_dirs(tmp_path)
        assert {d.name for d in dirs} == {"client_a", "client_b"}

    def test_skips_directories_without_train(self, tmp_path: Path) -> None:
        """Verify directories without train parquet files are skipped."""
        _write_client_splits(tmp_path / "good")
        (tmp_path / "bad").mkdir()
        (tmp_path / "bad" / "other.parquet").write_bytes(b"x")

        dirs = discover_client_dirs(tmp_path)
        assert {d.name for d in dirs} == {"good"}

    def test_empty_directory_raises(self, tmp_path: Path) -> None:
        """Ensure FileNotFoundError is raised if no directories exist."""
        with pytest.raises(FileNotFoundError, match="No client directories"):
            discover_client_dirs(tmp_path)

    def test_no_directories_raises(self, tmp_path: Path) -> None:
        """Ensure FileNotFoundError is raised if only non-directory files are present."""
        (tmp_path / "not_a_dir.txt").write_text("")
        with pytest.raises(FileNotFoundError, match="No client directories"):
            discover_client_dirs(tmp_path)

    def test_sorts_output(self, tmp_path: Path) -> None:
        """Verify discovered client directories are returned in sorted order."""
        for name in ("zebra", "alpha", "middle"):
            _write_client_splits(tmp_path / name)
        dirs = discover_client_dirs(tmp_path)
        names = [d.name for d in dirs]
        assert names == sorted(names)


class TestLoadClientArtifact:
    """Tests verifying single artifact file loading."""

    def test_loads_parquet(self, tmp_path: Path) -> None:
        """Verify loading an existing parquet file returns a Polars DataFrame."""
        client_dir = tmp_path / "c1"
        client_dir.mkdir()
        df_in = pl.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        write_artifact(df_in, split_path(client_dir, Split.TRAIN))

        df_out = load_client_artifact(client_dir, Split.TRAIN)
        assert df_out.shape == (2, 2)

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        """Verify FileNotFoundError is raised if the target split artifact is missing."""
        client_dir = tmp_path / "c1"
        client_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="Missing"):
            load_client_artifact(client_dir, Split.CAL)


class TestDfToTensor:
    """Tests verifying conversion of DataFrames to PyTorch float32 tensors."""

    def test_from_polars(self) -> None:
        """Verify conversion of a Polars DataFrame to a float32 tensor."""
        df = pl.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        t = df_to_tensor(df, torch.device(DeviceType.CPU))
        assert t.shape == (2, 2)
        assert t.dtype == torch.float32
        assert torch.allclose(t, torch.tensor([[1.0, 3.0], [2.0, 4.0]]))

    def test_from_numpy(self) -> None:
        """Verify conversion of a NumPy array to a float32 tensor."""
        arr = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64)
        t = df_to_tensor(arr, torch.device(DeviceType.CPU))
        assert t.shape == (2, 2)
        assert t.dtype == torch.float32

    def test_empty_dataframe(self) -> None:
        """Verify empty DataFrame converts to empty tensor of same column dimension."""
        df = pl.DataFrame({"a": [], "b": []}, schema={"a": pl.Float64, "b": pl.Float64})
        t = df_to_tensor(df, torch.device(DeviceType.CPU))
        assert t.shape == (0, 2)


class TestLoadSingleClientTrainingData:
    """Tests verifying training data loading for a single client directory."""

    def test_loads_train_and_cal(self, tmp_path: Path) -> None:
        """Verify loading training and calibration splits for a client."""
        _write_client_splits(tmp_path, splits=(Split.TRAIN, Split.CAL))
        train_t, cal_t = load_single_client_training_data(
            tmp_path, torch.device(DeviceType.CPU)
        )
        assert train_t.shape == (20, 4)
        assert cal_t.shape == (20, 4)
        assert train_t.dtype == torch.float32

    def test_missing_cal_raises(self, tmp_path: Path) -> None:
        """Ensure FileNotFoundError is raised if calibration split is missing."""
        _write_client_splits(tmp_path, splits=(Split.TRAIN,))
        with pytest.raises(FileNotFoundError):
            load_single_client_training_data(tmp_path, torch.device(DeviceType.CPU))


class TestLoadClientData:
    """Tests verifying multi-client split directory loading."""

    def test_loads_training_splits(self, tmp_path: Path) -> None:
        """Verify loading only the training splits for all client folders."""
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
        """Verify loading all four splits for all client folders."""
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
        """Verify loading only the requested splits subset for client folders."""
        _write_client_splits(
            tmp_path / "c1", splits=(Split.TRAIN, Split.CAL, Split.TEST_BENIGN)
        )

        data = load_client_data(
            tmp_path,
            device=torch.device(DeviceType.CPU),
            splits=(Split.TRAIN, Split.CAL),
        )
        cd = data["c1"]
        assert cd.train.shape == (20, 4)
        assert cd.val.shape == (20, 4)
        assert cd.test_benign.numel() == 0

    def test_empty_features_raises(self, tmp_path: Path) -> None:
        """Ensure ValueError is raised if loaded splits have zero column dimension."""
        client_dir = tmp_path / "c1"
        client_dir.mkdir()
        df = pl.DataFrame({})
        write_artifact(df, split_path(client_dir, Split.TRAIN))

        with pytest.raises(ValueError, match="0 columns"):
            load_client_data(
                tmp_path, device=torch.device(DeviceType.CPU), splits=TRAINING_SPLITS
            )

    def test_device_is_respected(self, tmp_path: Path) -> None:
        """Verify tensors are loaded onto the requested PyTorch device."""
        _write_client_splits(tmp_path / "c1", splits=TRAINING_SPLITS)

        data = load_client_data(
            tmp_path, device=torch.device(DeviceType.CPU), splits=TRAINING_SPLITS
        )
        cd = data["c1"]
        assert cd.train.device.type == DeviceType.CPU
        assert cd.val.device.type == DeviceType.CPU
