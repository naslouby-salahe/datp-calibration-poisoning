from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import json
import shutil
import tempfile
from pathlib import Path

import typer
from rich.console import Console

from datp.artifacts.io import write_json_atomic
from datp.artifacts.layout import ArtifactLayout
from datp.artifacts.names import ArtifactFile
from datp.checkpointing.invariants import (
    CheckpointValidationConfig,
    validate_checkpoint_evaluation_invariants,
)
from datp.checkpointing.status import checkpoint_artifact_status
from datp.checkpointing.summary import select_global_primary_checkpoint
from datp.config.compose import BASE_CONFIG
from datp.config.stages import ExperimentStage
from datp.core.identity import PolicyRunId, TrainingCellId
from datp.core.provenance import hash_file
from datp.thresholding.metrics_serialization import SweepMetrics

app = typer.Typer(help="Journal checkpoint protocol commands.")
_stdout = Console()


@app.command("preview")
def preview() -> None:
    """Print the resolved journal checkpoint protocol config."""
    if BASE_CONFIG.checkpoint_protocol is None:
        _stdout.print("checkpoint_protocol is not configured.")
        return
    payload = BASE_CONFIG.checkpoint_protocol.model_dump(mode="json")
    _stdout.print(json.dumps(payload, indent=2, sort_keys=True), highlight=False)


@app.command("smoke")
def smoke(
    artifact_root: Path | None = typer.Option(
        None,
        help="Temporary artifact root. Must not be outputs/.",
    ),
) -> None:
    """Create a tiny temp-root protocol fixture and select one global checkpoint."""
    if artifact_root is None:
        with tempfile.TemporaryDirectory(
            prefix="datp_checkpoint_protocol_smoke_"
        ) as tmp:
            _run_smoke(Path(tmp))
        return
    _run_smoke(artifact_root)


def _run_smoke(artifact_root: Path) -> None:
    _reject_outputs_path(artifact_root)
    if artifact_root.exists():
        shutil.rmtree(artifact_root)
    metrics = _write_smoke_fixture(artifact_root)
    selection = select_global_primary_checkpoint(
        metrics=metrics,
        n_bootstrap=200,
        bootstrap_seed=BASE_CONFIG.statistics.bootstrap_seed,
    )
    _stdout.print(
        json.dumps(
            {
                "artifact_root": str(artifact_root),
                "rounds": [25, 50],
                "selected_round": selection.selected_round,
            },
            indent=2,
            sort_keys=True,
        ),
        highlight=False,
    )


@app.command("evaluate-from-scores")
def evaluate_from_scores(
    artifact_root: Path = typer.Option(..., help="Artifact root to validate."),
    seed: int = typer.Option(..., help="Seed."),
    checkpoint_round: int = typer.Option(..., help="Checkpoint round."),
) -> None:
    """Validate that controlled policies use the same checkpoint-round score artifacts."""
    stage = ExperimentStage.NBAIOT_MAIN
    layout = ArtifactLayout(base_dir=artifact_root, stage=stage)
    cell = TrainingCellId(stage=stage, seed=seed)
    candidate_paths = tuple(
        layout.policy_run_for_round(
            PolicyRunId(cell=cell, policy=policy), checkpoint_round
        ).metrics_path
        for policy in (
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        )
    )
    metrics_paths = tuple(path for path in candidate_paths if path.exists())
    invariant = validate_checkpoint_evaluation_invariants(
        CheckpointValidationConfig(
            stage=stage,
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
                "checkpoint_round": invariant.checkpoint_round,
                "policies": [p.value for p in invariant.policies],
            },
            sort_keys=True,
        )
    )


@app.command("status")
def status(
    artifact_root: Path = typer.Option(..., help="Artifact root to inspect."),
    seed: int = typer.Option(..., help="Seed."),
    checkpoint_round: int = typer.Option(..., help="Checkpoint round."),
) -> None:
    """Report missing checkpoint scores/results for one checkpoint cell."""
    stage = ExperimentStage.NBAIOT_MAIN
    cell_status = checkpoint_artifact_status(
        artifact_root=artifact_root,
        stage=stage,
        seed=seed,
        checkpoint_round=checkpoint_round,
    )
    _stdout.print(
        json.dumps(
            {
                "complete": cell_status.complete,
                "checkpoint": cell_status.checkpoint.value,
                "scores": cell_status.scores.value,
                "results": {
                    policy.value: result_status.value
                    for policy, result_status in cell_status.results
                },
            },
            indent=2,
            sort_keys=True,
        ),
        highlight=False,
    )


