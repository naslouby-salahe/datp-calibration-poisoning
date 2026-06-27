"""Split enum and helpers for train/cal/test artifact filenames."""

from __future__ import annotations

import enum
from pathlib import Path


class Split(enum.StrEnum):
    """Named data splits used across the pipeline."""

    TRAIN = "train"
    CAL = "cal"
    TEST_BENIGN = "test_benign"
    TEST_ATTACK = "test_attack"


def filename_for_split(split: Split) -> str:
    """Return the canonical Parquet filename for a split."""
    return f"{split.value}.parquet"


def split_path(client_dir: Path, split: Split) -> Path:
    """Return the full path to a split file within a client directory."""
    return client_dir / filename_for_split(split)


def iter_scoring_splits() -> tuple[Split, ...]:
    """Return the splits that participate in scoring (non-train)."""
    return (Split.CAL, Split.TEST_BENIGN, Split.TEST_ATTACK)


def is_scoring_split(split: Split) -> bool:
    """Check whether a split is used for scoring."""
    return split in iter_scoring_splits()
