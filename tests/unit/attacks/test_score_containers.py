"""Tests verifying helper score container structures and dataset partitioning logic."""

from __future__ import annotations

import numpy as np
import pytest

from datp.attacks.constants import N_MIN
from datp.attacks.score_containers import (
    ScoreCollection,
    build_score_collection,
    build_victim_set,
)
from datp.testsupport.synthetic_scores import (
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
        assert len(col.eligible_ids) == 3
        assert len(col.pending_ids) == 1
        assert set(col.eligible_ids) | set(col.pending_ids) == set(col.all_ids)

    def test_eligible_ids_sorted(self) -> None:
        """Verify that the list of eligible client IDs is returned sorted alphabetically."""
        col = _collection_from_synthetics()
        assert col.eligible_ids == tuple(sorted(col.eligible_ids))

    def test_cal_dict_all_clients(self) -> None:
        """Verify that cal_dict contains error scores for all client devices regardless of status."""
        col = _collection_from_synthetics()
        cal = col.cal_dict()
        assert len(cal) == 4

    def test_eligible_cal_dict(self) -> None:
        """Verify that eligible_cal_dict maps error scores for eligible client IDs only."""
        col = _collection_from_synthetics()
        ecal = col.eligible_cal_dict()
        assert len(ecal) == 3
        for cid in ecal:
            assert cid in col.eligible_ids

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
        assert e.client_id in col.eligible_ids
        assert p.client_id in col.pending_ids


class TestVictimSet:
    """Tests verifying accessors, counts, and validation checks of the victim sets."""

    def test_victims_are_eligible(self) -> None:
        """Verify that the list of victim IDs matches the list of eligible client IDs."""
        col = _collection_from_synthetics()
        vs = build_victim_set(col)
        assert vs.eligible_ids == col.eligible_ids

    def test_n_victims(self) -> None:
        """Verify that the victim count equals the eligible client count."""
        col = _collection_from_synthetics()
        vs = build_victim_set(col)
        assert vs.n_victims == 3

    def test_victim_cal(self) -> None:
        """Verify that victim_cal returns a non-empty array of calibration scores for eligible clients."""
        col = _collection_from_synthetics()
        vs = build_victim_set(col)
        for vid in vs.eligible_ids:
            cal = vs.victim_cal(vid)
            assert isinstance(cal, np.ndarray)
            assert cal.shape[0] >= N_MIN

    def test_pending_not_victim(self) -> None:
        """Verify that victim_cal raises a ValueError if called on a pending/ineligible client ID."""
        col = _collection_from_synthetics()
        vs = build_victim_set(col)
        for pid in col.pending_ids:
            with pytest.raises(ValueError, match="is not eligible"):
                vs.victim_cal(pid)
