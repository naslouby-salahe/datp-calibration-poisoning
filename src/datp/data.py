from __future__ import annotations

import enum
import math
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Mapping

import joblib
import polars as pl
import torch
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sklearn.preprocessing import StandardScaler

from datp.artifacts import write_json_atomic
from datp.config import ExperimentStage
from datp.core import get_logger, hash_file, utc_timestamp
from datp.enums import (
    ArtifactFile,
    AuditDir,
    ClientStatus,
    DatasetID,
    NBaIoTAttackFamily,
    NBaIoTBalancePolicy,
    NBaIoTDevice,
    NBaIoTDeviceFamily,
    PathToken,
)
from datp.types import (
    ClientId,
    ColumnName,
    ContentHash,
    FeatureCount,
    JsonValue,
    NarrativeText,
    RandomSeed,
    Ratio,
    RecordKey,
    SampleCount,
    SignedCount,
)


class ClientMetricKey(enum.StrEnum):

    TRAIN_LOSS = "train_loss"
    VAL_LOSS = "val_loss"


class FederatedTensorLabel(enum.StrEnum):

    TRAIN = "train"
    VALIDATION = "val"
    BENIGN_TEST = "test_benign"
    ATTACK_TEST = "test_attack"
    TRAIN_DATA = "train_data"
    CALIBRATION_DATA = "cal_data"


@dataclass(frozen=True, slots=True)
class ClientData:

    train: torch.Tensor
    val: torch.Tensor
    test_benign: torch.Tensor
    test_attack: torch.Tensor


def validate_tensor_input(
    tensor: torch.Tensor,
    name: FederatedTensorLabel,
    client_id: ClientId,
    expected_dim: SignedCount | None = None,
) -> None:
    if tensor.ndim != 2:
        raise ValueError(f"{name} must be 2-D for {client_id} (got {tensor.ndim})")
    if tensor.numel() == 0:
        raise ValueError(f"{name} must be non-empty for {client_id}")
    if (~torch.isfinite(tensor)).any():
        raise ValueError(f"{name} contains non-finite values for {client_id}")
    if expected_dim is not None and tensor.shape[1] != expected_dim:
        raise ValueError(
            f"{name} expected dimension {expected_dim} for {client_id} (got {tensor.shape[1]})"
        )


def validate_client_data(
    client_data: ClientData, client_id: ClientId, expected_dim: SignedCount | None = None
) -> None:
    validate_tensor_input(client_data.train, FederatedTensorLabel.TRAIN, client_id, expected_dim)
    validate_tensor_input(client_data.val, FederatedTensorLabel.VALIDATION, client_id, expected_dim)
    validate_tensor_input(
        client_data.test_benign, FederatedTensorLabel.BENIGN_TEST, client_id, expected_dim
    )
    validate_tensor_input(
        client_data.test_attack, FederatedTensorLabel.ATTACK_TEST, client_id, expected_dim
    )


class SplitPolicyRole(enum.StrEnum):

    TRAIN = "train"
    GAP1 = "gap1"
    CAL = "cal"
    GAP2 = "gap2"
    TEST_BENIGN = "test_benign"


@dataclass(frozen=True, slots=True)
class DatasetSpec:

    id: DatasetID
    processed_slug: NarrativeText
    feature_count: FeatureCount
    raw_root_slug: NarrativeText
    family_map: Mapping[NBaIoTDevice, NBaIoTDeviceFamily] | None = None
    device_ids: tuple[NBaIoTDevice, ...] = ()
    attack_family_dirs: tuple[NBaIoTAttackFamily, ...] = ()


@cache
def dataset_spec(dataset_id: DatasetID) -> DatasetSpec:

    return {DatasetID.NBAIOT: NBAIOT_SPEC}[dataset_id]


_STAGE_DATASET = {
    ExperimentStage.NBAIOT_MAIN: DatasetID.NBAIOT,
}


def dataset_for_stage(stage: ExperimentStage) -> DatasetID:
    return _STAGE_DATASET[stage]


def data_root(base_dir: Path) -> Path:
    return base_dir / "data"


def raw_root(dataset: DatasetID, base_dir: Path) -> Path:
    return data_root(base_dir) / "raw" / dataset_spec(dataset).raw_root_slug


def processed_root(dataset: DatasetID, base_dir: Path) -> Path:
    return data_root(base_dir) / "processed" / dataset_spec(dataset).processed_slug


class Split(enum.StrEnum):

    TRAIN = "train"
    CAL = "cal"
    TEST_BENIGN = "test_benign"
    TEST_ATTACK = "test_attack"


