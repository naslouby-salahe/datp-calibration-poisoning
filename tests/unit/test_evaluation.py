from __future__ import annotations

import dataclasses
import math
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pytest

from datp.config import ExperimentStage
from datp.core import ClientThreshold, PolicyRunId, ThresholdResult, TrainingCellId
from datp.enums import ClientStatus, ScoringStage, ThresholdPolicy
from datp.evaluation import (
    BinaryMetrics,
    BinaryRankingMetrics,
    ClientEvaluationRecord,
    ConfusionCounts,
    aggregate_dispersion,
    build_evaluation_result,
    compute_binary_ranking_metrics,
    compute_client_record,
    evaluate_policy_run,
    recompute_binary_metrics,
)
from datp.scoring import ScoreProvider
from datp.statistics import cv
from datp.thresholding import MetricsBuildRequest, build_metrics_dict
from tests.fixtures import _make_client_record, _make_eval_result, _write_score_artifact


def _ct(threshold: float = 0.5) -> ClientThreshold:
    return ClientThreshold(
        client_id="test",
        threshold=threshold,
        status=ClientStatus.ELIGIBLE,
        strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
    )


def test_compute_client_metrics_perfect_separation() -> None:
    benign = np.array([0.1, 0.2, 0.3, 0.5, 0.9])
    attack = np.array([2.1, 2.5, 3.0, 4.0])
    result = compute_client_record("test", benign, attack, _ct(1.5))

    assert result.metrics.fpr == pytest.approx(0.0)
    assert result.metrics.tpr == pytest.approx(1.0)
    assert result.metrics.balanced_accuracy == pytest.approx(1.0)
    assert result.confusion.fp == 0
    assert result.confusion.tp == 4
    assert result.confusion.tn == 5
    assert result.confusion.fn == 0
    assert result.n_benign == 5
    assert result.n_attack == 4


def test_threshold_rule_strictly_greater_than() -> None:
    benign = np.array([1.5, 0.5])
    attack = np.array([1.5, 2.0])
    result = compute_client_record("test", benign, attack, _ct(1.5))
    assert result.confusion.tn == 2
    assert result.confusion.fn == 1
    assert result.confusion.tp == 1


def test_compute_client_metrics_all_false_positives() -> None:
    benign = np.array([0.1, 0.5, 1.0, 2.0])
    attack = np.array([3.0, 4.0])
    result = compute_client_record("test", benign, attack, _ct(0.0))

    assert result.metrics.fpr == pytest.approx(1.0)
    assert result.metrics.tpr == pytest.approx(1.0)
    assert result.confusion.fp == 4
    assert result.confusion.tn == 0


def test_benign_only_client_produces_fpr_and_nan_attack_metrics() -> None:
    benign = np.array([0.1, 0.5, 0.9])
    attack = np.array([], dtype=np.float64)
    result = compute_client_record("test", benign, attack, _ct(0.7))

    assert not math.isnan(result.metrics.fpr)
    assert math.isnan(result.metrics.tpr)
    assert math.isnan(result.metrics.balanced_accuracy)
    assert math.isnan(result.metrics.macro_f1)
    assert result.n_benign == 3
    assert result.n_attack == 0


def test_macro_f1_matches_sklearn_zero_division_behavior() -> None:
    benign = np.array([2.0, 3.0, 4.0, 5.0])
    attack = np.array([0.1, 0.2, 0.3])
    result = compute_client_record("test", benign, attack, _ct(1.5))
    assert result.confusion.fp == 4
    assert result.confusion.tn == 0
    assert result.confusion.tp == 0
    assert result.confusion.fn == 3
    assert result.metrics.macro_f1 == pytest.approx(0.0)


_STAGE = ExperimentStage.NBAIOT_MAIN


def _ct_evaluate_baseline(
    client_id: str,
    strategy: ThresholdPolicy = ThresholdPolicy.GLOBAL_THRESHOLD,
    threshold: float = 0.5,
) -> ClientThreshold:
    return ClientThreshold(
        client_id=client_id,
        threshold=threshold,
        status=ClientStatus.ELIGIBLE,
        strategy=strategy,
    )


