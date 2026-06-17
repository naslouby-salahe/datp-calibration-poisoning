"""Tests for datp.scoring.loading — ScoreProvider, read_score_column, load_parquets_from_dir."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from datp.core.enums import ScoringStage
from datp.scoring.loading import (
    ScoreProvider,
    load_parquets_from_dir,
    read_score_column,
)
from datp.scoring.schema import SCORE_COLUMN
from tests.unit.conftest import _write_score_artifact

# ── read_score_column ─────────────────────────────────────────────────────


class TestReadScoreColumn:
    def test_reads_score_column(self, tmp_path: Path) -> None:
        path = tmp_path / "scores.parquet"
        _write_score_artifact(path, [0.1, 0.2, 0.3])
        result = read_score_column(path)
        assert result.dtype == np.float64
        np.testing.assert_allclose(result, [0.1, 0.2, 0.3], rtol=1e-5)

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_score_column(tmp_path / "nonexistent.parquet")

    def test_raises_on_wrong_schema(self, tmp_path: Path) -> None:
        import pyarrow as pa
        import pyarrow.parquet as pq

        path = tmp_path / "bad.parquet"
        pq.write_table(pa.table({"wrong_col": pa.array([1.0])}), path)
        with pytest.raises(ValueError, match="schema mismatch"):
            read_score_column(path)

    def test_raises_on_non_float_type(self, tmp_path: Path) -> None:
        import pyarrow as pa
        import pyarrow.parquet as pq

        path = tmp_path / "bad.parquet"
        pq.write_table(pa.table({SCORE_COLUMN: pa.array([1, 2, 3], type=pa.int64())}), path)
        with pytest.raises(TypeError, match="non-floating"):
            read_score_column(path)

    def test_empty_parquet_is_valid(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.parquet"
        _write_score_artifact(path, [])
        result = read_score_column(path)
        assert result.size == 0
        assert result.dtype == np.float64


# ── load_parquets_from_dir ─────────────────────────────────────────────────


class TestLoadParquetsFromDir:
    def test_loads_all_parquets(self, tmp_path: Path) -> None:
        _write_score_artifact(tmp_path / "client_a.parquet", [0.1, 0.2])
        _write_score_artifact(tmp_path / "client_b.parquet", [0.3, 0.4, 0.5])
        result = load_parquets_from_dir(tmp_path)
        assert set(result.keys()) == {"client_a", "client_b"}
        np.testing.assert_allclose(result["client_a"], [0.1, 0.2])
        np.testing.assert_allclose(result["client_b"], [0.3, 0.4, 0.5])

    def test_empty_directory_when_allow_empty_true(self, tmp_path: Path) -> None:
        result = load_parquets_from_dir(tmp_path, allow_empty=True)
        assert result == {}

    def test_empty_directory_when_allow_empty_false(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="No parquet score artifacts"):
            load_parquets_from_dir(tmp_path, allow_empty=False)

    def test_missing_directory(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError, match="score directory"):
            load_parquets_from_dir(missing)

    def test_skips_non_parquet_files(self, tmp_path: Path) -> None:
        _write_score_artifact(tmp_path / "c1.parquet", [0.1])
        (tmp_path / "readme.txt").touch()
        (tmp_path / "subdir").mkdir()
        result = load_parquets_from_dir(tmp_path)
        assert list(result.keys()) == ["c1"]


# ── ScoreProvider ──────────────────────────────────────────────────────────


class TestScoreProvider:
    def test_score_root_property(self, tmp_path: Path) -> None:
        provider = ScoreProvider(tmp_path)
        assert provider.score_root == tmp_path

    def test_missing_benign_raises(self, tmp_path: Path) -> None:
        provider = ScoreProvider(tmp_path)
        with pytest.raises(FileNotFoundError, match="test_benign"):
            provider.load("client_01", ScoringStage.TEST_BENIGN)

    def test_missing_attack_raises(self, tmp_path: Path) -> None:
        provider = ScoreProvider(tmp_path)
        _write_score_artifact(
            tmp_path / ScoringStage.TEST_BENIGN / "c1.parquet", [0.1, 0.2]
        )
        with pytest.raises(FileNotFoundError, match="test_attack"):
            provider.load("c1", ScoringStage.TEST_ATTACK)

    def test_missing_cal_raises(self, tmp_path: Path) -> None:
        provider = ScoreProvider(tmp_path)
        with pytest.raises(FileNotFoundError, match="cal"):
            provider.load("c1", ScoringStage.CAL)

    def test_reads_score_column_only(self, tmp_path: Path) -> None:
        _write_score_artifact(
            tmp_path / ScoringStage.TEST_BENIGN / "c1.parquet", [0.1, 0.2, 0.3]
        )
        provider = ScoreProvider(tmp_path)
        arr = provider.load("c1", ScoringStage.TEST_BENIGN)
        assert arr.dtype == np.float64
        np.testing.assert_allclose(arr, [0.1, 0.2, 0.3], rtol=1e-5)

    def test_empty_attack_artifact_is_valid(self, tmp_path: Path) -> None:
        _write_score_artifact(tmp_path / ScoringStage.TEST_ATTACK / "c1.parquet", [])
        provider = ScoreProvider(tmp_path)
        arr = provider.load("c1", ScoringStage.TEST_ATTACK)
        assert arr.size == 0
        assert arr.dtype == np.float64

    def test_load_test_scores_returns_tuple(self, tmp_path: Path) -> None:
        _write_score_artifact(
            tmp_path / ScoringStage.TEST_BENIGN / "c1.parquet", [0.1, 0.2]
        )
        _write_score_artifact(
            tmp_path / ScoringStage.TEST_ATTACK / "c1.parquet", [0.5, 0.9]
        )
        provider = ScoreProvider(tmp_path)
        benign, attack = provider.load_test_scores("c1")
        assert benign.size == 2
        assert attack.size == 2

    def test_score_provider_has_no_cache_state(self, tmp_path: Path) -> None:
        provider = ScoreProvider(tmp_path)
        assert not hasattr(provider, "_lru")

    def test_shared_provider_across_baselines(self, tmp_path: Path) -> None:
        _write_score_artifact(tmp_path / ScoringStage.TEST_BENIGN / "c1.parquet", [0.1])
        _write_score_artifact(tmp_path / ScoringStage.TEST_ATTACK / "c1.parquet", [0.5])
        provider = ScoreProvider(tmp_path)
        b, a = provider.load_test_scores("c1")
        b2, a2 = provider.load_test_scores("c1")
        np.testing.assert_allclose(b, b2)
        np.testing.assert_allclose(a, a2)
