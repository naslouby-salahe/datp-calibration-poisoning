from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from datp.core.errors import fmt
from datp.scoring.schema import SCORE_COLUMN


def validate_feature_artifact(
    path: Path | str,
    expected_columns: Sequence[str],
) -> None:
    """Validate column names, order, and numeric types from Parquet metadata only; does not load file contents."""
    path = Path(path)
    schema = pq.read_schema(path)

    actual_columns = schema.names
    expected_list = list(expected_columns)

    if actual_columns != expected_list:
        raise ValueError(
            fmt(
                "data.schema",
                f"Feature artifact schema mismatch at {path}",
                f"columns: {expected_list}",
                f"columns: {actual_columns}",
            )
        )

    for name in expected_list:
        field = schema.field(name)
        if not pa.types.is_floating(field.type) and not pa.types.is_integer(field.type):
            raise TypeError(
                fmt(
                    "data.schema",
                    f"Feature artifact column '{name}' has non-numeric type",
                    "numeric type (floating or integer)",
                    str(field.type),
                )
            )


def validate_score_artifact(path: Path | str) -> None:
    path = Path(path)
    schema = pq.read_schema(path)

    if schema.names != [SCORE_COLUMN]:
        raise ValueError(
            fmt(
                "data.schema",
                f"Score artifact schema mismatch at {path}",
                f"columns: [{SCORE_COLUMN}]",
                f"columns: {schema.names}",
            )
        )

    field = schema.field(SCORE_COLUMN)
    if not pa.types.is_floating(field.type):
        raise TypeError(
            fmt(
                "data.schema",
                f"Score artifact column '{SCORE_COLUMN}' has non-floating type",
                "floating type",
                str(field.type),
            )
        )
