from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
import pytest
from sklearn.metrics import f1_score

from datp.artifacts.names import ArtifactFile
from datp.checkpointing.enums import ConvergenceStatus
from datp.config.compose import BASE_CONFIG
from datp.core.enums import (
    Baseline,
    NormalizationScope,
    Regime,
    ThresholdAggregationMethod,
)
from datp.core.metric_enums import MetricName
from datp.core.provenance import hash_file, source_hash
from datp.core.seeds import set_seeds
from datp.core.types import ClientThreshold
from datp.data.catalog import DatasetID
from datp.data.common.storage import write_artifact
from datp.evaluation.metrics import compute_client_record
from datp.scoring.schema import SCORE_COLUMN
from datp.validation.constants import (
    AUDIT_SUMMARY_MD,
    B4_CLUSTER_STABILITY_CSV,
    BASELINE_INVARIANTS_JSON,
    METRIC_DENOMINATOR_AUDIT_CSV,
    RECONSTRUCTION_ERROR_SUMMARY_CSV,
    REGIME_C_SEVERITY_TREND_CSV,
    RUN_MANIFEST_CSV,
    THRESHOLD_VALUES_CSV,
    WARNINGS_MD,
)
from datp.validation.enums import (
    AuditSeverity,
    WarningCode,
    WorstDirection,
)
from datp.validation._audit_helpers import _split_hash
from datp.validation._audit_types import _CellPanel
from datp.validation.results import (
    _METRICS_SOURCE_FILES,
    _SCORING_SOURCE_FILES,
    _THRESHOLD_SOURCE_FILES,
    run_results_audit,
)
from datp.validation.schemas import RunManifestRecord, WarningRecord

CLIENTS = (
    "Danmini_Doorbell",
    "Ecobee_Thermostat",
    "Ennio_Doorbell",
    "Philips_B120N10_Baby_Monitor",
)

_SAFE_SCORE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


def _safe_score_path(root: Path, stage: str, client_id: str) -> Path:
    if not _SAFE_SCORE_NAME.fullmatch(client_id):
        raise ValueError(f"Unsafe client id in score fixture: {client_id}")
    base = (root / "scores/a/seed_0").resolve()
    path = (base / stage / f"{client_id}.parquet").resolve()
    if not path.is_relative_to(base):
        raise ValueError(f"Score fixture path escapes base: {path}")
    return path


def _write_scores(root: Path) -> None:
    for index, client_id in enumerate(CLIENTS):
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


def _metrics_payload(baseline: Baseline) -> dict:
    per_client = []
    for client_id in CLIENTS:
        ct = ClientThreshold(
            client_id=client_id,
            threshold=0.06,
            calibration_pending=False,
            strategy=baseline,
        )
        rec = compute_client_record(
            client_id,
            np.array([0.01, 0.02, 0.07]),
            np.array([0.08, 0.09, 0.10]),
            ct,
        )
        per_client.append(
            {
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
                "threshold_source": baseline.value,
            }
        )
    return {
        "schema_version": "2",
        "metric_schema_version": "2",
        "threshold_schema_version": "1",
        "run_id": f"a_{baseline.value}_seed0",
        "run_kind": "core_ladder",
        "dataset": "nbaiot",
        "alpha": None,
        "baseline": baseline.value,
        "threshold_scope": "eligible_client_arithmetic_mean",
        "threshold_strategy_name": baseline.value,
        "coverage_ratio": 1.0,
        "cv_fpr": 0.0 if baseline == Baseline.B2 else 0.1,
        "mean_fpr": 0.0,
        "std_fpr": 0.0,
        "cv_tpr": 0.0,
        "iqr_fpr": 0.0,
        "iqr_tpr": 0.0,
        "worst_client_fpr": 0.0,
        "worst_client_id": CLIENTS[0],
        "eligible_count": len(CLIENTS),
        "client_count": len(CLIENTS),
        "pending_count": 0,
        "eval_incomplete_count": 0,
        "eligible_ids": list(CLIENTS),
        "pending_ids": [],
        "eval_incomplete_ids": [],
        "aggregate_metrics": {"cv_fpr": 0.0 if baseline == Baseline.B2 else 0.1},
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
        "regime": "a",
        "seed": 0,
        "tau_global": 0.06,
        "normalization_scope": "per_client_zscore",
    }


