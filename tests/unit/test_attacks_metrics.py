from __future__ import annotations

import math

import numpy as np
import pytest

from datp.attacks.injection import (
    ClientScores,
    MetricEngineInput,
    PoisonedCalibrationSet,
    build_reservoir,
    build_score_collection,
    inject_fixed_budget,
)
from datp.attacks.metrics import (
    MetricResult,
    VictimDownstreamMetrics,
    aggregate_non_victim_metrics,
    cluster_size_of,
    cluster_sizes,
    compute_auroc_records,
    compute_blast_radius,
    compute_cluster_pair,
    compute_delta_tau,
    compute_fleet_fpr,
    compute_global_pair,
    compute_local_pair,
    compute_metrics,
    compute_mu_flag_threshold,
    compute_non_victim_downstream,
    compute_spillover,
    compute_victim_downstream_metrics,
    duplicate_rate,
    materiality_scale,
    n_reassigned,
    per_client_scale_base,
    tau_bound_utilization,
)
from datp.config import IQR_FLOOR_FACTOR, MATERIALITY_FACTOR, THRESHOLD_QUANTILE
from datp.core import SeedPair, SeedRecord, make_seed_rng
from datp.enums import AttackerObjective, PoisoningSourceStrategy, ThresholdPolicy
from datp.thresholding import ClientThresholdsCollection
from datp.types import ClientId, ClusterId
from tests_support.synthetic_scores import (
    StandardScoreSetRequest,
    make_standard_score_set,
)

_CLEAN = {
    ClientId("a"): ClusterId("0"),
    ClientId("b"): ClusterId("0"),
    ClientId("c"): ClusterId("1"),
    ClientId("d"): ClusterId("1"),
    ClientId("e"): ClusterId("2"),
}


def test_sizes_sorted_descending() -> None:
    """Cluster sizes are reported largest first."""
    assert cluster_sizes(_CLEAN) == (2, 2, 1)


def test_size_of_client() -> None:
    """The size of a client's own cluster is returned."""
    assert cluster_size_of(_CLEAN, ClientId("e")) == 1
    assert cluster_size_of(_CLEAN, ClientId("a")) == 2


def test_relabeling_is_not_reassignment() -> None:
    """A pure label permutation reassigns nobody."""
    relabeled = {
        ClientId("a"): ClusterId("9"),
        ClientId("b"): ClusterId("9"),
        ClientId("c"): ClusterId("7"),
        ClientId("d"): ClusterId("7"),
        ClientId("e"): ClusterId("5"),
    }
    assert n_reassigned(_CLEAN, relabeled) == 0


def test_moved_client_counts_all_affected_clients() -> None:
    """Moving one client changes the mate sets of every client in the touched clusters."""
    moved = {
        ClientId("a"): ClusterId("0"),
        ClientId("b"): ClusterId("0"),
        ClientId("c"): ClusterId("1"),
        ClientId("d"): ClusterId("2"),
        ClientId("e"): ClusterId("2"),
    }
    assert n_reassigned(_CLEAN, moved) == 3


def test_scale_base_prefers_iqr() -> None:
    """A positive IQR is the base when available."""
    cal = np.arange(100, dtype=np.float64)
    assert per_client_scale_base(cal, 10.0) == 10.0


def test_scale_base_falls_back_to_min_spacing() -> None:
    """Zero IQR and zero MAD uses the smallest positive spacing."""
    cal = np.array([1.0, 1.0, 1.0, 1.0, 1.5])
    assert per_client_scale_base(cal, 0.0) == pytest.approx(0.5)


def test_scale_base_nan_when_degenerate() -> None:
    """A constant calibration array has no defined base."""
    assert math.isnan(per_client_scale_base(np.ones(10), 0.0))


def test_materiality_scale_applies_factor_and_floor() -> None:
    """The scale is the larger of the scaled base and the IQR floor."""
    assert materiality_scale(2.0, 1.0, MATERIALITY_FACTOR, IQR_FLOOR_FACTOR) == (
        pytest.approx(0.2)
    )
    assert materiality_scale(0.001, 1.0, 0.1, 0.01) == pytest.approx(0.01)
    assert math.isnan(materiality_scale(math.nan, 1.0, 0.1, 0.01))


def test_duplicate_rate() -> None:
    """Duplicate rate is the share of entries repeating an earlier value."""
    assert duplicate_rate(np.array([1.0, 2.0, 3.0, 4.0])) == 0.0
    assert duplicate_rate(np.array([1.0, 1.0, 1.0, 2.0])) == pytest.approx(0.5)


def test_bound_utilization_raise_and_lower() -> None:
    """Utilization is the shift divided by the reachable range in the attack direction."""
    cal = np.array([0.0, 1.0, 2.0, 3.0, 10.0])
    raised = tau_bound_utilization(
        clean_cal=cal,
        tau_clean=2.0,
        tau_pois=6.0,
        objective=AttackerObjective.THRESHOLD_RAISE,
    )
    lowered = tau_bound_utilization(
        clean_cal=cal,
        tau_clean=2.0,
        tau_pois=1.0,
        objective=AttackerObjective.THRESHOLD_LOWER,
    )
    assert raised == pytest.approx(0.5)
    assert lowered == pytest.approx(0.5)


