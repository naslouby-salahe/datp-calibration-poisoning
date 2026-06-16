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
    from flwr.client import NumPyClient
    from flwr.common import Context, ndarrays_to_parameters
    from flwr.server import ServerConfig
    from flwr.server.strategy import FedAvg
    from flwr.simulation import start_simulation

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

        def get_parameters(self, config):
            return _get_params(self.model)

        def fit(self, parameters, config):
            _set_params(self.model, parameters)
            optimizer = torch.optim.SGD(self.model.parameters(), lr=0.01)
            self.model.train()
            for _ in range(1):
                pred = self.model(self.data)
                loss = nn.functional.mse_loss(pred, self.data)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            return _get_params(self.model), len(self.data), {}

        def evaluate(self, parameters, config):
            _set_params(self.model, parameters)
            self.model.eval()
            with torch.no_grad():
                pred = self.model(self.data)
                loss = nn.functional.mse_loss(pred, self.data).item()
            return float(loss), len(self.data), {"loss": float(loss)}

    def client_fn(context: Context):
        cid = str(context.node_config["partition-id"])
        return _SmokeClient(cid).to_client()

    init_model = _SmokeAE()
    initial_params = _get_params(init_model)

    strategy = FedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=_SMOKE_NUM_CLIENTS,
        min_evaluate_clients=_SMOKE_NUM_CLIENTS,
        min_available_clients=_SMOKE_NUM_CLIENTS,
        initial_parameters=ndarrays_to_parameters(initial_params),
    )

    history = start_simulation(
        client_fn=client_fn,
        num_clients=_SMOKE_NUM_CLIENTS,
        config=ServerConfig(num_rounds=_SMOKE_NUM_ROUNDS),
        strategy=strategy,
        ray_init_args={"num_cpus": 2, "include_dashboard": False},
    )

    assert len(history.losses_distributed) == _SMOKE_NUM_ROUNDS, (
        f"Expected {_SMOKE_NUM_ROUNDS} rounds of distributed losses, "
        f"got {len(history.losses_distributed)}"
    )

    for rnd, loss in history.losses_distributed:
        assert math.isfinite(loss), (
            f"Round {rnd}: distributed loss is not finite ({loss})"
        )

    for rnd, loss in history.losses_centralized:
        assert math.isfinite(loss), (
            f"Round {rnd}: centralized loss is not finite ({loss})"
        )
