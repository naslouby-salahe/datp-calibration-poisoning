from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from datp.checkpointing.enums import CheckpointConvergenceMode
from datp.config.compose import BASE_CONFIG
from datp.federated.convergence import ConvergenceMonitor
from datp.federated.strategies import DatpFedAvg, FedAvgConfig


def test_convergence_log_only_does_not_stop_training() -> None:
    monitor = ConvergenceMonitor(
        rounds_initial=1,
        rounds_max=10,
        relative_threshold=0.05,
        window=2,
    )
    for round_id in range(1, 5):
        monitor.record(round_id, 1.0)

    should_stop = monitor.should_stop(4, stop_on_convergence=False)

    assert should_stop is False
    assert monitor.converged_round == 4


def test_strategy_log_only_mode_does_not_enter_stopped_state() -> None:
    from flwr.common import ndarrays_to_parameters

    monitor = ConvergenceMonitor(
        rounds_initial=1,
        rounds_max=10,
        relative_threshold=0.05,
        window=2,
    )
    strategy = DatpFedAvg(
        FedAvgConfig(
            convergence_monitor=monitor,
            round_timeout_s=300.0,
            fraction_fit=1.0,
            fraction_evaluate=1.0,
            min_fit_clients=1,
            min_evaluate_clients=1,
            min_available_clients=1,
            initial_parameters=ndarrays_to_parameters(
                [np.zeros((2, 2), dtype=np.float32)]
            ),
            convergence_mode=CheckpointConvergenceMode.LOG_ONLY,
        )
    )
    proxy = MagicMock()
    result = MagicMock()
    result.num_examples = 10
    result.loss = 1.0
    for round_id in range(1, 4):
        monitor.record(round_id, 1.0)

    strategy.aggregate_evaluate(4, [(proxy, result)], [])

    assert monitor.converged_round == 4
    assert strategy.stopped is False


def test_checkpoint_save_schedule_k_are_fixed() -> None:
    import pytest

    if BASE_CONFIG.checkpoint_protocol is None:
        pytest.skip("checkpoint protocol not configured in base YAML")
    assert BASE_CONFIG.checkpoint_protocol.milestones == (
        25,
        50,
        75,
        100,
        125,
        150,
        200,
    )
    assert BASE_CONFIG.checkpoint_protocol.max_rounds == 200
    assert (
        BASE_CONFIG.checkpoint_protocol.convergence_mode
        == CheckpointConvergenceMode.LOG_ONLY
    )
    assert BASE_CONFIG.threshold.cluster_k_nbaiot == 3


def test_canonical_nbaiot_cluster_is_fixed_k3() -> None:
    assert BASE_CONFIG.threshold.cluster_k_nbaiot == 3
