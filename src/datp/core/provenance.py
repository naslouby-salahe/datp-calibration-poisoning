"""Content-addressable hashing and provenance helpers for artifacts and source files."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

MISSING_MANIFEST_HASH = "MISSING_MANIFEST_HASH"
REPOSITORY_NAME = "datp-calibration-poisoning"


def utc_timestamp() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat()


def sha256_bytes(payload: bytes) -> str:
    """Return the hex-encoded SHA-256 digest of raw bytes."""
    return hashlib.sha256(payload).hexdigest()


def hash_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file, or 'MISSING' if absent."""
    if not path.exists():
        return "MISSING"
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1048576):
            digest.update(chunk)
    return digest.hexdigest()


def hash_jsonable(payload: Any) -> str:
    """Return a deterministic SHA-256 hex digest of a JSON-serializable value."""
    return sha256_bytes(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    )


def git_commit() -> str:
    """Return the current HEAD commit hash, or 'GIT_UNAVAILABLE' on failure."""
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
    """Return a combined SHA-256 digest over a sorted list of file paths and their contents."""
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path).encode("utf-8"))
        digest.update(hash_file(path).encode("utf-8"))
    return digest.hexdigest()


def array_hash(arr: np.ndarray) -> str:
    """Return a deterministic SHA-256 hex digest of a float64 numpy array's raw bytes."""
    return sha256_bytes(np.asarray(arr, dtype=np.float64).tobytes(order="C"))
