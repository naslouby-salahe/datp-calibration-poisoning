"""Tests for synthetic score fixtures ."""

from __future__ import annotations

import numpy as np
import pytest

from datp.artifacts.poison_names import N_MIN
from datp.scoring.schema import SCORE_COLUMN
from datp.testsupport.synthetic_scores import (
    make_degenerate_tail_client,
    make_eligible_client,
    make_pending_client,
    make_standard_score_set,
    make_synthetic_client,
)


class TestMakeSyntheticClient:
    def test_deterministic(self) -> None:
        a = make_synthetic_client(client_id="c0", client_idx=0)
        b = make_synthetic_client(client_id="c0", client_idx=0)
        np.testing.assert_array_equal(a.cal, b.cal)
        np.testing.assert_array_equal(a.test_benign, b.test_benign)
        np.testing.assert_array_equal(a.test_attack, b.test_attack)

    def test_different_seeds_differ(self) -> None:
        a = make_synthetic_client(client_id="c0", client_idx=0, training_seed=0)
        b = make_synthetic_client(client_id="c0", client_idx=0, training_seed=1)
        assert not np.array_equal(a.cal, b.cal)

    def test_different_clients_differ(self) -> None:
        a = make_synthetic_client(client_id="c0", client_idx=0)
        b = make_synthetic_client(client_id="c1", client_idx=1)
        assert not np.array_equal(a.cal, b.cal)

    def test_shapes(self) -> None:
        c = make_synthetic_client(
            client_id="c0",
            n_cal=150,
            n_test_benign=30,
            n_test_attack=40,
        )
        assert c.cal.shape == (150,)
        assert c.test_benign.shape == (30,)
        assert c.test_attack.shape == (40,)

    def test_non_negative(self) -> None:
        c = make_synthetic_client(client_id="c0")
        assert np.all(c.cal >= 0.0)
        assert np.all(c.test_benign >= 0.0)
        assert np.all(c.test_attack >= 0.0)

    def test_attack_scores_higher_than_benign(self) -> None:
        c = make_synthetic_client(client_id="c0")
        assert np.mean(c.test_attack) > np.mean(c.test_benign)

    def test_score_column_attribute(self) -> None:
        c = make_synthetic_client(client_id="c0")
        assert c.score_column == SCORE_COLUMN


class TestEligibility:
    def test_eligible_client_is_eligible(self) -> None:
        c = make_eligible_client()
        assert c.is_eligible
        assert c.n_cal >= N_MIN

    def test_pending_client_is_not_eligible(self) -> None:
        c = make_pending_client()
        assert not c.is_eligible
        assert c.n_cal < N_MIN

    def test_boundary_eligible(self) -> None:
        c = make_synthetic_client(client_id="c0", n_cal=N_MIN)
        assert c.is_eligible

    def test_boundary_pending(self) -> None:
        c = make_synthetic_client(client_id="c0", n_cal=N_MIN - 1)
        assert not c.is_eligible


class TestDegenerateTailClient:
    def test_is_eligible(self) -> None:
        c = make_degenerate_tail_client()
        assert c.is_eligible

    def test_cal_constant(self) -> None:
        c = make_degenerate_tail_client()
        assert len(np.unique(c.cal)) == 1

    def test_upper_tail_degenerate(self) -> None:
        c = make_degenerate_tail_client()
        n_tail = max(1, int(0.10 * c.n_cal))
        upper_tail = np.sort(c.cal)[-n_tail:]
        assert len(np.unique(upper_tail)) < 2

    def test_lower_tail_degenerate(self) -> None:
        c = make_degenerate_tail_client()
        n_tail = max(1, int(0.10 * c.n_cal))
        lower_tail = np.sort(c.cal)[:n_tail]
        assert len(np.unique(lower_tail)) < 2


class TestStandardScoreSet:
    def test_default_counts(self) -> None:
        ss = make_standard_score_set()
        assert len(ss.eligible) == 9
        assert len(ss.pending) == 1
        assert len(ss.clients) == 10

    def test_eligible_ids(self) -> None:
        ss = make_standard_score_set()
        assert all(c.startswith("eligible_") for c in ss.eligible_ids)

    def test_pending_ids(self) -> None:
        ss = make_standard_score_set()
        assert all(c.startswith("pending_") for c in ss.pending_ids)

    def test_calibration_scores(self) -> None:
        ss = make_standard_score_set()
        cal = ss.calibration_scores
        assert len(cal) == 10
        for client in cal.clients:
            assert isinstance(client.scores, np.ndarray)

    def test_client_by_id(self) -> None:
        ss = make_standard_score_set()
        c = ss.client_by_id("eligible_0")
        assert c.client_id == "eligible_0"

    def test_client_by_id_missing(self) -> None:
        ss = make_standard_score_set()
        with pytest.raises(KeyError):
            ss.client_by_id("nonexistent")

    def test_with_degenerate(self) -> None:
        ss = make_standard_score_set(include_degenerate=True)
        assert len(ss.clients) == 11
        degen = ss.client_by_id("degenerate_0")
        assert degen.is_eligible
        assert len(np.unique(degen.cal)) == 1

    def test_deterministic(self) -> None:
        a = make_standard_score_set()
        b = make_standard_score_set()
        for ca, cb in zip(a.clients, b.clients):
            np.testing.assert_array_equal(ca.cal, cb.cal)

    def test_custom_counts(self) -> None:
        ss = make_standard_score_set(n_eligible=3, n_pending=2)
        assert len(ss.eligible) == 3
        assert len(ss.pending) == 2
