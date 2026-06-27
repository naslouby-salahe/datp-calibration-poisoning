"""Partition audit models, builders, and schema-audit validation."""

from __future__ import annotations

from pathlib import Path

import polars as pl
from pydantic import BaseModel, ConfigDict, Field, model_validator

from datp.artifacts.io import write_json_atomic
from datp.config.models import ExperimentStage
from datp.core.logging import get_logger
from datp.data.contracts import PartitionResult
from datp.validation.enums import AuditDir

logger = get_logger(__name__)
_AUDIT_MODULE = "data.audit"


class AuditClient(BaseModel):
    """Per-client partition counts and flags for audit."""

    model_config = ConfigDict(extra="forbid")
    benign_train_count: int = Field(ge=0)
    benign_cal_count: int = Field(ge=0)
    test_benign_count: int = Field(ge=0)
    test_attack_count: int = Field(ge=0)
    attack_classes: list[str] = Field(default_factory=list)
    calibration_pending: bool
    evaluation_incomplete: bool


class AuditSummary(BaseModel):
    """Aggregated counts and flags across all clients."""

    model_config = ConfigDict(extra="forbid")
    total_benign_train: int = Field(ge=0)
    total_benign_cal: int = Field(ge=0)
    total_test_benign: int = Field(ge=0)
    total_test_attack: int = Field(ge=0)
    calibration_pending_count: int = Field(ge=0)
    evaluation_incomplete_count: int = Field(ge=0)
    all_above_n_min: bool


class PartitionAudit(BaseModel):
    """Top-level audit model containing per-client and summary data."""

    model_config = ConfigDict(extra="forbid")
    stage: ExperimentStage
    n_clients: int = Field(ge=0)
    n_min: int = Field(ge=0)
    clients: dict[str, AuditClient]
    summary: AuditSummary

    @model_validator(mode="after")
    def validate_summary(self) -> "PartitionAudit":
        """Check that summary fields are consistent with per-client data."""
        if self.n_clients != len(self.clients):
            raise ValueError(
                f"[{_AUDIT_MODULE}] n_clients mismatch. Expected: {str(len(self.clients))}. Got: {str(self.n_clients)}."
            )

        cal_pending = sum(c.calibration_pending for c in self.clients.values())
        if self.summary.calibration_pending_count != cal_pending:
            raise ValueError(
                f"[{_AUDIT_MODULE}] calibration_pending_count mismatch. Expected: {str(cal_pending)}. Got: {str(self.summary.calibration_pending_count)}."
            )

        eval_incomplete = sum(c.evaluation_incomplete for c in self.clients.values())
        if self.summary.evaluation_incomplete_count != eval_incomplete:
            raise ValueError(
                f"[{_AUDIT_MODULE}] evaluation_incomplete_count mismatch. Expected: {str(eval_incomplete)}. Got: {str(self.summary.evaluation_incomplete_count)}."
            )

        if self.summary.all_above_n_min != (cal_pending == 0):
            raise ValueError(
                f"[{_AUDIT_MODULE}] all_above_n_min mismatch. Expected: {str(cal_pending == 0)}. Got: {str(self.summary.all_above_n_min)}."
            )
        return self


def audit_partitions(
    partition_results: dict[str, PartitionResult],
    stage: ExperimentStage,
    output_dir: Path,
    n_min: int,
) -> PartitionAudit:
    """Build and persist a PartitionAudit from per-client partition results."""
    output_dir = Path(output_dir)
    clients = {
        client_id: AuditClient(
            benign_train_count=info.benign_train_count,
            benign_cal_count=info.benign_cal_count,
            test_benign_count=info.test_benign_count,
            test_attack_count=info.test_attack_count,
            attack_classes=list(info.attack_classes or info.attack_categories),
            calibration_pending=info.calibration_pending,
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
    audit_path = output_dir / AuditDir.DATA_AUDIT / f"{stage.value}_audit.json"
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


def run_schema_audit(file_path: Path, expected_feature_count: int) -> None:
    """Validate that a Parquet file has the expected number of columns."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(
            f"[{_AUDIT_MODULE}] Schema audit target {file_path} not found."
        )
    if file_path.suffix.lower() != ".parquet":
        raise ValueError(
            f"[{_AUDIT_MODULE}] Unsupported file format. Expected: .parquet. Got: {file_path.suffix.lower()}."
        )

    actual_count = len(pl.read_parquet_schema(file_path))
    if actual_count != expected_feature_count:
        raise ValueError(
            f"[{_AUDIT_MODULE}] Feature count mismatch for {file_path}. Expected: {str(expected_feature_count)}. Got: {str(actual_count)}."
        )
