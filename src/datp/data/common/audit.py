from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
from pydantic import BaseModel, ConfigDict, Field, model_validator

from datp.artifacts.markers import write_json_atomic
from datp.config.stages import ExperimentStage
from datp.core.errors import fmt, fmt_missing
from datp.core.logging import get_logger
from datp.data.contracts import PartitionResult
from datp.validation.constants import DATA_AUDIT_DIR

logger = get_logger(__name__)

_AUDIT_MODULE = "data.audit"


class AuditClient(BaseModel):
    model_config = ConfigDict(extra="forbid")

    benign_train_count: int = Field(ge=0)
    benign_cal_count: int = Field(ge=0)
    test_benign_count: int = Field(ge=0)
    test_attack_count: int = Field(ge=0)
    attack_classes: list[str] = Field(default_factory=list)
    calibration_pending: bool
    evaluation_incomplete: bool


class AuditSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_benign_train: int = Field(ge=0)
    total_benign_cal: int = Field(ge=0)
    total_test_benign: int = Field(ge=0)
    total_test_attack: int = Field(ge=0)
    calibration_pending_count: int = Field(ge=0)
    evaluation_incomplete_count: int = Field(ge=0)
    all_above_n_min: bool


class PartitionAudit(BaseModel):
    """Validated JSON payload for ``data_audit/<stage>_audit.json``."""

    model_config = ConfigDict(extra="forbid")

    stage: ExperimentStage
    n_clients: int = Field(ge=0)
    n_min: int = Field(ge=0)
    clients: dict[str, AuditClient]
    summary: AuditSummary

    @model_validator(mode="after")
    def validate_summary(self) -> "PartitionAudit":
        if self.n_clients != len(self.clients):
            raise ValueError(
                fmt(
                    _AUDIT_MODULE,
                    "n_clients mismatch",
                    str(len(self.clients)),
                    str(self.n_clients),
                )
            )
        calibration_pending_count = sum(
            client.calibration_pending for client in self.clients.values()
        )
        if self.summary.calibration_pending_count != calibration_pending_count:
            raise ValueError(
                fmt(
                    _AUDIT_MODULE,
                    "summary.calibration_pending_count mismatch",
                    str(calibration_pending_count),
                    str(self.summary.calibration_pending_count),
                )
            )
        evaluation_incomplete_count = sum(
            client.evaluation_incomplete for client in self.clients.values()
        )
        if self.summary.evaluation_incomplete_count != evaluation_incomplete_count:
            raise ValueError(
                fmt(
                    _AUDIT_MODULE,
                    "summary.evaluation_incomplete_count mismatch",
                    str(evaluation_incomplete_count),
                    str(self.summary.evaluation_incomplete_count),
                )
            )
        if self.summary.all_above_n_min != (calibration_pending_count == 0):
            raise ValueError(
                fmt(
                    _AUDIT_MODULE,
                    "summary.all_above_n_min mismatch",
                    str(calibration_pending_count == 0),
                    str(self.summary.all_above_n_min),
                )
            )
        return self


def audit_partitions(
    partition_results: dict[str, PartitionResult],
    stage: ExperimentStage,
    output_dir: Path,
    n_min: int,
) -> PartitionAudit:
    output_dir = Path(output_dir)

    clients: dict[str, AuditClient] = {}
    total_benign_train = 0
    total_benign_cal = 0
    total_test_benign = 0
    total_test_attack = 0
    calibration_pending_count = 0
    evaluation_incomplete_count = 0

    for client_id, info in partition_results.items():
        bt = info.benign_train_count
        bc = info.benign_cal_count
        tb = info.test_benign_count
        ta = info.test_attack_count

        total_benign_train += bt
        total_benign_cal += bc
        total_test_benign += tb
        total_test_attack += ta

        cal_pending = info.calibration_pending
        if cal_pending:
            calibration_pending_count += 1

        attack_classes = (
            info.attack_classes if info.attack_classes else info.attack_categories
        )

        eval_incomplete = info.evaluation_incomplete
        if eval_incomplete:
            evaluation_incomplete_count += 1

        clients[client_id] = AuditClient(
            benign_train_count=bt,
            benign_cal_count=bc,
            test_benign_count=tb,
            test_attack_count=ta,
            attack_classes=list(attack_classes),
            calibration_pending=cal_pending,
            evaluation_incomplete=eval_incomplete,
        )

    all_above_n_min = calibration_pending_count == 0

    audit_model = PartitionAudit(
        stage=stage,
        n_clients=len(partition_results),
        n_min=n_min,
        clients=clients,
        summary=AuditSummary(
            total_benign_train=total_benign_train,
            total_benign_cal=total_benign_cal,
            total_test_benign=total_test_benign,
            total_test_attack=total_test_attack,
            calibration_pending_count=calibration_pending_count,
            evaluation_incomplete_count=evaluation_incomplete_count,
            all_above_n_min=all_above_n_min,
        ),
    )
    audit_dir = output_dir / DATA_AUDIT_DIR
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / f"{stage.value}_audit.json"
    write_json_atomic(audit_path, audit_model)

    logger.info(
        "audit written",
        path=str(audit_path),
        n_clients=len(clients),
        calibration_pending=calibration_pending_count,
        evaluation_incomplete=evaluation_incomplete_count,
    )

    return audit_model


def run_schema_audit(
    file_path: Path,
    expected_feature_count: int,
) -> None:
    """Validate that a data file has the expected number of feature columns."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(
            fmt_missing(_AUDIT_MODULE, f"Schema audit target {file_path}")
        )

    if file_path.suffix.lower() != ".parquet":
        raise ValueError(
            fmt(
                _AUDIT_MODULE,
                "Unsupported file format",
                ".parquet",
                file_path.suffix.lower(),
            )
        )
    actual_count = len(pq.read_schema(file_path).names)

    if actual_count != expected_feature_count:
        raise ValueError(
            fmt(
                _AUDIT_MODULE,
                f"Feature count mismatch for {file_path}",
                str(expected_feature_count),
                str(actual_count),
            )
        )
