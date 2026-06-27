"""Unit tests for primary checkpoint selection logic."""

from __future__ import annotations

import pytest

from datp.checkpointing.summary import (
    select_global_primary_checkpoint,
    summaries_for_global_primary_checkpoint,
    summarize_checkpoint_metrics,
)
from datp.testsupport.checkpoint_protocol import build_fake_checkpoint_metrics


def test_summary_computes_checkpoint_metrics() -> None:
    metrics = build_fake_checkpoint_metrics(rounds=(25, 50), seeds=(0, 1, 2))

    summaries = summarize_checkpoint_metrics(metrics)

    assert {summary.checkpoint_round for summary in summaries} == {25, 50}
    assert all(summary.coverage_ratio == pytest.approx(1.0) for summary in summaries)
    assert all(summary.collapse_cell_count == 0 for summary in summaries)


def test_primary_training_selection_returns_one_global_checkpoint() -> None:
    metrics = build_fake_checkpoint_metrics(rounds=(25, 50), seeds=(0, 1, 2))

    selection = select_global_primary_checkpoint(
        metrics=metrics, n_bootstrap=200, bootstrap_seed=11
    )

    assert selection is not None
    assert selection.selected_round in {25, 50}


def test_primary_training_selection_handles_single_round() -> None:
    metrics = build_fake_checkpoint_metrics(rounds=(25,), seeds=(0, 1, 2))

    selection = select_global_primary_checkpoint(
        metrics=metrics, n_bootstrap=50, bootstrap_seed=7
    )

    assert selection is not None
    assert selection.selected_round == 25


def test_summaries_for_global_primary_checkpoint() -> None:
    metrics = build_fake_checkpoint_metrics(rounds=(25, 50), seeds=(0, 1, 2))

    selection = select_global_primary_checkpoint(
        metrics=metrics, n_bootstrap=200, bootstrap_seed=42
    )
    assert selection is not None
    policy_summaries = summarize_checkpoint_metrics(metrics)
    summaries = summaries_for_global_primary_checkpoint(policy_summaries, selection)

    assert len(summaries) > 0
    assert all(s.checkpoint_round == selection.selected_round for s in summaries)
