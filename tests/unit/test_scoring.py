from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from datp.artifacts import ArtifactLayout
from datp.config import ExperimentStage
from datp.core import TrainingCellId, set_seeds
from datp.data import Split
from datp.enums import Activation, ArtifactFile, DatasetID, PathToken, ScoringStage
from datp.modeling import Autoencoder
from datp.scoring import (
    ScoreProvider,
    ScoringColumn,
    ScoringManifestStatus,
    hash_model_state,
    load_main_cal_errors,
    load_parquets_from_dir,
    read_score_column,
    validate_scoring_manifest,
)
from tests.fixtures import _write_score_artifact, assert_loads_client_score_parquets

_STAGE = ExperimentStage.NBAIOT_MAIN


class TestLoadMainCalErrors:
    """Loading calibration errors from the main experiment stage."""

    def test_loads_calibration_errors(self, tmp_path: Path) -> None:
        seed = 42
        score_dir = tmp_path / "scores" / _STAGE.value / f"seed_{seed}"
        cal_dir = score_dir / ScoringStage.CAL.value
        _write_score_artifact(cal_dir / "c1.parquet", [0.01, 0.02])
        _write_score_artifact(cal_dir / "c2.parquet", [0.03])

        result = load_main_cal_errors(_STAGE, seed, tmp_path)
        assert set(result.keys()) == {"c1", "c2"}
        np.testing.assert_allclose(result["c1"], [0.01, 0.02])
        np.testing.assert_allclose(result["c2"], [0.03])

    def test_missing_cal_directory(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="score directory"):
            load_main_cal_errors(_STAGE, 1, tmp_path)

    def test_empty_cal_directory(self, tmp_path: Path) -> None:
        seed = 1
        score_dir = tmp_path / "scores" / _STAGE.value / f"seed_{seed}"
        cal_dir = score_dir / ScoringStage.CAL.value
        cal_dir.mkdir(parents=True)
        with pytest.raises(FileNotFoundError, match="No parquet score artifacts"):
            load_main_cal_errors(_STAGE, seed, tmp_path)


_SEED = 0


def _score_base(tmp_path: Path) -> Path:
    cell = TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=_SEED)
    return (
        ArtifactLayout(base_dir=tmp_path, stage=ExperimentStage.NBAIOT_MAIN)
        .score_cell(cell)
        .score_dir
    )


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
                    "dtypes": [{"column": "reconstruction_error", "dtype": "Float32"}],
                    "score_min": 0.1,
                    "score_max": 1.0,
                    "score_nan_count": 0,
                    "file_hash": "abc123",
                }
            )
    manifest = {
        "schema_version": "1",
        "dataset": DatasetID.NBAIOT.value,
        "stage": ExperimentStage.NBAIOT_MAIN.value,
        "seed": _SEED,
        "completion_status": ScoringManifestStatus.COMPLETE,
        "model_hash": "model-hash",
        "expected_client_ids": sorted(client_ids),
        "expected_splits": sorted(splits),
        "actual_client_ids": sorted(client_ids),
        "actual_splits": sorted(splits),
        "records": records,
    }
    (score_base / ArtifactFile.SCORING_MANIFEST).write_text(json.dumps(manifest))


def test_validate_scoring_manifest_passes_with_valid_manifest(tmp_path: Path) -> None:
    sb = _score_base(tmp_path)
    _write_valid_manifest(
        sb,
        ["c0", "c1"],
        [Split.CAL.value, Split.TEST_BENIGN.value, Split.TEST_ATTACK.value],
    )
    result = validate_scoring_manifest(sb)
    assert result.completion_status == ScoringManifestStatus.COMPLETE


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
        "dataset": DatasetID.NBAIOT.value,
        "stage": ExperimentStage.NBAIOT_MAIN.value,
        "seed": _SEED,
        "completion_status": "incomplete",
        "model_hash": "model-hash",
        "expected_client_ids": ["c0"],
        "expected_splits": [Split.CAL.value],
        "actual_client_ids": [],
        "actual_splits": [],
        "records": [],
    }
    (sb / ArtifactFile.SCORING_MANIFEST).write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Scoring manifest incomplete"):
        validate_scoring_manifest(sb)


