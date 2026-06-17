from __future__ import annotations

from pathlib import Path

import pytest

from datp.artifacts.io import write_json_atomic
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile
from datp.checkpointing.enums import CheckpointArtifactStatus
from datp.checkpointing.invariants import validate_checkpoint_evaluation_invariants
from datp.checkpointing.status import checkpoint_artifact_status
from datp.core.enums import Baseline, Regime
from datp.core.identity import BaselineRunId, TrainingCellId
from datp.core.provenance import hash_file
from datp.core.types import MetricsProvenance
from datp.testsupport.checkpoint_protocol import build_fake_checkpoint_metrics


def _write_manifest(layout: ArtifactLayout, cell: TrainingCellId, checkpoint_round: int) -> Path:
    ckpt_path = (
        layout.checkpoint_dir_for_round(cell, checkpoint_round)
        / ArtifactFile.MODEL_CHECKPOINT
    )
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    ckpt_path.write_text("checkpoint\n", encoding="utf-8")
    manifest_path = layout.score_cell_for_round(cell, checkpoint_round).manifest_path
    write_json_atomic(
        manifest_path,
        {
            "checkpoint_round": checkpoint_round,
            "model_checkpoint_hash": hash_file(ckpt_path),
            "expected_client_ids": ["c1", "c2"],
            "expected_splits": ["cal", "test_benign", "test_attack"],
        },
    )
    return manifest_path


def _write_metric(
    layout: ArtifactLayout,
    cell: TrainingCellId,
    baseline: Baseline,
    checkpoint_round: int,
    manifest_path: Path,
) -> Path:
    generated = build_fake_checkpoint_metrics(rounds=(checkpoint_round,), seeds=(cell.seed,))
    metric = next((item for item in generated if item.baseline == baseline), generated[0])
    provenance = MetricsProvenance(
        config_identity="config",
        split_manifest_identity="split",
        model_checkpoint_identity=hash_file(
            layout.checkpoint_dir_for_round(cell, checkpoint_round)
            / ArtifactFile.MODEL_CHECKPOINT
        ),
        score_artifact_identity=hash_file(manifest_path),
        metric_code_version="metric",
        threshold_code_version="threshold",
        package_version="package",
        generated_at_utc="2026-06-04T00:00:00Z",
    )
    metric = metric.model_copy(
        update={"baseline": baseline, "regime": cell.regime, "provenance": provenance}
    )
    run = BaselineRunId(cell=cell, baseline=baseline)
    metrics_path = layout.baseline_run_for_round(run, checkpoint_round).metrics_path
    write_json_atomic(metrics_path, metric.model_dump(mode="json"))
    return metrics_path


def test_same_round_invariant_passes(tmp_path: Path) -> None:
    layout = ArtifactLayout(base_dir=tmp_path, regime=Regime.A)
    cell = TrainingCellId(regime=Regime.A, seed=0, alpha=None)
    manifest = _write_manifest(layout, cell, 25)
    b1_path = _write_metric(layout, cell, Baseline.B1, 25, manifest)
    b2_path = _write_metric(layout, cell, Baseline.B2, 25, manifest)

    invariant = validate_checkpoint_evaluation_invariants(
        regime=Regime.A,
        seed=0,
        checkpoint_round=25,
        score_manifest_path=manifest,
        metrics_paths=(b1_path, b2_path),
        config_identity="config",
        split_manifest_identity="split",
        min_coverage_ratio=1.0,
    )

    assert invariant.checkpoint_round == 25
    assert invariant.baselines == (Baseline.B1, Baseline.B2)


def test_mixed_round_invariant_fails(tmp_path: Path) -> None:
    layout = ArtifactLayout(base_dir=tmp_path, regime=Regime.A)
    cell = TrainingCellId(regime=Regime.A, seed=0, alpha=None)
    manifest = _write_manifest(layout, cell, 25)
    b1_path = _write_metric(layout, cell, Baseline.B1, 25, manifest)

    with pytest.raises(ValueError, match="Mixed-round"):
        validate_checkpoint_evaluation_invariants(
            regime=Regime.A,
            seed=0,
            checkpoint_round=50,
            score_manifest_path=manifest,
            metrics_paths=(b1_path,),
            config_identity=None,
            split_manifest_identity=None,
            min_coverage_ratio=0.0,
        )


def test_b3_suppression_outside_regime_a_fails(tmp_path: Path) -> None:
    layout = ArtifactLayout(base_dir=tmp_path, regime=Regime.B)
    cell = TrainingCellId(regime=Regime.B, seed=0, alpha=None)
    manifest = _write_manifest(layout, cell, 25)
    metric_path = _write_metric(layout, cell, Baseline.B3, 25, manifest)

    with pytest.raises(ValueError, match="B3 is invalid"):
        validate_checkpoint_evaluation_invariants(
            regime=Regime.B,
            seed=0,
            checkpoint_round=25,
            score_manifest_path=manifest,
            metrics_paths=(metric_path,),
            config_identity=None,
            split_manifest_identity=None,
            min_coverage_ratio=0.0,
        )


def test_artifact_status_detects_missing_scores_and_results(tmp_path: Path) -> None:
    status = checkpoint_artifact_status(
        artifact_root=tmp_path,
        regime=Regime.A,
        seed=0,
        alpha=None,
        checkpoint_round=25,
        baselines=(Baseline.B1, Baseline.B2),
    )

    assert status.checkpoint == CheckpointArtifactStatus.MISSING
    assert status.scores == CheckpointArtifactStatus.MISSING
    assert status.complete is False
