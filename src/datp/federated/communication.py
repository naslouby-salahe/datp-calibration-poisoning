from __future__ import annotations

from datp.types import (
    ByteCount,
    RoundCount,
    RoundIndex,
    SampleCount,
    SignedCount,
)


from dataclasses import dataclass

from datp.core.enums import CLUSTER_FINGERPRINT_FEATURES, ThresholdPolicy

_BYTES_PER_SCALAR = 4
_CLUSTER_DOWNLINK_FLOATS_PER_CLIENT = 2


@dataclass(frozen=True, slots=True)
class RoundComm:

    round_num: RoundIndex
    server_uplink_payload_bytes: ByteCount
    server_downlink_payload_bytes: ByteCount


@dataclass(frozen=True, slots=True)
class ThresholdComm:

    policy: ThresholdPolicy
    server_uplink_payload_bytes: ByteCount
    server_downlink_payload_bytes: ByteCount


@dataclass(frozen=True, slots=True)
class TrainingCommSummary:

    model_bytes: ByteCount
    total_rounds: RoundCount
    num_clients: SampleCount
    uplink_bytes_per_round: RoundIndex
    downlink_bytes_per_round: RoundIndex
    total_uplink_bytes: ByteCount
    total_downlink_bytes: ByteCount


@dataclass(frozen=True, slots=True)
class CommSummary:

    training: TrainingCommSummary
    threshold_calibration: dict[ThresholdPolicy, ThresholdComm]


def compute_model_bytes(param_count: ByteCount) -> ByteCount:
    return param_count * _BYTES_PER_SCALAR


def compute_round_comm(round_num: RoundIndex, model_bytes: ByteCount, num_clients: SampleCount) -> RoundComm:
    return RoundComm(
        round_num=round_num,
        server_uplink_payload_bytes=model_bytes * num_clients,
        server_downlink_payload_bytes=model_bytes * num_clients,
    )


def compute_threshold_comm(policy: ThresholdPolicy, k_eligible: SignedCount) -> ThresholdComm:
    if policy == ThresholdPolicy.GLOBAL_THRESHOLD:
        return ThresholdComm(
            policy, _BYTES_PER_SCALAR * k_eligible, _BYTES_PER_SCALAR * k_eligible
        )
    if policy == ThresholdPolicy.LOCAL_THRESHOLD:
        return ThresholdComm(policy, 0, 0)
    if policy == ThresholdPolicy.CLUSTER_THRESHOLD:
        cluster_floats = len(CLUSTER_FINGERPRINT_FEATURES)
        return ThresholdComm(
            policy,
            cluster_floats * _BYTES_PER_SCALAR * k_eligible,
            _CLUSTER_DOWNLINK_FLOATS_PER_CLIENT * _BYTES_PER_SCALAR * k_eligible,
        )
    raise ValueError(f"Unknown policy for comm overhead: {policy}")


def build_comm_summary(
    total_rounds: RoundCount, model_bytes: ByteCount, num_clients: SampleCount, k_eligible: SignedCount
) -> CommSummary:
    round_comm = compute_round_comm(1, model_bytes, num_clients)
    training = TrainingCommSummary(
        model_bytes=model_bytes,
        total_rounds=total_rounds,
        num_clients=num_clients,
        uplink_bytes_per_round=round_comm.server_uplink_payload_bytes,
        downlink_bytes_per_round=round_comm.server_downlink_payload_bytes,
        total_uplink_bytes=round_comm.server_uplink_payload_bytes * total_rounds,
        total_downlink_bytes=round_comm.server_downlink_payload_bytes * total_rounds,
    )
    threshold_calibration = {
        bl: compute_threshold_comm(bl, k_eligible) for bl in ThresholdPolicy
    }
    return CommSummary(training=training, threshold_calibration=threshold_calibration)
