"""AE training and calibration use only benign records; attack rows never enter training or threshold estimation."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import polars as pl

from datp.artifacts.names import ArtifactFile
from datp.core.errors import fmt, fmt_missing
from datp.core.logging import get_logger
from datp.data.artifacts import create_empty_feature_frame, write_client_splits
from datp.data.contracts import PartitionResult
from datp.data.datasets.ciciot2023.spec import (
    BENIGN_LABEL,
    CAL_FRACTION,
    CICIOT2023_SPEC,
    EXPECTED_COLUMNS,
    FEATURE_COLUMNS,
    FEATURE_COUNT,
    LABEL_COLUMN,
    RAW_CSV_DIR,
    RAW_MERGED_DIR,
    RAW_MERGED_PATTERN,
    TEST_ATTACK_LABELS_ARTIFACT,
    attack_family,
)
from datp.data.manifests import create_manifest
from datp.data.sampling import apply_ciciot_cap
from datp.data.scaling import apply_scaler, fit_scaler
from sklearn.preprocessing import StandardScaler
from datp.data.splits import Split

logger = get_logger(__name__)
_CICIOT_MODULE = "data.ciciot"


def _clean_client_frame(df: pl.DataFrame, features: list[str]) -> pl.DataFrame:
    before = len(df)

    df = df.with_columns(
        [
            pl.when(pl.col(col).is_infinite())
            .then(None)
            .otherwise(pl.col(col))
            .alias(col)
            for col in features
        ]
    )

    cleaned = df.drop_nulls(subset=[*features, LABEL_COLUMN])
    dropped = before - len(cleaned)
    if dropped > 0:
        logger.warning(
            "dropped CICIoT2023 rows with non-finite or missing values",
            dropped=dropped,
        )
    return cleaned


def _read_client_csv(csv_path: Path) -> pl.DataFrame:
    """Read a CICIoT merged client CSV, tolerating malformed data rows."""
    try:
        return pl.read_csv(csv_path, infer_schema_length=10000, ignore_errors=False)
    except Exception:
        logger.warning(
            "falling back to ignore_errors=True for malformed CICIoT2023 rows",
            file=csv_path.name,
        )
        return pl.read_csv(csv_path, infer_schema_length=10000, ignore_errors=True)


def _validate_sample_rows(csv_file: Path, sample_df: pl.DataFrame) -> None:
    if len(sample_df) == 0:
        raise ValueError(
            fmt(
                _CICIOT_MODULE,
                f"Empty CICIoT2023 CSV: {csv_file.name}",
                "at least 1 sample row",
                "0 rows",
            )
        )

    feature_sample = sample_df.select(list(FEATURE_COLUMNS))
    for col in feature_sample.columns:
        dtype = feature_sample[col].dtype
        if not dtype.is_numeric():
            raise ValueError(
                fmt(
                    _CICIOT_MODULE,
                    f"Non-numeric feature sample in {csv_file.name}",
                    "numeric CICFlowMeter feature columns",
                    f"non-numeric feature value in {col} ({dtype})",
                )
            )

    if sample_df.select(pl.col(LABEL_COLUMN).is_null().any()).item():
        raise ValueError(
            fmt(
                _CICIOT_MODULE,
                f"Missing label sample in {csv_file.name}",
                "non-null Label values",
                "null Label value",
            )
        )


def validate_schema(raw_dir: Path) -> None:
    """Validate 39 features + Label across ALL MERGED_CSV files; raises ValueError on mismatch, FileNotFoundError if no files found."""
    raw_dir = Path(raw_dir)
    merged_dir = raw_dir / RAW_CSV_DIR / RAW_MERGED_DIR
    csv_files = sorted(merged_dir.glob(RAW_MERGED_PATTERN))

    if not csv_files:
        raise FileNotFoundError(
            fmt_missing(_CICIOT_MODULE, f"MERGED_CSV files in {merged_dir}")
        )

    expected_columns = list(EXPECTED_COLUMNS)
    for csv_file in csv_files:
        sample_df = pl.read_csv(csv_file, n_rows=100)
        actual_columns = sample_df.columns
        if actual_columns != expected_columns:
            raise ValueError(
                fmt(
                    _CICIOT_MODULE,
                    f"Schema mismatch in {csv_file.name}",
                    f"columns {expected_columns}",
                    f"columns {actual_columns}",
                )
            )
        _validate_sample_rows(csv_file, sample_df)

    logger.info(
        "CICIoT2023 schema validation passed",
        n_files=len(csv_files),
    )


def _split_benign_features(
    benign_features: pl.DataFrame,
    features: list[str],
    seed: int,
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    n_benign = len(benign_features)
    if n_benign < 3:
        return (
            benign_features,
            create_empty_feature_frame(features),
            create_empty_feature_frame(features),
        )
    n_train = round(n_benign * 0.70)
    n_cal = round(n_benign * CAL_FRACTION)
    shuffled = benign_features.sample(fraction=1.0, seed=seed, with_replacement=False)
    return (
        shuffled.slice(0, n_train),
        shuffled.slice(n_train, n_cal),
        shuffled.slice(n_train + n_cal),
    )


def _scale_ciciot_splits(
    train_df: pl.DataFrame,
    cal_df: pl.DataFrame,
    test_benign_df: pl.DataFrame,
    attack_features: pl.DataFrame,
    features: list[str],
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame, StandardScaler]:
    if len(train_df) > 0:
        scaler = fit_scaler(train_df)
        return (
            apply_scaler(train_df, scaler),
            apply_scaler(cal_df, scaler),
            apply_scaler(test_benign_df, scaler),
            apply_scaler(attack_features, scaler),
            scaler,
        )
    scaler = fit_scaler(pl.DataFrame(np.zeros((1, len(features))), schema=features))
    empty = create_empty_feature_frame(features)
    return empty, empty, empty, empty, scaler


def _resolve_attack_labels(
    client_id: str,
    attack_capped: pl.DataFrame,
) -> tuple[pl.DataFrame, list[str]]:
    if len(attack_capped) == 0:
        return pl.DataFrame({LABEL_COLUMN: pl.Series([], dtype=pl.Utf8)}), []
    attack_labels_series = attack_capped[LABEL_COLUMN]
    unknown = [
        lbl
        for lbl in attack_labels_series.unique().to_list()
        if lbl != BENIGN_LABEL and attack_family(lbl) is None
    ]
    if unknown:
        raise ValueError(
            fmt(
                _CICIOT_MODULE,
                f"Unknown attack labels in {client_id}",
                "labels mappable to a known attack family",
                str(sorted(unknown)),
            )
        )
    return (
        pl.DataFrame({LABEL_COLUMN: attack_labels_series}),
        sorted(attack_labels_series.unique().to_list()),
    )


def _prepare_client(
    client_id: str,
    csv_path: Path,
    output_root: Path,
    cap: int,
    n_min: int,
    seed: int,
    attack_reserve_fraction: float,
) -> PartitionResult:
    client_out = output_root / client_id

    df = _read_client_csv(csv_path)
    features = list(FEATURE_COLUMNS)
    df = df.select([*features, LABEL_COLUMN])
    df = _clean_client_frame(df, features)

    total_benign_pre_cap = df.filter(pl.col(LABEL_COLUMN) == BENIGN_LABEL).height
    total_attack_pre_cap = df.filter(pl.col(LABEL_COLUMN) != BENIGN_LABEL).height

    cal_estimate = math.floor(total_benign_pre_cap * CAL_FRACTION)
    calibration_pending = cal_estimate < n_min

    if calibration_pending:
        logger.warning(
            "client PRE-CAP benign cal estimate below n_min",
            client=client_id,
            cal_estimate=cal_estimate,
            n_min=n_min,
        )

    df_capped = apply_ciciot_cap(
        df,
        cap=cap,
        label_column=LABEL_COLUMN,
        benign_label=BENIGN_LABEL,
        attack_reserve_fraction=attack_reserve_fraction,
        seed=seed,
    )

    benign_capped = df_capped.filter(pl.col(LABEL_COLUMN) == BENIGN_LABEL)
    attack_capped = df_capped.filter(pl.col(LABEL_COLUMN) != BENIGN_LABEL)

    evaluation_incomplete = len(attack_capped) == 0
    if evaluation_incomplete:
        logger.warning("client has zero attack records after cap", client=client_id)

    benign_features = benign_capped.select(features)
    attack_features = attack_capped.select(features)

    train_df, cal_df, test_benign_df = _split_benign_features(
        benign_features, features, seed
    )
    train_scaled, cal_scaled, test_benign_scaled, test_attack_scaled, scaler = (
        _scale_ciciot_splits(
            train_df, cal_df, test_benign_df, attack_features, features
        )
    )

    write_client_splits(
        client_dir=client_out,
        splits={
            Split.TRAIN: train_scaled,
            Split.CAL: cal_scaled,
            Split.TEST_BENIGN: test_benign_scaled,
            Split.TEST_ATTACK: test_attack_scaled,
        },
        spec=CICIOT2023_SPEC,
        scaler=scaler,
    )

    labels_df, attack_categories = _resolve_attack_labels(client_id, attack_capped)
    labels_path = client_out / TEST_ATTACK_LABELS_ARTIFACT
    labels_df.write_parquet(str(labels_path))

    if len(test_attack_scaled) > 0 and len(labels_df) != len(test_attack_scaled):
        raise ValueError(
            fmt(
                _CICIOT_MODULE,
                f"Attack label count mismatch for {client_id}",
                str(len(test_attack_scaled)),
                str(len(labels_df)),
            )
        )

    logger.info(
        "client prepared",
        client=client_id,
        train=len(train_scaled),
        cal=len(cal_scaled),
        test_benign=len(test_benign_scaled),
        test_attack=len(test_attack_scaled),
        cal_pending=calibration_pending,
        eval_incomplete=evaluation_incomplete,
    )

    return PartitionResult(
        total_benign_pre_cap=total_benign_pre_cap,
        total_attack_pre_cap=total_attack_pre_cap,
        benign_train_count=len(train_scaled),
        benign_cal_count=len(cal_scaled),
        test_benign_count=len(test_benign_scaled),
        test_attack_count=len(test_attack_scaled),
        attack_categories=attack_categories,
        calibration_pending=calibration_pending,
        evaluation_incomplete=evaluation_incomplete,
    )


def prepare_ciciot(
    raw_dir: Path,
    output_dir: Path,
    *,
    seed: int,
    cap: int,
    n_min: int,
    attack_reserve_fraction: float,
) -> dict[str, PartitionResult]:
    raw_dir = Path(raw_dir)
    output_dir = Path(output_dir)
    client_root = (
        output_dir
        if output_dir.name == CICIOT2023_SPEC.id.value
        else output_dir / CICIOT2023_SPEC.id.value
    )

    validate_schema(raw_dir)

    merged_dir = raw_dir / RAW_CSV_DIR / RAW_MERGED_DIR
    csv_files = sorted(merged_dir.glob(RAW_MERGED_PATTERN))

    results: dict[str, PartitionResult] = {}
    for csv_file in csv_files:
        client_id = csv_file.stem
        results[client_id] = _prepare_client(
            client_id,
            csv_file,
            client_root,
            cap=cap,
            n_min=n_min,
            seed=seed,
            attack_reserve_fraction=attack_reserve_fraction,
        )

    eligible = sum(1 for v in results.values() if not v.calibration_pending)
    pending = sum(1 for v in results.values() if v.calibration_pending)
    eval_incomplete = sum(1 for v in results.values() if v.evaluation_incomplete)
    logger.info(
        "CICIoT2023 preparation complete",
        eligible=eligible,
        pending=pending,
        eval_incomplete=eval_incomplete,
        total=len(results),
    )

    create_manifest(
        dataset=CICIOT2023_SPEC.id.value,
        raw_files=csv_files,
        raw_base_dir=merged_dir,
        metadata={
            "dataset_display_name": CICIOT2023_SPEC.display_name,
            "n_clients": len(results),
            "n_features": FEATURE_COUNT,
            "cap": cap,
        },
        manifest_path=client_root / ArtifactFile.MANIFEST,
    )

    return results
