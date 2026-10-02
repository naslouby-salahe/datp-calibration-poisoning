"""Tests verifying helper score container structures and dataset partitioning logic."""

from __future__ import annotations

import pytest

from datp.attacks.score_containers import (
    ScoreCollection,
    build_score_collection,
)
from tests_support.synthetic_scores import (
    StandardScoreSetRequest,
    make_eligible_client,
    make_pending_client,
    make_standard_score_set,
)


def _collection_from_synthetics() -> ScoreCollection:
    """Helper to build a ScoreCollection instance populated with standard synthetic client scores."""
    ss = make_standard_score_set(StandardScoreSetRequest(n_eligible=3, n_pending=1))
    raw = {c.client_id: (c.cal, c.test_benign, c.test_attack) for c in ss.clients}
    return build_score_collection(raw)


class TestScoreCollection:
    """Tests verifying sorting, formatting, and coverage ratio methods of ScoreCollection."""

    def test_eligible_pending_partition(self) -> None:
        """Verify that ScoreCollection partitions clients into eligible/pending arrays based on N_MIN sample count."""
        col = _collection_from_synthetics()
        assert len(col.eligibility.eligible_ids) == 3
        assert len(col.eligibility.pending_ids) == 1
        assert set(col.eligibility.eligible_ids) | set(col.eligibility.pending_ids) == set(col.all_ids)

    def test_eligible_ids_sorted(self) -> None:
        """Verify that the list of eligible client IDs is returned sorted alphabetically."""
        col = _collection_from_synthetics()
        assert col.eligibility.eligible_ids == tuple(sorted(col.eligibility.eligible_ids))

    def test_calibration_errors_include_all_clients(self) -> None:
        """Calibration error values retain each client's domain identity."""
        col = _collection_from_synthetics()
        calibration_errors = col.calibration_errors
        assert len(calibration_errors.clients) == 4

    def test_eligible_calibration_errors(self) -> None:
        """Eligible calibration errors contain only clients above the sample minimum."""
        col = _collection_from_synthetics()
        ecal = col.eligible_calibration_errors
        assert len(ecal.clients) == 3
        for client in ecal.clients:
            cid = client.client_id
            assert cid in col.eligibility.eligible_ids

    def test_coverage_ratio(self) -> None:
        """Verify that coverage_ratio computes correct fraction (eligible count / total count)."""
        col = _collection_from_synthetics()
        assert col.coverage_ratio == pytest.approx(3 / 4)

    def test_coverage_ratio_empty(self) -> None:
        """Verify that coverage_ratio returns 0.0 if the collection is empty."""
        col = build_score_collection({})
        assert col.coverage_ratio == pytest.approx(0.0)

    def test_n_min_boundary(self) -> None:
        """Verify partitioning boundary conditions around minimum calibration sample count N_MIN."""
        e = make_eligible_client(client_id="e0")
        p = make_pending_client(client_id="p0")
        raw = {
            e.client_id: (e.cal, e.test_benign, e.test_attack),
            p.client_id: (p.cal, p.test_benign, p.test_attack),
        }
        col = build_score_collection(raw)
        assert e.client_id in col.eligibility.eligible_ids
        assert p.client_id in col.eligibility.pending_ids


def test_score_collection_survives_pickle_round_trip() -> None:
    """Collections must pickle so process-based workers can receive them."""
    import pickle

    import numpy as np

    from datp.attacks.score_containers import build_score_collection

    collection = build_score_collection(
        {
            "a": (np.arange(200.0), np.zeros(5), np.ones(5)),
            "b": (np.arange(150.0), np.zeros(4), np.ones(4)),
        }
    )
    restored = pickle.loads(pickle.dumps(collection))
    assert restored.all_ids == collection.all_ids
    assert restored.eligibility.eligible_ids == collection.eligibility.eligible_ids
    assert np.array_equal(restored.clients["a"].cal, collection.clients["a"].cal)
