"""Tests verifying convergence monitor algorithms, window-based thresholds, and strategy integration gates."""

from __future__ import annotations

from typing import Any
import pytest

from datp.federated.convergence import ConvergenceMonitor


def _feed(monitor: ConvergenceMonitor, losses: list[float]) -> int | None:
    """Helper method to feed a list of losses into a ConvergenceMonitor."""
    for r, loss in enumerate(losses, start=1):
        monitor.record(loss)
        if monitor.should_stop(r):
            return r
    return None


class TestConvergenceTrigger:
    """Tests verifying that convergence triggers under stable/flat loss sequences."""

    def test_convergence_triggers_at_expected_round(self) -> None:
        """Verify convergence triggers correctly for a decaying loss sequence."""
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=100,
            relative_threshold=0.03,
            window=4,
        )

        losses = [1.0, 0.8, 0.6, 0.5, 0.4, 0.35, 0.32, 0.30]
        losses += [0.30] * 10

        stop_round = _feed(monitor, losses)

        assert stop_round is not None
        assert stop_round >= 5
        assert stop_round >= 2 * 4
        assert monitor.converged_round == stop_round

    def test_gradual_convergence(self) -> None:
        """Verify convergence triggers for a gradually decaying sequence."""
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
        assert stop_round >= 2 * 5

    def test_window_mean_comparison_differs_from_first_last(self) -> None:
        """Confirm window comparison checks are mean-based, not endpoint-based."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=100,
            relative_threshold=0.02,
            window=4,
        )

        losses = [1.0, 0.9, 0.8, 0.7, 0.7, 0.8, 0.7, 0.7]
        stop_round = _feed(monitor, losses)

        assert stop_round is None

    def test_flat_sequence_converges_with_mean_comparison(self) -> None:
        """Verify that flat sequence triggers convergence."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=100,
            relative_threshold=0.02,
            window=4,
        )

        losses = [0.5] * 8
        stop_round = _feed(monitor, losses)
        assert stop_round == 8


class TestRoundsInitialGuard:
    """Tests verifying that initial training rounds are guarded from stopping early."""

    def test_convergence_does_not_fire_before_rounds_initial(self) -> None:
        """Ensure convergence does not stop training before rounds_initial is reached."""
        monitor = ConvergenceMonitor(
            rounds_initial=20,
            rounds_max=100,
            relative_threshold=0.05,
            window=4,
        )
        flat_losses = [0.5] * 19

        for r, loss in enumerate(flat_losses, start=1):
            monitor.record(loss)
            assert not monitor.should_stop(r), (
                f"should_stop fired at round {r}, before rounds_initial=20"
            )

        monitor.record(0.5)
        assert monitor.should_stop(20)


class TestHardCap:
    """Tests verifying the max rounds cap behavior."""

    def test_convergence_hard_cap_at_rounds_max(self) -> None:
        """Verify convergence forces stopping at rounds_max."""
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
        """Verify hard cap is enforced even if no loss records are available."""
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=10,
            relative_threshold=0.03,
            window=4,
        )
        assert monitor.should_stop(10)


class TestInsufficientHistory:
    """Tests verifying history length requirements."""

    def test_convergence_does_not_fire_without_2x_window(self) -> None:
        """Ensure convergence requires history length of at least twice the window size."""
        window = 4
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=100,
            relative_threshold=0.05,
            window=window,
        )

        for r in range(1, 2 * window):
            monitor.record(0.5)
            assert not monitor.should_stop(r), (
                f"should_stop fired with only {r} recorded losses "
                f"(need 2*window={2 * window})"
            )

        monitor.record(0.5)
        assert monitor.should_stop(2 * window)


class TestFiniteLossValidation:
    """Tests verifying input validation for loss values."""

    def test_nan_loss_raises(self) -> None:
        """Verify record raises ValueError if input loss is NaN."""
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=100,
            relative_threshold=0.03,
            window=4,
        )
        with pytest.raises(ValueError, match="Non-finite loss"):
            monitor.record(float("nan"))

    def test_inf_loss_raises(self) -> None:
        """Verify record raises ValueError if input loss is positive infinity."""
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=100,
            relative_threshold=0.03,
            window=4,
        )
        with pytest.raises(ValueError, match="Non-finite loss"):
            monitor.record(float("inf"))

    def test_negative_inf_loss_raises(self) -> None:
        """Verify record raises ValueError if input loss is negative infinity."""
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=100,
            relative_threshold=0.03,
            window=4,
        )
        with pytest.raises(ValueError, match="Non-finite loss"):
            monitor.record(float("-inf"))


class TestFromConfig:
    """Tests verifying ConvergenceMonitor instantiation from DatpConfig."""

    def test_from_config(self) -> None:
        """Verify monitor is correctly initialized using values from config parser."""
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

        for r in range(1, 40):
            monitor.record(0.5)
            assert not monitor.should_stop(r), (
                f"should_stop fired at round {r} < rounds_initial=40"
            )

        monitor.record(0.5)
        assert monitor.should_stop(40)
        assert monitor.converged_round == 40

    def test_from_config_missing_key_raises(self) -> None:
        """Verify monitor construction raises AttributeError if federation key is missing."""
        with pytest.raises(AttributeError):
            ConvergenceMonitor.from_config({"federation": {}})  # type: ignore[arg-type]


