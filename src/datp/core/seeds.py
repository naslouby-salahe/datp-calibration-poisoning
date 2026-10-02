from datp.types import (
    Index,
    RandomSeed,
    SignedCount,
)

import os
import random
from dataclasses import dataclass
from typing import Protocol, cast

import numpy as np
import torch
from pydantic import ConfigDict

from datp.core.types import FrozenModel


class _TorchSeedApi(Protocol):
    def manual_seed(self, seed: int) -> torch.Generator: ...

# Ensure deterministic cuBLAS operations by fixing the workspace size.
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")


@dataclass(frozen=True, slots=True)
class SeedPair:

    training_seed: RandomSeed
    poisoning_seed: RandomSeed


def set_seeds(seed: RandomSeed) -> None:
    random.seed(seed)
    np.random.seed(seed)
    cast(_TorchSeedApi, torch).manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.set_float32_matmul_precision("high")


class SeedRecord(FrozenModel):

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)
    pair: SeedPair
    client_idx: Index
    scope_idx: Index

    @property
    def training_seed(self) -> RandomSeed:
        return self.pair.training_seed

    @property
    def poisoning_seed(self) -> RandomSeed:
        return self.pair.poisoning_seed

    @property
    def entropy(self) -> tuple[SignedCount, SignedCount, SignedCount, SignedCount]:
        return (
            self.training_seed,
            self.poisoning_seed,
            self.client_idx,
            self.scope_idx,
        )


def make_seed_rng(record: SeedRecord, *, child_index: Index = 0) -> np.random.Generator:
    parent = np.random.SeedSequence(list(record.entropy))
    return np.random.default_rng(parent.spawn(child_index + 1)[child_index])
