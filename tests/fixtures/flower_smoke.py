"""Flower simulation smoke test helper."""

from __future__ import annotations

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

from datp.core.seeds import set_seeds

SMOKE_INPUT_DIM = 8
SMOKE_HIDDEN_DIM = 4
SMOKE_N_SAMPLES = 200
SMOKE_NUM_CLIENTS = 2
SMOKE_NUM_ROUNDS = 2


class SmokeAE(nn.Module):
    """Simple fully connected Autoencoder model for smoke tests."""

    def __init__(self) -> None:
        """Initialize the Autoencoder layers."""
        super().__init__()
        self.encoder = nn.Linear(SMOKE_INPUT_DIM, SMOKE_HIDDEN_DIM)
        self.decoder = nn.Linear(SMOKE_HIDDEN_DIM, SMOKE_INPUT_DIM)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Perform forward pass of the Autoencoder."""
        return self.decoder(torch.relu(self.encoder(x)))


def get_params(model: nn.Module) -> list[np.ndarray]:
    """Extract parameter weights from the model as numpy arrays."""
    return [p.detach().cpu().numpy() for p in model.parameters()]


def set_params(model: nn.Module, params: list[np.ndarray]) -> None:
    """Assign numpy weights back to the PyTorch model."""
    with torch.no_grad():
        for p, arr in zip(model.parameters(), params):
            p.copy_(torch.from_numpy(arr))


class TrackingFedAvg(FedAvg):
    """FedAvg strategy that keeps track of the aggregated round evaluation loss."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize TrackingFedAvg with list of round losses."""
        super().__init__(**kwargs)
        self.round_losses: list[tuple[int, float]] = []

    def aggregate_evaluate(self, server_round: int, results: Any, failures: Any) -> Any:
        """Record the aggregated round validation loss in history."""
        aggregated = super().aggregate_evaluate(server_round, results, failures)
        if aggregated[0] is not None:
            self.round_losses.append((server_round, aggregated[0]))
        return aggregated


def run_flower_smoke(seed: int | None) -> list[tuple[int, float]]:
    """Execute a minimal Flower simulation using client and server functions."""
    if seed is not None:
        set_seeds(seed)

    client_data = {
        str(i): torch.randn(SMOKE_N_SAMPLES, SMOKE_INPUT_DIM)
        for i in range(SMOKE_NUM_CLIENTS)
    }

    class SmokeClient(NumPyClient):
        """Mock NumPyClient representing a client in the smoke simulation."""

        def __init__(self, cid: str) -> None:
            """Initialize SmokeClient with client ID and data."""
            self.model = SmokeAE()
            self.data = client_data[cid]

        def get_parameters(self, config: Any) -> list[np.ndarray]:
            """Retrieve the current model parameter weights."""
            return get_params(self.model)

        def fit(
            self, parameters: list[np.ndarray], config: Any
        ) -> tuple[list[np.ndarray], int, dict[str, Any]]:
            """Train the local model on the client's dataset."""
            set_params(self.model, parameters)
            optimizer = torch.optim.SGD(
                self.model.parameters(), lr=0.01, momentum=0.0, weight_decay=0.0
            )
            self.model.train()
            pred = self.model(self.data)
            loss = nn.functional.mse_loss(pred, self.data)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            return get_params(self.model), len(self.data), {}

        def evaluate(
            self, parameters: list[np.ndarray], config: Any
        ) -> tuple[float, int, dict[str, Any]]:
            """Evaluate the local model on the client's dataset."""
            set_params(self.model, parameters)
            self.model.eval()
            with torch.no_grad():
                pred = self.model(self.data)
                loss = nn.functional.mse_loss(pred, self.data).item()
            return float(loss), len(self.data), {"loss": float(loss)}

    def client_fn(context: Context) -> Any:
        """Create a client instance for the simulation."""
        cid = str(context.node_config["partition-id"])
        return SmokeClient(cid).to_client()

    strategy = TrackingFedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=SMOKE_NUM_CLIENTS,
        min_evaluate_clients=SMOKE_NUM_CLIENTS,
        min_available_clients=SMOKE_NUM_CLIENTS,
        initial_parameters=ndarrays_to_parameters(get_params(SmokeAE())),
    )

    def server_fn(_: Context) -> ServerAppComponents:
        """Configure the federated server strategy and rounds."""
        return ServerAppComponents(
            strategy=strategy,
            config=ServerConfig(num_rounds=SMOKE_NUM_ROUNDS),
        )

    _run_simulation(
        num_supernodes=SMOKE_NUM_CLIENTS,
        client_app=ClientApp(client_fn=client_fn),
        server_app=ServerApp(server_fn=server_fn),
        backend_config={"init_args": {"num_cpus": 2, "include_dashboard": False}},
        exit_event=EventType.PYTHON_API_RUN_SIMULATION_LEAVE,
    )
    return strategy.round_losses
