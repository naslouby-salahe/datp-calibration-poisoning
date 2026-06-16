from __future__ import annotations

import pytest

from datp.core.enums import ConfusionKey, PayloadKey
from datp.evaluation.artifact_validation import validate_metrics_payload


def _base_provenance(**overrides: str) -> dict:
    base = {
        PayloadKey.CONFIG_IDENTITY: "abc123",
        PayloadKey.SPLIT_MANIFEST_IDENTITY: "def456",
        PayloadKey.MODEL_CHECKPOINT_IDENTITY: "ghi789",
        PayloadKey.SCORE_ARTIFACT_IDENTITY: "jkl012",
        PayloadKey.METRIC_CODE_VERSION: "v1",
        PayloadKey.THRESHOLD_CODE_VERSION: "v1",
        PayloadKey.PACKAGE_VERSION: "v1",
        PayloadKey.GENERATED_AT_UTC: "2026-01-01T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def _base_client(client_id: str = "c1", calibration_pending: bool = False) -> dict:
    return {
        PayloadKey.CLIENT_ID: client_id,
        "fpr": 0.0,
        "tpr": 1.0,
        "tnr": 1.0,
        "fnr": 0.0,
        "precision": 1.0,
        "recall": 1.0,
        "balanced_accuracy": 1.0,
        "macro_f1": 1.0,
        PayloadKey.CONFUSION_MATRIX: {
            ConfusionKey.TP: 10,
            ConfusionKey.FP: 0,
            ConfusionKey.TN: 10,
            ConfusionKey.FN: 0,
        },
        PayloadKey.N_BENIGN: 10,
        PayloadKey.N_ATTACK: 10,
        "benign_count": 10,
        "attack_count": 10,
        PayloadKey.CALIBRATION_PENDING: calibration_pending,
        PayloadKey.EVALUATION_INCOMPLETE: False,
        PayloadKey.THRESHOLD_VALUE: 0.5,
        PayloadKey.THRESHOLD_SOURCE: "b1",
    }


def _valid_payload(**overrides) -> dict:
    payload = {
        PayloadKey.SCHEMA_VERSION: "2",
        PayloadKey.METRIC_SCHEMA_VERSION: "2",
        PayloadKey.THRESHOLD_SCHEMA_VERSION: "1",
        PayloadKey.RUN_ID: "a_b1_seed0",
        PayloadKey.RUN_KIND: "core_ladder",
        PayloadKey.DATASET: "nbaiot",
        PayloadKey.BASELINE: "b1",
        PayloadKey.REGIME: "a",
        PayloadKey.SEED: 0,
        PayloadKey.ALPHA: None,
        PayloadKey.THRESHOLD_SCOPE: "eligible_client_arithmetic_mean",
        PayloadKey.THRESHOLD_STRATEGY_NAME: "b1",
        "tau_global": 0.5,
        PayloadKey.PER_CLIENT: [_base_client()],
        PayloadKey.ELIGIBLE_IDS: ["c1"],
        PayloadKey.PENDING_IDS: [],
        PayloadKey.EVAL_INCOMPLETE_IDS: [],
        PayloadKey.ELIGIBLE_COUNT: 1,
        PayloadKey.PENDING_COUNT: 0,
        PayloadKey.EVAL_INCOMPLETE_COUNT: 0,
        PayloadKey.CLIENT_COUNT: 1,
        PayloadKey.COVERAGE_RATIO: 1.0,
        "cv_fpr": 0.0,
        "mean_fpr": 0.0,
        "std_fpr": 0.0,
        "cv_tpr": 0.0,
        "iqr_fpr": 0.0,
        "iqr_tpr": 0.0,
        "worst_client_fpr": 0.0,
        "worst_client_id": "c1",
        "worst_ba": 1.0,
        "p10_macro_f1": 1.0,
        PayloadKey.AGGREGATE_METRICS: {},
        PayloadKey.PROVENANCE: _base_provenance(),
    }
    payload.update(overrides)
    return payload


class TestProvenanceValidation:
    def test_valid_payload_passes(self) -> None:
        assert validate_metrics_payload(_valid_payload(), module="test") == []

    @pytest.mark.parametrize(
        "field",
        [
            PayloadKey.CONFIG_IDENTITY,
            PayloadKey.SPLIT_MANIFEST_IDENTITY,
            PayloadKey.MODEL_CHECKPOINT_IDENTITY,
            PayloadKey.SCORE_ARTIFACT_IDENTITY,
        ],
    )
    def test_unknown_identity_fails(self, field: PayloadKey) -> None:
        payload = _valid_payload(provenance=_base_provenance(**{field: "UNKNOWN"}))
        errors = validate_metrics_payload(payload, module="test")
        assert any("UNKNOWN" in e or "vague" in e for e in errors)

    @pytest.mark.parametrize(
        "field,value",
        [
            (PayloadKey.CONFIG_IDENTITY, "MISSING_CONFIG_HASH"),
            (PayloadKey.SPLIT_MANIFEST_IDENTITY, "MISSING_MANIFEST_HASH"),
            (PayloadKey.MODEL_CHECKPOINT_IDENTITY, "MISSING_CHECKPOINT_HASH"),
            (PayloadKey.SCORE_ARTIFACT_IDENTITY, "MISSING_SCORE_HASH"),
        ],
    )
    def test_missing_hash_fails(self, field: PayloadKey, value: str) -> None:
        payload = _valid_payload(provenance=_base_provenance(**{field: value}))
        errors = validate_metrics_payload(payload, module="test")
        assert any("MISSING_" in e or "unresolved" in e for e in errors)

    def test_not_applicable_passes(self) -> None:
        payload = _valid_payload(
            provenance=_base_provenance(
                **{
                    PayloadKey.MODEL_CHECKPOINT_IDENTITY: "NOT_APPLICABLE_B0_OWN_MODEL",
                    PayloadKey.SCORE_ARTIFACT_IDENTITY: "NOT_APPLICABLE_B0_DIRECT_EVAL",
                }
            )
        )
        errors = validate_metrics_payload(payload, module="test")
        assert errors == []


class TestEligibilityValidation:
    @pytest.mark.parametrize(
        "missing_key",
        [
            PayloadKey.ELIGIBLE_IDS,
            PayloadKey.PENDING_IDS,
            PayloadKey.EVAL_INCOMPLETE_IDS,
        ],
    )
    def test_missing_id_list_fails(self, missing_key: PayloadKey) -> None:
        payload = _valid_payload()
        del payload[missing_key]
        errors = validate_metrics_payload(payload, module="test")
        assert any(missing_key.value in e for e in errors)

    def test_eligible_pending_overlap_fails(self) -> None:
        payload = _valid_payload(
            per_client=[_base_client("c1", calibration_pending=True)],
            eligible_ids=["c1"],
            pending_ids=["c1"],
        )
        errors = validate_metrics_payload(payload, module="test")
        assert any("overlap" in e for e in errors)

    def test_calibration_pending_excluded_from_eligible(self) -> None:
        payload = _valid_payload(
            per_client=[
                _base_client("c1"),
                _base_client("c2", calibration_pending=True),
            ],
            eligible_ids=["c1"],
            pending_ids=["c2"],
            eligible_count=1,
            pending_count=1,
            client_count=2,
            coverage_ratio=0.5,
        )
        errors = validate_metrics_payload(payload, module="test")
        assert errors == []

    def test_pending_client_without_flag_fails(self) -> None:
        payload = _valid_payload(
            per_client=[
                _base_client("c1"),
                _base_client("c2", calibration_pending=False), # flag missing
            ],
            eligible_ids=["c1"],
            pending_ids=["c2"],
            eligible_count=1,
            pending_count=1,
            client_count=2,
            coverage_ratio=0.5,
        )
        errors = validate_metrics_payload(payload, module="test")
        assert any("calibration_pending" in e for e in errors)
