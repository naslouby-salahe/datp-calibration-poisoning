"""Tests for cluster-assignment stability statistics."""

from __future__ import annotations

from datp.attacks.metrics.cluster_stability import (
    cluster_size_of,
    cluster_sizes,
    n_reassigned,
)
from datp.types import ClientId, ClusterId

_CLEAN = {
    ClientId("a"): ClusterId("0"),
    ClientId("b"): ClusterId("0"),
    ClientId("c"): ClusterId("1"),
    ClientId("d"): ClusterId("1"),
    ClientId("e"): ClusterId("2"),
}


def test_sizes_sorted_descending() -> None:
    """Cluster sizes are reported largest first."""
    assert cluster_sizes(_CLEAN) == (2, 2, 1)


def test_size_of_client() -> None:
    """The size of a client's own cluster is returned."""
    assert cluster_size_of(_CLEAN, ClientId("e")) == 1
    assert cluster_size_of(_CLEAN, ClientId("a")) == 2


def test_relabeling_is_not_reassignment() -> None:
    """A pure label permutation reassigns nobody."""
    relabeled = {
        ClientId("a"): ClusterId("9"),
        ClientId("b"): ClusterId("9"),
        ClientId("c"): ClusterId("7"),
        ClientId("d"): ClusterId("7"),
        ClientId("e"): ClusterId("5"),
    }
    assert n_reassigned(_CLEAN, relabeled) == 0


def test_moved_client_counts_all_affected_clients() -> None:
    """Moving one client changes the mate sets of every client in the touched clusters."""
    moved = {
        ClientId("a"): ClusterId("0"),
        ClientId("b"): ClusterId("0"),
        ClientId("c"): ClusterId("1"),
        ClientId("d"): ClusterId("2"),
        ClientId("e"): ClusterId("2"),
    }
    assert n_reassigned(_CLEAN, moved) == 3
