"""Tests verifying federation simulation runner setups, stage validations, and data loading precedence."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import torch

from datp.config.models import ExperimentStage
from datp.core.enums import DeviceType
from datp.federated.clients import DatpClient
from datp.federated.simulation import (
    FlSimulationRequest,
    SimClientConfig,
    TrainingResult,
    load_scoring_data,
    validate_stage,
)
from datp.federated.types import ClientData
from datp.modeling.autoencoder import Autoencoder

_STAGE = ExperimentStage.NBAIOT_MAIN


class TestValidateStage:
    """Tests verifying configuration stage validity parsing."""

    def test_returns_stage_when_set(self) -> None:
        """Verify validate_stage returns the correct stage when populated in config."""
        cfg = MagicMock()
        cfg.stage = _STAGE
        assert validate_stage(cfg) is _STAGE

    def test_raises_when_stage_is_none(self) -> None:
        """Verify ValueError is raised if the configuration stage is None."""
        cfg = MagicMock()
        cfg.stage = None
        with pytest.raises(ValueError, match="stage must be set"):
            validate_stage(cfg)


class TestSimClientConfig:
    """Tests verifying client configuration freezes and properties."""

    def test_default_construction(self) -> None:
        """Verify default properties of SimClientConfig."""
        c = SimClientConfig()
        assert c.client_cls is DatpClient
        assert c.client_extra_kwargs is None
        assert c.encoder_only is False
        assert c.score_after is True

    def test_custom_construction(self) -> None:
        """Verify custom properties of SimClientConfig."""
        c = SimClientConfig(
            client_cls=DatpClient,
            client_extra_kwargs={"mu": 0.1},
            encoder_only=True,
            score_after=False,
        )
        assert c.client_cls is DatpClient
        assert c.encoder_only is True
        assert c.score_after is False
        assert c.client_extra_kwargs is not None
        assert c.client_extra_kwargs["mu"] == pytest.approx(0.1)

    def test_is_frozen(self) -> None:
        """Verify that SimClientConfig fields are frozen to modifications."""
        c = SimClientConfig()
        with pytest.raises(Exception):
            setattr(c, "encoder_only", True)


class TestTrainingResult:
    """Tests verifying training results containers."""

    def _make(self, tmp_path: Path) -> TrainingResult:
        """Helper to build a standard TrainingResult container."""
        return TrainingResult(
            stage=_STAGE,
            seed=0,
            converged_round=10,
            total_rounds=20,
            checkpoint_dir=tmp_path,
            score_dir=tmp_path,
            loss_history=[1.0, 0.5],
        )

    def test_construction(self, tmp_path: Path) -> None:
        """Verify that TrainingResult properties match construction arguments."""
        r = self._make(tmp_path)
        assert r.stage is _STAGE
        assert r.seed == 0
        assert r.converged_round == 10
        assert r.total_rounds == 20
        assert r.loss_history == [1.0, 0.5]

    def test_converged_round_can_be_none(self, tmp_path: Path) -> None:
        """Verify converged_round property can be None if simulation failed to converge."""
        r = TrainingResult(
            stage=_STAGE,
            seed=1,
            converged_round=None,
            total_rounds=5,
            checkpoint_dir=tmp_path,
            score_dir=tmp_path,
            loss_history=[],
        )
        assert r.converged_round is None

    def test_is_frozen(self, tmp_path: Path) -> None:
        """Verify that TrainingResult fields are frozen to modifications."""
        r = self._make(tmp_path)
        with pytest.raises(Exception):
            setattr(r, "seed", 99)


def _client_data() -> ClientData:
    """Helper to build empty ClientData tensors."""
    return ClientData(
        train=torch.zeros(2, 2),
        val=torch.zeros(2, 2),
        test_benign=torch.zeros(2, 2),
        test_attack=torch.zeros(2, 2),
    )


class TestLoadScoringData:
    """Tests verifying precedence rules between memory client data and disk directories."""

    def test_returns_client_data_when_no_prepared_dir(self) -> None:
        """Verify in-memory client data is returned if prepared_dir is None."""
        data = {"c0": _client_data()}
        result = load_scoring_data(data, None)
        assert result is data

    def test_raises_when_both_absent(self) -> None:
        """Verify ValueError is raised if both scoring inputs are absent."""
        with pytest.raises(ValueError, match="No scoring data source"):
            load_scoring_data(None, None)

    def test_raises_when_client_data_empty_and_no_prepared_dir(self) -> None:
        """Verify ValueError is raised if in-memory client data is empty and prepared_dir is None."""
        with pytest.raises(ValueError, match="No scoring data source"):
            load_scoring_data({}, None)

    def test_loads_from_prepared_dir_ignoring_client_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify load client data from prepared_dir when in-memory client data is absent."""
        import datp.federated.simulation as sim_mod

        fake = {"c0": _client_data()}
        monkeypatch.setattr(sim_mod, "load_client_data", lambda *_a, **_kw: fake)

        result = load_scoring_data(None, tmp_path)
        assert result is fake

    def test_prepared_dir_wins_over_client_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify that prepared_dir loader takes precedence over in-memory client data."""
        import datp.federated.simulation as sim_mod

        from_disk = {"from_disk": _client_data()}
        monkeypatch.setattr(sim_mod, "load_client_data", lambda *_, **__: from_disk)

        in_memory = {"in_memory": _client_data()}
        result = load_scoring_data(in_memory, tmp_path)
        assert result is from_disk


class TestClientDataNotMutated:
    """Tests verifying run_fl_simulation does not mutate input client data."""

    def test_client_data_keys_preserved_when_prepared_dir_set(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify that original client data dict keys are not mutated by simulation run."""
        import datp.federated.simulation as sim_mod

        class _FakeCatalog:
            def __init__(self, **_kw: object) -> None: ...

            client_ids = ["client_0"]
            num_clients = 1

            def validate_prepared_splits(self) -> None: ...

        def fake_build_model(*_a: object, **_kw: object) -> object:
            raise RuntimeError("stop-early")

        monkeypatch.setattr(sim_mod, "TrainingClientCatalog", _FakeCatalog)
        monkeypatch.setattr(sim_mod, "validate_stage", lambda _cfg: _STAGE)
        monkeypatch.setattr(
            sim_mod, "resolve_device", lambda _: torch.device(DeviceType.CPU)
        )
        monkeypatch.setattr(sim_mod, "set_seeds", lambda _: None)
        monkeypatch.setattr(sim_mod, "build_model", fake_build_model)

        original_data: dict[str, ClientData] = {"client_0": _client_data()}
        prepared_dir = tmp_path / "prepared"

        mock_cfg = MagicMock()
        mock_cfg.machine.require_cuda = False

        with pytest.raises(RuntimeError, match="stop-early"):
            sim_mod.run_fl_simulation(
                FlSimulationRequest(
                    cfg=mock_cfg,
                    client_data=original_data,
                    seed=0,
                    model_cls=Autoencoder,
                    ckpt_dir=tmp_path,
                    score_base=tmp_path,
                    label="test",
                    prepared_dir=prepared_dir,
                )
            )

        assert set(original_data.keys()) == {"client_0"}, (
            "client_data must not be mutated by run_fl_simulation"
        )
