from __future__ import annotations

import math
from pathlib import Path

import polars as pl

from datp.artifacts.names import ArtifactFile
from datp.core.errors import fmt, fmt_missing
from datp.core.logging import get_logger
from datp.data.artifacts import create_empty_feature_frame, write_client_splits
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
from sklearn.preprocessing import StandardScaler
from datp.data.splits import Split
from datp.data.catalog import SplitPolicyRole

logger = get_logger(__name__)
_NBAIOT_MODULE = "data.nbaiot"


def _raw_nbaiot_files(raw_dir: Path) -> list[Path]:
    files: list[Path] = []
    for device_id in DEVICE_DIRS:
        device_dir = raw_dir / device_id
        files.append(device_dir / BENIGN_TRAFFIC_FILE)
        for attack_family_dir in ATTACK_FAMILY_DIRS:
            files.extend(sorted((device_dir / attack_family_dir).glob("*.csv")))
    return [path for path in files if path.exists()]


def _assert_contiguous(
    indices: dict[SplitPolicyRole, tuple[int, int]],
    predecessor: SplitPolicyRole,
    successor: SplitPolicyRole,
    label: str,
) -> None:
    if indices[successor][0] != indices[predecessor][1]:
        raise ValueError(
            fmt(
                _NBAIOT_MODULE, f"{label} alignment error", f"{label} contiguous", "gap"
            )
        )


def _compute_split_indices(n: int) -> dict[str, tuple[int, int]]:
    n_train = math.floor(n * SPLIT_RATIOS[SplitPolicyRole.TRAIN])
    n_gap1 = math.floor(n * SPLIT_RATIOS[SplitPolicyRole.GAP1])
    n_cal = math.floor(n * SPLIT_RATIOS[SplitPolicyRole.CAL])
    n_gap2 = math.floor(n * SPLIT_RATIOS[SplitPolicyRole.GAP2])

    train_start = 0
    train_end = n_train
    gap1_end = train_end + n_gap1
    cal_start = gap1_end
    cal_end = cal_start + n_cal
    gap2_end = cal_end + n_gap2
    test_start = gap2_end
    test_end = n

    indices = {
        SplitPolicyRole.TRAIN: (train_start, train_end),
        SplitPolicyRole.GAP1: (train_end, gap1_end),
        SplitPolicyRole.CAL: (cal_start, cal_end),
        SplitPolicyRole.GAP2: (cal_end, gap2_end),
        SplitPolicyRole.TEST_BENIGN: (test_start, test_end),
    }

    _assert_contiguous(indices, SplitPolicyRole.TRAIN, SplitPolicyRole.GAP1, "Gap1")
    _assert_contiguous(indices, SplitPolicyRole.GAP1, SplitPolicyRole.CAL, "Cal")
    _assert_contiguous(indices, SplitPolicyRole.CAL, SplitPolicyRole.GAP2, "Gap2")
    _assert_contiguous(
        indices, SplitPolicyRole.GAP2, SplitPolicyRole.TEST_BENIGN, "Test"
    )
    return {role.value: bounds for role, bounds in indices.items()}


def _load_attack_csvs(device_dir: Path) -> tuple[pl.DataFrame, list[str]]:
    attack_frames: list[pl.DataFrame] = []
    attack_classes: list[str] = []

    for attack_family_dir in ATTACK_FAMILY_DIRS:
        family_path = device_dir / attack_family_dir
        if not family_path.is_dir():
            continue
        for csv_file in sorted(family_path.glob("*.csv")):
            df = pl.read_csv(csv_file)
            attack_frames.append(df)
            attack_classes.append(
                f"{attack_family_dir.replace('_attacks', '')}_{csv_file.stem}"
            )

    if attack_frames:
        return pl.concat(attack_frames), sorted(set(attack_classes))
    return pl.DataFrame(), []


