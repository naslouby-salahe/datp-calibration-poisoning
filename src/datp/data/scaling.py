
from __future__ import annotations

from pathlib import Path

import joblib
import polars as pl
from sklearn.preprocessing import StandardScaler


def fit_scaler(train_df: pl.DataFrame) -> StandardScaler:
    scaler = StandardScaler()
    if not train_df.is_empty():
        scaler.fit(train_df.to_numpy())
    return scaler


def apply_scaler(df: pl.DataFrame, scaler: StandardScaler) -> pl.DataFrame:
    if df.is_empty():
        return pl.DataFrame(schema={col: pl.Float64 for col in df.columns})
    return pl.DataFrame(scaler.transform(df.to_numpy()), schema=df.columns)


def save_scaler(scaler: StandardScaler, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    joblib.dump(scaler, tmp_path)
    tmp_path.rename(path)


def load_scaler(path: Path) -> StandardScaler:
    if not path.exists():
        raise FileNotFoundError(f"[data.scaling] {path} not found.")
    return joblib.load(path)
