from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from datp.data.common.schemas import validate_feature_artifact


def _write(path: Path, schema: dict[str, pl.DataType]) -> None:
    pl.DataFrame(schema=schema).write_parquet(path)


class TestValidateFeatureArtifact:
    def test_exact_ordered_schema_passes(self, tmp_path: Path) -> None:
        path = tmp_path / "ok.parquet"
        _write(path, {"a": pl.Float64, "b": pl.Float64, "c": pl.Float64})
        validate_feature_artifact(path, ["a", "b", "c"])

    def test_reordered_columns_fail(self, tmp_path: Path) -> None:
        # Same column set, different order: a set comparison would pass, but the
        # ordered feature-schema contract must reject it.
        path = tmp_path / "reordered.parquet"
        _write(path, {"b": pl.Float64, "a": pl.Float64, "c": pl.Float64})
        with pytest.raises(ValueError, match="schema mismatch"):
            validate_feature_artifact(path, ["a", "b", "c"])

    def test_wrong_column_name_fails(self, tmp_path: Path) -> None:
        path = tmp_path / "wrong_name.parquet"
        _write(path, {"a": pl.Float64, "x": pl.Float64, "c": pl.Float64})
        with pytest.raises(ValueError, match="schema mismatch"):
            validate_feature_artifact(path, ["a", "b", "c"])

    def test_missing_column_fails(self, tmp_path: Path) -> None:
        path = tmp_path / "missing.parquet"
        _write(path, {"a": pl.Float64, "b": pl.Float64})
        with pytest.raises(ValueError, match="schema mismatch"):
            validate_feature_artifact(path, ["a", "b", "c"])

    def test_non_numeric_column_fails(self, tmp_path: Path) -> None:
        path = tmp_path / "non_numeric.parquet"
        _write(path, {"a": pl.Float64, "b": pl.Utf8, "c": pl.Float64})
        with pytest.raises(TypeError, match="non-numeric type"):
            validate_feature_artifact(path, ["a", "b", "c"])

    def test_integer_columns_pass(self, tmp_path: Path) -> None:
        path = tmp_path / "ints.parquet"
        _write(path, {"a": pl.Int64, "b": pl.Float64})
        validate_feature_artifact(path, ["a", "b"])
