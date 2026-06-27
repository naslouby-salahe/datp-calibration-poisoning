"""Tests verifying threshold computation policies: global, local, and clustering strategies."""

from __future__ import annotations

import numpy as np
import pytest

from datp.attacks.constants import (
    CLUSTER_K_NBAIOT,
    CLUSTER_MAX_ITER,
    CLUSTER_N_INIT,
    CLUSTER_RANDOM_STATE,
    N_MIN,
    THRESHOLD_QUANTILE,
)
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.types import ThresholdResult
from datp.thresholding.eligibility import (
    compute_client_thresholds,
    identify_eligible,
)
from datp.thresholding.policies import (
    compute_cluster,
    compute_fingerprints,
    compute_global,
    compute_local,
)


def _run(policy: ThresholdPolicy = ThresholdPolicy.GLOBAL_THRESHOLD) -> PolicyRunId:
    """Helper to build a PolicyRunId instance."""
    return PolicyRunId(
        cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=0), policy=policy
    )


def _make_errors(n: int, seed: int = 0) -> np.ndarray:
    """Helper to build exponential reconstruction error arrays."""
    rng = np.random.default_rng(seed)
    return rng.exponential(scale=0.5, size=n).astype(np.float32)


@pytest.fixture()
def client_errors() -> dict[str, np.ndarray]:
    """Fixture to build standard multi-client errors dict."""
    return {
        "client_a": _make_errors(200, seed=1),
        "client_b": _make_errors(150, seed=2),
        "client_c": _make_errors(300, seed=3),
        "client_d": _make_errors(50, seed=4),
    }


class TestGlobalThreshold:
    """Tests verifying compute_global threshold computation policy."""

    def test_all_clients_get_tau_global(
        self, client_errors: dict[str, np.ndarray]
    ) -> None:
        """Verify that all client thresholds match the global computed threshold in global mode."""
        result = compute_global(
            client_errors,
            n_min=N_MIN,
            q=THRESHOLD_QUANTILE,
            run=_run(ThresholdPolicy.GLOBAL_THRESHOLD),
        )
        assert isinstance(result, ThresholdResult)
        assert result.run.policy == ThresholdPolicy.GLOBAL_THRESHOLD
        for ct in result.client_thresholds:
            assert ct.threshold == pytest.approx(result.tau_global)

    def test_pending_flagged(self, client_errors: dict[str, np.ndarray]) -> None:
        """Verify pending clients are flagged and pending count is correct in global mode."""
        result = compute_global(
            client_errors,
            n_min=N_MIN,
            q=THRESHOLD_QUANTILE,
            run=_run(ThresholdPolicy.GLOBAL_THRESHOLD),
        )
        pending_cts = [ct for ct in result.client_thresholds if ct.calibration_pending]
        assert len(pending_cts) == 1
        assert pending_cts[0].client_id == "client_d"
        assert result.pending_count == 1
        assert result.eligible_count == 3

    def test_tau_global_is_unweighted_mean(
        self, client_errors: dict[str, np.ndarray]
    ) -> None:
        """Verify global threshold is the unweighted mean of eligible client percentiles."""
        eligible, _ = identify_eligible(client_errors, n_min=N_MIN)
        taus = compute_client_thresholds(client_errors, eligible, q=THRESHOLD_QUANTILE)
        expected = sum(taus.values()) / len(taus)
        result = compute_global(
            client_errors,
            n_min=N_MIN,
            q=THRESHOLD_QUANTILE,
            run=_run(ThresholdPolicy.GLOBAL_THRESHOLD),
        )
        assert result.tau_global == pytest.approx(expected)

    def test_arithmetic_mean_differs_from_pooled_percentile(self) -> None:
        """Verify global mean threshold is different from pooled percentiles."""
        errors = {
            "small_high": np.array([10.0, 11.0, 12.0], dtype=np.float64),
            "large_low": np.linspace(0.0, 1.0, 100, dtype=np.float64),
        }
        result = compute_global(
            errors,
            n_min=1,
            q=THRESHOLD_QUANTILE,
            run=_run(ThresholdPolicy.GLOBAL_THRESHOLD),
        )
        pooled = float(
            np.percentile(np.concatenate(list(errors.values())), THRESHOLD_QUANTILE)
        )
        assert result.tau_global != pytest.approx(pooled)


