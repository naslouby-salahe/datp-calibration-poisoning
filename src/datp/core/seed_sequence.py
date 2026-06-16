"""Deterministic seed derivation using numpy SeedSequence.

No integer seed addition. Co-victims differ by client_idx (independent streams
by construction). Every derived child seed is reproducible from the parent entropy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class SeedRecord:
    """Canonical record of SeedSequence inputs for one experiment cell.

    Embed this in every run manifest so any run can be reproduced exactly.
    """

    training_seed: int
    poisoning_seed: int
    client_idx: int
    scope_idx: int

    @property
    def entropy(self) -> tuple[int, int, int, int]:
        """The exact SeedSequence entropy list used to create child generators."""
        return (
            self.training_seed,
            self.poisoning_seed,
            self.client_idx,
            self.scope_idx,
        )


def _parent_sequence(record: SeedRecord) -> np.random.SeedSequence:
    return np.random.SeedSequence(list(record.entropy))


def make_seed_rng(
    *,
    training_seed: int,
    poisoning_seed: int,
    client_idx: int,
    scope_idx: int,
    child_index: int = 0,
) -> np.random.Generator:
    """Return a reproducible NumPy Generator for one experiment cell.

    Uses SeedSequence([training_seed, poisoning_seed, client_idx, scope_idx])
    and spawns child generators. ``child_index`` selects which child stream.

    Do NOT use integer seed addition (forbidden by protocol).
    """
    record = SeedRecord(
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        client_idx=client_idx,
        scope_idx=scope_idx,
    )
    parent = _parent_sequence(record)
    children = parent.spawn(child_index + 1)
    return np.random.default_rng(children[child_index])


def derive_seed_record(
    *,
    training_seed: int,
    poisoning_seed: int,
    client_idx: int,
    scope_idx: int,
) -> SeedRecord:
    """Build and return the typed seed record for a experiment cell."""
    return SeedRecord(
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        client_idx=client_idx,
        scope_idx=scope_idx,
    )
