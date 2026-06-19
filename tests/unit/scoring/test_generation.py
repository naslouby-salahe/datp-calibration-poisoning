from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import torch

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile, PathToken
from datp.core.enums import Activation, DeviceType, Regime, ScoringStage
from datp.core.identity import TrainingCellId
from datp.core.seeds import set_seeds
from datp.data.splits import Split
from datp.scoring.generation import validate_scoring_manifest
from datp.scoring.schema import SCORE_COLUMN, ScoringManifestStatus

_SEED = 0


def _score_base(tmp_path: Path) -> Path:
    cell = TrainingCellId(regime=Regime.A, seed=_SEED, alpha=None)
    return ArtifactLayout(base_dir=tmp_path, regime=Regime.A).score_cell(cell).score_dir


def _write_sentinel(score_base: Path) -> None:
    score_base.mkdir(parents=True, exist_ok=True)
    (score_base / ArtifactFile.SCORING_SENTINEL).write_text(
        "Scoring complete: 2 clients.\n"
    )


def _write_valid_manifest(
    score_base: Path, client_ids: list[str], splits: list[str]
) -> None:
    score_base.mkdir(parents=True, exist_ok=True)
    records = []
    for cid in client_ids:
        for split in splits:
            path = score_base / split / f"{cid}.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"\x00")
            records.append(
                {
                    "client_id": cid,
                    "split": split,
                    "path": str(path),
                    "row_count": 50,
                    "columns": ["reconstruction_error"],
                    "dtypes": {"reconstruction_error": "Float32"},
                    "score_min": 0.1,
                    "score_max": 1.0,
                    "score_nan_count": 0,
                    "file_hash": "abc123",
                }
            )
    manifest = {
        "schema_version": "1",
        "completion_status": ScoringManifestStatus.COMPLETE,
        "expected_client_ids": sorted(client_ids),
        "expected_splits": sorted(splits),
        "actual_client_ids": sorted(client_ids),
        "actual_splits": sorted(splits),
        "records": records,
    }
    (score_base / ArtifactFile.SCORING_MANIFEST).write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def test_validate_scoring_manifest_passes_with_valid_manifest(tmp_path: Path) -> None:
    sb = _score_base(tmp_path)
    _write_valid_manifest(
        sb,
        ["c0", "c1"],
        [Split.CAL.value, Split.TEST_BENIGN.value, Split.TEST_ATTACK.value],
    )
    result = validate_scoring_manifest(sb)
    assert result["completion_status"] == ScoringManifestStatus.COMPLETE


def test_sentinel_alone_is_not_sufficient(tmp_path: Path) -> None:
    sb = _score_base(tmp_path)
    _write_sentinel(sb)
    with pytest.raises(FileNotFoundError, match="Scoring manifest missing"):
        validate_scoring_manifest(sb)


def test_validate_scoring_manifest_fails_when_manifest_missing(tmp_path: Path) -> None:
    sb = _score_base(tmp_path)
    sb.mkdir(parents=True, exist_ok=True)
    with pytest.raises(FileNotFoundError, match="Scoring manifest missing"):
        validate_scoring_manifest(sb)


def test_validate_scoring_manifest_fails_incomplete_status(tmp_path: Path) -> None:
    sb = _score_base(tmp_path)
    sb.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1",
        "completion_status": "incomplete",
        "expected_client_ids": ["c0"],
        "expected_splits": [Split.CAL.value],
        "records": [],
    }
    (sb / ArtifactFile.SCORING_MANIFEST).write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Scoring manifest incomplete"):
        validate_scoring_manifest(sb)


def test_validate_scoring_manifest_fails_missing_records(tmp_path: Path) -> None:
    sb = _score_base(tmp_path)
    sb.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1",
        "completion_status": "complete",
        "expected_client_ids": ["c0"],
        "expected_splits": [Split.CAL.value],
        "actual_client_ids": [],
        "actual_splits": [],
        "records": [],
    }
    (sb / ArtifactFile.SCORING_MANIFEST).write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Scoring manifest incomplete"):
        validate_scoring_manifest(sb)


