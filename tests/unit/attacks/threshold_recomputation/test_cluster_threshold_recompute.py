"""Tests for CLUSTER_THRESHOLD threshold recomputation and Δτ decomposition ."""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import pytest

from datp.artifacts.poison_names import THRESHOLD_QUANTILE
from datp.attacks.threshold_recomputation.cluster_threshold_recompute import (
    compute_cluster_pair,
)
from datp.attacks.injection.injector import inject_fixed_budget
from datp.attacks.reservoirs.reservoir import build_reservoir
from datp.attacks.score_containers import build_score_collection
from datp.attacks.enums import PoisoningSourceStrategy
from datp.core.seed_sequence import make_seed_rng
from datp.testsupport.synthetic_scores import make_standard_score_set


def _make_collection():
    """9 eligible + 1 pending (matches N-BaIoT 9-device default)."""
    ss = make_standard_score_set(n_eligible=9, n_pending=1)
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    return build_score_collection(raw)


def _make_poisoned_cal(col, victim_idx: int = 0, fraction: float = 0.40):
    """Inject HIGH_SCORE_BENIGN into one victim; return poisoned_cal dict."""
    eligible_ids = list(col.eligible_ids)
    victim_id = eligible_ids[victim_idx]
    victim_cal = col.clients[victim_id].cal
    reservoir = build_reservoir(
        clean_cal=victim_cal,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        tail_mass=0.10,
    )
    rng = make_seed_rng(
        training_seed=0, poisoning_seed=100, client_idx=victim_idx, scope_idx=0
    )
    inj = inject_fixed_budget(
        clean_cal=victim_cal, reservoir=reservoir, fraction=fraction, rng=rng
    )
    poisoned_cal = {
        cid: (inj.poisoned_cal if cid == victim_id else col.clients[cid].cal.copy())
        for cid in eligible_ids
    }
    return poisoned_cal, victim_id


class TestClusterThresholdPairBasics:
    def test_policy_is_cluster(self) -> None:
        col = _make_collection()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        assert pair.policy == ThresholdPolicy.CLUSTER_THRESHOLD

    def test_eligible_ids_in_result(self) -> None:
        col = _make_collection()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        assert set(pair.thresholds_clean.keys()) == set(col.eligible_ids)
        assert set(pair.thresholds_pois.keys()) == set(col.eligible_ids)

    def test_decomposition_covers_eligible(self) -> None:
        col = _make_collection()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        assert set(pair.decomposition.keys()) == set(col.eligible_ids)

    def test_pending_not_in_thresholds(self) -> None:
        col = _make_collection()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for pid in col.pending_ids:
            assert pid not in pair.thresholds_clean
            assert pid not in pair.thresholds_pois


class TestDecompositionIdentity:
    def test_delta_total_equals_agg_plus_churn(self) -> None:
        """Δτ_agg + Δτ_churn = Δτ_total exactly."""
        col = _make_collection()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for cid, entry in pair.decomposition.items():
            assert entry.delta_tau_total == pytest.approx(
                entry.delta_tau_agg + entry.delta_tau_churn, abs=1e-10
            ), f"Decomposition identity failed for {cid}"

    def test_delta_total_matches_effective_thresholds(self) -> None:
        col = _make_collection()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for cid, entry in pair.decomposition.items():
            expected = pair.thresholds_pois[cid] - pair.thresholds_clean[cid]
            assert entry.delta_tau_total == pytest.approx(expected, abs=1e-10)

    def test_tau_clean_matches_thresholds_clean(self) -> None:
        col = _make_collection()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for cid, entry in pair.decomposition.items():
            assert entry.tau_clean == pytest.approx(pair.thresholds_clean[cid])

    def test_tau_pois_matches_thresholds_pois(self) -> None:
        col = _make_collection()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for cid, entry in pair.decomposition.items():
            assert entry.tau_pois == pytest.approx(pair.thresholds_pois[cid])


class TestDecompositionFrozenScaler:
    def test_normalization_gap_identity(self) -> None:
        """Δτ_normalization_gap == Δτ_total - Δτ_frozen_scaler (exact identity)."""
        col = _make_collection()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for cid, entry in pair.decomposition.items():
            assert entry.delta_tau_normalization_gap == pytest.approx(
                entry.delta_tau_total - entry.delta_tau_frozen_scaler, abs=1e-10
            ), f"Normalization-gap identity failed for {cid}"

    def test_frozen_scaler_is_finite(self) -> None:
        col = _make_collection()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        import math
        for entry in pair.decomposition.values():
            assert math.isfinite(entry.delta_tau_frozen_scaler)
            assert math.isfinite(entry.delta_tau_normalization_gap)

    def test_f0_frozen_scaler_zero(self) -> None:
        """f=0 → frozen-scaler delta and normalization-gap must be zero."""
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for entry in pair.decomposition.values():
            assert entry.delta_tau_frozen_scaler == pytest.approx(0.0, abs=1e-10)
            assert entry.delta_tau_normalization_gap == pytest.approx(0.0, abs=1e-10)


class TestFractionZero:
    def test_f0_all_deltas_zero(self) -> None:
        """f=0 → poisoned_cal == clean_cal → all Δτ == 0."""
        col = _make_collection()
        # f=0: poisoned cal equals clean cal for all eligible
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for entry in pair.decomposition.values():
            assert entry.delta_tau_total == pytest.approx(0.0, abs=1e-10)
            assert entry.delta_tau_agg == pytest.approx(0.0, abs=1e-10)
            assert entry.delta_tau_churn == pytest.approx(0.0, abs=1e-10)
            assert entry.delta_tau_frozen_scaler == pytest.approx(0.0, abs=1e-10)
            assert entry.delta_tau_normalization_gap == pytest.approx(0.0, abs=1e-10)


class TestDeterminism:
    def test_same_inputs_same_result(self) -> None:
        col = _make_collection()
        pois_cal, _ = _make_poisoned_cal(col)
        p1 = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        p2 = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for cid in col.eligible_ids:
            assert p1.thresholds_clean[cid] == p2.thresholds_clean[cid]
            assert p1.thresholds_pois[cid] == p2.thresholds_pois[cid]
            assert (
                p1.decomposition[cid].delta_tau_total
                == p2.decomposition[cid].delta_tau_total
            )


class TestNoClientLabelComparison:
    def test_no_raw_cluster_label_in_decomp(self) -> None:
        """Verify that decomposition entries do not store raw cluster labels."""
        col = _make_collection()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for entry in pair.decomposition.values():
            # ClusterDecompEntry must not have a 'cluster_label' field.
            assert not hasattr(entry, "cluster_label"), (
                "Decomposition entries must not store raw cluster labels."
            )
