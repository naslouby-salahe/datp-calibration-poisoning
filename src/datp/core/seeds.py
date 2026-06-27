"""Deterministic seed management for training, poisoning, and analysis reproducibility."""

import os
import random
from dataclasses import dataclass

import numpy as np
import torch
from pydantic import ConfigDict

from datp.core.types import FrozenModel

# Ensure deterministic cuBLAS operations by fixing the workspace size.
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")


@dataclass(frozen=True, slots=True)
class SeedPair:
    """A (training_seed, poisoning_seed) pair that identifies one experiment cell."""

    training_seed: int
    poisoning_seed: int


def set_seeds(seed: int) -> None:
    """Seed Python, NumPy, and PyTorch RNGs for deterministic execution."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.set_float32_matmul_precision("high")


class SeedRecord(FrozenModel):
    """Full seed context: seed pair plus client and scope indices for deterministic RNG derivation."""

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)
    pair: SeedPair
    client_idx: int
    scope_idx: int

    @property
    def training_seed(self) -> int:
        """Training seed from the underlying seed pair."""
        return self.pair.training_seed

    @property
    def poisoning_seed(self) -> int:
        """Poisoning seed from the underlying seed pair."""
        return self.pair.poisoning_seed

    @property
    def entropy(self) -> tuple[int, int, int, int]:
        """Return a 4-tuple entropy source for downstream RNG derivation."""
        return (
            self.training_seed,
            self.poisoning_seed,
            self.client_idx,
            self.scope_idx,
        )


def make_seed_rng(record: SeedRecord, *, child_index: int = 0) -> np.random.Generator:
    """Derive a deterministic NumPy Generator from a SeedRecord via SeedSequence."""
    parent = np.random.SeedSequence(list(record.entropy))
    return np.random.default_rng(parent.spawn(child_index + 1)[child_index])


def derive_seed_record(
    pair: SeedPair, *, client_idx: int, scope_idx: int
) -> SeedRecord:
    """Create a SeedRecord from a SeedPair with client and scope indices."""
    return SeedRecord(pair=pair, client_idx=client_idx, scope_idx=scope_idx)
