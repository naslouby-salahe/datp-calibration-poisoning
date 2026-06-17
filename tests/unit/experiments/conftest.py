from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def allow_mlflow_file_store(monkeypatch: pytest.MonkeyPatch) -> None:
    """Opt out of MLflow's file-store maintenance-mode exception for unit tests."""
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
