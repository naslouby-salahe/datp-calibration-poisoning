from __future__ import annotations

import pytest

from datp.federated.convergence import ConvergenceMonitor


def _feed(monitor: ConvergenceMonitor, losses: list[float]) -> int | None:
    for r, loss in enumerate(losses, start=1):
        monitor.record(r, loss)
        if monitor.should_stop(r):
            return r
    return None


class TestConvergenceTrigger:
    def test_convergence_triggers_at_expected_round(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=100,
            relative_threshold=0.03,
            window=4,
        )
        # Need 2*window=8 losses before evaluation starts
        losses = [1.0, 0.8, 0.6, 0.5, 0.4, 0.35, 0.32, 0.30]
        losses += [0.30] * 10

        stop_round = _feed(monitor, losses)

        assert stop_round is not None
        assert stop_round >= 5
        assert stop_round >= 2 * 4 # 2*window
        assert monitor.converged_round == stop_round

    def test_gradual_convergence(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=10,
            rounds_max=200,
            relative_threshold=0.05,
            window=5,
        )
        losses = [1.0 * (0.95**i) for i in range(30)]
        losses += [losses[-1]] * 20

        stop_round = _feed(monitor, losses)

        assert stop_round is not None
        assert stop_round >= 10
        assert stop_round >= 2 * 5 # 2*window

    def test_window_mean_comparison_differs_from_first_last(self) -> None:
        """The old first-vs-last behavior would give different answers from window-mean."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=100,
            relative_threshold=0.02,
            window=4,
        )
        # Sequence where first==last in window but means differ:
        # previous window [1.0, 0.9, 0.8, 0.7] mean=0.85
        # current window [0.7, 0.8, 0.7, 0.7] mean=0.725
        # rel_change = |0.725 - 0.85| / 0.85 = 0.147 > 0.02 => no convergence
        # But old method: start=0.7 end=0.7 => rel_change=0 => would converge (wrong!)
        losses = [1.0, 0.9, 0.8, 0.7, 0.7, 0.8, 0.7, 0.7]
        stop_round = _feed(monitor, losses)
        # With new method, this should NOT converge (rel_change ~0.147 > 0.02)
        assert stop_round is None

    def test_flat_sequence_converges_with_mean_comparison(self) -> None:
        """A truly flat sequence converges regardless of method."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=100,
            relative_threshold=0.02,
            window=4,
        )
        # Both windows will have mean=0.5, so rel_change=0
        losses = [0.5] * 8
        stop_round = _feed(monitor, losses)
        assert stop_round == 8 # fires at exactly 2*window


class TestRoundsInitialGuard:
    def test_convergence_does_not_fire_before_rounds_initial(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=20,
            rounds_max=100,
            relative_threshold=0.05,
            window=4,
        )
        flat_losses = [0.5] * 19

        for r, loss in enumerate(flat_losses, start=1):
            monitor.record(r, loss)
            assert not monitor.should_stop(r), (
                f"should_stop fired at round {r}, before rounds_initial=20"
            )

        monitor.record(20, 0.5)
        assert monitor.should_stop(20)


class TestHardCap:
    def test_convergence_hard_cap_at_rounds_max(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=10,
            relative_threshold=0.001,
            window=4,
        )
        losses = [1.0 - 0.05 * i for i in range(10)]

        stop_round = _feed(monitor, losses)

        assert stop_round == 10, f"Expected hard cap at round 10, got {stop_round}"

    def test_hard_cap_does_not_require_recorded_losses(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=10,
            relative_threshold=0.03,
            window=4,
        )
        assert monitor.should_stop(10)


class TestInsufficientHistory:
    def test_convergence_does_not_fire_without_2x_window(self) -> None:
        """Requires 2*window losses before convergence can be evaluated."""
        window = 4
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=100,
            relative_threshold=0.05,
            window=window,
        )
        # Feed 2*window - 1 = 7 flat losses: should not converge
        for r in range(1, 2 * window):
            monitor.record(r, 0.5)
            assert not monitor.should_stop(r), (
                f"should_stop fired with only {r} recorded losses "
                f"(need 2*window={2 * window})"
            )

        # At exactly 2*window with flat data, should converge
        monitor.record(2 * window, 0.5)
        assert monitor.should_stop(2 * window)