def test_validate_scoring_manifest_fails_missing_records(tmp_path: Path) -> None:
    sb = _score_base(tmp_path)
    sb.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1",
        "dataset": DatasetID.NBAIOT.value,
        "stage": ExperimentStage.NBAIOT_MAIN.value,
        "seed": _SEED,
        "completion_status": "complete",
        "model_hash": "model-hash",
        "expected_client_ids": ["c0"],
        "expected_splits": [Split.CAL.value],
        "actual_client_ids": [],
        "actual_splits": [],
        "records": [],
    }
    (sb / ArtifactFile.SCORING_MANIFEST).write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Scoring manifest incomplete"):
        validate_scoring_manifest(sb)


class TestHashModelState:
    """Content hash of the trained model that is recorded in the scoring manifest."""

    @staticmethod
    def _model() -> Autoencoder:
        set_seeds(7)
        return Autoencoder(
            input_dim=4, hidden_dims=[3, 2], activation=Activation.RELU, use_bn=False
        )

    def test_hash_is_deterministic(self) -> None:
        first = hash_model_state(self._model())
        second = hash_model_state(self._model())
        assert first == second

    def test_hash_changes_with_weights(self) -> None:
        model = self._model()
        before = hash_model_state(model)
        with torch.no_grad():
            next(model.parameters()).add_(1.0)

        assert hash_model_state(model) != before


class TestBatchedScoring:
    """Batched scoring pipeline."""

    def test_batched_matches_full(self) -> None:
        from datp.modeling import Autoencoder
        from datp.scoring import compute_reconstruction_errors

        set_seeds(42)
        model = Autoencoder(
            input_dim=4, hidden_dims=[3, 2], activation=Activation.RELU, use_bn=False
        )
        model.eval()
        data = torch.randn(100, 4)

        errors_full = compute_reconstruction_errors(model, data, batch_size=10000)

        errors_batched = compute_reconstruction_errors(model, data, batch_size=7)

        import numpy as np

        np.testing.assert_array_almost_equal(errors_full, errors_batched, decimal=5)

    def test_empty_tensor_returns_empty(self) -> None:
        from datp.modeling import Autoencoder
        from datp.scoring import compute_reconstruction_errors

        model = Autoencoder(
            input_dim=4, hidden_dims=[3, 2], activation=Activation.RELU, use_bn=False
        )
        model.eval()
        data = torch.empty(0, 4)

        errors = compute_reconstruction_errors(model, data, batch_size=128)
        assert errors.shape == (0,)


class TestScoreRecord:
    """ScoreRecord dataclass fields."""

    def test_score_record_fields(self, tmp_path: Path) -> None:
        from datp.scoring import _score_record

        path = tmp_path / "test.parquet"
        path.write_bytes(b"\x00")
        errors = np.array([0.1, 0.2, np.nan], dtype=np.float32)
        record = _score_record(path, "c0", ScoringStage.CAL, errors)

        assert record.client_id == "c0"
        assert record.split == ScoringStage.CAL
        assert record.row_count == 3
        assert record.columns == (ScoringColumn.RECONSTRUCTION_ERROR,)
        assert record.dtypes[0].column == ScoringColumn.RECONSTRUCTION_ERROR
        assert record.dtypes[0].dtype == "Float32"
        assert record.score_min == pytest.approx(0.1)
        assert record.score_max == pytest.approx(0.2)
        assert record.score_nan_count == 1
        assert record.file_hash != "MISSING"

    def test_score_record_all_nan(self, tmp_path: Path) -> None:
        from datp.scoring import _score_record

        path = tmp_path / "all_nan.parquet"
        path.write_bytes(b"\x00")
        errors = np.array([np.nan, np.nan], dtype=np.float32)
        record = _score_record(path, "c1", ScoringStage.TEST_BENIGN, errors)

        assert record.score_min is None
        assert record.score_max is None
        assert record.score_nan_count == 2
        assert record.row_count == 2


