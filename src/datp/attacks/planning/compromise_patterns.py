"""Compromise-pattern selection: pairs and triples of victim clients."""

from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations

import numpy as np

from datp.attacks.constants import COMPROMISE_PATTERN_SEED

DEFAULT_N_TRIPLES: int = 12


def _sorted_unique(victim_ids: Sequence[str]) -> list[str]:
    """Sort and deduplicate victim IDs, raising on duplicates."""
    if len(ordered := sorted(set(victim_ids))) != len(victim_ids):
        raise ValueError(f"victim_ids must be unique; got {list(victim_ids)!r}")
    return ordered


def _sample_combinations(items: tuple, size: int, seed: int) -> tuple:
    """Sample a fixed-size subset of items using a seeded RNG."""
    if len(items) <= size:
        return items
    rng = np.random.default_rng(np.random.SeedSequence([seed]))
    chosen = np.sort(rng.choice(len(items), size=size, replace=False))
    return tuple(items[i] for i in chosen)


def select_pairs(
    victim_ids: Sequence[str],
    *,
    max_pairs: int | None = None,
) -> tuple[tuple[str, str], ...]:
    """Select all 2-combinations of victim IDs, optionally capped."""
    all_pairs = tuple(combinations(_sorted_unique(victim_ids), 2))
    if max_pairs is None:
        return all_pairs
    if max_pairs < 0:
        raise ValueError(f"max_pairs must be non-negative; got {max_pairs}")
    return all_pairs[:max_pairs]


def select_triples(
    victim_ids: Sequence[str],
    *,
    n_triples: int = DEFAULT_N_TRIPLES,
    compromise_pattern_seed: int = COMPROMISE_PATTERN_SEED,
) -> tuple[tuple[str, str, str], ...]:
    """Select a random sample of 3-combinations from victim IDs."""
    if n_triples <= 0:
        raise ValueError(f"n_triples must be positive; got {n_triples}")

    all_triples = tuple(combinations(_sorted_unique(victim_ids), 3))
    if len(all_triples) < n_triples:
        raise ValueError(
            f"only {len(all_triples)} available; cannot select {n_triples}"
        )

    return _sample_combinations(all_triples, n_triples, compromise_pattern_seed)
