from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

from datp.config.stages import ExperimentStage
from datp.core.enums import ScoringStage
from datp.validation.enums import AuditStatus
from datp.validation.invariants import (
    InvariantHashes,
    InvariantKey,
    build_invariant_results,
)

_CELL_A = InvariantKey(stage=ExperimentStage.NBAIOT_MAIN, seed=0)
_CELL_B = InvariantKey(stage=ExperimentStage.SYNTHETIC_SMOKE, seed=0)
_CELL_C = InvariantKey(stage=ExperimentStage.NBAIOT_FULL_OPTIONAL, seed=0)

_HASH_MAP_REF: dict[tuple[ScoringStage, str], str] = {
    (ScoringStage.CAL, "client_1"): "aaa",
    (ScoringStage.TEST_BENIGN, "client_1"): "bbb",
    (ScoringStage.TEST_ATTACK, "client_1"): "ccc",
}
_HASH_MAP_ALT: dict[tuple[ScoringStage, str], str] = {
    (ScoringStage.CAL, "client_1"): "aaa",
    (ScoringStage.TEST_BENIGN, "client_1"): "bbb",
    (ScoringStage.TEST_ATTACK, "client_1"): "XXX",
}


def _inputs(
    cell: InvariantKey,
    baselines: list[ThresholdPolicy],
    split: str = "split1",
    model: str = "model1",
    scoring: str = "score1",
    metrics: str = "metrics1",
) -> dict[InvariantKey, dict[ThresholdPolicy, InvariantHashes]]:
    return {
        cell: {
            b: InvariantHashes(
                split_hash=split,
                model_hash=model,
                encoder_hash=model,
                scoring_code_hash=scoring,
                metrics_code_hash=metrics,
            )
            for b in baselines
        }
    }


def _score_hashes(
    cell: InvariantKey,
    baselines: list[ThresholdPolicy],
    hash_map: dict[tuple[ScoringStage, str], str] | None = None,
) -> dict[InvariantKey, dict[ThresholdPolicy, dict[tuple[ScoringStage, str], str]]]:
    if hash_map is None:
        hash_map = _HASH_MAP_REF
    return {cell: {b: dict(hash_map) for b in baselines}}


class TestInvariantPass:
    def test_all_controlled_policies_pass_nbaiot_main(self) -> None:
        baselines = [
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ]
        results = build_invariant_results(
            _inputs(_CELL_A, baselines),
            _score_hashes(_CELL_A, baselines),
        )
        assert len(results) == 1
        assert results[0].status == AuditStatus.PASS
        assert results[0].split_hash_shared is True
        assert results[0].model_or_encoder_hash_shared is True
        assert results[0].reconstruction_error_hashes_shared is True
        assert results[0].scoring_code_hash_shared is True
        assert results[0].metrics_code_hash_shared is True
        assert results[0].disallowed_differences == []

    def test_synthetic_smoke_controlled_policies_pass(self) -> None:
        baselines = [
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ]
        results = build_invariant_results(
            _inputs(_CELL_B, baselines),
            _score_hashes(_CELL_B, baselines),
        )
        assert results[0].status == AuditStatus.PASS

    def test_nbaiot_full_controlled_policies_pass(self) -> None:
        baselines = [
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ]
        results = build_invariant_results(
            _inputs(_CELL_C, baselines),
            _score_hashes(_CELL_C, baselines),
        )
        assert results[0].status == AuditStatus.PASS


