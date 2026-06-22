"""Tests for attack diagnostics: ASR, blast radius, spillover ."""

from __future__ import annotations

import pytest

from datp.artifacts.poison_names import THRESHOLD_QUANTILE
from datp.attacks.metrics.diagnostics import (
    compute_asr,
    compute_blast_radius,
    compute_spillover,
)
from datp.attacks.injection.injector import inject_fixed_budget
from datp.attacks.metrics.metric_engine import compute_metrics
from datp.attacks.types import MetricEngineInput
from datp.attacks.reservoirs.reservoir import build_reservoir
from datp.attacks.score_containers import build_score_collection
from datp.attacks.threshold_recomputation.threshold_recompute import compute_global_pair, compute_local_pair
from datp.attacks.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    ThresholdPolicy,
)
from datp.core.seed_sequence import make_seed_rng
from datp.testsupport.synthetic_scores import make_standard_score_set


def _make_setup(fraction: float = 0.40):
    """Return (collection, global_result, local_result, victim_id)."""
    ss = make_standard_score_set(n_eligible=5, n_pending=1)
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    col = build_score_collection(raw)

    eligible_ids = list(col.eligible_ids)
    victim_id = eligible_ids[0]
    cal = col.clients[victim_id].cal
    reservoir = build_reservoir(
        clean_cal=cal, source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN, tail_mass=0.10
    )
    rng = make_seed_rng(training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0)
    inj = inject_fixed_budget(
        clean_cal=cal, reservoir=reservoir, fraction=fraction, rng=rng
    )
    pois_cal = {
        cid: (inj.poisoned_cal if cid == victim_id else col.clients[cid].cal.copy())
        for cid in eligible_ids
    }

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


class TestAsr:
    def test_asr_in_0_1(self) -> None:
        _, global_result, _, victim_id = _make_setup()
        asr = compute_asr(
            global_result,
            victim_id=victim_id,
            objective=AttackerObjective.THRESHOLD_RAISE,
        )
        assert 0.0 <= asr.asr <= 1.0

    def test_asr_victim_id_recorded(self) -> None:
        _, _, local_result, victim_id = _make_setup()
        asr = compute_asr(
            local_result,
            victim_id=victim_id,
            objective=AttackerObjective.THRESHOLD_RAISE,
        )
        assert asr.victim_id == victim_id

    def test_asr_policy_recorded(self) -> None:
        _, _, local_result, victim_id = _make_setup()
        asr = compute_asr(
            local_result,
            victim_id=victim_id,
            objective=AttackerObjective.THRESHOLD_RAISE,
        )
        assert asr.policy == ThresholdPolicy.LOCAL_THRESHOLD

    def test_asr_raise_counts_positive_significant(self) -> None:
        _, _, local_result, victim_id = _make_setup()
        asr = compute_asr(
            local_result,
            victim_id=victim_id,
            objective=AttackerObjective.THRESHOLD_RAISE,
        )
        # Victim should have significant positive delta (HIGH_SCORE injection).
        assert asr.n_significant >= 1

    def test_asr_lower_zero_for_raise_attack(self) -> None:
        """THRESHOLD_LOWER ASR should be 0 when we only raised a victim threshold."""
        _, _, local_result, victim_id = _make_setup()
        # LOCAL_THRESHOLD: only victim changes, direction is RAISE → no LOWER significant clients.
        asr_lower = compute_asr(
            local_result,
            victim_id=victim_id,
            objective=AttackerObjective.THRESHOLD_LOWER,
        )
        # No clients should have Δτ < -scale since we raised the threshold.
        assert asr_lower.n_significant == 0

    def test_f0_asr_is_zero(self) -> None:
        ss = make_standard_score_set(n_eligible=5, n_pending=1)
        raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
        col = build_score_collection(raw)
        pois_cal = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
        global_pair = compute_global_pair(col, pois_cal, THRESHOLD_QUANTILE)
        result = compute_metrics(
            MetricEngineInput(collection=col, pair=global_pair, mu_flag_threshold=None)
        )
        asr = compute_asr(
            result,
            victim_id=next(iter(col.eligible_ids)),
            objective=AttackerObjective.THRESHOLD_RAISE,
        )
        assert asr.asr == pytest.approx(0.0)


class TestBlastRadius:
    def test_local_blast_radius_victim_only(self) -> None:
        """LOCAL_THRESHOLD: only victim threshold changes → blast radius at most 1."""
        _, _, local_result, victim_id = _make_setup()
        br = compute_blast_radius(local_result, victim_id=victim_id)
        assert br.n_significant <= 1, (
            "LOCAL_THRESHOLD blast radius must be at most 1 for single victim"
        )

    def test_global_blast_radius_gte_local(self) -> None:
        """GLOBAL_THRESHOLD: global effect → blast radius >= LOCAL_THRESHOLD blast radius."""
        _, global_result, local_result, victim_id = _make_setup()
        br_global = compute_blast_radius(global_result, victim_id=victim_id)
        br_local = compute_blast_radius(local_result, victim_id=victim_id)
        assert br_global.n_significant >= br_local.n_significant

    def test_blast_fraction_in_0_1(self) -> None:
        _, global_result, _, victim_id = _make_setup()
        br = compute_blast_radius(global_result, victim_id=victim_id)
        assert 0.0 <= br.blast_fraction <= 1.0

    def test_n_eligible_correct(self) -> None:
        _, global_result, _, _ = _make_setup()
        br = compute_blast_radius(global_result)
        assert br.n_eligible == 5


class TestSpillover:
    def test_local_no_spillover(self) -> None:
        """LOCAL_THRESHOLD single-victim attack: only victim threshold changes → no spillover."""
        _, _, local_result, victim_id = _make_setup()
        sp = compute_spillover(local_result, victim_id=victim_id)
        assert sp.n_spillover == 0, (
            "LOCAL_THRESHOLD should have no spillover for single victim"
        )
        assert len(sp.spillover_client_ids) == 0

    def test_spillover_does_not_include_victim(self) -> None:
        _, global_result, _, victim_id = _make_setup()
        sp = compute_spillover(global_result, victim_id=victim_id)
        assert victim_id not in sp.spillover_client_ids

    def test_n_non_victims_correct(self) -> None:
        _, _, local_result, victim_id = _make_setup()
        sp = compute_spillover(local_result, victim_id=victim_id)
        assert sp.n_non_victims == 4  # 5 eligible - 1 victim

    def test_spillover_ids_sorted(self) -> None:
        _, global_result, _, victim_id = _make_setup()
        sp = compute_spillover(global_result, victim_id=victim_id)
        assert sp.spillover_client_ids == tuple(sorted(sp.spillover_client_ids))
