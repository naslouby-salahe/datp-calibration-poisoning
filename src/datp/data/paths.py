from __future__ import annotations

from pathlib import Path

from datp.data.catalog import DatasetID, dataset_spec


def data_root(base_dir: Path) -> Path:
    return base_dir / "data"


def raw_root(dataset: DatasetID, base_dir: Path) -> Path:
    slug = dataset_spec(dataset).raw_layout.root_slug
    return data_root(base_dir) / "raw" / slug


def processed_root(dataset: DatasetID, base_dir: Path) -> Path:
    return data_root(base_dir) / "processed" / dataset_spec(dataset).processed_slug
