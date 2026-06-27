"""Communication-overhead modeling for FL training and threshold calibration."""

from __future__ import annotations

from dataclasses import dataclass

from datp.core.enums import CLUSTER_FINGERPRINT_FEATURES, ThresholdPolicy

_BYTES_PER_SCALAR = 4
_CLUSTER_DOWNLINK_FLOATS_PER_CLIENT = 2


@dataclass(frozen=True, slots=True)
class RoundComm:
    """Per-round communication payload sizes for model transfer in a single FL round."""

    round_num: int
    server_uplink_payload_bytes: int
    server_downlink_payload_bytes: int


@dataclass(frozen=True, slots=True)
class ThresholdComm:
    """Communication payload sizes for a single threshold-calibration policy."""

    policy: ThresholdPolicy
    server_uplink_payload_bytes: int
    server_downlink_payload_bytes: int


@dataclass(frozen=True, slots=True)
class TrainingCommSummary:
    """Aggregate communication summary for FL training: per-round and total bytes."""

    model_bytes: int
    total_rounds: int
    num_clients: int
    uplink_bytes_per_round: int
    downlink_bytes_per_round: int
    total_uplink_bytes: int
    total_downlink_bytes: int


@dataclass(frozen=True, slots=True)
class CommSummary:
    """Top-level communication summary: training overhead plus per-policy threshold overhead."""

    training: TrainingCommSummary
    threshold_calibration: dict[ThresholdPolicy, ThresholdComm]


def compute_model_bytes(param_count: int) -> int:
    """Return byte size of a model given its scalar parameter count."""
    return param_count * _BYTES_PER_SCALAR


def compute_round_comm(round_num: int, model_bytes: int, num_clients: int) -> RoundComm:
    """Compute per-round uplink and downlink bytes for model transfer."""
    return RoundComm(
        round_num=round_num,
        server_uplink_payload_bytes=model_bytes * num_clients,
        server_downlink_payload_bytes=model_bytes * num_clients,
    )


def compute_threshold_comm(policy: ThresholdPolicy, k_eligible: int) -> ThresholdComm:
    """Estimate communication bytes for a threshold-calibration policy."""
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
    total_rounds: int, model_bytes: int, num_clients: int, k_eligible: int
) -> CommSummary:
    """Build a complete communication summary for all threshold policies."""
    training = TrainingCommSummary(
        model_bytes=model_bytes,
        total_rounds=total_rounds,
        num_clients=num_clients,
        uplink_bytes_per_round=model_bytes * num_clients,
        downlink_bytes_per_round=model_bytes * num_clients,
        total_uplink_bytes=model_bytes * num_clients * total_rounds,
        total_downlink_bytes=model_bytes * num_clients * total_rounds,
    )
    threshold_calibration = {
        bl: compute_threshold_comm(bl, k_eligible) for bl in ThresholdPolicy
    }
    return CommSummary(training=training, threshold_calibration=threshold_calibration)