class TestFiniteLossValidation:
    def test_nan_loss_raises(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=100,
            relative_threshold=0.03,
            window=4,
        )
        with pytest.raises(ValueError, match="Non-finite loss"):
            monitor.record(1, float("nan"))

    def test_inf_loss_raises(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=100,
            relative_threshold=0.03,
            window=4,
        )
        with pytest.raises(ValueError, match="Non-finite loss"):
            monitor.record(1, float("inf"))

    def test_negative_inf_loss_raises(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=100,
            relative_threshold=0.03,
            window=4,
        )
        with pytest.raises(ValueError, match="Non-finite loss"):
            monitor.record(1, float("-inf"))


class TestFromConfig:
    def test_from_config(self) -> None:
        from datp.config.compose import BASE_CONFIG
        from datp.config.models import ConvergenceConfig, FederationConfig

        cfg = BASE_CONFIG.model_copy(
            update={
                "federation": FederationConfig(
                    local_epochs=5,
                    convergence=ConvergenceConfig(
                        rounds_initial=40,
                        rounds_max=150,
                        relative_threshold=0.005,
                        window=10,
                        round_timeout_s=300,
                    ),
                ),
            }
        )
        monitor = ConvergenceMonitor.from_config(cfg)

        # Behavioral verification: rounds_initial=40, window=10, threshold=0.005
        # With flat losses, convergence should not fire before round 40
        for r in range(1, 40):
            monitor.record(r, 0.5)
            assert not monitor.should_stop(r), f"should_stop fired at round {r} < rounds_initial=40"
        # At round 40 with 39 flat losses recorded (need 2*window=20), should converge
        monitor.record(40, 0.5)
        assert monitor.should_stop(40)
        assert monitor.converged_round == 40

    def test_from_config_missing_key_raises(self) -> None:
        with pytest.raises(AttributeError):
            ConvergenceMonitor.from_config({"federation": {}}) # type: ignore[arg-type]


class TestBaseConfigDefaults:
    def test_base_config_relative_threshold_is_0005(self) -> None:
        from datp.config.compose import BASE_CONFIG

        assert BASE_CONFIG.federation.convergence.relative_threshold == pytest.approx(0.005)

    def test_base_config_window_is_10(self) -> None:
        from datp.config.compose import BASE_CONFIG

        assert BASE_CONFIG.federation.convergence.window == 10

    def test_base_config_rounds_initial_is_40(self) -> None:
        from datp.config.compose import BASE_CONFIG

        assert BASE_CONFIG.federation.convergence.rounds_initial == 40

    def test_base_config_rounds_max_is_150(self) -> None:
        from datp.config.compose import BASE_CONFIG

        assert BASE_CONFIG.federation.convergence.rounds_max == 150


class TestValidationErrors:
    def test_rounds_initial_below_one(self) -> None:
        with pytest.raises(ValueError, match=r"rounds_initial must be >= 1"):
            ConvergenceMonitor(
                rounds_initial=0,
                rounds_max=10,
                relative_threshold=0.03,
                window=4,
            )

    def test_rounds_max_below_rounds_initial(self) -> None:
        with pytest.raises(ValueError, match=r"rounds_max must be >= rounds_initial"):
            ConvergenceMonitor(
                rounds_initial=20,
                rounds_max=10,
                relative_threshold=0.03,
                window=4,
            )

    def test_window_below_two(self) -> None:
        with pytest.raises(ValueError, match=r"window must be >= 2"):
            ConvergenceMonitor(
                rounds_initial=5,
                rounds_max=50,
                relative_threshold=0.03,
                window=1,
            )

    def test_error_messages_include_module_prefix(self) -> None:
        with pytest.raises(ValueError, match=r"\[federated\.convergence\]"):
            ConvergenceMonitor(
                rounds_initial=-1,
                rounds_max=10,
                relative_threshold=0.03,
                window=4,
            )


class TestConvergedRoundLogged:
    def test_converged_round_logged(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=100,
            relative_threshold=0.05,
            window=2,
        )
        for r in range(1, 4):
            monitor.record(r, 0.5)
            monitor.should_stop(r)

        assert monitor.converged_round is None

        monitor.record(4, 0.5)
        assert monitor.should_stop(4)
        assert monitor.converged_round == 4

    def test_converged_round_none_before_convergence(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=10,
            rounds_max=100,
            relative_threshold=0.001,
            window=4,
        )
        monitor.record(1, 1.0)
        monitor.record(2, 0.5)
        monitor.should_stop(2)

        assert monitor.converged_round is None

    def test_first_converged_round_is_preserved(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=100,
            relative_threshold=0.05,
            window=2,
        )
        for r in range(1, 5):
            monitor.record(r, 0.5)

        assert monitor.should_stop(4)
        assert monitor.converged_round == 4

        monitor.record(5, 0.5)
        assert monitor.should_stop(5)
        assert monitor.converged_round == 4


