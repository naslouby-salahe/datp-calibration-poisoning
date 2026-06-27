"""Unit tests for feature scaling and normalization."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
import pytest
from sklearn.preprocessing import StandardScaler

from datp.data.scaling import apply_scaler, fit_scaler, load_scaler, save_scaler


class TestFitScaler:
    """Scaler fitting on training data."""

    def test_fitted_on_train_only(self) -> None:
        rng = np.random.default_rng(7)
        cols = [f"f{i}" for i in range(5)]
        train_df = pd.DataFrame(
            rng.standard_normal((200, 5)) * 3 + 10, columns=pd.Index(cols)
        )
        other_df = pd.DataFrame(
            rng.standard_normal((100, 5)) * 0.5 - 5, columns=pd.Index(cols)
        )

        scaler = fit_scaler(pl.from_pandas(train_df))

        assert scaler.mean_ is not None
        assert scaler.scale_ is not None
        np.testing.assert_allclose(
            np.asarray(scaler.mean_), train_df.to_numpy().mean(axis=0), atol=1e-10
        )
        np.testing.assert_allclose(
            np.asarray(scaler.scale_),
            train_df.to_numpy().std(axis=0, ddof=0),
            atol=1e-10,
        )

        scaled_train = apply_scaler(pl.from_pandas(train_df), scaler)
        np.testing.assert_allclose(
            scaled_train.to_numpy().mean(axis=0), 0.0, atol=1e-10
        )
        np.testing.assert_allclose(
            scaled_train.to_numpy().std(axis=0, ddof=0), 1.0, atol=1e-10
        )

        scaled_other = apply_scaler(pl.from_pandas(other_df), scaler)
        assert not np.allclose(scaled_other.to_numpy().mean(axis=0), 0.0, atol=0.5)

    def test_fit_empty_dataframe(self) -> None:
        df = pl.DataFrame(schema={"a": pl.Float64, "b": pl.Float64})
        scaler = fit_scaler(df)

        with pytest.raises(Exception):
            _ = scaler.mean_


class TestApplyScaler:
    """Scaler application to new data."""

    def test_apply_preserves_columns(self) -> None:
        cols = ["alpha", "beta", "gamma"]
        df = pd.DataFrame(np.ones((10, 3)), columns=pd.Index(cols))
        scaler = fit_scaler(pl.from_pandas(df))
        result = apply_scaler(pl.from_pandas(df), scaler)
        assert list(result.columns) == cols

    def test_apply_empty_dataframe(self) -> None:
        cols = ["x", "y"]
        df = pl.DataFrame(schema={"x": pl.Float64, "y": pl.Float64})
        scaler = StandardScaler()
        scaler.mean_ = np.array([1.0, 2.0])
        scaler.scale_ = np.array([0.5, 0.5])
        result = apply_scaler(df, scaler)
        assert len(result) == 0
        assert list(result.columns) == cols


class TestSaveLoadScaler:
    """Scaler save and load round-trip."""

    def test_round_trip(self, tmp_path: Path) -> None:
        rng = np.random.default_rng(8)
        cols = [f"f{i}" for i in range(5)]
        train_df = pd.DataFrame(rng.standard_normal((100, 5)), columns=pd.Index(cols))

        scaler = fit_scaler(pl.from_pandas(train_df))
        path = tmp_path / "scaler.pkl"
        save_scaler(scaler, path)
        loaded = load_scaler(path)

        assert loaded.mean_ is not None
        assert loaded.scale_ is not None
        assert scaler.mean_ is not None
        assert scaler.scale_ is not None
        np.testing.assert_allclose(np.asarray(loaded.mean_), np.asarray(scaler.mean_))
        np.testing.assert_allclose(np.asarray(loaded.scale_), np.asarray(scaler.scale_))

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        rng = np.random.default_rng(1)
        cols = ["a"]
        df = pd.DataFrame(rng.standard_normal((10, 1)), columns=pd.Index(cols))
        scaler = fit_scaler(pl.from_pandas(df))

        nested = tmp_path / "deep" / "nested" / "scaler.pkl"
        save_scaler(scaler, nested)
        assert nested.exists()

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.pkl"
        with pytest.raises(FileNotFoundError):
            load_scaler(missing)
