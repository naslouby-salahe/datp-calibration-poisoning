"""Tests verifying blast radius and spillover diagnostics metrics on calibration poisoning outcomes."""

from __future__ import annotations

from datp.attacks.constants import THRESHOLD_QUANTILE
from datp.attacks.enums import AttackerObjective, PoisoningSourceStrategy
from datp.attacks.injection.injector import inject_fixed_budget
from datp.attacks.metrics.diagnostics import (
    compute_blast_radius,
    compute_spillover,
)
from datp.attacks.metrics.metric_engine import compute_metrics
from datp.attacks.reservoirs.reservoir import build_reservoir
from datp.attacks.score_containers import build_score_collection
from datp.attacks.threshold_recomputation.threshold_recompute import (
    compute_global_pair,
    compute_local_pair,
)
from datp.attacks.types import MetricEngineInput
from datp.core.seeds import SeedPair, SeedRecord, make_seed_rng
from datp.testsupport.synthetic_scores import (
    StandardScoreSetRequest,
    make_standard_score_set,
)


def _make_setup(fraction: float = 0.40):
    """Helper to build a completed mock metrics run setup for blast/spillover testing."""
    ss = make_standard_score_set(StandardScoreSetRequest(n_eligible=5, n_pending=1))
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    col = build_score_collection(raw)

    eligible_ids = list(col.eligible_ids)
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
