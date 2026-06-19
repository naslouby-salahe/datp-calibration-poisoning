from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd
import pytest
import torch

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile
from datp.checkpointing.enums import CheckpointProtocolMode
from datp.config.compose import BASE_CONFIG
from datp.config.models import (
    ConvergenceConfig,
    DatpConfig,
    FederationConfig,
)
from datp.core.enums import Regime, ScoringStage
from datp.core.identity import TrainingCellId
from datp.core.seeds import set_seeds
from datp.data.splits import Split
from datp.federated.protocols.fedavg import run_fl_training
from datp.federated.types import ClientData
from datp.scoring.generation import validate_scoring_manifest
from datp.scoring.schema import ScoringManifestStatus

_N_FEATURES = 10
_N_TRAIN = 200
_N_VAL = 50
_N_TEST = 50
_SEED = 42
_STAGES = (ScoringStage.CAL, ScoringStage.TEST_BENIGN, ScoringStage.TEST_ATTACK)


def _make_client_data(n_clients: int, seed: int = _SEED) -> dict[str, ClientData]:
    device = torch.device("cpu")
    rng = torch.Generator().manual_seed(seed)
    data = {}
    for i in range(n_clients):
        data[f"client_{i}"] = ClientData(
            train=torch.randn(_N_TRAIN, _N_FEATURES, generator=rng).to(device),
            val=torch.randn(_N_VAL, _N_FEATURES, generator=rng).to(device),
            test_benign=torch.randn(_N_TEST, _N_FEATURES, generator=rng).to(device),
            test_attack=(torch.randn(_N_TEST, _N_FEATURES, generator=rng) + 5.0).to(
                device
            ),
        )
    return data


def _make_cfg(
    regime: Regime = Regime.A,
    n_features: int = _N_FEATURES,
    rounds: int = 2,
) -> DatpConfig:
    checkpoint_protocol = BASE_CONFIG.checkpoint_protocol
    disabled_checkpoint_protocol = (
        checkpoint_protocol.model_copy(
            update={"mode": CheckpointProtocolMode.DISABLED}
        )
        if checkpoint_protocol is not None
        else None
    )
    return BASE_CONFIG.model_copy(
        update={
            "regime": regime,
            "model": BASE_CONFIG.model.model_copy(
                update={
                    "input_dim": n_features,
                    "encoder_dims": [8, 4],
                }
            ),
            "dataset": BASE_CONFIG.dataset.model_copy(
                update={
                    "feature_count": n_features,
                }
            ),
            "machine": BASE_CONFIG.machine.model_copy(
                update={
                    "batch_size_train": 64,
                }
            ),
            "federation": FederationConfig(
                local_epochs=1,
                convergence=ConvergenceConfig(
                    rounds_initial=1,
                    rounds_max=rounds,
                    relative_threshold=0.001,
                    window=2,
                    round_timeout_s=300.0,
                ),
            ),
            # Disable checkpoint protocol: these tests verify basic scoring
            # artifact layout, not the checkpoint protocol artifact paths.
            "checkpoint_protocol": disabled_checkpoint_protocol,
        }
    )


@pytest.mark.integration
def test_artifacts_written(tmp_path) -> None:
    set_seeds(_SEED)
    cfg = _make_cfg(regime=Regime.A, rounds=2)
    client_data = _make_client_data(n_clients=2)
    client_ids = sorted(client_data.keys())

    run_fl_training(
        cfg=cfg,
        client_data=client_data,
        seed=_SEED,
        alpha=None,
        base_dir=tmp_path,
    )

    layout = ArtifactLayout(base_dir=tmp_path, regime=Regime.A)
    cell = TrainingCellId(regime=Regime.A, seed=_SEED, alpha=None)
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
    set_seeds(_SEED)
    cfg = _make_cfg(regime=Regime.A, rounds=2)
    client_data = _make_client_data(n_clients=2)
    first_cid = sorted(client_data.keys())[0]

    run_fl_training(
        cfg=cfg,
        client_data=client_data,
        seed=_SEED,
        alpha=None,
        base_dir=tmp_path,
    )

    cell = TrainingCellId(regime=Regime.A, seed=_SEED, alpha=None)
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
    cell = TrainingCellId(regime=Regime.A, seed=_SEED, alpha=None)
    score_base = ArtifactLayout(base_dir=tmp_path, regime=Regime.A).score_cell(cell).score_dir
    score_base.mkdir(parents=True)
    (score_base / ArtifactFile.SCORING_MANIFEST).write_text(
        '{"schema_version":"1","completion_status":"complete","expected_client_ids":["c1"],'
        '"expected_splits":["' + Split.CAL.value + '"],"records":[]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Scoring manifest incomplete"):
        validate_scoring_manifest(score_base)
