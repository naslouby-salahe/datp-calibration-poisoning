from __future__ import annotations

from datp.core.enums import Baseline
from datp.federated.communication import (
    build_comm_summary,
    compute_model_bytes,
    compute_round_comm,
    compute_threshold_comm,
)


def test_compute_model_bytes_basic() -> None:
    assert compute_model_bytes(100) == 400  # 100 params × 4 bytes


def test_compute_model_bytes_zero_params() -> None:
    assert compute_model_bytes(0) == 0


def test_round_comm_single_client() -> None:
    rc = compute_round_comm(round_num=1, model_bytes=400, num_clients=1)
    assert rc.server_uplink_payload_bytes == 400
    assert rc.server_downlink_payload_bytes == 400


def test_round_comm_multiple_clients() -> None:
    rc = compute_round_comm(round_num=3, model_bytes=1000, num_clients=9)
    assert rc.server_uplink_payload_bytes == 9000
    assert rc.server_downlink_payload_bytes == 9000
    assert rc.round_num == 3


class TestThresholdComm:
    def test_b1_comm(self) -> None:
        tc = compute_threshold_comm(Baseline.B1, k_eligible=9, n_families=0)
        assert tc.baseline == Baseline.B1
        assert tc.server_uplink_payload_bytes == 36  # 9 × 4
        assert tc.server_downlink_payload_bytes == 36  # 9 × 4

    def test_b2_comm_zero(self) -> None:
        tc = compute_threshold_comm(Baseline.B2, k_eligible=9, n_families=0)
        assert tc.baseline == Baseline.B2
        assert tc.server_uplink_payload_bytes == 0
        assert tc.server_downlink_payload_bytes == 0

    def test_b3_comm(self) -> None:
        tc = compute_threshold_comm(Baseline.B3, k_eligible=9, n_families=3)
        assert tc.baseline == Baseline.B3
        assert tc.server_uplink_payload_bytes == 36  # 9 × 4
        assert tc.server_downlink_payload_bytes == 12  # 3 families × 4

    def test_b4_comm(self) -> None:
        tc = compute_threshold_comm(Baseline.B4, k_eligible=9, n_families=0)
        assert tc.baseline == Baseline.B4
        assert (
            tc.server_uplink_payload_bytes == 144
        )  # 9 × 4 fingerprint floats × 4 bytes
        assert tc.server_downlink_payload_bytes == 72  # 9 × 2 × 4


def test_build_comm_summary_structure() -> None:
    summary = build_comm_summary(
        total_rounds=10,
        model_bytes=1000,
        num_clients=9,
        k_eligible=7,
        n_families=3,
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
    assert tc[Baseline.B1].server_uplink_payload_bytes == 28  # 7 × 4
    assert tc[Baseline.B1].server_downlink_payload_bytes == 28  # 7 × 4
    assert tc[Baseline.B2].server_uplink_payload_bytes == 0
    assert tc[Baseline.B2].server_downlink_payload_bytes == 0
    assert tc[Baseline.B3].server_uplink_payload_bytes == 28  # 7 × 4
    assert tc[Baseline.B3].server_downlink_payload_bytes == 12  # 3 families × 4
    assert (
        tc[Baseline.B4].server_uplink_payload_bytes == 112
    )  # 7 × 4 fingerprint floats × 4 bytes
    assert tc[Baseline.B4].server_downlink_payload_bytes == 56  # 7 × 2 × 4


def test_build_comm_summary_all_baselines_present() -> None:
    summary = build_comm_summary(
        total_rounds=1,
        model_bytes=100,
        num_clients=2,
        k_eligible=2,
        n_families=1,
    )
    baselines = summary.threshold_calibration
    assert set(baselines.keys()) == {Baseline.B1, Baseline.B2, Baseline.B3, Baseline.B4}
