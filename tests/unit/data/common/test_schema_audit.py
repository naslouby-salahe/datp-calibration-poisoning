"""Unit tests for data schema audit checks."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from datp.data.common.audit import run_schema_audit


class TestSchemaAuditFeatureCountMismatch:
    """Schema audit detects feature-count mismatches."""

    def test_feature_count_mismatch_parquet(self, tmp_path: Path) -> None:
        rng = np.random.default_rng(42)
        import polars as pl

        df = pl.DataFrame(
            rng.standard_normal((50, 10)),
            schema=[f"feat_{i}" for i in range(10)],
        )
        file_path = tmp_path / "data.parquet"
        df.write_parquet(file_path)

        with pytest.raises(ValueError, match="Feature count mismatch"):
            run_schema_audit(file_path, expected_feature_count=15)

    def test_feature_count_match_passes(self, tmp_path: Path) -> None:
        rng = np.random.default_rng(42)
        import polars as pl

        df = pl.DataFrame(
            rng.standard_normal((50, 115)),
            schema=[f"feat_{i}" for i in range(115)],
        )
        file_path = tmp_path / "data.parquet"
        df.write_parquet(file_path)

        run_schema_audit(file_path, expected_feature_count=115)

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            run_schema_audit(
                tmp_path / "nonexistent.parquet", expected_feature_count=10
            )

    def test_unsupported_format_raises(self, tmp_path: Path) -> None:
        file_path = tmp_path / "data.json"
        file_path.write_text("{}")

        with pytest.raises(ValueError, match="Unsupported file format"):
            run_schema_audit(file_path, expected_feature_count=10)
