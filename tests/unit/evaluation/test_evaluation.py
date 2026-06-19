from __future__ import annotations

import dataclasses
import json
import math
import subprocess
from pathlib import Path

import numpy as np
import pytest

from datp.core.enums import (
    Baseline,
    Regime,
    ScoringStage,
)
from datp.core.identity import BaselineRunId, TrainingCellId
from datp.core.types import ClientThreshold, ThresholdMetadata, ThresholdResult
from datp.evaluation.confusion import save_confusion_matrices
from datp.evaluation.metric_filtering import _filter_eligible_metrics
from datp.evaluation.metrics import (
    BinaryMetrics,
    ClientEvaluationRecord,
    ConfusionCounts,
    EvaluationResult,
    build_evaluation_result,
    compute_client_record,
)
from datp.statistics.cv import cv
from datp.thresholding.metrics_serialization import build_metrics_dict
from tests.unit.conftest import _write_score_artifact


def _make_eval_result(
    per_client: list[ClientEvaluationRecord],
    eligible_ids: list[str],
    pending_ids: list[str],
    baseline: Baseline = Baseline.B1,
    regime: Regime = Regime.A,
    seed: int = 42,
    alpha: float | None = None,
    eval_incomplete_ids: list[str] | None = None,
) -> EvaluationResult:
    incomplete = eval_incomplete_ids or []
    return build_evaluation_result(
        baseline=baseline,
        regime=regime,
        seed=seed,
        alpha=alpha,
        clients=tuple(per_client),
        eligible_ids=tuple(eligible_ids),
        pending_ids=tuple(pending_ids),
        incomplete_ids=tuple(incomplete),
    )


def _make_client_record(
    client_id: str,
    fpr: float,
    tpr: float,
    n_benign: int = 100,
    n_attack: int = 100,
) -> ClientEvaluationRecord:
    tnr = 1.0 - fpr
    fnr = 1.0 - tpr
    ba = (tpr + tnr) / 2.0
    tp = int(tpr * n_attack)
    fp = int(fpr * n_benign)
    tn = int(tnr * n_benign)
    fn = int(fnr * n_attack)
    prec = tp / (tp + fp) if (tp + fp) > 0 else math.nan
    rec = tp / (tp + fn) if (tp + fn) > 0 else math.nan
    # Compute macro_f1 consistent with recompute_binary_metrics
    if n_benign > 0 and n_attack > 0:
        prec0 = tn / (tn + fn) if (tn + fn) > 0 else 0.0
        rec0 = tnr
        f1_0 = 2 * prec0 * rec0 / (prec0 + rec0) if (prec0 + rec0) > 0 else 0.0
        prec1 = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec1 = tpr
        f1_1 = 2 * prec1 * rec1 / (prec1 + rec1) if (prec1 + rec1) > 0 else 0.0
        macro_f1 = (f1_0 + f1_1) / 2.0
    else:
        macro_f1 = math.nan
    return ClientEvaluationRecord(
        client_id=client_id,
        metrics=BinaryMetrics(
            fpr=fpr,
            tpr=tpr,
            tnr=tnr,
            fnr=fnr,
            balanced_accuracy=ba,
            precision=prec,
            recall=rec,
            macro_f1=macro_f1,
        ),
        confusion=ConfusionCounts(tp=tp, fp=fp, tn=tn, fn=fn),
        n_benign=n_benign,
        n_attack=n_attack,
        threshold=ClientThreshold(
            client_id=client_id,
            threshold=0.5,
            calibration_pending=False,
            strategy=Baseline.B1,
        ),
        evaluation_incomplete=(n_attack == 0),
    )


def test_compute_client_metrics_perfect_separation():
    benign = np.array([0.1, 0.2, 0.3, 0.5, 0.9])
    attack = np.array([2.1, 2.5, 3.0, 4.0])
    ct = ClientThreshold(
        client_id="test", threshold=1.5, calibration_pending=False, strategy=Baseline.B1
    )
    result = compute_client_record("test", benign, attack, ct)

    assert result.metrics.fpr == pytest.approx(0.0)
    assert result.metrics.tpr == pytest.approx(1.0)
    assert result.metrics.balanced_accuracy == pytest.approx(1.0)
    assert result.confusion.fp == 0
    assert result.confusion.tp == 4
    assert result.confusion.tn == 5
    assert result.confusion.fn == 0
    assert result.n_benign == 5
    assert result.n_attack == 4