def _reject_outputs_path(path: Path) -> None:
    resolved = path.resolve()
    outputs_root = (Path.cwd() / "outputs").resolve()
    if resolved == outputs_root or outputs_root in resolved.parents:
        raise typer.BadParameter("checkpoint protocol smoke must not write to outputs/")


def _load_metrics(
    *, artifact_root: Path, seeds: tuple[int, ...], rounds: tuple[int, ...]
) -> tuple[SweepMetrics, ...]:
    stage = ExperimentStage.NBAIOT_MAIN
    layout = ArtifactLayout(base_dir=artifact_root, stage=stage)
    loaded: list[SweepMetrics] = []
    for seed in seeds:
        cell = TrainingCellId(stage=stage, seed=seed)
        for checkpoint_round in rounds:
            for policy in (
                ThresholdPolicy.GLOBAL_THRESHOLD,
                ThresholdPolicy.LOCAL_THRESHOLD,
            ):
                path = layout.policy_run_for_round(
                    PolicyRunId(cell=cell, policy=policy), checkpoint_round
                ).metrics_path
                loaded.append(
                    SweepMetrics.model_validate(
                        json.loads(path.read_text(encoding="utf-8"))
                    )
                )
    return tuple(loaded)


def _write_smoke_fixture(artifact_root: Path) -> tuple[SweepMetrics, ...]:
    from datp.testsupport.checkpoint_protocol import build_fake_checkpoint_metrics

    metrics = build_fake_checkpoint_metrics(rounds=(25, 50), seeds=(0, 1, 2))
    stage = ExperimentStage.NBAIOT_MAIN
    layout = ArtifactLayout(base_dir=artifact_root, stage=stage)
    for checkpoint_round in (25, 50):
        for seed in (0, 1, 2):
            cell = TrainingCellId(stage=stage, seed=seed)
            ckpt_path = (
                layout.checkpoint_dir_for_round(cell, checkpoint_round)
                / ArtifactFile.MODEL_CHECKPOINT
            )
            ckpt_path.parent.mkdir(parents=True, exist_ok=True)
            ckpt_path.write_text(
                f"fake checkpoint {seed} {checkpoint_round}\n", encoding="utf-8"
            )
            _write_manifest(layout, cell, checkpoint_round, ckpt_path)
    for metric in metrics:
        cell = TrainingCellId(stage=metric.stage, seed=metric.seed)
        run = PolicyRunId(cell=cell, policy=metric.policy)
        checkpoint_round = metric.checkpoint_round
        if checkpoint_round is None:
            raise RuntimeError("smoke metric lacks checkpoint_round")
        manifest_path = layout.score_cell_for_round(
            cell, checkpoint_round
        ).manifest_path
        checkpoint_path = (
            layout.checkpoint_dir_for_round(cell, checkpoint_round)
            / ArtifactFile.MODEL_CHECKPOINT
        )
        metric = metric.model_copy(
            update={
                "provenance": metric.provenance.model_copy(
                    update={
                        "model_checkpoint_identity": hash_file(checkpoint_path),
                        "score_artifact_identity": hash_file(manifest_path),
                    }
                )
            }
        )
        metrics_path = layout.policy_run_for_round(run, checkpoint_round).metrics_path
        write_json_atomic(metrics_path, metric.model_dump(mode="json"))
    return metrics


@app.command("summary")
def summary(
    artifact_root: Path = typer.Option(..., help="Artifact root to summarize."),
    seeds: list[int] = typer.Option(..., help="Seeds to include."),
    rounds: list[int] = typer.Option(..., help="Checkpoint rounds to include."),
) -> None:
    """Summarize primary training checkpoint metrics and select one global checkpoint."""
    metrics = _load_metrics(
        artifact_root=artifact_root, seeds=tuple(seeds), rounds=tuple(rounds)
    )
    selection = select_global_primary_checkpoint(
        metrics=metrics,
        n_bootstrap=BASE_CONFIG.statistics.n_bootstrap,
        bootstrap_seed=BASE_CONFIG.statistics.bootstrap_seed,
    )
    _stdout.print(
        json.dumps({"selected_round": selection.selected_round}, sort_keys=True)
    )


def _write_manifest(
    layout: ArtifactLayout,
    cell: TrainingCellId,
    checkpoint_round: int,
    checkpoint_path: Path,
) -> None:
    score_paths = layout.score_cell_for_round(cell, checkpoint_round)
    write_json_atomic(
        score_paths.manifest_path,
        {
            "schema_version": "1",
            "checkpoint_round": checkpoint_round,
            "model_checkpoint_hash": hash_file(checkpoint_path),
            "expected_client_ids": ["c1", "c2"],
            "expected_splits": ["cal", "test_benign", "test_attack"],
            "records": [],
            "completion_status": "complete",
        },
    )
