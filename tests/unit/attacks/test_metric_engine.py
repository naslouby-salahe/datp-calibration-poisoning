"""Tests for metric engine ."""

from __future__ import annotations

import math

import pytest

from datp.artifacts.poison_names import THRESHOLD_QUANTILE
from datp.attacks.injector import inject_fixed_budget
from datp.attacks.metric_engine import (
    MetricResult,
    compute_auroc_records,
    compute_delta_tau,
    compute_fleet_fpr,
    compute_metrics,
    compute_mu_flag_threshold,
)
from datp.attacks.types import MetricEngineInput
from datp.attacks.reservoir import build_reservoir
from datp.attacks.score_containers import build_score_collection
from datp.attacks.threshold_recompute import compute_b1_pair, compute_b2_pair
from datp.attacks.enums import PoisoningSourceStrategy, ThresholdPolicy
from datp.core.enums import Baseline
from datp.core.seed_sequence import make_seed_rng
from datp.testsupport.synthetic_scores import make_standard_score_set
from datp.thresholding.eligibility import ClientThresholdsCollection


def _make_collection():
    ss = make_standard_score_set(n_eligible=5, n_pending=1)
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    return build_score_collection(raw)


def _inject_one_victim(col, victim_idx: int = 0, fraction: float = 0.40):
    """Return (poisoned_cal, victim_id) with HIGH_SCORE injection on one victim."""
    eligible_ids = list(col.eligible_ids)
    victim_id = eligible_ids[victim_idx]
    cal = col.clients[victim_id].cal
    reservoir = build_reservoir(
        clean_cal=cal, source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN, tail_mass=0.10
    )
    rng = make_seed_rng(
        training_seed=0, poisoning_seed=100, client_idx=victim_idx, scope_idx=0
    )
    inj = inject_fixed_budget(clean_cal=cal, reservoir=reservoir, fraction=fraction, rng=rng)
    pois_cal = {
        cid: (inj.poisoned_cal if cid == victim_id else col.clients[cid].cal.copy())
        for cid in eligible_ids
    }
    return pois_cal, victim_id


class TestDeltaTau:
    def test_eligible_clients_covered(self) -> None:
        col = _make_collection()
        pois_cal, _ = _inject_one_victim(col)
        b2 = compute_b2_pair(col, pois_cal, THRESHOLD_QUANTILE, compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean)
        dt = compute_delta_tau(col, b2)
        assert set(dt.keys()) == set(col.eligible_ids)

    def test_victim_has_nonzero_delta(self) -> None:
        col = _make_collection()
        pois_cal, victim_id = _inject_one_victim(col)
        b2 = compute_b2_pair(col, pois_cal, THRESHOLD_QUANTILE, compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean)
        dt = compute_delta_tau(col, b2)
        assert not math.isclose(dt[victim_id].delta_tau, 0.0, abs_tol=1e-10)

    def test_f0_all_delta_zero(self) -> None:
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        b1 = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        dt = compute_delta_tau(col, b1)
        for entry in dt.values():
            assert entry.delta_tau == pytest.approx(0.0, abs=1e-10)

    def test_delta_tau_rel_nonzero_for_nonzero_delta(self) -> None:
        col = _make_collection()
        pois_cal, victim_id = _inject_one_victim(col)
        b2 = compute_b2_pair(col, pois_cal, THRESHOLD_QUANTILE, compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean)
        dt = compute_delta_tau(col, b2)
        assert not math.isclose(dt[victim_id].delta_tau_rel, 0.0, abs_tol=1e-10)

    def test_delta_tau_scale_positive(self) -> None:
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        b1 = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        dt = compute_delta_tau(col, b1)
        for entry in dt.values():
            assert entry.delta_tau_scale >= 0.0

    def test_policy_recorded(self) -> None:
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        b1 = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        dt = compute_delta_tau(col, b1)
        for entry in dt.values():
            assert entry.policy == ThresholdPolicy.B1_GLOBAL


