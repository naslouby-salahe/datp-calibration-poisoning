"""Prepared-data loading and tensor conversion for federated clients."""

from __future__ import annotations

import contextlib
import ctypes
import gc
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import polars as pl
import torch

from datp.data.common.storage import read_artifact
from datp.data.splits import Split, split_path
from datp.federated.types import ClientData

TRAINING_SPLITS: tuple[Split, ...] = (Split.TRAIN, Split.CAL)
ALL_SPLITS: tuple[Split, ...] = tuple(Split)


def release_freed_heap() -> None:
    """Trigger garbage collection and return freed pages to the OS."""
    gc.collect()
    with contextlib.suppress(OSError, AttributeError):
        ctypes.CDLL("libc.so.6").malloc_trim(0)


def discover_client_dirs(prepared_dir: Path) -> list[Path]:
    """Find all per-client subdirectories that contain a train split artifact."""
    client_dirs = sorted(
        d
        for d in prepared_dir.iterdir()
        if d.is_dir() and split_path(d, Split.TRAIN).exists()
    )
    if not client_dirs:
        raise FileNotFoundError(f"No client directories found in {prepared_dir}")
    return client_dirs


def load_client_artifact(client_dir: Path, split: Split) -> pl.DataFrame:
    """Read a single split artifact from a client directory as a Polars DataFrame."""
    path = split_path(client_dir, split)
    if not path.exists():
        raise FileNotFoundError(f"Missing {path.name} in {client_dir}")
    return read_artifact(path)


def df_to_tensor(df: pl.DataFrame | np.ndarray, device: torch.device) -> torch.Tensor:
    """Convert a DataFrame or array to a float32 tensor on the given device."""
    values = df.to_numpy() if isinstance(df, pl.DataFrame) else np.asarray(df)
    return torch.tensor(values, dtype=torch.float32, device=device)


def load_single_client_training_data(
    client_dir: Path, device: torch.device
) -> tuple[torch.Tensor, torch.Tensor]:
    """Load train and calibration tensors for one client from disk."""
    train_t = df_to_tensor(read_artifact(split_path(client_dir, Split.TRAIN)), device)
    cal_t = df_to_tensor(read_artifact(split_path(client_dir, Split.CAL)), device)
    release_freed_heap()
    return train_t, cal_t


def load_client_data(
    prepared_dir: Path, device: torch.device, splits: Sequence[Split]
) -> dict[str, ClientData]:
    """Load all requested splits for every client, reusing the first train read for shape inference."""
    client_dirs = discover_client_dirs(prepared_dir)
    splits_set = frozenset(splits)

    first_train_df = read_artifact(split_path(client_dirs[0], Split.TRAIN))
    n_features = first_train_df.shape[1]
    if n_features == 0:
        raise ValueError(f"Train artifact has 0 columns in {client_dirs[0]}")

    empty = torch.empty(0, n_features, dtype=torch.float32, device=device)

    def _load_or_empty(
        cdir: Path, split: Split, override_df: pl.DataFrame | None = None
    ) -> torch.Tensor:
        if split not in splits_set:
            return empty
        df = (
            override_df
            if override_df is not None
            else read_artifact(split_path(cdir, split))
        )
        return df_to_tensor(df, device)

    client_data: dict[str, ClientData] = {}
    for i, cdir in enumerate(client_dirs):
        client_data[cdir.name] = ClientData(
            train=_load_or_empty(cdir, Split.TRAIN, first_train_df if i == 0 else None),
            val=_load_or_empty(cdir, Split.CAL),
            test_benign=_load_or_empty(cdir, Split.TEST_BENIGN),
            test_attack=_load_or_empty(cdir, Split.TEST_ATTACK),
        )

    del first_train_df
    return client_data
