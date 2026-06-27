"""Shared fixtures for experiment unit tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def allow_mlflow_file_store(monkeypatch: pytest.MonkeyPatch) -> None:
    """Allow MLflow local file store in test environments."""
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