class TestBaseConfigDefaults:
    """Tests verifying the default convergence configuration parameters."""

    def test_base_config_relative_threshold_is_0005(self) -> None:
        """Verify default relative threshold setting is 0.005."""
        from datp.config.compose import BASE_CONFIG

        assert BASE_CONFIG.federation.convergence.relative_threshold == pytest.approx(
            0.005
        )

    def test_base_config_window_is_10(self) -> None:
        """Verify default evaluation sliding window setting is 10."""
        from datp.config.compose import BASE_CONFIG

        assert BASE_CONFIG.federation.convergence.window == 10

    def test_base_config_rounds_initial_is_40(self) -> None:
        """Verify default initial rounds setting is 40."""
        from datp.config.compose import BASE_CONFIG

        assert BASE_CONFIG.federation.convergence.rounds_initial == 40

    def test_base_config_rounds_max_is_150(self) -> None:
        """Verify default maximum rounds setting is 150."""
        from datp.config.compose import BASE_CONFIG

        assert BASE_CONFIG.federation.convergence.rounds_max == 150


class TestValidationErrors:
    """Tests verifying monitor validation logic on settings inputs."""

    def test_rounds_initial_below_one(self) -> None:
        """Verify ValueError is raised if rounds_initial is less than 1."""
        with pytest.raises(ValueError, match=r"Invalid convergence settings"):
            ConvergenceMonitor(
                rounds_initial=0,
                rounds_max=10,
                relative_threshold=0.03,
                window=4,
            )

    def test_rounds_max_below_rounds_initial(self) -> None:
        """Verify ValueError is raised if rounds_max is less than rounds_initial."""
        with pytest.raises(ValueError, match=r"Invalid convergence settings"):
            ConvergenceMonitor(
                rounds_initial=20,
                rounds_max=10,
                relative_threshold=0.03,
                window=4,
            )

    def test_window_below_two(self) -> None:
        """Verify ValueError is raised if sliding window size is less than 2."""
        with pytest.raises(ValueError, match=r"Invalid convergence settings"):
            ConvergenceMonitor(
                rounds_initial=5,
                rounds_max=50,
                relative_threshold=0.03,
                window=1,
            )


class TestConvergedRoundLogged:
    """Tests verifying tracking of the converged round milestone."""

    def test_converged_round_logged(self) -> None:
        """Verify converged_round remains None until the milestone criteria is met."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=10,
            relative_threshold=0.05,
            window=2,
        )
        for r in range(1, 4):
            monitor.record(0.5)
            monitor.should_stop(r)

        assert monitor.converged_round is None

        monitor.record(0.5)
        assert monitor.should_stop(4)
        assert monitor.converged_round == 4

    def test_converged_round_none_before_convergence(self) -> None:
        """Verify converged_round is None before convergence fires."""
        monitor = ConvergenceMonitor(
            rounds_initial=10,
            rounds_max=100,
            relative_threshold=0.001,
            window=4,
        )
        monitor.record(1.0)
        monitor.record(0.5)
        monitor.should_stop(2)

        assert monitor.converged_round is None

    def test_first_converged_round_is_preserved(self) -> None:
        """Ensure the very first round milestone that satisfies convergence is preserved."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=100,
            relative_threshold=0.05,
            window=2,
        )
        for _ in range(1, 5):
            monitor.record(0.5)

        assert monitor.should_stop(4)
        assert monitor.converged_round == 4

        monitor.record(0.5)
        assert monitor.should_stop(5)
        assert monitor.converged_round == 4


