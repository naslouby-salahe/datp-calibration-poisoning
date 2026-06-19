"""Tests for datp.core.provenance — hash utilities and provenance constants."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from datp.core.provenance import (
    MISSING_MANIFEST_HASH,
    NOT_APPLICABLE_B0_DIRECT_EVAL,
    array_hash,
    git_commit,
    hash_file,
    hash_jsonable,
    sha256_bytes,
    source_hash,
    utc_timestamp,
)

# ── sha256_bytes ──────────────────────────────────────────────────────────


class TestSha256Bytes:
    def test_deterministic(self) -> None:
        payload = b"hello world"
        assert sha256_bytes(payload) == sha256_bytes(payload)

    def test_different_content_different_hash(self) -> None:
        assert sha256_bytes(b"a") != sha256_bytes(b"b")

    def test_output_is_64_char_hex(self) -> None:
        assert len(sha256_bytes(b"test")) == 64
        int(sha256_bytes(b"test"), 16)  # valid hex


# ── hash_file ─────────────────────────────────────────────────────────────


class TestHashFile:
    def test_deterministic(self, tmp_path: Path) -> None:
        f = tmp_path / "data.bin"
        f.write_bytes(b"deterministic content")
        assert hash_file(f) == hash_file(f)

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(b"content A")
        f2.write_bytes(b"content B")
        assert hash_file(f1) != hash_file(f2)

    def test_missing_file_returns_missing_sentinel(self, tmp_path: Path) -> None:
        assert hash_file(tmp_path / "nonexistent.bin") == "MISSING"

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.bin"
        f.write_bytes(b"")
        result = hash_file(f)
        assert len(result) == 64
        # Empty file has a well-known SHA-256
        assert (
            result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )

    def test_output_is_64_char_hex(self, tmp_path: Path) -> None:
        f = tmp_path / "f.bin"
        f.write_bytes(b"test")
        assert len(hash_file(f)) == 64


# ── hash_jsonable ─────────────────────────────────────────────────────────


class TestHashJsonable:
    def test_deterministic(self) -> None:
        payload = {"a": 1, "b": [2, 3]}
        assert hash_jsonable(payload) == hash_jsonable(payload)

    def test_sort_key_independent(self) -> None:
        assert hash_jsonable({"b": 2, "a": 1}) == hash_jsonable({"a": 1, "b": 2})

    def test_different_content_different_hash(self) -> None:
        assert hash_jsonable({"x": 1}) != hash_jsonable({"x": 2})

    def test_nested_structures(self) -> None:
        h = hash_jsonable({"nested": {"list": [1, 2, 3]}, "str": "hello"})
        assert len(h) == 64

    def test_non_serializable_falls_back_to_str(self, tmp_path: Path) -> None:
        """default=str in json.dumps means any object can be hashed."""
        result = hash_jsonable({tmp_path})
        assert len(result) == 64


# ── git_commit ────────────────────────────────────────────────────────────


class TestGitCommit:
    def test_returns_string(self) -> None:
        result = git_commit()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_hex_or_sentinel(self) -> None:
        result = git_commit()
        # Either a 40-char hex SHA or the GIT_UNAVAILABLE sentinel
        assert len(result) == 40 or result == "GIT_UNAVAILABLE"


# ── source_hash ───────────────────────────────────────────────────────────


class TestSourceHash:
    def test_deterministic(self, tmp_path: Path) -> None:
        f = tmp_path / "src.py"
        f.write_text("print(1)", encoding="utf-8")
        assert source_hash([f]) == source_hash([f])

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("x=1", encoding="utf-8")
        f2.write_text("x=2", encoding="utf-8")
        assert source_hash([f1]) != source_hash([f2])

    def test_multiple_files(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("x=1", encoding="utf-8")
        f2.write_text("y=2", encoding="utf-8")
        h_both = source_hash([f1, f2])
        h_one = source_hash([f1])
        assert h_both != h_one  # different because order + content differs

    def test_path_order_matters(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("x=1", encoding="utf-8")
        f2.write_text("y=2", encoding="utf-8")
        assert source_hash([f1, f2]) != source_hash([f2, f1])


# ── array_hash ────────────────────────────────────────────────────────────


class TestArrayHash:
    def test_deterministic(self) -> None:
        arr = np.array([1.0, 2.0, 3.0])
        assert array_hash(arr) == array_hash(arr)

    def test_different_content_different_hash(self) -> None:
        assert array_hash(np.array([1.0])) != array_hash(np.array([2.0]))

    def test_dtype_normalization_float32_to_float64(self) -> None:
        """float32 and float64 arrays with same values produce same hash."""
        arr32 = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        arr64 = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        assert array_hash(arr32) == array_hash(arr64)

    def test_output_is_64_char_hex(self) -> None:
        assert len(array_hash(np.array([1.0]))) == 64

    def test_multidimensional(self) -> None:
        arr = np.array([[1.0, 2.0], [3.0, 4.0]])
        assert len(array_hash(arr)) == 64


# ── utc_timestamp ─────────────────────────────────────────────────────────


class TestUtcTimestamp:
    def test_returns_iso_format_string(self) -> None:
        ts = utc_timestamp()
        assert isinstance(ts, str)
        # ISO 8601 with timezone: e.g. 2026-06-01T12:00:00.123456+00:00
        assert "T" in ts
        assert "+" in ts or "Z" in ts

    def test_monotonic_within_call(self) -> None:
        ts1 = utc_timestamp()
        ts2 = utc_timestamp()
        # They should differ since time moves forward (or equal if very fast)
        assert ts1 <= ts2


# ── Constants ─────────────────────────────────────────────────────────────


class TestProvenanceConstants:
    def test_missing_manifest_hash_is_sentinel_string(self) -> None:
        assert isinstance(MISSING_MANIFEST_HASH, str)
        assert "MISSING" in MISSING_MANIFEST_HASH

    def test_not_applicable_b0_direct_eval_is_sentinel_string(self) -> None:
        assert isinstance(NOT_APPLICABLE_B0_DIRECT_EVAL, str)
        assert "NOT_APPLICABLE" in NOT_APPLICABLE_B0_DIRECT_EVAL

    def test_sentinels_are_distinct(self) -> None:
        assert MISSING_MANIFEST_HASH != NOT_APPLICABLE_B0_DIRECT_EVAL
