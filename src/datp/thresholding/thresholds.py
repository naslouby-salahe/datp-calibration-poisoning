from __future__ import annotations
from datp.core.enums import ThresholdPolicy

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from datp.core.errors import fmt
from datp.config.stages import ExperimentStage
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.types import ThresholdResult

if TYPE_CHECKING:
    from datp.config.models import ThresholdConfig

_MODULE = "thresholding.thresholds"


@dataclass(frozen=True, slots=True)
class _DeriveArgs:
    """Common arguments for policy threshold derivation."""

    client_errors: dict[str, np.ndarray]
    n_min: int
    q: float
    run: PolicyRunId


def percentile_threshold(errors: np.ndarray, q: float) -> float:
    """Raises ValueError if errors is empty."""
    if errors.size == 0:
        raise ValueError(
            fmt(_MODULE, "Cannot compute percentile", "non-empty array", "empty array")
        )
    return float(np.percentile(errors, q * 100))


def arithmetic_mean_threshold(tau_list: list[float] | np.ndarray) -> float:
    """Simple arithmetic mean (1/K)×Στᵢ; never weighted by sample size (weighting would introduce a second confound).

    Raises ValueError if tau_list is empty.
    """
    arr = np.asarray(tau_list, dtype=np.float64)
    if arr.size == 0:
        raise ValueError(
            fmt(
                _MODULE, "Cannot compute mean", "non-empty threshold list", "empty list"
            )
        )
    return float(arr.mean())


def _derive_global(args: _DeriveArgs) -> ThresholdResult:
    from datp.thresholding.policies import global_threshold as global_mod

    return global_mod.compute(args.client_errors, args.n_min, q=args.q, run=args.run)


def _derive_local(args: _DeriveArgs, tau_global: float) -> ThresholdResult:
    from datp.thresholding.policies import local_threshold as local_mod

    return local_mod.compute(
        args.client_errors, args.n_min, tau_global, q=args.q, run=args.run
    )


def _derive_cluster(
    args: _DeriveArgs,
    tau_global: float,
    threshold_cfg: "ThresholdConfig",
) -> ThresholdResult:
    from datp.thresholding.policies import cluster_threshold as cluster_mod

    k_for_a = threshold_cfg.cluster_k_nbaiot
    return cluster_mod.compute(
        args.client_errors,
        args.n_min,
        tau_global,
        q=args.q,
        random_state=threshold_cfg.cluster_random_state,
        cluster_k=k_for_a,
        k_candidates=threshold_cfg.cluster_k_candidates,
        n_init=threshold_cfg.cluster_n_init,
        max_iter=threshold_cfg.cluster_max_iter,
        run=args.run,
    )


@dataclass(frozen=True, slots=True)
class _DeriveInput:
    """Bundled inputs for threshold derivation."""

    policy: ThresholdPolicy
    client_errors: dict[str, np.ndarray]
    n_min: int
    q: float
    tau_global: float
    threshold_cfg: "ThresholdConfig"
    seed: int = 0


def derive_threshold(inputs: _DeriveInput) -> ThresholdResult:
    run = PolicyRunId(
        cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=inputs.seed),
        policy=inputs.policy,
    )
    args = _DeriveArgs(
        client_errors=inputs.client_errors, n_min=inputs.n_min, q=inputs.q, run=run
    )

    if inputs.policy == ThresholdPolicy.GLOBAL_THRESHOLD:
        return _derive_global(args)
    if inputs.policy == ThresholdPolicy.LOCAL_THRESHOLD:
        return _derive_local(args, inputs.tau_global)
    if inputs.policy == ThresholdPolicy.CLUSTER_THRESHOLD:
        return _derive_cluster(args, inputs.tau_global, inputs.threshold_cfg)

    raise ValueError(
        fmt(
            "thresholds",
            "Unknown policy for threshold derivation",
            "GLOBAL_THRESHOLD/LOCAL_THRESHOLD/CLUSTER_THRESHOLD",
            repr(inputs.policy),
        )
    )
