"""Statistical utilities: bootstrap, effect size, divergence, aggregation, and hypothesis tests."""

from datp.statistics.aggregates import FprFleetStats, compute_fpr_fleet_stats, cv, iqr
from datp.statistics.bootstrap import BootstrapResult, bca_ci, bootstrap_ci
from datp.statistics.constants import (
    BootstrapField,
    BootstrapMethod,
    EffectMagnitude,
    StatsField,
)
from datp.statistics.divergence import (
    JSSummary,
    histogram_distribution,
    js_divergence_to_pool,
    pairwise_js_divergence,
    pairwise_js_from_distributions,
    pairwise_js_summary,
)
from datp.statistics.effect_size import CliffsDeltaResult, cliffs_delta
from datp.statistics.spearman import SpearmanResult, spearman_correlation
from datp.statistics.wilcoxon import (
    BonferroniResult,
    WilcoxonResult,
    bonferroni_correct,
    wilcoxon_test,
)

__all__ = [
    "bca_ci",
    "bootstrap_ci",
    "BootstrapField",
    "BootstrapMethod",
    "BootstrapResult",
    "BonferroniResult",
    "bonferroni_correct",
    "cliffs_delta",
    "CliffsDeltaResult",
    "compute_fpr_fleet_stats",
    "cv",
    "EffectMagnitude",
    "FprFleetStats",
    "histogram_distribution",
    "iqr",
    "JSSummary",
    "js_divergence_to_pool",
    "pairwise_js_divergence",
    "pairwise_js_from_distributions",
    "pairwise_js_summary",
    "spearman_correlation",
    "SpearmanResult",
    "StatsField",
    "wilcoxon_test",
    "WilcoxonResult",
]
