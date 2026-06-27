"""Parquet schema validation for feature and score artifacts."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import polars as pl

from datp.scoring.manifest import SCORE_COLUMN

_SCHEMA_MODULE = "data.schema"


def validate_feature_artifact(path: Path, expected_columns: Sequence[str]) -> None:
    """Verify that a Parquet file has the expected numeric columns."""
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
                f"[{_SCHEMA_MODULE}] Column '{name}' has non-numeric type. Expected: numeric. Got: {str(schema[name])}."
            )


def validate_score_artifact(path: Path) -> None:
    """Verify that a Parquet file has the expected single float score column."""
    schema = pl.read_parquet_schema(path)
    if list(schema.keys()) != [SCORE_COLUMN]:
        raise ValueError(
            f"[{_SCHEMA_MODULE}] Schema mismatch at {path}. Expected: columns: [{SCORE_COLUMN}]. Got: columns: {list(schema.keys())}."
        )

    if not schema[SCORE_COLUMN].is_float():
        raise TypeError(
            f"[{_SCHEMA_MODULE}] Column '{SCORE_COLUMN}' has non-floating type. Expected: floating. Got: {str(schema[SCORE_COLUMN])}."
        )