def _make_setup(fraction: float = 0.40):
    """Helper to build a completed mock metrics run setup for blast/spillover testing."""
    ss = make_standard_score_set(StandardScoreSetRequest(n_eligible=5, n_pending=1))
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    col = build_score_collection(raw)

    eligible_ids = list(col.eligibility.eligible_ids)
    victim_id = eligible_ids[0]
    cal = col.clients[victim_id].cal
    reservoir = build_reservoir(
        clean_cal=cal, source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN, tail_mass=0.10
    )
    rng = make_seed_rng(
        SeedRecord(
            pair=SeedPair(training_seed=0, poisoning_seed=100),
            client_idx=0,
            scope_idx=0,
        )
    )
    inj = inject_fixed_budget(
        clean_cal=cal, reservoir=reservoir, fraction=fraction, rng=rng
    )
    pois_cal = PoisonedCalibrationSet.from_mapping(
        {
            cid: (inj.poisoned_cal if cid == victim_id else col.clients[cid].cal.copy())
            for cid in eligible_ids
        }
    )

    global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
    local_pair = compute_local_pair(
        col, pois_cal, THRESHOLD_QUANTILE, global_pair.tau_global_clean
    )
    global_result = compute_metrics(
        MetricEngineInput(collection=col, pair=global_pair, mu_flag_threshold=None)
    )
    local_result = compute_metrics(
        MetricEngineInput(collection=col, pair=local_pair, mu_flag_threshold=None)
    )
    return col, global_result, local_result, victim_id


class TestBlastRadius:
    """Tests verifying computation of blast radius parameters and properties."""

    def test_local_blast_radius_victim_only(self) -> None:
        """Verify that local threshold blast radius is at most 1 under single victim settings."""
        _, _, local_result, victim_id = _make_setup()
        br = compute_blast_radius(local_result, victim_id=victim_id)
        assert br.n_significant <= 1, (
            "LOCAL_THRESHOLD blast radius must be at most 1 for single victim"
        )

    def test_global_blast_radius_gte_local(self) -> None:
        """Verify that global blast radius counts are greater than or equal to local blast radius."""
        _, global_result, local_result, victim_id = _make_setup()
        br_global = compute_blast_radius(global_result, victim_id=victim_id)
        br_local = compute_blast_radius(local_result, victim_id=victim_id)
        assert br_global.n_significant >= br_local.n_significant

    def test_blast_fraction_in_0_1(self) -> None:
        """Verify that blast fraction falls within the bounded range of [0.0, 1.0]."""
        _, global_result, _, victim_id = _make_setup()
        br = compute_blast_radius(global_result, victim_id=victim_id)
        assert 0.0 <= br.blast_fraction <= 1.0

    def test_n_eligible_correct(self) -> None:
        """Verify that blast radius contains correct count of total eligible clients."""
        _, global_result, _, _ = _make_setup()
        br = compute_blast_radius(global_result)
        assert br.n_eligible == 5


class TestSpillover:
    """Tests verifying spillover counts, victim exclusion, and ordering."""

    def test_local_no_spillover(self) -> None:
        """Verify that local threshold raises show zero spillover to other non-victim devices."""
        col, _, local_result, victim_id = _make_setup()
        sp = compute_spillover(
            local_result,
            collection=col,
            victim_id=victim_id,
            objective=AttackerObjective.THRESHOLD_RAISE,
        )
        assert sp.n_spillover == 0, (
            "LOCAL_THRESHOLD should have no spillover for single victim"
        )
        assert len(sp.spillover_client_ids) == 0

    def test_spillover_does_not_include_victim(self) -> None:
        """Verify that the victim client ID is excluded from the spillover collection."""
        col, global_result, _, victim_id = _make_setup()
        sp = compute_spillover(
            global_result,
            collection=col,
            victim_id=victim_id,
            objective=AttackerObjective.THRESHOLD_RAISE,
        )
        assert victim_id not in sp.spillover_client_ids

    def test_n_non_victims_correct(self) -> None:
        """Verify that spillover output logs the correct number of non-victim devices."""
        col, _, local_result, victim_id = _make_setup()
        sp = compute_spillover(
            local_result,
            collection=col,
            victim_id=victim_id,
            objective=AttackerObjective.THRESHOLD_RAISE,
        )
        assert sp.n_non_victims == 4

    def test_spillover_ids_sorted(self) -> None:
        """Verify that the list of spillover client IDs is returned sorted alphabetically."""
        col, global_result, _, victim_id = _make_setup()
        sp = compute_spillover(
            global_result,
            collection=col,
            victim_id=victim_id,
            objective=AttackerObjective.THRESHOLD_RAISE,
        )
        assert sp.spillover_client_ids == tuple(sorted(sp.spillover_client_ids))


def _scores(client_id: str, benign: list[float], attack: list[float]) -> ClientScores:
    return ClientScores(
        client_id=client_id,
        cal=np.zeros(200, dtype=np.float64),
        test_benign=np.array(benign, dtype=np.float64),
        test_attack=np.array(attack, dtype=np.float64),
    )