def filename_for_split(split: Split) -> NarrativeText:
    return f"{split}.parquet"


def split_path(client_dir: Path, split: Split) -> Path:
    return client_dir / filename_for_split(split)


class PartitionResult(BaseModel):

    model_config = ConfigDict(frozen=True)
    benign_train_count: SampleCount
    benign_cal_count: SampleCount
    test_benign_count: SampleCount
    test_attack_count: SampleCount
    status: ClientStatus
    evaluation_incomplete: bool = False
    attack_classes: list[NarrativeText] = Field(default_factory=list)
    split_indices: dict[SplitPolicyRole, tuple[SignedCount, SignedCount]] | None = None


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


def create_empty_feature_frame(columns: list[ColumnName]) -> pl.DataFrame:
    return pl.DataFrame(schema={col: pl.Float64 for col in columns})


def write_client_splits(
    client_dir: Path,
    splits: Mapping[Split, pl.DataFrame],
    spec: DatasetSpec,
    scaler: StandardScaler | None = None,
) -> None:
    client_dir.mkdir(parents=True, exist_ok=True)

    for split, df in splits.items():
        write_artifact(df, client_dir / filename_for_split(split))
        if df.width != spec.feature_count:
            raise ValueError(
                f"[data.artifacts] Feature count mismatch. Expected: {spec.feature_count}. Got: {df.width}."
            )

    if scaler:
        save_scaler(scaler, client_dir / ArtifactFile.SCALER)


MANIFEST_MODULE = "data.manifests"


logger = get_logger(__name__)


class ManifestMetadata(BaseModel):

    model_config = ConfigDict(extra="allow")
    n_features: FeatureCount
    n_devices: SampleCount | None = None
    n_clients: SampleCount | None = None

    @model_validator(mode="after")
    def check_client_count(self) -> "ManifestMetadata":
        if self.n_devices is None and self.n_clients is None:
            raise ValueError(
                f"[{MANIFEST_MODULE}] metadata missing client count. Expected: n_devices or n_clients. Got: None."
            )
        return self


class PartitionManifest(BaseModel):

    model_config = ConfigDict(extra="forbid")
    dataset: DatasetID = Field(min_length=1, pattern=r"\S")
    file_hashes: dict[RecordKey, ContentHash] = Field(min_length=1)
    metadata: ManifestMetadata
    created: NarrativeText = Field(min_length=1)

    @classmethod
    def load(cls, path: Path) -> "PartitionManifest":
        if not path.exists():
            raise RuntimeError(f"[{MANIFEST_MODULE}] Manifest file {path} not found.")
        try:
            return cls.model_validate_json(path.read_bytes())
        except (ValueError, TypeError) as exc:
            raise RuntimeError(
                f"[{MANIFEST_MODULE}] Malformed manifest JSON. Expected: valid JSON matching schema. Got: parse error ({exc})."
            ) from exc

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(self.model_dump_json(indent=2))
        tmp.rename(path)
        logger.info("manifest written", path=str(path))

    def verify_hashes(self, raw_base_dir: Path) -> None:
        for rel_path_str, expected_hash in self.file_hashes.items():
            fpath = raw_base_dir / rel_path_str
            if not fpath.exists():
                raise RuntimeError(
                    f"[{MANIFEST_MODULE}] Raw file {rel_path_str} not found."
                )
            actual_hash = hash_file(fpath)
            if actual_hash != expected_hash:
                raise RuntimeError(
                    f"[{MANIFEST_MODULE}] Raw file hash mismatch for {rel_path_str}. Expected: {expected_hash}. Got: {actual_hash}."
                )
        logger.info(
            "partition manifest hash verification passed", n_files=len(self.file_hashes)
        )


def create_manifest(
    *,
    dataset: DatasetID,
    raw_files: list[Path],
    raw_base_dir: Path,
    metadata: JsonValue,
    manifest_path: Path,
) -> PartitionManifest:
    manifest = PartitionManifest(
        dataset=dataset,
        created=utc_timestamp(),
        file_hashes={
            str(p.relative_to(raw_base_dir)): hash_file(p) for p in sorted(raw_files)
        },
        metadata=metadata
        if isinstance(metadata, ManifestMetadata)
        else ManifestMetadata.model_validate(metadata),
    )
    manifest.write(manifest_path)
    return manifest


def _check_extension(path: Path) -> None:
    if path.suffix != PathToken.PARQUET_EXT:
        raise ValueError(
            f"[data.storage] Invalid extension. Expected: ending in .parquet. Got: ending in {path.suffix}."
        )


