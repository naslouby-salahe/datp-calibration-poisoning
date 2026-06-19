from __future__ import annotations

import polars as pl
import pytest

from datp.data.common.storage import (
    assert_no_csv_artifacts,
    read_artifact,
    write_artifact,
)


@pytest.fixture()
def sample_df() -> pl.DataFrame:
    return pl.DataFrame({"feature_a": [1.0, 2.0, 3.0], "feature_b": [4.0, 5.0, 6.0]})


class TestWriteArtifact:
    def test_produces_parquet_file(self, tmp_path, sample_df):
        path = tmp_path / "train.parquet"
        write_artifact(sample_df, path)
        assert path.exists()
        assert path.suffix == ".parquet"

    def test_creates_parent_directories(self, tmp_path, sample_df):
        path = tmp_path / "nested" / "dir" / "cal.parquet"
        write_artifact(sample_df, path)
        assert path.exists()

    def test_raises_on_csv_extension(self, tmp_path, sample_df):
        path = tmp_path / "train.csv"
        with pytest.raises(ValueError, match=r"\.parquet.*\.csv"):
            write_artifact(sample_df, path)

    def test_raises_on_other_extension(self, tmp_path, sample_df):
        path = tmp_path / "train.hdf5"
        with pytest.raises(ValueError, match=r"\.parquet"):
            write_artifact(sample_df, path)

    def test_raises_on_no_extension(self, tmp_path, sample_df):
        path = tmp_path / "train"
        with pytest.raises(ValueError, match=r"\.parquet"):
            write_artifact(sample_df, path)


class TestReadArtifact:
    def test_raises_on_csv_extension(self, tmp_path):
        path = tmp_path / "test_benign.csv"
        with pytest.raises(ValueError, match=r"\.parquet.*\.csv"):
            read_artifact(path)

    def test_raises_on_other_extension(self, tmp_path):
        path = tmp_path / "test_attack.feather"
        with pytest.raises(ValueError, match=r"\.parquet"):
            read_artifact(path)

    def test_raises_file_not_found(self, tmp_path):
        path = tmp_path / "missing.parquet"
        with pytest.raises(FileNotFoundError):
            read_artifact(path)


class TestRoundTrip:
    def test_parquet_only(self, tmp_path, sample_df):
        path = tmp_path / "test_benign.parquet"
        write_artifact(sample_df, path)
        result = read_artifact(path)
        from polars.testing import assert_frame_equal

        assert_frame_equal(result, sample_df)

    def test_preserves_dtypes(self, tmp_path):
        df = pl.DataFrame(
            {
                "int_col": [1, 2, 3],
                "float_col": [1.1, 2.2, 3.3],
                "str_col": ["a", "b", "c"],
            },
            schema={"int_col": pl.Int64, "float_col": pl.Float64, "str_col": pl.String},
        )
        path = tmp_path / "cal.parquet"
        write_artifact(df, path)
        result = read_artifact(path)
        from polars.testing import assert_frame_equal

        assert_frame_equal(result, df)


class TestAssertNoCsvArtifacts:
    def test_passes_on_parquet_only(self, tmp_path, sample_df):
        write_artifact(sample_df, tmp_path / "train.parquet")
        write_artifact(sample_df, tmp_path / "cal.parquet")
        assert_no_csv_artifacts(tmp_path)  # should not raise

    def test_passes_on_empty_directory(self, tmp_path):
        assert_no_csv_artifacts(tmp_path)  # should not raise

    def test_passes_on_nonexistent_directory(self, tmp_path):
        assert_no_csv_artifacts(tmp_path / "does_not_exist")  # should not raise

    def test_fails_if_csv_present(self, tmp_path, sample_df):
        write_artifact(sample_df, tmp_path / "train.parquet")
        (tmp_path / "leftover.csv").write_text("a,b\n1,2\n")
        with pytest.raises(RuntimeError, match=r"CSV files found"):
            assert_no_csv_artifacts(tmp_path)

    def test_fails_on_nested_csv(self, tmp_path, sample_df):
        sub = tmp_path / "client_0"
        sub.mkdir()
        write_artifact(sample_df, sub / "test_attack.parquet")
        (sub / "stale.csv").write_text("x\n1\n")
        with pytest.raises(RuntimeError, match=r"CSV files found"):
            assert_no_csv_artifacts(tmp_path)
