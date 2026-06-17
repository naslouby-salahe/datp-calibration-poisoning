from __future__ import annotations

import pytest

from datp.checkpointing.enums import PrimaryCheckpointSelectionRule
from datp.checkpointing.summary import (
    select_global_primary_checkpoint,
    summaries_for_global_primary_checkpoint,
    summarize_checkpoint_metrics,
)
from datp.core.enums import Regime
from datp.testsupport.checkpoint_protocol import build_fake_checkpoint_metrics


def test_summary_computes_checkpoint_metrics() -> None:
    metrics = build_fake_checkpoint_metrics(rounds=(25, 50), seeds=(0, 1, 2))

    summaries = summarize_checkpoint_metrics(metrics)

    assert {summary.checkpoint_round for summary in summaries} == {25, 50}
    assert all(summary.coverage_ratio == 1.0 for summary in summaries)
    assert all(summary.collapse_cell_count == 0 for summary in summaries)


def test_regime_a_selection_returns_one_global_checkpoint() -> None:
    metrics = build_fake_checkpoint_metrics(rounds=(25, 50), seeds=(0, 1, 2))

    selection = select_global_primary_checkpoint(
        metrics=metrics, n_bootstrap=200, bootstrap_seed=11
    )

    assert selection.regime == Regime.A
    assert selection.selected_round == 50
    assert selection.rule == PrimaryCheckpointSelectionRule.GLOBAL_LOWER_TAIL_TRADEOFF_FROM_REGIME_A
    assert not hasattr(selection, "selected_by_regime")


def test_selection_rejects_non_regime_a_metrics() -> None:
    metrics = build_fake_checkpoint_metrics(rounds=(25,), seeds=(0, 1, 2))
    mixed = tuple(metric.model_copy(update={"regime": Regime.B}) for metric in metrics)

    with pytest.raises(ValueError, match="Regime A only"):
        select_global_primary_checkpoint(
            metrics=mixed, n_bootstrap=200, bootstrap_seed=11
        )


def test_selected_global_checkpoint_can_be_applied_to_other_regime() -> None:
    metrics = build_fake_checkpoint_metrics(rounds=(25, 50), seeds=(0, 1, 2))

    selection = select_global_primary_checkpoint(
        metrics=metrics, n_bootstrap=200, bootstrap_seed=11
    )
    regime_b_metrics = tuple(
        metric.model_copy(update={"regime": Regime.B}) for metric in metrics
    )
    main_summaries = summaries_for_global_primary_checkpoint(
        summarize_checkpoint_metrics(regime_b_metrics),
        selection,
    )

    assert {summary.regime for summary in main_summaries} == {Regime.B}
    assert {summary.checkpoint_round for summary in main_summaries} == {50}


def test_selection_requires_full_coverage() -> None:
    metrics = list(build_fake_checkpoint_metrics(rounds=(25,), seeds=(0, 1, 2)))
    degraded = metrics[1].model_copy(update={"coverage_ratio": 0.5})
    metrics[1] = degraded

    with pytest.raises(ValueError, match="No checkpoint satisfies"):
        select_global_primary_checkpoint(
            metrics=tuple(metrics), n_bootstrap=200, bootstrap_seed=11
        )