def write_artifact(df: pl.DataFrame, path: Path) -> None:
    _check_extension(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp.parquet")
    df.write_parquet(tmp_path, compression="snappy")
    tmp_path.rename(path)


def read_artifact(path: Path) -> pl.DataFrame:
    _check_extension(path)
    return pl.read_parquet(path)


def assert_no_csv_artifacts(directory: Path) -> None:
    if csv_files := sorted(directory.rglob(PathToken.CSV_GLOB)):
        listing = "\n ".join(str(f) for f in csv_files[:10])
        extra = f"\n ... and {len(csv_files) - 10} more" if len(csv_files) > 10 else ""
        raise RuntimeError(
            f"[data.storage] CSV files found in {directory} — Parquet only.\n {listing}{extra}"
        )


_AUDIT_MODULE = "data.audit"


class AuditClient(BaseModel):

    model_config = ConfigDict(extra="forbid")
    benign_train_count: SampleCount = Field(ge=0)
    benign_cal_count: SampleCount = Field(ge=0)
    test_benign_count: SampleCount = Field(ge=0)
    test_attack_count: SampleCount = Field(ge=0)
    attack_classes: list[NarrativeText] = Field(default_factory=list)
    calibration_pending: bool
    evaluation_incomplete: bool


class AuditSummary(BaseModel):

    model_config = ConfigDict(extra="forbid")
    total_benign_train: SignedCount = Field(ge=0)
    total_benign_cal: SignedCount = Field(ge=0)
    total_test_benign: SignedCount = Field(ge=0)
    total_test_attack: SignedCount = Field(ge=0)
    calibration_pending_count: SampleCount = Field(ge=0)
    evaluation_incomplete_count: SampleCount = Field(ge=0)
    all_above_n_min: bool


class PartitionAudit(BaseModel):

    model_config = ConfigDict(extra="forbid")
    stage: ExperimentStage
    n_clients: SampleCount = Field(ge=0)
    n_min: SampleCount = Field(ge=0)
    clients: dict[ClientId, AuditClient]
    summary: AuditSummary

    @model_validator(mode="after")
    def validate_summary(self) -> "PartitionAudit":
        if self.n_clients != len(self.clients):
            raise ValueError(
                f"[{_AUDIT_MODULE}] n_clients mismatch. Expected: {len(self.clients)}. Got: {self.n_clients}."
            )

        cal_pending = sum(c.calibration_pending for c in self.clients.values())
        if self.summary.calibration_pending_count != cal_pending:
            raise ValueError(
                f"[{_AUDIT_MODULE}] calibration_pending_count mismatch. Expected: {cal_pending}. Got: {self.summary.calibration_pending_count}."
            )

        eval_incomplete = sum(c.evaluation_incomplete for c in self.clients.values())
        if self.summary.evaluation_incomplete_count != eval_incomplete:
            raise ValueError(
                f"[{_AUDIT_MODULE}] evaluation_incomplete_count mismatch. Expected: {eval_incomplete}. Got: {self.summary.evaluation_incomplete_count}."
            )

        if self.summary.all_above_n_min != (cal_pending == 0):
            raise ValueError(
                f"[{_AUDIT_MODULE}] all_above_n_min mismatch. Expected: {cal_pending == 0}. Got: {self.summary.all_above_n_min}."
            )
        return self


def audit_partitions(
    partition_results: dict[ClientId, PartitionResult],
    stage: ExperimentStage,
    output_dir: Path,
    n_min: SampleCount,
) -> PartitionAudit:
    output_dir = Path(output_dir)
    clients = {
        client_id: AuditClient(
            benign_train_count=info.benign_train_count,
            benign_cal_count=info.benign_cal_count,
            test_benign_count=info.test_benign_count,
            test_attack_count=info.test_attack_count,
            attack_classes=list(info.attack_classes),
            calibration_pending=info.status is ClientStatus.CALIBRATION_PENDING,
            evaluation_incomplete=info.evaluation_incomplete,
        )
        for client_id, info in partition_results.items()
    }

    summary = AuditSummary(
        total_benign_train=sum(c.benign_train_count for c in clients.values()),
        total_benign_cal=sum(c.benign_cal_count for c in clients.values()),
        total_test_benign=sum(c.test_benign_count for c in clients.values()),
        total_test_attack=sum(c.test_attack_count for c in clients.values()),
        calibration_pending_count=sum(c.calibration_pending for c in clients.values()),
        evaluation_incomplete_count=sum(
            c.evaluation_incomplete for c in clients.values()
        ),
        all_above_n_min=not any(c.calibration_pending for c in clients.values()),
    )

    audit_model = PartitionAudit(
        stage=stage,
        n_clients=len(clients),
        n_min=n_min,
        clients=clients,
        summary=summary,
    )
    audit_path = output_dir / AuditDir.DATA_AUDIT / f"{stage}_audit.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(audit_path, audit_model)

    logger.info(
        "audit written",
        path=str(audit_path),
        n_clients=len(clients),
        calibration_pending=summary.calibration_pending_count,
        evaluation_incomplete=summary.evaluation_incomplete_count,
    )
    return audit_model


def run_schema_audit(file_path: Path, expected_feature_count: FeatureCount) -> None:
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(
            f"[{_AUDIT_MODULE}] Schema audit target {file_path} not found."
        )
    if file_path.suffix.lower() != PathToken.PARQUET_EXT:
        raise ValueError(
            f"[{_AUDIT_MODULE}] Unsupported file format. Expected: .parquet. Got: {file_path.suffix.lower()}."
        )

    actual_count = len(pl.read_parquet_schema(file_path))
    if actual_count != expected_feature_count:
        raise ValueError(
            f"[{_AUDIT_MODULE}] Feature count mismatch for {file_path}. Expected: {expected_feature_count}. Got: {actual_count}."
        )


_NBAIOT_DISPLAY_NAME = "N-BaIoT"


FEATURE_COUNT: FeatureCount = 115


DEVICE_DIRS: tuple[NBaIoTDevice, ...] = (
    NBaIoTDevice.DANMINI_DOORBELL,
    NBaIoTDevice.ECOBEE_THERMOSTAT,
    NBaIoTDevice.ENNIO_DOORBELL,
    NBaIoTDevice.PHILIPS_B120N10_BABY_MONITOR,
    NBaIoTDevice.PROVISION_PT_737E_SECURITY_CAMERA,
    NBaIoTDevice.PROVISION_PT_838_SECURITY_CAMERA,
    NBaIoTDevice.SAMSUNG_SNH_1011_N_WEBCAM,
    NBaIoTDevice.SIMPLEHOME_XCS7_1002_WHT_SECURITY_CAMERA,
    NBaIoTDevice.SIMPLEHOME_XCS7_1003_WHT_SECURITY_CAMERA,
)


DEVICE_FAMILY_MAP: dict[NBaIoTDevice, NBaIoTDeviceFamily] = {
    NBaIoTDevice.DANMINI_DOORBELL: NBaIoTDeviceFamily.DOORBELL,
    NBaIoTDevice.ECOBEE_THERMOSTAT: NBaIoTDeviceFamily.OTHER,
    NBaIoTDevice.ENNIO_DOORBELL: NBaIoTDeviceFamily.DOORBELL,
    NBaIoTDevice.PHILIPS_B120N10_BABY_MONITOR: NBaIoTDeviceFamily.OTHER,
    NBaIoTDevice.PROVISION_PT_737E_SECURITY_CAMERA: NBaIoTDeviceFamily.CAMERA,
    NBaIoTDevice.PROVISION_PT_838_SECURITY_CAMERA: NBaIoTDeviceFamily.CAMERA,
    NBaIoTDevice.SAMSUNG_SNH_1011_N_WEBCAM: NBaIoTDeviceFamily.CAMERA,
    NBaIoTDevice.SIMPLEHOME_XCS7_1002_WHT_SECURITY_CAMERA: NBaIoTDeviceFamily.CAMERA,
    NBaIoTDevice.SIMPLEHOME_XCS7_1003_WHT_SECURITY_CAMERA: NBaIoTDeviceFamily.CAMERA,
}


ATTACK_FAMILY_DIRS: tuple[NBaIoTAttackFamily, ...] = (
    NBaIoTAttackFamily.GAFGYT,
    NBaIoTAttackFamily.MIRAI,
)


SPLIT_RATIOS: dict[SplitPolicyRole, Ratio] = {
    SplitPolicyRole.TRAIN: 0.60,
    SplitPolicyRole.GAP1: 0.01,
    SplitPolicyRole.CAL: 0.20,
    SplitPolicyRole.GAP2: 0.01,
}


NBAIOT_SPEC = DatasetSpec(
    id=DatasetID.NBAIOT,
    processed_slug=DatasetID.NBAIOT,
    feature_count=FEATURE_COUNT,
    raw_root_slug=_NBAIOT_DISPLAY_NAME,
    family_map=DEVICE_FAMILY_MAP,
    device_ids=DEVICE_DIRS,
    attack_family_dirs=ATTACK_FAMILY_DIRS,
)


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
        end = start + math.floor(n * SPLIT_RATIOS[role])
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
            "dataset_display_name": _NBAIOT_DISPLAY_NAME,
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
