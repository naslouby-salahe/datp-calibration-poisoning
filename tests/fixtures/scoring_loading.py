"""Helper assertions for validation of loaded Parquet scoring outputs."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from datp.scoring.loading import load_parquets_from_dir
from tests.unit.conftest import _write_score_artifact


def assert_loads_client_score_parquets(score_dir: Path) -> None:
    """Verify that score arrays are correctly loaded from client-specific Parquet files."""
    _write_score_artifact(score_dir / "client_a.parquet", [0.1, 0.2])
    _write_score_artifact(score_dir / "client_b.parquet", [0.3, 0.4, 0.5])
    result = load_parquets_from_dir(score_dir)
    assert set(result.keys()) == {"client_a", "client_b"}
    np.testing.assert_allclose(result["client_a"], [0.1, 0.2])
    np.testing.assert_allclose(result["client_b"], [0.3, 0.4, 0.5])
