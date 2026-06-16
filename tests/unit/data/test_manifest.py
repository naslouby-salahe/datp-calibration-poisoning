from __future__ import annotations

import json

import pytest

from datp.data.catalog import DatasetID
from datp.data.manifests import (
    ManifestMetadata,
    PartitionManifest,
    compute_manifest_hashes,
    create_manifest,
)


@pytest.fixture()
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


class TestComputeManifestHashes:
    def test_returns_relative_keys(self, raw_tree):
        base, files = raw_tree
        hashes = compute_manifest_hashes(files, base)
        assert "device_a/benign.csv" in hashes
        assert "device_a/attacks/combo.csv" in hashes
        assert "device_b.csv" in hashes
        assert len(hashes) == 3


class TestManifestWriteReadRoundtrip:
    def test_manifest_write_read_roundtrip(self, tmp_path, raw_tree):
        base, files = raw_tree
        mpath = tmp_path / "manifest.json"
        manifest = create_manifest(
            dataset=DatasetID.NBAIOT,
            raw_files=files,
            raw_base_dir=base,
            metadata=ManifestMetadata.model_validate({"n_devices": 2, "n_features": 115}),
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
    def test_hash_verification_passes_on_unchanged(self, tmp_path, raw_tree):
        base, files = raw_tree
        mpath = tmp_path / "manifest.json"
        create_manifest(
            dataset=DatasetID.NBAIOT,
            raw_files=files,
            raw_base_dir=base,
            metadata=ManifestMetadata.model_validate({"n_devices": 2, "n_features": 115}),
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
            metadata=ManifestMetadata.model_validate({"n_devices": 2, "n_features": 115}),
            manifest_path=mpath,
        )
        files[0].write_bytes(b"MUTATED CONTENT")
        with pytest.raises(RuntimeError, match=r"\[data\.manifests\].*hash mismatch"):
            PartitionManifest.load(mpath).verify_hashes(base)

    def test_hash_verification_fails_on_missing_file(self, tmp_path, raw_tree):
        base, files = raw_tree
        mpath = tmp_path / "manifest.json"
        create_manifest(
            dataset=DatasetID.NBAIOT,
            raw_files=files,
            raw_base_dir=base,
            metadata=ManifestMetadata.model_validate({"n_devices": 2, "n_features": 115}),
            manifest_path=mpath,
        )
        files[1].unlink()
        with pytest.raises(RuntimeError, match=r"\[data\.manifests\].*not found"):
            PartitionManifest.load(mpath).verify_hashes(base)


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
        m = ManifestMetadata.model_validate({
            "n_devices": 3,
            "n_features": 100,
            "extra_field": "preserved",
        })
        assert m.n_devices == 3
        assert m.n_features == 100
        # extra fields are stored via ConfigDict(extra="allow")
        assert m.model_extra == {"extra_field": "preserved"}

    def test_both_n_devices_and_n_clients_accepted(self):
        m = ManifestMetadata.model_validate({
            "n_devices": 5,
            "n_clients": 10,
            "n_features": 115,
        })
        assert m.n_devices == 5
        assert m.n_clients == 10


class TestManifestEmptyHashes:
    def test_empty_file_hashes_rejected(self, tmp_path):
        p = tmp_path / "manifest.json"
        data = {
            "dataset": "nbaiot",
            "created": "2026-04-20T00:00:00+00:00",
            "file_hashes": {},
            "metadata": {"n_devices": 2, "n_features": 115},
        }
        _write_json(p, data)
        with pytest.raises(RuntimeError, match=r"\[data\.manifests\].*file_hashes.*empty"):
            PartitionManifest.load(p)
