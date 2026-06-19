"""Unit tests for multi-client (co-victim) injection.

Asserts co-victim streams are independent and reproducible. Execution of the
real multi-client matrix is gated; these tests use synthetic data only.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pytest

from datp.attacks.cell_runner import (
    InjectionOutcome,
    MultiInjectionOutcome,
    inject_multi_victim,
    inject_single_victim,
)
from datp.attacks.score_containers import ScoreCollection, build_score_collection
from datp.attacks.enums import PoisoningSourceStrategy
from datp.testsupport.synthetic_scores import make_standard_score_set

_SOURCE = PoisoningSourceStrategy.HIGH_SCORE_BENIGN


def _make_collection() -> ScoreCollection:
    ss = make_standard_score_set(n_eligible=9, n_pending=1)
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    return build_score_collection(raw)


def _multi(col: ScoreCollection, victim_ids: Sequence[str]) -> MultiInjectionOutcome:
    return inject_multi_victim(
        col,
        victim_ids=victim_ids,
        source=_SOURCE,
        fraction=0.40,
        training_seed=0,
        poisoning_seed=100,
        scope_idx=0,
    )


def _solo(col: ScoreCollection, victim_id: str) -> InjectionOutcome:
    return inject_single_victim(
        col,
        victim_id=victim_id,
        source=_SOURCE,
        fraction=0.40,
        training_seed=0,
        poisoning_seed=100,
        scope_idx=0,
    )


def test_each_covictim_stream_matches_single_victim_stream():
    """A co-victim's poisoned array equals what it gets when attacked alone."""
    col = _make_collection()
    v0, v1 = col.eligible_ids[0], col.eligible_ids[1]

    multi = _multi(col, [v0, v1])
    solo0 = _solo(col, v0)
    solo1 = _solo(col, v1)

    assert np.array_equal(multi.poisoned_cal[v0], solo0.poisoned_cal[v0])
    assert np.array_equal(multi.poisoned_cal[v1], solo1.poisoned_cal[v1])


def test_covictim_streams_are_independent():
    """Distinct co-victims draw distinct replacement positions (independent streams)."""
    col = _make_collection()
    v0, v1 = col.eligible_ids[0], col.eligible_ids[1]
    multi = _multi(col, [v0, v1])
    pos0 = multi.per_victim[v0].injection.positions_replaced
    pos1 = multi.per_victim[v1].injection.positions_replaced
    # Same length budget but the two independent streams do not coincide.
    assert not np.array_equal(np.sort(pos0), np.sort(pos1))


def test_non_victims_keep_exact_clean_cal():
    col = _make_collection()
    v0, v1 = col.eligible_ids[0], col.eligible_ids[1]
    multi = _multi(col, [v0, v1])
    for cid in col.eligible_ids:
        if cid not in (v0, v1):
            assert np.array_equal(multi.poisoned_cal[cid], col.clients[cid].cal)


def test_clean_arrays_not_mutated_in_place():
    col = _make_collection()
    v0, v1 = col.eligible_ids[0], col.eligible_ids[1]
    before = {cid: col.clients[cid].cal.copy() for cid in col.eligible_ids}
    _multi(col, [v0, v1])
    for cid in col.eligible_ids:
        assert np.array_equal(col.clients[cid].cal, before[cid])


def test_result_is_deterministic():
    col = _make_collection()
    v0, v1, v2 = col.eligible_ids[0], col.eligible_ids[1], col.eligible_ids[2]
    a = _multi(col, [v0, v1, v2])
    b = _multi(col, [v2, v1, v0])
    assert a.victim_ids == b.victim_ids  # canonical sorted order
    for cid in a.victim_ids:
        assert np.array_equal(a.poisoned_cal[cid], b.poisoned_cal[cid])


def test_requires_at_least_two_victims():
    col = _make_collection()
    with pytest.raises(ValueError, match="at least 2"):
        _multi(col, [col.eligible_ids[0]])


def test_rejects_duplicate_victims():
    col = _make_collection()
    v0 = col.eligible_ids[0]
    with pytest.raises(ValueError, match="unique"):
        _multi(col, [v0, v0])
