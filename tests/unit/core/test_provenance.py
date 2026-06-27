"""Tests verifying SHA256 hashing, timestamping, and git metadata provenance utilities."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from datp.core.provenance import (
    MISSING_MANIFEST_HASH,
    array_hash,
    git_commit,
    hash_file,
    hash_jsonable,
    sha256_bytes,
    source_hash,
    utc_timestamp,
)


class TestSha256Bytes:
    """Tests verifying the deterministic SHA256 bytes hashing utility."""

    def test_deterministic(self) -> None:
        """Verify that hashing identical bytes yields the identical hash string."""
        payload = b"hello world"
        assert sha256_bytes(payload) == sha256_bytes(payload)

    def test_different_content_different_hash(self) -> None:
        """Ensure distinct byte contents result in different hashes."""
        assert sha256_bytes(b"a") != sha256_bytes(b"b")

    def test_output_is_64_char_hex(self) -> None:
        """Ensure output hash is a valid 64-character hexadecimal representation."""
        assert len(sha256_bytes(b"test")) == 64
        int(sha256_bytes(b"test"), 16)


class TestHashFile:
    """Tests verifying file-based hashing functionality and nonexistent file handling."""

    def test_deterministic(self, tmp_path: Path) -> None:
        """Verify file hashing is deterministic for identical file contents."""
        f = tmp_path / "data.bin"
        f.write_bytes(b"deterministic content")
        assert hash_file(f) == hash_file(f)

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        """Ensure files with different contents yield different hash strings."""
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(b"content A")
        f2.write_bytes(b"content B")
        assert hash_file(f1) != hash_file(f2)

    def test_missing_file_returns_missing_sentinel(self, tmp_path: Path) -> None:
        """Confirm hashing a nonexistent file returns the 'MISSING' sentinel."""
        assert hash_file(tmp_path / "nonexistent.bin") == "MISSING"

    def test_empty_file(self, tmp_path: Path) -> None:
        """Verify hashing an empty file returns the correct SHA256 of empty bytes."""
        f = tmp_path / "empty.bin"
        f.write_bytes(b"")
        result = hash_file(f)
        assert len(result) == 64
        assert (
            result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )

    def test_output_is_64_char_hex(self, tmp_path: Path) -> None:
        """Confirm output hash for a valid file is 64 characters long."""
        f = tmp_path / "f.bin"
        f.write_bytes(b"test")
        assert len(hash_file(f)) == 64


class TestHashJsonable:
    """Tests verifying dict/list JSON-serializable object hashing."""

    def test_deterministic(self) -> None:
        """Verify jsonable hashing is deterministic for identical structured payloads."""
        payload = {"a": 1, "b": [2, 3]}
        assert hash_jsonable(payload) == hash_jsonable(payload)

    def test_sort_key_independent(self) -> None:
        """Ensure hashing is independent of key order for dictionary inputs."""
        assert hash_jsonable({"b": 2, "a": 1}) == hash_jsonable({"a": 1, "b": 2})

    def test_different_content_different_hash(self) -> None:
        """Ensure changing JSON dictionary contents changes the hash."""
        assert hash_jsonable({"x": 1}) != hash_jsonable({"x": 2})

    def test_nested_structures(self) -> None:
        """Verify nested structures can be hashed successfully."""
        h = hash_jsonable({"nested": {"list": [1, 2, 3]}, "str": "hello"})
        assert len(h) == 64

    def test_non_serializable_falls_back_to_str(self, tmp_path: Path) -> None:
        """Confirm fallback to string representation for non-serializable types."""
        result = hash_jsonable({tmp_path})
        assert len(result) == 64


class TestGitCommit:
    """Tests verifying Git commit SHA-1 retrieval."""

    def test_returns_hex_or_sentinel(self) -> None:
        """Ensure git commit retrieval returns a valid 40-character hex or fallback string."""
        result = git_commit()
        assert len(result) == 40 or result == "GIT_UNAVAILABLE"


class TestSourceHash:
    """Tests verifying source code file bundle hashing."""

    def test_deterministic(self, tmp_path: Path) -> None:
        """Ensure source hash is deterministic for a constant set of file paths."""
        f = tmp_path / "src.py"
        f.write_text("print(1)")
        assert source_hash([f]) == source_hash([f])

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        """Verify modifying source file content alters the computed source hash."""
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("x=1")
        f2.write_text("x=2")
        assert source_hash([f1]) != source_hash([f2])

    def test_multiple_files(self, tmp_path: Path) -> None:
        """Verify that source hash accounts for all input files in the list."""
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("x=1")
        f2.write_text("y=2")
        h_both = source_hash([f1, f2])
        h_one = source_hash([f1])
        assert h_both != h_one

    def test_path_order_matters(self, tmp_path: Path) -> None:
        """Confirm file sequence order affects the compiled source hash."""
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("x=1")
        f2.write_text("y=2")
        assert source_hash([f1, f2]) != source_hash([f2, f1])


class TestArrayHash:
    """Tests verifying NumPy array hashing and dtype normalization."""

    def test_deterministic(self) -> None:
        """Verify array hashing is deterministic for a constant NumPy array."""
        arr = np.array([1.0, 2.0, 3.0])
        assert array_hash(arr) == array_hash(arr)

    def test_different_content_different_hash(self) -> None:
        """Ensure distinct array content changes the array hash."""
        assert array_hash(np.array([1.0])) != array_hash(np.array([2.0]))

    def test_dtype_normalization_float32_to_float64(self) -> None:
        """Verify array hashing normalizes float32 and float64 arrays to same hash."""
        arr32 = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        arr64 = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        assert array_hash(arr32) == array_hash(arr64)

    def test_output_is_64_char_hex(self) -> None:
        """Ensure array hash output is a 64-character hex string."""
        assert len(array_hash(np.array([1.0]))) == 64

    def test_multidimensional(self) -> None:
        """Verify multidimensional arrays are flattened or normalized for hashing."""
        arr = np.array([[1.0, 2.0], [3.0, 4.0]])
        assert len(array_hash(arr)) == 64


class TestUtcTimestamp:
    """Tests verifying ISO-formatted UTC timestamp generation."""

    def test_returns_iso_format_string(self) -> None:
        """Confirm utc_timestamp returns a valid ISO-8601 datetime string."""
        ts = utc_timestamp()
        assert isinstance(ts, str)
        assert "T" in ts
        assert "+" in ts or "Z" in ts


class TestProvenanceConstants:
    """Tests verifying static provenance sentinel constants."""

    def test_missing_manifest_hash_is_sentinel_string(self) -> None:
        """Ensure MISSING_MANIFEST_HASH is the correct string sentinel."""
        assert isinstance(MISSING_MANIFEST_HASH, str)
        assert "MISSING" in MISSING_MANIFEST_HASH
