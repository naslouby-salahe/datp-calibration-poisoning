from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import polars as pl

from datp.artifacts.constants import SCALER_FILE
from datp.data.catalog import DatasetSpec
from datp.data.common.schemas import validate_feature_artifact
from datp.data.common.storage import write_artifact
from datp.data.scaling import save_scaler
from datp.data.splits import (
    Split,
    filename_for_split,
)


def create_empty_feature_frame(columns: list[str]) -> pl.DataFrame:
    schema = {col: pl.Float64 for col in columns}
    return pl.DataFrame(schema=schema)


def write_client_splits(
    client_dir: Path,
    splits: Mapping[Split, pl.DataFrame],
    spec: DatasetSpec,
    scaler: Any | None = None,
) -> None:
    client_dir.mkdir(parents=True, exist_ok=True)

    feature_cols = (
        list(spec.feature_columns) if spec.feature_columns is not None else None
    )
    for split, df in splits.items():
        path = client_dir / filename_for_split(split)
        write_artifact(df, path)
        if feature_cols is not None:
            validate_feature_artifact(path, feature_cols)
        elif df.width != spec.feature_count:
            raise ValueError(
                f"[data.artifacts] Feature count mismatch. Expected: {spec.feature_count}. Got: {df.width}."
            )

    if scaler is not None:
        save_scaler(scaler, client_dir / SCALER_FILE)