class TestAbsoluteCounts:
    """Absolute false-positive and missed-detection counts."""

    def test_counts_move_with_threshold(self) -> None:
        """Raising the threshold removes false positives and adds missed detections."""
        scores = _scores("c0", [0.1, 0.4, 0.6, 0.9], [0.5, 0.7, 0.8, 1.0])
        m = compute_victim_downstream_metrics(
            clean_threshold=0.3, poisoned_threshold=0.65, client_scores=scores
        )
        assert (m.fp_clean, m.fp_poisoned) == (3, 1)
        assert (m.fn_clean, m.fn_poisoned) == (0, 1)
        assert m.n_test_benign == 4
        assert m.n_test_attack == 4

    def test_fpr_delta_matches_counts(self) -> None:
        """Delta FPR equals the change in false-positive count over benign samples."""
        scores = _scores("c0", [0.1, 0.4, 0.6, 0.9], [0.5, 0.7, 0.8, 1.0])
        m = compute_victim_downstream_metrics(
            clean_threshold=0.3, poisoned_threshold=0.65, client_scores=scores
        )
        assert m.delta_fpr == pytest.approx((m.fp_poisoned - m.fp_clean) / 4)


class TestNonVictimAggregation:
    """Fleet aggregation over non-victim clients."""

    def _fleet(self) -> dict[str, ClientScores]:
        return {
            "victim": _scores("victim", [0.1, 0.9], [0.5, 0.8]),
            "a": _scores("a", [0.1, 0.2, 0.7, 0.9], [0.5, 0.6, 0.8, 0.95]),
            "b": _scores("b", [0.1, 0.2, 0.3, 0.4], [0.35, 0.45, 0.8, 0.9]),
        }

    def test_victim_is_excluded(self) -> None:
        """The victim never contributes to the non-victim aggregate."""
        fleet = self._fleet()
        result = compute_non_victim_downstream(
            thresholds={cid: (0.3, 0.65) for cid in fleet},
            scores_by_client=fleet,
            victim_id="victim",
        )
        assert result.n_clients == 2

    def test_totals_are_sums_of_client_deltas(self) -> None:
        """Total error-count deltas equal the sum over non-victim clients."""
        fleet = self._fleet()
        per_client = {
            cid: compute_victim_downstream_metrics(
                clean_threshold=0.3, poisoned_threshold=0.65, client_scores=fleet[cid]
            )
            for cid in ("a", "b")
        }
        agg = aggregate_non_victim_metrics(per_client)
        assert agg.delta_fn_total == sum(
            m.fn_poisoned - m.fn_clean for m in per_client.values()
        )
        assert agg.delta_fp_total == sum(
            m.fp_poisoned - m.fp_clean for m in per_client.values()
        )
        assert agg.worst_delta_tpr == min(m.delta_tpr for m in per_client.values())
        assert agg.worst_delta_fpr == max(m.delta_fpr for m in per_client.values())

    def test_unchanged_thresholds_give_zero_deltas(self) -> None:
        """Identical clean and poisoned thresholds produce no downstream change."""
        fleet = self._fleet()
        result = compute_non_victim_downstream(
            thresholds={cid: (0.5, 0.5) for cid in fleet},
            scores_by_client=fleet,
            victim_id="victim",
        )
        assert result.mean_delta_tpr == pytest.approx(0.0)
        assert result.mean_delta_fpr == pytest.approx(0.0)
        assert result.delta_fp_total == 0
        assert result.delta_fn_total == 0

    def test_empty_aggregate_is_nan(self) -> None:
        """No non-victim clients yields NaN means and zero totals."""
        agg = aggregate_non_victim_metrics({})
        assert agg.n_clients == 0
        assert math.isnan(agg.mean_delta_tpr)
        assert agg.delta_fp_total == 0


def _make_collection():
    """Helper to build standard mock ScoreCollection for metric engine testing."""
    ss = make_standard_score_set(StandardScoreSetRequest(n_eligible=5, n_pending=1))
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    return build_score_collection(raw)


def _clean_calibration_set(collection):
    return PoisonedCalibrationSet.from_mapping(
        {
            cid: collection.clients[cid].cal.copy()
            for cid in collection.eligibility.eligible_ids
        }
    )


def _inject_one_victim(col, victim_idx: int = 0, fraction: float = 0.40):
    """Helper to run single victim calibration poisoning injection."""
    eligible_ids = list(col.eligibility.eligible_ids)
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
    return PoisonedCalibrationSet.from_mapping(pois_cal), victim_id


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
        assert set(dt.keys()) == set(col.eligibility.eligible_ids)

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
        pois_cal = _clean_calibration_set(col)
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
        pois_cal = _clean_calibration_set(col)
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        dt = compute_delta_tau(col, global_pair)
        for entry in dt.values():
            assert entry.delta_tau_scale >= 0.0

    def test_policy_recorded(self) -> None:
        """Verify that the tested threshold policy is recorded correctly on delta entries."""
        col = _make_collection()
        pois_cal = _clean_calibration_set(col)
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        dt = compute_delta_tau(col, global_pair)
        for entry in dt.values():
            assert entry.policy == ThresholdPolicy.GLOBAL_THRESHOLD


