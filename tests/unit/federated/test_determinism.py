from __future__ import annotations

from pathlib import Path

import pytest

from datp.artifacts.io import write_metrics_atomic
from tests.fixtures.flower_smoke import run_flower_smoke


def _run_experiment(seed: int | None, run_dir: Path) -> Path:
    metrics = {
        "losses_distributed": [
            {"round": rnd, "loss": loss} for rnd, loss in run_flower_smoke(seed=seed)
        ],
    }
    return write_metrics_atomic(run_dir, metrics)


@pytest.mark.integration
def test_determinism_same_seed_identical_metrics(tmp_path: Path) -> None:
    path_a = _run_experiment(seed=42, run_dir=tmp_path / "run_a")
    path_b = _run_experiment(seed=42, run_dir=tmp_path / "run_b")

    bytes_a = path_a.read_bytes()
    bytes_b = path_b.read_bytes()
    assert bytes_a == bytes_b, (
        "metrics.json files differ between two runs with the same seed.\n"
        f"Run A:\n{bytes_a.decode()}\n"
        f"Run B:\n{bytes_b.decode()}"
    )


@pytest.mark.integration
def test_determinism_guard_no_seeds_differ(tmp_path: Path) -> None:
    path_a = _run_experiment(seed=42, run_dir=tmp_path / "run_a")
    path_b = _run_experiment(seed=99, run_dir=tmp_path / "run_b")

    bytes_a = path_a.read_bytes()
    bytes_b = path_b.read_bytes()
    assert bytes_a != bytes_b, (
        "metrics.json files are identical despite different seeds - "
        "the determinism test is not sensitive to seed state."
    )
