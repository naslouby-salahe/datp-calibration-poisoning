"""Tests verifying seed sequences derivation and RNG reproducibility invariants."""

from __future__ import annotations

import numpy as np
import pytest

from datp.core.seeds import (
    SeedRecord,
    derive_seed_record,
    make_seed_rng,
)
from datp.core.seeds import SeedPair


def _seed_record(
    *,
    training_seed: int,
    poisoning_seed: int,
    client_idx: int,
    scope_idx: int,
) -> SeedRecord:
    """Helper function to build a SeedRecord fixture."""
    return SeedRecord(
        pair=SeedPair(
            training_seed=training_seed,
            poisoning_seed=poisoning_seed,
        ),
        client_idx=client_idx,
        scope_idx=scope_idx,
    )


class TestSeedRecord:
    """Tests verifying entropy and immutability properties of SeedRecord."""

    def test_entropy_matches_inputs(self) -> None:
        """Verify that SeedRecord entropy matches the input seeds and indices."""
        record = _seed_record(
            training_seed=0, poisoning_seed=100, client_idx=3, scope_idx=0
        )
        assert record.entropy == (0, 100, 3, 0)

    def test_frozen_immutable(self) -> None:
        """Ensure SeedRecord fields are frozen and cannot be modified."""
        record = _seed_record(
            training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0
        )
        with pytest.raises(Exception):
            setattr(record, "training_seed", 99)

    def test_entropy_is_tuple_of_four(self) -> None:
        """Verify that SeedRecord entropy is represented as a 4-tuple."""
        record = _seed_record(
            training_seed=1, poisoning_seed=101, client_idx=2, scope_idx=1
        )
        assert isinstance(record.entropy, tuple)
        assert len(record.entropy) == 4


class TestDeriveSeedRecord:
    """Tests verifying derivation of SeedRecord from SeedPair."""

    def test_returns_correct_record(self) -> None:
        """Verify derived SeedRecord fields correspond to the source seeds and indices."""
        record = derive_seed_record(
            SeedPair(training_seed=2, poisoning_seed=102),
            client_idx=5,
            scope_idx=1,
        )
        assert record.training_seed == 2
        assert record.poisoning_seed == 102
        assert record.client_idx == 5
        assert record.scope_idx == 1


class TestMakeRng:
    """Tests verifying RNG generation and sequence properties using derived seed records."""

    def test_returns_numpy_generator(self) -> None:
        """Verify make_seed_rng return value is a numpy Generator instance."""
        rng = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0)
        )
        assert isinstance(rng, np.random.Generator)

    def test_same_inputs_produce_identical_sequences(self) -> None:
        """Confirm that identical seed records produce identical RNG sequences."""
        rng1 = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0)
        )
        rng2 = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0)
        )
        assert np.array_equal(rng1.random(10), rng2.random(10))

    def test_different_client_idx_produces_different_sequences(self) -> None:
        """Confirm that changing client index changes the generated RNG sequence."""
        rng0 = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0)
        )
        rng1 = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=100, client_idx=1, scope_idx=0)
        )
        assert not np.array_equal(rng0.random(10), rng1.random(10))

    def test_different_training_seed_produces_different_sequences(self) -> None:
        """Confirm that changing training seed changes the generated RNG sequence."""
        rng0 = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0)
        )
        rng1 = make_seed_rng(
            _seed_record(training_seed=1, poisoning_seed=100, client_idx=0, scope_idx=0)
        )
        assert not np.array_equal(rng0.random(10), rng1.random(10))

    def test_different_poisoning_seed_produces_different_sequences(self) -> None:
        """Confirm that changing poisoning seed changes the generated RNG sequence."""
        rng0 = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0)
        )
        rng1 = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=101, client_idx=0, scope_idx=0)
        )
        assert not np.array_equal(rng0.random(10), rng1.random(10))

    def test_different_child_indices_produce_different_sequences(self) -> None:
        """Confirm that specifying a child index produces a distinct RNG sequence."""
        rng0 = make_seed_rng(
            _seed_record(
                training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0
            ),
            child_index=0,
        )
        rng1 = make_seed_rng(
            _seed_record(
                training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0
            ),
            child_index=1,
        )
        assert not np.array_equal(rng0.random(10), rng1.random(10))

    def test_no_integer_addition_pattern(self) -> None:
        """Ensure no overlaps occur between configurations that sum to the same value."""
        rng_a = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=101, client_idx=0, scope_idx=0)
        )
        rng_b = make_seed_rng(
            _seed_record(training_seed=1, poisoning_seed=100, client_idx=0, scope_idx=0)
        )
        assert not np.array_equal(rng_a.random(20), rng_b.random(20))

    def test_all_seed_pairs_produce_distinct_sequences(self) -> None:
        """Confirm that paired seed-sequence generation is globally distinct."""
        training_seeds = tuple(range(10))
        poisoning_seeds = tuple(range(100, 110))
        sequences = []
        for ts, ps in zip(training_seeds, poisoning_seeds):
            rng = make_seed_rng(
                _seed_record(
                    training_seed=ts, poisoning_seed=ps, client_idx=0, scope_idx=0
                )
            )
            sequences.append(rng.random(10).tolist())

        assert len(sequences) == len({tuple(s) for s in sequences})
