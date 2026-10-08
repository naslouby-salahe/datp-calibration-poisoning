from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
import pytest
from sklearn.preprocessing import StandardScaler

from datp.config import ExperimentStage
from datp.data import (
    ATTACK_FAMILY_DIRS,
    DEVICE_DIRS,
    DEVICE_FAMILY_MAP,
    SPLIT_RATIOS,
    ManifestMetadata,
    PartitionManifest,
    PartitionResult,
    SplitPolicyRole,
    apply_scaler,
    assert_no_csv_artifacts,
    audit_partitions,
    create_manifest,
    dataset_spec,
    fit_scaler,
    load_scaler,
    read_artifact,
    run_schema_audit,
    save_scaler,
    write_artifact,
)
from datp.enums import (
    ArtifactFile,
    AuditDir,
    ClientStatus,
    DatasetID,
    NBaIoTAttackFamily,
    NBaIoTDevice,
    NBaIoTDeviceFamily,
)
from datp.reporting.figures import NBAIOT_DEVICE_SHORT_LABELS

REQUIRED_CLIENT_FIELDS = {
    "benign_train_count",
    "benign_cal_count",
    "test_benign_count",
    "test_attack_count",
    "attack_classes",
    "calibration_pending",
    "evaluation_incomplete",
}


def _make_partition_results(
    n_clients: int = 3,
    cal_count: int = 200,
    eval_incomplete: bool = False,
) -> dict[str, PartitionResult]:
    results = {}
    for i in range(n_clients):
        results[f"device_{i}"] = PartitionResult(
            benign_train_count=1000 + i,
            benign_cal_count=cal_count + i,
            test_benign_count=500 + i,
            test_attack_count=800 + i,
            attack_classes=[f"atk_a_{i}", f"atk_b_{i}"],
            status=(
                ClientStatus.CALIBRATION_PENDING
                if cal_count + i < 100
                else ClientStatus.ELIGIBLE
            ),
            evaluation_incomplete=eval_incomplete,
        )
    return results


class TestAuditWritesJson:
    """Audit writes a valid JSON output file."""

    def test_audit_writes_json(self, tmp_path: Path) -> None:
        results = _make_partition_results()
        audit_partitions(
            results, stage=ExperimentStage.NBAIOT_MAIN, output_dir=tmp_path, n_min=100
        )
        audit_file = tmp_path / AuditDir.DATA_AUDIT / "nbaiot_main_audit.json"
        assert audit_file.exists()
        data = json.loads(audit_file.read_text())
        assert data["stage"] == "nbaiot_main"
        assert data["n_clients"] == 3


class TestAuditSummaryCounts:
    """Audit summary counts match partition results."""

    def test_audit_summary_counts(self, tmp_path: Path) -> None:
        results = _make_partition_results(n_clients=4, cal_count=150)
        audit = audit_partitions(
            results,
            stage=ExperimentStage.NBAIOT_MAIN,
            output_dir=tmp_path,
            n_min=100,
        )

        assert audit.summary.total_benign_train == sum(
            c.benign_train_count for c in audit.clients.values()
        )
        assert audit.summary.total_benign_cal == sum(
            c.benign_cal_count for c in audit.clients.values()
        )
        assert audit.summary.total_test_benign == sum(
            c.test_benign_count for c in audit.clients.values()
        )
        assert audit.summary.total_test_attack == sum(
            c.test_attack_count for c in audit.clients.values()
        )


class TestAuditFlagsCalibrationPending:
    """Audit correctly flags calibration-pending clients."""

    def test_audit_flags_calibration_pending(self, tmp_path: Path) -> None:
        results = _make_partition_results(n_clients=2, cal_count=50)

        audit = audit_partitions(
            results, stage=ExperimentStage.NBAIOT_MAIN, output_dir=tmp_path, n_min=100
        )

        for client_info in audit.clients.values():
            assert client_info.calibration_pending is True

        assert audit.summary.calibration_pending_count == 2
        assert audit.summary.all_above_n_min is False


class TestAuditAllAboveNMin:
    """All clients above n_min pass the audit."""

    def test_audit_all_above_n_min(self, tmp_path: Path) -> None:
        results = _make_partition_results(n_clients=3, cal_count=200)
        audit = audit_partitions(
            results, stage=ExperimentStage.NBAIOT_MAIN, output_dir=tmp_path, n_min=100
        )

        assert audit.summary.all_above_n_min is True
        assert audit.summary.calibration_pending_count == 0