def _write_minimal_outputs(root: Path) -> None:
    _write_scores(root)
    manifest = {
        "dataset": "nbaiot",
        "file_hashes": {"fixture": "abc"},
        "metadata": {"n_features": 115, "n_devices": len(CLIENTS), "n_clients": None},
        "created": "2026-04-26T00:00:00+00:00",
    }
    manifest_path = root / "data/processed/nbaiot" / ArtifactFile.MANIFEST
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    ckpt = root / "checkpoints/a/seed_0/model.pt"
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    ckpt.write_bytes(b"fixture-model")
    for baseline in (Baseline.B1, Baseline.B2, Baseline.B3, Baseline.B4):
        result_dir = root / "results/a" / baseline.value / "seed_0"
        result_dir.mkdir(parents=True, exist_ok=True)
        (result_dir / ArtifactFile.METRICS).write_text(
            json.dumps(_metrics_payload(baseline)), encoding="utf-8"
        )
        (result_dir / ArtifactFile.RESOLVED_CONFIG).write_text(
            "seed: 0\n", encoding="utf-8"
        )


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


def test_results_audit_generates_core_artifacts(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    paths = run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)

    assert paths["run_manifest"].is_file()
    assert (audit_dir / BASELINE_INVARIANTS_JSON).is_file()
    assert (audit_dir / RUN_MANIFEST_CSV).is_file()
    assert (audit_dir / RECONSTRUCTION_ERROR_SUMMARY_CSV).is_file()
    assert (audit_dir / METRIC_DENOMINATOR_AUDIT_CSV).is_file()
    assert (audit_dir / THRESHOLD_VALUES_CSV).is_file()
    assert (audit_dir / WARNINGS_MD).is_file()
    assert (audit_dir / AUDIT_SUMMARY_MD).is_file()

    invariants = json.loads(
        (audit_dir / BASELINE_INVARIANTS_JSON).read_text(encoding="utf-8")
    )
    assert invariants[0]["status"] == "PASS"
    assert invariants[0]["split_hash_shared"] is True
    assert invariants[0]["reconstruction_error_hashes_shared"] is True

    thresholds = pd.read_csv(audit_dir / THRESHOLD_VALUES_CSV)
    assert "threshold_aggregation_method" in thresholds.columns
    assert "local_tau_i" in thresholds.columns
    b1_rows = thresholds[thresholds["baseline"] == "b1"]
    assert set(b1_rows["threshold_aggregation_method"]) == {
        "eligible_client_arithmetic_mean"
    }


def test_results_audit_generates_severity_trend_and_cluster_stability(
    tmp_path: Path,
) -> None:
    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    paths = run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)

    assert "regime_c_severity_trend" in paths
    assert "b4_cluster_stability" in paths
    assert (audit_dir / REGIME_C_SEVERITY_TREND_CSV).is_file()
    assert (audit_dir / B4_CLUSTER_STABILITY_CSV).is_file()

    summary = (audit_dir / AUDIT_SUMMARY_MD).read_text(encoding="utf-8")
    assert "B0 is a centralized reference comparator" in summary


def test_split_hash_stability(tmp_path: Path) -> None:
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


def test_results_audit_generates_seed_deltas(tmp_path: Path) -> None:
    from datp.validation.constants import SEED_DELTAS_CSV

    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)
    csv_path = audit_dir / SEED_DELTAS_CSV
    assert csv_path.is_file()
    df = pd.read_csv(csv_path)
    assert "regime" in df.columns
    assert "seed" in df.columns
    assert "b1_cv_fpr" in df.columns
    assert "b2_cv_fpr" in df.columns
    assert "delta_cv_fpr_b1_minus_b2" in df.columns
    assert "coverage_ratio" in df.columns


