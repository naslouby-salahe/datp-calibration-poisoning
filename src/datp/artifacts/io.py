"""Atomic JSON/CSV writers and metrics persistence."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import orjson
import pandas as pd
from pydantic import BaseModel
from pydantic_core import to_jsonable_python

from datp.artifacts.names import ArtifactFile


def serialize_json_payload(data: Any) -> Any:
    """Convert a Pydantic model to a JSON-serializable Python object."""
    return to_jsonable_python(data)


def write_json_atomic(path: Path, data: Any) -> Path:
    """Write JSON atomically via tmp + rename with sorted, indented output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_bytes(
        orjson.dumps(
            data,
            default=to_jsonable_python,
            option=orjson.OPT_INDENT_2
            | orjson.OPT_SORT_KEYS
            | orjson.OPT_NON_STR_KEYS
            | orjson.OPT_APPEND_NEWLINE,
        )
    )
    tmp.replace(path)
    return path


def write_csv(path: Path, records: Sequence[BaseModel]) -> None:
    """Write a sequence of Pydantic models as CSV atomically via tmp + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    pd.DataFrame([to_jsonable_python(r) for r in records]).to_csv(tmp, index=False)
    tmp.replace(path)


def write_metrics_atomic(run_dir: Path, metrics: Any) -> Path:
    """Write metrics JSON atomically into a run directory."""
    return write_json_atomic(run_dir / ArtifactFile.METRICS, metrics)
