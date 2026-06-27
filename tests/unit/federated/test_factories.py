"""Tests verifying model construction configurations and client factory initializers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import torch
from flwr.common import Context, RecordDict

from datp.core.enums import Activation, DeviceType
from datp.federated.factories import ClientFactoryConfig, build_model, make_client_fn
from datp.federated.types import ClientData


def _make_cfg() -> MagicMock:
    """Helper to build a mock config with preset model properties."""
    cfg = MagicMock()
    cfg.model.input_dim = 4
    cfg.model.encoder_dims = [3, 2]
    cfg.model.activation = Activation.RELU
    cfg.model.use_bn = False
    cfg.model.lr = 0.01
    cfg.federation.local_epochs = 1
    cfg.machine.batch_size_train = 8
    return cfg


def _make_client_data() -> dict[str, ClientData]:
    """Helper to generate a dictionary of client identifiers to ClientData."""
    return {
        "client_a": ClientData(
            train=torch.randn(16, 4),
            val=torch.randn(8, 4),
            test_benign=torch.randn(8, 4),
            test_attack=torch.randn(8, 4),
        ),
        "client_b": ClientData(
            train=torch.randn(16, 4),
            val=torch.randn(8, 4),
            test_benign=torch.randn(8, 4),
            test_attack=torch.randn(8, 4),
        ),
    }


def _make_context(partition_id: int) -> Context:
    """Helper to create a Flower Context for client instantiations."""
    return Context(
        run_id=0,
        node_id=0,
        node_config={"partition-id": str(partition_id)},
        state=RecordDict(),
        run_config={},
    )


class TestBuildModel:
    """Tests verifying build_model parser mapping and property validation."""

    def test_returns_autoencoder(self) -> None:
        """Verify that build_model returns an Autoencoder network by default."""
        cfg = _make_cfg()
        model = build_model(cfg)
        assert model is not None
        assert hasattr(model, "encoder")
        assert hasattr(model, "decoder")

    def test_respects_input_dim(self) -> None:
        """Verify that the model first layer input size matches config input_dim."""
        cfg = _make_cfg()
        model = build_model(cfg)

        first_linear = model.encoder[0]
        assert first_linear.in_features == 4

    def test_respects_hidden_dims(self) -> None:
        """Verify that the number of hidden encoder layers matches config hidden dimensions."""
        cfg = _make_cfg()
        cfg.model.encoder_dims = [8, 4]
        model = build_model(cfg)

        linear_layers = [m for m in model.encoder if isinstance(m, torch.nn.Linear)]
        assert len(linear_layers) >= 2

    def test_respects_activation(self) -> None:
        """Verify that the model uses the activation function specified in config."""
        cfg = _make_cfg()
        cfg.model.activation = Activation.TANH
        model = build_model(cfg)
        activations = [m for m in model.encoder if isinstance(m, torch.nn.Tanh)]
        assert len(activations) >= 1

    def test_respects_use_bn(self) -> None:
        """Verify that batch normalization layers are added when enabled in config."""
        cfg = _make_cfg()
        cfg.model.use_bn = True
        model = build_model(cfg)
        bn_layers = [m for m in model.encoder if isinstance(m, torch.nn.BatchNorm1d)]
        assert len(bn_layers) >= 1

    def test_no_bn_when_disabled(self) -> None:
        """Verify that batch normalization layers are absent when disabled in config."""
        cfg = _make_cfg()
        cfg.model.use_bn = False
        model = build_model(cfg)
        bn_layers = [m for m in model.encoder if isinstance(m, torch.nn.BatchNorm1d)]
        assert len(bn_layers) == 0

    def test_custom_model_cls(self) -> None:
        """Verify that build_model can initialize custom network classes."""
        from datp.modeling.autoencoder import Autoencoder

        cfg = _make_cfg()
        model = build_model(cfg, model_cls=Autoencoder)
        assert isinstance(model, Autoencoder)


class TestMakeClientFn:
    """Tests verifying client function generation in memory-only mode."""

    def test_returns_callable(self) -> None:
        """Verify that make_client_fn returns a callable client generator."""
        cfg = _make_cfg()
        client_data = _make_client_data()
        client_ids = sorted(client_data.keys())
        fn = make_client_fn(
            client_data,
            ClientFactoryConfig(
                client_ids=client_ids, cfg=cfg, device=torch.device(DeviceType.CPU)
            ),
        )
        assert callable(fn)

    def test_default_client_cls(self) -> None:
        """Verify that invoking the generated function returns a client instance."""
        cfg = _make_cfg()
        client_data = _make_client_data()
        client_ids = sorted(client_data.keys())
        fn = make_client_fn(
            client_data,
            ClientFactoryConfig(
                client_ids=client_ids, cfg=cfg, device=torch.device(DeviceType.CPU)
            ),
        )
        client = fn(_make_context(0))
        assert client is not None

    def test_partition_id_maps_to_correct_client(self) -> None:
        """Verify partition IDs map to correct client indices."""
        cfg = _make_cfg()
        client_data = _make_client_data()
        client_ids = sorted(client_data.keys())

        fn = make_client_fn(
            client_data,
            ClientFactoryConfig(
                client_ids=client_ids, cfg=cfg, device=torch.device(DeviceType.CPU)
            ),
        )

        fn(_make_context(0))
        fn(_make_context(1))


class TestMakeClientFnPreparedDir:
    """Tests verifying client function generation from disk directory."""

    def test_uses_discover_and_load(self, tmp_path: Path) -> None:
        """Verify client factory loads data from disk when prepared_dir is set."""
        cfg = _make_cfg()
        client_ids = ["client_a", "client_b"]
        client_data: dict[str, ClientData] = {}

        for cid in client_ids:
            d = tmp_path / cid
            d.mkdir()

        train_t = torch.randn(8, 4)
        cal_t = torch.randn(4, 4)

        with (
            patch(
                "datp.federated.factories.load_single_client_training_data",
                return_value=(train_t, cal_t),
            ),
            patch(
                "datp.federated.factories.discover_client_dirs",
                return_value=[tmp_path / cid for cid in client_ids],
            ),
        ):
            fn = make_client_fn(
                client_data,
                ClientFactoryConfig(
                    client_ids=client_ids,
                    cfg=cfg,
                    device=torch.device(DeviceType.CPU),
                    prepared_dir=tmp_path,
                ),
            )
            client = fn(_make_context(0))
            assert client is not None


class TestPreparedDirUpfrontValidation:
    """Tests verifying client folder existence checks on initialization."""

    def test_missing_client_dir_raises_upfront(self, tmp_path: Path) -> None:
        """Ensure upfront configuration check raises FileNotFoundError if directories are missing."""
        cfg = _make_cfg()
        client_ids = ["client_a", "client_b", "client_missing"]
        client_data: dict[str, ClientData] = {}

        import pytest

        with patch(
            "datp.federated.factories.discover_client_dirs",
            return_value=[tmp_path / "client_a", tmp_path / "client_b"],
        ):
            with pytest.raises(
                FileNotFoundError, match="Prepared directories missing"
            ) as exc_info:
                make_client_fn(
                    client_data,
                    ClientFactoryConfig(
                        client_ids=client_ids,
                        cfg=cfg,
                        device=torch.device(DeviceType.CPU),
                        prepared_dir=tmp_path,
                    ),
                )
            assert "client_missing" in str(exc_info.value)

    def test_all_client_dirs_present_returns_callable(self, tmp_path: Path) -> None:
        """Ensure call passes if all client directories exist in prepared_dir."""
        cfg = _make_cfg()
        client_ids = ["client_a", "client_b"]
        client_data: dict[str, ClientData] = {}

        with patch(
            "datp.federated.factories.discover_client_dirs",
            return_value=[tmp_path / cid for cid in client_ids],
        ):
            fn = make_client_fn(
                client_data,
                ClientFactoryConfig(
                    client_ids=client_ids,
                    cfg=cfg,
                    device=torch.device(DeviceType.CPU),
                    prepared_dir=tmp_path,
                ),
            )
            assert callable(fn)


class TestWorkerSideSeeding:
    """Tests verifying worker-side determinism seeding configuration."""

    def test_seed_param_calls_set_seeds(self) -> None:
        """Verify worker seeds are set and offset by partition index."""
        cfg = _make_cfg()
        client_data = _make_client_data()
        client_ids = sorted(client_data.keys())

        with patch("datp.federated.factories.set_seeds") as mock_seeds:
            fn = make_client_fn(
                client_data,
                ClientFactoryConfig(
                    client_ids=client_ids,
                    cfg=cfg,
                    device=torch.device(DeviceType.CPU),
                    seed=42,
                ),
            )
            fn(_make_context(0))
            fn(_make_context(1))

        assert mock_seeds.call_count == 2

        assert mock_seeds.call_args_list[0].args == (42,)
        assert mock_seeds.call_args_list[1].args == (43,)

    def test_no_seed_skips_set_seeds(self) -> None:
        """Verify that set_seeds is not called if seed config parameter is missing."""
        cfg = _make_cfg()
        client_data = _make_client_data()
        client_ids = sorted(client_data.keys())

        with patch("datp.federated.factories.set_seeds") as mock_seeds:
            fn = make_client_fn(
                client_data,
                ClientFactoryConfig(
                    client_ids=client_ids, cfg=cfg, device=torch.device(DeviceType.CPU)
                ),
            )
            fn(_make_context(0))

        mock_seeds.assert_not_called()

    def test_seed_param_in_prepared_dir_path(self, tmp_path: Path) -> None:
        """Verify worker seed offset logic in prepared directory mode."""
        cfg = _make_cfg()
        client_ids = ["client_a", "client_b"]
        client_data: dict[str, ClientData] = {}
        train_t = torch.randn(8, 4)
        cal_t = torch.randn(4, 4)

        with (
            patch(
                "datp.federated.factories.discover_client_dirs",
                return_value=[tmp_path / cid for cid in client_ids],
            ),
            patch(
                "datp.federated.factories.load_single_client_training_data",
                return_value=(train_t, cal_t),
            ),
            patch("datp.federated.factories.set_seeds") as mock_seeds,
        ):
            fn = make_client_fn(
                client_data,
                ClientFactoryConfig(
                    client_ids=client_ids,
                    cfg=cfg,
                    device=torch.device(DeviceType.CPU),
                    prepared_dir=tmp_path,
                    seed=7,
                ),
            )
            fn(_make_context(1))

        mock_seeds.assert_called_once_with(7 ^ 1)
