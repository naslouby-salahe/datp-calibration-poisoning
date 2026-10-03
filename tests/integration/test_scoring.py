from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from datp.artifacts import ArtifactLayout
from datp.config import ExperimentStage
from datp.core import TrainingCellId, set_seeds
from datp.data import Split
from datp.enums import Activation, ArtifactFile, DatasetID, PathToken, ScoringStage
from datp.modeling import Autoencoder
from datp.scoring import ScoringManifestStatus, score_clients, validate_scoring_manifest
from tests.fixtures import N_FEATURES, SEED, make_client_data

_STAGES = (ScoringStage.CAL, ScoringStage.TEST_BENIGN, ScoringStage.TEST_ATTACK)


def _score_untrained(tmp_path, n_clients: int = 2):
    """Score synthetic clients with an untrained autoencoder (no FL training)."""
    set_seeds(SEED)
    client_data = make_client_data(n_clients=n_clients)
    cell = TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=SEED)
    layout = ArtifactLayout(base_dir=tmp_path, stage=ExperimentStage.NBAIOT_MAIN)
    score_dir = layout.score_cell(cell).score_dir
    score_clients(
        Autoencoder(N_FEATURES, [8, 4], Activation.RELU, use_bn=False),
        client_data,
        score_base=score_dir,
        stage=ExperimentStage.NBAIOT_MAIN,
        seed=SEED,
        dataset=DatasetID.NBAIOT,
        scoring_batch_size=64,
    )
    return client_data, layout, cell


@pytest.mark.integration
def test_artifacts_written(tmp_path) -> None:
    """Scoring writes parquet files for every client and stage, with a complete manifest."""
    client_data, layout, cell = _score_untrained(tmp_path)
    client_ids = sorted(client_data.keys())

    for cid in client_ids:
        for stage in _STAGES:
            expected = (
                layout.score_cell(cell).score_dir
                / stage
                / f"{cid}{PathToken.PARQUET_EXT}"
            )
            assert expected.exists(), (
                f"Missing score artifact: {expected} (client={cid}, stage={stage})"
            )
    manifest = validate_scoring_manifest(layout.score_cell(cell).score_dir)
    assert manifest.completion_status == ScoringManifestStatus.COMPLETE
    assert manifest.expected_client_ids == tuple(client_ids)
    assert len(manifest.records) == len(client_ids) * len(_STAGES)


@pytest.mark.integration
def test_artifact_schema(tmp_path) -> None:
    """Score parquet files have a single float32 reconstruction_error column."""
    client_data, layout, cell = _score_untrained(tmp_path)
    first_cid = min(client_data.keys())
    parquet_file = (
        layout.score_cell(cell).score_dir
        / ScoringStage.CAL
        / f"{first_cid}{PathToken.PARQUET_EXT}"
    )
    df = pd.read_parquet(parquet_file)

    assert list(df.columns) == ["reconstruction_error"], (
        f"Expected single column 'reconstruction_error', got {list(df.columns)}"
    )
    assert df["reconstruction_error"].dtype == np.float32, (
        f"Expected float32, got {df['reconstruction_error'].dtype}"
    )


def test_scoring_manifest_validation_fails_when_missing(tmp_path) -> None:
    """Scoring manifest validation raises when actual files do not match expected records."""
    cell = TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=SEED)
    score_base = (
        ArtifactLayout(base_dir=tmp_path, stage=ExperimentStage.NBAIOT_MAIN)
        .score_cell(cell)
        .score_dir
    )
    score_base.mkdir(parents=True)
    (score_base / ArtifactFile.SCORING_MANIFEST).write_text(
        '{"schema_version":"1","dataset":"nbaiot","stage":"nbaiot_main","seed":42,'
        '"model_hash":"h","completion_status":"complete","expected_client_ids":["c1"],'
        '"expected_splits":["'
        + Split.CAL.value
        + '"],"actual_client_ids":[],"actual_splits":[],"records":[]}',
    )
    with pytest.raises(ValueError, match="Scoring manifest incomplete"):
        validate_scoring_manifest(score_base)