class TestScoringStageClientDataAttr:
    """ScoringStage client_data attribute access."""

    def test_cal_maps_to_val(self) -> None:
        assert ScoringStage.CAL.client_data_attr == "val"

    def test_test_benign_maps_to_test_benign(self) -> None:
        assert ScoringStage.TEST_BENIGN.client_data_attr == "test_benign"

    def test_test_attack_maps_to_test_attack(self) -> None:
        assert ScoringStage.TEST_ATTACK.client_data_attr == "test_attack"


class TestScoreClients:
    """End-to-end score_clients pipeline."""

    def test_score_clients_writes_parquet_and_manifest(self, tmp_path: Path) -> None:
        import torch

        from datp.data import ClientData
        from datp.enums import DatasetID
        from datp.modeling import Autoencoder
        from datp.scoring import score_clients

        model = Autoencoder(
            input_dim=4, hidden_dims=[3, 2], activation=Activation.RELU, use_bn=False
        )
        model.eval()

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
            stage=ExperimentStage.NBAIOT_MAIN,
            seed=0,
            dataset=DatasetID.NBAIOT,
            scoring_batch_size=128,
        )

        for stage in ScoringStage.all():
            pf = score_base / stage.value / f"c0{PathToken.PARQUET_EXT}"
            assert pf.exists(), f"Missing {pf}"
        manifest = validate_scoring_manifest(score_base)
        assert manifest.completion_status == ScoringManifestStatus.COMPLETE
        assert manifest.expected_client_ids == ("c0",)
        assert manifest.model_hash == hash_model_state(model)

    def test_score_clients_empty_client_data(self, tmp_path: Path) -> None:
        from datp.enums import DatasetID
        from datp.modeling import Autoencoder
        from datp.scoring import score_clients

        model = Autoencoder(
            input_dim=4, hidden_dims=[3, 2], activation=Activation.RELU, use_bn=False
        )
        model.eval()

        score_base = tmp_path / "scores"
        score_clients(
            model=model,
            client_data={},
            score_base=score_base,
            stage=ExperimentStage.NBAIOT_MAIN,
            seed=0,
            dataset=DatasetID.NBAIOT,
            scoring_batch_size=128,
        )

        manifest = validate_scoring_manifest(score_base)
        assert manifest.expected_client_ids == ()
        assert manifest.records == ()


