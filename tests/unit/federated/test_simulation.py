# SPDX-License-Identifier: Proprietary
"""Tests for run_fl_simulation orchestration, validate_regime, SimClientConfig, TrainingResult, and load_scoring_data."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import torch

from datp.core.enums import DeviceType, Regime
from datp.federated.clients import DatpClient
from datp.federated.simulation import (
    SimClientConfig,
    TrainingResult,
    load_scoring_data,
    validate_regime,
)
from datp.federated.types import ClientData

# ---------------------------------------------------------------------------
# validate_regime
# ---------------------------------------------------------------------------


class TestValidateRegime:
    def test_returns_regime_when_set(self) -> None:
        cfg = MagicMock()
        cfg.regime = Regime.A
        assert validate_regime(cfg) is Regime.A

    def test_raises_when_regime_is_none(self) -> None:
        cfg = MagicMock()
        cfg.regime = None
        with pytest.raises(ValueError, match="regime must be set"):
            validate_regime(cfg)

    def test_error_message_includes_expected_and_got(self) -> None:
        cfg = MagicMock()
        cfg.regime = None
        with pytest.raises(ValueError, match="non-null regime"):
            validate_regime(cfg)


# ---------------------------------------------------------------------------
# SimClientConfig
# ---------------------------------------------------------------------------


class TestSimClientConfig:
    def test_default_construction(self) -> None:
        c = SimClientConfig()
        assert c.client_cls is DatpClient
        assert c.client_extra_kwargs is None
        assert c.encoder_only is False
        assert c.score_after is True

    def test_custom_construction(self) -> None:
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
        c = SimClientConfig()
        with pytest.raises(Exception):
            c.encoder_only = True # type: ignore[misc]


# ---------------------------------------------------------------------------
# TrainingResult
# ---------------------------------------------------------------------------


class TestTrainingResult:
    def _make(self, tmp_path: Path) -> TrainingResult:
        return TrainingResult(
            regime=Regime.A,
            seed=0,
            alpha=None,
            converged_round=10,
            total_rounds=20,
            checkpoint_dir=tmp_path,
            score_dir=tmp_path,
            loss_history=[1.0, 0.5],
        )

    def test_construction(self, tmp_path: Path) -> None:
        r = self._make(tmp_path)
        assert r.regime is Regime.A
        assert r.seed == 0
        assert r.alpha is None
        assert r.converged_round == 10
        assert r.total_rounds == 20
        assert r.loss_history == [1.0, 0.5]

    def test_alpha_can_be_float(self, tmp_path: Path) -> None:
        r = TrainingResult(
            regime=Regime.C,
            seed=1,
            alpha=0.5,
            converged_round=None,
            total_rounds=5,
            checkpoint_dir=tmp_path,
            score_dir=tmp_path,
            loss_history=[],
        )
        assert r.alpha == pytest.approx(0.5)
        assert r.converged_round is None

    def test_is_frozen(self, tmp_path: Path) -> None:
        r = self._make(tmp_path)
        with pytest.raises(Exception):
            r.seed = 99 # type: ignore[misc]


# ---------------------------------------------------------------------------
# load_scoring_data
# ---------------------------------------------------------------------------


def _client_data() -> ClientData:
    return ClientData(
        train=torch.zeros(2, 2),
        val=torch.zeros(2, 2),
        test_benign=torch.zeros(2, 2),
        test_attack=torch.zeros(2, 2),
    )


class TestLoadScoringData:
    def test_returns_client_data_when_no_prepared_dir(self) -> None:
        data = {"c0": _client_data()}
        result = load_scoring_data(data, None)
        assert result is data

    def test_raises_when_both_absent(self) -> None:
        with pytest.raises(ValueError, match="No scoring data source"):
            load_scoring_data(None, None)

    def test_raises_when_client_data_empty_and_no_prepared_dir(self) -> None:
        with pytest.raises(ValueError, match="No scoring data source"):
            load_scoring_data({}, None)

    def test_loads_from_prepared_dir_ignoring_client_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import datp.federated.simulation as sim_mod

        fake = {"c0": _client_data()}
        monkeypatch.setattr(sim_mod, "load_client_data", lambda *_a, **_kw: fake)

        result = load_scoring_data(None, tmp_path)
        assert result is fake

    def test_prepared_dir_wins_over_client_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import datp.federated.simulation as sim_mod

        from_disk = {"from_disk": _client_data()}
        monkeypatch.setattr(sim_mod, "load_client_data", lambda *_, **__: from_disk)

        in_memory = {"in_memory": _client_data()}
        result = load_scoring_data(in_memory, tmp_path)
        assert result is from_disk


# ---------------------------------------------------------------------------
# run_fl_simulation — client-data mutation guard
# ---------------------------------------------------------------------------


class TestClientDataNotMutated:
    """run_fl_simulation must not clear the caller's client_data dict."""

    def test_client_data_keys_preserved_when_prepared_dir_set(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import datp.federated.simulation as sim_mod

        sentinel: dict[str, object] = {"client_data_at_call": None}

        def fake_make_client_fn(
            client_data: dict[str, object],
            _client_ids: list[str],
            _cfg: object,
            _device: object,
            **_kwargs: object,
        ) -> object:
            sentinel["client_data_at_call"] = dict(client_data)
            raise RuntimeError("stop-early")

        mock_strategy = MagicMock()

        class _FakeCatalog:
            def __init__(self, **_kw: object) -> None:
                # no-op: catalog state provided as class attributes
                pass

            client_ids = ["client_0"]
            num_clients = 1

            def validate_prepared_splits(self) -> None:
                # no-op: no disk access needed in this test
                pass

        monkeypatch.setattr(sim_mod, "TrainingClientCatalog", _FakeCatalog)
        monkeypatch.setattr(sim_mod, "make_client_fn", fake_make_client_fn)
        monkeypatch.setattr(
            sim_mod,
            "validate_regime",
            lambda _cfg: Regime.A,
        )
        monkeypatch.setattr(
            sim_mod, "resolve_device", lambda _: torch.device(DeviceType.CPU)
        )
        monkeypatch.setattr(sim_mod, "set_seeds", lambda _: None)
        monkeypatch.setattr(
            sim_mod, "_init_model_and_params", lambda *_, **__: (None, None, None)
        )
        monkeypatch.setattr(
            sim_mod.DatpFedAvg, "from_config", lambda *_, **__: mock_strategy
        )

        original_data: dict[str, ClientData] = {"client_0": _client_data()}
        prepared_dir = tmp_path / "prepared"

        mock_cfg = MagicMock()
        mock_cfg.machine.require_cuda = False

        with pytest.raises(RuntimeError, match="stop-early"):
            sim_mod.run_fl_simulation(
                cfg=mock_cfg,
                client_data=original_data,
                seed=0,
                alpha=None,
                model_cls=None, # type: ignore[arg-type]
                ckpt_dir=tmp_path,
                score_base=tmp_path,
                label="test",
                prepared_dir=prepared_dir,
            )

        assert set(original_data.keys()) == {"client_0"}, (
            "client_data must not be mutated by run_fl_simulation"
        )


# ---------------------------------------------------------------------------
# _execute_flower_simulation — simulation call
# ---------------------------------------------------------------------------


class TestExecuteFlowerSimulation:
    """_execute_flower_simulation must call _run_simulation with correct num_supernodes."""

    def test_calls_run_simulation_with_num_clients(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import datp.federated.simulation as sim_mod
        from datp.config.compose import BASE_CONFIG

        monkeypatch.setattr(sim_mod, "configure_runtime_env", lambda: None)
        monkeypatch.setattr(sim_mod, "ensure_ray_memory_threshold", lambda _: None)
        monkeypatch.setattr(
            sim_mod,
            "derive_client_resources",
            lambda **_kw: {"num_cpus": 1.0, "num_gpus": 0.0},
        )

        called: dict[str, object] = {}

        def fake_run_simulation(**kwargs: object) -> None:
            called.update(kwargs)

        monkeypatch.setattr(sim_mod, "_run_simulation", fake_run_simulation)

        sim_mod._execute_flower_simulation(
            BASE_CONFIG,
            lambda _ctx: None, # type: ignore[arg-type]
            7,
            None,
            "test",
            BASE_CONFIG.federation.convergence.rounds_max,
        )

        assert called.get("num_supernodes") == 7

    def test_propagates_simulation_exception(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import datp.federated.simulation as sim_mod
        from datp.config.compose import BASE_CONFIG

        monkeypatch.setattr(sim_mod, "configure_runtime_env", lambda: None)
        monkeypatch.setattr(sim_mod, "ensure_ray_memory_threshold", lambda _: None)
        monkeypatch.setattr(
            sim_mod,
            "derive_client_resources",
            lambda **_kw: {"num_cpus": 1.0, "num_gpus": 0.0},
        )
        def boom(**_kw: object) -> None:
            raise RuntimeError("sim-boom")

        monkeypatch.setattr(sim_mod, "_run_simulation", boom)

        with pytest.raises(RuntimeError, match="sim-boom"):
            sim_mod._execute_flower_simulation(
                BASE_CONFIG,
                lambda _ctx: None, # type: ignore[arg-type]
                1,
                None,
                "test",
                BASE_CONFIG.federation.convergence.rounds_max,
            )
