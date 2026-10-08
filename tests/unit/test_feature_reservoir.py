from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import polars as pl
import pytest
import torch

from datp.artifacts import ArtifactLayout
from datp.attacks.feature_reservoir import inject_feature_reservoir, score_feature_rows
from datp.attacks.sweep import load_train_feature_reservoirs
from datp.config import ExperimentStage, ModelConfig
from datp.core import TrainingCellId
from datp.enums import Activation, DatasetID, FeatureDonorScope
from datp.modeling import Autoencoder
from datp.scoring import hash_model_state


def test_score_feature_rows_batches_model_scores() -> None:
    model = Autoencoder(2, [2], Activation.RELU, False)
    features = np.array([[0.0, 1.0], [1.0, 0.0], [1.0, 1.0]], dtype=np.float32)

    actual = score_feature_rows(model, features, batch_size=2)
    with torch.inference_mode():
        expected = model.reconstruction_error(torch.as_tensor(features)).numpy()

    np.testing.assert_allclose(actual, expected)


@pytest.mark.parametrize(
    ("features", "batch_size", "message"),
    [
        (np.array([1.0]), 2, "non-empty 2-D"),
        (np.empty((0, 2)), 2, "non-empty 2-D"),
        (np.ones((2, 2)), 0, "batch_size must be positive"),
        (np.array([[np.nan, 0.0]]), 2, "finite"),
    ],
)
def test_score_feature_rows_rejects_invalid_input(
    features: np.ndarray, batch_size: int, message: str
) -> None:
    model = Autoencoder(2, [2], Activation.RELU, False)
    with pytest.raises(ValueError, match=message):
        score_feature_rows(model, features, batch_size=batch_size)


def test_injection_uses_unique_rows_from_high_score_tail() -> None:
    clean = np.arange(10, dtype=np.float64)
    scores = np.array([0.1, 0.1, 0.2, 0.4, 0.4, 0.8, 0.9])
    row_ids = np.array([0, 0, 1, 2, 2, 3, 4])

    result = inject_feature_reservoir(
        clean_cal=clean,
        benign_reservoir_scores=scores,
        feature_row_ids=row_ids,
        fraction=0.2,
        tail_fraction=0.4,
        rng=np.random.default_rng(10),
    )

    assert set(row_ids[result.candidate_indices]) == {3, 4}
    assert len(np.unique(row_ids[result.donor_indices])) == 2
    assert result.donor_feature_unique_fraction == 1.0
    assert result.injection.n_replaced == 2


def test_zero_fraction_has_no_donor_uniqueness_value() -> None:
    result = inject_feature_reservoir(
        clean_cal=np.arange(5, dtype=np.float64),
        benign_reservoir_scores=np.array([0.1, 0.2]),
        feature_row_ids=np.array([0, 1]),
        fraction=0.0,
        tail_fraction=1.0,
        rng=np.random.default_rng(1),
    )

    assert result.injection.n_replaced == 0
    assert result.donor_feature_unique_fraction is None


@pytest.mark.parametrize(
    ("clean", "scores", "ids", "fraction", "tail", "message"),
    [
        (np.ones((2, 2)), np.ones(2), np.arange(2), 0.5, 1.0, "one-dimensional"),
        (np.ones(2), np.ones(2), np.arange(1), 0.5, 1.0, "align"),
        (np.array([np.nan]), np.ones(2), np.arange(2), 0.5, 1.0, "finite"),
        (np.ones(2), np.ones(2), np.arange(2), 1.1, 1.0, "fraction"),
        (np.ones(2), np.ones(2), np.arange(2), 0.5, 0.0, "tail_fraction"),
        (np.ones(2), np.array([]), np.array([], dtype=int), 0.5, 1.0, "empty"),
        (np.array([]), np.ones(2), np.arange(2), 0.5, 1.0, "empty"),
    ],
)
def test_injection_rejects_invalid_input(
    clean: np.ndarray,
    scores: np.ndarray,
    ids: np.ndarray,
    fraction: float,
    tail: float,
    message: str,
) -> None:
    default_rng_value = np.random.default_rng(1)
    with pytest.raises(ValueError, match=message):
        inject_feature_reservoir(
            clean_cal=clean,
            benign_reservoir_scores=scores,
            feature_row_ids=ids,
            fraction=fraction,
            tail_fraction=tail,
            rng=default_rng_value,
        )


