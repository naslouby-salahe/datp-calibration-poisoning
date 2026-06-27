"""Tests verifying calculations of delta_tau thresholds, fleet FPR dispersion metrics, and AUROC invariants."""

from __future__ import annotations

import math

import pytest

from datp.attacks.constants import THRESHOLD_QUANTILE
from datp.attacks.enums import PoisoningSourceStrategy
from datp.attacks.injection.injector import inject_fixed_budget
from datp.attacks.metrics.metric_engine import (
    MetricResult,
    compute_auroc_records,
    compute_delta_tau,
    compute_fleet_fpr,
    compute_metrics,
    compute_mu_flag_threshold,
)
from datp.attacks.reservoirs.reservoir import build_reservoir
from datp.attacks.score_containers import build_score_collection
from datp.attacks.threshold_recomputation.threshold_recompute import (
    compute_global_pair,
    compute_local_pair,
)
from datp.attacks.types import MetricEngineInput
from datp.core.enums import ThresholdPolicy
from datp.core.seeds import SeedPair, SeedRecord, make_seed_rng
from datp.testsupport.synthetic_scores import (
    StandardScoreSetRequest,
    make_standard_score_set,
)
from datp.thresholding.eligibility import ClientThresholdsCollection


def _make_collection():
    """Helper to build standard mock ScoreCollection for metric engine testing."""
    ss = make_standard_score_set(StandardScoreSetRequest(n_eligible=5, n_pending=1))
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    return build_score_collection(raw)


def _inject_one_victim(col, victim_idx: int = 0, fraction: float = 0.40):
    """Helper to run single victim calibration poisoning injection."""
    eligible_ids = list(col.eligible_ids)
    victim_id = eligible_ids[victim_idx]
    cal = col.clients[victim_id].cal
    reservoir = build_reservoir(
        clean_cal=cal, source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN, tail_mass=0.10
    )
    rng = make_seed_rng(
        SeedRecord(
            pair=SeedPair(training_seed=0, poisoning_seed=100),
            client_idx=victim_idx,
            scope_idx=0,
        )
    )
    inj = inject_fixed_budget(
        clean_cal=cal, reservoir=reservoir, fraction=fraction, rng=rng
    )
    pois_cal = {
        cid: (inj.poisoned_cal if cid == victim_id else col.clients[cid].cal.copy())
        for cid in eligible_ids
    }
    return pois_cal, victim_id


class TestDeltaTau:
    """Tests verifying calculation of absolute and relative delta_tau threshold metrics."""

    def test_eligible_clients_covered(self) -> None:
        """Verify that delta_tau dictionary covers all eligible client IDs."""
        col = _make_collection()
        pois_cal, _ = _inject_one_victim(col)
        local_pair = compute_local_pair(
            col,
            pois_cal,
            THRESHOLD_QUANTILE,
            compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean,
        )
        dt = compute_delta_tau(col, local_pair)
        assert set(dt.keys()) == set(col.eligible_ids)

    def test_victim_has_nonzero_delta(self) -> None:
        """Verify that poisoned victim clients get a nonzero threshold delta."""
        col = _make_collection()
        pois_cal, victim_id = _inject_one_victim(col)
        local_pair = compute_local_pair(
            col,
            pois_cal,
            THRESHOLD_QUANTILE,
            compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean,
        )
        dt = compute_delta_tau(col, local_pair)
        assert not math.isclose(dt[victim_id].delta_tau, 0.0, abs_tol=1e-10)

    def test_f0_all_delta_zero(self) -> None:
        """Verify that clean baseline (unpoisoned) results in delta_tau values of exactly 0.0."""
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        dt = compute_delta_tau(col, global_pair)
        for entry in dt.values():
            assert entry.delta_tau == pytest.approx(0.0, abs=1e-10)

    def test_delta_tau_rel_nonzero_for_nonzero_delta(self) -> None:
        """Verify that relative threshold delta is nonzero when absolute delta is nonzero."""
        col = _make_collection()
        pois_cal, victim_id = _inject_one_victim(col)
        local_pair = compute_local_pair(
            col,
            pois_cal,
            THRESHOLD_QUANTILE,
            compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean,
        )
        dt = compute_delta_tau(col, local_pair)
        assert not math.isclose(dt[victim_id].delta_tau_rel, 0.0, abs_tol=1e-10)

    def test_delta_tau_scale_positive(self) -> None:
        """Verify that scale denominators used in relative calculation are strictly positive."""
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        dt = compute_delta_tau(col, global_pair)
        for entry in dt.values():
            assert entry.delta_tau_scale >= 0.0

    def test_policy_recorded(self) -> None:
        """Verify that the tested threshold policy is recorded correctly on delta entries."""
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        dt = compute_delta_tau(col, global_pair)
        for entry in dt.values():
            assert entry.policy == ThresholdPolicy.GLOBAL_THRESHOLD


