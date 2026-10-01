"""Cluster-assignment stability statistics between clean and poisoned clusterings."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping


def cluster_sizes(assignments: Mapping[str, str]) -> tuple[int, ...]:
    """Return cluster sizes sorted in descending order."""
    return tuple(sorted(Counter(assignments.values()).values(), reverse=True))


def cluster_size_of(assignments: Mapping[str, str], client_id: str) -> int:
    """Return the size of the cluster containing a client."""
    own = assignments[client_id]
    return sum(1 for label in assignments.values() if label == own)


def _mates(assignments: Mapping[str, str], client_id: str) -> frozenset[str]:
    own = assignments[client_id]
    return frozenset(c for c, label in assignments.items() if label == own)


def n_reassigned(clean: Mapping[str, str], poisoned: Mapping[str, str]) -> int:
    """Count clients whose cluster membership set differs between clean and poisoned clusterings."""
    return sum(1 for cid in clean if _mates(clean, cid) != _mates(poisoned, cid))
