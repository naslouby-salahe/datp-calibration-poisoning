from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.types import ThresholdResult
from datp.thresholding.policies import compute_cluster, compute_global, compute_local
from datp.types import (
    ClientId,
    Quantile,
    RandomSeed,
    SampleCount,
    ScoreVector,
    Threshold,
)

if TYPE_CHECKING:
    from datp.config.models import ThresholdConfig

_MODULE = "thresholding.derivation"


@dataclass(frozen=True, slots=True)
class ThresholdDerivation:
    policy: ThresholdPolicy
    client_errors: dict[ClientId, ScoreVector]
    n_min: SampleCount
    q: Quantile
    tau_global: Threshold
    threshold_cfg: ThresholdConfig
    seed: RandomSeed = RandomSeed(0)


def derive_threshold(inputs: ThresholdDerivation) -> ThresholdResult:
    run = PolicyRunId(
        cell=TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=inputs.seed),
        policy=inputs.policy,
    )

    if inputs.policy is ThresholdPolicy.GLOBAL_THRESHOLD:
        return compute_global(
            inputs.client_errors,
            inputs.n_min,
            q=inputs.q,
            run=run,
        )
    if inputs.policy is ThresholdPolicy.LOCAL_THRESHOLD:
        return compute_local(
            inputs.client_errors,
            inputs.n_min,
            inputs.tau_global,
            q=inputs.q,
            run=run,
        )
    if inputs.policy is ThresholdPolicy.CLUSTER_THRESHOLD:
        return compute_cluster(
            inputs.client_errors,
            inputs.n_min,
            inputs.tau_global,
            q=inputs.q,
            random_state=RandomSeed(inputs.threshold_cfg.cluster_random_state),
            cluster_k=inputs.threshold_cfg.cluster_k_nbaiot,
            n_init=inputs.threshold_cfg.cluster_n_init,
            max_iter=inputs.threshold_cfg.cluster_max_iter,
            run=run,
        )

    raise ValueError(
        f"[{_MODULE}] Unknown policy for threshold derivation. Expected: GLOBAL_THRESHOLD/LOCAL_THRESHOLD/CLUSTER_THRESHOLD. Got: {inputs.policy!r}."
    )
