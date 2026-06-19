"""Tests for B1/B2 threshold recomputation under poisoning ."""

from __future__ import annotations

import numpy as np
import pytest

from datp.artifacts.poison_names import THRESHOLD_QUANTILE
from datp.attacks.injector import inject_fixed_budget
from datp.attacks.reservoir import build_reservoir
from datp.attacks.score_containers import build_score_collection
from datp.attacks.threshold_recompute import (
    compute_b1_pair,
    compute_b2_pair,
)
from datp.attacks.enums import (
    PoisoningSourceStrategy,
    ThresholdPolicy,
)
from datp.core.seed_sequence import make_seed_rng
from datp.testsupport.synthetic_scores import make_standard_score_set


def _make_collection_and_pois_cal(
    victim_idx: int = 0, fraction: float = 0.40
) -> tuple:
    """Build a score collection and a poisoned cal dict for one victim."""
    ss = make_standard_score_set(n_eligible=3, n_pending=1)
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    col = build_score_collection(raw)

    eligible_ids = list(col.eligible_ids)
    victim_id = eligible_ids[victim_idx]
    victim_cal = col.clients[victim_id].cal

    # Build HIGH_SCORE reservoir to ensure threshold raise.
    reservoir = build_reservoir(
        clean_cal=victim_cal,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        tail_mass=0.10,
    )
    rng = make_seed_rng(
        training_seed=0, poisoning_seed=100, client_idx=victim_idx, scope_idx=0
    )
    injection = inject_fixed_budget(
        clean_cal=victim_cal, reservoir=reservoir, fraction=fraction, rng=rng
    )

    # Poisoned cal: victim gets poisoned; others stay clean.
    poisoned_cal: dict[str, np.ndarray] = {}
    for cid in eligible_ids:
        if cid == victim_id:
            poisoned_cal[cid] = injection.poisoned_cal
        else:
            poisoned_cal[cid] = col.clients[cid].cal

    return col, poisoned_cal, victim_id


class TestB1Pair:
    def test_policy_is_b1(self) -> None:
        col, pois_cal, _ = _make_collection_and_pois_cal()
        pair = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        assert pair.policy == ThresholdPolicy.B1_GLOBAL

    def test_tau_global_pois_differs_from_clean(self) -> None:
        col, pois_cal, _ = _make_collection_and_pois_cal()
        pair = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        # HIGH_SCORE injection should raise the global threshold.
        assert pair.tau_global_pois > pair.tau_global_clean

    def test_all_eligible_share_tau_global_b1(self) -> None:
        col, pois_cal, _ = _make_collection_and_pois_cal()
        pair = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for tau in pair.thresholds_clean.values():
            assert tau == pair.tau_global_clean
        for tau in pair.thresholds_pois.values():
            assert tau == pair.tau_global_pois

    def test_eligible_ids_in_result(self) -> None:
        col, pois_cal, _ = _make_collection_and_pois_cal()
        pair = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        assert set(pair.thresholds_clean.keys()) == set(col.eligible_ids)
        assert set(pair.thresholds_pois.keys()) == set(col.eligible_ids)

    def test_clean_reproducible(self) -> None:
        col, pois_cal, _ = _make_collection_and_pois_cal()
        p1 = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        p2 = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        assert p1.tau_global_clean == p2.tau_global_clean

    def test_f0_pair_equals_clean(self) -> None:
        """f=0 injection → poisoned cal equals clean → tau_global_pois == tau_global_clean."""
        ss = make_standard_score_set(n_eligible=3, n_pending=1)
        raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
        col = build_score_collection(raw)
        # Poisoned cal is just the clean cal (f=0 case).
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        pair = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        assert pair.tau_global_pois == pytest.approx(pair.tau_global_clean)


class TestB2Pair:
    def test_policy_is_b2(self) -> None:
        col, pois_cal, _ = _make_collection_and_pois_cal()
        tau_g = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean
        pair = compute_b2_pair(col, pois_cal, THRESHOLD_QUANTILE, tau_g)
        assert pair.policy == ThresholdPolicy.B2_PERSONALIZED

    def test_only_victim_threshold_changes(self) -> None:
        col, pois_cal, victim_id = _make_collection_and_pois_cal(victim_idx=0)
        tau_g = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean
        pair = compute_b2_pair(col, pois_cal, THRESHOLD_QUANTILE, tau_g)
        for cid in col.eligible_ids:
            if cid != victim_id:
                assert pair.thresholds_clean[cid] == pytest.approx(
                    pair.thresholds_pois[cid]
                ), f"Non-victim {cid!r} threshold should not change"

    def test_victim_threshold_raised(self) -> None:
        col, pois_cal, victim_id = _make_collection_and_pois_cal(victim_idx=0)
        tau_g = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean
        pair = compute_b2_pair(col, pois_cal, THRESHOLD_QUANTILE, tau_g)
        # HIGH_SCORE injection on victim should raise victim's threshold.
        assert pair.thresholds_pois[victim_id] > pair.thresholds_clean[victim_id]

    def test_eligible_ids_in_result(self) -> None:
        col, pois_cal, _ = _make_collection_and_pois_cal()
        tau_g = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean
        pair = compute_b2_pair(col, pois_cal, THRESHOLD_QUANTILE, tau_g)
        assert set(pair.thresholds_clean.keys()) == set(col.eligible_ids)
        assert set(pair.thresholds_pois.keys()) == set(col.eligible_ids)

    def test_f0_pair_equals_clean(self) -> None:
        ss = make_standard_score_set(n_eligible=3, n_pending=1)
        raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
        col = build_score_collection(raw)
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        tau_g = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean
        pair = compute_b2_pair(col, pois_cal, THRESHOLD_QUANTILE, tau_g)
        for cid in col.eligible_ids:
            assert pair.thresholds_clean[cid] == pytest.approx(
                pair.thresholds_pois[cid]
            )


class TestNoPendingMutation:
    def test_pending_not_in_threshold_dicts(self) -> None:
        col, pois_cal, _ = _make_collection_and_pois_cal()
        pair = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for pid in col.pending_ids:
            assert pid not in pair.thresholds_clean
            assert pid not in pair.thresholds_pois
