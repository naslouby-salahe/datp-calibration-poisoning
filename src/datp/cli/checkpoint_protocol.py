"""Checkpoint protocol CLI: preview, smoke, evaluate, status, and summary."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import typer
from rich.console import Console

from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactDir
from datp.checkpointing.invariants import (
    CheckpointValidationConfig,
    validate_checkpoint_evaluation_invariants,
)
from datp.checkpointing.status import checkpoint_artifact_status
from datp.checkpointing.summary import select_global_primary_checkpoint
from datp.cli.enums import (
    _CHECKPOINT_DEFAULT_STAGE,
    _CHECKPOINT_SUMMARY_POLICIES,
    _ERROR_MUST_NOT_WRITE_OUTPUTS,
    _ERROR_NOT_CONFIGURED,
    _SMOKE_TEMP_DIR_PREFIX,
    CheckpointCommand,
    _CheckpointEvalField,
    _CheckpointSmokeField,
    _CheckpointStatusField,
    _CheckpointSummaryField,
)
from datp.config.compose import BASE_CONFIG
from datp.core.enums import CONTROLLED_POLICIES
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.thresholding.metrics_serialization import SweepMetrics

app = typer.Typer()
_stdout = Console()


@app.command(CheckpointCommand.PREVIEW.value)
def preview() -> None:
    """Print the resolved checkpoint protocol configuration as JSON."""
    if not BASE_CONFIG.checkpoint_protocol:
        _stdout.print(_ERROR_NOT_CONFIGURED)
        return
    _stdout.print(
        json.dumps(
            BASE_CONFIG.checkpoint_protocol.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        ),
        highlight=False,
    )


@app.command(CheckpointCommand.SMOKE.value)
def smoke(artifact_root: Path | None = typer.Option(None)) -> None:
    """Run a smoke test of the primary checkpoint selection logic."""
    if artifact_root:
        _run_smoke(artifact_root)
    else:
        with tempfile.TemporaryDirectory(prefix=_SMOKE_TEMP_DIR_PREFIX) as tmp:
            _run_smoke(Path(tmp))


def _run_smoke(artifact_root: Path) -> None:
    """Build a smoke fixture and run primary checkpoint selection."""
    from datp.testsupport.checkpoint_protocol import (
        SMOKE_N_BOOTSTRAP,
        SMOKE_ROUNDS,
        build_smoke_fixture,
    )

    _reject_outputs_path(artifact_root)
    if artifact_root.exists():
        shutil.rmtree(artifact_root)

    selection = select_global_primary_checkpoint(
        metrics=build_smoke_fixture(artifact_root),
        n_bootstrap=SMOKE_N_BOOTSTRAP,
        bootstrap_seed=BASE_CONFIG.statistics.bootstrap_seed,
    )

    _stdout.print(
        json.dumps(
            {
                _CheckpointSmokeField.ARTIFACT_ROOT.value: str(artifact_root),
                _CheckpointSmokeField.ROUNDS.value: list(SMOKE_ROUNDS),
                _CheckpointSmokeField.SELECTED_ROUND.value: selection.selected_round,
            },
            indent=2,
            sort_keys=True,
        ),
        highlight=False,
    )


@app.command(CheckpointCommand.EVALUATE_FROM_SCORES.value)
def evaluate_from_scores(
    artifact_root: Path = typer.Option(...),
    seed: int = typer.Option(...),
    checkpoint_round: int = typer.Option(...),
) -> None:
    """Validate checkpoint evaluation invariants from existing score artifacts."""
    layout = ArtifactLayout(base_dir=artifact_root, stage=_CHECKPOINT_DEFAULT_STAGE)
    cell = TrainingCellId(stage=_CHECKPOINT_DEFAULT_STAGE, seed=seed)

    metrics_paths = tuple(
        p
        for p in (
            layout.policy_run_for_round(
                PolicyRunId(cell=cell, policy=pol), checkpoint_round
            ).metrics_path
            for pol in CONTROLLED_POLICIES
        )
        if p.exists()
    )

    invariant = validate_checkpoint_evaluation_invariants(
        CheckpointValidationConfig(
            stage=_CHECKPOINT_DEFAULT_STAGE,
            seed=seed,
            checkpoint_round=checkpoint_round,
            score_manifest_path=layout.score_cell_for_round(
                cell, checkpoint_round
            ).manifest_path,
            config_identity=None,
            split_manifest_identity=None,
            min_coverage_ratio=0.0,
        ),
        metrics_paths=metrics_paths,
    )

    _stdout.print(
        json.dumps(
            {
                _CheckpointEvalField.CHECKPOINT_ROUND.value: invariant.checkpoint_round,
                _CheckpointEvalField.POLICIES.value: [
                    p.value for p in invariant.policies
                ],
            },
            sort_keys=True,
        )
    )


@app.command(CheckpointCommand.STATUS.value)
def status(
    artifact_root: Path = typer.Option(...),
    seed: int = typer.Option(...),
    checkpoint_round: int = typer.Option(...),
) -> None:
    """Print the artifact status for a checkpoint round cell as JSON."""
    cell_status = checkpoint_artifact_status(
        artifact_root=artifact_root,
        stage=_CHECKPOINT_DEFAULT_STAGE,
        seed=seed,
        checkpoint_round=checkpoint_round,
    )

    _stdout.print(
        json.dumps(
            {
                _CheckpointStatusField.COMPLETE.value: cell_status.complete,
                _CheckpointStatusField.CHECKPOINT.value: cell_status.checkpoint.value,
                _CheckpointStatusField.SCORES.value: cell_status.scores.value,
                _CheckpointStatusField.RESULTS.value: {
                    policy.value: res.value for policy, res in cell_status.results
                },
            },
            indent=2,
            sort_keys=True,
        ),
        highlight=False,
    )


@app.command(CheckpointCommand.SUMMARY.value)
def summary(
    artifact_root: Path = typer.Option(...),
    seeds: list[int] = typer.Option(...),
    rounds: list[int] = typer.Option(...),
) -> None:
    """Print the selected primary checkpoint round as JSON."""
    layout = ArtifactLayout(base_dir=artifact_root, stage=_CHECKPOINT_DEFAULT_STAGE)
    metrics = tuple(
        SweepMetrics.model_validate_json(
            layout.policy_run_for_round(
                PolicyRunId(
                    cell=TrainingCellId(stage=_CHECKPOINT_DEFAULT_STAGE, seed=s),
                    policy=p,
                ),
                r,
            ).metrics_path.read_text()
        )
        for s in seeds
        for r in rounds
        for p in _CHECKPOINT_SUMMARY_POLICIES
    )
    selection = select_global_primary_checkpoint(
        metrics=metrics,
        n_bootstrap=BASE_CONFIG.statistics.n_bootstrap,
        bootstrap_seed=BASE_CONFIG.statistics.bootstrap_seed,
    )
    _stdout.print(
        json.dumps(
            {_CheckpointSummaryField.SELECTED_ROUND.value: selection.selected_round},
            sort_keys=True,
        )
    )


def _reject_outputs_path(path: Path) -> None:
    """Raise if path resolves inside the outputs directory."""
    if path.resolve().is_relative_to((Path.cwd() / ArtifactDir.OUTPUTS).resolve()):
        raise typer.BadParameter(_ERROR_MUST_NOT_WRITE_OUTPUTS)
