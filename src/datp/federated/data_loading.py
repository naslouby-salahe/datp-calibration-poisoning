from __future__ import annotations

import contextlib
import ctypes
import gc
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import polars as pl
import torch

from datp.core.errors import fmt
from datp.core.logging import get_logger
from datp.data.common.storage import read_artifact
from datp.data.splits import Split, split_path
from datp.federated.types import ClientData

logger = get_logger(__name__)

_MODULE = "federated.data_loading"


def release_freed_heap() -> None:
    """Return freed heap pages to OS via glibc malloc_trim; prevents RSS growth from malloc arena fragmentation during repeated large DataFrame allocations in Ray actors."""
    gc.collect()
    with contextlib.suppress(OSError, AttributeError):
        ctypes.CDLL("libc.so.6").malloc_trim(0)


# TRAINING_SPLITS avoids loading the massive test_attack artifacts (~3 GB for 9 N-BaIoT clients).
TRAINING_SPLITS: tuple[Split, ...] = (Split.TRAIN, Split.CAL)
ALL_SPLITS: tuple[Split, ...] = tuple(Split)


def discover_client_dirs(prepared_dir: Path) -> list[Path]:
    client_dirs = sorted(
        d
        for d in prepared_dir.iterdir()
        if d.is_dir() and split_path(d, Split.TRAIN).exists()
    )
    if not client_dirs:
        raise FileNotFoundError(
            fmt(
                _MODULE,
                "No client directories found",
                "directories with train.parquet",
                str(prepared_dir),
            )
        )
    return client_dirs


def load_client_artifact(client_dir: Path, split: Split) -> pl.DataFrame:
    path = split_path(client_dir, split)
    if not path.exists():
        raise FileNotFoundError(
            fmt(
                _MODULE,
                f"Missing {path.name}",
                f"{path.name} present in {client_dir}",
                "absent",
            )
        )
    return read_artifact(path)


def df_to_tensor(df: pl.DataFrame | np.ndarray, device: torch.device) -> torch.Tensor:
    values = df.to_numpy() if isinstance(df, pl.DataFrame) else np.asarray(df)
    return torch.tensor(values, dtype=torch.float32, device=device)


def load_single_client_training_data(
    client_dir: Path,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    # Each Ray actor loads only its assigned client to avoid large actor closures.
    train_df = read_artifact(split_path(client_dir, Split.TRAIN))
    train_t = torch.tensor(train_df.to_numpy(), dtype=torch.float32, device=device)
    del train_df

    cal_df = read_artifact(split_path(client_dir, Split.CAL))
    cal_t = torch.tensor(cal_df.to_numpy(), dtype=torch.float32, device=device)
    del cal_df

    release_freed_heap()
    return train_t, cal_t


def load_client_data(
    prepared_dir: Path,
    device: torch.device,
    splits: Sequence[Split],
) -> dict[str, ClientData]:
    client_dirs = discover_client_dirs(prepared_dir)

    splits_set = frozenset(splits)

    first_train_df = read_artifact(split_path(client_dirs[0], Split.TRAIN))
    n_features = first_train_df.shape[1]
    if n_features == 0:
        raise ValueError(
            fmt(
                _MODULE,
                "Train artifact has 0 columns",
                "at least 1 column",
                str(client_dirs[0]),
            )
        )
    empty = torch.empty(0, n_features, dtype=torch.float32, device=device)

    def _load_or_empty(cdir: Path, split: Split, first_train_df_override):
        if split not in splits_set:
            return empty
        if first_train_df_override is not None:
            return torch.tensor(
                first_train_df_override.to_numpy(), dtype=torch.float32, device=device
            )
        return torch.tensor(
            read_artifact(split_path(cdir, split)).to_numpy(),
            dtype=torch.float32,
            device=device,
        )

    client_data: dict[str, ClientData] = {}
    for i, cdir in enumerate(client_dirs):
        cid = cdir.name
        # Reuse the DataFrame we already read for n_features detection.
        train_t = _load_or_empty(
            cdir,
            Split.TRAIN,
            first_train_df_override=first_train_df if i == 0 else None,
        )
        val_t = _load_or_empty(cdir, Split.CAL, first_train_df_override=None)
        tb_t = _load_or_empty(cdir, Split.TEST_BENIGN, first_train_df_override=None)
        ta_t = _load_or_empty(cdir, Split.TEST_ATTACK, first_train_df_override=None)

        client_data[cid] = ClientData(
            train=train_t,
            val=val_t,
            test_benign=tb_t,
            test_attack=ta_t,
        )

    del first_train_df
    loaded = ", ".join(sorted(split.value for split in splits_set))
    logger.info(
        "loaded clients",
        n_clients=len(client_data),
        path=str(prepared_dir),
        device=str(device),
        splits=loaded,
    )
    return client_data