class TestPreweightedScalar:
    def test_monitor_accepts_preweighted_scalar(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.05,
            window=4,
        )
        # Need 2*window=8 losses; last 4 vs previous 4 must show <5% relative change
        preweighted = [0.123, 0.119, 0.115, 0.114, 0.114, 0.114, 0.114, 0.114]

        for r, loss in enumerate(preweighted, start=1):
            monitor.record(r, loss)

        assert monitor.num_recorded == len(preweighted)
        assert monitor.should_stop(len(preweighted))

    def test_num_recorded_tracks_calls(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=50,
            relative_threshold=0.03,
            window=4,
        )
        assert monitor.num_recorded == 0
        monitor.record(1, 0.5)
        assert monitor.num_recorded == 1
        monitor.record(2, 0.4)
        assert monitor.num_recorded == 2


class TestEdgeCases:
    def test_near_zero_loss_converges(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.05,
            window=4,
        )
        # Need 2*window=8 losses for evaluation
        losses = [1e-15] * 8
        stop_round = _feed(monitor, losses)
        assert stop_round is not None

    def test_window_odd_size(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.05,
            window=5,
        )
        # Need 2*window=10 losses for evaluation
        losses = [0.5] * 10
        stop_round = _feed(monitor, losses)
        assert stop_round is not None


class TestConvergenceAlgorithm:
    """Tests for the window-mean comparison algorithm.

    The algorithm compares mean(losses[-(2*window):-window]) vs mean(losses[-window:]).
    Requires 2*window losses before evaluation.
    """

    def test_no_convergence_with_diverging_windows(self) -> None:
        """If previous window mean differs significantly from current, no convergence."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.05,
            window=4,
        )
        # Previous window: [1.0, 0.9, 0.8, 0.7] → mean=0.85
        # Current window: [0.3, 0.3, 0.3, 0.3] → mean=0.3
        # rel_change = |0.3-0.85|/0.85 ≈ 0.647 > 0.05
        losses = [1.0, 0.9, 0.8, 0.7, 0.3, 0.3, 0.3, 0.3]
        for r, loss in enumerate(losses, start=1):
            monitor.record(r, loss)
        assert not monitor.should_stop(8)

    def test_converges_when_windows_similar(self) -> None:
        """Convergence fires when previous and current window means are close."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.05,
            window=4,
        )
        # Previous window: [0.50, 0.50, 0.50, 0.50] → mean=0.50
        # Current window: [0.49, 0.49, 0.49, 0.49] → mean=0.49
        # rel_change = |0.49-0.50|/0.50 = 0.02 < 0.05
        losses = [0.50, 0.50, 0.50, 0.50, 0.49, 0.49, 0.49, 0.49]
        for r, loss in enumerate(losses, start=1):
            monitor.record(r, loss)
        assert monitor.should_stop(8)

    def test_latest_relative_change_tracks_window_means(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.50,
            window=4,
        )
        # Previous window: [2.0, 2.0, 2.0, 2.0] → mean=2.0
        # Current window: [1.8, 1.8, 1.8, 1.8] → mean=1.8
        # rel_change = |1.8-2.0|/2.0 = 0.10
        losses = [2.0, 2.0, 2.0, 2.0, 1.8, 1.8, 1.8, 1.8]
        for r, loss in enumerate(losses, start=1):
            monitor.record(r, loss)
        monitor.should_stop(8)
        assert monitor.latest_relative_change == pytest.approx(0.10, abs=1e-9)


