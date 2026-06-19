"""Deterministic seed derivation using numpy SeedSequence.

No integer seed addition. Co-victims differ by client_idx (independent streams
by construction). Every derived child seed is reproducible from the parent entropy.
"""

from __future__ import annotations

import numpy as np
from pydantic import ConfigDict, model_validator

from datp.core.seeds import SeedPair
from datp.core.types import FrozenModel


class SeedRecord(FrozenModel):
    """Canonical record of SeedSequence inputs for one experiment cell.

    Embed this in every run manifest so any run can be reproduced exactly.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    pair: SeedPair
    client_idx: int
    scope_idx: int

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_flat_seed_fields(cls, value: object) -> object:
        if isinstance(value, dict) and "pair" not in value:
            if "training_seed" in value and "poisoning_seed" in value:
                converted = dict(value)
                converted["pair"] = SeedPair(
                    training_seed=converted.pop("training_seed"),
                    poisoning_seed=converted.pop("poisoning_seed"),
                )
                return converted
        return value

    @property
    def training_seed(self) -> int:
        return self.pair.training_seed

    @property
    def poisoning_seed(self) -> int:
        return self.pair.poisoning_seed

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
    record: SeedRecord | None = None,
    *,
    child_index: int = 0,
    **legacy: int,
) -> np.random.Generator:
    """Return a reproducible NumPy Generator for one experiment cell.

    Uses SeedSequence([training_seed, poisoning_seed, client_idx, scope_idx])
    and spawns child generators. ``child_index`` selects which child stream.

    Do NOT use integer seed addition (forbidden by protocol).
    """
    if record is None:
        record = SeedRecord(
            pair=SeedPair(
                training_seed=legacy["training_seed"],
                poisoning_seed=legacy["poisoning_seed"],
            ),
            client_idx=legacy["client_idx"],
            scope_idx=legacy["scope_idx"],
        )
    parent = _parent_sequence(record)
    children = parent.spawn(child_index + 1)
    return np.random.default_rng(children[child_index])


def derive_seed_record(
    pair: SeedPair | None = None,
    *,
    training_seed: int | None = None,
    poisoning_seed: int | None = None,
    client_idx: int,
    scope_idx: int,
) -> SeedRecord:
    """Build and return the typed seed record for a experiment cell."""
    if pair is None:
        if training_seed is None or poisoning_seed is None:
            raise TypeError("pair or both legacy seed integers are required")
        pair = SeedPair(training_seed=training_seed, poisoning_seed=poisoning_seed)
    return SeedRecord(
        pair=pair,
        client_idx=client_idx,
        scope_idx=scope_idx,
    )
