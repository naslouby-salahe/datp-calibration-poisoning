"""Unit tests for CLUSTER_THRESHOLD recomputation and decomposition logic."""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

import pytest

from datp.attacks.constants import THRESHOLD_QUANTILE
from datp.attacks.threshold_recomputation.cluster_threshold_recompute import (
    compute_cluster_pair,
)
from datp.attacks.injection.injector import inject_fixed_budget
from datp.attacks.reservoirs.reservoir import build_reservoir
from datp.attacks.score_containers import build_score_collection
from datp.attacks.enums import PoisoningSourceStrategy
from datp.core.seeds import SeedRecord, make_seed_rng
from datp.core.seeds import SeedPair
from datp.testsupport.synthetic_scores import (
    StandardScoreSetRequest,
    make_standard_score_set,
)


def _make_collection():

    ss = make_standard_score_set(StandardScoreSetRequest(n_eligible=9, n_pending=1))
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    return build_score_collection(raw)


def _make_poisoned_cal(col, victim_idx: int = 0, fraction: float = 0.40):

    eligible_ids = list(col.eligible_ids)
    victim_id = eligible_ids[victim_idx]
    victim_cal = col.clients[victim_id].cal
    reservoir = build_reservoir(
        clean_cal=victim_cal,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        tail_mass=0.10,
    )
    rng = make_seed_rng(
        SeedRecord(
            pair=SeedPair(training_seed=0, poisoning_seed=100),
            client_idx=victim_idx,
            scope_idx=0,
        )
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
    """ClusterThresholdPair construction and basic properties."""

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
    """Delta decomposition sums to total."""

    def test_delta_total_equals_agg_plus_churn(self) -> None:

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
    """Decomposition uses a frozen scaler for reproducibility."""

    def test_normalization_gap_identity(self) -> None:

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

        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for entry in pair.decomposition.values():
            assert entry.delta_tau_frozen_scaler == pytest.approx(0.0, abs=1e-10)
            assert entry.delta_tau_normalization_gap == pytest.approx(0.0, abs=1e-10)


class TestFractionZero:
    """Zero-fraction poisoning produces zero delta."""

    def test_f0_all_deltas_zero(self) -> None:

        col = _make_collection()

        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for entry in pair.decomposition.values():
            assert entry.delta_tau_total == pytest.approx(0.0, abs=1e-10)
            assert entry.delta_tau_agg == pytest.approx(0.0, abs=1e-10)
            assert entry.delta_tau_churn == pytest.approx(0.0, abs=1e-10)
            assert entry.delta_tau_frozen_scaler == pytest.approx(0.0, abs=1e-10)
            assert entry.delta_tau_normalization_gap == pytest.approx(0.0, abs=1e-10)


class TestDeterminism:
    """Identical inputs produce identical cluster threshold recomputation."""

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
    """Cluster assignment uses scores only, never client labels."""

    def test_no_raw_cluster_label_in_decomp(self) -> None:

        col = _make_collection()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for entry in pair.decomposition.values():
            assert not hasattr(entry, "cluster_label"), (
                "Decomposition entries must not store raw cluster labels."
            )
