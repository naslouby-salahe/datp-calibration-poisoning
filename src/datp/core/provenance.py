from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

MISSING_MANIFEST_HASH = "MISSING_MANIFEST_HASH"
NOT_APPLICABLE_B0_DIRECT_EVAL = "NOT_APPLICABLE_B0_DIRECT_EVAL"


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def hash_file(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_jsonable(payload: Any) -> str:
    return sha256_bytes(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    )


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path.cwd(),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, OSError):
        return "GIT_UNAVAILABLE"


def source_hash(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path).encode("utf-8"))
        digest.update(hash_file(path).encode("utf-8"))
    return digest.hexdigest()


def array_hash(arr: np.ndarray) -> str:
    normalized = np.asarray(arr, dtype=np.float64)
    return sha256_bytes(normalized.tobytes(order="C"))