def test_threshold_rule_strictly_greater_than():
    benign = np.array([1.5, 0.5])  # 1.5 == threshold: should be TN
    attack = np.array([1.5, 2.0])  # 1.5 == threshold: should be FN; 2.0: TP
    ct = ClientThreshold(
        client_id="test", threshold=1.5, calibration_pending=False, strategy=Baseline.B1
    )
    result = compute_client_record("test", benign, attack, ct)
    # 1.5 > 1.5 is False → both 1.5 values are not anomalous
    assert result.confusion.tn == 2  # both benign are TN
    assert result.confusion.fn == 1  # benign-score attack is FN
    assert result.confusion.tp == 1  # 2.0 > 1.5


def test_compute_client_metrics_all_false_positives():
    benign = np.array([0.1, 0.5, 1.0, 2.0])
    attack = np.array([3.0, 4.0])
    ct = ClientThreshold(
        client_id="test", threshold=0.0, calibration_pending=False, strategy=Baseline.B1
    )
    result = compute_client_record("test", benign, attack, ct)

    assert result.metrics.fpr == pytest.approx(1.0)
    assert result.metrics.tpr == pytest.approx(1.0)
    assert result.confusion.fp == 4
    assert result.confusion.tn == 0


def test_benign_only_client_produces_fpr_and_nan_attack_metrics():
    benign = np.array([0.1, 0.5, 0.9])
    attack = np.array([], dtype=np.float64)
    ct = ClientThreshold(
        client_id="test", threshold=0.7, calibration_pending=False, strategy=Baseline.B1
    )
    result = compute_client_record("test", benign, attack, ct)

    assert not math.isnan(result.metrics.fpr)
    assert math.isnan(result.metrics.tpr)
    assert math.isnan(result.metrics.balanced_accuracy)
    assert math.isnan(result.metrics.macro_f1)
    assert result.n_benign == 3
    assert result.n_attack == 0


def test_macro_f1_matches_sklearn_zero_division_behavior():
    # All benign predicted positive (fp=4), all attacks missed (fn=3)
    benign = np.array([2.0, 3.0, 4.0, 5.0])
    attack = np.array([0.1, 0.2, 0.3])
    ct = ClientThreshold(
        client_id="test", threshold=1.5, calibration_pending=False, strategy=Baseline.B1
    )
    result = compute_client_record("test", benign, attack, ct)
    # All benign > 1.5 → fp=4, tn=0; all attack < 1.5 → fn=3, tp=0
    assert result.confusion.fp == 4
    assert result.confusion.tn == 0
    assert result.confusion.tp == 0
    assert result.confusion.fn == 3
    assert result.metrics.macro_f1 == pytest.approx(0.0)


def test_cv_fpr_eligible_only():
    c1 = _make_client_record("c1", fpr=0.10, tpr=0.90)
    c2 = _make_client_record("c2", fpr=0.15, tpr=0.85)
    c3 = _make_client_record("c3", fpr=0.20, tpr=0.80)
    c4_pending = _make_client_record("c4", fpr=0.50, tpr=0.60)

    ev = _make_eval_result(
        per_client=[c1, c2, c3, c4_pending],
        eligible_ids=["c1", "c2", "c3"],
        pending_ids=["c4"],
    )

    expected_fpr_arr = np.array([0.10, 0.15, 0.20])
    expected_cv = cv(expected_fpr_arr, ddof=1)

    assert abs(ev.cv_fpr - expected_cv) < 1e-12
    fpr_with_pending = np.array([0.10, 0.15, 0.20, 0.50])
    cv_with_pending = cv(fpr_with_pending, ddof=1)
    assert abs(ev.cv_fpr - cv_with_pending) > 0.01