def test_injection_rejects_tail_that_cannot_fill_budget() -> None:
    arange_value = np.arange(10, dtype=np.float64)
    arange_value_2 = np.arange(5, dtype=np.float64)
    arange_value_3 = np.arange(5)
    default_rng_value = np.random.default_rng(1)
    with pytest.raises(ValueError, match="only 1 distinct rows"):
        inject_feature_reservoir(
            clean_cal=arange_value,
            benign_reservoir_scores=arange_value_2,
            feature_row_ids=arange_value_3,
            fraction=0.5,
            tail_fraction=0.2,
            rng=default_rng_value,
        )


@pytest.mark.parametrize("scope", list(FeatureDonorScope))
def test_load_train_feature_reservoirs_scores_processed_rows(
    tmp_path: Path, scope: FeatureDonorScope
) -> None:
    base_dir = tmp_path / "outputs"
    data_root = tmp_path / "data"
    seed = 0
    cell = TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=seed)
    model_config = ModelConfig(
        input_dim=2,
        encoder_dims=[2],
        lr=0.001,
        epochs=1,
        activation=Activation.RELU,
        use_bn=False,
    )
    model = Autoencoder(2, [2], Activation.RELU, False)
    layout = ArtifactLayout(base_dir=base_dir, stage=ExperimentStage.NBAIOT_MAIN)
    checkpoint_path = layout.model_checkpoint(cell)
    checkpoint_path.parent.mkdir(parents=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "model_config": model_config.model_dump(mode="json"),
        },
        checkpoint_path,
    )
    frames = {
        "client-a": {"f0": [0.0, 1.0, 1.0], "f1": [1.0, 0.0, 0.0]},
        "client-b": {"f0": [1.0, 5.0], "f1": [0.0, 5.0]},
    }
    for client, frame in frames.items():
        feature_path = (
            data_root
            / "data"
            / "processed"
            / DatasetID.NBAIOT
            / client
            / "train.parquet"
        )
        feature_path.parent.mkdir(parents=True)
        pl.DataFrame(frame).write_parquet(feature_path)
    collection = SimpleNamespace(eligible_ids=("client-a", "client-b"))
    with patch(
        "datp.attacks.sweep.validate_scoring_manifest",
        return_value=SimpleNamespace(model_hash=hash_model_state(model)),
    ):
        scores, row_ids = load_train_feature_reservoirs(
            base_dir,
            {seed: collection},
            data_root=data_root,
            donor_scope=scope,
        )

    if scope is FeatureDonorScope.OWN_DEVICE:
        assert scores[seed]["client-a"].shape == (3,)
        assert row_ids[seed]["client-a"][1] == row_ids[seed]["client-a"][2]
        return
    assert scores[seed]["client-a"].shape == (2,)
    assert scores[seed]["client-b"].shape == (3,)
    # the row (1, 0) is shared across devices and gets one global row id
    assert row_ids[seed]["client-b"][1] == row_ids[seed]["client-a"][0]
    assert row_ids[seed]["client-a"][1] != row_ids[seed]["client-a"][0]


def test_load_train_feature_reservoirs_requires_checkpoint(tmp_path: Path) -> None:
    simple_namespace = SimpleNamespace(eligible_ids=())
    with pytest.raises(FileNotFoundError, match="Missing federated model checkpoint"):
        load_train_feature_reservoirs(
            tmp_path / "outputs",
            {0: simple_namespace},
            data_root=tmp_path,
            donor_scope=FeatureDonorScope.CROSS_DEVICE,
        )
