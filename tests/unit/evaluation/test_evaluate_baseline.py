from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import tempfile
from pathlib import Path

import pytest

from datp.config.stages import ExperimentStage
from datp.core.enums import ScoringStage
from datp.core.types import ClientThreshold
from datp.evaluation.metrics import evaluate_policy_run
from datp.scoring.loading import ScoreProvider
from tests.unit.conftest import _write_score_artifact

_STAGE = ExperimentStage.NBAIOT_MAIN


def _ct(
    client_id: str, strategy: ThresholdPolicy = ThresholdPolicy.GLOBAL_THRESHOLD, threshold: float = 0.5
) -> ClientThreshold:
    return ClientThreshold(
        client_id=client_id,
        threshold=threshold,
        calibration_pending=False,
        strategy=strategy,
    )


def test_evaluate_policy_run_rejects_empty_thresholds() -> None:
    with pytest.raises(ValueError, match="empty"):
        evaluate_policy_run(
            [], Path("/nonexistent"), _STAGE, 0, score_provider=None
        )


def test_evaluate_policy_run_rejects_duplicate_client_ids() -> None:
    ct = _ct("c1")
    with pytest.raises(ValueError, match="[Dd]uplicate"):
        evaluate_policy_run(
            [ct, ct], Path("/nonexistent"), _STAGE, 0, score_provider=None
        )


def test_evaluate_policy_run_rejects_mixed_strategies() -> None:
    ct1 = _ct("c1", strategy=ThresholdPolicy.GLOBAL_THRESHOLD)
    ct2 = _ct("c2", strategy=ThresholdPolicy.LOCAL_THRESHOLD)
    with pytest.raises(ValueError, match="[Mm]ixed"):
        evaluate_policy_run(
            [ct1, ct2], Path("/nonexistent"), _STAGE, 0, score_provider=None
        )


def test_evaluate_policy_run_rejects_missing_preloaded_client() -> None:
    ct = _ct("c1")
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = ScoreProvider(Path(tmpdir))
        with pytest.raises(FileNotFoundError):
            evaluate_policy_run(
                [ct], Path(tmpdir), _STAGE, 0, score_provider=provider
            )


def test_evaluate_policy_run_accepts_score_provider_and_marks_eval_incomplete(
    tmp_path: Path,
) -> None:
    _write_score_artifact(
        tmp_path / ScoringStage.TEST_BENIGN / "c1.parquet", [0.1, 0.2]
    )
    _write_score_artifact(tmp_path / ScoringStage.TEST_ATTACK / "c1.parquet", [])

    result = evaluate_policy_run(
        [_ct("c1", threshold=0.15)],
        tmp_path,
        _STAGE,
        0,
        score_provider=ScoreProvider(tmp_path),
    )

    assert result.eval_incomplete_ids == ("c1",)
    assert result.stage == _STAGE
    assert result.policy == ThresholdPolicy.GLOBAL_THRESHOLD


def test_attack_empty_valid_artifact_is_eval_incomplete() -> None:
    import math

    import numpy as np

    from datp.evaluation.metrics import compute_client_record

    benign = np.array([0.5, 0.6, 0.7])
    attack = np.array([], dtype=np.float64)
    ct = ClientThreshold(
        client_id="test", threshold=0.8, calibration_pending=False, strategy=ThresholdPolicy.GLOBAL_THRESHOLD
    )
    result = compute_client_record("test", benign, attack, ct)
    assert result.n_attack == 0
    assert math.isnan(result.metrics.tpr)
    assert math.isnan(result.metrics.balanced_accuracy)
    assert math.isnan(result.metrics.macro_f1)
    assert not math.isnan(result.metrics.fpr)
