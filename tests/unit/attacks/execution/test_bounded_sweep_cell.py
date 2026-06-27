"""Tests verifying execution of individual poisoning sweep cells, mu locks, and threshold delta bounds."""

from __future__ import annotations

import math

from datp.attacks.enums import AttackerObjective, PoisoningSourceStrategy
from datp.attacks.execution.bounded_sweep_cell import (
    SweepCellConfig,
    lock_mu_flag_threshold,
    run_sweep_cell,
)
from datp.attacks.planning.bounded_sweep_matrix import SweepCellSpec
from datp.attacks.score_containers import build_score_collection
from datp.core.enums import ThresholdPolicy
from datp.core.seeds import SeedPair
from datp.testsupport.synthetic_scores import (
    StandardScoreSetRequest,
    make_standard_score_set,
)


def _make_collection():
    """Helper to build standard mock ScoreCollection for sweep cell testing."""
    ss = make_standard_score_set(StandardScoreSetRequest(n_eligible=9, n_pending=1))
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    return build_score_collection(raw)


def _make_spec(
    *,
    victim_id,
    policy,
    source,
    fraction,
    training_seed,
    poisoning_seed,
    objective=AttackerObjective.THRESHOLD_RAISE,
):
    """Helper to construct SweepCellSpec instances."""
    return SweepCellSpec(
        seed_pair=SeedPair(training_seed=training_seed, poisoning_seed=poisoning_seed),
        victim_id=victim_id,
        policy=policy,
        objective=objective,
        source=source,
        fraction=fraction,
    )


def test_lock_mu_flag_threshold_is_deterministic():
    """Verify that lock_mu_flag_threshold computes the same value deterministically on a collection."""
    col = _make_collection()
    mu_a = lock_mu_flag_threshold(col)
    mu_b = lock_mu_flag_threshold(col)
    assert mu_a == mu_b
    assert mu_a >= 0.0


def test_run_sweep_cell_zero_fraction_gives_zero_delta():
    """Verify that running a sweep cell with fraction=0.0 produces a delta_tau of exactly 0.0."""
    col = _make_collection()
    mu_flag = lock_mu_flag_threshold(col)
    victim_id = col.eligible_ids[0]
    spec = _make_spec(
        victim_id=victim_id,
        policy=ThresholdPolicy.GLOBAL_THRESHOLD,
        source=PoisoningSourceStrategy.RANDOM_BENIGN,
        fraction=0.0,
        training_seed=0,
        poisoning_seed=100,
    )
    result = run_sweep_cell(
        spec, config=SweepCellConfig(collection=col, mu_flag_threshold=mu_flag)
    )
    delta = result.poisoned_metrics.delta_tau[victim_id].delta_tau
    assert math.isclose(delta, 0.0, abs_tol=1e-12)


def test_run_sweep_cell_high_source_raises_threshold():
    """Verify that high-score poisoning raises the local threshold (positive delta_tau)."""
    col = _make_collection()
    mu_flag = lock_mu_flag_threshold(col)
    victim_id = col.eligible_ids[0]
    spec = _make_spec(
        victim_id=victim_id,
        policy=ThresholdPolicy.LOCAL_THRESHOLD,
        source=PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
        fraction=0.40,
        training_seed=0,
        poisoning_seed=100,
    )
    result = run_sweep_cell(
        spec, config=SweepCellConfig(collection=col, mu_flag_threshold=mu_flag)
    )
    delta = result.poisoned_metrics.delta_tau[victim_id].delta_tau
    assert delta > 0.0


def test_run_sweep_cell_uses_passed_mu_flag_not_recomputed():
    """Verify that the sweep cell execution uses the provided mu_flag_threshold configuration directly."""
    col = _make_collection()
    victim_id = col.eligible_ids[0]
    real_mu = lock_mu_flag_threshold(col)
    sentinel_mu = real_mu + 999.0
    spec = _make_spec(
        victim_id=victim_id,
        policy=ThresholdPolicy.CLUSTER_THRESHOLD,
        source=PoisoningSourceStrategy.LOW_SCORE_BENIGN,
        objective=AttackerObjective.THRESHOLD_LOWER,
        fraction=0.20,
        training_seed=0,
        poisoning_seed=100,
    )
    result = run_sweep_cell(
        spec, config=SweepCellConfig(collection=col, mu_flag_threshold=sentinel_mu)
    )
    assert result.poisoned_metrics.mu_flag_threshold == sentinel_mu