def test_coverage_ratio():
    clients = [_make_client_record(f"c{i}", fpr=0.1, tpr=0.9) for i in range(4)]
    ev = _make_eval_result(
        per_client=clients,
        eligible_ids=["c0", "c1", "c2"],
        pending_ids=["c3"],
    )
    assert ev.coverage_ratio == pytest.approx(0.75)


def test_confusion_matrix_saved_before_averaging(tmp_path):
    c1 = _make_client_record("c1", fpr=0.1, tpr=0.9)
    c2 = _make_client_record("c2", fpr=0.2, tpr=0.8)

    ev = _make_eval_result(
        per_client=[c1, c2],
        eligible_ids=["c1", "c2"],
        pending_ids=[],
    )

    out = save_confusion_matrices(ev, tmp_path)
    assert out.exists()

    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["per_client"]) == 2
    for entry in data["per_client"]:
        assert "confusion_matrix" in entry
        cm = entry["confusion_matrix"]
        assert all(k in cm for k in ("tp", "fp", "tn", "fn"))


def test_confusion_matrix_write_is_atomic(tmp_path):
    c1 = _make_client_record("c1", fpr=0.1, tpr=0.9)
    ev = _make_eval_result(per_client=[c1], eligible_ids=["c1"], pending_ids=[])
    out = save_confusion_matrices(ev, tmp_path)
    # No .tmp.json file should remain
    tmp_files = list(out.parent.glob("*.tmp.json"))
    assert len(tmp_files) == 0


def test_regime_c_confusion_includes_alpha(tmp_path):
    c1 = _make_client_record("c1", fpr=0.1, tpr=0.9)
    ev = _make_eval_result(
        per_client=[c1],
        eligible_ids=["c1"],
        pending_ids=[],
        regime=Regime.C,
        alpha=0.5,
    )

    out = save_confusion_matrices(ev, tmp_path)
    assert "alpha0.5" in out.name

    ev_no_alpha = _make_eval_result(
        per_client=[c1],
        eligible_ids=["c1"],
        pending_ids=[],
        regime=Regime.A,
        alpha=None,
    )
    out_no_alpha = save_confusion_matrices(ev_no_alpha, tmp_path)
    assert "alpha" not in out_no_alpha.name


def test_eval_incomplete_excluded_from_attack_metrics():
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
            calibration_pending=False,
            strategy=Baseline.B1,
        ),
        evaluation_incomplete=True,
    )

    fm = _filter_eligible_metrics(
        clients=[c1, c2, c3_noattack],
        eligible_ids=["c1", "c2", "c3"],
        incomplete_ids=["c3"],
    )

    assert fm.fpr_eligible.shape[0] == 3  # FPR includes all 3 eligible
    assert fm.tpr_eligible.shape[0] == 2  # attack metrics exclude c3
    assert fm.ba_eligible.shape[0] == 2
    assert fm.f1_eligible.shape[0] == 2


def test_filter_eligible_metrics_excludes_pending():
    c_elig = _make_client_record("e1", fpr=0.1, tpr=0.9)
    c_pend = _make_client_record("p1", fpr=0.5, tpr=0.6)

    fm = _filter_eligible_metrics(
        clients=[c_elig, c_pend],
        eligible_ids=["e1"],
        incomplete_ids=None,
    )

    assert fm.fpr_eligible.shape[0] == 1
    assert fm.tpr_eligible.shape[0] == 1
    assert float(fm.fpr_eligible[0]) == pytest.approx(0.1)


def test_attack_empty_valid_artifact_is_eval_incomplete():
    benign = np.array([0.5, 0.6, 0.7])
    attack = np.array([], dtype=np.float64)
    ct = ClientThreshold(
        client_id="test", threshold=0.8, calibration_pending=False, strategy=Baseline.B1
    )
    result = compute_client_record("test", benign, attack, ct)
    assert result.n_attack == 0
    assert math.isnan(result.metrics.tpr)
    assert math.isnan(result.metrics.balanced_accuracy)
    assert math.isnan(result.metrics.macro_f1)
    # FPR still defined
    assert not math.isnan(result.metrics.fpr)


