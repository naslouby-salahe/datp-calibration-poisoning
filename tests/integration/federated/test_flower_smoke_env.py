import math

import numpy as np
import pytest
import torch
import torch.nn as nn

from datp.core.seeds import set_seeds

_SMOKE_INPUT_DIM = 8
_SMOKE_HIDDEN_DIM = 4
_SMOKE_N_SAMPLES = 200 # per client
_SMOKE_NUM_CLIENTS = 2
_SMOKE_NUM_ROUNDS = 2
_SMOKE_SEED = 42


@pytest.mark.integration
def test_two_client_flower_simulation() -> None:
    from typing import Any

    from flwr.client import ClientApp, NumPyClient
    from flwr.common import Context, ndarrays_to_parameters
    from flwr.common.telemetry import EventType
    from flwr.server import ServerApp, ServerConfig
    from flwr.server.serverapp_components import ServerAppComponents
    from flwr.server.strategy import FedAvg
    from flwr.simulation.run_simulation import _run_simulation

    set_seeds(_SMOKE_SEED)

    # Minimal test-only AE — defined inside the test so Ray workers don't need to import the test
    # module when deserializing pickled closures.
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

    assert len(strategy.round_losses) == _SMOKE_NUM_ROUNDS, (
        f"Expected {_SMOKE_NUM_ROUNDS} rounds of distributed losses, "
        f"got {len(strategy.round_losses)}"
    )

    for rnd, loss in strategy.round_losses:
        assert math.isfinite(loss), (
            f"Round {rnd}: distributed loss is not finite ({loss})"
        )
