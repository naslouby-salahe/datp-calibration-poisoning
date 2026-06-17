from __future__ import annotations

from unittest import mock

import numpy as np
import pytest
from sklearn.cluster import KMeans as RealKMeans

from datp.core.enums import B4_FINGERPRINT_FEATURES, Baseline, Regime
from datp.core.identity import BaselineRunId, TrainingCellId
from datp.thresholding.strategies.b4_cluster import compute, compute_fingerprints


def _run(regime: Regime = Regime.A) -> BaselineRunId:
    return BaselineRunId(
        cell=TrainingCellId(regime=regime, seed=0, alpha=None), baseline=Baseline.B4
    )


def _make_errors(n: int, seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).exponential(scale=0.3, size=n).astype(np.float32)


@pytest.fixture()
def eligible_errors() -> dict[str, np.ndarray]:
    rng = np.random.default_rng(42)
    errors: dict[str, np.ndarray] = {
        f"c{i}": rng.exponential(scale=0.2 + i * 0.15, size=200).astype(np.float32)
        for i in range(5)
    }
    errors["pending"] = _make_errors(10, seed=99)
    return errors


N_MIN = 100


class TestB4FixedMode:
    def test_fixed_k3_returns_k3(self, eligible_errors: dict[str, np.ndarray]) -> None:
        result = compute(
            eligible_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            k_regime_a=3,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(Regime.A),
            regime=Regime.A,
        )
        assert result.metadata.b4 is not None
        assert result.metadata.b4.k == 3

    def test_fixed_k_pending_excluded(
        self, eligible_errors: dict[str, np.ndarray]
    ) -> None:
        result = compute(
            eligible_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            k_regime_a=3,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(Regime.A),
            regime=Regime.A,
        )
        assert result.metadata.b4 is not None
        assert "pending" not in result.metadata.b4.fingerprints


class TestB4SilhouetteMode:
    def test_silhouette_selects_valid_k(
        self, eligible_errors: dict[str, np.ndarray]
    ) -> None:
        result = compute(
            eligible_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            k_regime_a=0,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(Regime.A),
            regime=Regime.A,
        )
        assert result.metadata.b4 is not None
        assert result.metadata.b4.k in {2, 3, 4, 5}

    def test_silhouette_scores_non_empty(
        self, eligible_errors: dict[str, np.ndarray]
    ) -> None:
        result = compute(
            eligible_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            k_regime_a=0,
            k_candidates=[2, 3, 4],
            n_init=10,
            max_iter=300,
            run=_run(Regime.A),
            regime=Regime.A,
        )
        assert result.metadata.b4 is not None
        assert len(result.metadata.b4.silhouette_scores) > 0

    def test_invalid_k_skipped(self) -> None:
        errors = {f"c{i}": _make_errors(200, seed=i) for i in range(3)}
        result = compute(
            errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            k_regime_a=0,
            k_candidates=[2, 3, 100],  # k=100 >= n_eligible=3, will be skipped
            n_init=10,
            max_iter=300,
            run=_run(Regime.B),
            regime=Regime.B,
        )
        assert result.metadata.b4 is not None
        assert result.metadata.b4.k in {2, 3}