class TestAuditRequiredFields:
    """Audit output includes all required schema fields."""

    def test_audit_includes_all_required_fields(self, tmp_path: Path) -> None:
        results = _make_partition_results(n_clients=2, cal_count=300)
        audit = audit_partitions(
            results,
            stage=ExperimentStage.NBAIOT_MAIN,
            output_dir=tmp_path,
            n_min=100,
        )

        for client_id, client_info in audit.clients.items():
            missing = REQUIRED_CLIENT_FIELDS - {
                f for f in REQUIRED_CLIENT_FIELDS if hasattr(client_info, f)
            }
            assert not missing, f"{client_id} missing fields: {missing}"

        assert audit.stage is not None
        assert audit.n_clients >= 0
        assert audit.n_min >= 0
        assert audit.summary is not None
        assert audit.clients is not None


class TestSchemaAuditFeatureCountMismatch:
    """Schema audit detects feature-count mismatches."""

    def test_feature_count_mismatch_parquet(self, tmp_path: Path) -> None:
        rng = np.random.default_rng(42)
        import polars as pl

        df = pl.DataFrame(
            rng.standard_normal((50, 10)),
            schema=[f"feat_{i}" for i in range(10)],
        )
        file_path = tmp_path / "data.parquet"
        df.write_parquet(file_path)

        with pytest.raises(ValueError, match="Feature count mismatch"):
            run_schema_audit(file_path, expected_feature_count=15)

    def test_feature_count_match_passes(self, tmp_path: Path) -> None:
        rng = np.random.default_rng(42)
        import polars as pl

        df = pl.DataFrame(
            rng.standard_normal((50, 115)),
            schema=[f"feat_{i}" for i in range(115)],
        )
        file_path = tmp_path / "data.parquet"
        df.write_parquet(file_path)

        run_schema_audit(file_path, expected_feature_count=115)

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            run_schema_audit(
                tmp_path / "nonexistent.parquet", expected_feature_count=10
            )

    def test_unsupported_format_raises(self, tmp_path: Path) -> None:
        file_path = tmp_path / "data.json"
        file_path.write_text("{}")

        with pytest.raises(ValueError, match="Unsupported file format"):
            run_schema_audit(file_path, expected_feature_count=10)


@pytest.fixture
def sample_df() -> pl.DataFrame:
    return pl.DataFrame({"feature_a": [1.0, 2.0, 3.0], "feature_b": [4.0, 5.0, 6.0]})


class TestWriteArtifact:
    """Parquet artifact writing."""

    def test_produces_parquet_file(self, tmp_path, sample_df):
        path = tmp_path / "train.parquet"
        write_artifact(sample_df, path)
        assert path.exists()
        assert path.suffix == ".parquet"

    def test_creates_parent_directories(self, tmp_path, sample_df):
        path = tmp_path / "nested" / "dir" / "cal.parquet"
        write_artifact(sample_df, path)
        assert path.exists()

    def test_raises_on_csv_extension(self, tmp_path, sample_df):
        path = tmp_path / "train.csv"
        with pytest.raises(ValueError, match=r"\.parquet.*\.csv"):
            write_artifact(sample_df, path)

    def test_raises_on_other_extension(self, tmp_path, sample_df):
        path = tmp_path / "train.hdf5"
        with pytest.raises(ValueError, match=r"\.parquet"):
            write_artifact(sample_df, path)

    def test_raises_on_no_extension(self, tmp_path, sample_df):
        path = tmp_path / "train"
        with pytest.raises(ValueError, match=r"\.parquet"):
            write_artifact(sample_df, path)


class TestReadArtifact:
    """Parquet artifact reading."""

    def test_raises_on_csv_extension(self, tmp_path):
        path = tmp_path / "test_benign.csv"
        with pytest.raises(ValueError, match=r"\.parquet.*\.csv"):
            read_artifact(path)

    def test_raises_on_other_extension(self, tmp_path):
        path = tmp_path / "test_attack.feather"
        with pytest.raises(ValueError, match=r"\.parquet"):
            read_artifact(path)

    def test_raises_file_not_found(self, tmp_path):
        path = tmp_path / "missing.parquet"
        with pytest.raises(FileNotFoundError):
            read_artifact(path)


