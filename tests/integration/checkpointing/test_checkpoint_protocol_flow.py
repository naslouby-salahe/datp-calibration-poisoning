from __future__ import annotations

from pathlib import Path

import torch

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile
from datp.checkpointing.status import checkpoint_artifact_status
from datp.checkpointing.summary import select_global_primary_checkpoint
from datp.config.compose import BASE_CONFIG
from datp.core.enums import Baseline, Regime, ScoringStage
from datp.core.identity import TrainingCellId
from datp.data.catalog import DatasetID
from datp.evaluation.metrics import evaluate_baseline
from datp.federated.types import ClientData
from datp.modeling.autoencoder import Autoencoder
from datp.scoring.generation import score_clients
from datp.scoring.loading import ScoreProvider
from datp.testsupport.checkpoint_protocol import build_fake_checkpoint_metrics
from datp.thresholding.eligibility import (
    compute_client_thresholds,
    compute_tau_global,
)
from datp.thresholding.thresholds import _DeriveInput, derive_threshold


def _client_data() -> dict[str, ClientData]:
    return {
        "c1": ClientData(
            train=torch.zeros((4, 4)),
            val=torch.zeros((4, 4)),
            test_benign=torch.zeros((4, 4)),
            test_attack=torch.ones((4, 4)),
        ),
        "c2": ClientData(
            train=torch.ones((4, 4)) * 0.1,
            val=torch.ones((4, 4)) * 0.1,
            test_benign=torch.ones((4, 4)) * 0.1,
            test_attack=torch.ones((4, 4)) * 1.2,
        ),
    }


def test_checkpoint_scoring_evaluation_summary_and_status(tmp_path: Path) -> None:
    assert "outputs" not in tmp_path.parts
    layout = ArtifactLayout(base_dir=tmp_path, regime=Regime.A)
    cell = TrainingCellId(regime=Regime.A, seed=0, alpha=None)
    model = Autoencoder(
        input_dim=4,
        hidden_dims=[3, 2],
        activation=BASE_CONFIG.model.activation,
        use_bn=False,
    )
    client_data = _client_data()

    for checkpoint_round in (25, 50):
        ckpt_path = (
            layout.checkpoint_dir_for_round(cell, checkpoint_round)
            / ArtifactFile.MODEL_CHECKPOINT
        )
        ckpt_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), ckpt_path)
        score_clients(
            model=model,
            client_data=client_data,
            score_base=layout.score_cell_for_round(cell, checkpoint_round).score_dir,
            regime=Regime.A,
            seed=0,
            alpha=None,
            dataset=DatasetID.NBAIOT,
            checkpoint_path=ckpt_path,
            checkpoint_round=checkpoint_round,
            scoring_batch_size=8,
        )

    provider = ScoreProvider(layout.score_cell_for_round(cell, 25).score_dir)
    client_errors = {
        client_id: provider.load(client_id, stage=ScoringStage.CAL)
        for client_id in ("c1", "c2")
    }
    client_taus = compute_client_thresholds(client_errors, ["c1", "c2"], q=0.95)
    tau_global = compute_tau_global(client_taus)
    b1_thresholds = derive_threshold(_DeriveInput(
        baseline=Baseline.B1,
        client_errors=client_errors,
        n_min=1,
        q=0.95,
        tau_global=tau_global,
        regime=Regime.A,
        threshold_cfg=BASE_CONFIG.threshold,
        seed=0,
    ))
    b2_thresholds = derive_threshold(_DeriveInput(
        baseline=Baseline.B2,
        client_errors=client_errors,
        n_min=1,
        q=0.95,
        tau_global=tau_global,
        regime=Regime.A,
        threshold_cfg=BASE_CONFIG.threshold,
        seed=0,
    ))

    b1 = evaluate_baseline(
        b1_thresholds.client_thresholds,
        provider.score_root,
        Regime.A,
        0,
        None,
        score_provider=provider,
    )
    b2 = evaluate_baseline(
        b2_thresholds.client_thresholds,
        provider.score_root,
        Regime.A,
        0,
        None,
        score_provider=provider,
    )
    assert b1.run.baseline == Baseline.B1
    assert b2.run.baseline == Baseline.B2

    selection = select_global_primary_checkpoint(
        metrics=build_fake_checkpoint_metrics(rounds=(25, 50), seeds=(0, 1, 2)),
        n_bootstrap=200,
        bootstrap_seed=7,
    )
    assert selection.selected_round == 50

    status = checkpoint_artifact_status(
        artifact_root=tmp_path,
        regime=Regime.A,
        seed=0,
        alpha=None,
        checkpoint_round=25,
        baselines=(Baseline.B1, Baseline.B2),
    )
    assert status.checkpoint.value == "present"
    assert status.scores.value == "present"
