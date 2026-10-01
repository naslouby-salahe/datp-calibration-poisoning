"""Shared field bundles for building BoundedSweepResultRow instances in tests."""

from __future__ import annotations

import math
from typing import Any

from datp.core.enums import ThresholdPolicy


def extended_row_fields(policy: ThresholdPolicy) -> dict[str, Any]:
    """Return values for every row field added after the original bounded-sweep schema."""
    is_cluster = policy == ThresholdPolicy.CLUSTER_THRESHOLD
    nan = math.nan
    return {
        "victim_fpr_clean": 0.01,
        "victim_fpr_poisoned": 0.01,
        "victim_delta_fpr": 0.0,
        "victim_fp_clean": 10,
        "victim_fp_poisoned": 10,
        "victim_fn_clean": 5,
        "victim_fn_poisoned": 5,
        "victim_n_test_benign": 1000,
        "victim_n_test_attack": 100,
        "nonvictim_mean_tpr_clean": 0.9,
        "nonvictim_mean_tpr_poisoned": 0.9,
        "nonvictim_mean_delta_tpr": 0.0,
        "nonvictim_worst_delta_tpr": 0.0,
        "nonvictim_mean_fpr_clean": 0.01,
        "nonvictim_mean_fpr_poisoned": 0.01,
        "nonvictim_mean_delta_fpr": 0.0,
        "nonvictim_worst_delta_fpr": 0.0,
        "nonvictim_mean_delta_ba": 0.0,
        "nonvictim_mean_delta_macro_f1": 0.0,
        "nonvictim_delta_fp_total": 0,
        "nonvictim_delta_fn_total": 0,
        "victim_delta_tau_scale_base": 0.02,
        "iqr_median_clean": 0.02,
        "delta_tau_bound_utilization": 0.1,
        "n_replaced": 10,
        "cal_duplicate_rate_clean": 0.0,
        "cal_duplicate_rate_poisoned": 0.05,
        "cluster_sizes_clean": (4, 3, 2) if is_cluster else (),
        "cluster_sizes_poisoned": (4, 3, 2) if is_cluster else (),
        "cluster_victim_size_clean": 2 if is_cluster else nan,
        "cluster_victim_size_poisoned": 2 if is_cluster else nan,
        "cluster_n_reassigned": 0 if is_cluster else nan,
        "cluster_silhouette_clean": 0.4 if is_cluster else nan,
        "cluster_silhouette_poisoned": 0.4 if is_cluster else nan,
        "fixed_cluster_victim_delta_tau": 0.05 if is_cluster else nan,
        "fixed_cluster_victim_delta_tpr": 0.0 if is_cluster else nan,
        "fixed_cluster_victim_delta_fpr": 0.0 if is_cluster else nan,
        "fixed_cluster_delta_cv_fpr": 0.0 if is_cluster else nan,
        "fixed_cluster_delta_mean_fpr": 0.0 if is_cluster else nan,
        "fixed_cluster_nonvictim_mean_delta_tpr": 0.0 if is_cluster else nan,
        "fixed_cluster_nonvictim_mean_delta_fpr": 0.0 if is_cluster else nan,
    }
