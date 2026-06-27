"""Threshold primitives and policy derivation dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.types import ThresholdResult

if TYPE_CHECKING:
    from datp.config.models import ThresholdConfig

_MODULE = "thresholding.thresholds"


@dataclass(frozen=True, slots=True)
class _DeriveArgs:
    client_errors: dict[str, np.ndarray]
    n_min: int
    q: float
    run: PolicyRunId


@dataclass(frozen=True, slots=True)
class _DeriveInput:
    policy: ThresholdPolicy
    client_errors: dict[str, np.ndarray]
    n_min: int
    q: float
    tau_global: float
    threshold_cfg: "ThresholdConfig"
    seed: int = 0


def percentile_threshold(errors: np.ndarray, q: float) -> float:
    """Return the q-th percentile of error scores."""
    if errors.size == 0:
        raise ValueError(
            f"[{_MODULE}] Cannot compute percentile. Expected: non-empty array. Got: empty array."
        )
    if q < 0.0 or q > 100.0:
        raise ValueError(
            f"[{_MODULE}] Invalid percentile. Expected: 0 <= q <= 100. Got: {str(q)}."
        )
    return float(np.percentile(errors, q))


def arithmetic_mean_threshold(tau_list: list[float] | np.ndarray) -> float:
    """Return the arithmetic mean of a list of threshold values."""
    arr = np.asarray(tau_list, dtype=np.float64)
    if arr.size == 0:
        raise ValueError(
            f"[{_MODULE}] Cannot compute mean. Expected: non-empty threshold list. Got: empty list."
        )
    return float(arr.mean())


def _derive_global(args: _DeriveArgs) -> ThresholdResult:
    """Dispatch to the global-threshold computation."""
    from datp.thresholding.policies import compute_global

    return compute_global(args.client_errors, args.n_min, q=args.q, run=args.run)


def _derive_local(args: _DeriveArgs, tau_global: float) -> ThresholdResult:
    """Dispatch to the local-threshold computation."""
    from datp.thresholding.policies import compute_local

    return compute_local(
        args.client_errors,
        args.n_min,
        tau_global,
        q=args.q,
        run=args.run,
    )


def _derive_cluster(
    args: _DeriveArgs,
    tau_global: float,
    threshold_cfg: "ThresholdConfig",
) -> ThresholdResult:
    """Dispatch to the cluster-threshold computation."""
    from datp.thresholding.policies import compute_cluster

    return compute_cluster(
        args.client_errors,
        args.n_min,
        tau_global,
        q=args.q,
        random_state=threshold_cfg.cluster_random_state,
        cluster_k=threshold_cfg.cluster_k_nbaiot,
        n_init=threshold_cfg.cluster_n_init,
        max_iter=threshold_cfg.cluster_max_iter,
        run=args.run,
    )


def derive_threshold(inputs: _DeriveInput) -> ThresholdResult:
    """Derive thresholds by dispatching to the policy-specific computation."""
    run = PolicyRunId(
        cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=inputs.seed),
        policy=inputs.policy,
    )
    args = _DeriveArgs(
        client_errors=inputs.client_errors,
        n_min=inputs.n_min,
        q=inputs.q,
        run=run,
    )

    if inputs.policy == ThresholdPolicy.GLOBAL_THRESHOLD:
        return _derive_global(args)
    if inputs.policy == ThresholdPolicy.LOCAL_THRESHOLD:
        return _derive_local(args, inputs.tau_global)
    if inputs.policy == ThresholdPolicy.CLUSTER_THRESHOLD:
        return _derive_cluster(args, inputs.tau_global, inputs.threshold_cfg)

    raise ValueError(
        f"[{_MODULE}] Unknown policy for threshold derivation. Expected: GLOBAL_THRESHOLD/LOCAL_THRESHOLD/CLUSTER_THRESHOLD. Got: {repr(inputs.policy)}."
    )
