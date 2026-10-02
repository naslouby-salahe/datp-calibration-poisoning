from __future__ import annotations

from datp.types import (
    ContentHash,
    JsonValue,
    NarrativeText,
    RepositoryName,
    ScoreVector,
)
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

REPOSITORY_NAME: RepositoryName = RepositoryName("datp-calibration-poisoning")


def utc_timestamp() -> NarrativeText:
    return datetime.now(UTC).isoformat()


def sha256_bytes(payload: bytes) -> NarrativeText:
    return hashlib.sha256(payload).hexdigest()


def hash_file(path: Path) -> ContentHash:
    if not path.exists():
        return "MISSING"
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1048576):
            digest.update(chunk)
    return digest.hexdigest()


def hash_jsonable(payload: JsonValue) -> ContentHash:
    return sha256_bytes(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    )


def git_commit() -> NarrativeText:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path.cwd(),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, OSError):
        return "GIT_UNAVAILABLE"


def source_hash(paths: list[Path]) -> ContentHash:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path).encode("utf-8"))
        digest.update(hash_file(path).encode("utf-8"))
    return digest.hexdigest()


def array_hash(arr: ScoreVector) -> ContentHash:
    return sha256_bytes(np.asarray(arr, dtype=np.float64).tobytes(order="C"))
