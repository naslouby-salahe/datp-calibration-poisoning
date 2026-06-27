"""N-BaIoT preprocessing: CSV loading, splitting, scaling, and artifact writing."""

from __future__ import annotations

import math
from pathlib import Path

import polars as pl
from sklearn.preprocessing import StandardScaler

from datp.artifacts.names import ArtifactFile
from datp.core.logging import get_logger
from datp.data.artifacts import create_empty_feature_frame, write_client_splits
from datp.data.catalog import SplitPolicyRole
from datp.data.contracts import PartitionResult
from datp.data.datasets.nbaiot.spec import (
    ATTACK_FAMILY_DIRS,
    BENIGN_TRAFFIC_FILE,
    DEVICE_DIRS,
    FEATURE_COUNT,
    NBAIOT_SPEC,
    SPLIT_RATIOS,
)
from datp.data.manifests import create_manifest
from datp.data.scaling import apply_scaler, fit_scaler
from datp.data.splits import Split

logger = get_logger(__name__)
_NBAIOT_MODULE = "data.nbaiot"


def _raw_nbaiot_files(raw_dir: Path) -> list[Path]:
    """Collect all existing raw CSV files across devices and attack families."""
    files = []
    for device_id in DEVICE_DIRS:
        device_dir = raw_dir / device_id
        files.append(device_dir / BENIGN_TRAFFIC_FILE)
        for attack_family_dir in ATTACK_FAMILY_DIRS:
            files.extend(sorted((device_dir / attack_family_dir).glob("*.csv")))
    return [path for path in files if path.exists()]


def _compute_split_indices(n: int) -> dict[str, tuple[int, int]]:
    """Compute chronological split boundaries from the configured ratios."""
    indices = {}
    start = 0
    for role in (
        SplitPolicyRole.TRAIN,
        SplitPolicyRole.GAP1,
        SplitPolicyRole.CAL,
        SplitPolicyRole.GAP2,
    ):
        end = start + math.floor(n * SPLIT_RATIOS[role])
        indices[role.value] = (start, end)
        start = end
    indices[SplitPolicyRole.TEST_BENIGN.value] = (start, n)
    return indices


def _load_attack_csvs(device_dir: Path) -> tuple[pl.DataFrame, list[str]]:
    """Load all attack CSV files for a device and return a concatenated frame with class labels."""
    attack_frames, attack_classes = [], []
    for family in ATTACK_FAMILY_DIRS:
        family_path = device_dir / family
        if not family_path.is_dir():
            continue
        for csv_file in sorted(family_path.glob("*.csv")):
            attack_frames.append(pl.read_csv(csv_file))
            attack_classes.append(f"{family.replace('_attacks', '')}_{csv_file.stem}")

    df = pl.concat(attack_frames) if attack_frames else pl.DataFrame()
    return df, sorted(set(attack_classes))


def _scale_device_splits(
    *,
    train_df: pl.DataFrame,
    cal_df: pl.DataFrame,
    test_benign_df: pl.DataFrame,
    attack_df_raw: pl.DataFrame,
    feature_cols: list[str],
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame, StandardScaler]:
    """Fit a scaler on the training split and transform all splits."""
    scaler = fit_scaler(train_df)
    test_attack_scaled = (
        apply_scaler(attack_df_raw, scaler)
        if len(attack_df_raw) > 0
        else create_empty_feature_frame(feature_cols)
    )
    return (
        apply_scaler(train_df, scaler),
        apply_scaler(cal_df, scaler),
        apply_scaler(test_benign_df, scaler),
        test_attack_scaled,
        scaler,
    )


