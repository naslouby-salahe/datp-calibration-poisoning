from __future__ import annotations

from datp.types import (
    ContentHash,
    FeatureCount,
    JsonValue,
    NarrativeText,
    RecordKey,
    SampleCount,
)

from datp.core.enums import DatasetID

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from datp.core.logging import get_logger
from datp.core.provenance import hash_file, utc_timestamp

MANIFEST_MODULE = "data.manifests"
logger = get_logger(__name__)


class ManifestMetadata(BaseModel):

    model_config = ConfigDict(extra="allow")
    n_features: FeatureCount
    n_devices: SampleCount | None = None
    n_clients: SampleCount | None = None

    @model_validator(mode="after")
    def check_client_count(self) -> "ManifestMetadata":
        if self.n_devices is None and self.n_clients is None:
            raise ValueError(
                f"[{MANIFEST_MODULE}] metadata missing client count. Expected: n_devices or n_clients. Got: None."
            )
        return self


class PartitionManifest(BaseModel):

    model_config = ConfigDict(extra="forbid")
    dataset: DatasetID = Field(min_length=1, pattern=r"\S")
    file_hashes: dict[RecordKey, ContentHash] = Field(min_length=1)
    metadata: ManifestMetadata
    created: NarrativeText = Field(min_length=1)

    @classmethod
    def load(cls, path: Path) -> "PartitionManifest":
        if not path.exists():
            raise RuntimeError(f"[{MANIFEST_MODULE}] Manifest file {path} not found.")
        try:
            return cls.model_validate_json(path.read_bytes())
        except (ValueError, TypeError) as exc:
            raise RuntimeError(
                f"[{MANIFEST_MODULE}] Malformed manifest JSON. Expected: valid JSON matching schema. Got: parse error ({exc})."
            ) from exc

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(self.model_dump_json(indent=2))
        tmp.rename(path)
        logger.info("manifest written", path=str(path))

    def verify_hashes(self, raw_base_dir: Path) -> None:
        for rel_path_str, expected_hash in self.file_hashes.items():
            fpath = raw_base_dir / rel_path_str
            if not fpath.exists():
                raise RuntimeError(
                    f"[{MANIFEST_MODULE}] Raw file {rel_path_str} not found."
                )
            actual_hash = hash_file(fpath)
            if actual_hash != expected_hash:
                raise RuntimeError(
                    f"[{MANIFEST_MODULE}] Raw file hash mismatch for {rel_path_str}. Expected: {expected_hash}. Got: {actual_hash}."
                )
        logger.info(
            "partition manifest hash verification passed", n_files=len(self.file_hashes)
        )


def create_manifest(
    *,
    dataset: DatasetID,
    raw_files: list[Path],
    raw_base_dir: Path,
    metadata: JsonValue,
    manifest_path: Path,
) -> PartitionManifest:
    manifest = PartitionManifest(
        dataset=dataset,
        created=utc_timestamp(),
        file_hashes={
            str(p.relative_to(raw_base_dir)): hash_file(p) for p in sorted(raw_files)
        },
        metadata=metadata
        if isinstance(metadata, ManifestMetadata)
        else ManifestMetadata.model_validate(metadata),
    )
    manifest.write(manifest_path)
    return manifest