class TestLocalThreshold:
    """Tests verifying compute_local threshold computation policy."""

    def test_eligible_get_local_threshold(
        self, client_errors: dict[str, np.ndarray]
    ) -> None:
        """Verify eligible clients receive their own local percentile thresholds."""
        tau_global = 0.42
        result = compute_local(
            client_errors,
            n_min=N_MIN,
            tau_global=tau_global,
            q=THRESHOLD_QUANTILE,
            run=_run(ThresholdPolicy.LOCAL_THRESHOLD),
        )
        eligible_cts = [
            ct for ct in result.client_thresholds if not ct.calibration_pending
        ]
        for ct in eligible_cts:
            expected = float(
                np.percentile(client_errors[ct.client_id], THRESHOLD_QUANTILE)
            )
            assert ct.threshold == pytest.approx(expected)

    def test_pending_get_tau_global(self, client_errors: dict[str, np.ndarray]) -> None:
        """Verify pending clients receive the global fallback threshold value."""
        tau_global = 0.42
        result = compute_local(
            client_errors,
            n_min=N_MIN,
            tau_global=tau_global,
            q=THRESHOLD_QUANTILE,
            run=_run(ThresholdPolicy.LOCAL_THRESHOLD),
        )
        pending_cts = [ct for ct in result.client_thresholds if ct.calibration_pending]
        for ct in pending_cts:
            assert ct.threshold == pytest.approx(tau_global)

    def test_tau_global_not_recomputed(
        self, client_errors: dict[str, np.ndarray]
    ) -> None:
        """Verify global threshold is not re-computed from scratch during local mode."""
        sentinel = 999.999
        result = compute_local(
            client_errors,
            n_min=N_MIN,
            tau_global=sentinel,
            q=THRESHOLD_QUANTILE,
            run=_run(ThresholdPolicy.LOCAL_THRESHOLD),
        )
        assert result.tau_global == pytest.approx(sentinel)

    def test_return_type(self, client_errors: dict[str, np.ndarray]) -> None:
        """Verify compute_local returns a valid ThresholdResult instance."""
        result = compute_local(
            client_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=THRESHOLD_QUANTILE,
            run=_run(ThresholdPolicy.LOCAL_THRESHOLD),
        )
        assert isinstance(result, ThresholdResult)
        assert result.run.policy == ThresholdPolicy.LOCAL_THRESHOLD


class TestClusterThresholdFingerprints:
    """Tests verifying fingerprint extraction in clustering mode."""

    def test_four_scalars(self, client_errors: dict[str, np.ndarray]) -> None:
        """Verify that fingerprint tensors contain exactly 4 scalars per client."""
        eligible, _ = identify_eligible(client_errors, n_min=N_MIN)
        fps = compute_fingerprints(client_errors, eligible, q=THRESHOLD_QUANTILE)
        for cid in eligible:
            assert fps[cid].shape == (4,)

    def test_pending_excluded(self, client_errors: dict[str, np.ndarray]) -> None:
        """Verify that pending clients are completely excluded from fingerprint output."""
        eligible, _ = identify_eligible(client_errors, n_min=N_MIN)
        fps = compute_fingerprints(client_errors, eligible, q=THRESHOLD_QUANTILE)
        assert "client_d" not in fps