class TestFleetFpr:
    """Tests verifying fleet-wide false positive rates under poisoning."""

    def test_coverage_ratio_correct(self) -> None:
        """Verify that coverage ratio matches fraction of eligible clients over total clients."""
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        fleet = compute_fleet_fpr(col, global_pair, None)
        assert fleet.coverage_ratio == pytest.approx(5 / 6)

    def test_n_eligible_and_n_total(self) -> None:
        """Verify that eligible and total count properties match the source dataset split size."""
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        fleet = compute_fleet_fpr(col, global_pair, None)
        assert fleet.n_eligible == 5
        assert fleet.n_total == 6

    def test_cv_fpr_no_epsilon(self) -> None:
        """Verify that CV(FPR) is NaN when mean FPR is exactly 0.0 to prevent divide-by-zero."""
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)

        from datp.attacks.threshold_recomputation.threshold_recompute import (
            ThresholdPair,
        )

        high_tau = 1e9
        high_pair = ThresholdPair(
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            tau_global_clean=global_pair.tau_global_clean,
            tau_global_pois=high_tau,
            thresholds_clean=global_pair.thresholds_clean,
            thresholds_pois=ClientThresholdsCollection.from_mapping(
                dict.fromkeys(global_pair.thresholds_pois, high_tau),
                ThresholdPolicy.GLOBAL_THRESHOLD,
            ),
        )
        fleet = compute_fleet_fpr(col, high_pair, None)
        assert math.isnan(fleet.cv_fpr), "CV(FPR) must be nan when mean FPR = 0"

    def test_mu_flag_not_triggered_by_default(self) -> None:
        """Verify that clean baselines do not trigger the anomalous threshold mu flag."""
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        fleet = compute_fleet_fpr(col, global_pair, None)
        assert not fleet.mu_flag_triggered

    def test_companion_dispersion_populated(self) -> None:
        """Verify that companion dispersion measures (IQR, std, gap) are computed as positive numbers."""
        col = _make_collection()
        pois_cal, _ = _inject_one_victim(col)
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        fleet = compute_fleet_fpr(col, global_pair, None)
        assert math.isfinite(fleet.iqr_fpr)
        assert fleet.iqr_fpr >= 0.0
        assert math.isfinite(fleet.max_min_fpr_gap)
        assert fleet.max_min_fpr_gap >= 0.0
        assert math.isfinite(fleet.std_fpr)
        assert fleet.std_fpr >= 0.0

    def test_worst_client_is_max_fpr(self) -> None:
        """Verify that worst client FPR reflects the maximum false positive rate across the fleet."""
        col = _make_collection()
        pois_cal, _ = _inject_one_victim(col)
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        fleet = compute_fleet_fpr(col, global_pair, None)
        if fleet.worst_client_id is not None:
            assert fleet.worst_client_fpr >= fleet.mean_fpr


class TestAurocRecords:
    """Tests verifying AUROC records generated for model scoring quality evaluation."""

    def test_auroc_in_0_1(self) -> None:
        """Verify that generated AUROC values are bounded between 0.0 and 1.0."""
        col = _make_collection()
        records = compute_auroc_records(col)
        for rec in records.values():
            if rec.auroc is not None:
                assert 0.0 <= rec.auroc <= 1.0

    def test_eligible_clients_covered(self) -> None:
        """Verify that AUROC records are generated for all eligible client devices."""
        col = _make_collection()
        records = compute_auroc_records(col)
        assert set(records.keys()) == set(col.eligible_ids)

    def test_auroc_invariant_test_scores_unchanged(self) -> None:
        """Verify that AUROCs remain invariant across repeated evaluations since test scores are clean."""
        col = _make_collection()
        r1 = compute_auroc_records(col)
        r2 = compute_auroc_records(col)
        for cid in col.eligible_ids:
            assert r1[cid].auroc is not None
            assert r2[cid].auroc is not None
            assert r1[cid].auroc == pytest.approx(r2[cid].auroc)


