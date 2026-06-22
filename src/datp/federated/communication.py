# SPDX-License-Identifier: Proprietary
"""Threshold calibration payload accounting.

Accounting model: **server-aggregated payload bytes**.
- uplink_bytes = total bytes received by the server from all clients in one round/phase.
- downlink_bytes = total bytes sent by the server to all clients in one round/phase.
All payloads are 32-bit (4-byte) floats.
"""

from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from dataclasses import dataclass

from datp.core.enums import CLUSTER_FINGERPRINT_FEATURES
from datp.core.errors import fmt

_BYTES_PER_SCALAR = 4
_MODULE = "federated.communication"

# Cluster threshold downlink: assignment index + cluster-level threshold.
_CLUSTER_DOWNLINK_FLOATS_PER_CLIENT = 2


@dataclass(frozen=True, slots=True)
class RoundComm:
    round_num: int
    server_uplink_payload_bytes: int
    server_downlink_payload_bytes: int


@dataclass(frozen=True, slots=True)
class ThresholdComm:
    policy: ThresholdPolicy
    server_uplink_payload_bytes: int
    server_downlink_payload_bytes: int


@dataclass(frozen=True, slots=True)
class TrainingCommSummary:
    model_bytes: int
    total_rounds: int
    num_clients: int
    uplink_bytes_per_round: int
    downlink_bytes_per_round: int
    total_uplink_bytes: int
    total_downlink_bytes: int


@dataclass(frozen=True, slots=True)
class CommSummary:
    training: TrainingCommSummary
    threshold_calibration: dict[ThresholdPolicy, ThresholdComm]


def compute_model_bytes(param_count: int) -> int:
    return param_count * _BYTES_PER_SCALAR


def compute_round_comm(
    round_num: int,
    model_bytes: int,
    num_clients: int,
) -> RoundComm:
    return RoundComm(
        round_num=round_num,
        server_uplink_payload_bytes=model_bytes * num_clients,
        server_downlink_payload_bytes=model_bytes * num_clients,
    )


def compute_threshold_comm(
    policy: ThresholdPolicy,
    k_eligible: int,
) -> ThresholdComm:
    if policy == ThresholdPolicy.GLOBAL_THRESHOLD:
        return ThresholdComm(
            policy=policy,
            server_uplink_payload_bytes=_BYTES_PER_SCALAR * k_eligible,
            server_downlink_payload_bytes=_BYTES_PER_SCALAR * k_eligible,
        )
    if policy == ThresholdPolicy.LOCAL_THRESHOLD:
        # LOCAL_THRESHOLD computes the per-client threshold locally from calibration scores — no inter-client
        # threshold communication is required; each client applies only its own quantile.
        return ThresholdComm(
            policy=policy,
            server_uplink_payload_bytes=0,
            server_downlink_payload_bytes=0,
        )
    if policy == ThresholdPolicy.CLUSTER_THRESHOLD:
        cluster_fingerprint_floats = len(CLUSTER_FINGERPRINT_FEATURES)
        return ThresholdComm(
            policy=policy,
            server_uplink_payload_bytes=cluster_fingerprint_floats
            * _BYTES_PER_SCALAR
            * k_eligible,
            server_downlink_payload_bytes=_CLUSTER_DOWNLINK_FLOATS_PER_CLIENT
            * _BYTES_PER_SCALAR
            * k_eligible,
        )
    raise ValueError(
        fmt(
            _MODULE,
            "Unknown policy for comm overhead",
            "one of ['global_threshold', 'local_threshold', 'cluster_threshold']",
            repr(policy),
        )
    )


def build_comm_summary(
    total_rounds: int,
    model_bytes: int,
    num_clients: int,
    k_eligible: int,
) -> CommSummary:
    training = TrainingCommSummary(
        model_bytes=model_bytes,
        total_rounds=total_rounds,
        num_clients=num_clients,
        uplink_bytes_per_round=model_bytes * num_clients,
        downlink_bytes_per_round=model_bytes * num_clients,
        total_uplink_bytes=model_bytes * num_clients * total_rounds,
        total_downlink_bytes=model_bytes * num_clients * total_rounds,
    )

    threshold_calibration: dict[ThresholdPolicy, ThresholdComm] = {}
    for bl in ThresholdPolicy:
        threshold_calibration[bl] = compute_threshold_comm(bl, k_eligible)

    return CommSummary(
        training=training,
        threshold_calibration=threshold_calibration,
    )