class TestLoadModelFromCheckpoint:
    """load_model_from_checkpoint must use resolve_device(), not hardcode CUDA."""

    def _write_checkpoint(self, tmp_path: Path) -> None:
        import io

        from datp.config.compose import BASE_CONFIG
        from datp.modeling.autoencoder import Autoencoder

        model = Autoencoder(
            input_dim=BASE_CONFIG.model.input_dim,
            hidden_dims=BASE_CONFIG.model.encoder_dims,
            activation=BASE_CONFIG.model.activation,
            use_bn=BASE_CONFIG.model.use_bn,
        )
        buf = io.BytesIO()
        torch.save(model.state_dict(), buf)
        (tmp_path / "model.pt").write_bytes(buf.getvalue())

    def test_uses_resolve_device_not_hardcoded_cuda(self, tmp_path: Path) -> None:
        from datp.config.compose import BASE_CONFIG
        from datp.scoring.generation import load_model_from_checkpoint

        self._write_checkpoint(tmp_path)
        cpu_device = torch.device(DeviceType.CPU)

        with patch("datp.scoring.generation.resolve_device", return_value=cpu_device):
            model = load_model_from_checkpoint(
                BASE_CONFIG, ckpt_dir=tmp_path, require_cuda=False
            )

        assert next(model.parameters()).device.type == DeviceType.CPU

    def test_fails_clearly_when_device_unavailable(self, tmp_path: Path) -> None:
        from datp.config.compose import BASE_CONFIG
        from datp.scoring.generation import load_model_from_checkpoint

        self._write_checkpoint(tmp_path)

        def _raise_cuda_unavailable(require_cuda: bool) -> torch.device:
            raise RuntimeError("CUDA is required but not available")

        with patch(
            "datp.scoring.generation.resolve_device",
            side_effect=_raise_cuda_unavailable,
        ):
            with pytest.raises(RuntimeError, match="CUDA"):
                load_model_from_checkpoint(
                    BASE_CONFIG, ckpt_dir=tmp_path, require_cuda=True
                )


class TestBatchedScoring:
    """Batched scoring must produce identical results to full-tensor scoring."""

    def test_batched_matches_full(self) -> None:
        from datp.modeling.autoencoder import Autoencoder
        from datp.scoring.generation import compute_reconstruction_errors

        set_seeds(42)
        model = Autoencoder(
            input_dim=4, hidden_dims=[3, 2], activation=Activation.RELU, use_bn=False
        )
        model.eval()
        data = torch.randn(100, 4)

        # Full (large batch)
        errors_full = compute_reconstruction_errors(model, data, batch_size=10000)
        # Batched with small batch size
        errors_batched = compute_reconstruction_errors(model, data, batch_size=7)

        import numpy as np

        np.testing.assert_array_almost_equal(errors_full, errors_batched, decimal=5)

    def test_empty_tensor_returns_empty(self) -> None:
        from datp.modeling.autoencoder import Autoencoder
        from datp.scoring.generation import compute_reconstruction_errors

        model = Autoencoder(
            input_dim=4, hidden_dims=[3, 2], activation=Activation.RELU, use_bn=False
        )
        model.eval()
        data = torch.empty(0, 4)

        errors = compute_reconstruction_errors(model, data, batch_size=128)
        assert errors.shape == (0,)

    def test_raises_file_not_found_when_checkpoint_missing(
        self, tmp_path: Path
    ) -> None:
        from datp.config.compose import BASE_CONFIG
        from datp.scoring.generation import load_model_from_checkpoint

        with pytest.raises(FileNotFoundError, match="Checkpoint missing"):
            load_model_from_checkpoint(
                BASE_CONFIG, ckpt_dir=tmp_path, require_cuda=False
            )


class TestErrorsToDataFrame:
    def test_empty_errors(self) -> None:
        from datp.scoring.generation import _errors_to_dataframe

        df = _errors_to_dataframe(np.array([], dtype=np.float32))
        assert df.shape == (0, 1)
        assert df.columns == [SCORE_COLUMN]

    def test_non_empty_errors(self) -> None:
        from datp.scoring.generation import _errors_to_dataframe

        errors = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        df = _errors_to_dataframe(errors)
        assert df.shape == (3, 1)
        assert df.columns == [SCORE_COLUMN]
        assert df[SCORE_COLUMN].to_list() == pytest.approx([0.1, 0.2, 0.3])