def test_evaluate_baseline_rejects_empty_thresholds():
    from datp.evaluation.metrics import evaluate_baseline

    with pytest.raises(ValueError, match="empty"):
        evaluate_baseline(
            [], Path("/nonexistent"), Regime.A, 0, None, score_provider=None
        )


def test_evaluate_baseline_rejects_duplicate_client_ids():
    from datp.core.enums import Baseline
    from datp.core.types import ClientThreshold
    from datp.evaluation.metrics import evaluate_baseline

    ct = ClientThreshold(
        client_id="c1", threshold=0.5, calibration_pending=False, strategy=Baseline.B1
    )
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        evaluate_baseline(
            [ct, ct], Path("/nonexistent"), Regime.A, 0, None, score_provider=None
        )


def test_evaluate_baseline_rejects_mixed_strategies():
    from datp.core.enums import Baseline
    from datp.core.types import ClientThreshold
    from datp.evaluation.metrics import evaluate_baseline

    ct1 = ClientThreshold(
        client_id="c1", threshold=0.5, calibration_pending=False, strategy=Baseline.B1
    )
    ct2 = ClientThreshold(
        client_id="c2", threshold=0.6, calibration_pending=False, strategy=Baseline.B2
    )
    with pytest.raises(ValueError, match="[Mm]ixed"):
        evaluate_baseline(
            [ct1, ct2], Path("/nonexistent"), Regime.A, 0, None, score_provider=None
        )


