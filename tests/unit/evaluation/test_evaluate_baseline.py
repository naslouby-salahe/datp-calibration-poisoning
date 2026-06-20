from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from datp.core.enums import Baseline, Regime, ScoringStage
from datp.core.types import ClientThreshold
from datp.evaluation.metrics import evaluate_baseline
from datp.scoring.loading import ScoreProvider
from tests.unit.conftest import _write_score_artifact


def _ct(
    client_id: str, strategy: Baseline = Baseline.B1, threshold: float = 0.5
) -> ClientThreshold:
    return ClientThreshold(
        client_id=client_id,
        threshold=threshold,
        calibration_pending=False,
        strategy=strategy,
    )


def test_evaluate_baseline_rejects_empty_thresholds() -> None:
    with pytest.raises(ValueError, match="empty"):
        evaluate_baseline(
            [], Path("/nonexistent"), Regime.A, 0, None, score_provider=None
        )


def test_evaluate_baseline_rejects_duplicate_client_ids() -> None:
    ct = _ct("c1")
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        evaluate_baseline(
            [ct, ct], Path("/nonexistent"), Regime.A, 0, None, score_provider=None
        )


def test_evaluate_baseline_rejects_mixed_strategies() -> None:
    ct1 = _ct("c1", strategy=Baseline.B1)
    ct2 = _ct("c2", strategy=Baseline.B2)
    with pytest.raises(ValueError, match="[Mm]ixed"):
        evaluate_baseline(
            [ct1, ct2], Path("/nonexistent"), Regime.A, 0, None, score_provider=None
        )


def test_evaluate_baseline_rejects_missing_preloaded_client() -> None:
    ct = _ct("c1")
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = ScoreProvider(Path(tmpdir))
        with pytest.raises(FileNotFoundError):
            evaluate_baseline(
                [ct], Path(tmpdir), Regime.A, 0, None, score_provider=provider
            )


def test_evaluate_baseline_accepts_score_provider_and_marks_eval_incomplete(
    tmp_path: Path,
) -> None:
    _write_score_artifact(
        tmp_path / ScoringStage.TEST_BENIGN / "c1.parquet", [0.1, 0.2]
    )
    _write_score_artifact(tmp_path / ScoringStage.TEST_ATTACK / "c1.parquet", [])

    result = evaluate_baseline(
        [_ct("c1", threshold=0.15)],
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
    import dataclasses

    _write_score_artifact(
        tmp_path / ScoringStage.TEST_BENIGN / "c1.parquet", [0.1, 0.2]
    )
    _write_score_artifact(tmp_path / ScoringStage.TEST_ATTACK / "c1.parquet", [0.3])

    result = evaluate_baseline(
        [_ct("c1", threshold=0.15)],
        tmp_path,
        Regime.A,
        7,
        None,
        score_provider=None,
    )

    payload = dataclasses.asdict(result)
    assert payload["run"]["cell"]["regime"] == Regime.A
    assert payload["run"]["baseline"] == Baseline.B1


def test_attack_empty_valid_artifact_is_eval_incomplete() -> None:
    import math

    import numpy as np

    from datp.evaluation.metrics import compute_client_record

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
    assert not math.isnan(result.metrics.fpr)
