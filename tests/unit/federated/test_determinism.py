from __future__ import annotations

from pathlib import Path

import pytest

# Synthetic / test-only constants — identical to the smoke test (T0-7).
_SMOKE_INPUT_DIM = 8
_SMOKE_HIDDEN_DIM = 4
_SMOKE_N_SAMPLES = 200
_SMOKE_NUM_CLIENTS = 2
_SMOKE_NUM_ROUNDS = 2


def _run_experiment(seed: int | None, run_dir: Path) -> Path:
    from typing import Any

    import numpy as np
    import torch
    import torch.nn as nn
    from flwr.client import ClientApp, NumPyClient
    from flwr.common import Context, ndarrays_to_parameters
    from flwr.common.telemetry import EventType
    from flwr.server import ServerApp, ServerConfig
    from flwr.server.serverapp_components import ServerAppComponents
    from flwr.server.strategy import FedAvg
    from flwr.simulation.run_simulation import _run_simulation

    from datp.artifacts.io import write_metrics_atomic
    from datp.core.seeds import set_seeds

    if seed is not None:
        set_seeds(seed)

    # Minimal test-only AE — defined inside the function so Ray workers
    # can pickle the closure without importing the test module.
    class _SmokeAE(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.encoder = nn.Linear(_SMOKE_INPUT_DIM, _SMOKE_HIDDEN_DIM)
            self.decoder = nn.Linear(_SMOKE_HIDDEN_DIM, _SMOKE_INPUT_DIM)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.decoder(torch.relu(self.encoder(x)))

    def _get_params(model: nn.Module) -> list[np.ndarray]:
        return [p.detach().cpu().numpy() for p in model.parameters()]

    def _set_params(model: nn.Module, params: list[np.ndarray]) -> None:
        with torch.no_grad():
            for p, arr in zip(model.parameters(), params):
                p.copy_(torch.from_numpy(arr))

    client_data = {
        str(i): torch.randn(_SMOKE_N_SAMPLES, _SMOKE_INPUT_DIM)
        for i in range(_SMOKE_NUM_CLIENTS)
    }

    class _SmokeClient(NumPyClient):
        def __init__(self, cid: str) -> None:
            self.cid = cid
            self.model = _SmokeAE()
            self.data = client_data[cid]

        def get_parameters(self, config: Any) -> list[np.ndarray]:
            return _get_params(self.model)

        def fit(self, parameters: list[np.ndarray], config: Any) -> tuple[list[np.ndarray], int, dict[str, Any]]:
            _set_params(self.model, parameters)
            optimizer = torch.optim.SGD(self.model.parameters(), lr=0.01, momentum=0.0, weight_decay=0.0)
            self.model.train()
            for _ in range(1):
                pred = self.model(self.data)
                loss = nn.functional.mse_loss(pred, self.data)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            return _get_params(self.model), len(self.data), {}

        def evaluate(self, parameters: list[np.ndarray], config: Any) -> tuple[float, int, dict[str, Any]]:
            _set_params(self.model, parameters)
            self.model.eval()
            with torch.no_grad():
                pred = self.model(self.data)
                loss = nn.functional.mse_loss(pred, self.data).item()
            return float(loss), len(self.data), {"loss": float(loss)}

    def client_fn(context: Context) -> Any:
        cid = str(context.node_config["partition-id"])
        return _SmokeClient(cid).to_client()

    init_model = _SmokeAE()
    initial_params = _get_params(init_model)

    class _TrackingFedAvg(FedAvg):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.round_losses: list[tuple[int, float]] = []

        def aggregate_evaluate(self, server_round: int, results: Any, failures: Any) -> Any:
            aggregated = super().aggregate_evaluate(server_round, results, failures)
            if aggregated[0] is not None:
                self.round_losses.append((server_round, aggregated[0]))
            return aggregated

    strategy = _TrackingFedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=_SMOKE_NUM_CLIENTS,
        min_evaluate_clients=_SMOKE_NUM_CLIENTS,
        min_available_clients=_SMOKE_NUM_CLIENTS,
        initial_parameters=ndarrays_to_parameters(initial_params),
    )

    def server_fn(_: Context) -> ServerAppComponents:
        return ServerAppComponents(
            strategy=strategy,
            config=ServerConfig(num_rounds=_SMOKE_NUM_ROUNDS),
        )

    _run_simulation(
        num_supernodes=_SMOKE_NUM_CLIENTS,
        client_app=ClientApp(client_fn=client_fn),
        server_app=ServerApp(server_fn=server_fn),
        backend_config={"init_args": {"num_cpus": 2, "include_dashboard": False}}, # type: ignore[arg-type]
        exit_event=EventType.PYTHON_API_RUN_SIMULATION_LEAVE,
    )

    metrics = {
        "losses_distributed": [
            {"round": rnd, "loss": loss}
            for rnd, loss in strategy.round_losses
        ],
    }

    return write_metrics_atomic(run_dir, metrics)


@pytest.mark.integration
def test_determinism_same_seed_identical_metrics(tmp_path: Path) -> None:
    dir_a = tmp_path / "run_a"
    path_a = _run_experiment(seed=42, run_dir=dir_a)


    dir_b = tmp_path / "run_b"
    path_b = _run_experiment(seed=42, run_dir=dir_b)


    bytes_a = path_a.read_bytes()
    bytes_b = path_b.read_bytes()
    assert bytes_a == bytes_b, (
        "metrics.json files differ between two runs with the same seed.\n"
        f"Run A:\n{bytes_a.decode()}\n"
        f"Run B:\n{bytes_b.decode()}"
    )


@pytest.mark.integration
def test_determinism_guard_no_seeds_differ(tmp_path: Path) -> None:
    dir_a = tmp_path / "run_a"
    path_a = _run_experiment(seed=42, run_dir=dir_a)


    dir_b = tmp_path / "run_b"
    path_b = _run_experiment(seed=99, run_dir=dir_b)


    bytes_a = path_a.read_bytes()
    bytes_b = path_b.read_bytes()
    assert bytes_a != bytes_b, (
        "metrics.json files are identical despite different seeds — "
        "the determinism test is not sensitive to seed state."
    )
