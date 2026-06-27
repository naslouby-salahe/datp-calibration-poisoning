"""Tests verifying selection patterns of victim triples and pairs for calibration poisoning sweeps."""

from __future__ import annotations

import pytest

from datp.attacks.constants import COMPROMISE_PATTERN_SEED
from datp.attacks.planning.compromise_patterns import (
    DEFAULT_N_TRIPLES,
    select_pairs,
    select_triples,
)

_VICTIMS = ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8")


def test_default_triple_count_matches_lock() -> None:
    """Verify that the default triple count constant matches standard setting of 12."""
    assert DEFAULT_N_TRIPLES == 12


def test_select_triples_returns_exactly_twelve_by_default() -> None:
    """Verify that select_triples returns exactly twelve entries by default."""
    triples = select_triples(_VICTIMS)
    assert len(triples) == 12


def test_select_triples_are_distinct_and_valid() -> None:
    """Verify that all selected triples contain unique items sorted alphabetically."""
    triples = select_triples(_VICTIMS)
    assert len(set(triples)) == 12
    for t in triples:
        assert len(t) == 3
        assert len(set(t)) == 3
        assert set(t).issubset(set(_VICTIMS))
        assert list(t) == sorted(t)


def test_select_triples_is_deterministic_with_seed_400() -> None:
    """Verify that select_triples outputs identical selections with fixed seed."""
    a = select_triples(_VICTIMS, compromise_pattern_seed=COMPROMISE_PATTERN_SEED)
    b = select_triples(_VICTIMS, compromise_pattern_seed=COMPROMISE_PATTERN_SEED)
    assert a == b


def test_select_triples_differs_for_different_seed() -> None:
    """Verify that different selection seeds result in distinct client triples."""
    a = select_triples(_VICTIMS, compromise_pattern_seed=400)
    b = select_triples(_VICTIMS, compromise_pattern_seed=401)
    assert a != b


def test_select_triples_raises_when_too_few_victims() -> None:
    """Verify that requesting more triples than mathematically possible raises ValueError."""
    with pytest.raises(ValueError, match="cannot select"):
        select_triples(("c0", "c1", "c2"), n_triples=20)


def test_select_triples_rejects_nonpositive_count() -> None:
    """Verify that requesting a zero or negative triple count raises ValueError."""
    with pytest.raises(ValueError, match="positive"):
        select_triples(_VICTIMS, n_triples=0)


def test_select_pairs_returns_all_pairs_by_default() -> None:
    """Verify that select_pairs returns all possible unique victim pairs sorted lexicographically."""
    pairs = select_pairs(_VICTIMS)
    assert len(pairs) == 36
    assert len(set(pairs)) == len(pairs)
    for p in pairs:
        assert list(p) == sorted(p)


def test_select_pairs_is_deterministic() -> None:
    """Verify that select_pairs is deterministic across identical calls."""
    assert select_pairs(_VICTIMS) == select_pairs(_VICTIMS)


def test_select_pairs_cap_takes_first_lexicographic_pairs() -> None:
    """Verify that max_pairs limits the selection to the first N lexicographic pairs."""
    capped = select_pairs(_VICTIMS, max_pairs=10)
    assert len(capped) == 10
    assert capped == select_pairs(_VICTIMS)[:10]


def test_select_rejects_duplicate_victims() -> None:
    """Verify that selection raises ValueError if the victim pools contain duplicates."""
    with pytest.raises(ValueError, match="unique"):
        select_triples(("c0", "c0", "c1", "c2"))
