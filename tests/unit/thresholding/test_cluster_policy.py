"""Tests verifying K-Means clustering threshold policies, client error fingerprints, and locked hyperparameter bindings."""

from __future__ import annotations

from unittest import mock

import numpy as np
import pytest
from sklearn.cluster import KMeans as RealKMeans

from datp.attacks.constants import (
    CLUSTER_K_NBAIOT,
    CLUSTER_MAX_ITER,
    CLUSTER_N_INIT,
    CLUSTER_RANDOM_STATE,
    N_MIN,
    THRESHOLD_QUANTILE,
)
from datp.config.models import ExperimentStage
from datp.core.enums import CLUSTER_FINGERPRINT_FEATURES, ThresholdPolicy
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.thresholding.policies import compute_cluster, compute_fingerprints


def _run() -> PolicyRunId:
    """Helper to build a PolicyRunId instance."""
    return PolicyRunId(
        cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=0),
        policy=ThresholdPolicy.CLUSTER_THRESHOLD,
    )


def _make_errors(n: int, seed: int = 0) -> np.ndarray:
    """Helper to build random mock reconstruction error arrays."""
    return np.random.default_rng(seed).exponential(scale=0.3, size=n).astype(np.float32)


@pytest.fixture()
def eligible_errors() -> dict[str, np.ndarray]:
    """Fixture to build standard multi-client eligible errors dict."""
    rng = np.random.default_rng(42)
    errors: dict[str, np.ndarray] = {
        f"c{i}": rng.exponential(scale=0.2 + i * 0.15, size=200).astype(np.float32)
        for i in range(5)
    }
    errors["pending"] = _make_errors(10, seed=99)
    return errors


class TestClusterThresholdFixedMode:
    """Tests verifying K-Means clustering policy in fixed-k mode."""

    def test_fixed_k3_returns_k3(self, eligible_errors: dict[str, np.ndarray]) -> None:
        """Verify that requesting K=3 returns cluster predictions with exactly 3 clusters."""
        result = compute_cluster(
            eligible_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=THRESHOLD_QUANTILE,
            random_state=CLUSTER_RANDOM_STATE,
            cluster_k=CLUSTER_K_NBAIOT,
            n_init=CLUSTER_N_INIT,
            max_iter=CLUSTER_MAX_ITER,
            run=_run(),
        )
        assert result.metadata.cluster is not None
        assert result.metadata.cluster.k == CLUSTER_K_NBAIOT

    def test_fixed_k_pending_excluded(
        self, eligible_errors: dict[str, np.ndarray]
    ) -> None:
        """Ensure pending clients are excluded from cluster fingerprint calculations."""
        result = compute_cluster(
            eligible_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=THRESHOLD_QUANTILE,
            random_state=CLUSTER_RANDOM_STATE,
            cluster_k=CLUSTER_K_NBAIOT,
            n_init=CLUSTER_N_INIT,
            max_iter=CLUSTER_MAX_ITER,
            run=_run(),
        )
        assert result.metadata.cluster is not None
        assert "pending" not in result.metadata.cluster.fingerprints


class TestClusterThresholdKLock:
    """Tests verifying that adaptive clustering is disabled or locked in nbaIoT environments."""

    def test_adaptive_k_rejected(self, eligible_errors: dict[str, np.ndarray]) -> None:
        """Verify that setting k=0 (adaptive clustering) is rejected with ValueError."""
        with pytest.raises(ValueError, match="locked fixed K"):
            compute_cluster(
                eligible_errors,
                n_min=N_MIN,
                tau_global=0.5,
                q=THRESHOLD_QUANTILE,
                random_state=CLUSTER_RANDOM_STATE,
                cluster_k=0,
                n_init=CLUSTER_N_INIT,
                max_iter=CLUSTER_MAX_ITER,
                run=_run(),
            )

    def test_silhouette_scores_only_for_locked_k(
        self, eligible_errors: dict[str, np.ndarray]
    ) -> None:
        """Verify that silhouette scores are only calculated for the target locked K setting."""
        result = compute_cluster(
            eligible_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=THRESHOLD_QUANTILE,
            random_state=CLUSTER_RANDOM_STATE,
            cluster_k=CLUSTER_K_NBAIOT,
            n_init=CLUSTER_N_INIT,
            max_iter=CLUSTER_MAX_ITER,
            run=_run(),
        )
        assert result.metadata.cluster is not None
        assert set(result.metadata.cluster.silhouette_scores.keys()) <= {
            str(CLUSTER_K_NBAIOT)
        }