def _scale_device_splits(
    *,
    train_df: pl.DataFrame,
    cal_df: pl.DataFrame,
    test_benign_df: pl.DataFrame,
    attack_df_raw: pl.DataFrame,
    feature_cols: list[str],
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame, StandardScaler]:
    scaler = fit_scaler(train_df)
    train_scaled = apply_scaler(train_df, scaler)
    cal_scaled = apply_scaler(cal_df, scaler)
    test_benign_scaled = apply_scaler(test_benign_df, scaler)
    test_attack_scaled = (
        apply_scaler(attack_df_raw, scaler)
        if len(attack_df_raw) > 0
        else create_empty_feature_frame(feature_cols)
    )
    return train_scaled, cal_scaled, test_benign_scaled, test_attack_scaled, scaler


def _maybe_subsample_benign_test(
    test_benign_scaled: pl.DataFrame,
    test_attack_scaled: pl.DataFrame,
    *,
    seed: int,
    device_id: str,
) -> pl.DataFrame:
    if len(test_attack_scaled) == 0:
        return test_benign_scaled
    n_attack = len(test_attack_scaled)
    if len(test_benign_scaled) <= n_attack:
        return test_benign_scaled
    logger.info(
        "balanced-test sensitivity: subsampled benign test to match attack count",
        device=device_id,
        n=n_attack,
    )
    return test_benign_scaled.sample(n=n_attack, seed=seed, with_replacement=False)


def _prepare_device(
    device_id: str,
    raw_dir: Path,
    output_dir: Path,
    n_min: int,
    seed: int,
    *,
    balanced_test: bool,
) -> PartitionResult:

    device_raw = raw_dir / device_id
    device_out = output_dir / device_id

    benign_csv = device_raw / BENIGN_TRAFFIC_FILE
    if not benign_csv.exists():
        raise FileNotFoundError(fmt_missing(_NBAIOT_MODULE, str(benign_csv)))
    benign_df = pl.read_csv(benign_csv)
    feature_cols = benign_df.columns
    n_benign = len(benign_df)
    logger.info(
        "device loaded",
        device=device_id,
        n_benign=n_benign,
        n_features=len(feature_cols),
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

    cal_count = len(cal_df)
    calibration_pending = cal_count < n_min
    if calibration_pending:
        logger.warning(
            "device flagged as Calibration-Pending",
            device=device_id,
            cal_count=cal_count,
            n_min=n_min,
        )
    else:
        logger.info(
            "device eligible", device=device_id, cal_count=cal_count, n_min=n_min
        )

    train_scaled, cal_scaled, test_benign_scaled, test_attack_scaled, scaler = (
        _scale_device_splits(
            train_df=train_df,
            cal_df=cal_df,
            test_benign_df=test_benign_df,
            attack_df_raw=attack_df_raw,
            feature_cols=feature_cols,
        )
    )

    if balanced_test:
        test_benign_scaled = _maybe_subsample_benign_test(
            test_benign_scaled, test_attack_scaled, seed=seed, device_id=device_id
        )

    write_client_splits(
        client_dir=device_out,
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
        benign_cal_count=cal_count,
        test_benign_count=len(test_benign_scaled),
        test_attack_count=len(test_attack_scaled),
        attack_classes=attack_classes,
        calibration_pending=calibration_pending,
        split_indices=splits,
    )


def prepare_nbaiot(
    raw_dir: Path,
    output_dir: Path,
    n_min: int,
    seed: int,
    *,
    balanced_test: bool,
) -> dict[str, PartitionResult]:
    raw_dir = Path(raw_dir)
    output_dir = Path(output_dir)

    if not raw_dir.is_dir():
        raise FileNotFoundError(
            fmt_missing(_NBAIOT_MODULE, f"Raw N-BaIoT directory {raw_dir}")
        )

    results: dict[str, PartitionResult] = {}
    for device_id in DEVICE_DIRS:
        results[device_id] = _prepare_device(
            device_id, raw_dir, output_dir, n_min, seed, balanced_test=balanced_test
        )

    eligible = sum(1 for v in results.values() if not v.calibration_pending)
    pending = sum(1 for v in results.values() if v.calibration_pending)
    logger.info(
        "N-BaIoT preparation complete",
        eligible=eligible,
        pending=pending,
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
                dev: {k: list(v) for k, v in result.split_indices.items()}
                for dev, result in results.items()
                if result.split_indices is not None
            },
        },
        manifest_path=output_dir / ArtifactFile.MANIFEST,
    )

    return results
