# SPDX-License-Identifier: Proprietary
"""TrainingClientCatalog — single source of truth for client identity during training."""

from __future__ import annotations

from pathlib import Path

from datp.artifacts.names import ArtifactFile
from datp.core.errors import fmt
from datp.data.splits import Split, filename_for_split
from datp.federated.data_loading import discover_client_dirs
from datp.federated.types import ClientData

_MODULE = "federated.catalog"


class TrainingClientCatalog:
    """Discovers and validates the deterministic ordered list of client IDs.

    Works in two modes:
      - prepared_dir mode: discovers client IDs from on-disk directories.
      - in-memory mode: extracts client IDs from the provided client_data dict.

    At least one source must be non-empty. When both are provided, the prepared_dir
    source wins (in-memory data is used only for scoring afterward).
    """

    def __init__(
        self,
        *,
        client_data: dict[str, ClientData] | None = None,
        prepared_dir: Path | None = None,
    ) -> None:
        self._prepared_dir = prepared_dir
        if prepared_dir is not None:
            dirs = discover_client_dirs(prepared_dir)
            if not dirs:
                raise ValueError(
                    fmt(
                        _MODULE,
                        "prepared_dir contains no client directories",
                        "at least one client directory",
                        f"empty: {prepared_dir}",
                    )
                )
            self._client_ids = sorted(d.name for d in dirs)
        elif client_data:
            self._client_ids = sorted(client_data.keys())
        else:
            raise ValueError(
                fmt(
                    _MODULE,
                    "No client source provided",
                    "non-empty client_data or valid prepared_dir",
                    "both None/empty",
                )
            )

    @property
    def client_ids(self) -> list[str]:
        return list(self._client_ids)

    @property
    def num_clients(self) -> int:
        return len(self._client_ids)

    @property
    def prepared_dir(self) -> Path | None:
        return self._prepared_dir

    def validate_prepared_splits(self) -> None:
        """Validate that all required split files exist for every client in prepared_dir."""
        if self._prepared_dir is None:
            return
        required = tuple(filename_for_split(s) for s in Split) + (
            str(ArtifactFile.SCALER),
        )
        for cid in self._client_ids:
            client_dir = self._prepared_dir / cid
            if not client_dir.is_dir():
                raise FileNotFoundError(
                    fmt(
                        _MODULE,
                        f"Client directory missing: {cid}",
                        f"directory at {client_dir}",
                        "not found",
                    )
                )
            missing = [name for name in required if not (client_dir / name).exists()]
            if missing:
                raise FileNotFoundError(
                    fmt(
                        _MODULE,
                        f"Missing prepared artifacts for {cid}",
                        ", ".join(required),
                        f"missing: {', '.join(missing)}",
                    )
                )