class TestFleetFpr:
    """Tests verifying fleet-wide false positive rates under poisoning."""

    def test_coverage_ratio_correct(self) -> None:
        """Verify that coverage ratio matches fraction of eligible clients over total clients."""
        col = _make_collection()
        pois_cal = _clean_calibration_set(col)
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        fleet = compute_fleet_fpr(col, global_pair, None)
        assert fleet.coverage_ratio == pytest.approx(5 / 6)

    def test_n_eligible_and_n_total(self) -> None:
        """Verify that eligible and total count properties match the source dataset split size."""
        col = _make_collection()
        pois_cal = _clean_calibration_set(col)
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        fleet = compute_fleet_fpr(col, global_pair, None)
        assert fleet.n_eligible == 5
        assert fleet.n_total == 6

    def test_cv_fpr_no_epsilon(self) -> None:
        """Verify that CV(FPR) is NaN when mean FPR is exactly 0.0 to prevent divide-by-zero."""
        col = _make_collection()
        pois_cal = _clean_calibration_set(col)
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)

        from datp.attacks.injection import ThresholdPairBase

        high_tau = 1e9
        high_pair = ThresholdPairBase(
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
        pois_cal = _clean_calibration_set(col)
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
        assert set(records.records.keys()) == set(col.eligibility.eligible_ids)

    def test_auroc_invariant_test_scores_unchanged(self) -> None:
        """Verify that AUROCs remain invariant across repeated evaluations since test scores are clean."""
        col = _make_collection()
        r1 = compute_auroc_records(col)
        r2 = compute_auroc_records(col)
        for cid in col.eligibility.eligible_ids:
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
        pois_cal = _clean_calibration_set(col)
        local_pair = compute_local_pair(
            col,
            pois_cal,
            THRESHOLD_QUANTILE,
            compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean,
        )
        result = compute_metrics(
            MetricEngineInput(collection=col, pair=local_pair, mu_flag_threshold=0.05)
        )
        assert set(result.delta_tau.keys()) == set(col.eligibility.eligible_ids)
        assert set(result.auroc_records.records.keys()) == set(
            col.eligibility.eligible_ids
        )
        assert result.mu_flag_threshold == pytest.approx(0.05)


class TestAbsoluteDispersionWhenCvNan:
    """Tests verifying absolute dispersion checks when CV(FPR) evaluates to NaN."""

    def test_iqr_fpr_finite_when_cv_fpr_nan(self) -> None:
        """Verify that companion dispersion IQR/gap metrics remain finite even when cv_fpr is NaN."""
        col = _make_collection()
        pois_cal = _clean_calibration_set(col)
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        from datp.attacks.injection import ThresholdPairBase

        high_tau = 1e9
        high_pair = ThresholdPairBase(
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


def _scores_victim_downstream_metrics(
    benign: list[float],
    attack: list[float],
    client_id: str = "c0",
) -> ClientScores:
    """Helper to build ClientScores with dummy calibration scores and configured test sets."""
    return ClientScores(
        client_id=client_id,
        cal=np.zeros(200, dtype=np.float64),
        test_benign=np.array(benign, dtype=np.float64),
        test_attack=np.array(attack, dtype=np.float64),
    )


class TestBasicComputation:
    """Tests verifying simple accuracy, TPR, FPR, and balanced accuracy calculations."""

    def test_tpr_all_attack_above_threshold(self) -> None:
        """Verify that TPR is 1.0 when all attack scores lie above the threshold."""
        scores = _scores_victim_downstream_metrics(
            benign=[0.1, 0.2, 0.3], attack=[0.8, 0.9, 1.0]
        )
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )

        assert result.tpr_clean == pytest.approx(1.0)
        assert result.tpr_poisoned == pytest.approx(1.0)
        assert result.delta_tpr == pytest.approx(0.0)

    def test_fpr_no_benign_above_threshold(self) -> None:
        """Verify balanced accuracy is 1.0 when no benign scores lie above the threshold."""
        scores = _scores_victim_downstream_metrics(
            benign=[0.1, 0.2, 0.3], attack=[0.8, 0.9, 1.0]
        )
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )

        assert result.ba_clean == pytest.approx(1.0)
        assert result.ba_poisoned == pytest.approx(1.0)

    def test_tpr_half_attack_above_threshold(self) -> None:
        """Verify correct calculation when exactly half of attack scores cross threshold."""
        scores = _scores_victim_downstream_metrics(benign=[0.1, 0.6], attack=[0.4, 0.8])

        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert result.tpr_clean == pytest.approx(0.5)
        assert result.ba_clean == pytest.approx(0.5)

    def test_macro_f1_perfect_separation(self) -> None:
        """Verify macro F1 is 1.0 under perfect separation of benign and attack scores."""
        scores = _scores_victim_downstream_metrics(benign=[0.1, 0.2], attack=[0.8, 0.9])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert result.macro_f1_clean == pytest.approx(1.0)
        assert result.macro_f1_poisoned == pytest.approx(1.0)
        assert result.delta_macro_f1 == pytest.approx(0.0)

    def test_delta_fields_are_poisoned_minus_clean(self) -> None:
        """Verify that delta_tpr represents poisoned TPR minus clean TPR."""
        scores = _scores_victim_downstream_metrics(benign=[0.1, 0.2], attack=[0.7, 0.9])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.85,
            client_scores=scores,
        )
        expected_tpr_clean = 1.0
        expected_tpr_pois = 0.5
        assert result.tpr_clean == pytest.approx(expected_tpr_clean)
        assert result.tpr_poisoned == pytest.approx(expected_tpr_pois)
        assert result.delta_tpr == pytest.approx(expected_tpr_pois - expected_tpr_clean)

    def test_delta_ba_is_poisoned_minus_clean(self) -> None:
        """Verify that delta_ba represents poisoned Balanced Accuracy minus clean Balanced Accuracy."""
        scores = _scores_victim_downstream_metrics(benign=[0.1, 0.2], attack=[0.7, 0.9])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.85,
            client_scores=scores,
        )

        assert result.ba_clean == pytest.approx(1.0)
        assert result.ba_poisoned == pytest.approx(0.75)
        assert result.delta_ba == pytest.approx(0.75 - 1.0)

    def test_returns_victim_downstream_metrics_instance(self) -> None:
        """Verify that compute_victim_downstream_metrics returns a VictimDownstreamMetrics model instance."""
        scores = _scores_victim_downstream_metrics(benign=[0.1], attack=[0.9])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert isinstance(result, VictimDownstreamMetrics)


