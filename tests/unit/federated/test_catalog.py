"""Tests verifying the training client catalog configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest
import torch

from datp.artifacts.names import ArtifactFile
from datp.data.common.storage import write_artifact
from datp.data.splits import Split, filename_for_split
from datp.federated.catalog import TrainingClientCatalog
from datp.federated.types import ClientData


def _write_client_dir(
    prepared_dir: Path, name: str, *, omit: str | None = None
) -> None:
    """Helper to write a mock prepared client directory on disk."""
    client_dir = prepared_dir / name
    client_dir.mkdir(parents=True)
    df = pl.DataFrame({"f0": [1.0], "f1": [2.0]})
    for split in Split:
        artifact = filename_for_split(split)
        if artifact != omit:
            write_artifact(df, client_dir / artifact)
    if omit != str(ArtifactFile.SCALER):
        (client_dir / str(ArtifactFile.SCALER)).write_bytes(b"scaler")


def _make_client_data(*names: str) -> dict[str, ClientData]:
    """Helper to build a dict of mock ClientData structures."""
    return {
        name: ClientData(
            train=torch.zeros(4, 2),
            val=torch.zeros(2, 2),
            test_benign=torch.zeros(2, 2),
            test_attack=torch.zeros(2, 2),
        )
        for name in names
    }


class TestTrainingClientCatalog:
    """Tests verifying properties and validation checks on TrainingClientCatalog."""

    def test_from_prepared_dir(self, tmp_path: Path) -> None:
        """Verify sorting and registration of clients from prepared directory."""
        prepared_dir = tmp_path / "prep"
        _write_client_dir(prepared_dir, "client_b")
        _write_client_dir(prepared_dir, "client_a")

        catalog = TrainingClientCatalog(prepared_dir=prepared_dir)

        assert catalog.client_ids == ["client_a", "client_b"]
        assert catalog.num_clients == 2

    def test_from_client_data(self) -> None:
        """Verify client catalog construction from memory ClientData structures."""
        data = _make_client_data("z_client", "a_client")

        catalog = TrainingClientCatalog(client_data=data)

        assert catalog.client_ids == ["a_client", "z_client"]
        assert catalog.num_clients == 2

    def test_prepared_dir_takes_precedence(self, tmp_path: Path) -> None:
        """Verify prepared_dir wins over memory client_data when both are set."""
        prepared_dir = tmp_path / "prep"
        _write_client_dir(prepared_dir, "disk_client")
        data = _make_client_data("memory_client")

        catalog = TrainingClientCatalog(client_data=data, prepared_dir=prepared_dir)

        assert catalog.client_ids == ["disk_client"]

    def test_raises_when_both_none(self) -> None:
        """Verify ValueError is raised if neither input is set."""
        with pytest.raises(
            ValueError, match="No non-empty client_data or valid prepared_dir"
        ):
            TrainingClientCatalog()

    def test_raises_when_empty_dict(self) -> None:
        """Verify ValueError is raised if client_data dictionary is empty."""
        with pytest.raises(
            ValueError, match="No non-empty client_data or valid prepared_dir"
        ):
            TrainingClientCatalog(client_data={})

    def test_client_ids_returns_copy(self) -> None:
        """Ensure client_ids property returns a copy of list to prevent mutation leaks."""
        data = _make_client_data("x")
        catalog = TrainingClientCatalog(client_data=data)

        ids = catalog.client_ids
        ids.append("mutation")
        assert catalog.client_ids == ["x"]

    def test_validate_prepared_splits_accepts_complete_client(
        self, tmp_path: Path
    ) -> None:
        """Verify validation passes for a prepared directory containing all splits."""
        prepared_dir = tmp_path / "prepared"
        _write_client_dir(prepared_dir, "client_0")

        catalog = TrainingClientCatalog(prepared_dir=prepared_dir)
        catalog.validate_prepared_splits()

    def test_validate_prepared_splits_rejects_missing_test_attack(
        self, tmp_path: Path
    ) -> None:
        """Verify validation raises FileNotFoundError if attack split is missing."""
        prepared_dir = tmp_path / "prepared"
        _write_client_dir(
            prepared_dir, "client_0", omit=filename_for_split(Split.TEST_ATTACK)
        )

        catalog = TrainingClientCatalog(prepared_dir=prepared_dir)
        with pytest.raises(
            FileNotFoundError, match=filename_for_split(Split.TEST_ATTACK)
        ):
            catalog.validate_prepared_splits()

    def test_validate_prepared_splits_noop_when_no_prepared_dir(self) -> None:
        """Verify validation is a no-op when client catalog is memory-only."""
        data = _make_client_data("a")
        catalog = TrainingClientCatalog(client_data=data)
        catalog.validate_prepared_splits()
