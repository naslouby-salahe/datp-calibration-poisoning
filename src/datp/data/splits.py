from __future__ import annotations

from datp.types import NarrativeText


import enum
from pathlib import Path


class Split(enum.StrEnum):

    TRAIN = "train"
    CAL = "cal"
    TEST_BENIGN = "test_benign"
    TEST_ATTACK = "test_attack"


def filename_for_split(split: Split) -> NarrativeText:
    return f"{split}.parquet"


def split_path(client_dir: Path, split: Split) -> Path:
    return client_dir / filename_for_split(split)