class TestPreweightedScalar:
    """Tests verifying convergence monitor updates with pre-calculated losses."""

    def test_monitor_accepts_preweighted_scalar(self) -> None:
        """Verify monitor successfully processes external loss sequences."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.05,
            window=4,
        )

        preweighted = [0.123, 0.119, 0.115, 0.114, 0.114, 0.114, 0.114, 0.114]

        for r, loss in enumerate(preweighted, start=1):
            monitor.record(loss)

        assert monitor.num_recorded == len(preweighted)
        assert monitor.should_stop(len(preweighted))

    def test_num_recorded_tracks_calls(self) -> None:
        """Verify num_recorded increments on every record call."""
        monitor = ConvergenceMonitor(
            rounds_initial=5,
            rounds_max=50,
            relative_threshold=0.03,
            window=4,
        )
        assert monitor.num_recorded == 0
        monitor.record(0.5)
        assert monitor.num_recorded == 1
        monitor.record(0.4)
        assert monitor.num_recorded == 2


class TestEdgeCases:
    """Tests verifying edge cases such as near-zero loss values and odd window sizes."""

    def test_near_zero_loss_converges(self) -> None:
        """Verify convergence succeeds for loss values close to zero."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.05,
            window=4,
        )

        losses = [1e-15] * 8
        stop_round = _feed(monitor, losses)
        assert stop_round is not None

    def test_window_odd_size(self) -> None:
        """Verify convergence monitor works correctly when sliding window has odd size."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.05,
            window=5,
        )

        losses = [0.5] * 10
        stop_round = _feed(monitor, losses)
        assert stop_round is not None


class TestConvergenceAlgorithm:
    """Tests verifying the similarity checking logic inside the monitor."""

    def test_no_convergence_with_diverging_windows(self) -> None:
        """Ensure no convergence fires when consecutive window means diverge."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.05,
            window=4,
        )

        losses = [1.0, 0.9, 0.8, 0.7, 0.3, 0.3, 0.3, 0.3]
        for r, loss in enumerate(losses, start=1):
            monitor.record(loss)
        assert not monitor.should_stop(8)

    def test_converges_when_windows_similar(self) -> None:
        """Verify convergence triggers when consecutive window means are within relative threshold."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.05,
            window=4,
        )

        losses = [0.50, 0.50, 0.50, 0.50, 0.49, 0.49, 0.49, 0.49]
        for r, loss in enumerate(losses, start=1):
            monitor.record(loss)
        assert monitor.should_stop(8)

    def test_latest_relative_change_tracks_window_means(self) -> None:
        """Verify latest_relative_change correctly computes the relative change between window means."""
        monitor = ConvergenceMonitor(
            rounds_initial=1,
            rounds_max=50,
            relative_threshold=0.50,
            window=4,
        )

        losses = [2.0, 2.0, 2.0, 2.0, 1.8, 1.8, 1.8, 1.8]
        for r, loss in enumerate(losses, start=1):
            monitor.record(loss)
        monitor.should_stop(8)
        assert monitor.latest_relative_change == pytest.approx(0.10, abs=1e-9)


class TestAggregateEvaluateGuards:
    """Tests verifying strategy interaction and evaluation safeguards."""

    def _make_strategy(self, monitor: ConvergenceMonitor) -> Any:
        """Helper to configure and instantiate DatpFedAvg strategy."""
        import numpy as np
        from flwr.common import ndarrays_to_parameters
        from datp.federated.strategies import DatpFedAvg, FedAvgConfig

        return DatpFedAvg(
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
            )
        )

    def test_no_results_returns_none_and_does_not_record(self) -> None:
        """Verify strategy returns None evaluation loss and does not record if results list is empty."""
        monitor = ConvergenceMonitor(
            rounds_initial=1, rounds_max=10, relative_threshold=0.05, window=2
        )
        strategy = self._make_strategy(monitor)

        loss, metrics = strategy.aggregate_evaluate(
            server_round=1, results=[], failures=[]
        )

        assert loss is None
        assert metrics == {}
        assert monitor.num_recorded == 0
        assert monitor.loss_history == []

    def test_zero_total_examples_returns_none_and_does_not_record(self) -> None:
        """Verify strategy ignores evaluation results with zero client samples."""
        from unittest.mock import MagicMock

        monitor = ConvergenceMonitor(
            rounds_initial=1, rounds_max=10, relative_threshold=0.05, window=2
        )
        strategy = self._make_strategy(monitor)
        proxy = MagicMock()
        result = MagicMock()
        result.num_examples = 0
        result.loss = 0.5

        loss, metrics = strategy.aggregate_evaluate(
            server_round=1, results=[(proxy, result)], failures=[]
        )

        assert loss is None
        assert metrics == {}
        assert monitor.num_recorded == 0
        assert monitor.loss_history == []

    def test_valid_weighted_aggregation_records(self) -> None:
        """Verify strategy correctly computes weighted aggregate loss and updates the monitor."""
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

        loss, metrics = strategy.aggregate_evaluate(
            server_round=1, results=[(proxy_a, res_a), (proxy_b, res_b)], failures=[]
        )

        assert loss == pytest.approx((0.4 * 100 + 0.8 * 300) / 400)
        assert metrics["weighted_val_loss"] == pytest.approx(loss)
        assert monitor.num_recorded == 1
        assert monitor.loss_history == [pytest.approx(loss)]


class TestConvergenceScheduling:
    """Tests verifying training round scheduling flags after convergence has been met."""

    def test_strategy_skips_fit_and_evaluate_after_convergence(self) -> None:
        """Verify strategy returns empty instructions list once convergence stopped flag is set."""
        from unittest.mock import MagicMock
        import numpy as np
        from flwr.common import ndarrays_to_parameters
        from datp.federated.strategies import DatpFedAvg, FedAvgConfig

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
            )
        )

        mock_proxy = MagicMock()
        mock_result = MagicMock()
        mock_result.num_examples = 100
        mock_result.loss = 0.5

        for _ in range(1, 4):
            monitor.record(0.5)
        strategy.aggregate_evaluate(
            server_round=4,
            results=[(mock_proxy, mock_result)],
            failures=[],
        )

        assert strategy.stopped is True
        assert strategy.configure_fit(5, MagicMock(), MagicMock()) == []
        assert strategy.configure_evaluate(5, MagicMock(), MagicMock()) == []