def _prepare_device(
    device_id: str,
    raw_dir: Path,
    output_dir: Path,
    n_min: int,
    seed: int,
    *,
    balanced_test: bool,
) -> PartitionResult:
    """Load, split, scale, and write artifacts for a single N-BaIoT device."""
    device_raw = raw_dir / device_id
    benign_csv = device_raw / BENIGN_TRAFFIC_FILE
    if not benign_csv.exists():
        raise FileNotFoundError(f"[{_NBAIOT_MODULE}] {str(benign_csv)} not found.")

    benign_df = pl.read_csv(benign_csv)
    n_benign = len(benign_df)
    logger.info(
        "device loaded",
        device=device_id,
        n_benign=n_benign,
        n_features=len(benign_df.columns),
    )

    attack_df_raw, attack_classes = _load_attack_csvs(device_raw)
    splits = _compute_split_indices(n_benign)

    train_df = benign_df.slice(
        splits["train"][0], splits["train"][1] - splits["train"][0]
    )
    cal_df = benign_df.slice(splits["cal"][0], splits["cal"][1] - splits["cal"][0])
    test_benign_df = benign_df.slice(
        splits["test_benign"][0], splits["test_benign"][1] - splits["test_benign"][0]
    )

    calibration_pending = len(cal_df) < n_min
    logger.warning(
        "device flagged as Calibration-Pending",
        device=device_id,
        cal_count=len(cal_df),
        n_min=n_min,
    ) if calibration_pending else logger.info(
        "device eligible", device=device_id, cal_count=len(cal_df), n_min=n_min
    )

    train_scaled, cal_scaled, test_benign_scaled, test_attack_scaled, scaler = (
        _scale_device_splits(
            train_df=train_df,
            cal_df=cal_df,
            test_benign_df=test_benign_df,
            attack_df_raw=attack_df_raw,
            feature_cols=benign_df.columns,
        )
    )

    if balanced_test and 0 < len(test_attack_scaled) < len(test_benign_scaled):
        logger.info(
            "balanced-test sensitivity: subsampled benign test",
            device=device_id,
            n=len(test_attack_scaled),
        )
        test_benign_scaled = test_benign_scaled.sample(
            n=len(test_attack_scaled), seed=seed, with_replacement=False
        )

    write_client_splits(
        client_dir=output_dir / device_id,
        splits={
            Split.TRAIN: train_scaled,
            Split.CAL: cal_scaled,
            Split.TEST_BENIGN: test_benign_scaled,
            Split.TEST_ATTACK: test_attack_scaled,
        },
        spec=NBAIOT_SPEC,
        scaler=scaler,
    )

    logger.info(
        "device prepared",
        device=device_id,
        train=len(train_scaled),
        cal=len(cal_scaled),
        test_benign=len(test_benign_scaled),
        test_attack=len(test_attack_scaled),
        attacks=attack_classes,
    )
    return PartitionResult(
        benign_train_count=len(train_scaled),
        benign_cal_count=len(cal_scaled),
        test_benign_count=len(test_benign_scaled),
        test_attack_count=len(test_attack_scaled),
        attack_classes=attack_classes,
        calibration_pending=calibration_pending,
        split_indices=splits,
    )


def prepare_nbaiot(
    raw_dir: Path, output_dir: Path, n_min: int, seed: int, *, balanced_test: bool
) -> dict[str, PartitionResult]:
    """Preprocess all N-BaIoT devices, write manifests, and return partition results."""
    raw_dir, output_dir = Path(raw_dir), Path(output_dir)
    if not raw_dir.is_dir():
        raise FileNotFoundError(
            f"[{_NBAIOT_MODULE}] Raw N-BaIoT directory {raw_dir} not found."
        )

    results = {
        dev: _prepare_device(
            dev, raw_dir, output_dir, n_min, seed, balanced_test=balanced_test
        )
        for dev in DEVICE_DIRS
    }

    logger.info(
        "N-BaIoT preparation complete",
        eligible=sum(not v.calibration_pending for v in results.values()),
        pending=sum(v.calibration_pending for v in results.values()),
        total=len(results),
    )

    create_manifest(
        dataset=NBAIOT_SPEC.id.value,
        raw_files=_raw_nbaiot_files(raw_dir),
        raw_base_dir=raw_dir,
        metadata={
            "dataset_display_name": NBAIOT_SPEC.display_name,
            "n_devices": len(results),
            "n_features": FEATURE_COUNT,
            "split_indices": {
                dev: {k: list(v) for k, v in res.split_indices.items()}
                for dev, res in results.items()
                if res.split_indices
            },
        },
        manifest_path=output_dir / ArtifactFile.MANIFEST,
    )
    return results