def test_results_audit_generates_regime_c_alpha_csv(tmp_path: Path) -> None:
    from datp.validation.constants import REGIME_C_ALPHA_AUDIT_CSV

    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    paths = run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)
    # File must exist even when empty (no Regime C runs in fixture)
    assert (audit_dir / REGIME_C_ALPHA_AUDIT_CSV).is_file()
    assert "regime_c_alpha_audit" in paths


def test_flat_cv_tpr_warning_emitted() -> None:
    from datp.validation._warnings import (
        emit_flat_cv_tpr_warnings as _emit_flat_cv_tpr_warnings,
    )

    warnings_out: list[WarningRecord] = []
    cell_panel: dict[tuple[Regime, int, str | None, Baseline], _CellPanel] = {
        (Regime.A, 0, None, Baseline.B1): _CellPanel(cv_tpr=0.5),
        (Regime.A, 0, None, Baseline.B2): _CellPanel(cv_tpr=0.5),
        (Regime.A, 0, None, Baseline.B3): _CellPanel(cv_tpr=0.5),
        (Regime.A, 0, None, Baseline.B4): _CellPanel(cv_tpr=0.5),
    }
    _emit_flat_cv_tpr_warnings(cell_panel, warnings_out)
    assert any(w.code == "FLAT_CV_TPR_SUSPICIOUS" for w in warnings_out)


def test_no_flat_cv_tpr_warning_when_different() -> None:
    from datp.validation._warnings import (
        emit_flat_cv_tpr_warnings as _emit_flat_cv_tpr_warnings,
    )

    warnings_out: list[WarningRecord] = []
    cell_panel: dict[tuple[Regime, int, str | None, Baseline], _CellPanel] = {
        (Regime.A, 0, None, Baseline.B1): _CellPanel(cv_tpr=0.3),
        (Regime.A, 0, None, Baseline.B2): _CellPanel(cv_tpr=0.6),
        (Regime.A, 0, None, Baseline.B3): _CellPanel(cv_tpr=0.4),
        (Regime.A, 0, None, Baseline.B4): _CellPanel(cv_tpr=0.5),
    }
    _emit_flat_cv_tpr_warnings(cell_panel, warnings_out)
    assert not any(w.code == "FLAT_CV_TPR_SUSPICIOUS" for w in warnings_out)


def test_worst_client_stability_warning_when_always_same() -> None:
    from datp.validation._warnings import (
        emit_worst_client_stability_warnings as _emit_worst_client_stability_warnings,
    )
    from datp.validation.schemas import WorstClientRecord

    worst_records = [
        WorstClientRecord(
            run_id=f"a_b1_seed{s}",
            seed=s,
            regime=Regime.A,
            baseline=Baseline.B1,
            alpha=None,
            metric=MetricName.FPR,
            direction=WorstDirection.MAX_IS_WORST,
            worst_client_id="Danmini_Doorbell",
            worst_value=0.9,
            eligible_pool_size=4,
        )
        for s in range(5)
    ]
    warnings_out: list[WarningRecord] = []
    _emit_worst_client_stability_warnings(worst_records, warnings_out)
    codes = [w.code for w in warnings_out]
    assert "WORST_CLIENT_STABLE" in codes


def test_worst_client_varies_info_when_different() -> None:
    from datp.validation._warnings import (
        emit_worst_client_stability_warnings as _emit_worst_client_stability_warnings,
    )
    from datp.validation.schemas import WorstClientRecord

    worst_records = [
        WorstClientRecord(
            run_id=f"a_b1_seed{s}",
            seed=s,
            regime=Regime.A,
            baseline=Baseline.B1,
            alpha=None,
            metric=MetricName.FPR,
            direction=WorstDirection.MAX_IS_WORST,
            worst_client_id=f"Client_{s}",
            worst_value=0.9,
            eligible_pool_size=4,
        )
        for s in range(5)
    ]
    warnings_out: list[WarningRecord] = []
    _emit_worst_client_stability_warnings(worst_records, warnings_out)
    codes = [w.code for w in warnings_out]
    assert "WORST_CLIENT_VARIES" in codes
    assert "WORST_CLIENT_STABLE" not in codes


