from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import polars as pl

from datp.artifacts.constants import MANIFEST_FILE
from datp.core.errors import fmt, fmt_missing
from datp.core.logging import get_logger
from datp.data.artifacts import create_empty_feature_frame, write_client_splits
from datp.data.contracts import RegimeCClientSummary, RegimeCResult
from datp.data.datasets.nbaiot.spec import (
    ATTACK_FAMILY_DIRS,
    BENIGN_TRAFFIC_FILE,
    DEVICE_DIRS,
    FEATURE_COUNT,
    NBAIOT_SPEC,
)
from datp.data.manifests import create_manifest
from datp.data.paths import regime_c_prepared_dir
from datp.data.scaling import apply_scaler, fit_scaler
from datp.data.splits import Split
from datp.statistics.divergence import pairwise_js_from_distributions

logger = get_logger(__name__)


def _raw_nbaiot_files(raw_dir: Path) -> list[Path]:
    files: list[Path] = []
    for device_id in DEVICE_DIRS:
        device_dir = raw_dir / device_id
        files.append(device_dir / BENIGN_TRAFFIC_FILE)
        for attack_family_dir in ATTACK_FAMILY_DIRS:
            files.extend(sorted((device_dir / attack_family_dir).glob("*.csv")))
    return [path for path in files if path.exists()]


def _load_benign_records(
    raw_dir: Path,
) -> tuple[dict[str, pl.DataFrame], list[str]]:
    records: dict[str, pl.DataFrame] = {}
    feature_cols: list[str] | None = None

    for device_id in DEVICE_DIRS:
        csv_path = raw_dir / device_id / BENIGN_TRAFFIC_FILE
        if not csv_path.exists():
            raise FileNotFoundError(fmt_missing("data.regime_c", str(csv_path)))
        df = pl.read_csv(csv_path)
        if feature_cols is None:
            feature_cols = df.columns
        records[device_id] = df

    if feature_cols is None:
        raise ValueError(fmt("data.regime_c", "No feature columns found", "non-empty feature columns", "None"))
    return records, feature_cols


def _load_attack_records(
    raw_dir: Path,
    feature_cols: list[str],
) -> dict[str, pl.DataFrame]:
    records: dict[str, pl.DataFrame] = {}

    for device_id in DEVICE_DIRS:
        device_dir = raw_dir / device_id
        frames: list[pl.DataFrame] = []

        for family in ATTACK_FAMILY_DIRS:
            family_dir = device_dir / family
            if not family_dir.is_dir():
                continue
            for csv_file in sorted(family_dir.glob("*.csv")):
                df = pl.read_csv(csv_file)
                frames.append(df)

        if frames:
            records[device_id] = pl.concat(frames)
        else:
            schema = {col: pl.Float64 for col in feature_cols}
            records[device_id] = pl.DataFrame(schema=schema)

    return records


