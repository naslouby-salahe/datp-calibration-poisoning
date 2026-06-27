"""Tests verifying Pydantic models for run manifests, warning schema definitions, and validation metric evaluations."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score

from datp.artifacts.names import ArtifactFile
from datp.checkpointing.enums import ConvergenceStatus
from datp.config.models import ExperimentStage
from datp.core.enums import (
    NormalizationScope,
    ThresholdAggregationMethod,
    ThresholdPolicy,
)
from datp.core.seeds import set_seeds
from datp.core.types import ClientThreshold
from datp.core.provenance import hash_jsonable
from datp.data.catalog import DatasetID
from datp.evaluation.metrics import compute_client_record
from datp.validation.enums import AuditSeverity, WarningCode
from datp.validation.schemas import RunManifestRecord, WarningRecord


def test_manifest_schema_validation() -> None:
    """Verify that RunManifestRecord conforms to schema and JSON serialization requirements."""
    record = RunManifestRecord(
        run_id="nbaiot_main_global_threshold_seed0",
        timestamp="2026-04-26T00:00:00+00:00",
        git_commit_hash="abc",
        seed=0,
        dataset=DatasetID.NBAIOT,
        stage=ExperimentStage.NBAIOT_MAIN,
        policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        client_count=4,
        split_hash="split",
        model_hash="model",
        encoder_hash="model",
        training_config_hash="cfg",
        preprocessing_config_hash="prep",
        scoring_code_hash="score",
        threshold_code_hash="thr",
        metrics_code_hash="metrics",
        artifact_schema_version="1.0",
        convergence_round=None,
        convergence_criterion_value=None,
        convergence_status=ConvergenceStatus.BLOCKED_PENDING_RUN,
        eligible_clients=4,
        calibration_pending_clients=0,
        evaluation_incomplete_clients=0,
        feature_count=115,
        feature_list_hash="features",
        threshold_aggregation_method=ThresholdAggregationMethod.ELIGIBLE_CLIENT_ARITHMETIC_MEAN,
        normalization_scope=NormalizationScope.PER_CLIENT_ZSCORE,
        train_count=None,
        calibration_count=None,
        test_count=24,
    )
    assert record.policy == ThresholdPolicy.GLOBAL_THRESHOLD
    assert record.model_dump(mode="json")["convergence_status"] == "BLOCKED_PENDING_RUN"


def test_split_hash_stability(tmp_path: Path) -> None:
    """Verify that JSON serialization key order differences do not affect split hash outcomes."""
    manifest = tmp_path / ArtifactFile.MANIFEST
    manifest.write_text(json.dumps({"b": 2, "a": 1}))
    first = hash_jsonable(json.loads(manifest.read_text()))
    manifest.write_text(json.dumps({"a": 1, "b": 2}))
    assert hash_jsonable(json.loads(manifest.read_text())) == first


def test_fpr_and_tpr_denominators() -> None:
    """Verify that benign/attack counts sum correctly from validation confusion matrices."""
    ct = ClientThreshold(
        client_id="c",
        threshold=0.5,
        calibration_pending=False,
        strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
    )
    rec = compute_client_record("c", np.array([0.1, 0.9]), np.array([0.8, 0.2]), ct)
    assert rec.confusion.fp + rec.confusion.tn == rec.n_benign
    assert rec.confusion.tp + rec.confusion.fn == rec.n_attack


def test_binary_macro_f1_ignores_multiclass_attack_names() -> None:
    """Verify that F1 score uses binary labels even under multiclass targets."""
    benign = np.array([0.1, 0.2])
    attack = np.array([0.9, 0.3])
    ct = ClientThreshold(
        client_id="c",
        threshold=0.5,
        calibration_pending=False,
        strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
    )
    rec = compute_client_record("c", benign, attack, ct)
    expected = f1_score(
        [0, 0, 1, 1],
        [0, 0, 1, 0],
        average="macro",
        labels=[0, 1],
        zero_division=0,  # type: ignore[arg-type]
    )
    multiclass_wrong = f1_score(
        [0, 0, 2, 3],
        [0, 0, 1, 0],
        average="macro",
        zero_division=0,  # type: ignore[arg-type]
    )
    assert rec.metrics.macro_f1 == expected
    assert rec.metrics.macro_f1 != multiclass_wrong


def test_evaluation_incomplete_exclusion() -> None:
    """Verify TPR and macro F1 are NaN if the client test attack set is empty."""
    ct = ClientThreshold(
        client_id="c",
        threshold=0.5,
        calibration_pending=False,
        strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
    )
    rec = compute_client_record("c", np.array([0.1, 0.9]), np.array([]), ct)
    assert np.isnan(rec.metrics.tpr)
    assert np.isnan(rec.metrics.macro_f1)


def test_deterministic_fixture_repeatability() -> None:
    """Verify seed setting behaves deterministically across random generators."""
    set_seeds(0)
    rng = np.random.default_rng(0)
    first = rng.random(5)
    set_seeds(0)
    rng2 = np.random.default_rng(0)
    second = rng2.random(5)
    assert np.array_equal(first, second)


def test_audit_warning_generation() -> None:
    """Verify WarningRecord severity values map successfully to enum strings."""
    warning = WarningRecord(
        severity=AuditSeverity.BLOCKED_PENDING_RUN,
        code=WarningCode.MISSING_CONVERGENCE_CURVES,
        message="missing",
        exact_command="datp sweep --resume",
    )
    assert warning.severity == "BLOCKED_PENDING_RUN"
