
from __future__ import annotations

from pathlib import Path

import polars as pl

from datp.core.enums import PathToken


def _check_extension(path: Path) -> None:
    if path.suffix != PathToken.PARQUET_EXT:
        raise ValueError(
            f"[data.storage] Invalid extension. Expected: ending in .parquet. Got: ending in {path.suffix}."
        )


def write_artifact(df: pl.DataFrame, path: Path) -> None:
    _check_extension(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp.parquet")
    df.write_parquet(tmp_path, compression="snappy")
    tmp_path.rename(path)


def read_artifact(path: Path) -> pl.DataFrame:
    _check_extension(path)
    return pl.read_parquet(path)


def assert_no_csv_artifacts(directory: Path) -> None:
    if csv_files := sorted(directory.rglob(PathToken.CSV_GLOB)):
        listing = "\n ".join(str(f) for f in csv_files[:10])
        extra = f"\n ... and {len(csv_files) - 10} more" if len(csv_files) > 10 else ""
        raise RuntimeError(
            f"[data.storage] CSV files found in {directory} — Parquet only.\n {listing}{extra}"
        )
