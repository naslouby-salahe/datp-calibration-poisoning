from __future__ import annotations

from datp.types import ColumnName


from collections.abc import Sequence
from pathlib import Path

import polars as pl

from datp.scoring.manifest import ScoringColumn

_SCHEMA_MODULE = "data.schema"


def validate_feature_artifact(path: Path, expected_columns: Sequence[ColumnName]) -> None:
    schema = pl.read_parquet_schema(path)
    actual_columns = list(schema.keys())
    expected_list = list(expected_columns)

    if actual_columns != expected_list:
        raise ValueError(
            f"[{_SCHEMA_MODULE}] Schema mismatch at {path}. Expected: columns: {expected_list}. Got: columns: {actual_columns}."
        )

    for name in expected_list:
        if not schema[name].is_numeric():
            raise TypeError(
                f"[{_SCHEMA_MODULE}] Column '{name}' has non-numeric type. Expected: numeric. Got: {schema[name]}."
            )


def validate_score_artifact(path: Path) -> None:
    schema = pl.read_parquet_schema(path)
    if list(schema.keys()) != [ScoringColumn.RECONSTRUCTION_ERROR]:
        raise ValueError(
            f"[{_SCHEMA_MODULE}] Schema mismatch at {path}. Expected: columns: [{ScoringColumn.RECONSTRUCTION_ERROR}]. Got: columns: {list(schema.keys())}."
        )

    if not schema[ScoringColumn.RECONSTRUCTION_ERROR].is_float():
        raise TypeError(
                f"[{_SCHEMA_MODULE}] Column '{ScoringColumn.RECONSTRUCTION_ERROR}' has non-floating type. Expected: floating. Got: {schema[ScoringColumn.RECONSTRUCTION_ERROR]}."
        )