def test_evaluate_policy_run_rejects_empty_thresholds() -> None:
    with pytest.raises(ValueError, match="empty"):
        evaluate_policy_run([], Path("/nonexistent"), _STAGE, 0, score_provider=None)


def test_evaluate_policy_run_rejects_duplicate_client_ids() -> None:
    ct = _ct_evaluate_baseline("c1")
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        evaluate_policy_run(
            [ct, ct], Path("/nonexistent"), _STAGE, 0, score_provider=None
        )


def test_evaluate_policy_run_rejects_mixed_strategies() -> None:
    ct1 = _ct_evaluate_baseline("c1", strategy=ThresholdPolicy.GLOBAL_THRESHOLD)
    ct2 = _ct_evaluate_baseline("c2", strategy=ThresholdPolicy.LOCAL_THRESHOLD)
    with pytest.raises(ValueError, match="[Mm]ixed"):
        evaluate_policy_run(
            [ct1, ct2], Path("/nonexistent"), _STAGE, 0, score_provider=None
        )


def test_evaluate_policy_run_rejects_missing_preloaded_client() -> None:
    ct = _ct_evaluate_baseline("c1")
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = ScoreProvider(Path(tmpdir))
        with pytest.raises(FileNotFoundError):
            evaluate_policy_run([ct], Path(tmpdir), _STAGE, 0, score_provider=provider)


def test_evaluate_policy_run_accepts_score_provider_and_marks_eval_incomplete(
    tmp_path: Path,
) -> None:
    _write_score_artifact(
        tmp_path / ScoringStage.TEST_BENIGN / "c1.parquet", [0.1, 0.2]
    )
    _write_score_artifact(tmp_path / ScoringStage.TEST_ATTACK / "c1.parquet", [])

    result = evaluate_policy_run(
        [_ct_evaluate_baseline("c1", threshold=0.15)],
        tmp_path,
        _STAGE,
        0,
        score_provider=ScoreProvider(tmp_path),
    )

    assert result.incomplete_ids == ("c1",)
    assert result.run.stage == _STAGE
    assert result.run.policy == ThresholdPolicy.GLOBAL_THRESHOLD


def test_attack_empty_valid_artifact_is_eval_incomplete() -> None:
    import math

    import numpy as np

    from datp.evaluation import compute_client_record

    benign = np.array([0.5, 0.6, 0.7])
    attack = np.array([], dtype=np.float64)
    ct = ClientThreshold(
        client_id="test",
        threshold=0.8,
        status=ClientStatus.ELIGIBLE,
        strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
    )
    result = compute_client_record("test", benign, attack, ct)
    assert result.n_attack == 0
    assert math.isnan(result.metrics.tpr)
    assert math.isnan(result.metrics.balanced_accuracy)
    assert math.isnan(result.metrics.macro_f1)
    assert not math.isnan(result.metrics.fpr)


def test_eval_incomplete_excluded_from_attack_metrics() -> None:
    c1 = _make_client_record("c1", fpr=0.1, tpr=0.9, n_attack=100)
    c2 = _make_client_record("c2", fpr=0.2, tpr=0.8, n_attack=100)
    c3_noattack = ClientEvaluationRecord(
        client_id="c3",
        metrics=BinaryMetrics(
            fpr=0.05,
            tpr=float("nan"),
            tnr=0.95,
            fnr=float("nan"),
            balanced_accuracy=float("nan"),
            precision=float("nan"),
            recall=float("nan"),
            macro_f1=float("nan"),
        ),
        confusion=ConfusionCounts(tp=0, fp=5, tn=95, fn=0),
        n_benign=100,
        n_attack=0,
        threshold=ClientThreshold(
            client_id="c3",
            threshold=0.5,
            status=ClientStatus.ELIGIBLE,
            strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
        ),
        evaluation_incomplete=True,
    )

    disp = aggregate_dispersion(
        clients=(c1, c2, c3_noattack),
        eligible_ids=("c1", "c2", "c3"),
        incomplete_ids=("c3",),
    )

    assert disp.eligible_count == 3
    assert disp.mean_fpr == pytest.approx((0.1 + 0.2 + 0.05) / 3)

    assert not math.isnan(disp.worst_ba)
    assert disp.worst_ba == pytest.approx(0.8)