class TestThresholdDirectionInvariants:
    """Tests verifying monotonic changes in metrics when shifting threshold values."""

    def test_raising_threshold_does_not_increase_tpr(self) -> None:
        """Verify that raising the decision threshold results in a negative delta_tpr."""
        scores = _scores_victim_downstream_metrics(
            benign=[0.1, 0.2, 0.3], attack=[0.6, 0.7, 0.8, 0.9]
        )
        result = compute_victim_downstream_metrics(
            clean_threshold=0.55,
            poisoned_threshold=0.75,
            client_scores=scores,
        )

        assert result.tpr_poisoned < result.tpr_clean
        assert result.delta_tpr < 0.0

    def test_lowering_threshold_does_not_decrease_fpr(self) -> None:
        """Verify that lowering the decision threshold decreases balanced accuracy by raising FPR."""
        scores = _scores_victim_downstream_metrics(
            benign=[0.4, 0.5, 0.6, 0.7], attack=[0.5, 0.9, 1.0]
        )
        result = compute_victim_downstream_metrics(
            clean_threshold=0.65,
            poisoned_threshold=0.45,
            client_scores=scores,
        )

        assert result.delta_tpr > 0.0
        assert result.ba_poisoned < result.ba_clean


class TestZeroFractionInvariant:
    """Tests verifying that identical clean and poisoned thresholds yield zero metric changes."""

    def test_identical_thresholds_produce_zero_deltas(self) -> None:
        """Verify that equal thresholds produce exact zero metric delta values."""
        scores = _scores_victim_downstream_metrics(
            benign=[0.1, 0.4, 0.7], attack=[0.6, 0.8, 0.95]
        )
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert result.delta_tpr == pytest.approx(0.0)
        assert result.delta_ba == pytest.approx(0.0)
        if not math.isnan(result.delta_macro_f1):
            assert result.delta_macro_f1 == pytest.approx(0.0)

    def test_zero_fraction_tpr_and_poisoned_are_equal(self) -> None:
        """Verify that clean and poisoned TPR/balanced accuracy values match when thresholds are equal."""
        scores = _scores_victim_downstream_metrics(benign=[0.1, 0.2], attack=[0.8, 0.9])
        threshold = 0.5
        result = compute_victim_downstream_metrics(
            clean_threshold=threshold,
            poisoned_threshold=threshold,
            client_scores=scores,
        )
        assert result.tpr_clean == pytest.approx(result.tpr_poisoned)
        assert result.ba_clean == pytest.approx(result.ba_poisoned)


class TestNoMutationOfTestScores:
    """Tests verifying that original test score arrays are not mutated in-place."""

    def test_test_benign_not_mutated(self) -> None:
        """Verify that test score arrays remain unmodified after metrics extraction."""
        benign = np.array([0.1, 0.4, 0.7], dtype=np.float64)
        attack = np.array([0.8, 0.9], dtype=np.float64)
        benign_copy = benign.copy()
        attack_copy = attack.copy()
        scores = ClientScores(
            client_id="c0",
            cal=np.zeros(200),
            test_benign=benign,
            test_attack=attack,
        )
        compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.6,
            client_scores=scores,
        )
        np.testing.assert_array_equal(benign, benign_copy)
        np.testing.assert_array_equal(attack, attack_copy)