class TestClusterThreshold:
    """Tests verifying compute_cluster policy algorithms and properties."""

    @pytest.fixture()
    def large_errors(self) -> dict[str, np.ndarray]:
        """Fixture to generate exponential error distributions for larger pool of clients."""
        rng = np.random.default_rng(42)
        return {
            f"c{i}": rng.exponential(scale=0.3 + i * 0.1, size=200).astype(np.float32)
            for i in range(5)
        } | {"pending": _make_errors(10, seed=99)}

    def test_fail_fast_k_elig_lt_2(self) -> None:
        """Verify ValueError is raised if there are fewer than 2 eligible clients to cluster."""
        errors = {"only_one": _make_errors(200, seed=0)}
        with pytest.raises(ValueError, match="at least 2 eligible clients"):
            compute_cluster(
                errors,
                n_min=N_MIN,
                tau_global=0.5,
                q=THRESHOLD_QUANTILE,
                random_state=CLUSTER_RANDOM_STATE,
                cluster_k=CLUSTER_K_NBAIOT,
                n_init=CLUSTER_N_INIT,
                max_iter=CLUSTER_MAX_ITER,
                run=_run(ThresholdPolicy.CLUSTER_THRESHOLD),
            )

    def test_fixed_k3(self, large_errors: dict[str, np.ndarray]) -> None:
        """Verify that compute_cluster successfully clusters when using fixed k=3."""
        result = compute_cluster(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=THRESHOLD_QUANTILE,
            random_state=CLUSTER_RANDOM_STATE,
            cluster_k=CLUSTER_K_NBAIOT,
            n_init=CLUSTER_N_INIT,
            max_iter=CLUSTER_MAX_ITER,
            run=_run(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        assert result.metadata.cluster is not None
        assert result.metadata.cluster.k == CLUSTER_K_NBAIOT

    def test_adaptive_k_selection_rejected(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        """Verify that adaptive k=0 selection is rejected with ValueError."""
        with pytest.raises(ValueError, match="locked fixed K"):
            compute_cluster(
                large_errors,
                n_min=N_MIN,
                tau_global=0.5,
                q=THRESHOLD_QUANTILE,
                random_state=CLUSTER_RANDOM_STATE,
                cluster_k=0,
                n_init=CLUSTER_N_INIT,
                max_iter=CLUSTER_MAX_ITER,
                run=_run(ThresholdPolicy.CLUSTER_THRESHOLD),
            )

    def test_pending_get_tau_global_not_cluster(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        """Verify pending clients receive the global fallback threshold, not cluster-assigned values."""
        tau_global = 0.42
        result = compute_cluster(
            large_errors,
            n_min=N_MIN,
            tau_global=tau_global,
            q=THRESHOLD_QUANTILE,
            random_state=CLUSTER_RANDOM_STATE,
            cluster_k=CLUSTER_K_NBAIOT,
            n_init=CLUSTER_N_INIT,
            max_iter=CLUSTER_MAX_ITER,
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
        """Verify that eligible clients are not marked pending in clustering results."""
        result = compute_cluster(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=THRESHOLD_QUANTILE,
            random_state=CLUSTER_RANDOM_STATE,
            cluster_k=CLUSTER_K_NBAIOT,
            n_init=CLUSTER_N_INIT,
            max_iter=CLUSTER_MAX_ITER,
            run=_run(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        for ct in result.client_thresholds:
            if ct.client_id == "pending":
                assert ct.calibration_pending is True
            else:
                assert ct.calibration_pending is False

    def test_return_type(self, large_errors: dict[str, np.ndarray]) -> None:
        """Verify compute_cluster returns a valid ThresholdResult containing cluster metadata."""
        result = compute_cluster(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=THRESHOLD_QUANTILE,
            random_state=CLUSTER_RANDOM_STATE,
            cluster_k=CLUSTER_K_NBAIOT,
            n_init=CLUSTER_N_INIT,
            max_iter=CLUSTER_MAX_ITER,
            run=_run(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        assert isinstance(result, ThresholdResult)
        assert result.run.policy == ThresholdPolicy.CLUSTER_THRESHOLD
        assert result.metadata.cluster is not None
        assert result.metadata.cluster.cluster_info

    def test_cluster_metadata_complete(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        """Verify that members count in cluster metadata equals the eligible clients count."""
        result = compute_cluster(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=THRESHOLD_QUANTILE,
            random_state=CLUSTER_RANDOM_STATE,
            cluster_k=CLUSTER_K_NBAIOT,
            n_init=CLUSTER_N_INIT,
            max_iter=CLUSTER_MAX_ITER,
            run=_run(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        assert result.metadata.cluster is not None
        cluster_info = result.metadata.cluster.cluster_info
        total_eligible = sum(len(info.members) for info in cluster_info.values())
        assert total_eligible == result.eligible_count

    def test_pending_absent_from_fingerprints_metadata(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        """Ensure pending clients are omitted from the metadata fingerprints field."""
        result = compute_cluster(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=THRESHOLD_QUANTILE,
            random_state=CLUSTER_RANDOM_STATE,
            cluster_k=CLUSTER_K_NBAIOT,
            n_init=CLUSTER_N_INIT,
            max_iter=CLUSTER_MAX_ITER,
            run=_run(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        assert result.metadata.cluster is not None
        assert "pending" not in result.metadata.cluster.fingerprints
