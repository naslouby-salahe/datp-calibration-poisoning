from __future__ import annotations

from datp.types import (
    ClientId,
    ClusterId,
    SampleCount,
    SignedCount,
)


from collections import Counter
from collections.abc import Mapping



def cluster_sizes(assignments: Mapping[ClientId, ClusterId]) -> tuple[SignedCount, ...]:
    return tuple(sorted(Counter(assignments.values()).values(), reverse=True))


def cluster_size_of(
    assignments: Mapping[ClientId, ClusterId], client_id: ClientId
) -> SignedCount:
    own = assignments[client_id]
    return sum(1 for label in assignments.values() if label == own)


def _mates(
    assignments: Mapping[ClientId, ClusterId], client_id: ClientId
) -> frozenset[ClientId]:
    own = assignments[client_id]
    return frozenset(c for c, label in assignments.items() if label == own)


def n_reassigned(
    clean: Mapping[ClientId, ClusterId], poisoned: Mapping[ClientId, ClusterId]
) -> SampleCount:
    return sum(1 for cid in clean if _mates(clean, cid) != _mates(poisoned, cid))