class TestRoundTrip:
    """Parquet write-then-read round-trip fidelity."""

    def test_parquet_only(self, tmp_path, sample_df):
        path = tmp_path / "test_benign.parquet"
        write_artifact(sample_df, path)
        result = read_artifact(path)
        from polars.testing import assert_frame_equal

        assert_frame_equal(result, sample_df)

    def test_preserves_dtypes(self, tmp_path):
        df = pl.DataFrame(
            {
                "int_col": [1, 2, 3],
                "float_col": [1.1, 2.2, 3.3],
                "str_col": ["a", "b", "c"],
            },
            schema={"int_col": pl.Int64, "float_col": pl.Float64, "str_col": pl.String},
        )
        path = tmp_path / "cal.parquet"
        write_artifact(df, path)
        result = read_artifact(path)
        from polars.testing import assert_frame_equal

        assert_frame_equal(result, df)


class TestAssertNoCsvArtifacts:
    """No CSV artifacts remain; only Parquet is used."""

    def test_passes_on_parquet_only(self, tmp_path, sample_df):
        write_artifact(sample_df, tmp_path / "train.parquet")
        write_artifact(sample_df, tmp_path / "cal.parquet")
        assert_no_csv_artifacts(tmp_path)

    def test_passes_on_empty_directory(self, tmp_path):
        assert_no_csv_artifacts(tmp_path)

    def test_passes_on_nonexistent_directory(self, tmp_path):
        assert_no_csv_artifacts(tmp_path / "does_not_exist")

    def test_fails_if_csv_present(self, tmp_path, sample_df):
        write_artifact(sample_df, tmp_path / "train.parquet")
        (tmp_path / "leftover.csv").write_text("a,b\n1,2\n")
        with pytest.raises(RuntimeError, match=r"CSV files found"):
            assert_no_csv_artifacts(tmp_path)

    def test_fails_on_nested_csv(self, tmp_path, sample_df):
        sub = tmp_path / "client_0"
        sub.mkdir()
        write_artifact(sample_df, sub / "test_attack.parquet")
        (sub / "stale.csv").write_text("x\n1\n")
        with pytest.raises(RuntimeError, match=r"CSV files found"):
            assert_no_csv_artifacts(tmp_path)


class TestDatasetID:
    """DatasetID enum values."""

    def test_all_members_present(self) -> None:
        assert set(DatasetID) == {
            DatasetID.NBAIOT,
        }

    def test_values_are_lowercase_slugs(self) -> None:
        for member in DatasetID:
            assert member.value == member.value.lower()
            assert " " not in member.value


class TestNBaIoTEnums:
    def test_device_catalog_and_family_map_cover_the_enum_domain(self) -> None:
        assert set(DEVICE_DIRS) == set(NBaIoTDevice)
        assert set(DEVICE_FAMILY_MAP) == set(NBaIoTDevice)
        assert set(DEVICE_FAMILY_MAP.values()) == set(NBaIoTDeviceFamily)

    def test_attack_families_and_report_labels_cover_their_enum_domains(self) -> None:
        assert set(ATTACK_FAMILY_DIRS) == set(NBaIoTAttackFamily)
        assert set(NBAIOT_DEVICE_SHORT_LABELS) == set(NBaIoTDevice)
        assert ArtifactFile.BENIGN_TRAFFIC.value == "benign_traffic.csv"


class TestDatasetPolicyEnums:
    def test_split_policy_role_members(self) -> None:
        assert set(SplitPolicyRole) == {
            SplitPolicyRole.TRAIN,
            SplitPolicyRole.GAP1,
            SplitPolicyRole.CAL,
            SplitPolicyRole.GAP2,
            SplitPolicyRole.TEST_BENIGN,
        }


class TestDatasetSpecHelper:
    """DatasetSpec helper lookups."""

    def test_nbaiot_properties(self) -> None:
        spec = dataset_spec(DatasetID.NBAIOT)
        assert spec.id == DatasetID.NBAIOT
        assert spec.feature_count == 115
        assert spec.processed_slug == "nbaiot"
        assert SPLIT_RATIOS[SplitPolicyRole.CAL] == 0.20
        assert spec.family_map is not None

    def test_raises_keyerror_for_invalid_id(self) -> None:
        with pytest.raises(KeyError):
            dataset_spec("not_an_enum")  # type: ignore[arg-type]


