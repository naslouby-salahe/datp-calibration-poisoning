from __future__ import annotations

from pathlib import Path

import joblib
import polars as pl
from sklearn.preprocessing import StandardScaler

from datp.core.errors import fmt_missing


def _frame_to_numpy(df: pl.DataFrame):
    return df.to_numpy()


def _frame_columns(df: pl.DataFrame) -> list[str]:
    return list(df.columns)


def fit_scaler(train_df: pl.DataFrame) -> StandardScaler:
    scaler = StandardScaler()
    if len(train_df) > 0:
        scaler.fit(_frame_to_numpy(train_df))
    return scaler


def apply_scaler(df: pl.DataFrame, scaler: StandardScaler) -> pl.DataFrame:
    columns = _frame_columns(df)
    if len(df) == 0:
        return pl.DataFrame(schema={column: pl.Float64 for column in columns})
    scaled = scaler.transform(_frame_to_numpy(df))
    return pl.DataFrame(scaled, schema=columns)


def save_scaler(scaler: StandardScaler, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    joblib.dump(scaler, tmp_path)
    tmp_path.rename(path)


def load_scaler(path: Path) -> StandardScaler:
    if not path.exists():
        raise FileNotFoundError(fmt_missing("data.scaling", str(path)))
    return joblib.load(path)
