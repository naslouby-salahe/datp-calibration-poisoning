from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from datp.core.errors import fmt, fmt_missing
from datp.core.logging import get_logger
from datp.core.provenance import hash_file, utc_timestamp

MANIFEST_MODULE = "data.manifests"
logger = get_logger(__name__)


def compute_manifest_hashes(raw_files: list[Path], base_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for fpath in sorted(raw_files):
        rel = fpath.relative_to(base_dir)
        hashes[str(rel)] = hash_file(fpath)
    return hashes


class ManifestMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")
    n_features: int
    n_devices: int | None = None
    n_clients: int | None = None

    @model_validator(mode="after")
    def check_client_count(self) -> "ManifestMetadata":
        if self.n_devices is None and self.n_clients is None:
            raise ValueError(
                fmt(
                    MANIFEST_MODULE,
                    "metadata missing client count",
                    "n_devices or n_clients",
                    "None",
                )
            )
        return self


class PartitionManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: str = Field(min_length=1, pattern=r"\S")
    file_hashes: dict[str, str]
    metadata: ManifestMetadata
    created: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_hashes(self) -> "PartitionManifest":
        if not self.file_hashes:
            raise ValueError(
                fmt(
                    MANIFEST_MODULE,
                    "file_hashes is empty",
                    "at least 1 hash",
                    "0 entries",
                )
            )
        return self

    @classmethod
    def load(cls, path: Path) -> "PartitionManifest":
        if not path.exists():
            raise RuntimeError(fmt_missing(MANIFEST_MODULE, f"Manifest file {path}"))
        try:
            return cls.model_validate_json(path.read_bytes())
        except (ValueError, TypeError) as exc:
            raise RuntimeError(
                fmt(
                    MANIFEST_MODULE,
                    "Malformed manifest JSON",
                    "valid JSON matching schema",
                    f"parse error ({exc})",
                )
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
                    fmt_missing(MANIFEST_MODULE, f"Raw file {rel_path_str}")
                )
            actual_hash = hash_file(fpath)
            if actual_hash != expected_hash:
                raise RuntimeError(
                    fmt(
                        MANIFEST_MODULE,
                        f"Raw file hash mismatch for {rel_path_str}",
                        expected_hash,
                        actual_hash,
                    )
                )
        logger.info(
            "partition manifest hash verification passed", n_files=len(self.file_hashes)
        )


def create_manifest(
    *,
    dataset: str,
    raw_files: list[Path],
    raw_base_dir: Path,
    metadata: dict[str, Any] | ManifestMetadata,
    manifest_path: Path,
) -> PartitionManifest:
    file_hashes = compute_manifest_hashes(raw_files, raw_base_dir)
    manifest = PartitionManifest(
        dataset=dataset,
        created=utc_timestamp(),
        file_hashes=file_hashes,
        metadata=metadata
        if isinstance(metadata, ManifestMetadata)
        else ManifestMetadata.model_validate(metadata),
    )
    manifest.write(manifest_path)
    return manifest
