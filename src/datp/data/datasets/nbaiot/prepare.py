from __future__ import annotations

from datp.types import (
    ClientId,
    NarrativeText,
    RandomSeed,
    SampleCount,
    SignedCount,
)


import math
from pathlib import Path

import polars as pl
from sklearn.preprocessing import StandardScaler

from datp.core.enums import (
    ArtifactFile,
    ClientStatus,
    NBaIoTBalancePolicy,
    NBaIoTDevice,
    PathToken,
)
from datp.core.logging import get_logger
from datp.data.artifacts import create_empty_feature_frame, write_client_splits
from datp.data.catalog import SplitPolicyRole
from datp.data.contracts import PartitionResult
from datp.data.datasets.nbaiot.spec import (
    ATTACK_FAMILY_DIRS,
    DEVICE_DIRS,
    FEATURE_COUNT,
    NBAIOT_SPEC,
)
from datp.data.manifests import create_manifest
from datp.data.scaling import apply_scaler, fit_scaler
from datp.data.splits import Split

logger = get_logger(__name__)
_NBAIOT_MODULE = "data.nbaiot"


def _raw_nbaiot_files(raw_dir: Path) -> list[Path]:
    files: list[Path] = []
    for device_id in DEVICE_DIRS:
        device_dir = raw_dir / device_id
        files.append(device_dir / ArtifactFile.BENIGN_TRAFFIC)
        for attack_family_dir in ATTACK_FAMILY_DIRS:
            files.extend(sorted((device_dir / attack_family_dir).glob(PathToken.CSV_GLOB)))
    return [path for path in files if path.exists()]


def _compute_split_indices(
    n: SampleCount,
) -> dict[SplitPolicyRole, tuple[SignedCount, SignedCount]]:
    indices: dict[SplitPolicyRole, tuple[SignedCount, SignedCount]] = {}
    start = 0
    for role in (
        SplitPolicyRole.TRAIN,
        SplitPolicyRole.GAP1,
        SplitPolicyRole.CAL,
        SplitPolicyRole.GAP2,
    ):
        end = start + math.floor(n * NBAIOT_SPEC.split_policy.ratios[role])
        indices[role] = (start, end)
        start = end
    indices[SplitPolicyRole.TEST_BENIGN] = (start, n)
    return indices


def _load_attack_csvs(device_dir: Path) -> tuple[pl.DataFrame, list[NarrativeText]]:
    attack_frames: list[pl.DataFrame] = []
    attack_classes: list[NarrativeText] = []
    for family in ATTACK_FAMILY_DIRS:
        family_path = device_dir / family
        if not family_path.is_dir():
            continue
        for csv_file in sorted(family_path.glob(PathToken.CSV_GLOB)):
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
    feature_cols: list[NarrativeText],
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, pl.DataFrame, StandardScaler]:
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
    device_id: NBaIoTDevice,
    raw_dir: Path,
    output_dir: Path,
    n_min: SampleCount,
    seed: RandomSeed,
    *,
    test_balance_policy: NBaIoTBalancePolicy,
) -> PartitionResult:
    device_raw = raw_dir / device_id
    benign_csv = device_raw / ArtifactFile.BENIGN_TRAFFIC
    if not benign_csv.exists():
        raise FileNotFoundError(f"[{_NBAIOT_MODULE}] {benign_csv} not found.")

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
        splits[SplitPolicyRole.TRAIN][0],
        splits[SplitPolicyRole.TRAIN][1] - splits[SplitPolicyRole.TRAIN][0],
    )
    cal_df = benign_df.slice(
        splits[SplitPolicyRole.CAL][0],
        splits[SplitPolicyRole.CAL][1] - splits[SplitPolicyRole.CAL][0],
    )
    test_benign_df = benign_df.slice(
        splits[SplitPolicyRole.TEST_BENIGN][0],
        splits[SplitPolicyRole.TEST_BENIGN][1] - splits[SplitPolicyRole.TEST_BENIGN][0],
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

    if test_balance_policy is NBaIoTBalancePolicy.BALANCED:
        if 0 < len(test_attack_scaled) < len(test_benign_scaled):
            logger.info(
                "balanced-test sensitivity: subsampled benign test",
                device=device_id,
                n=len(test_attack_scaled),
            )
            test_benign_scaled = test_benign_scaled.sample(
                n=len(test_attack_scaled), seed=seed, with_replacement=False
            )
    elif test_balance_policy is not NBaIoTBalancePolicy.NATURAL_DISTRIBUTION:
        raise ValueError(f"Unsupported test balance policy: {test_balance_policy!r}")

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
        status=(
            ClientStatus.CALIBRATION_PENDING
            if calibration_pending
            else ClientStatus.ELIGIBLE
        ),
        split_indices=splits,
    )


def prepare_nbaiot(
    raw_dir: Path,
    output_dir: Path,
    n_min: SampleCount,
    seed: RandomSeed,
    *,
    test_balance_policy: NBaIoTBalancePolicy,
) -> dict[ClientId, PartitionResult]:
    raw_dir, output_dir = Path(raw_dir), Path(output_dir)
    if not raw_dir.is_dir():
        raise FileNotFoundError(
            f"[{_NBAIOT_MODULE}] Raw N-BaIoT directory {raw_dir} not found."
        )

    results = {
        ClientId(dev): _prepare_device(
            dev,
            raw_dir,
            output_dir,
            n_min,
            seed,
            test_balance_policy=test_balance_policy,
        )
        for dev in DEVICE_DIRS
    }

    logger.info(
        "N-BaIoT preparation complete",
        eligible=sum(v.status is ClientStatus.ELIGIBLE for v in results.values()),
        pending=sum(
            v.status is ClientStatus.CALIBRATION_PENDING for v in results.values()
        ),
        total=len(results),
    )

    create_manifest(
        dataset=NBAIOT_SPEC.id,
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
