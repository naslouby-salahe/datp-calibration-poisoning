"""Tests for deterministic seed derivation."""

from __future__ import annotations

import numpy as np
import pytest

from datp.core.seed_sequence import (
    SeedRecord,
    derive_seed_record,
    make_seed_rng,
)


class TestSeedRecord:
    def test_entropy_matches_inputs(self) -> None:
        record = SeedRecord(
            training_seed=0, poisoning_seed=100, client_idx=3, scope_idx=0
        )
        assert record.entropy == (0, 100, 3, 0)

    def test_frozen_immutable(self) -> None:
        record = SeedRecord(
            training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0
        )
        with pytest.raises(Exception):
            record.training_seed = 99 # type: ignore[misc]

    def test_entropy_is_tuple_of_four(self) -> None:
        record = SeedRecord(
            training_seed=1, poisoning_seed=101, client_idx=2, scope_idx=1
        )
        assert isinstance(record.entropy, tuple)
        assert len(record.entropy) == 4


class TestDeriveSeedRecord:
    def test_returns_correct_record(self) -> None:
        record = derive_seed_record(
            training_seed=2,
            poisoning_seed=102,
            client_idx=5,
            scope_idx=1,
        )
        assert record.training_seed == 2
        assert record.poisoning_seed == 102
        assert record.client_idx == 5
        assert record.scope_idx == 1

    def test_is_seed_record_instance(self) -> None:
        record = derive_seed_record(
            training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0
        )
        assert isinstance(record, SeedRecord)


class TestMakeRng:
    def test_returns_numpy_generator(self) -> None:
        rng = make_seed_rng(
            training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0
        )
        assert isinstance(rng, np.random.Generator)

    def test_same_inputs_produce_identical_sequences(self) -> None:
        rng1 = make_seed_rng(
            training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0
        )
        rng2 = make_seed_rng(
            training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0
        )
        assert np.array_equal(rng1.random(10), rng2.random(10))

    def test_different_client_idx_produces_different_sequences(self) -> None:
        rng0 = make_seed_rng(
            training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0
        )
        rng1 = make_seed_rng(
            training_seed=0, poisoning_seed=100, client_idx=1, scope_idx=0
        )
        assert not np.array_equal(rng0.random(10), rng1.random(10))

    def test_different_training_seed_produces_different_sequences(self) -> None:
        rng0 = make_seed_rng(
            training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0
        )
        rng1 = make_seed_rng(
            training_seed=1, poisoning_seed=100, client_idx=0, scope_idx=0
        )
        assert not np.array_equal(rng0.random(10), rng1.random(10))

    def test_different_poisoning_seed_produces_different_sequences(self) -> None:
        rng0 = make_seed_rng(
            training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0
        )
        rng1 = make_seed_rng(
            training_seed=0, poisoning_seed=101, client_idx=0, scope_idx=0
        )
        assert not np.array_equal(rng0.random(10), rng1.random(10))

    def test_different_child_indices_produce_different_sequences(self) -> None:
        rng0 = make_seed_rng(
            training_seed=0, poisoning_seed=100, client_idx=0,
            scope_idx=0, child_index=0,
        )
        rng1 = make_seed_rng(
            training_seed=0, poisoning_seed=100, client_idx=0,
            scope_idx=0, child_index=1,
        )
        assert not np.array_equal(rng0.random(10), rng1.random(10))

    def test_no_integer_addition_pattern(self) -> None:
        # Verify that the protocol uses SeedSequence, not integer addition.
        # If integer addition were used: seed = training_seed + poisoning_seed
        # which would conflate (0, 101) with (1, 100). Verify they differ.
        rng_a = make_seed_rng(
            training_seed=0, poisoning_seed=101, client_idx=0, scope_idx=0
        )
        rng_b = make_seed_rng(
            training_seed=1, poisoning_seed=100, client_idx=0, scope_idx=0
        )
        assert not np.array_equal(rng_a.random(20), rng_b.random(20))

    def test_all_seed_pairs_produce_distinct_sequences(self) -> None:
        training_seeds = (0, 1, 2, 3, 4)
        poisoning_seeds = (100, 101, 102, 103, 104)
        sequences = []
        for ts, ps in zip(training_seeds, poisoning_seeds):
            rng = make_seed_rng(
                training_seed=ts, poisoning_seed=ps, client_idx=0, scope_idx=0
            )
            sequences.append(rng.random(10).tolist())
        # All 5 paired sequences must be distinct.
        assert len(sequences) == len({tuple(s) for s in sequences})
