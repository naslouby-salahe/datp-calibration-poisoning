from __future__ import annotations

import enum
import hashlib
import json
import logging
import os
import random
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path, PurePath
from threading import Event, Lock
from typing import TYPE_CHECKING, Protocol, cast

import numpy as np
import structlog
import torch
from pydantic import BaseModel, ConfigDict
from rich.console import Console
from rich.logging import RichHandler
from structlog.stdlib import get_logger as get_logger

from datp.config import ExperimentStage
from datp.enums import (
    EnvironmentVariable,
    ArtifactFile,
    ClientStatus,
    DeviceType,
    LogLevel,
    PathToken,
    ThresholdPolicy,
)
from datp.types import (
    ByteCount,
    ClassificationScore,
    ClientId,
    ClusterCount,
    ClusterId,
    ContentHash,
    Index,
    JsonValue,
    NarrativeText,
    RandomSeed,
    RepositoryName,
    RunId,
    SampleCount,
    SchemaVersion,
    ScoreValue,
    ScoreVector,
    SignedCount,
    Threshold,
)

if TYPE_CHECKING:
    from datp.config import LoggingConfig


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MetricsProvenance(FrozenModel):
    config_identity: ContentHash
    split_manifest_identity: ContentHash
    model_identity: ContentHash
    score_artifact_identity: ContentHash
    metric_code_version: SchemaVersion
    threshold_code_version: SchemaVersion
    package_version: SchemaVersion
    generated_at_utc: NarrativeText


@dataclass(frozen=True, slots=True)
class ClusterInfo:
    cluster_id: ClusterId
    tau_cluster: Threshold
    members: tuple[ClientId, ...]


@dataclass(frozen=True, slots=True)
class ClientFingerprint:
    client_id: ClientId
    mean: ScoreValue
    std: ScoreValue
    skewness: ScoreValue
    p95: ScoreValue


@dataclass(frozen=True, slots=True)
class ClusterCountSilhouetteScore:
    cluster_count: SampleCount
    score: ScoreValue


@dataclass(frozen=True, slots=True)
class ClusterMetadata:
    cluster_info: tuple[ClusterInfo, ...]
    fingerprints: tuple[ClientFingerprint, ...]
    silhouette: ClassificationScore
    silhouette_scores: tuple[ClusterCountSilhouetteScore, ...]
    k: ClusterCount


@dataclass(frozen=True, slots=True)
class ClientThreshold:
    client_id: ClientId
    threshold: Threshold
    status: ClientStatus
    strategy: ThresholdPolicy


@dataclass(frozen=True, slots=True)
class ThresholdResult:
    run: PolicyRunId
    tau_global: Threshold
    client_thresholds: tuple[ClientThreshold, ...]
    cluster: ClusterMetadata | None

    @property
    def eligible_count(self) -> SampleCount:
        return sum(
            1 for ct in self.client_thresholds if ct.status is ClientStatus.ELIGIBLE
        )

    @property
    def pending_count(self) -> SampleCount:
        return sum(
            1
            for ct in self.client_thresholds
            if ct.status is ClientStatus.CALIBRATION_PENDING
        )


def seed_segment(seed: RandomSeed) -> NarrativeText:
    return f"{PathToken.SEED_PREFIX}{seed}"


@dataclass(frozen=True, slots=True)
class TrainingCellId:
    stage: ExperimentStage
    seed: RandomSeed

    def label(self) -> NarrativeText:
        return f"stage={self.stage} seed={self.seed}"


@dataclass(frozen=True, slots=True)
class PolicyRunId:
    cell: TrainingCellId
    policy: ThresholdPolicy

    @property
    def stage(self) -> ExperimentStage:
        return self.cell.stage

    @property
    def seed(self) -> RandomSeed:
        return self.cell.seed

    def audit_id(self) -> RunId:
        return RunId(f"{self.stage}_{self.policy}_seed{self.seed}")

    def label(self) -> NarrativeText:
        return f"stage={self.stage} policy={self.policy} seed={self.seed}"


class _TorchSeedApi(Protocol):
    def manual_seed(self, seed: RandomSeed) -> torch.Generator: ...


# Ensure deterministic cuBLAS operations by fixing the workspace size.
os.environ.setdefault(EnvironmentVariable.CUBLAS_WORKSPACE_CONFIG, ":4096:8")


@dataclass(frozen=True, slots=True)
class SeedPair:
    training_seed: RandomSeed
    poisoning_seed: RandomSeed


def set_seeds(seed: RandomSeed) -> None:
    random.seed(seed)
    np.random.seed(seed)
    cast(_TorchSeedApi, torch).manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.set_float32_matmul_precision("high")