def _stratified_split(
    df: pl.DataFrame,
    device_labels: np.ndarray,
    rng: np.random.Generator,
    train_frac: float,
    cal_frac: float,
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    train_parts = []
    cal_parts = []
    test_parts = []

    unique_devices = np.unique(device_labels)
    for dev in unique_devices:
        dev_indices = np.nonzero(device_labels == dev)[0].copy()
        rng.shuffle(dev_indices)

        n = len(dev_indices)
        n_train = max(1, round(n * train_frac))
        n_cal = max(0, round(n * cal_frac))
        if n_train + n_cal > n:
            n_cal = max(0, n - n_train)

        dev_df = df[dev_indices.tolist()]
        train_parts.append(dev_df.slice(0, n_train))
        if n_cal > 0:
            cal_parts.append(dev_df.slice(n_train, n_cal))
        test_start = n_train + n_cal
        if test_start < n:
            test_parts.append(dev_df.slice(test_start, n - test_start))

    schema = {c: pl.Float64 for c in df.columns}
    train_df = pl.concat(train_parts) if train_parts else pl.DataFrame(schema=schema)
    cal_df = pl.concat(cal_parts) if cal_parts else pl.DataFrame(schema=schema)
    test_df = pl.concat(test_parts) if test_parts else pl.DataFrame(schema=schema)

    return train_df, cal_df, test_df


def _build_client_partition(
    client_idx: int,
    run_dir: Path,
    benign_df: pl.DataFrame,
    device_labs: np.ndarray,
    attack_df: pl.DataFrame,
    feature_cols: list[str],
    n_min: int,
    rng: np.random.Generator,
    train_frac: float,
    cal_frac: float,
    device_names: list[str],
) -> RegimeCClientSummary:
    client_id = f"client_{client_idx:02d}"
    client_dir = run_dir / client_id

    n_devices = len(device_names)
    if len(device_labs) > 0:
        hist = np.bincount(device_labs, minlength=n_devices).astype(float)
        total = hist.sum()
        fractions = hist / total if total > 0 else np.ones(n_devices) / n_devices
    else:
        fractions = np.ones(n_devices) / n_devices
    device_mixture_proportions = {device_names[i]: float(fractions[i]) for i in range(n_devices)}

    train_df, cal_df, test_benign_df = _stratified_split(benign_df, device_labs, rng, train_frac, cal_frac)

    cal_count = len(cal_df)
    calibration_pending = cal_count < n_min
    if calibration_pending:
        logger.warning(
            "client flagged as Calibration-Pending",
            client=client_id, cal_count=cal_count, n_min=n_min,
        )

    if len(train_df) > 0:
        scaler = fit_scaler(train_df)
        train_scaled = apply_scaler(train_df, scaler)
        cal_scaled = apply_scaler(cal_df, scaler) if len(cal_df) > 0 else create_empty_feature_frame(feature_cols)
        test_benign_scaled = apply_scaler(test_benign_df, scaler) if len(test_benign_df) > 0 else create_empty_feature_frame(feature_cols)
        test_attack_scaled = apply_scaler(attack_df, scaler) if len(attack_df) > 0 else create_empty_feature_frame(feature_cols)
    else:
        scaler = None
        train_scaled = create_empty_feature_frame(feature_cols)
        cal_scaled = create_empty_feature_frame(feature_cols)
        test_benign_scaled = create_empty_feature_frame(feature_cols)
        test_attack_scaled = create_empty_feature_frame(feature_cols)

    write_client_splits(
        client_dir=client_dir,
        splits={
            Split.TRAIN: train_scaled,
            Split.CAL: cal_scaled,
            Split.TEST_BENIGN: test_benign_scaled,
            Split.TEST_ATTACK: test_attack_scaled,
        },
        spec=NBAIOT_SPEC,
        scaler=scaler,
    )

    summary = RegimeCClientSummary(
        client_id=client_id,
        train_count=len(train_scaled),
        cal_count=cal_count,
        test_benign_count=len(test_benign_scaled),
        test_attack_count=len(test_attack_scaled),
        calibration_pending=calibration_pending,
        device_mixture_proportions=device_mixture_proportions,
    )
    logger.info(
        "client prepared",
        client=client_id,
        train=summary.train_count, cal=summary.cal_count,
        test_benign=summary.test_benign_count, test_attack=summary.test_attack_count,
        pending=calibration_pending,
    )
    return summary


def _distribute_device_records(
    df: pl.DataFrame,
    proportions: np.ndarray,
    rng: np.random.Generator,
) -> list[pl.DataFrame]:
    n_total = len(df)
    exact_counts = proportions * n_total
    floor_counts = np.floor(exact_counts).astype(int)
    remainders = exact_counts - floor_counts
    remaining = n_total - np.sum(floor_counts)

    if remaining > 0:
        indices = np.argsort(remainders)[::-1]
        floor_counts[indices[:remaining]] += 1

    parts = []
    shuffled_df = df.sample(fraction=1.0, seed=int(rng.integers(0, 1000000)), with_replacement=False)

    start = 0
    for count in floor_counts:
        parts.append(shuffled_df.slice(start, count))
        start += count

    return parts

def _distribute_dataset_with_labels(
    dataset_by_device: dict[str, pl.DataFrame],
    proportions: np.ndarray,
    device_names: list[str],
    n_clients: int,
    rng: np.random.Generator,
    feature_cols: list[str],
) -> tuple[list[pl.DataFrame], list[np.ndarray]]:
    client_dfs: list[list[pl.DataFrame]] = [[] for _ in range(n_clients)]
    client_labels: list[list[np.ndarray]] = [[] for _ in range(n_clients)]

    for dev_idx, dev_name in enumerate(device_names):
        df = dataset_by_device[dev_name]
        if len(df) == 0:
            continue
        parts = _distribute_device_records(df, proportions[dev_idx], rng)
        for c_idx in range(n_clients):
            client_dfs[c_idx].append(parts[c_idx])
            client_labels[c_idx].append(np.full(len(parts[c_idx]), dev_idx, dtype=int))

    merged_dfs: list[pl.DataFrame] = []
    merged_labels: list[np.ndarray] = []
    for c_idx in range(n_clients):
        merged_dfs.append(
            pl.concat(client_dfs[c_idx]) if client_dfs[c_idx] else create_empty_feature_frame(feature_cols)
        )
        merged_labels.append(
            np.concatenate(client_labels[c_idx]) if client_labels[c_idx] else np.array([], dtype=int)
        )

    return merged_dfs, merged_labels


def _distribute_dataset(
    dataset_by_device: dict[str, pl.DataFrame],
    proportions: np.ndarray,
    device_names: list[str],
    n_clients: int,
    rng: np.random.Generator,
    feature_cols: list[str],
) -> list[pl.DataFrame]:
    client_dfs: list[list[pl.DataFrame]] = [[] for _ in range(n_clients)]

    for dev_idx, dev_name in enumerate(device_names):
        df = dataset_by_device[dev_name]
        if len(df) == 0:
            continue
        parts = _distribute_device_records(df, proportions[dev_idx], rng)
        for c_idx in range(n_clients):
            client_dfs[c_idx].append(parts[c_idx])

    return [
        pl.concat(client_dfs[c_idx]) if client_dfs[c_idx] else create_empty_feature_frame(feature_cols)
        for c_idx in range(n_clients)
    ]


def partition_regime_c(
    raw_nbaiot_dir: Path,
    output_dir: Path,
    alpha: float,
    seed: int,
    n_clients: int,
    n_min: int,
    train_frac: float,
    cal_frac: float,
) -> RegimeCResult:
    raw_nbaiot_dir = Path(raw_nbaiot_dir)
    output_dir = Path(output_dir)
    is_iid = math.isinf(alpha)

    run_dir = regime_c_prepared_dir(output_dir, alpha, seed)

    logger.info(
        "Regime C partition",
        alpha="IID" if is_iid else str(alpha), seed=seed, n_clients=n_clients,
    )

    benign_by_device, feature_cols = _load_benign_records(raw_nbaiot_dir)
    attack_by_device = _load_attack_records(raw_nbaiot_dir, feature_cols)

    n_devices = len(DEVICE_DIRS)
    rng = np.random.default_rng(seed)

    if is_iid:
        proportions = np.ones((n_devices, n_clients)) / n_clients
    else:
        proportions = rng.dirichlet([alpha] * n_clients, n_devices)

    device_names = sorted(DEVICE_DIRS)

    client_benign_merged, client_benign_labs_merged = _distribute_dataset_with_labels(
        benign_by_device, proportions, device_names, n_clients, rng, feature_cols
    )
    client_attack_merged = _distribute_dataset(
        attack_by_device, proportions, device_names, n_clients, rng, feature_cols
    )

    client_summaries: list[RegimeCClientSummary] = []
    n_eligible = 0
    n_pending = 0

    for client_idx in range(n_clients):
        summary = _build_client_partition(
            client_idx=client_idx,
            run_dir=run_dir,
            benign_df=client_benign_merged[client_idx],
            device_labs=client_benign_labs_merged[client_idx],
            attack_df=client_attack_merged[client_idx],
            feature_cols=feature_cols,
            n_min=n_min,
            rng=rng,
            train_frac=train_frac,
            cal_frac=cal_frac,
            device_names=device_names,
        )
        client_summaries.append(summary)
        if summary.calibration_pending:
            n_pending += 1
        else:
            n_eligible += 1

    mixture_vectors = [
        np.array(
            [
                s.device_mixture_proportions[d] if d in s.device_mixture_proportions else 0.0
                for d in device_names
            ],
            dtype=np.float64,
        )
        for s in client_summaries
    ]
    js_summary = pairwise_js_from_distributions(mixture_vectors)
    js_div: float | None = js_summary.mean

    logger.info(
        "JS divergence computed",
        alpha="IID" if is_iid else str(alpha), seed=seed, js_divergence=js_div,
    )

    js_path = run_dir / "js_divergence.json"
    js_path.parent.mkdir(parents=True, exist_ok=True)
    with js_path.open("w") as f:
        json.dump(
            {
                "js_divergence": js_div,
                "alpha": "iid" if is_iid else alpha,
                "seed": seed,
            },
            f,
            indent=2,
        )

    create_manifest(
        dataset=NBAIOT_SPEC.id.value,
        raw_files=_raw_nbaiot_files(raw_nbaiot_dir),
        raw_base_dir=raw_nbaiot_dir,
        metadata={
            "dataset_display_name": NBAIOT_SPEC.display_name,
            "n_clients": n_clients,
            "n_features": FEATURE_COUNT,
            "alpha": "iid" if is_iid else alpha,
            "seed": seed,
            "js_divergence": js_div,
            "client_summaries": [
                {
                    "client_id": s.client_id,
                    "cal_count": s.cal_count,
                    "calibration_pending": s.calibration_pending,
                    "device_mixture_proportions": s.device_mixture_proportions,
                }
                for s in client_summaries
            ],
        },
        manifest_path=run_dir / MANIFEST_FILE,
    )

    result = RegimeCResult(
        alpha=float("inf") if is_iid else alpha,
        seed=seed,
        n_clients=n_clients,
        js_divergence=js_div,
        n_eligible=n_eligible,
        n_calibration_pending=n_pending,
        coverage=f"{n_eligible}/{n_clients}",
        clients=client_summaries,
    )

    logger.info(
        "Regime C partition complete",
        alpha="IID" if is_iid else str(alpha),
        seed=seed,
        eligible=n_eligible,
        pending=n_pending,
        js_divergence=js_div,
    )

    return result
