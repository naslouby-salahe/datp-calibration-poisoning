"""Tests verifying multi-victim poisoning injection strategies and independence of parallel random streams."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pytest

from datp.attacks.enums import PoisoningSourceStrategy
from datp.attacks.execution.cell_runner import (
    InjectionOutcome,
    InjectionSpec,
    MultiInjectionOutcome,
    inject_multi_victim,
    inject_single_victim,
)
from datp.attacks.score_containers import ScoreCollection, build_score_collection
from datp.core.seeds import SeedPair
from datp.testsupport.synthetic_scores import (
    StandardScoreSetRequest,
    make_standard_score_set,
)

_SOURCE = PoisoningSourceStrategy.HIGH_SCORE_BENIGN


def _make_collection() -> ScoreCollection:
    """Helper to build a standard mock ScoreCollection for injection testing."""
    ss = make_standard_score_set(StandardScoreSetRequest(n_eligible=9, n_pending=1))
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    return build_score_collection(raw)


def _multi(col: ScoreCollection, victim_ids: Sequence[str]) -> MultiInjectionOutcome:
    """Helper to execute multi-victim injection on a collection."""
    return inject_multi_victim(
        col,
        victim_ids=victim_ids,
        spec=InjectionSpec(
            source=_SOURCE,
            fraction=0.40,
            seed_pair=SeedPair(training_seed=0, poisoning_seed=100),
            objective=None,
            scope_idx=0,
        ),
    )


def _solo(col: ScoreCollection, victim_id: str) -> InjectionOutcome:
    """Helper to execute single-victim injection on a collection."""
    return inject_single_victim(
        col,
        victim_id=victim_id,
        spec=InjectionSpec(
            source=_SOURCE,
            fraction=0.40,
            seed_pair=SeedPair(training_seed=0, poisoning_seed=100),
            objective=None,
            scope_idx=0,
        ),
    )


def test_each_covictim_stream_matches_single_victim_stream() -> None:
    """Verify that each co-victim client stream behaves identically to its solo injection baseline."""
    col = _make_collection()
    v0, v1 = col.eligible_ids[0], col.eligible_ids[1]

    multi = _multi(col, [v0, v1])
    solo0 = _solo(col, v0)
    solo1 = _solo(col, v1)

    assert np.array_equal(
        multi.poisoned_cal_set.for_client(v0).cal,
        solo0.poisoned_cal_set.for_client(v0).cal,
    )
    assert np.array_equal(
        multi.poisoned_cal_set.for_client(v1).cal,
        solo1.poisoned_cal_set.for_client(v1).cal,
    )


def test_covictim_streams_are_independent() -> None:
    """Verify that co-victim client streams draw replacements from independent random streams."""
    col = _make_collection()
    v0, v1 = col.eligible_ids[0], col.eligible_ids[1]
    multi = _multi(col, [v0, v1])
    pos0 = multi.for_victim(v0).injection.positions_replaced
    pos1 = multi.for_victim(v1).injection.positions_replaced

    assert not np.array_equal(np.sort(pos0), np.sort(pos1))


def test_non_victims_keep_exact_clean_cal() -> None:
    """Verify that non-victim client error scores are left completely unpoisoned/clean."""
    col = _make_collection()
    v0, v1 = col.eligible_ids[0], col.eligible_ids[1]
    multi = _multi(col, [v0, v1])
    for cid in col.eligible_ids:
        if cid not in (v0, v1):
            assert np.array_equal(
                multi.poisoned_cal_set.for_client(cid).cal, col.clients[cid].cal
            )


def test_clean_arrays_not_mutated_in_place() -> None:
    """Verify that source score arrays within the collection are not modified in-place."""
    col = _make_collection()
    v0, v1 = col.eligible_ids[0], col.eligible_ids[1]
    before = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
    _multi(col, [v0, v1])
    for cid in col.eligible_ids:
        assert np.array_equal(col.clients[cid].cal, before[cid])


def test_result_is_deterministic() -> None:
    """Verify that multi-victim injection is deterministic and order-independent."""
    col = _make_collection()
    v0, v1, v2 = col.eligible_ids[0], col.eligible_ids[1], col.eligible_ids[2]
    a = _multi(col, [v0, v1, v2])
    b = _multi(col, [v2, v1, v0])
    assert a.victim_ids == b.victim_ids
    for cid in a.victim_ids:
        assert np.array_equal(
            a.poisoned_cal_set.for_client(cid).cal,
            b.poisoned_cal_set.for_client(cid).cal,
        )


def test_requires_at_least_two_victims() -> None:
    """Verify that inject_multi_victim raises ValueError if passed fewer than 2 victims."""
    col = _make_collection()
    with pytest.raises(ValueError, match="at least 2"):
        _multi(col, [col.eligible_ids[0]])


def test_rejects_duplicate_victims() -> None:
    """Verify that inject_multi_victim raises ValueError if duplicate client IDs are passed."""
    col = _make_collection()
    v0 = col.eligible_ids[0]
    with pytest.raises(ValueError, match="unique"):
        _multi(col, [v0, v0])
