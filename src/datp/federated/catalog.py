"""Client catalog for federated training data discovery and validation."""

from __future__ import annotations

from pathlib import Path

from datp.artifacts.names import ArtifactFile
from datp.data.splits import Split, filename_for_split
from datp.federated.data_loading import discover_client_dirs
from datp.federated.types import ClientData


class TrainingClientCatalog:
    """Catalog of client identities and their prepared data directories."""

    def __init__(
        self,
        *,
        client_data: dict[str, ClientData] | None = None,
        prepared_dir: Path | None = None,
    ) -> None:
        """Initialize from in-memory client data or a prepared directory."""
        self._prepared_dir = prepared_dir
        if prepared_dir is not None:
            dirs = discover_client_dirs(prepared_dir)
            if not dirs:
                raise ValueError(f"prepared_dir empty: {prepared_dir}")
            self._client_ids = sorted(d.name for d in dirs)
        elif client_data:
            self._client_ids = sorted(client_data.keys())
        else:
            raise ValueError("No non-empty client_data or valid prepared_dir provided")

    @property
    def client_ids(self) -> list[str]:
        """Return a copy of the sorted client ID list."""
        return list(self._client_ids)

    @property
    def num_clients(self) -> int:
        """Number of clients in the catalog."""
        return len(self._client_ids)

    @property
    def prepared_dir(self) -> Path | None:
        """Root directory of prepared per-client data, if any."""
        return self._prepared_dir

    def validate_prepared_splits(self) -> None:
        """Verify that every client directory contains all required split and scaler files."""
        if self._prepared_dir is None:
            return
        required = tuple(filename_for_split(s) for s in Split) + (
            str(ArtifactFile.SCALER),
        )
        for cid in self._client_ids:
            client_dir = self._prepared_dir / cid
            if not client_dir.is_dir():
                raise FileNotFoundError(f"Missing client directory: {client_dir}")
            missing = [name for name in required if not (client_dir / name).exists()]
            if missing:
                raise FileNotFoundError(
                    f"Missing prepared artifacts for {cid}: {', '.join(missing)}"
                )