class TestReadScoreColumn:
    """Reading a single score column from Parquet."""

    def test_reads_score_column(self, tmp_path: Path) -> None:
        path = tmp_path / "scores.parquet"
        _write_score_artifact(path, [0.1, 0.2, 0.3])
        result = read_score_column(path)
        assert result.dtype == np.float64
        np.testing.assert_allclose(result, [0.1, 0.2, 0.3], rtol=1e-5)

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_score_column(tmp_path / "nonexistent.parquet")

    def test_raises_on_wrong_schema(self, tmp_path: Path) -> None:
        import pyarrow as pa
        import pyarrow.parquet as pq

        path = tmp_path / "bad.parquet"
        pq.write_table(pa.table({"wrong_col": pa.array([1.0])}), path)
        with pytest.raises(ValueError, match="(?i)schema mismatch"):
            read_score_column(path)

    def test_raises_on_non_float_type(self, tmp_path: Path) -> None:
        import pyarrow as pa
        import pyarrow.parquet as pq

        path = tmp_path / "bad.parquet"
        pq.write_table(
            pa.table(
                {
                    ScoringColumn.RECONSTRUCTION_ERROR: pa.array(
                        [1, 2, 3], type=pa.int64()
                    )
                }
            ),
            path,
        )
        with pytest.raises(TypeError, match="non-floating"):
            read_score_column(path)

    def test_empty_parquet_is_valid(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.parquet"
        _write_score_artifact(path, [])
        result = read_score_column(path)
        assert result.size == 0
        assert result.dtype == np.float64


class TestLoadParquetsFromDir:
    """Loading all Parquet files from a directory."""

    def test_loads_all_parquets(self, tmp_path: Path) -> None:
        assert_loads_client_score_parquets(tmp_path)

    def test_empty_directory_when_allow_empty_true(self, tmp_path: Path) -> None:
        result = load_parquets_from_dir(tmp_path, allow_empty=True)
        assert result == {}

    def test_empty_directory_when_allow_empty_false(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="No parquet score artifacts"):
            load_parquets_from_dir(tmp_path, allow_empty=False)

    def test_missing_directory(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError, match="score directory"):
            load_parquets_from_dir(missing)

    def test_skips_non_parquet_files(self, tmp_path: Path) -> None:
        _write_score_artifact(tmp_path / "c1.parquet", [0.1])
        (tmp_path / "readme.txt").touch()
        (tmp_path / "subdir").mkdir()
        result = load_parquets_from_dir(tmp_path)
        assert list(result.keys()) == ["c1"]


class TestScoreProvider:
    """ScoreProvider caching and lazy loading."""

    def test_score_root_property(self, tmp_path: Path) -> None:
        provider = ScoreProvider(tmp_path)
        assert provider.score_root == tmp_path

    def test_missing_benign_raises(self, tmp_path: Path) -> None:
        provider = ScoreProvider(tmp_path)
        with pytest.raises(FileNotFoundError, match="test_benign"):
            provider.load("client_01", ScoringStage.TEST_BENIGN)

    def test_missing_attack_raises(self, tmp_path: Path) -> None:
        provider = ScoreProvider(tmp_path)
        _write_score_artifact(
            tmp_path / ScoringStage.TEST_BENIGN / "c1.parquet", [0.1, 0.2]
        )
        with pytest.raises(FileNotFoundError, match="test_attack"):
            provider.load("c1", ScoringStage.TEST_ATTACK)

    def test_missing_cal_raises(self, tmp_path: Path) -> None:
        provider = ScoreProvider(tmp_path)
        with pytest.raises(FileNotFoundError, match="cal"):
            provider.load("c1", ScoringStage.CAL)

    def test_reads_score_column_only(self, tmp_path: Path) -> None:
        _write_score_artifact(
            tmp_path / ScoringStage.TEST_BENIGN / "c1.parquet", [0.1, 0.2, 0.3]
        )
        provider = ScoreProvider(tmp_path)
        arr = provider.load("c1", ScoringStage.TEST_BENIGN)
        assert arr.dtype == np.float64
        np.testing.assert_allclose(arr, [0.1, 0.2, 0.3], rtol=1e-5)

    def test_empty_attack_artifact_is_valid(self, tmp_path: Path) -> None:
        _write_score_artifact(tmp_path / ScoringStage.TEST_ATTACK / "c1.parquet", [])
        provider = ScoreProvider(tmp_path)
        arr = provider.load("c1", ScoringStage.TEST_ATTACK)
        assert arr.size == 0
        assert arr.dtype == np.float64

    def test_load_test_scores_returns_tuple(self, tmp_path: Path) -> None:
        _write_score_artifact(
            tmp_path / ScoringStage.TEST_BENIGN / "c1.parquet", [0.1, 0.2]
        )
        _write_score_artifact(
            tmp_path / ScoringStage.TEST_ATTACK / "c1.parquet", [0.5, 0.9]
        )
        provider = ScoreProvider(tmp_path)
        benign, attack = provider.load_test_scores("c1")
        assert benign.size == 2
        assert attack.size == 2

    def test_score_provider_has_no_cache_state(self, tmp_path: Path) -> None:
        provider = ScoreProvider(tmp_path)
        assert not hasattr(provider, "_lru")

    def test_shared_provider_across_baselines(self, tmp_path: Path) -> None:
        _write_score_artifact(tmp_path / ScoringStage.TEST_BENIGN / "c1.parquet", [0.1])
        _write_score_artifact(tmp_path / ScoringStage.TEST_ATTACK / "c1.parquet", [0.5])
        provider = ScoreProvider(tmp_path)
        b, a = provider.load_test_scores("c1")
        b2, a2 = provider.load_test_scores("c1")
        np.testing.assert_allclose(b, b2)
        np.testing.assert_allclose(a, a2)
