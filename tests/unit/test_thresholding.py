from __future__ import annotations

import dataclasses
import math
import typing
from pathlib import Path
from unittest import mock

import numpy as np
import pytest
from sklearn.cluster import KMeans as RealKMeans

from datp.attacks.injection import (
    PoisonedCalibrationSet,
    apply_defense,
    build_defended_collection,
    build_score_collection,
    trimmed_calibration,
)
from datp.attacks.sweep import InjectionSpec, inject_single_victim, recompute_pair
from datp.config import (
    CLUSTER_K_NBAIOT,
    CLUSTER_MAX_ITER,
    CLUSTER_N_INIT,
    CLUSTER_RANDOM_STATE,
    N_MIN,
    THRESHOLD_QUANTILE,
    ExperimentStage,
)
from datp.core import (
    ClientFingerprint,
    ClusterCountSilhouetteScore,
    ClusterInfo,
    ClusterMetadata,
    PolicyRunId,
    SeedPair,
    ThresholdResult,
    TrainingCellId,
)
from datp.enums import (
    ClientStatus,
    PayloadKey,
    PoisoningDefense,
    PoisoningSourceStrategy,
    ThresholdPolicy,
)
from datp.thresholding import (
    ClusterHyperparams,
    _CLUSTER_CACHE,
    EligibilityResult,
    arithmetic_mean_threshold,
    build_threshold_result,
    compute_client_thresholds,
    compute_cluster,
    compute_fingerprints,
    compute_global,
    compute_local,
    compute_tau_global,
    identify_eligible,
    percentile_threshold,
)
from tests_support.synthetic_scores import (
    StandardScoreSetRequest,
    make_standard_score_set,
)


def _base_provenance(**overrides: str) -> dict:
    base: dict[PayloadKey | str, str] = {
        PayloadKey.CONFIG_IDENTITY: "abc123",
        PayloadKey.SPLIT_MANIFEST_IDENTITY: "def456",
        PayloadKey.MODEL_IDENTITY: "ghi789",
        PayloadKey.SCORE_ARTIFACT_IDENTITY: "jkl012",
        PayloadKey.METRIC_CODE_VERSION: "v1",
        PayloadKey.THRESHOLD_CODE_VERSION: "v1",
        PayloadKey.PACKAGE_VERSION: "v1",
        PayloadKey.GENERATED_AT_UTC: "2026-01-01T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def _base_client(client_id: str = "c1", calibration_pending: bool = False) -> dict:
    return {
        PayloadKey.CLIENT_ID: client_id,
        "fpr": 0.0,
        "tpr": 1.0,
        "tnr": 1.0,
        "fnr": 0.0,
        "precision": 1.0,
        "recall": 1.0,
        "balanced_accuracy": 1.0,
        "macro_f1": 1.0,
        PayloadKey.CONFUSION_MATRIX: {
            "tp": 10,
            "fp": 0,
            "tn": 10,
            "fn": 0,
        },
        PayloadKey.N_BENIGN: 10,
        PayloadKey.N_ATTACK: 10,
        PayloadKey.CALIBRATION_PENDING: calibration_pending,
        PayloadKey.EVALUATION_INCOMPLETE: False,
        PayloadKey.THRESHOLD_VALUE: 0.5,
        PayloadKey.THRESHOLD_SOURCE: "global",
    }


@pytest.fixture(autouse=True)
def _clear_cluster_cache() -> None:
    """Cluster results are memoised per process; isolate tests that patch KMeans."""
    _CLUSTER_CACHE.clear()


_FINGERPRINT_FEATURE_COUNT = 4


def _run() -> PolicyRunId:
    """Helper to build a PolicyRunId instance."""
    return PolicyRunId(
        cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=0),
        policy=ThresholdPolicy.CLUSTER_THRESHOLD,
    )


def _make_errors(n: int, seed: int = 0) -> np.ndarray:
    """Helper to build random mock reconstruction error arrays."""
    return np.random.default_rng(seed).exponential(scale=0.3, size=n).astype(np.float32)


@pytest.fixture
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
            0.5,
            THRESHOLD_QUANTILE,
            ClusterHyperparams(
                k=CLUSTER_K_NBAIOT,
                n_init=CLUSTER_N_INIT,
                max_iter=CLUSTER_MAX_ITER,
                random_state=CLUSTER_RANDOM_STATE,
                n_min=N_MIN,
            ),
            _run(),
        )
        assert result.cluster is not None
        assert result.cluster.k == CLUSTER_K_NBAIOT

    def test_identical_inputs_are_memoised(
        self, eligible_errors: dict[str, np.ndarray]
    ) -> None:
        """Verify repeated clustering of identical errors returns the cached result."""
        params = ClusterHyperparams(
            k=CLUSTER_K_NBAIOT,
            n_init=CLUSTER_N_INIT,
            max_iter=CLUSTER_MAX_ITER,
            random_state=CLUSTER_RANDOM_STATE,
            n_min=N_MIN,
        )
        run = _run()
        first = compute_cluster(eligible_errors, 0.5, THRESHOLD_QUANTILE, params, run)
        assert (
            compute_cluster(eligible_errors, 0.5, THRESHOLD_QUANTILE, params, run)
            is first
        )
        changed = {**eligible_errors, "c0": eligible_errors["c0"] + 0.01}
        assert (
            compute_cluster(changed, 0.5, THRESHOLD_QUANTILE, params, run) is not first
        )

    def test_fixed_k_pending_excluded(
        self, eligible_errors: dict[str, np.ndarray]
    ) -> None:
        """Ensure pending clients are excluded from cluster fingerprint calculations."""
        result = compute_cluster(
            eligible_errors,
            0.5,
            THRESHOLD_QUANTILE,
            ClusterHyperparams(
                k=CLUSTER_K_NBAIOT,
                n_init=CLUSTER_N_INIT,
                max_iter=CLUSTER_MAX_ITER,
                random_state=CLUSTER_RANDOM_STATE,
                n_min=N_MIN,
            ),
            _run(),
        )
        assert result.cluster is not None
        assert all(
            fingerprint.client_id != "pending"
            for fingerprint in result.cluster.fingerprints
        )