def test_results_audit_fpr_companion_has_required_columns(tmp_path: Path) -> None:
    from datp.validation.constants import FPR_COMPANION_METRICS_CSV

    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)
    df = pd.read_csv(audit_dir / FPR_COMPANION_METRICS_CSV)
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
    from datp.validation.constants import METRIC_RECOMPUTATION_AUDIT_CSV

    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    paths = run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)
    assert (audit_dir / METRIC_RECOMPUTATION_AUDIT_CSV).is_file()
    assert "metric_recomputation_audit" in paths
    df = pd.read_csv(audit_dir / METRIC_RECOMPUTATION_AUDIT_CSV)
    for col in (
        "run_id",
        "seed",
        "regime",
        "baseline",
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


def test_recomputation_fails_on_wrong_fpr() -> None:
    from datp.validation._recomputation import (
        RecomputationParams,
        append_recomputation_records,
    )
    from datp.validation.enums import DenominatorStatus

    records: list = []
    append_recomputation_records(
        records,
        RecomputationParams(
            run_id="a_b1_seed0",
            seed=0,
            regime=Regime.A,
            baseline=Baseline.B1,
            alpha=None,
            client_id="c1",
            tp=10,
            fp=0,
            tn=10,
            fn=0,
            n_benign=10,
            n_attack=10,
            saved_fpr=0.99,
            saved_tpr=1.0,
            saved_balanced_accuracy=1.0,
            saved_macro_f1=1.0,
        ),
    )
    fpr_rows = [r for r in records if r.metric == MetricName.FPR]
    assert len(fpr_rows) == 1
    assert fpr_rows[0].status == DenominatorStatus.FAIL
    assert fpr_rows[0].recomputed_value == pytest.approx(0.0)


def test_recomputation_excludes_attack_metrics_when_n_attack_zero() -> None:
    from datp.validation._recomputation import (
        RecomputationParams,
        append_recomputation_records,
    )
    from datp.validation.enums import DenominatorStatus

    records: list = []
    append_recomputation_records(
        records,
        RecomputationParams(
            run_id="a_b1_seed0",
            seed=0,
            regime=Regime.A,
            baseline=Baseline.B1,
            alpha=None,
            client_id="c1",
            tp=0,
            fp=1,
            tn=9,
            fn=0,
            n_benign=10,
            n_attack=0,
            saved_fpr=0.1,
            saved_tpr=None,
            saved_balanced_accuracy=None,
            saved_macro_f1=None,
        ),
    )
    for m in (MetricName.TPR, MetricName.BALANCED_ACCURACY, MetricName.MACRO_F1):
        rows = [r for r in records if r.metric == m]
        assert rows[0].status == DenominatorStatus.EXCLUDED_EVALUATION_INCOMPLETE

    fpr_rows = [r for r in records if r.metric == MetricName.FPR]
    assert fpr_rows[0].status == DenominatorStatus.PASS


def test_recomputation_fails_on_denominator_mismatch() -> None:
    from datp.validation._recomputation import (
        RecomputationParams,
        append_recomputation_records,
    )
    from datp.validation.enums import DenominatorStatus

    records: list = []
    # confusion matrix: fp=1, tn=8 → actual n_benign used internally = 9
    # stored row says n_benign=10 and fpr=0.1 (= 1/10), but recomputed = 1/9 ≈ 0.111
    append_recomputation_records(
        records,
        RecomputationParams(
            run_id="a_b1_seed0",
            seed=0,
            regime=Regime.A,
            baseline=Baseline.B1,
            alpha=None,
            client_id="c1",
            tp=5,
            fp=1,
            tn=8,
            fn=1,
            n_benign=10,
            n_attack=6,
            saved_fpr=0.1,
            saved_tpr=0.9,
            saved_balanced_accuracy=0.9,
            saved_macro_f1=0.9,
        ),
    )
    fpr_rows = [r for r in records if r.metric == MetricName.FPR]
    assert len(fpr_rows) == 1
    assert fpr_rows[0].status == DenominatorStatus.FAIL
    assert fpr_rows[0].recomputed_value == pytest.approx(1 / 9)


def test_naked_cv_fpr_emits_fail_warning(tmp_path: Path) -> None:
    from datp.validation.constants import WARNINGS_MD

    outputs = tmp_path / "outputs"
    audit_dir = tmp_path / "audit"

    _write_minimal_outputs(outputs)
    # Overwrite b1 metrics to strip companion fields
    result_dir = outputs / "results/a" / Baseline.B1.value / "seed_0"
    payload = json.loads((result_dir / ArtifactFile.METRICS).read_text("utf-8"))
    del payload["mean_fpr"]
    del payload["std_fpr"]
    (result_dir / ArtifactFile.METRICS).write_text(
        json.dumps(payload), encoding="utf-8"
    )
    run_results_audit(base_dir=outputs, audit_dir=audit_dir, cfg=BASE_CONFIG)

    warnings_text = (audit_dir / WARNINGS_MD).read_text(encoding="utf-8")
    assert WarningCode.NAKED_CV_FPR in warnings_text, (
        "Expected NAKED_CV_FPR warning in audit output"
    )


# ── check_b2_utility_tradeoff ──────────────────────────────


def test_check_b2_utility_tradeoff_warns_when_b2_improves_cv_fpr_but_worsens_utility() -> (
    None
):
    from datp.validation._warnings import (
        check_b2_utility_tradeoff as _check_b2_utility_tradeoff,
    )

    warnings_out: list[WarningRecord] = []
    b1 = _CellPanel(
        cv_fpr=0.3, macro_f1_mean=0.85, pr_auc_mean=0.90, auroc_mean=0.92, cv_tpr=0.80
    )
    b2 = _CellPanel(
        cv_fpr=0.2, macro_f1_mean=0.80, pr_auc_mean=0.88, auroc_mean=0.91, cv_tpr=0.78
    )
    _check_b2_utility_tradeoff((Regime.A, 0, None), b1, b2, warnings_out)
    codes = [w.code for w in warnings_out]
    assert WarningCode.B2_UTILITY_TRADEOFF in codes
    msg = warnings_out[0].message
    assert "macro_f1" in msg
    assert "pr_auc" in msg


def test_check_b2_utility_tradeoff_no_warning_when_cv_fpr_not_improved() -> None:
    from datp.validation._warnings import (
        check_b2_utility_tradeoff as _check_b2_utility_tradeoff,
    )

    warnings_out: list[WarningRecord] = []
    b1 = _CellPanel(cv_fpr=0.2, macro_f1_mean=0.80)
    b2 = _CellPanel(cv_fpr=0.3, macro_f1_mean=0.85)
    _check_b2_utility_tradeoff((Regime.A, 0, None), b1, b2, warnings_out)
    assert len(warnings_out) == 0


def test_check_b2_utility_tradeoff_no_warning_when_no_utility_worsened() -> None:
    from datp.validation._warnings import (
        check_b2_utility_tradeoff as _check_b2_utility_tradeoff,
    )

    warnings_out: list[WarningRecord] = []
    b1 = _CellPanel(cv_fpr=0.3, macro_f1_mean=0.80, auroc_mean=0.90, cv_tpr=0.75)
    b2 = _CellPanel(cv_fpr=0.2, macro_f1_mean=0.85, auroc_mean=0.92, cv_tpr=0.80)
    _check_b2_utility_tradeoff((Regime.A, 0, None), b1, b2, warnings_out)
    assert len(warnings_out) == 0


# ── emit_ciciot_homogeneity_warnings ───────────────────────


def test_emit_ciciot_homogeneity_warning_homogeneous() -> None:
    from datp.validation._warnings import (
        emit_ciciot_homogeneity_warnings as _emit_ciciot_homogeneity_warnings,
    )
    from datp.validation.enums import HomogeneityVerdict
    from datp.validation.schemas import CICIoTHomogeneityRecord

    warnings_out: list[WarningRecord] = []
    records = [
        CICIoTHomogeneityRecord(
            regime=Regime.B,
            seed=0,
            alpha=None,
            baseline=Baseline.B1,
            n_clients_compared=10,
            n_pairs=45,
            n_bins=20,
            pairwise_js_mean=0.02,
            pairwise_js_std=0.01,
            pairwise_js_p50=0.015,
            pairwise_js_p95=0.04,
            pairwise_js_max=0.05,
            fingerprint_method="benign_recon_error_histogram",
            homogeneity_verdict=HomogeneityVerdict.HOMOGENEOUS,
        )
    ]
    _emit_ciciot_homogeneity_warnings(records, warnings_out, homogeneity_threshold=0.05)
    assert any(w.code == WarningCode.CICIOT_HOMOGENEITY_VERIFIED for w in warnings_out)


def test_emit_ciciot_homogeneity_warning_heterogeneous() -> None:
    from datp.validation._warnings import (
        emit_ciciot_homogeneity_warnings as _emit_ciciot_homogeneity_warnings,
    )
    from datp.validation.enums import HomogeneityVerdict
    from datp.validation.schemas import CICIoTHomogeneityRecord

    warnings_out: list[WarningRecord] = []
    records = [
        CICIoTHomogeneityRecord(
            regime=Regime.B,
            seed=0,
            alpha=None,
            baseline=Baseline.B1,
            n_clients_compared=10,
            n_pairs=45,
            n_bins=20,
            pairwise_js_mean=0.12,
            pairwise_js_std=0.05,
            pairwise_js_p50=0.10,
            pairwise_js_p95=0.20,
            pairwise_js_max=0.22,
            fingerprint_method="benign_recon_error_histogram",
            homogeneity_verdict=HomogeneityVerdict.HETEROGENEOUS,
        )
    ]
    _emit_ciciot_homogeneity_warnings(records, warnings_out, homogeneity_threshold=0.05)
    assert any(w.code == WarningCode.CICIOT_NOT_HOMOGENEOUS for w in warnings_out)


def test_emit_ciciot_homogeneity_warning_incomplete() -> None:
    from datp.validation._warnings import (
        emit_ciciot_homogeneity_warnings as _emit_ciciot_homogeneity_warnings,
    )
    from datp.validation.enums import HomogeneityVerdict
    from datp.validation.schemas import CICIoTHomogeneityRecord

    warnings_out: list[WarningRecord] = []
    records = [
        CICIoTHomogeneityRecord(
            regime=Regime.B,
            seed=0,
            alpha=None,
            baseline=Baseline.B1,
            n_clients_compared=1,
            n_pairs=0,
            n_bins=20,
            pairwise_js_mean=None,
            pairwise_js_std=None,
            pairwise_js_p50=None,
            pairwise_js_p95=None,
            pairwise_js_max=None,
            fingerprint_method="benign_recon_error_histogram",
            homogeneity_verdict=HomogeneityVerdict.BLOCKED_PENDING_RUN,
        )
    ]
    _emit_ciciot_homogeneity_warnings(records, warnings_out, homogeneity_threshold=0.05)
    codes = [w.code for w in warnings_out]
    assert WarningCode.CICIOT_HOMOGENEITY_INCOMPLETE in codes


class TestProvenanceSourcePaths:
    """The source files hashed into provenance must exist; a stale path makes
    hash_file return the constant 'MISSING' sentinel, silently breaking
    traceability."""

    def test_all_provenance_source_files_exist(self) -> None:
        all_files = (
            *_SCORING_SOURCE_FILES,
            *_THRESHOLD_SOURCE_FILES,
            *_METRICS_SOURCE_FILES,
        )
        missing = [str(p) for p in all_files if hash_file(p) == "MISSING"]
        assert not missing, f"provenance source files not found: {missing}"

    def test_provenance_hashes_are_not_missing_sentinel(self) -> None:
        for group in (
            _SCORING_SOURCE_FILES,
            _THRESHOLD_SOURCE_FILES,
            _METRICS_SOURCE_FILES,
        ):
            digest = source_hash(list(group))
            # A list of all-MISSING files still hashes to a non-"MISSING" digest,
            # so assert against the degenerate all-missing digest explicitly.
            all_missing = source_hash([p.with_suffix(".does_not_exist") for p in group])
            assert digest != all_missing