class TestEdgeCases:
    """Tests verifying behavior under empty inputs or extreme score ranges."""

    def test_empty_attack_array_returns_nan_tpr(self) -> None:
        """Verify that empty attack score arrays evaluate to NaN TPR."""
        scores = _scores_victim_downstream_metrics(benign=[0.1, 0.2], attack=[])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert math.isnan(result.tpr_clean)
        assert math.isnan(result.tpr_poisoned)

    def test_empty_benign_array_returns_nan_ba(self) -> None:
        """Verify that empty benign score arrays evaluate to NaN balanced accuracy."""
        scores = _scores_victim_downstream_metrics(benign=[], attack=[0.8, 0.9])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert math.isnan(result.ba_clean)
        assert math.isnan(result.ba_poisoned)

    def test_all_below_threshold_gives_zero_tpr(self) -> None:
        """Verify that TPR evaluates to 0.0 when all attack scores fall below the decision threshold."""
        scores = _scores_victim_downstream_metrics(benign=[0.1, 0.2], attack=[0.3, 0.4])
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert result.tpr_clean == pytest.approx(0.0)
        assert result.tpr_poisoned == pytest.approx(0.0)


class TestThresholdRaiseReducesDetection:
    """Tests verifying that raising thresholds specifically leads to lower True Positive Rates."""

    def test_raised_threshold_produces_non_positive_delta_tpr(self) -> None:
        """Verify that raising decision threshold yields a negative delta_tpr."""
        scores = _scores_victim_downstream_metrics(
            benign=[0.1, 0.2, 0.3, 0.4],
            attack=[0.6, 0.7, 0.8, 0.9],
        )
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.75,
            client_scores=scores,
        )
        assert result.tpr_clean == pytest.approx(1.0)
        assert result.tpr_poisoned == pytest.approx(0.5)
        assert result.delta_tpr < 0.0

    def test_clean_and_raised_equal_threshold_zero_delta_tpr(self) -> None:
        """Verify delta_tpr is exactly zero when thresholds are identical."""
        scores = _scores_victim_downstream_metrics(
            benign=[0.1, 0.2],
            attack=[0.6, 0.8],
        )
        result = compute_victim_downstream_metrics(
            clean_threshold=0.5,
            poisoned_threshold=0.5,
            client_scores=scores,
        )
        assert result.delta_tpr == pytest.approx(0.0)


def _make_collection_cluster_threshold_recompute():

    ss = make_standard_score_set(StandardScoreSetRequest(n_eligible=9, n_pending=1))
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    return build_score_collection(raw)


def _make_poisoned_cal(col, victim_idx: int = 0, fraction: float = 0.40):

    eligible_ids = list(col.eligibility.eligible_ids)
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
    return PoisonedCalibrationSet.from_mapping(poisoned_cal), victim_id


class TestClusterThresholdPairBasics:
    """ClusterThresholdPair construction and basic properties."""

    def test_policy_is_cluster(self) -> None:
        col = _make_collection_cluster_threshold_recompute()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        assert pair.policy == ThresholdPolicy.CLUSTER_THRESHOLD

    def test_eligible_ids_in_result(self) -> None:
        col = _make_collection_cluster_threshold_recompute()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        assert set(pair.thresholds_clean.keys()) == set(col.eligibility.eligible_ids)
        assert set(pair.thresholds_pois.keys()) == set(col.eligibility.eligible_ids)

    def test_decomposition_covers_eligible(self) -> None:
        col = _make_collection_cluster_threshold_recompute()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        assert set(pair.decomposition.keys()) == set(col.eligibility.eligible_ids)

    def test_pending_not_in_thresholds(self) -> None:
        col = _make_collection_cluster_threshold_recompute()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for pid in col.eligibility.pending_ids:
            assert pid not in pair.thresholds_clean
            assert pid not in pair.thresholds_pois


class TestDecompositionIdentity:
    """Delta decomposition sums to total."""

    def test_delta_total_equals_agg_plus_churn(self) -> None:

        col = _make_collection_cluster_threshold_recompute()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for cid, entry in pair.decomposition.items():
            assert entry.delta_tau_total == pytest.approx(
                entry.delta_tau_agg + entry.delta_tau_churn, abs=1e-10
            ), f"Decomposition identity failed for {cid}"

    def test_delta_total_matches_effective_thresholds(self) -> None:
        col = _make_collection_cluster_threshold_recompute()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for cid, entry in pair.decomposition.items():
            expected = pair.thresholds_pois[cid] - pair.thresholds_clean[cid]
            assert entry.delta_tau_total == pytest.approx(expected, abs=1e-10)

    def test_tau_clean_matches_thresholds_clean(self) -> None:
        col = _make_collection_cluster_threshold_recompute()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for cid, entry in pair.decomposition.items():
            assert entry.tau_clean == pytest.approx(pair.thresholds_clean[cid])

    def test_tau_pois_matches_thresholds_pois(self) -> None:
        col = _make_collection_cluster_threshold_recompute()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for cid, entry in pair.decomposition.items():
            assert entry.tau_pois == pytest.approx(pair.thresholds_pois[cid])