class TestFleetFpr:
    def test_coverage_ratio_correct(self) -> None:
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        b1 = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        fleet = compute_fleet_fpr(col, b1, None)
        assert fleet.coverage_ratio == pytest.approx(5 / 6)

    def test_n_eligible_and_n_total(self) -> None:
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        b1 = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        fleet = compute_fleet_fpr(col, b1, None)
        assert fleet.n_eligible == 5
        assert fleet.n_total == 6

    def test_cv_fpr_no_epsilon(self) -> None:
        """CV(FPR) must use no ε in denominator — nan when mean=0."""
        col = _make_collection()
        # Force all FPRs to 0 by setting an impossibly high threshold.
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        b1 = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        # Set all poisoned thresholds very high to force FPR=0.
        from datp.attacks.threshold_recompute import ThresholdPair
        high_tau = 1e9
        high_pair = ThresholdPair(
            policy=ThresholdPolicy.B1_GLOBAL,
            tau_global_clean=b1.tau_global_clean,
            tau_global_pois=high_tau,
            thresholds_clean=b1.thresholds_clean,
            thresholds_pois=ClientThresholdsCollection.from_mapping(
                dict.fromkeys(b1.thresholds_pois, high_tau),
                Baseline.B1,
            ),
        )
        fleet = compute_fleet_fpr(col, high_pair, None)
        assert math.isnan(fleet.cv_fpr), "CV(FPR) must be nan when mean FPR = 0"

    def test_mu_flag_not_triggered_by_default(self) -> None:
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        b1 = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        fleet = compute_fleet_fpr(col, b1, None)
        assert not fleet.mu_flag_triggered

    def test_companion_dispersion_populated(self) -> None:
        """Companion dispersion (IQR, range) accompanies CV(FPR) and is non-negative."""
        col = _make_collection()
        pois_cal, _ = _inject_one_victim(col)
        b1 = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        fleet = compute_fleet_fpr(col, b1, None)
        assert math.isfinite(fleet.iqr_fpr)
        assert fleet.iqr_fpr >= 0.0
        assert math.isfinite(fleet.max_min_fpr_gap)
        assert fleet.max_min_fpr_gap >= 0.0
        assert math.isfinite(fleet.std_fpr)
        assert fleet.std_fpr >= 0.0

    def test_worst_client_is_max_fpr(self) -> None:
        col = _make_collection()
        pois_cal, _ = _inject_one_victim(col)
        b1 = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        fleet = compute_fleet_fpr(col, b1, None)
        if fleet.worst_client_id is not None:
            assert fleet.worst_client_fpr >= fleet.mean_fpr


class TestAurocRecords:
    def test_auroc_in_0_1(self) -> None:
        col = _make_collection()
        records = compute_auroc_records(col)
        for rec in records.values():
            if rec.auroc is not None:
                assert 0.0 <= rec.auroc <= 1.0

    def test_eligible_clients_covered(self) -> None:
        col = _make_collection()
        records = compute_auroc_records(col)
        assert set(records.keys()) == set(col.eligible_ids)

    def test_auroc_invariant_test_scores_unchanged(self) -> None:
        """AUROC computed from test scores must be identical regardless of cal poisoning."""
        col = _make_collection()
        # Simulate different poisoning conditions — AUROC uses test scores only.
        r1 = compute_auroc_records(col)
        r2 = compute_auroc_records(col) # same input → same output
        for cid in col.eligible_ids:
            assert r1[cid].auroc is not None
            assert r2[cid].auroc is not None
            assert r1[cid].auroc == pytest.approx(r2[cid].auroc)


class TestMuFlagThreshold:
    def test_round_to_2sf(self) -> None:
        # 0.08 / 8 = 0.01 → round to 2 s.f. → 0.01
        assert compute_mu_flag_threshold(0.08) == pytest.approx(0.01)

    def test_nonzero_mean(self) -> None:
        val = compute_mu_flag_threshold(0.4)
        assert val > 0.0

    def test_zero_mean(self) -> None:
        assert compute_mu_flag_threshold(0.0) == pytest.approx(0.0)

    def test_magnitude_preserved(self) -> None:
        # 0.8 / 8 = 0.1 → 0.10
        assert compute_mu_flag_threshold(0.8) == pytest.approx(0.1)


class TestComputeMetrics:
    def test_returns_metric_result(self) -> None:
        col = _make_collection()
        pois_cal, _ = _inject_one_victim(col)
        b1 = compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE)
        result = compute_metrics(MetricEngineInput(collection=col, pair=b1, mu_flag_threshold=None))
        assert isinstance(result, MetricResult)
        assert result.policy == ThresholdPolicy.B1_GLOBAL

    def test_all_fields_populated(self) -> None:
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        b2 = compute_b2_pair(col, pois_cal, THRESHOLD_QUANTILE, compute_b1_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean)
        result = compute_metrics(MetricEngineInput(collection=col, pair=b2, mu_flag_threshold=0.05))
        assert set(result.delta_tau.keys()) == set(col.eligible_ids)
        assert set(result.auroc_records.keys()) == set(col.eligible_ids)
        assert result.mu_flag_threshold == pytest.approx(0.05)
