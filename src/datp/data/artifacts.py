"""Writing and validation of per-client split artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import polars as pl
from sklearn.preprocessing import StandardScaler

from datp.artifacts.names import ArtifactFile
from datp.data.catalog import DatasetSpec
from datp.data.common.schemas import validate_feature_artifact
from datp.data.common.storage import write_artifact
from datp.data.scaling import save_scaler
from datp.data.splits import Split, filename_for_split


def create_empty_feature_frame(columns: list[str]) -> pl.DataFrame:
    """Return an empty DataFrame with Float64 columns."""
    return pl.DataFrame(schema={col: pl.Float64 for col in columns})


def write_client_splits(
    client_dir: Path,
    splits: Mapping[Split, pl.DataFrame],
    spec: DatasetSpec,
    scaler: StandardScaler | None = None,
) -> None:
    """Write split Parquet files and an optional scaler for a single client."""
    client_dir.mkdir(parents=True, exist_ok=True)
    feature_cols = list(spec.feature_columns) if spec.feature_columns else None

    for split, df in splits.items():
        path = client_dir / filename_for_split(split)
        write_artifact(df, path)
        if feature_cols:
            validate_feature_artifact(path, feature_cols)
        elif df.width != spec.feature_count:
            raise ValueError(
                f"[data.artifacts] Feature count mismatch. Expected: {spec.feature_count}. Got: {df.width}."
            )

    if scaler:
        save_scaler(scaler, client_dir / ArtifactFile.SCALER)
