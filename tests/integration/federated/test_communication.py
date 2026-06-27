"""Unit tests for federated communication-cost calculations."""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from datp.federated.communication import (
    build_comm_summary,
    compute_model_bytes,
    compute_round_comm,
    compute_threshold_comm,
)


def test_compute_model_bytes_basic() -> None:
    """100 float32 parameters produce 400 bytes."""
    assert compute_model_bytes(100) == 400


def test_compute_model_bytes_zero_params() -> None:
    """Zero parameters produce zero bytes."""
    assert compute_model_bytes(0) == 0


def test_round_comm_single_client() -> None:
    """Single-client round sends model bytes once up and once down."""
    rc = compute_round_comm(round_num=1, model_bytes=400, num_clients=1)
    assert rc.server_uplink_payload_bytes == 400
    assert rc.server_downlink_payload_bytes == 400


def test_round_comm_multiple_clients() -> None:
    """Multi-client round scales uplink and downlink by client count."""
    rc = compute_round_comm(round_num=3, model_bytes=1000, num_clients=9)
    assert rc.server_uplink_payload_bytes == 9000
    assert rc.server_downlink_payload_bytes == 9000
    assert rc.round_num == 3


class TestThresholdComm:
    """Threshold communication cost for each policy."""

    def test_global_threshold_comm(self) -> None:
        """Global threshold sends one float32 per eligible client each way."""
        tc = compute_threshold_comm(ThresholdPolicy.GLOBAL_THRESHOLD, k_eligible=9)
        assert tc.policy == ThresholdPolicy.GLOBAL_THRESHOLD
        assert tc.server_uplink_payload_bytes == 36
        assert tc.server_downlink_payload_bytes == 36

    def test_local_threshold_comm_zero(self) -> None:
        """Local threshold requires zero communication."""
        tc = compute_threshold_comm(ThresholdPolicy.LOCAL_THRESHOLD, k_eligible=9)
        assert tc.policy == ThresholdPolicy.LOCAL_THRESHOLD
        assert tc.server_uplink_payload_bytes == 0
        assert tc.server_downlink_payload_bytes == 0

    def test_cluster_threshold_comm(self) -> None:
        """Cluster threshold sends k assignments up and per-cluster thresholds down."""
        tc = compute_threshold_comm(ThresholdPolicy.CLUSTER_THRESHOLD, k_eligible=9)
        assert tc.policy == ThresholdPolicy.CLUSTER_THRESHOLD
        assert tc.server_uplink_payload_bytes == 144
        assert tc.server_downlink_payload_bytes == 72


def test_build_comm_summary_structure() -> None:
    """Full communication summary includes training and threshold-calibration byte counts."""
    summary = build_comm_summary(
        total_rounds=10,
        model_bytes=1000,
        num_clients=9,
        k_eligible=7,
    )

    training = summary.training
    assert training.model_bytes == 1000
    assert training.total_rounds == 10
    assert training.num_clients == 9
    assert training.uplink_bytes_per_round == 9000
    assert training.downlink_bytes_per_round == 9000
    assert training.total_uplink_bytes == 90000
    assert training.total_downlink_bytes == 90000

    tc = summary.threshold_calibration
    assert tc[ThresholdPolicy.GLOBAL_THRESHOLD].server_uplink_payload_bytes == 28
    assert tc[ThresholdPolicy.GLOBAL_THRESHOLD].server_downlink_payload_bytes == 28
    assert tc[ThresholdPolicy.LOCAL_THRESHOLD].server_uplink_payload_bytes == 0
    assert tc[ThresholdPolicy.LOCAL_THRESHOLD].server_downlink_payload_bytes == 0
    assert tc[ThresholdPolicy.CLUSTER_THRESHOLD].server_uplink_payload_bytes == 112
    assert tc[ThresholdPolicy.CLUSTER_THRESHOLD].server_downlink_payload_bytes == 56


def test_build_comm_summary_all_policies_present() -> None:
    """Summary includes entries for all three threshold policies."""
    summary = build_comm_summary(
        total_rounds=1,
        model_bytes=100,
        num_clients=2,
        k_eligible=2,
    )
    baselines = summary.threshold_calibration
    assert set(baselines.keys()) == {
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    }
