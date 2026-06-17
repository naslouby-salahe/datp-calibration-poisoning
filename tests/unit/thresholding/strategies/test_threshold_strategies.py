from __future__ import annotations

import numpy as np
import pytest

from datp.core.enums import Baseline, Regime
from datp.core.identity import BaselineRunId, TrainingCellId
from datp.core.types import ThresholdResult
from datp.thresholding.eligibility import (
    compute_client_thresholds,
    identify_eligible,
)
from datp.thresholding.strategies import (
    b1_global as b1,
)
from datp.thresholding.strategies import (
    b2_personalized as b2,
)
from datp.thresholding.strategies import (
    b3_family as b3,
)
from datp.thresholding.strategies import (
    b4_cluster as b4,
)
from datp.thresholding.strategies.b4_cluster import compute_fingerprints


def _run(baseline: Baseline = Baseline.B1, regime: Regime = Regime.A) -> BaselineRunId:
    return BaselineRunId(
        cell=TrainingCellId(regime=regime, seed=0, alpha=None), baseline=baseline
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


class TestB1:
    def test_all_clients_get_tau_global(
        self, client_errors: dict[str, np.ndarray]
    ) -> None:
        result = b1.compute(client_errors, n_min=N_MIN, q=0.95, run=_run(Baseline.B1))
        assert isinstance(result, ThresholdResult)
        assert result.run.baseline == Baseline.B1
        for ct in result.client_thresholds:
            assert ct.threshold == pytest.approx(result.tau_global)

    def test_pending_flagged(self, client_errors: dict[str, np.ndarray]) -> None:
        result = b1.compute(client_errors, n_min=N_MIN, q=0.95, run=_run(Baseline.B1))
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
        result = b1.compute(client_errors, n_min=N_MIN, q=0.95, run=_run(Baseline.B1))
        assert result.tau_global == pytest.approx(expected)

    def test_arithmetic_mean_differs_from_pooled_percentile(self) -> None:
        errors = {
            "small_high": np.array([10.0, 11.0, 12.0], dtype=np.float64),
            "large_low": np.linspace(0.0, 1.0, 100, dtype=np.float64),
        }
        result = b1.compute(errors, n_min=1, q=0.95, run=_run(Baseline.B1))
        pooled = float(np.percentile(np.concatenate(list(errors.values())), 95))
        assert result.tau_global != pytest.approx(pooled)


class TestB2:
    def test_eligible_get_local_threshold(
        self, client_errors: dict[str, np.ndarray]
    ) -> None:
        tau_global = 0.42
        result = b2.compute(
            client_errors,
            n_min=N_MIN,
            tau_global=tau_global,
            q=0.95,
            run=_run(Baseline.B2),
        )
        eligible_cts = [
            ct for ct in result.client_thresholds if not ct.calibration_pending
        ]
        for ct in eligible_cts:
            expected = float(np.percentile(client_errors[ct.client_id], 95))
            assert ct.threshold == pytest.approx(expected)

    def test_pending_get_tau_global(self, client_errors: dict[str, np.ndarray]) -> None:
        tau_global = 0.42
        result = b2.compute(
            client_errors,
            n_min=N_MIN,
            tau_global=tau_global,
            q=0.95,
            run=_run(Baseline.B2),
        )
        pending_cts = [ct for ct in result.client_thresholds if ct.calibration_pending]
        for ct in pending_cts:
            assert ct.threshold == pytest.approx(tau_global)

    def test_tau_global_not_recomputed(
        self, client_errors: dict[str, np.ndarray]
    ) -> None:
        sentinel = 999.999
        result = b2.compute(
            client_errors,
            n_min=N_MIN,
            tau_global=sentinel,
            q=0.95,
            run=_run(Baseline.B2),
        )
        assert result.tau_global == pytest.approx(sentinel)

    def test_return_type(self, client_errors: dict[str, np.ndarray]) -> None:
        result = b2.compute(
            client_errors, n_min=N_MIN, tau_global=0.5, q=0.95, run=_run(Baseline.B2)
        )
        assert isinstance(result, ThresholdResult)
        assert result.run.baseline == Baseline.B2


class TestB3:
    @pytest.fixture()
    def family_map(self) -> dict[str, str]:
        return {
            "client_a": "cameras",
            "client_b": "cameras",
            "client_c": "doorbells",
            "client_d": "other",
        }

    def test_eligible_get_family_threshold(
        self, client_errors: dict[str, np.ndarray], family_map: dict[str, str]
    ) -> None:
        tau_global = 0.42
        result = b3.compute(
            client_errors,
            n_min=N_MIN,
            tau_global=tau_global,
            family_map=family_map,
            q=0.95,
            regime=Regime.A,
            run=_run(Baseline.B3),
        )

        eligible, _ = identify_eligible(client_errors, n_min=N_MIN)
        taus = compute_client_thresholds(client_errors, eligible, q=0.95)

        camera_taus = [taus[c] for c in eligible if family_map[c] == "cameras"]
        expected_camera_tau = sum(camera_taus) / len(camera_taus)

        ct_a = next(ct for ct in result.client_thresholds if ct.client_id == "client_a")
        ct_b = next(ct for ct in result.client_thresholds if ct.client_id == "client_b")
        assert ct_a.threshold == pytest.approx(expected_camera_tau)
        assert ct_b.threshold == pytest.approx(expected_camera_tau)

    def test_pending_get_tau_global_not_family(
        self, client_errors: dict[str, np.ndarray], family_map: dict[str, str]
    ) -> None:
        tau_global = 0.42
        result = b3.compute(
            client_errors,
            n_min=N_MIN,
            tau_global=tau_global,
            family_map=family_map,
            q=0.95,
            regime=Regime.A,
            run=_run(Baseline.B3),
        )
        ct_d = next(ct for ct in result.client_thresholds if ct.client_id == "client_d")
        assert ct_d.calibration_pending is True
        assert ct_d.threshold == pytest.approx(tau_global)

    def test_missing_family_raises(self, client_errors: dict[str, np.ndarray]) -> None:
        incomplete_map = {"client_a": "cameras"}
        with pytest.raises(ValueError, match="Missing family mapping"):
            b3.compute(
                client_errors,
                n_min=N_MIN,
                tau_global=0.5,
                family_map=incomplete_map,
                q=0.95,
                regime=Regime.A,
                run=_run(Baseline.B3),
            )

    def test_metadata_has_family_info(
        self, client_errors: dict[str, np.ndarray], family_map: dict[str, str]
    ) -> None:
        result = b3.compute(
            client_errors,
            n_min=N_MIN,
            tau_global=0.5,
            family_map=family_map,
            q=0.95,
            regime=Regime.A,
            run=_run(Baseline.B3),
        )
        assert result.metadata.b3 is not None
        assert "cameras" in result.metadata.b3.family_info

    def test_singleton_family_tau_equals_member_tau(
        self, client_errors: dict[str, np.ndarray], family_map: dict[str, str]
    ) -> None:
        result = b3.compute(
            client_errors,
            n_min=N_MIN,
            tau_global=999.0,
            family_map=family_map,
            q=0.95,
            regime=Regime.A,
            run=_run(Baseline.B3),
        )
        expected = float(np.percentile(client_errors["client_c"], 95))
        assert result.metadata.b3 is not None
        assert result.metadata.b3.family_info["doorbells"].singleton is True
        assert result.metadata.b3.family_info["doorbells"].tau_family == pytest.approx(
            expected
        )
        ct_c = next(ct for ct in result.client_thresholds if ct.client_id == "client_c")
        assert ct_c.threshold == pytest.approx(expected)


class TestB4Fingerprints:
    def test_four_scalars(self, client_errors: dict[str, np.ndarray]) -> None:
        eligible, _ = identify_eligible(client_errors, n_min=N_MIN)
        fps = compute_fingerprints(client_errors, eligible, q=0.95)
        for cid in eligible:
            assert fps[cid].shape == (4,)

    def test_pending_excluded(self, client_errors: dict[str, np.ndarray]) -> None:
        eligible, _ = identify_eligible(client_errors, n_min=N_MIN)
        fps = compute_fingerprints(client_errors, eligible, q=0.95)
        assert "client_d" not in fps


class TestB4:
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
            b4.compute(
                errors,
                n_min=N_MIN,
                tau_global=0.5,
                q=0.95,
                random_state=42,
                k_regime_a=3,
                k_candidates=[2, 3, 4, 5],
                n_init=10,
                max_iter=300,
                run=_run(Baseline.B4, regime=Regime.A),
                regime=Regime.A,
            )

    def test_regime_a_k_fixed_3(self, large_errors: dict[str, np.ndarray]) -> None:
        result = b4.compute(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            k_regime_a=3,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(Baseline.B4, regime=Regime.A),
            regime=Regime.A,
        )
        assert result.metadata.b4 is not None
        assert result.metadata.b4.k == 3

    def test_regime_a_supports_silhouette_k_selection(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        result = b4.compute(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            k_regime_a=0,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(Baseline.B4, regime=Regime.A),
            regime=Regime.A,
        )
        assert result.metadata.b4 is not None
        assert result.metadata.b4.k in {2, 3, 4, 5}
        assert result.metadata.b4.silhouette_scores

    def test_regime_b_silhouette_selection(
        self,
        large_errors: dict[str, np.ndarray],
    ) -> None:
        import structlog.testing

        with structlog.testing.capture_logs() as cap:
            result = b4.compute(
                large_errors,
                n_min=N_MIN,
                tau_global=0.5,
                q=0.95,
                random_state=42,
                k_regime_a=3,
                k_candidates=[2, 3, 4, 5],
                n_init=10,
                max_iter=300,
                run=_run(Baseline.B4, regime=Regime.B),
                regime=Regime.B,
            )
        assert result.metadata.b4 is not None
        assert result.metadata.b4.k in {2, 3, 4, 5}
        assert result.metadata.b4.silhouette is not None
        assert any("silhouette" in entry.get("event", "").lower() for entry in cap)

    def test_pending_get_tau_global_not_cluster(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        tau_global = 0.42
        result = b4.compute(
            large_errors,
            n_min=N_MIN,
            tau_global=tau_global,
            q=0.95,
            random_state=42,
            k_regime_a=3,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(Baseline.B4, regime=Regime.A),
            regime=Regime.A,
        )
        ct_pending = next(
            ct for ct in result.client_thresholds if ct.client_id == "pending"
        )
        assert ct_pending.calibration_pending is True
        assert ct_pending.threshold == pytest.approx(tau_global)

    def test_eligible_never_pending_in_cluster(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        result = b4.compute(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            k_regime_a=3,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(Baseline.B4, regime=Regime.A),
            regime=Regime.A,
        )
        for ct in result.client_thresholds:
            if ct.client_id == "pending":
                assert ct.calibration_pending is True
            else:
                assert ct.calibration_pending is False

    def test_invalid_regime_type_raises(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        with pytest.raises(TypeError, match="requires regime as Regime enum"):
            b4.compute(
                large_errors,
                n_min=N_MIN,
                tau_global=0.5,
                q=0.95,
                random_state=42,
                k_regime_a=3,
                k_candidates=[2, 3, 4, 5],
                n_init=10,
                max_iter=300,
                run=_run(Baseline.B4, regime=Regime.A),
                regime="X",  # type: ignore[arg-type]
            )

    def test_return_type(self, large_errors: dict[str, np.ndarray]) -> None:
        result = b4.compute(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            k_regime_a=3,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(Baseline.B4, regime=Regime.A),
            regime=Regime.A,
        )
        assert isinstance(result, ThresholdResult)
        assert result.run.baseline == Baseline.B4
        assert result.metadata.b4 is not None
        assert result.metadata.b4.cluster_info

    def test_cluster_metadata_complete(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        result = b4.compute(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            k_regime_a=3,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(Baseline.B4, regime=Regime.A),
            regime=Regime.A,
        )
        assert result.metadata.b4 is not None
        cluster_info = result.metadata.b4.cluster_info
        total_eligible = sum(len(info.members) for info in cluster_info.values())
        assert total_eligible == result.eligible_count

    def test_pending_absent_from_fingerprints_metadata(
        self, large_errors: dict[str, np.ndarray]
    ) -> None:
        result = b4.compute(
            large_errors,
            n_min=N_MIN,
            tau_global=0.5,
            q=0.95,
            random_state=42,
            k_regime_a=3,
            k_candidates=[2, 3, 4, 5],
            n_init=10,
            max_iter=300,
            run=_run(Baseline.B4, regime=Regime.A),
            regime=Regime.A,
        )
        assert result.metadata.b4 is not None
        assert "pending" not in result.metadata.b4.fingerprints