@pytest.fixture
def raw_tree(tmp_path):
    base = tmp_path / "raw"
    base.mkdir()

    (base / "device_a").mkdir()
    f1 = base / "device_a" / "benign.csv"
    f1.write_bytes(b"col1,col2\n1,2\n3,4\n")

    (base / "device_a" / "attacks").mkdir()
    f2 = base / "device_a" / "attacks" / "combo.csv"
    f2.write_bytes(b"col1,col2\n5,6\n7,8\n")

    f3 = base / "device_b.csv"
    f3.write_bytes(b"x,y\n9,10\n")

    return base, [f1, f2, f3]


class TestManifestWriteReadRoundtrip:
    """Manifest survives write-then-read round-trip."""

    def test_manifest_write_read_roundtrip(self, tmp_path, raw_tree):
        base, files = raw_tree
        mpath = tmp_path / "manifest.json"
        manifest = create_manifest(
            dataset=DatasetID.NBAIOT,
            raw_files=files,
            raw_base_dir=base,
            metadata=ManifestMetadata.model_validate(
                {"n_devices": 2, "n_features": 115}
            ),
            manifest_path=mpath,
        )
        loaded = PartitionManifest.load(mpath)
        assert loaded.dataset == manifest.dataset
        assert loaded.file_hashes == manifest.file_hashes
        assert loaded.metadata.n_devices == manifest.metadata.n_devices
        assert loaded.metadata.n_features == manifest.metadata.n_features

    def test_load_missing_manifest_raises(self, tmp_path):
        with pytest.raises(RuntimeError, match=r"\[data\.manifests\].*not found"):
            PartitionManifest.load(tmp_path / "no_such.json")


class TestVerifyManifestHashes:
    """Manifest hash verification detects mismatches."""

    def test_hash_verification_passes_on_unchanged(self, tmp_path, raw_tree):
        base, files = raw_tree
        mpath = tmp_path / "manifest.json"
        create_manifest(
            dataset=DatasetID.NBAIOT,
            raw_files=files,
            raw_base_dir=base,
            metadata=ManifestMetadata.model_validate(
                {"n_devices": 2, "n_features": 115}
            ),
            manifest_path=mpath,
        )
        PartitionManifest.load(mpath).verify_hashes(base)

    def test_hash_verification_fails_on_mutated(self, tmp_path, raw_tree):
        base, files = raw_tree
        mpath = tmp_path / "manifest.json"
        create_manifest(
            dataset=DatasetID.NBAIOT,
            raw_files=files,
            raw_base_dir=base,
            metadata=ManifestMetadata.model_validate(
                {"n_devices": 2, "n_features": 115}
            ),
            manifest_path=mpath,
        )
        files[0].write_bytes(b"MUTATED CONTENT")
        load_value = PartitionManifest.load(mpath)
        with pytest.raises(RuntimeError, match=r"\[data\.manifests\].*hash mismatch"):
            load_value.verify_hashes(base)

    def test_hash_verification_fails_on_missing_file(self, tmp_path, raw_tree):
        base, files = raw_tree
        mpath = tmp_path / "manifest.json"
        create_manifest(
            dataset=DatasetID.NBAIOT,
            raw_files=files,
            raw_base_dir=base,
            metadata=ManifestMetadata.model_validate(
                {"n_devices": 2, "n_features": 115}
            ),
            manifest_path=mpath,
        )
        files[1].unlink()
        load_value = PartitionManifest.load(mpath)
        with pytest.raises(RuntimeError, match=r"\[data\.manifests\].*not found"):
            load_value.verify_hashes(base)


def _write_json(path, data):
    path.write_text(json.dumps(data, indent=2))


def _valid_manifest_dict():
    return {
        "dataset": "nbaiot",
        "created": "2026-04-20T00:00:00+00:00",
        "file_hashes": {"a.csv": "aaa111", "b.csv": "bbb222"},
        "metadata": {"n_devices": 2, "n_features": 115},
    }