class TestScoreRecord:
    def test_score_record_fields(self, tmp_path: Path) -> None:
        from datp.scoring.generation import _score_record

        path = tmp_path / "test.parquet"
        path.write_bytes(b"\x00")
        errors = np.array([0.1, 0.2, np.nan], dtype=np.float32)
        record = _score_record(path, "c0", ScoringStage.CAL, errors)

        assert record["client_id"] == "c0"
        assert record["split"] == Split.CAL.value
        assert record["row_count"] == 3
        assert record["columns"] == [SCORE_COLUMN]
        assert record["dtypes"] == {SCORE_COLUMN: "Float32"}
        assert record["score_min"] == pytest.approx(0.1)
        assert record["score_max"] == pytest.approx(0.2)
        assert record["score_nan_count"] == 1
        assert record["file_hash"] != "MISSING"

    def test_score_record_all_nan(self, tmp_path: Path) -> None:
        from datp.scoring.generation import _score_record

        path = tmp_path / "all_nan.parquet"
        path.write_bytes(b"\x00")
        errors = np.array([np.nan, np.nan], dtype=np.float32)
        record = _score_record(path, "c1", ScoringStage.TEST_BENIGN, errors)

        assert record["score_min"] is None
        assert record["score_max"] is None
        assert record["score_nan_count"] == 2
        assert record["row_count"] == 2


class TestScoringStageClientDataAttr:
    def test_cal_maps_to_val(self) -> None:
        assert ScoringStage.CAL.client_data_attr == "val"

    def test_test_benign_maps_to_test_benign(self) -> None:
        assert ScoringStage.TEST_BENIGN.client_data_attr == "test_benign"

    def test_test_attack_maps_to_test_attack(self) -> None:
        assert ScoringStage.TEST_ATTACK.client_data_attr == "test_attack"


class TestScoreClients:
    def test_score_clients_writes_parquet_and_manifest(self, tmp_path: Path) -> None:
        import io

        import torch

        from datp.data.catalog import DatasetID
        from datp.federated.types import ClientData
        from datp.modeling.autoencoder import Autoencoder
        from datp.scoring.generation import score_clients, validate_scoring_manifest

        model = Autoencoder(
            input_dim=4, hidden_dims=[3, 2], activation=Activation.RELU, use_bn=False
        )
        model.eval()

        buf = io.BytesIO()
        torch.save(model.state_dict(), buf)
        ckpt_dir = tmp_path / "ckpt"
        ckpt_dir.mkdir()
        (ckpt_dir / "model.pt").write_bytes(buf.getvalue())

        client_data = {
            "c0": ClientData(
                train=torch.randn(10, 4),
                val=torch.randn(5, 4),
                test_benign=torch.randn(3, 4),
                test_attack=torch.randn(2, 4),
            ),
        }

        score_base = tmp_path / "scores"
        score_clients(
            model=model,
            client_data=client_data,
            score_base=score_base,
            regime=Regime.A,
            seed=0,
            alpha=None,
            dataset=DatasetID.NBAIOT,
            checkpoint_path=ckpt_dir / "model.pt",
            checkpoint_round=None,
            scoring_batch_size=128,
        )

        # Each stage produces one parquet per client
        for stage in ScoringStage.all():
            pf = score_base / stage.value / f"c0{PathToken.PARQUET_EXT}"
            assert pf.exists(), f"Missing {pf}"
        manifest = validate_scoring_manifest(score_base)
        assert manifest["completion_status"] == ScoringManifestStatus.COMPLETE
        assert manifest["expected_client_ids"] == ["c0"]

    def test_score_clients_empty_client_data(self, tmp_path: Path) -> None:
        from datp.data.catalog import DatasetID
        from datp.modeling.autoencoder import Autoencoder
        from datp.scoring.generation import score_clients, validate_scoring_manifest

        model = Autoencoder(
            input_dim=4, hidden_dims=[3, 2], activation=Activation.RELU, use_bn=False
        )
        model.eval()

        score_base = tmp_path / "scores"
        score_clients(
            model=model,
            client_data={},
            score_base=score_base,
            regime=Regime.A,
            seed=0,
            alpha=None,
            dataset=DatasetID.NBAIOT,
            checkpoint_path=None,
            checkpoint_round=None,
            scoring_batch_size=128,
        )

        manifest = validate_scoring_manifest(score_base)
        assert manifest["expected_client_ids"] == []
        assert manifest["records"] == []