class TestDecompositionFrozenScaler:
    """Decomposition uses a frozen scaler for reproducibility."""

    def test_normalization_gap_identity(self) -> None:

        col = _make_collection_cluster_threshold_recompute()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for cid, entry in pair.decomposition.items():
            assert entry.delta_tau_normalization_gap == pytest.approx(
                entry.delta_tau_total - entry.delta_tau_frozen_scaler, abs=1e-10
            ), f"Normalization-gap identity failed for {cid}"

    def test_frozen_scaler_is_finite(self) -> None:
        col = _make_collection_cluster_threshold_recompute()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        import math

        for entry in pair.decomposition.values():
            assert math.isfinite(entry.delta_tau_frozen_scaler)
            assert math.isfinite(entry.delta_tau_normalization_gap)

    def test_f0_frozen_scaler_zero(self) -> None:

        col = _make_collection_cluster_threshold_recompute()
        pois_cal = {
            cid: col.clients[cid].cal.copy() for cid in col.eligibility.eligible_ids
        }
        pair = compute_cluster_pair(
            col,
            PoisonedCalibrationSet.from_mapping(pois_cal),
            THRESHOLD_QUANTILE,
        )
        for entry in pair.decomposition.values():
            assert entry.delta_tau_frozen_scaler == pytest.approx(0.0, abs=1e-10)
            assert entry.delta_tau_normalization_gap == pytest.approx(0.0, abs=1e-10)


class TestFractionZero:
    """Zero-fraction poisoning produces zero delta."""

    def test_f0_all_deltas_zero(self) -> None:

        col = _make_collection_cluster_threshold_recompute()

        pois_cal = {
            cid: col.clients[cid].cal.copy() for cid in col.eligibility.eligible_ids
        }
        pair = compute_cluster_pair(
            col,
            PoisonedCalibrationSet.from_mapping(pois_cal),
            THRESHOLD_QUANTILE,
        )
        for entry in pair.decomposition.values():
            assert entry.delta_tau_total == pytest.approx(0.0, abs=1e-10)
            assert entry.delta_tau_agg == pytest.approx(0.0, abs=1e-10)
            assert entry.delta_tau_churn == pytest.approx(0.0, abs=1e-10)
            assert entry.delta_tau_frozen_scaler == pytest.approx(0.0, abs=1e-10)
            assert entry.delta_tau_normalization_gap == pytest.approx(0.0, abs=1e-10)


class TestDeterminism:
    """Identical inputs produce identical cluster threshold recomputation."""

    def test_same_inputs_same_result(self) -> None:
        col = _make_collection_cluster_threshold_recompute()
        pois_cal, _ = _make_poisoned_cal(col)
        p1 = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        p2 = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for cid in col.eligibility.eligible_ids:
            assert p1.thresholds_clean[cid] == p2.thresholds_clean[cid]
            assert p1.thresholds_pois[cid] == p2.thresholds_pois[cid]
            assert (
                p1.decomposition[cid].delta_tau_total
                == p2.decomposition[cid].delta_tau_total
            )


class TestNoClientLabelComparison:
    """Cluster assignment uses scores only, never client labels."""

    def test_no_raw_cluster_label_in_decomp(self) -> None:

        col = _make_collection_cluster_threshold_recompute()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for entry in pair.decomposition.values():
            assert not hasattr(entry, "cluster_label"), (
                "Decomposition entries must not store raw cluster labels."
            )


class TestFixedAssignmentAndTransitions:
    """Frozen-assignment thresholds, assignments, and silhouettes."""

    def test_fixed_assignment_equals_agg_decomposition(self) -> None:
        col = _make_collection_cluster_threshold_recompute()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for cid in col.eligibility.eligible_ids:
            assert pair.fixed_assignment_thresholds[cid] == pytest.approx(
                pair.decomposition[cid].tau_agg
            )

    def test_assignments_cover_eligible_clients(self) -> None:
        col = _make_collection_cluster_threshold_recompute()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        assert set(pair.clean_assignments) == set(col.eligibility.eligible_ids)
        assert set(pair.poisoned_assignments) == set(col.eligibility.eligible_ids)

    def test_zero_fraction_keeps_assignments_and_thresholds(self) -> None:
        col = _make_collection_cluster_threshold_recompute()
        pois_cal, _ = _make_poisoned_cal(col, fraction=0.0)
        pair = compute_cluster_pair(col, pois_cal, THRESHOLD_QUANTILE)
        assert dict(pair.clean_assignments) == dict(pair.poisoned_assignments)
        for cid in col.eligibility.eligible_ids:
            assert pair.thresholds_pois[cid] == pytest.approx(
                pair.thresholds_clean[cid]
            )
            assert pair.fixed_assignment_thresholds[cid] == pytest.approx(
                pair.thresholds_clean[cid]
            )

    def test_hyperparams_change_cluster_count(self) -> None:
        from datp.thresholding import ClusterHyperparams

        col = _make_collection_cluster_threshold_recompute()
        pois_cal, _ = _make_poisoned_cal(col)
        pair = compute_cluster_pair(
            col, pois_cal, THRESHOLD_QUANTILE, ClusterHyperparams(k=2)
        )
        assert len(set(pair.clean_assignments.values())) == 2