def test_evaluate_baseline_rejects_missing_preloaded_client():
    import tempfile

    from datp.core.enums import Baseline
    from datp.core.types import ClientThreshold
    from datp.evaluation.metrics import evaluate_baseline
    from datp.scoring.loading import ScoreProvider

    ct = ClientThreshold(
        client_id="c1", threshold=0.5, calibration_pending=False, strategy=Baseline.B1
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = ScoreProvider(Path(tmpdir))
        # c1 score files are absent — expect FileNotFoundError from ScoreProvider
        with pytest.raises(FileNotFoundError):
            evaluate_baseline(
                [ct], Path(tmpdir), Regime.A, 0, None, score_provider=provider
            )


def test_evaluate_baseline_accepts_score_provider_and_marks_eval_incomplete(
    tmp_path: Path,
) -> None:
    from datp.core.enums import Baseline
    from datp.core.types import ClientThreshold
    from datp.evaluation.metrics import evaluate_baseline
    from datp.scoring.loading import ScoreProvider

    _write_score_artifact(
        tmp_path / ScoringStage.TEST_BENIGN / "c1.parquet", [0.1, 0.2]
    )
    _write_score_artifact(tmp_path / ScoringStage.TEST_ATTACK / "c1.parquet", [])

    result = evaluate_baseline(
        [
            ClientThreshold(
                client_id="c1",
                threshold=0.15,
                calibration_pending=False,
                strategy=Baseline.B1,
            )
        ],
        tmp_path,
        Regime.A,
        0,
        None,
        score_provider=ScoreProvider(tmp_path),
    )

    assert result.eval_incomplete_ids == ("c1",)
    assert result.regime == Regime.A
    assert result.baseline == Baseline.B1


def test_evaluate_baseline_serializes_enum_inputs_as_values(tmp_path: Path) -> None:
    from datp.core.enums import Baseline
    from datp.core.types import ClientThreshold
    from datp.evaluation.metrics import evaluate_baseline

    _write_score_artifact(
        tmp_path / ScoringStage.TEST_BENIGN / "c1.parquet", [0.1, 0.2]
    )
    _write_score_artifact(tmp_path / ScoringStage.TEST_ATTACK / "c1.parquet", [0.3])

    result = evaluate_baseline(
        [
            ClientThreshold(
                client_id="c1",
                threshold=0.15,
                calibration_pending=False,
                strategy=Baseline.B1,
            )
        ],
        tmp_path,
        Regime.A,
        7,
        None,
        score_provider=None,
    )

    payload = dataclasses.asdict(result)
    assert payload["run"]["cell"]["regime"] == Regime.A
    assert payload["run"]["baseline"] == Baseline.B1


def test_evaluation_result_asdict():
    c1 = _make_client_record("c1", fpr=0.1, tpr=0.9)
    ev = _make_eval_result(per_client=[c1], eligible_ids=["c1"], pending_ids=[])
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


def test_metrics_serialization_contains_eligibility_threshold_and_provenance_fields():
    c1 = _make_client_record("c1", fpr=0.1, tpr=0.9)
    c2_base = _make_client_record("c2", fpr=0.2, tpr=0.8)
    # Make c2 calibration-pending by replacing its threshold
    c2 = ClientEvaluationRecord(
        client_id=c2_base.client_id,
        metrics=c2_base.metrics,
        confusion=c2_base.confusion,
        n_benign=c2_base.n_benign,
        n_attack=c2_base.n_attack,
        threshold=ClientThreshold(
            client_id="c2",
            threshold=0.5,
            calibration_pending=True,
            strategy=Baseline.B1,
        ),
        evaluation_incomplete=c2_base.evaluation_incomplete,
    )
    ev = build_evaluation_result(
        baseline=Baseline.B1,
        regime=Regime.A,
        seed=0,
        alpha=None,
        clients=(c1, c2),
        eligible_ids=("c1",),
        pending_ids=("c2",),
        incomplete_ids=(),
    )
    metrics = build_metrics_dict(
        ev,
        ThresholdResult(
            run=BaselineRunId(
                cell=TrainingCellId(regime=Regime.A, seed=0, alpha=None),
                baseline=Baseline.B1,
            ),
            tau_global=0.5,
            client_thresholds=(
                ClientThreshold(
                    client_id="c1",
                    threshold=0.5,
                    calibration_pending=False,
                    strategy=Baseline.B1,
                ),
                ClientThreshold(
                    client_id="c2",
                    threshold=0.5,
                    calibration_pending=True,
                    strategy=Baseline.B1,
                ),
            ),
            metadata=ThresholdMetadata(b3=None, b4=None),
        ),
        config_identity="test",
        split_manifest_identity="test",
        model_checkpoint_identity="test",
        score_artifact_identity="test",
        checkpoint_round=None,
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


def test_client_record_asdict():
    cr = _make_client_record("c1", fpr=0.05, tpr=0.95)
    d = dataclasses.asdict(cr)
    assert d["client_id"] == "c1"
    assert "confusion" in d
    assert set(d["confusion"].keys()) == {"tp", "fp", "tn", "fn"}


def test_single_cv_implementation():
    result = subprocess.run(
        ["grep", "-rn", r"def cv(", "src/datp/"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[3],  # repo root
    )
    lines = [line for line in result.stdout.strip().splitlines() if line.strip()]
    assert len(lines) == 1, f"Expected 1 'def cv(' match, got {len(lines)}: {lines}"
    assert "statistics/cv.py" in lines[0]


# Per-attack TPR


class TestPerAttackTPR:
    def setup_method(self) -> None:
        from datp.evaluation.metrics import compute_per_attack_tpr

        self._fn = compute_per_attack_tpr

    def _family(self, label: str) -> str | None:
        return {"DDoS_TCP": "DDoS", "Mirai_Bot": "Mirai"}.get(label)

    def test_correct_tpr_per_label(self) -> None:
        scores = np.array([0.1, 0.2, 0.9, 0.8, 0.05, 0.7], dtype=float)
        labels = np.array(
            ["DDoS_TCP", "DDoS_TCP", "DDoS_TCP", "Mirai_Bot", "Mirai_Bot", "Mirai_Bot"]
        )
        threshold = 0.5
        results = self._fn("c1", scores, labels, threshold, self._family)
        by_label = {r.attack_label: r for r in results}
        # DDoS_TCP: 1 of 3 > 0.5
        assert by_label["DDoS_TCP"].detected_count == 1
        assert by_label["DDoS_TCP"].denominator == 3
        assert by_label["DDoS_TCP"].tpr == pytest.approx(1 / 3)
        # Mirai_Bot: 2 of 3 > 0.5
        assert by_label["Mirai_Bot"].detected_count == 2
        assert by_label["Mirai_Bot"].denominator == 3
        assert by_label["Mirai_Bot"].tpr == pytest.approx(2 / 3)

    def test_family_set_correctly(self) -> None:
        scores = np.array([0.9], dtype=float)
        labels = np.array(["DDoS_TCP"])
        results = self._fn("c1", scores, labels, 0.5, self._family)
        assert results[0].family == "DDoS"

    def test_unknown_label_family_is_none(self) -> None:
        scores = np.array([0.9], dtype=float)
        labels = np.array(["UNKNOWN_XYZ"])
        results = self._fn("c1", scores, labels, 0.5, self._family)
        assert results[0].family is None

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="mismatch"):
            self._fn(
                "c1", np.array([0.1, 0.2]), np.array(["DDoS_TCP"]), 0.5, self._family
            )

    def test_empty_inputs_return_empty_list(self) -> None:
        results = self._fn("c1", np.array([]), np.array([]), 0.5, self._family)
        assert results == []

    def test_client_id_propagated(self) -> None:
        scores = np.array([0.9], dtype=float)
        labels = np.array(["DDoS_TCP"])
        results = self._fn("my_client", scores, labels, 0.5, self._family)
        assert results[0].client_id == "my_client"


class TestRecomputeBinaryMetrics:
    def setup_method(self) -> None:
        from datp.evaluation.metrics import recompute_binary_metrics

        self._fn = recompute_binary_metrics

    def test_matches_compute_client_record(self) -> None:
        benign = np.array([0.1, 0.2, 0.7], dtype=float)
        attack = np.array([0.8, 0.9, 0.95], dtype=float)
        threshold = 0.5
        ct = ClientThreshold(
            client_id="c",
            threshold=threshold,
            calibration_pending=False,
            strategy=Baseline.B1,
        )
        cr = compute_client_record("c", benign, attack, ct)
        tp = cr.confusion.tp
        fp = cr.confusion.fp
        tn = cr.confusion.tn
        fn = cr.confusion.fn
        bm = self._fn(tp, fp, tn, fn)
        assert bm.fpr == pytest.approx(cr.metrics.fpr)
        assert bm.tpr == pytest.approx(cr.metrics.tpr)
        assert bm.balanced_accuracy == pytest.approx(cr.metrics.balanced_accuracy)
        assert bm.macro_f1 == pytest.approx(cr.metrics.macro_f1)

    def test_zero_attack_returns_nan_for_attack_metrics(self) -> None:
        bm = self._fn(tp=0, fp=2, tn=8, fn=0)
        assert not math.isnan(bm.fpr)
        assert math.isnan(bm.tpr)
        assert math.isnan(bm.balanced_accuracy)
        assert math.isnan(bm.macro_f1)

    def test_zero_benign_returns_nan_fpr(self) -> None:
        bm = self._fn(tp=3, fp=0, tn=0, fn=1)
        assert math.isnan(bm.fpr)
        assert not math.isnan(bm.tpr)

    def test_perfect_classifier(self) -> None:
        bm = self._fn(tp=10, fp=0, tn=10, fn=0)
        assert bm.fpr == pytest.approx(0.0)
        assert bm.tpr == pytest.approx(1.0)
        assert bm.balanced_accuracy == pytest.approx(1.0)
        assert bm.macro_f1 == pytest.approx(1.0)

    def test_worst_classifier(self) -> None:
        bm = self._fn(tp=0, fp=10, tn=0, fn=10)
        assert bm.fpr == pytest.approx(1.0)
        assert bm.tpr == pytest.approx(0.0)
        assert bm.balanced_accuracy == pytest.approx(0.0)
        assert bm.macro_f1 == pytest.approx(0.0)

    def test_denominator_check_fp_plus_tn_equals_n_benign(self) -> None:
        bm = self._fn(tp=5, fp=3, tn=7, fn=2)
        assert (3 + 7) == 10
        assert bm.fpr == pytest.approx(3 / 10)

    def test_denominator_check_tp_plus_fn_equals_n_attack(self) -> None:
        bm = self._fn(tp=5, fp=3, tn=7, fn=2)
        assert (5 + 2) == 7
        assert bm.tpr == pytest.approx(5 / 7)


# Companion metrics bundle


def test_fpr_bundle_includes_mean_std_worst():
    c1 = _make_client_record("c1", fpr=0.10, tpr=0.90)
    c2 = _make_client_record("c2", fpr=0.20, tpr=0.80)
    c3 = _make_client_record("c3", fpr=0.30, tpr=0.70)

    ev = _make_eval_result(
        per_client=[c1, c2, c3],
        eligible_ids=["c1", "c2", "c3"],
        pending_ids=[],
    )

    assert ev.mean_fpr == pytest.approx(0.20, abs=1e-10)
    assert ev.std_fpr == pytest.approx(np.std([0.10, 0.20, 0.30], ddof=1), abs=1e-10)
    assert ev.worst_client_fpr == pytest.approx(0.30, abs=1e-10)
    assert ev.worst_client_id == "c3"
    assert ev.eligible_count == 3
    assert ev.client_count == 3


def test_bundle_excludes_pending_from_fpr_stats():
    c1 = _make_client_record("c1", fpr=0.10, tpr=0.90)
    c2 = _make_client_record("c2", fpr=0.20, tpr=0.80)
    c_pending = _make_client_record("cp", fpr=0.99, tpr=0.50)

    ev = _make_eval_result(
        per_client=[c1, c2, c_pending],
        eligible_ids=["c1", "c2"],
        pending_ids=["cp"],
    )

    assert ev.mean_fpr == pytest.approx(0.15, abs=1e-10)
    assert ev.worst_client_fpr == pytest.approx(0.20, abs=1e-10)
    assert ev.worst_client_id == "c2"
    assert ev.eligible_count == 2
    assert ev.client_count == 3


def test_bundle_single_eligible_std_is_nan():
    c1 = _make_client_record("c1", fpr=0.10, tpr=0.90)
    ev = _make_eval_result(
        per_client=[c1],
        eligible_ids=["c1"],
        pending_ids=[],
    )
    assert math.isnan(ev.std_fpr)
    assert ev.mean_fpr == pytest.approx(0.10, abs=1e-10)


def test_bundle_no_eligible_all_nan():
    c_pending = _make_client_record("cp", fpr=0.5, tpr=0.5)
    ev = _make_eval_result(
        per_client=[c_pending],
        eligible_ids=[],
        pending_ids=["cp"],
    )
    assert math.isnan(ev.cv_fpr)
    assert math.isnan(ev.mean_fpr)
    assert math.isnan(ev.std_fpr)
    assert math.isnan(ev.worst_client_fpr)
    assert ev.worst_client_id is None
    assert ev.eligible_count == 0
    assert ev.client_count == 1


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
            calibration_pending=False,
            strategy=Baseline.B1,
        ),
        evaluation_incomplete=False,
    )

    with pytest.raises(ValueError, match="Undefined eligible-client FPR"):
        build_evaluation_result(
            baseline=Baseline.B1,
            regime=Regime.A,
            seed=0,
            alpha=None,
            clients=(client,),
            eligible_ids=("attack_only",),
            pending_ids=(),
            incomplete_ids=(),
        )


def test_build_evaluation_result_rejects_mixed_eligibility_status() -> None:
    client = _make_client_record("c1", fpr=0.1, tpr=0.9)

    with pytest.raises(ValueError, match="mixed eligibility"):
        build_evaluation_result(
            baseline=Baseline.B1,
            regime=Regime.A,
            seed=0,
            alpha=None,
            clients=(client,),
            eligible_ids=("c1",),
            pending_ids=("c1",),
            incomplete_ids=(),
        )
