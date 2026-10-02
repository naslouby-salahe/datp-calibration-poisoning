
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
from datp.checkpointing.status import (
    CheckpointArtifactCellStatus,
    checkpoint_artifact_status,
)
from datp.checkpointing.summary import select_global_primary_checkpoint
from datp.cli.enums import (
    CHECKPOINT_DEFAULT_STAGE,
    CHECKPOINT_SUMMARY_POLICIES,
    ERROR_MUST_NOT_WRITE_OUTPUTS,
    ERROR_NOT_CONFIGURED,
    CheckpointCommand,
    CheckpointEvalField,
    CheckpointSmokeField,
    CheckpointStatusField,
    CheckpointSummaryField,
)
from datp.config.compose import BASE_CONFIG
from datp.core.enums import CONTROLLED_POLICIES, PathToken
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.types import (
    RandomSeed,
    RoundIndex,
)
from datp.thresholding.metrics_serialization import SweepMetrics

app = typer.Typer()
_stdout = Console()


def _round_index_from_cli(value: int) -> RoundIndex:
    if value < 0:
        raise typer.BadParameter("round must be non-negative")
    return value


@app.command(CheckpointCommand.PREVIEW)
def preview() -> None:
    """Print the resolved checkpoint protocol configuration as JSON."""
    if not BASE_CONFIG.checkpoint_protocol:
        _stdout.print(ERROR_NOT_CONFIGURED)
        return
    _stdout.print(
        json.dumps(
            BASE_CONFIG.checkpoint_protocol.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        ),
        highlight=False,
    )


@app.command(CheckpointCommand.SMOKE)
def smoke(artifact_root: Path | None = typer.Option(None)) -> None:
    """Run a smoke test of the primary checkpoint selection logic."""
    if artifact_root:
        _run_smoke(artifact_root)
    else:
        with tempfile.TemporaryDirectory(prefix=PathToken.CHECKPOINT_PROTOCOL_SMOKE_TEMP_PREFIX) as tmp:
            _run_smoke(Path(tmp))


def _run_smoke(artifact_root: Path) -> None:
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
                CheckpointSmokeField.ARTIFACT_ROOT: str(artifact_root),
                CheckpointSmokeField.ROUNDS: list(SMOKE_ROUNDS),
                CheckpointSmokeField.SELECTED_ROUND: selection.selected_round,
            },
            indent=2,
            sort_keys=True,
        ),
        highlight=False,
    )


@app.command(CheckpointCommand.EVALUATE_FROM_SCORES)
def evaluate_from_scores(
    artifact_root: Path = typer.Option(...),
    seed: int = typer.Option(...),
    checkpoint_round: int = typer.Option(...),
) -> None:
    """Validate checkpoint evaluation invariants from existing score artifacts."""
    seed_value = RandomSeed(seed)
    round_index = _round_index_from_cli(checkpoint_round)
    layout = ArtifactLayout(base_dir=artifact_root, stage=CHECKPOINT_DEFAULT_STAGE)
    cell = TrainingCellId(stage=CHECKPOINT_DEFAULT_STAGE, seed=seed_value)

    metrics_paths = tuple(
        p
        for p in (
            layout.policy_run(
                PolicyRunId(cell=cell, policy=pol), round_index
            ).metrics_path
            for pol in CONTROLLED_POLICIES
        )
        if p.exists()
    )

    invariant = validate_checkpoint_evaluation_invariants(
        CheckpointValidationConfig(
            stage=CHECKPOINT_DEFAULT_STAGE,
            seed=seed_value,
            checkpoint_round=round_index,
            score_manifest_path=layout.score_cell(
                cell, round_index
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
                CheckpointEvalField.CHECKPOINT_ROUND: invariant.checkpoint_round,
                CheckpointEvalField.POLICIES: [
                    p for p in invariant.policies
                ],
            },
            sort_keys=True,
        )
    )


@app.command(CheckpointCommand.STATUS)
def status(
    artifact_root: Path = typer.Option(...),
    seed: int = typer.Option(...),
    checkpoint_round: int = typer.Option(...),
) -> None:
    """Print the artifact status for a checkpoint round cell as JSON."""
    seed_value = RandomSeed(seed)
    round_index = _round_index_from_cli(checkpoint_round)
    cell_status: CheckpointArtifactCellStatus = checkpoint_artifact_status(
        artifact_root=artifact_root,
        stage=CHECKPOINT_DEFAULT_STAGE,
        seed=seed_value,
        checkpoint_round=round_index,
    )

    _stdout.print(
        json.dumps(
            {
                CheckpointStatusField.COMPLETE: cell_status.complete,
                CheckpointStatusField.CHECKPOINT: cell_status.checkpoint,
                CheckpointStatusField.SCORES: cell_status.scores,
                CheckpointStatusField.RESULTS: {
                    policy: res for policy, res in cell_status.results
                },
            },
            indent=2,
            sort_keys=True,
        ),
        highlight=False,
    )


@app.command(CheckpointCommand.SUMMARY)
def summary(
    artifact_root: Path = typer.Option(...),
    seeds: list[int] = typer.Option(...),
    rounds: list[int] = typer.Option(...),
) -> None:
    """Print the selected primary checkpoint round as JSON."""
    training_seeds = tuple(RandomSeed(seed) for seed in seeds)
    checkpoint_rounds = tuple(_round_index_from_cli(value) for value in rounds)
    layout = ArtifactLayout(base_dir=artifact_root, stage=CHECKPOINT_DEFAULT_STAGE)
    metrics = tuple(
        SweepMetrics.model_validate_json(
            layout.policy_run(
                PolicyRunId(
                    cell=TrainingCellId(
                        stage=CHECKPOINT_DEFAULT_STAGE, seed=RandomSeed(s)
                    ),
                    policy=p,
                ),
                r,
            ).metrics_path.read_text()
        )
        for s in training_seeds
        for r in checkpoint_rounds
        for p in CHECKPOINT_SUMMARY_POLICIES
    )
    selection = select_global_primary_checkpoint(
        metrics=metrics,
        n_bootstrap=BASE_CONFIG.statistics.n_bootstrap,
        bootstrap_seed=BASE_CONFIG.statistics.bootstrap_seed,
    )
    _stdout.print(
        json.dumps(
            {CheckpointSummaryField.SELECTED_ROUND: selection.selected_round},
            sort_keys=True,
        )
    )


def _reject_outputs_path(path: Path) -> None:
    if path.resolve().is_relative_to((Path.cwd() / ArtifactDir.OUTPUTS).resolve()):
        raise typer.BadParameter(ERROR_MUST_NOT_WRITE_OUTPUTS)