class TestInvariantFail:
    def test_model_hash_differs_marks_fail(self) -> None:
        baselines = [
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ]
        inv_inputs: dict[InvariantKey, dict[ThresholdPolicy, InvariantHashes]] = {
            _CELL_A: {
                ThresholdPolicy.GLOBAL_THRESHOLD: InvariantHashes(
                    split_hash="s1",
                    model_hash="model_A",
                    encoder_hash="model_A",
                    scoring_code_hash="sc",
                    metrics_code_hash="mc",
                ),
                ThresholdPolicy.LOCAL_THRESHOLD: InvariantHashes(
                    split_hash="s1",
                    model_hash="model_B",
                    encoder_hash="model_B",
                    scoring_code_hash="sc",
                    metrics_code_hash="mc",
                ),
                ThresholdPolicy.CLUSTER_THRESHOLD: InvariantHashes(
                    split_hash="s1",
                    model_hash="model_A",
                    encoder_hash="model_A",
                    scoring_code_hash="sc",
                    metrics_code_hash="mc",
                ),
            }
        }
        results = build_invariant_results(
            inv_inputs,
            _score_hashes(_CELL_A, baselines),
        )
        assert results[0].status == AuditStatus.FAIL
        assert "model_hash_or_encoder_hash" in results[0].disallowed_differences
        assert results[0].model_or_encoder_hash_shared is False

    def test_score_array_hash_differs_marks_fail(self) -> None:
        baselines = [
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ]
        score_hashes: dict[
            InvariantKey, dict[ThresholdPolicy, dict[tuple[ScoringStage, str], str]]
        ] = {
            _CELL_B: {
                ThresholdPolicy.GLOBAL_THRESHOLD: dict(_HASH_MAP_REF),
                ThresholdPolicy.LOCAL_THRESHOLD: dict(_HASH_MAP_ALT),
                ThresholdPolicy.CLUSTER_THRESHOLD: dict(_HASH_MAP_REF),
            }
        }
        results = build_invariant_results(
            _inputs(_CELL_B, baselines),
            score_hashes,
        )
        assert results[0].status == AuditStatus.FAIL
        assert results[0].reconstruction_error_hashes_shared is False
        assert "reconstruction_error_arrays" in results[0].disallowed_differences

    def test_split_hash_differs_marks_fail(self) -> None:
        inv_inputs: dict[InvariantKey, dict[ThresholdPolicy, InvariantHashes]] = {
            _CELL_A: {
                ThresholdPolicy.GLOBAL_THRESHOLD: InvariantHashes(
                    split_hash="s1",
                    model_hash="m1",
                    encoder_hash="m1",
                    scoring_code_hash="sc",
                    metrics_code_hash="mc",
                ),
                ThresholdPolicy.LOCAL_THRESHOLD: InvariantHashes(
                    split_hash="s2",
                    model_hash="m1",
                    encoder_hash="m1",
                    scoring_code_hash="sc",
                    metrics_code_hash="mc",
                ),
                ThresholdPolicy.CLUSTER_THRESHOLD: InvariantHashes(
                    split_hash="s1",
                    model_hash="m1",
                    encoder_hash="m1",
                    scoring_code_hash="sc",
                    metrics_code_hash="mc",
                ),
            }
        }
        results = build_invariant_results(
            inv_inputs,
            _score_hashes(
                _CELL_A,
                [
                    ThresholdPolicy.GLOBAL_THRESHOLD,
                    ThresholdPolicy.LOCAL_THRESHOLD,
                    ThresholdPolicy.CLUSTER_THRESHOLD,
                ],
            ),
        )
        assert results[0].status == AuditStatus.FAIL
        assert "split_hash" in results[0].disallowed_differences


class TestInvariantBlocked:
    def test_missing_policies_marks_blocked(self) -> None:
        baselines = [ThresholdPolicy.GLOBAL_THRESHOLD, ThresholdPolicy.LOCAL_THRESHOLD]
        results = build_invariant_results(
            _inputs(_CELL_A, baselines),
            _score_hashes(_CELL_A, baselines),
        )
        assert results[0].status == AuditStatus.BLOCKED_PENDING_RUN
        assert ThresholdPolicy.CLUSTER_THRESHOLD in results[0].missing_policies

    def test_no_score_hashes_marks_blocked_not_fail(self) -> None:
        baselines = [
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ]
        results = build_invariant_results(
            _inputs(_CELL_A, baselines),
            {},
        )
        assert results[0].status == AuditStatus.BLOCKED_PENDING_RUN
        assert results[0].reconstruction_error_hashes_shared is False
