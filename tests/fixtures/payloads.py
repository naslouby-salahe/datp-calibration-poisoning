from __future__ import annotations

import json

from datp.core.metric_enums import PayloadKey


def valid_metrics_dict(baseline: str = "b1", regime: str = "a", seed: int = 0) -> dict:
    client = {
        PayloadKey.CLIENT_ID: "c1",
        "fpr": 0.0,
        "tpr": 1.0,
        "tnr": 1.0,
        "fnr": 0.0,
        "precision": 1.0,
        "recall": 1.0,
        "balanced_accuracy": 1.0,
        "macro_f1": 1.0,
        PayloadKey.CONFUSION_MATRIX: {"tp": 10, "fp": 0, "tn": 10, "fn": 0},
        PayloadKey.N_BENIGN: 10,
        PayloadKey.N_ATTACK: 10,
        "benign_count": 10,
        "attack_count": 10,
        PayloadKey.CALIBRATION_PENDING: False,
        PayloadKey.EVALUATION_INCOMPLETE: False,
        PayloadKey.THRESHOLD_VALUE: 0.5,
        PayloadKey.THRESHOLD_SOURCE: baseline,
    }
    return {
        PayloadKey.SCHEMA_VERSION: "2",
        PayloadKey.METRIC_SCHEMA_VERSION: "2",
        PayloadKey.THRESHOLD_SCHEMA_VERSION: "1",
        PayloadKey.RUN_ID: f"{regime}_{baseline}_seed{seed}",
        PayloadKey.RUN_KIND: "main",
        PayloadKey.DATASET: "nbaiot",
        PayloadKey.BASELINE: baseline,
        PayloadKey.REGIME: regime,
        PayloadKey.SEED: seed,
        PayloadKey.ALPHA: None,
        PayloadKey.THRESHOLD_SCOPE: "eligible_client_arithmetic_mean",
        PayloadKey.THRESHOLD_STRATEGY_NAME: baseline,
        "tau_global": 0.5,
        PayloadKey.PER_CLIENT: {client[PayloadKey.CLIENT_ID]: client},
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
        PayloadKey.AGGREGATE_METRICS: {"cv_fpr": 0.0, "p10_client_macro_f1": 1.0},
        PayloadKey.PROVENANCE: {
            PayloadKey.CONFIG_IDENTITY: "abc123",
            PayloadKey.SPLIT_MANIFEST_IDENTITY: "def456",
            PayloadKey.MODEL_CHECKPOINT_IDENTITY: "ghi789",
            PayloadKey.SCORE_ARTIFACT_IDENTITY: "jkl012",
            PayloadKey.METRIC_CODE_VERSION: "v1",
            PayloadKey.THRESHOLD_CODE_VERSION: "v1",
            PayloadKey.PACKAGE_VERSION: "v1",
            PayloadKey.GENERATED_AT_UTC: "2026-01-01T00:00:00+00:00",
        },
    }


def valid_metrics_json(baseline: str = "b1", regime: str = "a", seed: int = 0) -> str:
    return json.dumps(valid_metrics_dict(baseline, regime, seed))
