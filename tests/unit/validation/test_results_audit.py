"""Tests verifying the results validation audit suite, policy invariants, and recomputation checks."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
from datp.artifacts.names import ArtifactFile
from datp.config.compose import BASE_CONFIG
from datp.core.enums import ThresholdPolicy
from datp.core.types import ClientThreshold
from datp.data.common.storage import write_artifact
from datp.evaluation.metrics import compute_client_record
from datp.scoring.manifest import SCORE_COLUMN
from datp.validation.enums import AuditArtifact, WarningCode
from datp.validation.results import run_results_audit

_CLIENTS = (
    "Danmini_Doorbell",
    "Ecobee_Thermostat",
    "Ennio_Doorbell",
    "Philips_B120N10_Baby_Monitor",
)

_SAFE_SCORE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


def _safe_score_path(root: Path, stage: str, client_id: str) -> Path:
    """Helper to build a relative-safe score parquet file path."""
    if not _SAFE_SCORE_NAME.fullmatch(client_id):
        raise ValueError(f"Unsafe client id in score fixture: {client_id}")
    base = (root / "scores/nbaiot_main/seed_0").resolve()
    path = (base / stage / f"{client_id}.parquet").resolve()
    if not path.is_relative_to(base):
        raise ValueError(f"Score fixture path escapes base: {path}")
    return path


def _write_scores(root: Path) -> None:
    """Helper to write synthetic scores across clients into workspace directories."""
    for index, client_id in enumerate(_CLIENTS):
        cal = np.linspace(0.01, 0.05 + index * 0.01, 120, dtype=float)
        benign = np.array([0.01, 0.02, 0.07], dtype=float)
        attack = np.array([0.08, 0.09, 0.10], dtype=float)
        for stage, values in {
            "cal": cal,
            "test_benign": benign,
            "test_attack": attack,
        }.items():
            write_artifact(
                pl.DataFrame({SCORE_COLUMN: values}),
                _safe_score_path(root, stage, client_id),
            )


def _make_client_metric_entry(client_id: str, policy: ThresholdPolicy) -> dict:
    """Helper to package synthetic validation client metric dictionary entry."""
    ct = ClientThreshold(
        client_id=client_id,
        threshold=0.06,
        calibration_pending=False,
        strategy=policy,
    )
    rec = compute_client_record(
        client_id, np.array([0.01, 0.02, 0.07]), np.array([0.08, 0.09, 0.10]), ct
    )
    return {
        "client_id": client_id,
        "fpr": rec.metrics.fpr,
        "tpr": rec.metrics.tpr,
        "balanced_accuracy": rec.metrics.balanced_accuracy,
        "macro_f1": rec.metrics.macro_f1,
        "auroc": None,
        "pr_auc": None,
        "confusion_matrix": {
            "tp": rec.confusion.tp,
            "fp": rec.confusion.fp,
            "tn": rec.confusion.tn,
            "fn": rec.confusion.fn,
        },
        "n_benign": rec.n_benign,
        "n_attack": rec.n_attack,
        "benign_count": rec.n_benign,
        "attack_count": rec.n_attack,
        "calibration_pending": False,
        "evaluation_incomplete": False,
        "threshold_value": 0.06,
        "threshold_source": policy.value,
    }


def _metrics_payload(policy: ThresholdPolicy) -> dict:
    """Helper to mock metrics file payload structures for a given threshold policy."""
    per_client = [_make_client_metric_entry(cid, policy) for cid in _CLIENTS]
    return {
        "schema_version": "2",
        "metric_schema_version": "2",
        "threshold_schema_version": "1",
        "run_id": f"nbaiot_main_{policy.value}_seed0",
        "run_kind": "core_ladder",
        "dataset": "nbaiot",
        "policy": policy.value,
        "threshold_scope": "eligible_client_arithmetic_mean",
        "threshold_strategy_name": policy.value,
        "coverage_ratio": 1.0,
        "cv_fpr": 0.0 if policy == ThresholdPolicy.LOCAL_THRESHOLD else 0.1,
        "mean_fpr": 0.0,
        "std_fpr": 0.0,
        "cv_tpr": 0.0,
        "iqr_fpr": 0.0,
        "iqr_tpr": 0.0,
        "worst_client_fpr": 0.0,
        "worst_client_id": _CLIENTS[0],
        "eligible_count": len(_CLIENTS),
        "client_count": len(_CLIENTS),
        "pending_count": 0,
        "eval_incomplete_count": 0,
        "eligible_ids": list(_CLIENTS),
        "pending_ids": [],
        "eval_incomplete_ids": [],
        "aggregate_metrics": {
            "cv_fpr": 0.0 if policy == ThresholdPolicy.LOCAL_THRESHOLD else 0.1
        },
        "provenance": {
            "config_identity": "fixture",
            "split_manifest_identity": "fixture",
            "model_checkpoint_identity": "fixture",
            "score_artifact_identity": "fixture",
            "metric_code_version": "fixture",
            "threshold_code_version": "fixture",
            "package_version": "fixture",
            "generated_at_utc": "2026-01-01T00:00:00+00:00",
        },
        "per_client": per_client,
        "stage": "nbaiot_main",
        "seed": 0,
        "tau_global": 0.06,
        "normalization_scope": "per_client_zscore",
    }


def _write_minimal_outputs(root: Path) -> None:
    """Helper to populate mock workspace directories with manifests, configs, and scores."""
    _write_scores(root)
    manifest = {
        "dataset": "nbaiot",
        "file_hashes": {"fixture": "abc"},
        "metadata": {"n_features": 115, "n_devices": len(_CLIENTS), "n_clients": None},
        "created": "2026-04-26T00:00:00+00:00",
    }
    manifest_path = root / "data/processed/nbaiot" / ArtifactFile.MANIFEST
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest))
    ckpt = root / "checkpoints/nbaiot_main/seed_0/model.pt"
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    ckpt.write_bytes(b"fixture-model")
    for policy in (
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    ):
        result_dir = root / "results/nbaiot_main" / policy.value / "seed_0"
        result_dir.mkdir(parents=True, exist_ok=True)
        (result_dir / ArtifactFile.METRICS).write_text(
            json.dumps(_metrics_payload(policy))
        )
        (result_dir / ArtifactFile.RESOLVED_CONFIG).write_text("seed: 0\n")


def test_results_audit_generates_core_artifacts(tmp_path: Path) -> None:
    """Verify that results audit generates all expected summary, manifests, and checks CSVs."""
    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    paths = run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)

    from datp.validation.results import AuditOutputName

    assert paths.path_for(AuditOutputName.RUN_MANIFEST).is_file()
    assert (audit_dir / AuditArtifact.POLICY_INVARIANTS).is_file()
    assert (audit_dir / AuditArtifact.RUN_MANIFEST).is_file()
    assert (audit_dir / AuditArtifact.RECONSTRUCTION_ERROR_SUMMARY).is_file()
    assert (audit_dir / AuditArtifact.METRIC_DENOMINATOR_AUDIT).is_file()
    assert (audit_dir / AuditArtifact.THRESHOLD_VALUES).is_file()
    assert (audit_dir / AuditArtifact.WARNINGS).is_file()
    assert (audit_dir / AuditArtifact.AUDIT_SUMMARY).is_file()

    invariants = json.loads((audit_dir / AuditArtifact.POLICY_INVARIANTS).read_text())
    assert invariants[0]["status"] == "PASS"
    assert invariants[0]["split_hash_shared"] is True
    assert invariants[0]["reconstruction_error_hashes_shared"] is True

    thresholds = pd.read_csv(audit_dir / AuditArtifact.THRESHOLD_VALUES)
    assert "threshold_aggregation_method" in thresholds.columns
    assert "local_tau_i" in thresholds.columns
    global_rows = thresholds[
        thresholds["policy"] == ThresholdPolicy.GLOBAL_THRESHOLD.value
    ]
    assert set(global_rows["threshold_aggregation_method"]) == {
        "eligible_client_arithmetic_mean"
    }


def test_results_audit_generates_severity_trend_and_cluster_stability(
    tmp_path: Path,
) -> None:
    """Verify that results audit generates cluster stability CSV and includes summaries."""
    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    paths = run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)

    assert "cluster_stability" in paths
    assert (audit_dir / AuditArtifact.CLUSTER_STABILITY).is_file()

    summary = (audit_dir / AuditArtifact.AUDIT_SUMMARY).read_text()
    assert "Controlled threshold policies share the trained encoder" in summary


def test_results_audit_generates_seed_deltas(tmp_path: Path) -> None:
    """Verify that seed deltas audit CSV is generated with all expected schema columns."""
    from datp.validation.enums import AuditArtifact as _Art

    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)
    csv_path = audit_dir / _Art.SEED_DELTAS
    assert csv_path.is_file()
    df = pd.read_csv(csv_path)
    for col in (
        "stage",
        "seed",
        "global_cv_fpr",
        "local_cv_fpr",
        "delta_cv_fpr_global_minus_local",
        "coverage_ratio",
    ):
        assert col in df.columns


def test_results_audit_generates_metric_denominator_audit(tmp_path: Path) -> None:
    """Verify that metric denominator audit CSV file is successfully generated."""
    from datp.validation.enums import AuditArtifact as _Art

    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    paths = run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)
    assert (audit_dir / _Art.METRIC_DENOMINATOR_AUDIT).is_file()
    assert "metric_denominator_audit" in paths


def test_results_audit_fpr_companion_has_required_columns(tmp_path: Path) -> None:
    """Verify that FPR companion metrics audit CSV contains all expected fields."""
    from datp.validation.enums import AuditArtifact as _Art

    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)
    df = pd.read_csv(audit_dir / _Art.FPR_COMPANION_METRICS)
    for col in (
        "cv_fpr",
        "mean_fpr",
        "std_fpr",
        "iqr_fpr",
        "worst_client_fpr",
        "coverage_ratio",
    ):
        assert col in df.columns, f"Missing FPR companion column: {col}"


def test_results_audit_generates_metric_recomputation_csv(tmp_path: Path) -> None:
    """Verify that metric recomputations audit CSV evaluates PASS/FAIL correctly."""
    from datp.validation.enums import AuditArtifact as _Art

    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    paths = run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)
    assert (audit_dir / _Art.METRIC_RECOMPUTATION_AUDIT).is_file()
    assert "metric_recomputation_audit" in paths
    df = pd.read_csv(audit_dir / _Art.METRIC_RECOMPUTATION_AUDIT)
    for col in (
        "run_id",
        "seed",
        "stage",
        "policy",
        "client_id",
        "metric",
        "saved_value",
        "recomputed_value",
        "abs_diff",
        "status",
    ):
        assert col in df.columns, f"Missing metric recomputation column: {col}"
    assert set(df["status"]).issubset(
        {"PASS", "FAIL", "EXCLUDED_EVALUATION_INCOMPLETE", "BLOCKED_PENDING_RUN"}
    )
    assert (df["status"] == "FAIL").sum() == 0, (
        "All saved metrics must match recomputed values"
    )


def test_naked_cv_fpr_emits_fail_warning(tmp_path: Path) -> None:
    """Verify NAKED_CV_FPR warning is emitted if metrics are missing mean/std helper stats."""
    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    result_dir = (
        outputs
        / "results/nbaiot_main"
        / ThresholdPolicy.GLOBAL_THRESHOLD.value
        / "seed_0"
    )
    payload = json.loads((result_dir / ArtifactFile.METRICS).read_text("utf-8"))
    del payload["mean_fpr"]
    del payload["std_fpr"]
    (result_dir / ArtifactFile.METRICS).write_text(json.dumps(payload))
    run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)

    warnings_text = (audit_dir / AuditArtifact.WARNINGS).read_text()
    assert WarningCode.NAKED_CV_FPR in warnings_text, (
        "Expected NAKED_CV_FPR warning in audit output"
    )