class TestSelfValidatingLoad:
    """Self-validating manifest load catches corruption."""

    def test_self_validating_load_valid(self, tmp_path):
        p = tmp_path / "manifest.json"
        data = _valid_manifest_dict()
        _write_json(p, data)

        m = PartitionManifest.load(p)
        assert m.dataset == "nbaiot"
        assert m.file_hashes == {"a.csv": "aaa111", "b.csv": "bbb222"}
        assert m.metadata.n_devices == 2
        assert m.metadata.n_features == 115
        assert m.created == "2026-04-20T00:00:00+00:00"

    def test_self_validating_load_missing_dataset(self, tmp_path):
        p = tmp_path / "manifest.json"
        data = _valid_manifest_dict()
        del data["dataset"]
        _write_json(p, data)

        with pytest.raises(RuntimeError, match="dataset"):
            PartitionManifest.load(p)

    def test_self_validating_load_missing_file_hashes(self, tmp_path):
        p = tmp_path / "manifest.json"
        data = _valid_manifest_dict()
        del data["file_hashes"]
        _write_json(p, data)

        with pytest.raises(RuntimeError, match=r"file_hashes"):
            PartitionManifest.load(p)

    def test_self_validating_load_wrong_type_file_hashes(self, tmp_path):
        p = tmp_path / "manifest.json"
        data = _valid_manifest_dict()
        data["file_hashes"] = ["not", "a", "dict"]
        _write_json(p, data)

        with pytest.raises(RuntimeError, match="file_hashes"):
            PartitionManifest.load(p)

    def test_self_validating_load_missing_metadata(self, tmp_path):
        p = tmp_path / "manifest.json"
        data = _valid_manifest_dict()
        del data["metadata"]
        _write_json(p, data)

        with pytest.raises(RuntimeError, match="metadata"):
            PartitionManifest.load(p)

    def test_self_validating_load_malformed_json(self, tmp_path):
        p = tmp_path / "manifest.json"
        p.write_text("{broken json !!!")

        with pytest.raises(RuntimeError, match=r"\[data\.manifests\].*Malformed"):
            PartitionManifest.load(p)

    def test_self_validating_load_empty_dataset(self, tmp_path):
        p = tmp_path / "manifest.json"
        data = _valid_manifest_dict()
        data["dataset"] = " "
        _write_json(p, data)

        with pytest.raises(RuntimeError, match="dataset"):
            PartitionManifest.load(p)

    def test_self_validating_load_metadata_missing_n_features(self, tmp_path):
        p = tmp_path / "manifest.json"
        data = _valid_manifest_dict()
        data["metadata"] = {"n_devices": 2}
        _write_json(p, data)

        with pytest.raises(RuntimeError, match="n_features"):
            PartitionManifest.load(p)

    def test_self_validating_load_metadata_missing_device_count(self, tmp_path):
        p = tmp_path / "manifest.json"
        data = _valid_manifest_dict()
        data["metadata"] = {"n_features": 115}
        _write_json(p, data)

        with pytest.raises(RuntimeError, match="n_devices or n_clients"):
            PartitionManifest.load(p)

    def test_self_validating_load_n_clients_accepted(self, tmp_path):
        p = tmp_path / "manifest.json"
        data = _valid_manifest_dict()
        data["metadata"] = {"n_clients": 10, "n_features": 50}
        _write_json(p, data)

        m = PartitionManifest.load(p)
        assert m.metadata.n_clients == 10


class TestManifestMetadataValidation:
    """Manifest metadata field validation."""

    def test_requires_n_features(self):
        with pytest.raises(ValueError, match="n_features"):
            ManifestMetadata.model_validate({"n_devices": 5})

    def test_requires_device_or_client_count(self):
        with pytest.raises(ValueError, match="n_devices or n_clients"):
            ManifestMetadata.model_validate({"n_features": 115})

    def test_accepts_n_devices(self):
        m = ManifestMetadata.model_validate({"n_devices": 5, "n_features": 115})
        assert m.n_devices == 5
        assert m.n_features == 115

    def test_accepts_n_clients(self):
        m = ManifestMetadata.model_validate({"n_clients": 10, "n_features": 50})
        assert m.n_clients == 10
        assert m.n_features == 50

    def test_allows_extra_fields(self):
        m = ManifestMetadata.model_validate(
            {
                "n_devices": 3,
                "n_features": 100,
                "extra_field": "preserved",
            }
        )
        assert m.n_devices == 3
        assert m.n_features == 100

        assert m.model_extra == {"extra_field": "preserved"}

    def test_both_n_devices_and_n_clients_accepted(self):
        m = ManifestMetadata.model_validate(
            {
                "n_devices": 5,
                "n_clients": 10,
                "n_features": 115,
            }
        )
        assert m.n_devices == 5
        assert m.n_clients == 10