class TestClusterThresholdFingerprintRobustness:
    """Tests verifying calculation robustness of client error fingerprints."""

    def test_constant_errors_skew_is_zero(self) -> None:
        """Verify skew features evaluate to 0.0 when errors list is constant."""
        errors = {
            "c0": np.full(200, 0.5, dtype=np.float32),
            "c1": np.full(200, 0.3, dtype=np.float32),
        }
        fps = compute_fingerprints(errors, ["c0", "c1"], q=THRESHOLD_QUANTILE)
        for cid, fp in fps.items():
            assert np.isfinite(fp).all(), (
                f"fingerprint for {cid} contains NaN/inf: {fp}"
            )
            assert fp[2] == pytest.approx(0.0), (
                f"skew for {cid} should be 0.0, got {fp[2]}"
            )

    def test_near_constant_errors_finite_fingerprint(self) -> None:
        """Ensure fingerprints remain finite even under very low variance input distributions."""
        rng = np.random.default_rng(0)
        errors = {
            "c0": np.full(200, 0.01, dtype=np.float32)
            + rng.standard_normal(200).astype(np.float32) * 1e-7,
            "c1": np.full(200, 0.05, dtype=np.float32)
            + rng.standard_normal(200).astype(np.float32) * 1e-7,
        }
        fps = compute_fingerprints(errors, ["c0", "c1"], q=THRESHOLD_QUANTILE)
        for cid, fp in fps.items():
            assert np.isfinite(fp).all(), (
                f"fingerprint for {cid} contains NaN/inf: {fp}"
            )

    def test_identical_fingerprints_raises_via_compute(self) -> None:
        """Verify ValueError is raised if all fingerprints are identical (degenerate input)."""
        errors = {
            "c0": np.full(200, 0.5, dtype=np.float32),
            "c1": np.full(200, 0.5, dtype=np.float32),
        }
        with pytest.raises(ValueError, match="Degenerate fingerprints"):
            compute_cluster(
                errors,
                n_min=N_MIN,
                tau_global=0.5,
                q=THRESHOLD_QUANTILE,
                random_state=CLUSTER_RANDOM_STATE,
                cluster_k=CLUSTER_K_NBAIOT,
                n_init=CLUSTER_N_INIT,
                max_iter=CLUSTER_MAX_ITER,
                run=_run(),
            )

    def test_fingerprints_match_canonical_feature_order(self) -> None:
        """Verify generated fingerprints match the canonical feature schema definitions length."""
        errors = {
            "c0": np.random.default_rng(0)
            .exponential(0.3, size=200)
            .astype(np.float32),
            "c1": np.random.default_rng(1)
            .exponential(0.4, size=200)
            .astype(np.float32),
        }
        fps = compute_fingerprints(errors, ["c0", "c1"], q=THRESHOLD_QUANTILE)
        for cid, fp in fps.items():
            assert len(fp) == len(CLUSTER_FINGERPRINT_FEATURES), (
                f"fingerprint for {cid} has {len(fp)} features, "
                f"expected {len(CLUSTER_FINGERPRINT_FEATURES)}"
            )
            assert np.isfinite(fp).all(), (
                f"fingerprint for {cid} contains NaN/inf: {fp}"
            )

    def test_pending_client_excluded_from_fingerprints(self) -> None:
        """Verify pending clients are omitted from fingerprint results."""
        errors = {
            "eligible": np.random.default_rng(0)
            .exponential(0.3, size=200)
            .astype(np.float32),
            "pending": _make_errors(5, seed=99),
        }
        fps = compute_fingerprints(errors, ["eligible"], q=THRESHOLD_QUANTILE)
        assert "pending" not in fps
        assert "eligible" in fps

    def test_one_eligible_client_raises_before_clustering(self) -> None:
        """Verify clustering fails with ValueError if only 1 client is eligible."""
        errors = {
            "only_one": np.random.default_rng(0)
            .exponential(0.3, size=200)
            .astype(np.float32)
        }
        with pytest.raises(ValueError, match="Cannot cluster"):
            compute_cluster(
                errors,
                n_min=N_MIN,
                tau_global=0.5,
                q=THRESHOLD_QUANTILE,
                random_state=CLUSTER_RANDOM_STATE,
                cluster_k=CLUSTER_K_NBAIOT,
                n_init=CLUSTER_N_INIT,
                max_iter=CLUSTER_MAX_ITER,
                run=_run(),
            )

    def test_calibration_pending_uses_tau_global(self) -> None:
        """Verify that calibration pending clients default to using the global threshold setting."""
        rng = np.random.default_rng(42)
        errors: dict[str, np.ndarray] = {
            f"c{i}": rng.exponential(scale=0.2 + i * 0.15, size=200).astype(np.float32)
            for i in range(4)
        }
        errors["pending"] = _make_errors(10, seed=99)
        tau_global = 0.99

        result = compute_cluster(
            errors,
            n_min=N_MIN,
            tau_global=tau_global,
            q=THRESHOLD_QUANTILE,
            random_state=CLUSTER_RANDOM_STATE,
            cluster_k=CLUSTER_K_NBAIOT,
            n_init=CLUSTER_N_INIT,
            max_iter=CLUSTER_MAX_ITER,
            run=_run(),
        )
        pending_ct = next(
            ct for ct in result.client_thresholds if ct.calibration_pending
        )
        assert pending_ct.threshold == pytest.approx(tau_global)


class TestClusterThresholdKMeansHyperparametersLocked:
    """Tests verifying that KMeans hyperparameters conform strictly to system constants."""

    def test_kmeans_receives_locked_max_iter(
        self, eligible_errors: dict[str, np.ndarray]
    ) -> None:
        """Verify that KMeans is instantiated with the locked system hyperparameter constants."""
        with mock.patch(
            "datp.thresholding.policies.KMeans",
            wraps=RealKMeans,
        ) as km_spy:
            compute_cluster(
                eligible_errors,
                n_min=N_MIN,
                tau_global=0.5,
                q=THRESHOLD_QUANTILE,
                random_state=CLUSTER_RANDOM_STATE,
                cluster_k=CLUSTER_K_NBAIOT,
                n_init=CLUSTER_N_INIT,
                max_iter=CLUSTER_MAX_ITER,
                run=_run(),
            )

        assert km_spy.call_count >= 1
        for call in km_spy.call_args_list:
            assert call.kwargs["max_iter"] == CLUSTER_MAX_ITER
            assert call.kwargs["n_init"] == CLUSTER_N_INIT
            assert call.kwargs["random_state"] == CLUSTER_RANDOM_STATE
