"""Tests for CP2 score containers and victim-set model (CP2-T025)."""

from __future__ import annotations

import numpy as np
import pytest

from datp.artifacts.poison_names import CP2_N_MIN
from datp.attacks.score_containers import (
    Cp2ScoreCollection,
    Cp2VictimSet,
    build_score_collection,
    build_victim_set,
)
from datp.testsupport.synthetic_scores import (
    make_eligible_client,
    make_pending_client,
    make_standard_score_set,
)


def _collection_from_synthetics() -> Cp2ScoreCollection:
    ss = make_standard_score_set(n_eligible=3, n_pending=1)
    raw = {
        c.client_id: (c.cal, c.test_benign, c.test_attack)
        for c in ss.clients
    }
    return build_score_collection(raw)


class TestCp2ScoreCollection:
    def test_eligible_pending_partition(self) -> None:
        col = _collection_from_synthetics()
        assert len(col.eligible_ids) == 3
        assert len(col.pending_ids) == 1
        assert set(col.eligible_ids) | set(col.pending_ids) == set(col.all_ids)

    def test_eligible_ids_sorted(self) -> None:
        col = _collection_from_synthetics()
        assert col.eligible_ids == tuple(sorted(col.eligible_ids))

    def test_cal_dict_all_clients(self) -> None:
        col = _collection_from_synthetics()
        cal = col.cal_dict()
        assert len(cal) == 4

    def test_eligible_cal_dict(self) -> None:
        col = _collection_from_synthetics()
        ecal = col.eligible_cal_dict()
        assert len(ecal) == 3
        for cid in ecal:
            assert cid in col.eligible_ids

    def test_coverage_ratio(self) -> None:
        col = _collection_from_synthetics()
        assert col.coverage_ratio == pytest.approx(3 / 4)

    def test_coverage_ratio_empty(self) -> None:
        col = build_score_collection({})
        assert col.coverage_ratio == 0.0

    def test_n_min_boundary(self) -> None:
        e = make_eligible_client(client_id="e0")
        p = make_pending_client(client_id="p0")
        raw = {
            e.client_id: (e.cal, e.test_benign, e.test_attack),
            p.client_id: (p.cal, p.test_benign, p.test_attack),
        }
        col = build_score_collection(raw)
        assert e.client_id in col.eligible_ids
        assert p.client_id in col.pending_ids


class TestCp2VictimSet:
    def test_victims_are_eligible(self) -> None:
        col = _collection_from_synthetics()
        vs = build_victim_set(col)
        assert vs.eligible_ids == col.eligible_ids

    def test_n_victims(self) -> None:
        col = _collection_from_synthetics()
        vs = build_victim_set(col)
        assert vs.n_victims == 3

    def test_victim_cal(self) -> None:
        col = _collection_from_synthetics()
        vs = build_victim_set(col)
        for vid in vs.eligible_ids:
            cal = vs.victim_cal(vid)
            assert isinstance(cal, np.ndarray)
            assert cal.shape[0] >= CP2_N_MIN

    def test_pending_not_victim(self) -> None:
        col = _collection_from_synthetics()
        vs = build_victim_set(col)
        for pid in col.pending_ids:
            with pytest.raises(ValueError, match="not an eligible victim"):
                vs.victim_cal(pid)