class TestManifestEmptyHashes:
    """Manifest with empty hashes still passes validation."""

    def test_empty_file_hashes_rejected(self, tmp_path):
        p = tmp_path / "manifest.json"
        data = {
            "dataset": "nbaiot",
            "created": "2026-04-20T00:00:00+00:00",
            "file_hashes": {},
            "metadata": {"n_devices": 2, "n_features": 115},
        }
        _write_json(p, data)
        with pytest.raises(RuntimeError, match=r"(?s)\[data\.manifests\].*file_hashes"):
            PartitionManifest.load(p)


class TestFitScaler:
    """Scaler fitting on training data."""

    def test_fitted_on_train_only(self) -> None:
        rng = np.random.default_rng(7)
        cols = [f"f{i}" for i in range(5)]
        train_df = pd.DataFrame(
            rng.standard_normal((200, 5)) * 3 + 10, columns=pd.Index(cols)
        )
        other_df = pd.DataFrame(
            rng.standard_normal((100, 5)) * 0.5 - 5, columns=pd.Index(cols)
        )

        scaler = fit_scaler(pl.from_pandas(train_df))

        assert scaler.mean_ is not None
        assert scaler.scale_ is not None
        np.testing.assert_allclose(
            np.asarray(scaler.mean_), train_df.to_numpy().mean(axis=0), atol=1e-10
        )
        np.testing.assert_allclose(
            np.asarray(scaler.scale_),
            train_df.to_numpy().std(axis=0, ddof=0),
            atol=1e-10,
        )

        scaled_train = apply_scaler(pl.from_pandas(train_df), scaler)
        np.testing.assert_allclose(
            scaled_train.to_numpy().mean(axis=0), 0.0, atol=1e-10
        )
        np.testing.assert_allclose(
            scaled_train.to_numpy().std(axis=0, ddof=0), 1.0, atol=1e-10
        )

        scaled_other = apply_scaler(pl.from_pandas(other_df), scaler)
        assert not np.allclose(scaled_other.to_numpy().mean(axis=0), 0.0, atol=0.5)

    def test_fit_empty_dataframe(self) -> None:
        df = pl.DataFrame(schema={"a": pl.Float64, "b": pl.Float64})
        scaler = fit_scaler(df)

        with pytest.raises(AttributeError):
            _ = scaler.mean_


class TestApplyScaler:
    """Scaler application to new data."""

    def test_apply_preserves_columns(self) -> None:
        cols = ["alpha", "beta", "gamma"]
        df = pd.DataFrame(np.ones((10, 3)), columns=pd.Index(cols))
        scaler = fit_scaler(pl.from_pandas(df))
        result = apply_scaler(pl.from_pandas(df), scaler)
        assert list(result.columns) == cols

    def test_apply_empty_dataframe(self) -> None:
        cols = ["x", "y"]
        df = pl.DataFrame(schema={"x": pl.Float64, "y": pl.Float64})
        scaler = StandardScaler()
        scaler.mean_ = np.array([1.0, 2.0])
        scaler.scale_ = np.array([0.5, 0.5])
        result = apply_scaler(df, scaler)
        assert len(result) == 0
        assert list(result.columns) == cols


class TestSaveLoadScaler:
    """Scaler save and load round-trip."""

    def test_round_trip(self, tmp_path: Path) -> None:
        rng = np.random.default_rng(8)
        cols = [f"f{i}" for i in range(5)]
        train_df = pd.DataFrame(rng.standard_normal((100, 5)), columns=pd.Index(cols))

        scaler = fit_scaler(pl.from_pandas(train_df))
        path = tmp_path / "scaler.pkl"
        save_scaler(scaler, path)
        loaded = load_scaler(path)

        assert loaded.mean_ is not None
        assert loaded.scale_ is not None
        assert scaler.mean_ is not None
        assert scaler.scale_ is not None
        np.testing.assert_allclose(np.asarray(loaded.mean_), np.asarray(scaler.mean_))
        np.testing.assert_allclose(np.asarray(loaded.scale_), np.asarray(scaler.scale_))

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        rng = np.random.default_rng(1)
        cols = ["a"]
        df = pd.DataFrame(rng.standard_normal((10, 1)), columns=pd.Index(cols))
        scaler = fit_scaler(pl.from_pandas(df))

        nested = tmp_path / "deep" / "nested" / "scaler.pkl"
        save_scaler(scaler, nested)
        assert nested.exists()

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.pkl"
        with pytest.raises(FileNotFoundError):
            load_scaler(missing)
