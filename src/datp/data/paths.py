"""Filesystem path helpers for data directories."""

from __future__ import annotations

from pathlib import Path

from datp.data.catalog import DatasetID, dataset_spec


def data_root(base_dir: Path) -> Path:
    """Return the top-level data directory under base_dir."""
    return base_dir / "data"


def raw_root(dataset: DatasetID, base_dir: Path) -> Path:
    """Return the raw-data directory for a dataset."""
    return data_root(base_dir) / "raw" / dataset_spec(dataset).raw_layout.root_slug


def processed_root(dataset: DatasetID, base_dir: Path) -> Path:
    """Return the processed-data directory for a dataset."""
    return data_root(base_dir) / "processed" / dataset_spec(dataset).processed_slug
