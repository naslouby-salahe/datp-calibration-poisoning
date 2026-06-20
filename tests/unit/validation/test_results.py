from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score

from datp.checkpointing.enums import ConvergenceStatus
from datp.core.enums import (
    Baseline,
    NormalizationScope,
    Regime,
    ThresholdAggregationMethod,
)
from datp.core.seeds import set_seeds
from datp.core.types import ClientThreshold
from datp.data.catalog import DatasetID
from datp.evaluation.metrics import compute_client_record
from datp.validation._audit_helpers import _split_hash
from datp.validation.enums import AuditSeverity, WarningCode
from datp.validation.schemas import RunManifestRecord, WarningRecord

from datp.artifacts.names import ArtifactFile


def test_manifest_schema_validation() -> None:
    record = RunManifestRecord(
        run_id="a_b1_seed0",
        timestamp="2026-04-26T00:00:00+00:00",
        git_commit_hash="abc",
        seed=0,
        dataset=DatasetID.NBAIOT,
        regime=Regime.A,
        baseline=Baseline.B1,
        alpha=None,
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
    assert record.baseline == Baseline.B1
    assert record.model_dump(mode="json")["convergence_status"] == "BLOCKED_PENDING_RUN"


def test_split_hash_stability(tmp_path: Path) -> None:
    import json

    manifest = tmp_path / ArtifactFile.MANIFEST
    manifest.write_text(json.dumps({"b": 2, "a": 1}), encoding="utf-8")
    first = _split_hash(manifest)
    manifest.write_text(json.dumps({"a": 1, "b": 2}), encoding="utf-8")
    assert _split_hash(manifest) == first


def test_fpr_and_tpr_denominators() -> None:
    ct = ClientThreshold(
        client_id="c", threshold=0.5, calibration_pending=False, strategy=Baseline.B1
    )
    rec = compute_client_record("c", np.array([0.1, 0.9]), np.array([0.8, 0.2]), ct)
    assert rec.confusion.fp + rec.confusion.tn == rec.n_benign
    assert rec.confusion.tp + rec.confusion.fn == rec.n_attack


def test_binary_macro_f1_ignores_multiclass_attack_names() -> None:
    benign = np.array([0.1, 0.2])
    attack = np.array([0.9, 0.3])
    ct = ClientThreshold(
        client_id="c", threshold=0.5, calibration_pending=False, strategy=Baseline.B1
    )
    rec = compute_client_record("c", benign, attack, ct)
    expected = f1_score(
        [0, 0, 1, 1],
        [0, 0, 1, 0],
        average="macro",
        labels=[0, 1],
        zero_division=0,  # type: ignore[call-overload]
    )  # type: ignore[arg-type]
    multiclass_wrong = f1_score(
        [0, 0, 2, 3],
        [0, 0, 1, 0],
        average="macro",
        zero_division=0,  # type: ignore[call-overload]
    )  # type: ignore[arg-type]
    assert rec.metrics.macro_f1 == expected
    assert rec.metrics.macro_f1 != multiclass_wrong


def test_evaluation_incomplete_exclusion() -> None:
    ct = ClientThreshold(
        client_id="c", threshold=0.5, calibration_pending=False, strategy=Baseline.B1
    )
    rec = compute_client_record("c", np.array([0.1, 0.9]), np.array([]), ct)
    assert np.isnan(rec.metrics.tpr)
    assert np.isnan(rec.metrics.macro_f1)


def test_deterministic_fixture_repeatability() -> None:
    set_seeds(0)
    rng = np.random.default_rng(0)
    first = rng.random(5)
    set_seeds(0)
    rng2 = np.random.default_rng(0)
    second = rng2.random(5)
    assert np.array_equal(first, second)


def test_audit_warning_generation() -> None:
    warning = WarningRecord(
        severity=AuditSeverity.BLOCKED_PENDING_RUN,
        code=WarningCode.MISSING_CONVERGENCE_CURVES,
        message="missing",
        exact_command="datp sweep --resume",
    )
    assert warning.severity == "BLOCKED_PENDING_RUN"