class TestStallDetection:
    def test_stall_warning_logged(self) -> None:
        import time
        from unittest.mock import MagicMock

        import numpy as np
        import structlog.testing
        from flwr.common import ndarrays_to_parameters

        from datp.federated.strategies import DatpFedAvg

        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=10,
            relative_threshold=0.001,
            window=2,
        )
        strategy = DatpFedAvg(
            convergence_monitor=monitor,
            round_timeout_s=0.001,
            fraction_fit=1.0,
            fraction_evaluate=1.0,
            min_fit_clients=1,
            min_evaluate_clients=1,
            min_available_clients=1,
            initial_parameters=ndarrays_to_parameters(
                [np.zeros((4, 3), dtype=np.float32)]
            ),
        )
        strategy._round_start_time = time.monotonic() - 1.0

        mock_proxy = MagicMock()
        mock_result = MagicMock()
        mock_result.num_examples = 100
        mock_result.loss = 0.5

        with structlog.testing.capture_logs() as cap:
            strategy.aggregate_evaluate(1, [(mock_proxy, mock_result)], [])

        assert any(
            "exceeded timeout" in entry.get("event", "")
            or "exceeded timeout" in str(entry)
            for entry in cap
        ), f"Expected stall warning but got: {cap}"


class TestAggregateEvaluateGuards:
    """Empty results / zero-example branches must not contaminate the convergence monitor
    and must signal 'no data' to Flower via None (not 0.0)."""

    def _make_strategy(self, monitor: ConvergenceMonitor) -> object:
        import numpy as np
        from flwr.common import ndarrays_to_parameters

        from datp.federated.strategies import DatpFedAvg

        return DatpFedAvg(
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
        )

    def test_no_results_returns_none_and_does_not_record(self) -> None:
        monitor = ConvergenceMonitor(
            rounds_initial=1, rounds_max=10, relative_threshold=0.05, window=2
        )
        strategy = self._make_strategy(monitor)

        loss, metrics = strategy.aggregate_evaluate( # type: ignore[attr-defined]
            server_round=1, results=[], failures=[]
        )

        assert loss is None
        assert metrics == {}
        assert monitor.num_recorded == 0
        assert monitor.loss_history == []

    def test_zero_total_examples_returns_none_and_does_not_record(self) -> None:
        from unittest.mock import MagicMock

        monitor = ConvergenceMonitor(
            rounds_initial=1, rounds_max=10, relative_threshold=0.05, window=2
        )
        strategy = self._make_strategy(monitor)
        proxy = MagicMock()
        result = MagicMock()
        result.num_examples = 0
        result.loss = 0.5

        loss, metrics = strategy.aggregate_evaluate( # type: ignore[attr-defined]
            server_round=1, results=[(proxy, result)], failures=[]
        )

        assert loss is None
        assert metrics == {}
        assert monitor.num_recorded == 0
        assert monitor.loss_history == []

    def test_valid_weighted_aggregation_records(self) -> None:
        from unittest.mock import MagicMock

        monitor = ConvergenceMonitor(
            rounds_initial=1, rounds_max=10, relative_threshold=0.05, window=2
        )
        strategy = self._make_strategy(monitor)
        proxy_a = MagicMock()
        res_a = MagicMock()
        res_a.num_examples = 100
        res_a.loss = 0.4
        proxy_b = MagicMock()
        res_b = MagicMock()
        res_b.num_examples = 300
        res_b.loss = 0.8

        loss, metrics = strategy.aggregate_evaluate( # type: ignore[attr-defined]
            server_round=1, results=[(proxy_a, res_a), (proxy_b, res_b)], failures=[]
        )

        assert loss == pytest.approx((0.4 * 100 + 0.8 * 300) / 400)
        assert metrics["weighted_val_loss"] == pytest.approx(loss)
        assert monitor.num_recorded == 1
        assert monitor.loss_history == [pytest.approx(loss)]


class TestConvergenceScheduling:
    def test_strategy_skips_fit_and_evaluate_after_convergence(self) -> None:
        from unittest.mock import MagicMock

        import numpy as np
        from flwr.common import ndarrays_to_parameters

        from datp.federated.strategies import DatpFedAvg

        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=10,
            relative_threshold=0.05,
            window=2,
        )
        strategy = DatpFedAvg(
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
        )

        mock_proxy = MagicMock()
        mock_result = MagicMock()
        mock_result.num_examples = 100
        mock_result.loss = 0.5

        # Need 2*window=4 constant losses to trigger convergence
        for r in range(1, 4):
            monitor.record(r, 0.5)
        strategy.aggregate_evaluate(
            server_round=4,
            results=[(mock_proxy, mock_result)],
            failures=[],
        )

        assert strategy.stopped is True
        assert strategy.configure_fit(5, MagicMock(), MagicMock()) == []
        assert strategy.configure_evaluate(5, MagicMock(), MagicMock()) == []