class SeedRecord(FrozenModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
        revalidate_instances="never",
    )
    pair: SeedPair
    client_idx: Index
    scope_idx: Index

    @property
    def training_seed(self) -> RandomSeed:
        return self.pair.training_seed

    @property
    def poisoning_seed(self) -> RandomSeed:
        return self.pair.poisoning_seed

    @property
    def entropy(self) -> tuple[SignedCount, SignedCount, SignedCount, SignedCount]:
        return (
            self.training_seed,
            self.poisoning_seed,
            self.client_idx,
            self.scope_idx,
        )


def make_seed_rng(record: SeedRecord, *, child_index: Index = 0) -> np.random.Generator:
    return np.random.default_rng(
        np.random.SeedSequence(list(record.entropy), spawn_key=(child_index,))
    )


def resolve_device(require_cuda: bool) -> torch.device:
    if require_cuda and not torch.cuda.is_available():
        raise RuntimeError(
            "[core.device] CUDA required by config but not available. "
            "Expected: True. Got: False."
        )
    return torch.device(DeviceType.CUDA if require_cuda else DeviceType.CPU)


REPOSITORY_NAME: RepositoryName = RepositoryName("datp-calibration-poisoning")


def utc_timestamp() -> NarrativeText:
    return datetime.now(UTC).isoformat()


def sha256_bytes(payload: bytes) -> NarrativeText:
    return hashlib.sha256(payload).hexdigest()


def hash_file(path: Path) -> ContentHash:
    if not path.exists():
        return "MISSING"
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1048576):
            digest.update(chunk)
    return digest.hexdigest()


def hash_jsonable(payload: JsonValue) -> ContentHash:
    return sha256_bytes(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    )


def git_commit() -> NarrativeText:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path.cwd(),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, OSError) as exc:
        get_logger(__name__).warning("git commit unavailable", error=exc)
        return "GIT_UNAVAILABLE"


def source_hash(paths: list[Path]) -> ContentHash:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.as_posix().encode("utf-8"))
        digest.update(hash_file(path).encode("utf-8"))
    return digest.hexdigest()


def array_hash(arr: ScoreVector) -> ContentHash:
    return sha256_bytes(np.asarray(arr, dtype=np.float64).tobytes(order="C"))


class ExternalLibraryLogger(enum.StrEnum):
    FLOWER = "flwr"
    RAY = "ray"
    URLLIB3 = "urllib3"
    PYTORCH_LIGHTNING = "pytorch_lightning"
    LIGHTNING = "lightning"


console = Console(stderr=True)


_SETUP_DONE = Event()


_SETUP_LOCK = Lock()


class _PathRenderer:
    def __call__(
        self,
        _logger: structlog.types.WrappedLogger,
        _method: NarrativeText,
        event_dict: structlog.types.EventDict,
    ) -> structlog.types.EventDict:
        return {
            key: value.as_posix() if isinstance(value, PurePath) else value
            for key, value in event_dict.items()
        }


def _structlog_shared_processors() -> list[structlog.types.Processor]:
    return [
        _PathRenderer(),
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
        structlog.processors.StackInfoRenderer(),
    ]


def _parse_level(level: LogLevel) -> SignedCount:
    match level:
        case LogLevel.DEBUG:
            return logging.DEBUG
        case LogLevel.INFO:
            return logging.INFO
        case LogLevel.WARNING:
            return logging.WARNING
        case LogLevel.ERROR:
            return logging.ERROR
        case LogLevel.CRITICAL:
            return logging.CRITICAL


def _make_handlers(
    *,
    level: LogLevel,
    json: bool,
    log_dir: Path,
    max_bytes: ByteCount,
    backup_count: SampleCount,
) -> list[logging.Handler]:
    log_dir.mkdir(parents=True, exist_ok=True)
    lvl = _parse_level(level)

    console_handler = RichHandler(
        console=console,
        show_path=False,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
    )
    console_handler.setLevel(lvl)

    file_handler = RotatingFileHandler(
        log_dir / ArtifactFile.LOG,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(lvl)

    shared = _structlog_shared_processors()
    console_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
        )
    )
    file_renderer = (
        structlog.processors.JSONRenderer()
        if json
        else structlog.processors.KeyValueRenderer(
            sort_keys=True, key_order=["timestamp", "level", "logger", "event"]
        )
    )
    file_handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=[*shared, structlog.processors.ExceptionRenderer()],
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                file_renderer,
            ],
        )
    )
    return [console_handler, file_handler]


def configure_logging(cfg: LoggingConfig, log_dir: Path) -> None:
    with _SETUP_LOCK:
        if _SETUP_DONE.is_set():
            return

        structlog.configure(
            processors=[
                *_structlog_shared_processors(),
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
            handler.close()

        root.setLevel(_parse_level(cfg.level))
        for handler in _make_handlers(
            level=cfg.level,
            json=cfg.json_format,
            log_dir=log_dir,
            max_bytes=cfg.max_bytes,
            backup_count=cfg.backup_count,
        ):
            root.addHandler(handler)

        for name in ExternalLibraryLogger:
            logging.getLogger(name).setLevel(logging.WARNING)

        _SETUP_DONE.set()
