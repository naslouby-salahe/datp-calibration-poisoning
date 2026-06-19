"""B1/B2/B3/B4 share one ScoreProvider per (regime, seed, alpha) cell; missing artifacts always raise FileNotFoundError."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from datp.artifacts.names import PathToken
from datp.core.enums import ScoringStage
from datp.core.errors import fmt, fmt_missing
from datp.data.common.schemas import validate_score_artifact
from datp.scoring.schema import SCORE_COLUMN

_MODULE = "scoring.loading"


def read_score_column(path: Path) -> np.ndarray:
    validate_score_artifact(path)
    table = pq.read_table(path, columns=[SCORE_COLUMN])
    chunked = table.column(SCORE_COLUMN)
    return chunked.combine_chunks().to_numpy(zero_copy_only=False).astype(np.float64)


def load_parquets_from_dir(
    directory: Path,
    *,
    allow_empty: bool = True,
) -> dict[str, np.ndarray]:
    """Load all .parquet score files from *directory*.

    Returns ``{client_id: reconstruction_error_array}``.
    Raises ``FileNotFoundError`` if *directory* is missing, or if
    *allow_empty* is ``False`` and no parquet files are found.
    """
    if not directory.is_dir():
        raise FileNotFoundError(fmt_missing(_MODULE, f"score directory {directory}"))
    parquets: dict[str, np.ndarray] = {}
    for pf in sorted(directory.glob(PathToken.PARQUET_GLOB)):
        parquets[pf.stem] = read_score_column(pf)
    if not allow_empty and not parquets:
        raise FileNotFoundError(
            fmt(
                _MODULE,
                f"No parquet score artifacts at {directory}",
                "at least one .parquet score artifact",
                "none",
            )
        )
    return parquets


class ScoreProvider:
    def __init__(self, score_root: Path) -> None:
        self._root = score_root

    @property
    def score_root(self) -> Path:
        return self._root

    def load(self, client_id: str, stage: ScoringStage) -> np.ndarray:
        path = self._root / stage / f"{client_id}{PathToken.PARQUET_EXT}"
        if not path.exists():
            raise FileNotFoundError(
                fmt(
                    _MODULE,
                    f"Missing {stage} score artifact for client '{client_id}'",
                    str(path),
                    "absent",
                )
            )
        return read_score_column(path)

    def load_test_scores(self, client_id: str) -> tuple[np.ndarray, np.ndarray]:
        """Load test_benign and test_attack scores; test_attack may be empty."""
        benign = self.load(client_id, ScoringStage.TEST_BENIGN)
        attack = self.load(client_id, ScoringStage.TEST_ATTACK)
        return benign, attack