def _make_collection_and_pois_cal(victim_idx: int = 0, fraction: float = 0.40) -> tuple:

    ss = make_standard_score_set(StandardScoreSetRequest(n_eligible=3, n_pending=1))
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    col = build_score_collection(raw)

    eligible_ids = list(col.eligibility.eligible_ids)
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
    injection = inject_fixed_budget(
        clean_cal=victim_cal, reservoir=reservoir, fraction=fraction, rng=rng
    )

    poisoned_cal: dict[str, np.ndarray] = {}
    for cid in eligible_ids:
        if cid == victim_id:
            poisoned_cal[cid] = injection.poisoned_cal
        else:
            poisoned_cal[cid] = col.clients[cid].cal

    return col, PoisonedCalibrationSet.from_mapping(poisoned_cal), victim_id


class TestGlobalThresholdPair:
    """Global threshold pair computation and properties."""

    def test_policy_is_global(self) -> None:
        col, pois_cal, _ = _make_collection_and_pois_cal()
        pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        assert pair.policy == ThresholdPolicy.GLOBAL_THRESHOLD

    def test_tau_global_pois_differs_from_clean(self) -> None:
        col, pois_cal, _ = _make_collection_and_pois_cal()
        pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)

        assert pair.tau_global_pois > pair.tau_global_clean

    def test_all_eligible_share_tau_global(self) -> None:
        col, pois_cal, _ = _make_collection_and_pois_cal()
        pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for tau in pair.thresholds_clean.values():
            assert tau == pair.tau_global_clean
        for tau in pair.thresholds_pois.values():
            assert tau == pair.tau_global_pois

    def test_eligible_ids_in_result(self) -> None:
        col, pois_cal, _ = _make_collection_and_pois_cal()
        pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        assert set(pair.thresholds_clean.keys()) == set(col.eligibility.eligible_ids)
        assert set(pair.thresholds_pois.keys()) == set(col.eligibility.eligible_ids)

    def test_clean_reproducible(self) -> None:
        col, pois_cal, _ = _make_collection_and_pois_cal()
        p1 = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        p2 = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        assert p1.tau_global_clean == p2.tau_global_clean

    def test_f0_pair_equals_clean(self) -> None:

        ss = make_standard_score_set(StandardScoreSetRequest(n_eligible=3, n_pending=1))
        raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
        col = build_score_collection(raw)

        pois_cal = PoisonedCalibrationSet.from_mapping(
            {cid: col.clients[cid].cal.copy() for cid in col.eligibility.eligible_ids}
        )
        pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        assert pair.tau_global_pois == pytest.approx(pair.tau_global_clean)


class TestLocalThresholdPair:
    """Local threshold pair computation and properties."""

    def test_policy_is_local(self) -> None:
        col, pois_cal, _ = _make_collection_and_pois_cal()
        tau_g = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean
        pair = compute_local_pair(col, pois_cal, THRESHOLD_QUANTILE, tau_g)
        assert pair.policy == ThresholdPolicy.LOCAL_THRESHOLD

    def test_only_victim_threshold_changes(self) -> None:
        col, pois_cal, victim_id = _make_collection_and_pois_cal(victim_idx=0)
        tau_g = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean
        pair = compute_local_pair(col, pois_cal, THRESHOLD_QUANTILE, tau_g)
        for cid in col.eligibility.eligible_ids:
            if cid != victim_id:
                assert pair.thresholds_clean[cid] == pytest.approx(
                    pair.thresholds_pois[cid]
                ), f"Non-victim {cid!r} threshold should not change"

    def test_victim_threshold_raised(self) -> None:
        col, pois_cal, victim_id = _make_collection_and_pois_cal(victim_idx=0)
        tau_g = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean
        pair = compute_local_pair(col, pois_cal, THRESHOLD_QUANTILE, tau_g)

        assert pair.thresholds_pois[victim_id] > pair.thresholds_clean[victim_id]

    def test_eligible_ids_in_result(self) -> None:
        col, pois_cal, _ = _make_collection_and_pois_cal()
        tau_g = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean
        pair = compute_local_pair(col, pois_cal, THRESHOLD_QUANTILE, tau_g)
        assert set(pair.thresholds_clean.keys()) == set(col.eligibility.eligible_ids)
        assert set(pair.thresholds_pois.keys()) == set(col.eligibility.eligible_ids)

    def test_f0_pair_equals_clean(self) -> None:
        ss = make_standard_score_set(StandardScoreSetRequest(n_eligible=3, n_pending=1))
        raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
        col = build_score_collection(raw)
        pois_cal = PoisonedCalibrationSet.from_mapping(
            {cid: col.clients[cid].cal.copy() for cid in col.eligibility.eligible_ids}
        )
        tau_g = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE).tau_global_clean
        pair = compute_local_pair(col, pois_cal, THRESHOLD_QUANTILE, tau_g)
        for cid in col.eligibility.eligible_ids:
            assert pair.thresholds_clean[cid] == pytest.approx(
                pair.thresholds_pois[cid]
            )


class TestNoPendingMutation:
    """Pending clients are never mutated during threshold recomputation."""

    def test_pending_not_in_threshold_dicts(self) -> None:
        col, pois_cal, _ = _make_collection_and_pois_cal()
        pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        for pid in col.eligibility.pending_ids:
            assert pid not in pair.thresholds_clean
            assert pid not in pair.thresholds_pois