class TestClusterThresholdKLock:
    """Tests verifying that adaptive clustering is disabled or locked in nbaIoT environments."""

    def test_adaptive_k_rejected(self, eligible_errors: dict[str, np.ndarray]) -> None:
        """Verify that setting k=0 (adaptive clustering) is rejected with ValueError."""
        cluster_hyperparams = ClusterHyperparams(
            k=0,
            n_init=CLUSTER_N_INIT,
            max_iter=CLUSTER_MAX_ITER,
            random_state=CLUSTER_RANDOM_STATE,
            n_min=N_MIN,
        )
        run_value = _run()
        with pytest.raises(ValueError, match="locked fixed K"):
            compute_cluster(
                eligible_errors,
                0.5,
                THRESHOLD_QUANTILE,
                cluster_hyperparams,
                run_value,
            )

    def test_silhouette_scores_only_for_locked_k(
        self, eligible_errors: dict[str, np.ndarray]
    ) -> None:
        """Verify that silhouette scores are only calculated for the target locked K setting."""
        result = compute_cluster(
            eligible_errors,
            0.5,
            THRESHOLD_QUANTILE,
            ClusterHyperparams(
                k=CLUSTER_K_NBAIOT,
                n_init=CLUSTER_N_INIT,
                max_iter=CLUSTER_MAX_ITER,
                random_state=CLUSTER_RANDOM_STATE,
                n_min=N_MIN,
            ),
            _run(),
        )
        assert result.cluster is not None
        assert {score.cluster_count for score in result.cluster.silhouette_scores} <= {
            CLUSTER_K_NBAIOT
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
        cluster_hyperparams = ClusterHyperparams(
            k=CLUSTER_K_NBAIOT,
            n_init=CLUSTER_N_INIT,
            max_iter=CLUSTER_MAX_ITER,
            random_state=CLUSTER_RANDOM_STATE,
            n_min=N_MIN,
        )
        run_value = _run()
        with pytest.raises(ValueError, match="Degenerate fingerprints"):
            compute_cluster(
                errors,
                0.5,
                THRESHOLD_QUANTILE,
                cluster_hyperparams,
                run_value,
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
            assert len(fp) == _FINGERPRINT_FEATURE_COUNT, (
                f"fingerprint for {cid} has {len(fp)} features, "
                f"expected {_FINGERPRINT_FEATURE_COUNT}"
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
        cluster_hyperparams = ClusterHyperparams(
            k=CLUSTER_K_NBAIOT,
            n_init=CLUSTER_N_INIT,
            max_iter=CLUSTER_MAX_ITER,
            random_state=CLUSTER_RANDOM_STATE,
            n_min=N_MIN,
        )
        run_value = _run()
        with pytest.raises(ValueError, match="Cannot cluster"):
            compute_cluster(
                errors,
                0.5,
                THRESHOLD_QUANTILE,
                cluster_hyperparams,
                run_value,
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
            tau_global,
            THRESHOLD_QUANTILE,
            ClusterHyperparams(
                k=CLUSTER_K_NBAIOT,
                n_init=CLUSTER_N_INIT,
                max_iter=CLUSTER_MAX_ITER,
                random_state=CLUSTER_RANDOM_STATE,
                n_min=N_MIN,
            ),
            _run(),
        )
        pending_ct = next(
            ct
            for ct in result.client_thresholds
            if ct.status is ClientStatus.CALIBRATION_PENDING
        )
        assert pending_ct.threshold == pytest.approx(tau_global)


class TestClusterThresholdKMeansHyperparametersLocked:
    """Tests verifying that KMeans hyperparameters conform strictly to system constants."""

    def test_kmeans_receives_locked_max_iter(
        self, eligible_errors: dict[str, np.ndarray]
    ) -> None:
        """Verify that KMeans is instantiated with the locked system hyperparameter constants."""
        with mock.patch(
            "datp.thresholding.KMeans",
            wraps=RealKMeans,
        ) as km_spy:
            compute_cluster(
                eligible_errors,
                0.5,
                THRESHOLD_QUANTILE,
                ClusterHyperparams(
                    k=CLUSTER_K_NBAIOT,
                    n_init=CLUSTER_N_INIT,
                    max_iter=CLUSTER_MAX_ITER,
                    random_state=CLUSTER_RANDOM_STATE,
                    n_min=N_MIN,
                ),
                _run(),
            )

        assert km_spy.call_count >= 1
        for call in km_spy.call_args_list:
            assert call.kwargs["max_iter"] == CLUSTER_MAX_ITER
            assert call.kwargs["n_init"] == CLUSTER_N_INIT
            assert call.kwargs["random_state"] == CLUSTER_RANDOM_STATE


def _run_eligibility(
    policy: ThresholdPolicy = ThresholdPolicy.GLOBAL_THRESHOLD,
) -> PolicyRunId:
    """Helper to build a PolicyRunId instance."""
    return PolicyRunId(
        cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=0), policy=policy
    )


def _make_errors_eligibility(n: int, seed: int = 0) -> np.ndarray:
    """Helper to build exponential error distributions for test clients."""
    return np.random.default_rng(seed).exponential(scale=0.5, size=n).astype(np.float32)


@pytest.fixture
def client_errors() -> dict[str, np.ndarray]:
    """Fixture to build standard multi-client errors dict with varied sample sizes."""
    return {
        "client_a": _make_errors_eligibility(200, seed=1),
        "client_b": _make_errors_eligibility(150, seed=2),
        "client_c": _make_errors_eligibility(300, seed=3),
        "client_d": _make_errors_eligibility(50, seed=4),
    }


class TestIdentifyEligible:
    """Tests verifying partitioning of clients into eligible/pending based on sample counts."""

    def test_partitions_correctly(self, client_errors: dict[str, np.ndarray]) -> None:
        """Verify that clients are correctly partitioned according to the N_MIN limit."""
        result = identify_eligible(client_errors, n_min=N_MIN)
        assert set(result.eligible_ids) == {"client_a", "client_b", "client_c"}
        assert set(result.pending_ids) == {"client_d"}

    def test_n_min_from_param(self, client_errors: dict[str, np.ndarray]) -> None:
        """Verify N_MIN threshold limits are correctly respected when customized."""
        eligible_ids = identify_eligible(client_errors, n_min=500).eligible_ids
        assert "client_a" not in eligible_ids
        assert "client_b" not in eligible_ids

    def test_all_eligible(self, client_errors: dict[str, np.ndarray]) -> None:
        """Verify all clients are eligible when N_MIN is set to 1."""
        result = identify_eligible(client_errors, n_min=1)
        assert len(result.eligible_ids) == 4
        assert len(result.pending_ids) == 0

    def test_all_pending(self, client_errors: dict[str, np.ndarray]) -> None:
        """Verify all clients are pending when N_MIN is larger than any client sample count."""
        result = identify_eligible(client_errors, n_min=1000)
        assert len(result.eligible_ids) == 0
        assert len(result.pending_ids) == 4

    def test_empty_input(self) -> None:
        """Verify empty input dictionary returns empty lists for both partitions."""
        result = identify_eligible({}, n_min=100)
        assert result.eligible_ids == ()
        assert result.pending_ids == ()

    def test_exact_boundary(self) -> None:
        """Verify client is marked eligible when sample count is exactly N_MIN."""
        errors = {"a": _make_errors_eligibility(100, seed=0)}
        result = identify_eligible(errors, n_min=100)
        assert result.eligible_ids == ("a",)
        assert result.pending_ids == ()


class TestComputeClientThresholds:
    """Tests verifying percentile-based threshold calculations for eligible partitions."""

    def test_eligible_only(self, client_errors: dict[str, np.ndarray]) -> None:
        """Verify that thresholds are computed only for the eligible subset."""
        eligibility = identify_eligible(client_errors, n_min=N_MIN)
        taus = compute_client_thresholds(
            client_errors, eligibility, q=THRESHOLD_QUANTILE
        )
        assert "client_d" not in taus

    def test_matches_percentile(self, client_errors: dict[str, np.ndarray]) -> None:
        """Verify calculated thresholds match the exact percentile values from numpy."""
        eligibility = identify_eligible(client_errors, n_min=N_MIN)
        taus = compute_client_thresholds(
            client_errors, eligibility, q=THRESHOLD_QUANTILE
        )
        for cid in eligibility.eligible_ids:
            expected = float(np.percentile(client_errors[cid], THRESHOLD_QUANTILE))
            assert taus[cid] == pytest.approx(expected)

    def test_empty_eligible_returns_empty(self) -> None:
        """Verify an empty eligibility result returns no client thresholds."""
        taus = compute_client_thresholds(
            {}, EligibilityResult(eligible_ids=(), pending_ids=()), q=THRESHOLD_QUANTILE
        )
        assert taus == {}


class TestComputeTauGlobal:
    """Tests verifying calculation of the global fallback threshold averaging."""

    def test_simple_mean(self) -> None:
        """Verify that global threshold computes the arithmetic mean of client thresholds."""
        taus = {"a": 0.1, "b": 0.9}
        tau_g = compute_tau_global(taus)
        assert tau_g == pytest.approx(0.5)

    def test_empty_raises(self) -> None:
        """Verify ValueError is raised if the eligible thresholds dictionary is empty."""
        with pytest.raises(ValueError, match="no eligible clients"):
            compute_tau_global({})

    def test_single_client(self) -> None:
        """Verify global threshold matches the single client's threshold if count is 1."""
        assert compute_tau_global({"x": 0.42}) == pytest.approx(0.42)

    def test_unweighted_mean(self) -> None:
        """Verify that global threshold calculation is unweighted by sample size."""
        taus = {"a": 0.0, "b": 0.0, "c": 0.0, "d": 1.0}
        assert compute_tau_global(taus) == pytest.approx(0.25)


class TestBuildThresholdResult:
    """Tests verifying construction and mappings of the final ThresholdResult entity."""

    def test_basic_construction(self) -> None:
        """Verify properties of ThresholdResult match the builder inputs."""
        run = _run_eligibility(ThresholdPolicy.GLOBAL_THRESHOLD)
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
        assert result.cluster is None

    def test_eligible_clients_not_pending(self) -> None:
        """Verify that eligible clients have calibration_pending set to False."""
        result = build_threshold_result(
            run=_run_eligibility(ThresholdPolicy.LOCAL_THRESHOLD),
            tau_global=0.5,
            eligible_thresholds={"a": 0.3},
            pending_clients=[],
            cluster_metadata=None,
        )
        ct = next(ct for ct in result.client_thresholds if ct.client_id == "a")
        assert ct.threshold == pytest.approx(0.3)
        assert ct.status is ClientStatus.ELIGIBLE
        assert ct.strategy == ThresholdPolicy.LOCAL_THRESHOLD

    def test_pending_clients_get_tau_global(self) -> None:
        """Verify that pending clients default to global threshold and have calibration_pending set to True."""
        result = build_threshold_result(
            run=_run_eligibility(ThresholdPolicy.GLOBAL_THRESHOLD),
            tau_global=0.42,
            eligible_thresholds={"a": 0.3},
            pending_clients=["p"],
            cluster_metadata=None,
        )
        ct = next(ct for ct in result.client_thresholds if ct.client_id == "p")
        assert ct.threshold == pytest.approx(0.42)
        assert ct.status is ClientStatus.CALIBRATION_PENDING
        assert ct.strategy == ThresholdPolicy.GLOBAL_THRESHOLD

    def test_all_eligible_no_pending(self) -> None:
        """Verify result properties when there are no pending clients."""
        result = build_threshold_result(
            run=_run_eligibility(ThresholdPolicy.LOCAL_THRESHOLD),
            tau_global=0.5,
            eligible_thresholds={"a": 0.1, "b": 0.2},
            pending_clients=[],
            cluster_metadata=None,
        )
        assert result.eligible_count == 2
        assert result.pending_count == 0

    def test_all_pending_no_eligible(self) -> None:
        """Verify result properties when all clients are pending."""
        result = build_threshold_result(
            run=_run_eligibility(ThresholdPolicy.GLOBAL_THRESHOLD),
            tau_global=0.99,
            eligible_thresholds={},
            pending_clients=["x", "y", "z"],
            cluster_metadata=None,
        )
        assert result.eligible_count == 0
        assert result.pending_count == 3
        for ct in result.client_thresholds:
            assert ct.status is ClientStatus.CALIBRATION_PENDING
            assert ct.threshold == pytest.approx(0.99)

    def test_with_cluster_metadata(self) -> None:
        """Verify that cluster metadata is correctly linked in the built result."""
        cluster_meta = ClusterMetadata(
            k=2,
            cluster_info=(
                ClusterInfo(cluster_id="cluster_0", tau_cluster=0.3, members=("a",)),
                ClusterInfo(cluster_id="cluster_1", tau_cluster=0.7, members=("b",)),
            ),
            silhouette=0.85,
            silhouette_scores=(
                ClusterCountSilhouetteScore(cluster_count=2, score=0.85),
                ClusterCountSilhouetteScore(cluster_count=3, score=0.72),
            ),
            fingerprints=(
                ClientFingerprint(
                    client_id="a", mean=1.0, std=0.5, skewness=0.1, p95=2.0
                ),
                ClientFingerprint(
                    client_id="b", mean=3.0, std=0.2, skewness=-0.1, p95=4.0
                ),
            ),
        )

        result = build_threshold_result(
            run=_run_eligibility(ThresholdPolicy.CLUSTER_THRESHOLD),
            tau_global=0.5,
            eligible_thresholds={"a": 0.3, "b": 0.7},
            pending_clients=[],
            cluster_metadata=cluster_meta,
        )
        assert result.cluster is cluster_meta

    def test_strategy_matches_run_policy(self) -> None:
        """Ensure client thresholds strategy matches the policy run ID configuration."""
        for policy in (
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        ):
            result = build_threshold_result(
                run=_run_eligibility(policy),
                tau_global=0.5,
                eligible_thresholds={"a": 0.3},
                pending_clients=[],
                cluster_metadata=None,
            )
            for ct in result.client_thresholds:
                assert ct.strategy == policy


def _run_policies(
    policy: ThresholdPolicy = ThresholdPolicy.GLOBAL_THRESHOLD,
) -> PolicyRunId:
    """Helper to build a PolicyRunId instance."""
    return PolicyRunId(
        cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=0), policy=policy
    )


def _make_errors_policies(n: int, seed: int = 0) -> np.ndarray:
    """Helper to build exponential reconstruction error arrays."""
    rng = np.random.default_rng(seed)
    return rng.exponential(scale=0.5, size=n).astype(np.float32)


@pytest.fixture
def client_errors_policies() -> dict[str, np.ndarray]:
    """Fixture to build standard multi-client errors dict."""
    return {
        "client_a": _make_errors_policies(200, seed=1),
        "client_b": _make_errors_policies(150, seed=2),
        "client_c": _make_errors_policies(300, seed=3),
        "client_d": _make_errors_policies(50, seed=4),
    }


class TestGlobalThreshold:
    """Tests verifying compute_global threshold computation policy."""

    def test_all_clients_get_tau_global(
        self, client_errors_policies: dict[str, np.ndarray]
    ) -> None:
        """Verify that all client thresholds match the global computed threshold in global mode."""
        result = compute_global(
            client_errors_policies,
            n_min=N_MIN,
            q=THRESHOLD_QUANTILE,
            run=_run_policies(ThresholdPolicy.GLOBAL_THRESHOLD),
        )
        assert isinstance(result, ThresholdResult)
        assert result.run.policy == ThresholdPolicy.GLOBAL_THRESHOLD
        for ct in result.client_thresholds:
            assert ct.threshold == pytest.approx(result.tau_global)

    def test_pending_flagged(
        self, client_errors_policies: dict[str, np.ndarray]
    ) -> None:
        """Verify pending clients are flagged and pending count is correct in global mode."""
        result = compute_global(
            client_errors_policies,
            n_min=N_MIN,
            q=THRESHOLD_QUANTILE,
            run=_run_policies(ThresholdPolicy.GLOBAL_THRESHOLD),
        )
        pending_cts = [
            ct
            for ct in result.client_thresholds
            if ct.status is ClientStatus.CALIBRATION_PENDING
        ]
        assert len(pending_cts) == 1
        assert pending_cts[0].client_id == "client_d"
        assert result.pending_count == 1
        assert result.eligible_count == 3

    def test_tau_global_is_unweighted_mean(
        self, client_errors_policies: dict[str, np.ndarray]
    ) -> None:
        """Verify global threshold is the unweighted mean of eligible client percentiles."""
        eligibility = identify_eligible(client_errors_policies, n_min=N_MIN)
        taus = compute_client_thresholds(
            client_errors_policies, eligibility, q=THRESHOLD_QUANTILE
        )
        expected = sum(taus.values()) / len(taus)
        result = compute_global(
            client_errors_policies,
            n_min=N_MIN,
            q=THRESHOLD_QUANTILE,
            run=_run_policies(ThresholdPolicy.GLOBAL_THRESHOLD),
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
            run=_run_policies(ThresholdPolicy.GLOBAL_THRESHOLD),
        )
        pooled = float(
            np.percentile(np.concatenate(list(errors.values())), THRESHOLD_QUANTILE)
        )
        assert result.tau_global != pytest.approx(pooled)


class TestLocalThreshold:
    """Tests verifying compute_local threshold computation policy."""

    def test_eligible_get_local_threshold(
        self, client_errors_policies: dict[str, np.ndarray]
    ) -> None:
        """Verify eligible clients receive their own local percentile thresholds."""
        tau_global = 0.42
        result = compute_local(
            client_errors_policies,
            n_min=N_MIN,
            tau_global=tau_global,
            q=THRESHOLD_QUANTILE,
            run=_run_policies(ThresholdPolicy.LOCAL_THRESHOLD),
        )
        eligible_cts = [
            ct for ct in result.client_thresholds if ct.status is ClientStatus.ELIGIBLE
        ]
        for ct in eligible_cts:
            expected = float(
                np.percentile(client_errors_policies[ct.client_id], THRESHOLD_QUANTILE)
            )
            assert ct.threshold == pytest.approx(expected)

    def test_pending_get_tau_global(
        self, client_errors_policies: dict[str, np.ndarray]
    ) -> None:
        """Verify pending clients receive the global fallback threshold value."""
        tau_global = 0.42
        result = compute_local(
            client_errors_policies,
            n_min=N_MIN,
            tau_global=tau_global,
            q=THRESHOLD_QUANTILE,
            run=_run_policies(ThresholdPolicy.LOCAL_THRESHOLD),
        )
        pending_cts = [
            ct
            for ct in result.client_thresholds
            if ct.status is ClientStatus.CALIBRATION_PENDING
        ]
        for ct in pending_cts:
            assert ct.threshold == pytest.approx(tau_global)

    def test_tau_global_not_recomputed(
        self, client_errors_policies: dict[str, np.ndarray]
    ) -> None:
        """Verify global threshold is not re-computed from scratch during local mode."""
        sentinel = 999.999
        result = compute_local(
            client_errors_policies,
            n_min=N_MIN,
            tau_global=sentinel,
            q=THRESHOLD_QUANTILE,
            run=_run_policies(ThresholdPolicy.LOCAL_THRESHOLD),
        )
        assert result.tau_global == pytest.approx(sentinel)

    def test_return_type(self, client_errors_policies: dict[str, np.ndarray]) -> None:
        """Verify compute_local returns a valid ThresholdResult instance."""
        result = compute_local(
            client_errors_policies,
            n_min=N_MIN,
            tau_global=0.5,
            q=THRESHOLD_QUANTILE,
            run=_run_policies(ThresholdPolicy.LOCAL_THRESHOLD),
        )
        assert isinstance(result, ThresholdResult)
        assert result.run.policy == ThresholdPolicy.LOCAL_THRESHOLD


class TestClusterThresholdFingerprints:
    """Tests verifying fingerprint extraction in clustering mode."""

    def test_four_scalars(self, client_errors_policies: dict[str, np.ndarray]) -> None:
        """Verify that fingerprint tensors contain exactly 4 scalars per client."""
        eligibility = identify_eligible(client_errors_policies, n_min=N_MIN)
        fps = compute_fingerprints(
            client_errors_policies, eligibility.eligible_ids, q=THRESHOLD_QUANTILE
        )
        for cid in eligibility.eligible_ids:
            assert fps[cid].shape == (4,)

    def test_pending_excluded(
        self, client_errors_policies: dict[str, np.ndarray]
    ) -> None:
        """Verify that pending clients are completely excluded from fingerprint output."""
        eligibility = identify_eligible(client_errors_policies, n_min=N_MIN)
        fps = compute_fingerprints(
            client_errors_policies, eligibility.eligible_ids, q=THRESHOLD_QUANTILE
        )
        assert "client_d" not in fps


class TestClusterThreshold:
    """Tests verifying compute_cluster policy algorithms and properties."""

    @pytest.fixture
    def large_errors(self) -> dict[str, np.ndarray]:
        """Fixture to generate exponential error distributions for larger pool of clients."""
        rng = np.random.default_rng(42)
        return {
            f"c{i}": rng.exponential(scale=0.3 + i * 0.1, size=200).astype(np.float32)
            for i in range(5)
        } | {"pending": _make_errors_policies(10, seed=99)}

    def test_fail_fast_k_elig_lt_2(self) -> None:
        """Verify ValueError is raised if there are fewer than 2 eligible clients to cluster."""
        errors = {"only_one": _make_errors_policies(200, seed=0)}
        cluster_hyperparams = ClusterHyperparams(
            k=CLUSTER_K_NBAIOT,
            n_init=CLUSTER_N_INIT,
            max_iter=CLUSTER_MAX_ITER,
            random_state=CLUSTER_RANDOM_STATE,
            n_min=N_MIN,
        )
        run_policies_value = _run_policies(ThresholdPolicy.CLUSTER_THRESHOLD)
        with pytest.raises(ValueError, match="at least 2 eligible clients"):
            compute_cluster(
                errors,
                0.5,
                THRESHOLD_QUANTILE,
                cluster_hyperparams,
                run_policies_value,
            )

    def test_fixed_k3(self, large_errors: dict[str, np.ndarray]) -> None:
        """Verify that compute_cluster successfully clusters when using fixed k=3."""
        result = compute_cluster(
            large_errors,
            0.5,
            THRESHOLD_QUANTILE,
            ClusterHyperparams(
                k=CLUSTER_K_NBAIOT,
                n_init=CLUSTER_N_INIT,
                max_iter=CLUSTER_MAX_ITER,
                random_state=CLUSTER_RANDOM_STATE,
                n_min=N_MIN,
            ),
            _run_policies(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        assert result.cluster is not None
        assert result.cluster.k == CLUSTER_K_NBAIOT

    def test_adaptive_k_selection_rejected(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        """Verify that adaptive k=0 selection is rejected with ValueError."""
        cluster_hyperparams = ClusterHyperparams(
            k=0,
            n_init=CLUSTER_N_INIT,
            max_iter=CLUSTER_MAX_ITER,
            random_state=CLUSTER_RANDOM_STATE,
            n_min=N_MIN,
        )
        run_policies_value = _run_policies(ThresholdPolicy.CLUSTER_THRESHOLD)
        with pytest.raises(ValueError, match="locked fixed K"):
            compute_cluster(
                large_errors,
                0.5,
                THRESHOLD_QUANTILE,
                cluster_hyperparams,
                run_policies_value,
            )

    def test_pending_get_tau_global_not_cluster(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        """Verify pending clients receive the global fallback threshold, not cluster-assigned values."""
        tau_global = 0.42
        result = compute_cluster(
            large_errors,
            tau_global,
            THRESHOLD_QUANTILE,
            ClusterHyperparams(
                k=CLUSTER_K_NBAIOT,
                n_init=CLUSTER_N_INIT,
                max_iter=CLUSTER_MAX_ITER,
                random_state=CLUSTER_RANDOM_STATE,
                n_min=N_MIN,
            ),
            _run_policies(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        ct_pending = next(
            ct for ct in result.client_thresholds if ct.client_id == "pending"
        )
        assert ct_pending.status is ClientStatus.CALIBRATION_PENDING
        assert ct_pending.threshold == pytest.approx(tau_global)

    def test_eligible_never_pending_in_cluster(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        """Verify that eligible clients are not marked pending in clustering results."""
        result = compute_cluster(
            large_errors,
            0.5,
            THRESHOLD_QUANTILE,
            ClusterHyperparams(
                k=CLUSTER_K_NBAIOT,
                n_init=CLUSTER_N_INIT,
                max_iter=CLUSTER_MAX_ITER,
                random_state=CLUSTER_RANDOM_STATE,
                n_min=N_MIN,
            ),
            _run_policies(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        for ct in result.client_thresholds:
            if ct.client_id == "pending":
                assert ct.status is ClientStatus.CALIBRATION_PENDING
            else:
                assert ct.status is ClientStatus.ELIGIBLE

    def test_return_type(self, large_errors: dict[str, np.ndarray]) -> None:
        """Verify compute_cluster returns a valid ThresholdResult containing cluster metadata."""
        result = compute_cluster(
            large_errors,
            0.5,
            THRESHOLD_QUANTILE,
            ClusterHyperparams(
                k=CLUSTER_K_NBAIOT,
                n_init=CLUSTER_N_INIT,
                max_iter=CLUSTER_MAX_ITER,
                random_state=CLUSTER_RANDOM_STATE,
                n_min=N_MIN,
            ),
            _run_policies(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        assert isinstance(result, ThresholdResult)
        assert result.run.policy == ThresholdPolicy.CLUSTER_THRESHOLD
        assert result.cluster is not None
        assert result.cluster.cluster_info

    def test_cluster_metadata_complete(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        """Verify that members count in cluster metadata equals the eligible clients count."""
        result = compute_cluster(
            large_errors,
            0.5,
            THRESHOLD_QUANTILE,
            ClusterHyperparams(
                k=CLUSTER_K_NBAIOT,
                n_init=CLUSTER_N_INIT,
                max_iter=CLUSTER_MAX_ITER,
                random_state=CLUSTER_RANDOM_STATE,
                n_min=N_MIN,
            ),
            _run_policies(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        assert result.cluster is not None
        cluster_info = result.cluster.cluster_info
        total_eligible = sum(len(info.members) for info in cluster_info)
        assert total_eligible == result.eligible_count

    def test_pending_absent_from_fingerprints_metadata(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        """Ensure pending clients are omitted from the metadata fingerprints field."""
        result = compute_cluster(
            large_errors,
            0.5,
            THRESHOLD_QUANTILE,
            ClusterHyperparams(
                k=CLUSTER_K_NBAIOT,
                n_init=CLUSTER_N_INIT,
                max_iter=CLUSTER_MAX_ITER,
                random_state=CLUSTER_RANDOM_STATE,
                n_min=N_MIN,
            ),
            _run_policies(ThresholdPolicy.CLUSTER_THRESHOLD),
        )
        assert result.cluster is not None
        assert all(
            fingerprint.client_id != "pending"
            for fingerprint in result.cluster.fingerprints
        )


def test_client_metrics_is_frozen_dataclass() -> None:
    """Verify that ClientEvaluationRecord is a frozen python dataclass."""
    from datp.evaluation import ClientEvaluationRecord

    assert dataclasses.is_dataclass(ClientEvaluationRecord)
    assert getattr(ClientEvaluationRecord, "__dataclass_params__").frozen


def test_evaluation_result_is_frozen_dataclass() -> None:
    """Verify that EvaluationResult is a frozen python dataclass."""
    from datp.evaluation import EvaluationResult

    assert dataclasses.is_dataclass(EvaluationResult)
    assert getattr(EvaluationResult, "__dataclass_params__").frozen


def test_threshold_result_required_keys() -> None:
    """Verify that ThresholdResult has all expected fields in its schema hints."""
    from datp.core import ThresholdResult

    hints = typing.get_type_hints(ThresholdResult)
    expected = {
        "run",
        "tau_global",
        "client_thresholds",
        "cluster",
    }
    assert expected.issubset(hints.keys()), f"Missing keys: {expected - hints.keys()}"


def test_client_metrics_dict_keys() -> None:
    """Verify that ClientEvaluationRecord fields match target metadata schema."""
    from datp.evaluation import ClientEvaluationRecord

    field_names = {f.name for f in dataclasses.fields(ClientEvaluationRecord)}
    expected = {
        "client_id",
        "metrics",
        "confusion",
        "n_benign",
        "n_attack",
        "threshold",
        "evaluation_incomplete",
    }
    assert expected.issubset(field_names), f"Missing keys: {expected - field_names}"


def test_threshold_result_is_frozen_dataclass() -> None:
    """Verify that ThresholdResult is a frozen python dataclass."""
    from datp.core import ThresholdResult

    assert dataclasses.is_dataclass(ThresholdResult)
    assert getattr(ThresholdResult, "__dataclass_params__").frozen


def test_client_threshold_is_frozen_dataclass() -> None:
    """Verify that ClientThreshold is a frozen python dataclass."""
    from datp.core import ClientThreshold

    assert dataclasses.is_dataclass(ClientThreshold)
    assert getattr(ClientThreshold, "__dataclass_params__").frozen


def test_threshold_result_client_thresholds_is_tuple() -> None:
    """Verify that client thresholds in ThresholdResult are stored as an immutable tuple."""
    from datp.core import ThresholdResult

    hints = typing.get_type_hints(ThresholdResult)
    assert "tuple" in str(hints["client_thresholds"])


def test_cluster_metadata_is_frozen_dataclass() -> None:
    """Verify that ClusterInfo and ClusterMetadata are frozen python dataclasses."""
    from datp.core import ClusterInfo, ClusterMetadata

    for cls in (ClusterInfo, ClusterMetadata):
        assert dataclasses.is_dataclass(cls), f"{cls.__name__} must be a dataclass"
        assert getattr(cls, "__dataclass_params__").frozen, (
            f"{cls.__name__} must be frozen"
        )


def test_identity_classes_are_frozen_dataclasses() -> None:
    """Verify that PolicyRunId and TrainingCellId are frozen python dataclasses."""
    from datp.core import PolicyRunId, TrainingCellId

    for cls in (TrainingCellId, PolicyRunId):
        assert dataclasses.is_dataclass(cls), f"{cls.__name__} must be a dataclass"
        assert getattr(cls, "__dataclass_params__").frozen, (
            f"{cls.__name__} must be frozen"
        )


def test_score_cell_id_is_frozen_dataclass() -> None:
    """Verify that TrainingCellId is a frozen python dataclass."""
    from datp.core import TrainingCellId

    assert dataclasses.is_dataclass(TrainingCellId)
    assert getattr(TrainingCellId, "__dataclass_params__").frozen


def test_score_cell_id_delegates_to_cell() -> None:
    """Verify properties and field accessors of TrainingCellId."""
    from datp.config import ExperimentStage
    from datp.core import TrainingCellId

    cell = TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=42)
    sc = cell
    assert sc.stage == ExperimentStage.NBAIOT_MAIN
    assert sc.seed == 42


def test_dispersion_metrics_is_frozen_dataclass() -> None:
    """Verify that DispersionMetrics is a frozen python dataclass."""
    from datp.evaluation import DispersionMetrics

    assert dataclasses.is_dataclass(DispersionMetrics)
    assert getattr(DispersionMetrics, "__dataclass_params__").frozen


def test_confusion_counts_is_frozen_dataclass() -> None:
    """Verify that ConfusionCounts is a frozen python dataclass."""
    from datp.evaluation import ConfusionCounts

    assert dataclasses.is_dataclass(ConfusionCounts)
    assert getattr(ConfusionCounts, "__dataclass_params__").frozen
    cc = ConfusionCounts(tp=10, fp=2, tn=88, fn=5)
    assert cc.fp + cc.tn == 90
    assert cc.tp + cc.fn == 15


def test_client_evaluation_record_is_frozen_dataclass() -> None:
    """Verify that ClientEvaluationRecord is a frozen python dataclass."""
    from datp.evaluation import ClientEvaluationRecord

    assert dataclasses.is_dataclass(ClientEvaluationRecord)
    assert getattr(ClientEvaluationRecord, "__dataclass_params__").frozen


def test_artifact_layout_is_frozen_dataclass() -> None:
    """Verify that ArtifactLayout is a frozen python dataclass."""
    from datp.artifacts import ArtifactLayout

    assert dataclasses.is_dataclass(ArtifactLayout)
    assert getattr(ArtifactLayout, "__dataclass_params__").frozen


def test_score_cell_paths_is_frozen_dataclass() -> None:
    """Verify that ScoreCellPaths is a frozen python dataclass."""
    from datp.artifacts import ScoreCellPaths

    assert dataclasses.is_dataclass(ScoreCellPaths)
    assert getattr(ScoreCellPaths, "__dataclass_params__").frozen


def test_policy_run_paths_is_frozen_dataclass() -> None:
    """Verify that PolicyRunPaths is a frozen python dataclass."""
    from datp.artifacts import PolicyRunPaths

    assert dataclasses.is_dataclass(PolicyRunPaths)
    assert getattr(PolicyRunPaths, "__dataclass_params__").frozen


def test_path_contracts_compose_with_identity(tmp_path: Path) -> None:
    """Verify that ArtifactLayout resolves correct paths for TrainingCellId and PolicyRunId."""
    from datp.artifacts import ArtifactLayout
    from datp.config import ExperimentStage
    from datp.core import PolicyRunId, TrainingCellId

    cell = TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=1)
    layout = ArtifactLayout(
        base_dir=tmp_path / "out", stage=ExperimentStage.NBAIOT_MAIN
    )

    sc_paths = layout.score_cell(cell)
    assert "seed_1" in str(sc_paths.score_dir)

    run = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
    br_paths = layout.policy_run(run)
    assert "global_threshold" in str(br_paths.result_dir)


class TestPercentileThreshold:
    """Tests verifying percentile-based threshold computations and bound checks."""

    def test_known_uniform(self) -> None:
        """Verify percentile calculations for uniform arrays."""
        errors = np.arange(1.0, 101.0)
        result = percentile_threshold(errors, q=THRESHOLD_QUANTILE)
        expected = float(np.percentile(errors, THRESHOLD_QUANTILE))
        assert result == pytest.approx(expected)

    def test_known_exact(self) -> None:
        """Verify percentile calculations for small exact arrays."""
        errors = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        result = percentile_threshold(errors, q=50)
        expected = float(np.percentile(errors, 50))
        assert result == pytest.approx(expected)

    def test_q_zero(self) -> None:
        """Verify that setting percentile q=0.0 returns the minimum element."""
        errors = np.array([3.0, 1.0, 2.0])
        assert percentile_threshold(errors, q=0.0) == pytest.approx(1.0)

    def test_q_one(self) -> None:
        """Verify that setting percentile q=100.0 returns the maximum element."""
        errors = np.array([3.0, 1.0, 2.0])
        assert percentile_threshold(errors, q=100) == pytest.approx(3.0)

    def test_single_element(self) -> None:
        """Verify that percentile threshold returns the element itself if length is 1."""
        errors = np.array([42.0])
        assert percentile_threshold(errors, q=THRESHOLD_QUANTILE) == pytest.approx(42.0)

    def test_empty_array_raises(self) -> None:
        """Verify ValueError is raised if input errors array is empty."""
        array_value = np.array([])
        with pytest.raises(ValueError, match="empty"):
            percentile_threshold(array_value, q=THRESHOLD_QUANTILE)


class TestArithmeticMeanThreshold:
    """Tests verifying unweighted arithmetic mean calculations for threshold values."""

    def test_unweighted_not_weighted(self) -> None:
        """Verify that mean is unweighted by client sample sizes."""
        tau_values = [0.1, 0.9]
        sample_sizes = [1000, 10]

        unweighted = arithmetic_mean_threshold(tau_values)
        weighted = float(np.average(tau_values, weights=sample_sizes))

        assert unweighted != pytest.approx(weighted, abs=1e-6)
        assert unweighted == pytest.approx(0.5)

    def test_known_values(self) -> None:
        """Verify arithmetic mean threshold on known list of values."""
        assert arithmetic_mean_threshold([2.0, 4.0, 6.0]) == pytest.approx(4.0)

    def test_single_value(self) -> None:
        """Verify arithmetic mean threshold on a single value."""
        assert arithmetic_mean_threshold([7.5]) == pytest.approx(7.5)

    def test_equal_values(self) -> None:
        """Verify arithmetic mean threshold on a list of identical values."""
        assert arithmetic_mean_threshold([3.0, 3.0, 3.0]) == pytest.approx(3.0)

    def test_numpy_input(self) -> None:
        """Verify arithmetic mean threshold accepts numpy arrays."""
        arr = np.array([1.0, 2.0, 3.0])
        assert arithmetic_mean_threshold(arr) == pytest.approx(2.0)

    def test_empty_raises(self) -> None:
        """Verify ValueError is raised if input list is empty."""
        with pytest.raises(ValueError, match="empty"):
            arithmetic_mean_threshold([])


def test_trim_zero_fraction_returns_equal_copy() -> None:
    """Verify that trimming with a 0.0 fraction returns a sorted or identical copy."""
    cal = np.array([0.1, 0.9, 0.3, 0.5, 0.2])
    out = trimmed_calibration(cal, 0.0)
    assert np.array_equal(np.sort(cal), np.sort(out)) or np.array_equal(cal, out)
    assert out is not cal


def test_trim_does_not_mutate_input() -> None:
    """Verify that trimming does not modify the original input array in-place."""
    cal = np.array([0.1, 0.9, 0.3, 0.5, 0.2])
    before = cal.copy()
    trimmed_calibration(cal, 0.2)
    assert np.array_equal(cal, before)


def test_trim_drops_floor_k_from_each_tail() -> None:
    """Verify that trimming drops floor(N * fraction) elements from both high and low tails."""
    cal = np.arange(10, dtype=np.float64)
    out = trimmed_calibration(cal, 0.1)
    assert np.array_equal(out, np.array([1, 2, 3, 4, 5, 6, 7, 8], dtype=np.float64))


def test_trim_removes_extreme_outliers() -> None:
    """Verify that extreme outliers are successfully pruned by the trimming defense."""
    cal = np.concatenate([np.full(90, 0.05), np.full(10, 100.0)])

    out = trimmed_calibration(cal, 0.10)
    assert out.max() < 1.0


def test_trim_rejects_out_of_range_fraction() -> None:
    """Verify that invalid trimming fractions (outside [0, 0.5)) raise ValueError."""
    cal = np.arange(10, dtype=np.float64)
    with pytest.raises(ValueError, match="0, 0.5"):
        trimmed_calibration(cal, 0.5)
    with pytest.raises(ValueError, match="0, 0.5"):
        trimmed_calibration(cal, -0.1)


def _make_collection() -> object:
    """Helper to build a synthetic client score collection."""
    ss = make_standard_score_set(StandardScoreSetRequest(n_eligible=9, n_pending=1))
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    return build_score_collection(raw)


def test_defended_collection_trims_cal_keeps_test_arrays() -> None:
    """Verify that defended collection trims only the calibration splits, leaving test splits intact."""
    col = _make_collection()
    defended = build_defended_collection(col, 0.10)
    for cid in col.all_ids:
        assert defended.clients[cid].cal.shape[0] < col.clients[cid].cal.shape[0]
        assert np.array_equal(
            defended.clients[cid].test_attack, col.clients[cid].test_attack
        )


def test_apply_defense_none_is_identity() -> None:
    """Verify that applying PoisoningDefense.NONE acts as a no-op identity."""
    col = _make_collection()
    victim = col.eligible_ids[0]
    outcome = inject_single_victim(
        col,
        victim_id=victim,
        spec=InjectionSpec(
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=0.10,
            seed_pair=SeedPair(training_seed=0, poisoning_seed=100),
            objective=None,
        ),
    )
    poisoned_cal = {
        cid: outcome.poisoned_cal_set[cid].cal for cid in outcome.poisoned_cal_set
    }
    col2, pois2 = apply_defense(
        col, poisoned_cal, defense=PoisoningDefense.NONE, trim_fraction=0.05
    )
    assert col2 is col
    assert pois2 is poisoned_cal


_Q = 0.95


def _build_tail_contaminated_cal(
    clean: np.ndarray, *, fraction: float, value: float, rng: np.random.Generator
) -> np.ndarray:
    """Helper to poison a target calibration array with outlier values."""
    poisoned = clean.copy()
    m = max(1, round(fraction * clean.shape[0]))
    positions = rng.choice(clean.shape[0], size=m, replace=False)
    poisoned[positions] = value
    return poisoned


def _abs_delta_tau_for_poisoned(
    col: object, victim: str, poisoned_victim_cal: np.ndarray, *, defended: bool
) -> float:
    """Helper to compute the absolute threshold delta between poisoned and clean victim."""
    poisoned_cal = {
        cid: (poisoned_victim_cal if cid == victim else col.clients[cid].cal.copy())
        for cid in col.eligible_ids
    }
    work_col, work_pois = col, poisoned_cal
    if defended:
        work_col, work_pois = apply_defense(
            col,
            poisoned_cal,
            defense=PoisoningDefense.TRIMMED_CALIBRATION,
            trim_fraction=0.15,
        )
    pair = recompute_pair(
        work_col,
        PoisonedCalibrationSet.from_mapping(work_pois),
        ThresholdPolicy.LOCAL_THRESHOLD,
    )
    return abs(pair.thresholds_pois[victim] - pair.thresholds_clean[victim])


def test_trimming_reduces_abs_delta_tau_high_contamination() -> None:
    """Verify that trimming defense reduces threshold delta under poisoning."""
    col = _make_collection()
    victim = col.eligible_ids[0]
    rng = np.random.default_rng(0)
    poisoned = _build_tail_contaminated_cal(
        col.clients[victim].cal, fraction=0.10, value=0.5, rng=rng
    )
    undefended = _abs_delta_tau_for_poisoned(col, victim, poisoned, defended=False)
    defended = _abs_delta_tau_for_poisoned(col, victim, poisoned, defended=True)
    assert undefended > 0.0
    assert defended < undefended


def test_trimming_neutralizes_injected_low_tail() -> None:
    """Verify that trimming neutralizes low-tail injection values."""
    base = np.full(100, 0.5)
    poisoned = base.copy()
    poisoned[:10] = 0.0
    assert int((poisoned < 0.4).sum()) == 10
    trimmed = trimmed_calibration(poisoned, 0.15)
    assert int((trimmed < 0.4).sum()) == 0


def test_defense_runs_end_to_end_through_recompute_pipeline() -> None:
    """Verify end-to-end execution of trimmed calibration defense in the recompute pipeline."""
    col = _make_collection()
    victim = col.eligible_ids[0]
    outcome = inject_single_victim(
        col,
        victim_id=victim,
        spec=InjectionSpec(
            source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
            fraction=0.20,
            seed_pair=SeedPair(training_seed=0, poisoning_seed=100),
            objective=None,
        ),
    )
    work_col, work_pois = apply_defense(
        col,
        {cid: outcome.poisoned_cal_set[cid].cal for cid in outcome.poisoned_cal_set},
        defense=PoisoningDefense.TRIMMED_CALIBRATION,
        trim_fraction=0.05,
    )
    pair = recompute_pair(
        work_col,
        PoisonedCalibrationSet.from_mapping(work_pois),
        ThresholdPolicy.LOCAL_THRESHOLD,
    )
    assert math.isfinite(pair.thresholds_clean[victim])
    assert math.isfinite(pair.thresholds_pois[victim])


def test_defended_victim_still_eligible_after_trim() -> None:
    """Verify that victims are still eligible and coverage ratio remains close after trimming."""
    col = _make_collection()
    defended = build_defended_collection(col, 0.15)

    assert col.eligible_ids[0] in defended.eligible_ids
    assert math.isclose(defended.coverage_ratio, col.coverage_ratio)
