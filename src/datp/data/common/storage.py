"""Low-level Parquet read/write with atomic writes and format guards."""

from __future__ import annotations

from pathlib import Path

import polars as pl

_PARQUET_SUFFIX = ".parquet"


def _check_extension(path: Path) -> None:
    """Raise if the file path does not end in .parquet."""
    if path.suffix != _PARQUET_SUFFIX:
        raise ValueError(
            f"[data.storage] Invalid extension. Expected: ending in .parquet. Got: ending in {path.suffix}."
        )


def write_artifact(df: pl.DataFrame, path: Path) -> None:
    """Write a DataFrame to Parquet atomically via a temp file."""
    _check_extension(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp.parquet")
    df.write_parquet(tmp_path, compression="snappy")
    tmp_path.rename(path)


def read_artifact(path: Path) -> pl.DataFrame:
    """Read a Parquet file into a DataFrame."""
    _check_extension(path)
    return pl.read_parquet(path)


def assert_no_csv_artifacts(directory: Path) -> None:
    """Raise if any CSV files are found under the given directory."""
    if csv_files := sorted(directory.rglob("*.csv")):
        listing = "\n ".join(str(f) for f in csv_files[:10])
        extra = f"\n ... and {len(csv_files) - 10} more" if len(csv_files) > 10 else ""
        raise RuntimeError(
            f"[data.storage] CSV files found in {directory} — Parquet only.\n {listing}{extra}"
        )