class TestB4FingerprintRobustness:
    def test_constant_errors_skew_is_zero(self) -> None:
        errors = {
            "c0": np.full(200, 0.5, dtype=np.float32),
            "c1": np.full(200, 0.3, dtype=np.float32),
        }
        fps = compute_fingerprints(errors, ["c0", "c1"], q=0.95)
        for cid, fp in fps.items():
            assert np.isfinite(fp).all(), (
                f"fingerprint for {cid} contains NaN/inf: {fp}"
            )
            # skew is the 3rd element (index 2)
            assert fp[2] == pytest.approx(0.0), (
                f"skew for {cid} should be 0.0, got {fp[2]}"
            )

    def test_near_constant_errors_finite_fingerprint(self) -> None:
        rng = np.random.default_rng(0)
        errors = {
            "c0": np.full(200, 0.01, dtype=np.float32)
            + rng.standard_normal(200).astype(np.float32) * 1e-7,
            "c1": np.full(200, 0.05, dtype=np.float32)
            + rng.standard_normal(200).astype(np.float32) * 1e-7,
        }
        fps = compute_fingerprints(errors, ["c0", "c1"], q=0.95)
        for cid, fp in fps.items():
            assert np.isfinite(fp).all(), (
                f"fingerprint for {cid} contains NaN/inf: {fp}"
            )

    def test_identical_fingerprints_raises_via_compute(self) -> None:
        errors = {
            "c0": np.full(200, 0.5, dtype=np.float32),
            "c1": np.full(200, 0.5, dtype=np.float32),  # identical to c0
        }
        # Two clients with identical errors → identical fingerprints → degenerate
        with pytest.raises(ValueError, match="Degenerate fingerprints"):
            compute(
                errors,
                n_min=N_MIN,
                tau_global=0.5,
                q=0.95,
                random_state=42,
                k_regime_a=0,
                k_candidates=[2, 3],
                n_init=10,
                max_iter=300,
                run=_run(Regime.B),
                regime=Regime.B,
            )

    def test_fingerprints_match_canonical_feature_order(self) -> None:
        errors = {
            "c0": np.random.default_rng(0)
            .exponential(0.3, size=200)
            .astype(np.float32),
            "c1": np.random.default_rng(1)
            .exponential(0.4, size=200)
            .astype(np.float32),
        }
        fps = compute_fingerprints(errors, ["c0", "c1"], q=0.95)
        for cid, fp in fps.items():
            assert len(fp) == len(B4_FINGERPRINT_FEATURES), (
                f"fingerprint for {cid} has {len(fp)} features, "
                f"expected {len(B4_FINGERPRINT_FEATURES)}"
            )
            assert np.isfinite(fp).all(), (
                f"fingerprint for {cid} contains NaN/inf: {fp}"
            )

    def test_pending_client_excluded_from_fingerprints(self) -> None:
        errors = {
            "eligible": np.random.default_rng(0)
            .exponential(0.3, size=200)
            .astype(np.float32),
            "pending": _make_errors(5, seed=99),  # 5 samples < n_min=100 → pending
        }
        fps = compute_fingerprints(errors, ["eligible"], q=0.95)
        assert "pending" not in fps
        assert "eligible" in fps

    def test_one_eligible_client_raises_before_clustering(self) -> None:
        errors = {
            "only_one": np.random.default_rng(0)
            .exponential(0.3, size=200)
            .astype(np.float32)
        }
        with pytest.raises(ValueError, match="Cannot cluster"):
            compute(
                errors,
                n_min=N_MIN,
                tau_global=0.5,
                q=0.95,
                random_state=42,
                k_regime_a=0,
                k_candidates=[2, 3],
                n_init=10,
                max_iter=300,
                run=_run(Regime.B),
                regime=Regime.B,
            )

    def test_calibration_pending_uses_tau_global(self) -> None:
        rng = np.random.default_rng(42)
        errors: dict[str, np.ndarray] = {
            f"c{i}": rng.exponential(scale=0.2 + i * 0.15, size=200).astype(np.float32)
            for i in range(4)
        }
        errors["pending"] = _make_errors(10, seed=99)
        tau_global = 0.99

        result = compute(
            errors,
            n_min=N_MIN,
            tau_global=tau_global,
            q=0.95,
            random_state=42,
            k_regime_a=0,
            k_candidates=[2, 3],
            n_init=10,
            max_iter=300,
            run=_run(Regime.B),
            regime=Regime.B,
        )
        pending_ct = next(
            ct for ct in result.client_thresholds if ct.calibration_pending
        )
        assert pending_ct.threshold == pytest.approx(tau_global)


class TestB4KMeansHyperparametersLocked:
    """Every KMeans constructor must receive the locked hyperparameters
    (K=3, n_init=10, max_iter=300, random_state=42)."""

    def test_kmeans_receives_locked_max_iter(
        self, eligible_errors: dict[str, np.ndarray]
    ) -> None:
        with mock.patch(
            "datp.thresholding.strategies.b4_cluster.KMeans",
            wraps=RealKMeans,
        ) as km_spy:
            compute(
                eligible_errors,
                n_min=N_MIN,
                tau_global=0.5,
                q=0.95,
                random_state=42,
                k_regime_a=3,
                k_candidates=[2, 3, 4, 5],
                n_init=10,
                max_iter=300,
                run=_run(Regime.A),
                regime=Regime.A,
            )

        assert km_spy.call_count >= 1
        for call in km_spy.call_args_list:
            assert call.kwargs["max_iter"] == 300
            assert call.kwargs["n_init"] == 10
            assert call.kwargs["random_state"] == 42