def test_pending_clients_excluded_from_eligible_dispersion() -> None:
    c_elig = _make_client_record("e1", fpr=0.1, tpr=0.9)
    c_pend = _make_client_record("p1", fpr=0.5, tpr=0.6)

    disp = aggregate_dispersion(
        clients=(c_elig, c_pend),
        eligible_ids=("e1",),
        incomplete_ids=(),
    )

    assert disp.eligible_count == 1
    assert disp.mean_fpr == pytest.approx(0.1)


def test_evaluation_result_asdict() -> None:
    c1 = _make_client_record("c1", fpr=0.1, tpr=0.9)
    ev = _make_eval_result([c1], ["c1"], [])
    d = dataclasses.asdict(ev)
    assert "run" in d
    assert "clients" in d
    assert "coverage_ratio" in d
    assert "dispersion" in d
    assert "cv_fpr" in d["dispersion"]
    assert "iqr_fpr" in d["dispersion"]
    assert "worst_ba" in d["dispersion"]
    assert "p10_macro_f1" in d["dispersion"]
    assert isinstance(d["clients"], tuple)


def test_client_record_asdict() -> None:
    cr = _make_client_record("c1", fpr=0.05, tpr=0.95)
    d = dataclasses.asdict(cr)
    assert d["client_id"] == "c1"
    assert "confusion" in d
    assert set(d["confusion"].keys()) == {"tp", "fp", "tn", "fn"}


def test_metrics_serialization_contains_eligibility_threshold_and_provenance_fields() -> (
    None
):
    from datp.evaluation import compute_client_record as _ccr

    ct_eligible = ClientThreshold(
        client_id="c1",
        threshold=0.5,
        status=ClientStatus.ELIGIBLE,
        strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
    )
    c1_rec = _ccr(
        "c1", np.array([0.01, 0.02, 0.07]), np.array([0.08, 0.09, 0.10]), ct_eligible
    )
    ct_pending = ClientThreshold(
        client_id="c2",
        threshold=0.5,
        status=ClientStatus.CALIBRATION_PENDING,
        strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
    )
    c2_rec = ClientEvaluationRecord(
        client_id="c2",
        metrics=c1_rec.metrics,
        confusion=c1_rec.confusion,
        n_benign=c1_rec.n_benign,
        n_attack=c1_rec.n_attack,
        threshold=ct_pending,
        evaluation_incomplete=c1_rec.evaluation_incomplete,
    )
    cell = TrainingCellId(stage=_STAGE, seed=0)
    run = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
    ev = build_evaluation_result(
        policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        stage=_STAGE,
        seed=0,
        clients=(c1_rec, c2_rec),
        eligible_ids=("c1",),
        pending_ids=("c2",),
        incomplete_ids=(),
    )
    metrics = build_metrics_dict(
        MetricsBuildRequest(
            eval_result=ev,
            threshold_result=ThresholdResult(
                run=run,
                tau_global=0.5,
                client_thresholds=(
                    ClientThreshold(
                        client_id="c1",
                        threshold=0.5,
                        status=ClientStatus.ELIGIBLE,
                        strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
                    ),
                    ClientThreshold(
                        client_id="c2",
                        threshold=0.5,
                        status=ClientStatus.CALIBRATION_PENDING,
                        strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
                    ),
                ),
                cluster=None,
            ),
            config_identity="test",
            split_manifest_identity="test",
            model_identity="test",
            score_artifact_identity="test",
        )
    ).model_dump(mode="json")
    for key in (
        "schema_version",
        "metric_schema_version",
        "threshold_schema_version",
        "eligible_ids",
        "pending_ids",
        "eval_incomplete_ids",
        "coverage_ratio",
        "aggregate_metrics",
        "provenance",
    ):
        assert key in metrics
    assert metrics["per_client"][1]["calibration_pending"] is True
    assert metrics["per_client"][1]["threshold_source"] == "tau_global_fallback"


