"""Tests for cluster-assignment stability statistics."""

from __future__ import annotations

from datp.attacks.metrics.cluster_stability import (
    cluster_size_of,
    cluster_sizes,
    n_reassigned,
)

_CLEAN = {"a": "0", "b": "0", "c": "1", "d": "1", "e": "2"}


def test_sizes_sorted_descending() -> None:
    """Cluster sizes are reported largest first."""
    assert cluster_sizes(_CLEAN) == (2, 2, 1)


def test_size_of_client() -> None:
    """The size of a client's own cluster is returned."""
    assert cluster_size_of(_CLEAN, "e") == 1
    assert cluster_size_of(_CLEAN, "a") == 2


def test_relabeling_is_not_reassignment() -> None:
    """A pure label permutation reassigns nobody."""
    relabeled = {"a": "9", "b": "9", "c": "7", "d": "7", "e": "5"}
    assert n_reassigned(_CLEAN, relabeled) == 0


def test_moved_client_counts_all_affected_clients() -> None:
    """Moving one client changes the mate sets of every client in the touched clusters."""
    moved = {"a": "0", "b": "0", "c": "1", "d": "2", "e": "2"}
    assert n_reassigned(_CLEAN, moved) == 3
