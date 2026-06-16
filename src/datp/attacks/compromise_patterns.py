"""Deterministic multi-client compromise-pattern selection.

Selects which co-victim groups are attacked together under the MULTI_CLIENT
target scope: all eligible pairs (optionally capped) and a fixed count of
triples. Selection is driven solely by ``compromise_pattern_seed`` via
``SeedSequence`` — never integer seed addition — and is independent of the
per-victim injection streams (those are keyed by client index in the
calibration-poisoning seed scheme, giving each co-victim an independent stream).
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations

import numpy as np

from datp.artifacts.poison_names import COMPROMISE_PATTERN_SEED

DEFAULT_N_TRIPLES: int = 20


def _pattern_rng(compromise_pattern_seed: int) -> np.random.Generator:
    """Reproducible generator for pattern selection (SeedSequence, no addition)."""
    return np.random.default_rng(np.random.SeedSequence([compromise_pattern_seed]))


def _sorted_unique(victim_ids: Sequence[str]) -> list[str]:
    ordered = sorted(set(victim_ids))
    if len(ordered) != len(victim_ids):
        raise ValueError(f"victim_ids must be unique; got {list(victim_ids)!r}")
    return ordered


def select_pairs(
    victim_ids: Sequence[str],
    *,
    compromise_pattern_seed: int = COMPROMISE_PATTERN_SEED,
    max_pairs: int | None = None,
) -> tuple[tuple[str, str], ...]:
    """Select co-victim pairs from eligible victims.

    Returns all eligible pairs in deterministic sorted order. If ``max_pairs``
    is given and there are more candidate pairs than that, a reproducible
    seeded subset of exactly ``max_pairs`` pairs is returned (caps combinatorial
    blow-up while staying deterministic).
    """
    ordered = _sorted_unique(victim_ids)
    all_pairs = [tuple(c) for c in combinations(ordered, 2)]
    if max_pairs is None or len(all_pairs) <= max_pairs:
        return tuple(all_pairs)  # type: ignore[return-value]
    rng = _pattern_rng(compromise_pattern_seed)
    chosen = rng.choice(len(all_pairs), size=max_pairs, replace=False)
    return tuple(all_pairs[i] for i in sorted(int(i) for i in chosen))  # type: ignore[return-value]


def select_triples(
    victim_ids: Sequence[str],
    *,
    n_triples: int = DEFAULT_N_TRIPLES,
    compromise_pattern_seed: int = COMPROMISE_PATTERN_SEED,
) -> tuple[tuple[str, str, str], ...]:
    """Select exactly ``n_triples`` distinct co-victim triples.

    Triples are drawn without replacement from all eligible triples using a
    reproducible ``SeedSequence``-seeded generator, then returned in sorted
    order. Raises ``ValueError`` if fewer than ``n_triples`` triples exist.
    """
    if n_triples <= 0:
        raise ValueError(f"n_triples must be positive; got {n_triples}")
    ordered = _sorted_unique(victim_ids)
    all_triples = [tuple(c) for c in combinations(ordered, 3)]
    if len(all_triples) < n_triples:
        raise ValueError(
            f"only {len(all_triples)} triples available from {len(ordered)} "
            f"victims; cannot select {n_triples}"
        )
    rng = _pattern_rng(compromise_pattern_seed)
    chosen = rng.choice(len(all_triples), size=n_triples, replace=False)
    return tuple(all_triples[i] for i in sorted(int(i) for i in chosen))  # type: ignore[return-value]
