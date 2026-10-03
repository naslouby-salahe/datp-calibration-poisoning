"""Synthetic score artifacts and a tiny poisoning config for attack integration tests."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import polars as pl
import pytest

from datp.artifacts import ArtifactLayout
from datp.attacks import manifests as manifests_module
from datp.attacks import sensitivity as sensitivity_module
from datp.attacks import sweep as sweep_module
from datp.config import N_MIN, CalibrationPoisoningConfig, ExperimentStage, SeedPools
from datp.core import TrainingCellId
from datp.enums import (
    AttackerObjective,
    PoisoningSourceStrategy,
    ScoringStage,
    ThresholdPolicy,
)
from datp.scoring import ScoringColumn
from datp.types import RandomSeed
from tests_support.synthetic_scores import SyntheticClientSpec, make_synthetic_client

N_CLIENTS = 4
N_CAL = N_MIN + 100
N_TEST = 50
TRAINING_SEED = RandomSeed(0)
TINY_SEEDS = SeedPools(
    training=(TRAINING_SEED,), poisoning=(RandomSeed(100),), analysis=(RandomSeed(300),)
)
TINY_FRACTIONS = (0.0, 0.4)
TINY_SOURCES = (PoisoningSourceStrategy.HIGH_SCORE_BENIGN,)
# (source, objective) pairs surviving the pairing filter for TINY_SOURCES.
TINY_PAIR_COUNT = 1
TINY_POLICY_COUNT = len(tuple(ThresholdPolicy))


def write_synthetic_scores(
    base_dir: Path, seeds: Iterable[RandomSeed], n_clients: int = N_CLIENTS
) -> None:
    """Write benign-calibration and test score parquets in the scoring layout."""
    layout = ArtifactLayout(base_dir=base_dir, stage=ExperimentStage.NBAIOT_MAIN)
    for seed in seeds:
        score_dir = layout.score_cell(
            TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=seed)
        ).score_dir
        for i in range(n_clients):
            client = make_synthetic_client(
                SyntheticClientSpec(
                    client_id=f"client_{i}",
                    n_cal=N_CAL,
                    n_test_benign=N_TEST,
                    n_test_attack=N_TEST,
                    cal_loc=0.05 * (1.0 + 0.6 * i),
                    cal_scale=0.02 * (1.0 + 0.5 * i),
                    training_seed=seed,
                    client_idx=i,
                )
            )
            for stage, scores in (
                (ScoringStage.CAL, client.cal),
                (ScoringStage.TEST_BENIGN, client.test_benign),
                (ScoringStage.TEST_ATTACK, client.test_attack),
            ):
                path = score_dir / stage.value / f"{client.client_id}.parquet"
                path.parent.mkdir(parents=True, exist_ok=True)
                pl.DataFrame(
                    {ScoringColumn.RECONSTRUCTION_ERROR: scores.astype("float32")}
                ).write_parquet(path)


@pytest.fixture(scope="session")
def tiny_config() -> CalibrationPoisoningConfig:
    """Bounded-sweep config shrunk to one seed pair, two fractions and one source."""
    return CalibrationPoisoningConfig.for_bounded_sweep().model_copy(
        update={
            "seeds": TINY_SEEDS,
            "fractions": TINY_FRACTIONS,
            "sources": TINY_SOURCES,
        }
    )


@pytest.fixture(scope="module")
def scores_dir(tmp_path_factory) -> Path:
    """Base directory holding synthetic score artifacts for the tiny seed pool."""
    base_dir = tmp_path_factory.mktemp("synthetic_scores")
    write_synthetic_scores(base_dir, TINY_SEEDS.training)
    return base_dir


@pytest.fixture(scope="module")
def tiny_runtime(tiny_config):
    """Run sweeps sequentially under the tiny config and shrink sensitivity grids."""
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_tiny_runtime(monkeypatch, tiny_config)
        yield tiny_config


def _patch_tiny_runtime(
    monkeypatch: pytest.MonkeyPatch, tiny_config: CalibrationPoisoningConfig
) -> None:

    def sequential_parallel(**_kwargs):
        return lambda jobs: [fn(*args, **kwargs) for fn, args, kwargs in jobs]

    for module in (sweep_module, sensitivity_module):
        monkeypatch.setattr(module, "Parallel", sequential_parallel)
    monkeypatch.setattr(manifests_module, "TRAINING_SEEDS", TINY_SEEDS.training)
    monkeypatch.setattr(manifests_module, "POISONING_SEEDS", TINY_SEEDS.poisoning)
    monkeypatch.setattr(manifests_module, "ANALYSIS_SEEDS", TINY_SEEDS.analysis)
    monkeypatch.setattr(
        CalibrationPoisoningConfig,
        "for_bounded_sweep",
        classmethod(lambda _cls: tiny_config),
    )
    monkeypatch.setattr(sensitivity_module, "CLUSTER_SENSITIVITY_K_GRID", (2, 3))
    monkeypatch.setattr(sensitivity_module, "CLUSTER_SENSITIVITY_RANDOM_STATES", (0,))
    monkeypatch.setattr(sensitivity_module, "CLUSTER_SENSITIVITY_N_INIT_GRID", (1,))
    monkeypatch.setattr(sensitivity_module, "CLUSTER_SENSITIVITY_FRACTIONS", (0.4,))
    monkeypatch.setattr(sensitivity_module, "DRAW_VARIANT_FRACTIONS", (0.4,))
    monkeypatch.setattr(
        sensitivity_module,
        "NBAIOT_MAIN_SOURCE_OBJECTIVE_PAIRS",
        (
            (
                PoisoningSourceStrategy.HIGH_SCORE_BENIGN,
                AttackerObjective.THRESHOLD_RAISE,
            ),
            (
                PoisoningSourceStrategy.LOW_SCORE_BENIGN,
                AttackerObjective.THRESHOLD_LOWER,
            ),
        ),
    )