def test_build_evaluation_result_rejects_undefined_eligible_fpr() -> None:
    client = ClientEvaluationRecord(
        client_id="attack_only",
        metrics=BinaryMetrics(
            fpr=float("nan"),
            tpr=1.0,
            tnr=float("nan"),
            fnr=0.0,
            balanced_accuracy=float("nan"),
            precision=float("nan"),
            recall=1.0,
            macro_f1=float("nan"),
        ),
        confusion=ConfusionCounts(tp=3, fp=0, tn=0, fn=0),
        n_benign=0,
        n_attack=3,
        threshold=ClientThreshold(
            client_id="attack_only",
            threshold=0.5,
            status=ClientStatus.ELIGIBLE,
            strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
        ),
        evaluation_incomplete=False,
    )

    with pytest.raises(ValueError, match="Undefined eligible-client FPR"):
        build_evaluation_result(
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            stage=_STAGE,
            seed=0,
            clients=(client,),
            eligible_ids=("attack_only",),
            pending_ids=(),
            incomplete_ids=(),
        )


def test_build_evaluation_result_rejects_mixed_eligibility_status() -> None:
    client = _make_client_record("c1", fpr=0.1, tpr=0.9)

    with pytest.raises(ValueError, match="mixed eligibility"):
        build_evaluation_result(
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            stage=_STAGE,
            seed=0,
            clients=(client,),
            eligible_ids=("c1",),
            pending_ids=("c1",),
            incomplete_ids=(),
        )


