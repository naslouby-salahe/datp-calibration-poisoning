from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import numpy as np
import pytest

from datp.config.stages import ExperimentStage
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.types import ThresholdResult
from datp.thresholding.eligibility import (
    compute_client_thresholds,
    identify_eligible,
)
from datp.thresholding.strategies import (
    global_threshold,
    local_threshold,
    cluster_threshold,
)
from datp.thresholding.strategies.cluster_threshold import compute_fingerprints


def _run(policy: ThresholdPolicy = ThresholdPolicy.GLOBAL_THRESHOLD) -> PolicyRunId:
    return PolicyRunId(
        cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=0), policy=policy
    )


def _make_errors(n: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.exponential(scale=0.5, size=n).astype(np.float32)


@pytest.fixture()
def client_errors() -> dict[str, np.ndarray]:
    return {
        "client_a": _make_errors(200, seed=1),
        "client_b": _make_errors(150, seed=2),
        "client_c": _make_errors(300, seed=3),
        "client_d": _make_errors(50, seed=4),  # Cal-Pending
    }


N_MIN = 100


class TestGlobalThreshold:
    def test_all_clients_get_tau_global(
        self, client_errors: dict[str, np.ndarray]
    ) -> None:
        result = global_threshold.compute(client_errors, n_min=N_MIN, q=0.95, run=_run(ThresholdPolicy.GLOBAL_THRESHOLD))
        assert isinstance(result, ThresholdResult)
        assert result.run.policy == ThresholdPolicy.GLOBAL_THRESHOLD
        for ct in result.client_thresholds:
            assert ct.threshold == pytest.approx(result.tau_global)

    def test_pending_flagged(self, client_errors: dict[str, np.ndarray]) -> None:
        result = global_threshold.compute(client_errors, n_min=N_MIN, q=0.95, run=_run(ThresholdPolicy.GLOBAL_THRESHOLD))
        pending_cts = [ct for ct in result.client_thresholds if ct.calibration_pending]
        assert len(pending_cts) == 1
        assert pending_cts[0].client_id == "client_d"
        assert result.pending_count == 1
        assert result.eligible_count == 3

    def test_tau_global_is_unweighted_mean(
        self, client_errors: dict[str, np.ndarray]
    ) -> None:
        eligible, _ = identify_eligible(client_errors, n_min=N_MIN)
        taus = compute_client_thresholds(client_errors, eligible, q=0.95)
        expected = sum(taus.values()) / len(taus)
        result = global_threshold.compute(client_errors, n_min=N_MIN, q=0.95, run=_run(ThresholdPolicy.GLOBAL_THRESHOLD))
        assert result.tau_global == pytest.approx(expected)

    def test_arithmetic_mean_differs_from_pooled_percentile(self) -> None:
        errors = {
            "small_high": np.array([10.0, 11.0, 12.0], dtype=np.float64),
            "large_low": np.linspace(0.0, 1.0, 100, dtype=np.float64),
        }
        result = global_threshold.compute(errors, n_min=1, q=0.95, run=_run(ThresholdPolicy.GLOBAL_THRESHOLD))
        pooled = float(np.percentile(np.concatenate(list(errors.values())), 95))
        assert result.tau_global != pytest.approx(pooled)


class TestLocalThreshold:
    def test_eligible_get_local_threshold(
        self, client_errors: dict[str, np.ndarray]
    ) -> None:
        tau_global = 0.42
        result = local_threshold.compute(
            client_errors,
            n_min=N_MIN,
            tau_global=tau_global,
            q=0.95,
            run=_run(ThresholdPolicy.LOCAL_THRESHOLD),
        )
        eligible_cts = [
            ct for ct in result.client_thresholds if not ct.calibration_pending
        ]
        for ct in eligible_cts:
            expected = float(np.percentile(client_errors[ct.client_id], 95))
            assert ct.threshold == pytest.approx(expected)

    def test_pending_get_tau_global(self, client_errors: dict[str, np.ndarray]) -> None:
        tau_global = 0.42
        result = local_threshold.compute(
            client_errors,
            n_min=N_MIN,
            tau_global=tau_global,
            q=0.95,
            run=_run(ThresholdPolicy.LOCAL_THRESHOLD),
        )
        pending_cts = [ct for ct in result.client_thresholds if ct.calibration_pending]
        for ct in pending_cts:
            assert ct.threshold == pytest.approx(tau_global)

    def test_tau_global_not_recomputed(
        self, client_errors: dict[str, np.ndarray]
    ) -> None:
        sentinel = 999.999
        result = local_threshold.compute(
            client_errors,
            n_min=N_MIN,
            tau_global=sentinel,
            q=0.95,
            run=_run(ThresholdPolicy.LOCAL_THRESHOLD),
        )
        assert result.tau_global == pytest.approx(sentinel)

    def test_return_type(self, client_errors: dict[str, np.ndarray]) -> None:
        result = local_threshold.compute(
            client_errors, n_min=N_MIN, tau_global=0.5, q=0.95, run=_run(ThresholdPolicy.LOCAL_THRESHOLD)
        )
        assert isinstance(result, ThresholdResult)
        assert result.run.policy == ThresholdPolicy.LOCAL_THRESHOLD


class TestClusterThresholdFingerprints:
    def test_four_scalars(self, client_errors: dict[str, np.ndarray]) -> None:
        eligible, _ = identify_eligible(client_errors, n_min=N_MIN)
        fps = compute_fingerprints(client_errors, eligible, q=0.95)
        for cid in eligible:
            assert fps[cid].shape == (4,)

    def test_pending_excluded(self, client_errors: dict[str, np.ndarray]) -> None:
        eligible, _ = identify_eligible(client_errors, n_min=N_MIN)
        fps = compute_fingerprints(client_errors, eligible, q=0.95)
        assert "client_d" not in fps


class TestClusterThreshold:
    @pytest.fixture()
    def large_errors(self) -> dict[str, np.ndarray]:
        rng = np.random.default_rng(42)
        return {
            f"c{i}": rng.exponential(scale=0.3 + i * 0.1, size=200).astype(np.float32)
            for i in range(5)
        } | {"pending": _make_errors(10, seed=99)}

    def test_fail_fast_k_elig_lt_2(self) -> None:
        errors = {"only_one": _make_errors(200, seed=0)}
        with pytest.raises(ValueError, match="at least 2 eligible clients"):
            cluster_threshold.compute(
                errors,
                n_min=N_MIN,
                tau_global=0.5,
                q=0.95,
                random_state=42,
                cluster_k=3,
                k_candidates=[2, 3, 4, 5],
                n_init=10,
                max_iter=300,
                run=_run(ThresholdPolicy.CLUSTER_THRESHOLD),
            )

    def test_fixed_k3(self, large_errors: dict[str, np.ndarray]) -> None:
        result = cluster_threshold.compute(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            cluster_k=3,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        assert result.metadata.cluster is not None
        assert result.metadata.cluster.k == 3

    def test_silhouette_k_selection(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        result = cluster_threshold.compute(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            cluster_k=0,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        assert result.metadata.cluster is not None
        assert result.metadata.cluster.k in {2, 3, 4, 5}
        assert result.metadata.cluster.silhouette_scores

    def test_pending_get_tau_global_not_cluster(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        tau_global = 0.42
        result = cluster_threshold.compute(
            large_errors,
            n_min=N_MIN,
            tau_global=tau_global,
            q=0.95,
            random_state=42,
            cluster_k=3,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        ct_pending = next(
            ct for ct in result.client_thresholds if ct.client_id == "pending"
        )
        assert ct_pending.calibration_pending is True
        assert ct_pending.threshold == pytest.approx(tau_global)

    def test_eligible_never_pending_in_cluster(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        result = cluster_threshold.compute(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            cluster_k=3,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        for ct in result.client_thresholds:
            if ct.client_id == "pending":
                assert ct.calibration_pending is True
            else:
                assert ct.calibration_pending is False

    def test_return_type(self, large_errors: dict[str, np.ndarray]) -> None:
        result = cluster_threshold.compute(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            cluster_k=3,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        assert isinstance(result, ThresholdResult)
        assert result.run.policy == ThresholdPolicy.CLUSTER_THRESHOLD
        assert result.metadata.cluster is not None
        assert result.metadata.cluster.cluster_info

    def test_cluster_metadata_complete(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        result = cluster_threshold.compute(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            cluster_k=3,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        assert result.metadata.cluster is not None
        cluster_info = result.metadata.cluster.cluster_info
        total_eligible = sum(len(info.members) for info in cluster_info.values())
        assert total_eligible == result.eligible_count

    def test_pending_absent_from_fingerprints_metadata(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        result = cluster_threshold.compute(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            cluster_k=3,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        assert result.metadata.cluster is not None
        assert "pending" not in result.metadata.cluster.fingerprints
