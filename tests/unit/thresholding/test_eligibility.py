"""Unit tests for datp.thresholding.eligibility — eligibility partition, client thresholds, tau_global, and ThresholdResult assembly."""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import numpy as np
import pytest

from datp.config.stages import ExperimentStage
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.types import (
    ClusterInfo,
    ClusterInfoTuple,
    ClusterMetadata,
    ClientFingerprint,
    ClientFingerprintTuple,
    ClientSilhouetteScore,
    ClientSilhouetteScoreTuple,
    ClientThreshold,
    ThresholdResult,
)
from datp.thresholding.eligibility import (
    build_threshold_result,
    compute_client_thresholds,
    compute_tau_global,
    identify_eligible,
)


def _run(policy: ThresholdPolicy = ThresholdPolicy.GLOBAL_THRESHOLD) -> PolicyRunId:
    return PolicyRunId(
        cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=0), policy=policy
    )


def _make_errors(n: int, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).exponential(scale=0.5, size=n).astype(np.float32)


@pytest.fixture()
def client_errors() -> dict[str, np.ndarray]:
    return {
        "client_a": _make_errors(200, seed=1),
        "client_b": _make_errors(150, seed=2),
        "client_c": _make_errors(300, seed=3),
        "client_d": _make_errors(50, seed=4),  # Calibration-Pending
    }


N_MIN = 100


# ── identify_eligible ──────────────────────────────────────────────


class TestIdentifyEligible:
    def test_partitions_correctly(self, client_errors: dict[str, np.ndarray]) -> None:
        eligible, pending = identify_eligible(client_errors, n_min=N_MIN)
        assert set(eligible) == {"client_a", "client_b", "client_c"}
        assert set(pending) == {"client_d"}

    def test_n_min_from_param(self, client_errors: dict[str, np.ndarray]) -> None:
        eligible, _ = identify_eligible(client_errors, n_min=500)
        assert "client_a" not in eligible
        assert "client_b" not in eligible

    def test_all_eligible(self, client_errors: dict[str, np.ndarray]) -> None:
        eligible, pending = identify_eligible(client_errors, n_min=1)
        assert len(eligible) == 4
        assert len(pending) == 0

    def test_all_pending(self, client_errors: dict[str, np.ndarray]) -> None:
        eligible, pending = identify_eligible(client_errors, n_min=1000)
        assert len(eligible) == 0
        assert len(pending) == 4

    def test_empty_input(self) -> None:
        eligible, pending = identify_eligible({}, n_min=100)
        assert eligible == []
        assert pending == []

    def test_exact_boundary(self) -> None:
        errors = {"a": _make_errors(100, seed=0)}
        eligible, pending = identify_eligible(errors, n_min=100)
        assert eligible == ["a"]
        assert pending == []


# ── compute_client_thresholds ───────────────────────────────────────


class TestComputeClientThresholds:
    def test_eligible_only(self, client_errors: dict[str, np.ndarray]) -> None:
        eligible, _ = identify_eligible(client_errors, n_min=N_MIN)
        taus = compute_client_thresholds(client_errors, eligible, q=0.95)
        assert "client_d" not in taus

    def test_matches_percentile(self, client_errors: dict[str, np.ndarray]) -> None:
        eligible, _ = identify_eligible(client_errors, n_min=N_MIN)
        taus = compute_client_thresholds(client_errors, eligible, q=0.95)
        for cid in eligible:
            expected = float(np.percentile(client_errors[cid], 95))
            assert taus[cid] == pytest.approx(expected)

    def test_empty_eligible_returns_empty(self) -> None:
        taus = compute_client_thresholds({}, [], q=0.95)
        assert taus == {}

    def test_returns_float_values(self, client_errors: dict[str, np.ndarray]) -> None:
        eligible, _ = identify_eligible(client_errors, n_min=N_MIN)
        taus = compute_client_thresholds(client_errors, eligible, q=0.95)
        for v in taus.values():
            assert isinstance(v, float)


# ── compute_tau_global ──────────────────────────────────────────────


class TestComputeTauGlobal:
    def test_simple_mean(self) -> None:
        taus = {"a": 0.1, "b": 0.9}
        tau_g = compute_tau_global(taus)
        assert tau_g == pytest.approx(0.5)

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="no eligible clients"):
            compute_tau_global({})

    def test_single_client(self) -> None:
        assert compute_tau_global({"x": 0.42}) == pytest.approx(0.42)

    def test_unweighted_mean(self) -> None:
        taus = {"a": 0.0, "b": 0.0, "c": 0.0, "d": 1.0}
        assert compute_tau_global(taus) == pytest.approx(0.25)

    def test_returns_float(self) -> None:
        assert isinstance(compute_tau_global({"a": 0.5}), float)


# ── build_threshold_result ─────────────────────────────────────────


