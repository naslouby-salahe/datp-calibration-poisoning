"""Common unit test configuration and helper fixtures."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from datp.scoring.manifest import SCORE_COLUMN


def _write_score_artifact(path: Path, values: list[float]) -> None:
    """Write score values as a single-column Parquet table artifact."""

    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table({SCORE_COLUMN: pa.array(values, type=pa.float32())})
    pq.write_table(table, path)
