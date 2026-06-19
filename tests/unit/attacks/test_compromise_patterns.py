"""Unit tests for multi-client compromise-pattern selection.

Execution of multi-client runs is gated; these tests cover pattern selection
determinism and independence only.
"""

from __future__ import annotations

import pytest

from datp.attacks.constants import COMPROMISE_PATTERN_SEED
from datp.attacks.compromise_patterns import (
    DEFAULT_N_TRIPLES,
    select_pairs,
    select_triples,
)

_VICTIMS = ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8")


def test_default_triple_count_is_twenty():
    assert DEFAULT_N_TRIPLES == 20


def test_select_triples_returns_exactly_twenty():
    triples = select_triples(_VICTIMS)
    assert len(triples) == 20


def test_select_triples_are_distinct_and_valid():
    triples = select_triples(_VICTIMS)
    assert len(set(triples)) == 20
    for t in triples:
        assert len(t) == 3
        assert len(set(t)) == 3
        assert set(t).issubset(set(_VICTIMS))
        assert list(t) == sorted(t)


def test_select_triples_is_deterministic_with_seed_400():
    a = select_triples(_VICTIMS, compromise_pattern_seed=COMPROMISE_PATTERN_SEED)
    b = select_triples(_VICTIMS, compromise_pattern_seed=COMPROMISE_PATTERN_SEED)
    assert a == b


def test_select_triples_differs_for_different_seed():
    a = select_triples(_VICTIMS, compromise_pattern_seed=400)
    b = select_triples(_VICTIMS, compromise_pattern_seed=401)
    assert a != b


def test_select_triples_raises_when_too_few_victims():
    with pytest.raises(ValueError, match="cannot select"):
        select_triples(("c0", "c1", "c2"), n_triples=20)


def test_select_triples_rejects_nonpositive_count():
    with pytest.raises(ValueError, match="positive"):
        select_triples(_VICTIMS, n_triples=0)


def test_select_pairs_returns_all_pairs_by_default():
    pairs = select_pairs(_VICTIMS)
    assert len(pairs) == 36
    assert len(set(pairs)) == len(pairs)
    for p in pairs:
        assert list(p) == sorted(p)


def test_select_pairs_is_deterministic():
    assert select_pairs(_VICTIMS) == select_pairs(_VICTIMS)


def test_select_pairs_caps_with_seed():
    capped = select_pairs(_VICTIMS, max_pairs=10)
    assert len(capped) == 10
    assert len(set(capped)) == 10
    # Reproducible under the same seed.
    assert capped == select_pairs(_VICTIMS, max_pairs=10)


def test_select_rejects_duplicate_victims():
    with pytest.raises(ValueError, match="unique"):
        select_triples(("c0", "c0", "c1", "c2"))