class TestBuildThresholdResult:
    def test_basic_construction(self) -> None:
        run = _run(ThresholdPolicy.GLOBAL_THRESHOLD)
        result = build_threshold_result(
            run=run,
            tau_global=0.5,
            eligible_thresholds={"a": 0.3, "b": 0.7},
            pending_clients=["c"],
            cluster_metadata=None,
        )
        assert isinstance(result, ThresholdResult)
        assert result.run == run
        assert result.tau_global == pytest.approx(0.5)
        assert result.eligible_count == 2
        assert result.pending_count == 1
        assert result.metadata.cluster is None

    def test_eligible_clients_not_pending(self) -> None:
        result = build_threshold_result(
            run=_run(ThresholdPolicy.LOCAL_THRESHOLD),
            tau_global=0.5,
            eligible_thresholds={"a": 0.3},
            pending_clients=[],
            cluster_metadata=None,
        )
        ct = next(ct for ct in result.client_thresholds if ct.client_id == "a")
        assert ct.threshold == pytest.approx(0.3)
        assert ct.calibration_pending is False
        assert ct.strategy == ThresholdPolicy.LOCAL_THRESHOLD

    def test_pending_clients_get_tau_global(self) -> None:
        result = build_threshold_result(
            run=_run(ThresholdPolicy.GLOBAL_THRESHOLD),
            tau_global=0.42,
            eligible_thresholds={"a": 0.3},
            pending_clients=["p"],
            cluster_metadata=None,
        )
        ct = next(ct for ct in result.client_thresholds if ct.client_id == "p")
        assert ct.threshold == pytest.approx(0.42)
        assert ct.calibration_pending is True
        assert ct.strategy == ThresholdPolicy.GLOBAL_THRESHOLD

    def test_all_eligible_no_pending(self) -> None:
        result = build_threshold_result(
            run=_run(ThresholdPolicy.LOCAL_THRESHOLD),
            tau_global=0.5,
            eligible_thresholds={"a": 0.1, "b": 0.2},
            pending_clients=[],
            cluster_metadata=None,
        )
        assert result.eligible_count == 2
        assert result.pending_count == 0

    def test_all_pending_no_eligible(self) -> None:
        result = build_threshold_result(
            run=_run(ThresholdPolicy.GLOBAL_THRESHOLD),
            tau_global=0.99,
            eligible_thresholds={},
            pending_clients=["x", "y", "z"],
            cluster_metadata=None,
        )
        assert result.eligible_count == 0
        assert result.pending_count == 3
        for ct in result.client_thresholds:
            assert ct.calibration_pending is True
            assert ct.threshold == pytest.approx(0.99)

    def test_with_cluster_metadata(self) -> None:
        cluster_meta = ClusterMetadata(
            k=2,
            cluster_info=ClusterInfoTuple(
                (
                    ClusterInfo(
                        cluster_id="cluster_0", tau_cluster=0.3, members=("a",)
                    ),
                    ClusterInfo(
                        cluster_id="cluster_1", tau_cluster=0.7, members=("b",)
                    ),
                )
            ),
            silhouette=0.85,
            silhouette_scores=ClientSilhouetteScoreTuple(
                (
                    ClientSilhouetteScore(client_id="2", score=0.85),
                    ClientSilhouetteScore(client_id="3", score=0.72),
                )
            ),
            fingerprints=ClientFingerprintTuple(
                (
                    ClientFingerprint(
                        client_id="a",
                        mean=1.0,
                        variance=0.5,
                        skewness=0.1,
                        p95=2.0,
                    ),
                    ClientFingerprint(
                        client_id="b",
                        mean=3.0,
                        variance=0.2,
                        skewness=-0.1,
                        p95=4.0,
                    ),
                )
            ),
        )
        result = build_threshold_result(
            run=_run(ThresholdPolicy.CLUSTER_THRESHOLD),
            tau_global=0.5,
            eligible_thresholds={"a": 0.3, "b": 0.7},
            pending_clients=[],
            cluster_metadata=cluster_meta,
        )
        assert result.metadata.cluster is cluster_meta

    def test_client_thresholds_is_tuple(self) -> None:
        result = build_threshold_result(
            run=_run(ThresholdPolicy.GLOBAL_THRESHOLD),
            tau_global=0.5,
            eligible_thresholds={"a": 0.3},
            pending_clients=["p"],
            cluster_metadata=None,
        )
        assert isinstance(result.client_thresholds, tuple)
        for ct in result.client_thresholds:
            assert isinstance(ct, ClientThreshold)

    def test_strategy_matches_run_baseline(self) -> None:
        for policy in (
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ):
            result = build_threshold_result(
                run=_run(policy),
                tau_global=0.5,
                eligible_thresholds={"a": 0.3},
                pending_clients=[],
                cluster_metadata=None,
            )
            for ct in result.client_thresholds:
                assert ct.strategy == policy