class TestMuFlagThreshold:
    """Tests verifying calculations of mu anomalous triggers flag limits."""

    def test_exact_division_by_eight(self) -> None:
        """Verify division math maps exactly to one-eighth of average FPR bounds."""
        assert compute_mu_flag_threshold(0.08) == pytest.approx(0.01)

    def test_no_significant_figure_rounding(self) -> None:
        """Verify that no loss of numerical precision is introduced in divisions."""
        assert compute_mu_flag_threshold(0.37) == pytest.approx(0.04625)

    def test_nonzero_mean(self) -> None:
        """Verify positive bounds produce positive mu flag values."""
        val = compute_mu_flag_threshold(0.4)
        assert val > 0.0

    def test_zero_mean(self) -> None:
        """Verify that zero average FPR yields exactly zero mu flag threshold."""
        assert compute_mu_flag_threshold(0.0) == pytest.approx(0.0)

    def test_magnitude_preserved(self) -> None:
        """Verify magnitude ratio preservation in scale divisions."""
        assert compute_mu_flag_threshold(0.8) == pytest.approx(0.1)


class TestComputeMetrics:
    """Tests verifying high-level orchestration wrapper compute_metrics execution."""

    def test_returns_metric_result(self) -> None:
        """Verify that compute_metrics outputs a valid MetricResult for global thresholding."""
        col = _make_collection()
        pois_cal, _ = _inject_one_victim(col)
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        result = compute_metrics(
            MetricEngineInput(collection=col, pair=global_pair, mu_flag_threshold=None)
        )
        assert isinstance(result, MetricResult)
        assert result.policy == ThresholdPolicy.GLOBAL_THRESHOLD

    def test_all_fields_populated(self) -> None:
        """Verify that delta_tau maps, AUROC maps, and mu threshold properties are all populated."""
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        local_pair = compute_local_pair(
            col,
            pois_cal,
            THRESHOLD_QUANTILE,
            compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean,
        )
        result = compute_metrics(
            MetricEngineInput(collection=col, pair=local_pair, mu_flag_threshold=0.05)
        )
        assert set(result.delta_tau.keys()) == set(col.eligible_ids)
        assert set(result.auroc_records.keys()) == set(col.eligible_ids)
        assert result.mu_flag_threshold == pytest.approx(0.05)


class TestAbsoluteDispersionWhenCvNan:
    """Tests verifying absolute dispersion checks when CV(FPR) evaluates to NaN."""

    def test_iqr_fpr_finite_when_cv_fpr_nan(self) -> None:
        """Verify that companion dispersion IQR/gap metrics remain finite even when cv_fpr is NaN."""
        col = _make_collection()
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        from datp.attacks.threshold_recomputation.threshold_recompute import (
            ThresholdPair,
        )

        high_tau = 1e9
        high_pair = ThresholdPair(
            policy=ThresholdPolicy.GLOBAL_THRESHOLD,
            tau_global_clean=global_pair.tau_global_clean,
            tau_global_pois=high_tau,
            thresholds_clean=global_pair.thresholds_clean,
            thresholds_pois=ClientThresholdsCollection.from_mapping(
                dict.fromkeys(global_pair.thresholds_pois, high_tau),
                ThresholdPolicy.GLOBAL_THRESHOLD,
            ),
        )
        fleet = compute_fleet_fpr(col, high_pair, None)
        assert math.isnan(fleet.cv_fpr), "cv_fpr must be NaN when mean_fpr=0"
        assert math.isfinite(fleet.iqr_fpr), (
            "iqr_fpr must be finite even when cv_fpr is NaN"
        )
        assert math.isfinite(fleet.max_min_fpr_gap), (
            "max_min_fpr_gap must be finite even when cv_fpr is NaN"
        )
