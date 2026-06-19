from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd
import pytest

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile
from datp.core.enums import Regime, ScoringStage
from datp.core.identity import TrainingCellId
from datp.core.seeds import set_seeds
from datp.data.splits import Split
from datp.federated.protocols.fedavg import run_fl_training
from datp.scoring.generation import validate_scoring_manifest
from datp.scoring.schema import ScoringManifestStatus
from tests.fixtures.fl_training import SEED, make_client_data, make_fl_cfg

_STAGES = (ScoringStage.CAL, ScoringStage.TEST_BENIGN, ScoringStage.TEST_ATTACK)


@pytest.mark.integration
def test_artifacts_written(tmp_path) -> None:
    set_seeds(SEED)
    cfg = make_fl_cfg(regime=Regime.A, rounds=2)
    client_data = make_client_data(n_clients=2)
    client_ids = sorted(client_data.keys())

    run_fl_training(
        cfg=cfg,
        client_data=client_data,
        seed=SEED,
        alpha=None,
        base_dir=tmp_path,
    )

    layout = ArtifactLayout(base_dir=tmp_path, regime=Regime.A)
    cell = TrainingCellId(regime=Regime.A, seed=SEED, alpha=None)
    for cid in client_ids:
        for stage in _STAGES:
            expected = layout.score_file(cell, stage, cid)
            assert expected.exists(), (
                f"Missing score artifact: {expected} (client={cid}, stage={stage})"
            )
    manifest = validate_scoring_manifest(layout.score_cell(cell).score_dir)
    assert manifest["completion_status"] == ScoringManifestStatus.COMPLETE
    assert manifest["expected_client_ids"] == client_ids
    assert len(cast(list, manifest["records"])) == len(client_ids) * len(_STAGES)


@pytest.mark.integration
def test_artifact_schema(tmp_path) -> None:
    set_seeds(SEED)
    cfg = make_fl_cfg(regime=Regime.A, rounds=2)
    client_data = make_client_data(n_clients=2)
    first_cid = min(client_data.keys())

    run_fl_training(
        cfg=cfg,
        client_data=client_data,
        seed=SEED,
        alpha=None,
        base_dir=tmp_path,
    )

    cell = TrainingCellId(regime=Regime.A, seed=SEED, alpha=None)
    parquet_file = ArtifactLayout(base_dir=tmp_path, regime=Regime.A).score_file(
        cell, ScoringStage.CAL, first_cid
    )
    df = pd.read_parquet(parquet_file)

    assert list(df.columns) == ["reconstruction_error"], (
        f"Expected single column 'reconstruction_error', got {list(df.columns)}"
    )
    assert df["reconstruction_error"].dtype == np.float32, (
        f"Expected float32, got {df['reconstruction_error'].dtype}"
    )


def test_scoring_manifest_validation_fails_when_missing(tmp_path) -> None:
    cell = TrainingCellId(regime=Regime.A, seed=SEED, alpha=None)
    score_base = (
        ArtifactLayout(base_dir=tmp_path, regime=Regime.A).score_cell(cell).score_dir
    )
    score_base.mkdir(parents=True)
    (score_base / ArtifactFile.SCORING_MANIFEST).write_text(
        '{"schema_version":"1","completion_status":"complete","expected_client_ids":["c1"],'
        '"expected_splits":["' + Split.CAL.value + '"],"records":[]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Scoring manifest incomplete"):
        validate_scoring_manifest(score_base)