def test_single_cv_implementation() -> None:
    result = subprocess.run(
        ["grep", "-rn", r"def cv(", "src/datp/"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[2],
    )
    lines = [line for line in result.stdout.strip().splitlines() if line.strip()]
    assert len(lines) == 1, f"Expected 1 'def cv(' match, got {len(lines)}: {lines}"
    assert "statistics.py" in lines[0]


def test_cv_fpr_eligible_only() -> None:
    c1 = _make_client_record("c1", fpr=0.10, tpr=0.90)
    c2 = _make_client_record("c2", fpr=0.15, tpr=0.85)
    c3 = _make_client_record("c3", fpr=0.20, tpr=0.80)
    c4_pending = _make_client_record("c4", fpr=0.50, tpr=0.60)

    ev = _make_eval_result(
        per_client=[c1, c2, c3, c4_pending],
        eligible_ids=["c1", "c2", "c3"],
        pending_ids=["c4"],
    )

    expected_cv = cv(np.array([0.10, 0.15, 0.20]), ddof=0)
    assert abs(ev.dispersion.cv_fpr - expected_cv) < 1e-12
    assert (
        abs(ev.dispersion.cv_fpr - cv(np.array([0.10, 0.15, 0.20, 0.50]), ddof=0))
        > 0.01
    )


def test_coverage_ratio() -> None:
    clients = [_make_client_record(f"c{i}", fpr=0.1, tpr=0.9) for i in range(4)]
    ev = _make_eval_result(
        per_client=clients,
        eligible_ids=["c0", "c1", "c2"],
        pending_ids=["c3"],
    )
    assert ev.coverage_ratio == pytest.approx(0.75)


def test_fpr_bundle_includes_mean_std_worst() -> None:
    c1 = _make_client_record("c1", fpr=0.10, tpr=0.90)
    c2 = _make_client_record("c2", fpr=0.20, tpr=0.80)
    c3 = _make_client_record("c3", fpr=0.30, tpr=0.70)
    ev = _make_eval_result([c1, c2, c3], ["c1", "c2", "c3"], [])

    assert ev.dispersion.mean_fpr == pytest.approx(0.20, abs=1e-10)
    assert ev.dispersion.std_fpr == pytest.approx(
        np.std([0.10, 0.20, 0.30], ddof=1), abs=1e-10
    )
    assert ev.dispersion.worst_client_fpr == pytest.approx(0.30, abs=1e-10)
    assert ev.dispersion.worst_client_id == "c3"
    assert ev.dispersion.eligible_count == 3
    assert ev.dispersion.client_count == 3


def test_bundle_excludes_pending_from_fpr_stats() -> None:
    c1 = _make_client_record("c1", fpr=0.10, tpr=0.90)
    c2 = _make_client_record("c2", fpr=0.20, tpr=0.80)
    c_pending = _make_client_record("cp", fpr=0.99, tpr=0.50)
    ev = _make_eval_result([c1, c2, c_pending], ["c1", "c2"], ["cp"])

    assert ev.dispersion.mean_fpr == pytest.approx(0.15, abs=1e-10)
    assert ev.dispersion.worst_client_fpr == pytest.approx(0.20, abs=1e-10)
    assert ev.dispersion.worst_client_id == "c2"
    assert ev.dispersion.eligible_count == 2
    assert ev.dispersion.client_count == 3


def test_bundle_single_eligible_std_is_nan() -> None:
    c1 = _make_client_record("c1", fpr=0.10, tpr=0.90)
    ev = _make_eval_result([c1], ["c1"], [])
    assert math.isnan(ev.dispersion.std_fpr)
    assert ev.dispersion.mean_fpr == pytest.approx(0.10, abs=1e-10)


def test_bundle_no_eligible_all_nan() -> None:
    c_pending = _make_client_record("cp", fpr=0.5, tpr=0.5)
    ev = _make_eval_result([c_pending], [], ["cp"])
    assert math.isnan(ev.dispersion.cv_fpr)
    assert math.isnan(ev.dispersion.mean_fpr)
    assert math.isnan(ev.dispersion.std_fpr)
    assert math.isnan(ev.dispersion.worst_client_fpr)
    assert ev.dispersion.worst_client_id is None
    assert ev.dispersion.eligible_count == 0
    assert ev.dispersion.client_count == 1


class TestBinaryRankingMetrics:
    """Binary ranking metric computation."""

    def test_is_frozen_dataclass(self) -> None:
        m = BinaryRankingMetrics(auroc=0.9, pr_auc=0.8)
        with pytest.raises(Exception):
            setattr(m, "auroc", 0.5)

    def test_construct_with_values(self) -> None:
        m = BinaryRankingMetrics(auroc=0.95, pr_auc=0.87)
        assert m.auroc == pytest.approx(0.95)
        assert m.pr_auc == pytest.approx(0.87)

    def test_construct_with_none(self) -> None:
        m = BinaryRankingMetrics(auroc=None, pr_auc=None)
        assert m.auroc is None
        assert m.pr_auc is None


class TestComputeBinaryRankingMetrics:
    """End-to-end binary ranking metrics from scores."""

    def test_perfect_separation(self) -> None:
        benign = np.array([0.1, 0.2, 0.15], dtype=np.float64)
        attack = np.array([0.9, 0.95, 0.85], dtype=np.float64)
        result = compute_binary_ranking_metrics(benign, attack)
        assert result.auroc == pytest.approx(1.0)
        assert result.pr_auc == pytest.approx(1.0)

    def test_random_scores_near_chance(self) -> None:
        rng = np.random.default_rng(42)
        benign = rng.normal(0.5, 0.1, size=500).astype(np.float64)
        attack = rng.normal(0.5, 0.1, size=500).astype(np.float64)
        result = compute_binary_ranking_metrics(benign, attack)
        assert result.auroc is not None
        assert result.pr_auc is not None
        assert 0.3 < result.auroc < 0.7
        assert 0.3 < result.pr_auc < 0.7

    def test_moderate_separation(self) -> None:
        rng = np.random.default_rng(42)
        benign = rng.normal(0.3, 0.1, size=200).astype(np.float64)
        attack = rng.normal(0.7, 0.1, size=200).astype(np.float64)
        result = compute_binary_ranking_metrics(benign, attack)
        assert result.auroc is not None
        assert result.pr_auc is not None
        assert result.auroc > 0.8
        assert result.pr_auc > 0.8

    def test_empty_benign_returns_none(self) -> None:
        result = compute_binary_ranking_metrics(
            np.empty(0, dtype=np.float64), np.array([0.5, 0.6])
        )
        assert result.auroc is None
        assert result.pr_auc is None

    def test_empty_attack_returns_none(self) -> None:
        result = compute_binary_ranking_metrics(
            np.array([0.1, 0.2]), np.empty(0, dtype=np.float64)
        )
        assert result.auroc is None
        assert result.pr_auc is None

    def test_none_benign_returns_none(self) -> None:
        result = compute_binary_ranking_metrics(
            None,  # type: ignore[arg-type]
            np.array([0.5, 0.6]),
        )
        assert result.auroc is None
        assert result.pr_auc is None

    def test_none_attack_returns_none(self) -> None:
        result = compute_binary_ranking_metrics(
            np.array([0.1, 0.2]),
            None,  # type: ignore[arg-type]
        )
        assert result.auroc is None
        assert result.pr_auc is None

    def test_single_sample_each(self) -> None:
        result = compute_binary_ranking_metrics(np.array([0.3]), np.array([0.7]))
        assert result.auroc == pytest.approx(1.0)
        assert result.pr_auc == pytest.approx(1.0)

    def test_single_sample_tied(self) -> None:
        result = compute_binary_ranking_metrics(np.array([0.5]), np.array([0.5]))
        assert result.auroc is not None
        assert result.pr_auc is not None
        assert 0.0 <= result.auroc <= 1.0
        assert 0.0 <= result.pr_auc <= 1.0

    def test_inverted_scores_low_auroc(self) -> None:
        benign = np.array([0.9, 0.95, 0.85], dtype=np.float64)
        attack = np.array([0.1, 0.2, 0.15], dtype=np.float64)
        result = compute_binary_ranking_metrics(benign, attack)

        assert result.auroc == pytest.approx(0.0)
        assert result.pr_auc is not None
        assert 0.3 <= result.pr_auc <= 0.5


class TestRecomputeBinaryMetrics:
    """Recomputation of binary classification metrics from saved artifacts."""

    def test_matches_compute_client_record(self) -> None:
        benign = np.array([0.1, 0.2, 0.7], dtype=float)
        attack = np.array([0.8, 0.9, 0.95], dtype=float)
        ct = ClientThreshold(
            client_id="c",
            threshold=0.5,
            status=ClientStatus.ELIGIBLE,
            strategy=ThresholdPolicy.GLOBAL_THRESHOLD,
        )
        cr = compute_client_record("c", benign, attack, ct)
        bm = recompute_binary_metrics(
            cr.confusion.tp, cr.confusion.fp, cr.confusion.tn, cr.confusion.fn
        )
        assert bm.fpr == pytest.approx(cr.metrics.fpr)
        assert bm.tpr == pytest.approx(cr.metrics.tpr)
        assert bm.balanced_accuracy == pytest.approx(cr.metrics.balanced_accuracy)
        assert bm.macro_f1 == pytest.approx(cr.metrics.macro_f1)

    def test_zero_attack_returns_nan_for_attack_metrics(self) -> None:
        bm = recompute_binary_metrics(tp=0, fp=2, tn=8, fn=0)
        assert not math.isnan(bm.fpr)
        assert math.isnan(bm.tpr)
        assert math.isnan(bm.balanced_accuracy)
        assert math.isnan(bm.macro_f1)

    def test_zero_benign_returns_nan_fpr(self) -> None:
        bm = recompute_binary_metrics(tp=3, fp=0, tn=0, fn=1)
        assert math.isnan(bm.fpr)
        assert not math.isnan(bm.tpr)

    def test_perfect_classifier(self) -> None:
        bm = recompute_binary_metrics(tp=10, fp=0, tn=10, fn=0)
        assert bm.fpr == pytest.approx(0.0)
        assert bm.tpr == pytest.approx(1.0)
        assert bm.balanced_accuracy == pytest.approx(1.0)
        assert bm.macro_f1 == pytest.approx(1.0)

    def test_worst_classifier(self) -> None:
        bm = recompute_binary_metrics(tp=0, fp=10, tn=0, fn=10)
        assert bm.fpr == pytest.approx(1.0)
        assert bm.tpr == pytest.approx(0.0)
        assert bm.balanced_accuracy == pytest.approx(0.0)
        assert bm.macro_f1 == pytest.approx(0.0)

    def test_denominator_check_fp_plus_tn_equals_n_benign(self) -> None:
        bm = recompute_binary_metrics(tp=5, fp=3, tn=7, fn=2)
        assert bm.fpr == pytest.approx(3 / 10)

    def test_denominator_check_tp_plus_fn_equals_n_attack(self) -> None:
        bm = recompute_binary_metrics(tp=5, fp=3, tn=7, fn=2)
        assert bm.tpr == pytest.approx(5 / 7)
