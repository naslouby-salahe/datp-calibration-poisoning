
from __future__ import annotations
from datp.types import JsonValue

from collections.abc import Mapping, Sequence
from pathlib import Path

import orjson
import pandas as pd
from pydantic import BaseModel
from pydantic_core import to_jsonable_python

def write_json_atomic(
    path: Path,
    data: JsonValue
    | BaseModel
    | Sequence[BaseModel]
    | Mapping[str, JsonValue | BaseModel | Sequence[BaseModel]],
) -> Path:
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
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    pd.DataFrame([to_jsonable_python(r) for r in records]).to_csv(tmp, index=False)
    tmp.replace(path)
