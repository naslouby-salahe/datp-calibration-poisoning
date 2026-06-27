"""Manifest building, emission, loading, and run-log entry writing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from datp.artifacts.poison_names import ManifestFile
from datp.attacks.enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.attacks.manifests.run_manifest import (
    RESERVOIR_MODE,
    ProvenanceRecord,
    RunManifest,
)
from datp.attacks.planning.guardrails import assert_valid_source_objective_pair
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.seeds import SeedPair, SeedRecord


class ManifestEmissionError(ValueError):
    """Raised when manifest emission preconditions are not met."""


@dataclass(frozen=True, slots=True)
class ManifestBuildRequest:
    """Input bundle for constructing a RunManifest."""

    dataset: str
    stage: ExperimentStage
    policy: ThresholdPolicy
    objective: AttackerObjective
    source: PoisoningSourceStrategy
    fraction: float
    target_scope: PoisoningTargetScope
    training_seed: int
    poisoning_seed: int
    client_idx: int
    scope_idx: int
    mu_flag_threshold: float | None
    repository: str
    local_epochs: int = 1
    checkpoint_round: int | None = None
    injection_rule: CalibrationInjectionRule = (
        CalibrationInjectionRule.REPLACE_FIXED_BUDGET
    )
    reservoir_mode: str = RESERVOIR_MODE


def build_manifest(request: ManifestBuildRequest) -> RunManifest:
    """Build a RunManifest from a validated build request."""
    assert_valid_source_objective_pair(request.source, request.objective)

    return RunManifest(
        dataset=request.dataset,
        stage=request.stage,
        policy=request.policy,
        objective=request.objective,
        source=request.source,
        injection_rule=request.injection_rule,
        fraction=request.fraction,
        target_scope=request.target_scope,
        training_seed=request.training_seed,
        poisoning_seed=request.poisoning_seed,
        client_idx=request.client_idx,
        scope_idx=request.scope_idx,
        reservoir_mode=request.reservoir_mode,
        mu_flag_threshold=request.mu_flag_threshold,
        seed_record=SeedRecord(
            pair=SeedPair(
                training_seed=request.training_seed,
                poisoning_seed=request.poisoning_seed,
            ),
            client_idx=request.client_idx,
            scope_idx=request.scope_idx,
        ),
        provenance=ProvenanceRecord(
            local_epochs=request.local_epochs,
            repository=request.repository,
            checkpoint_round=request.checkpoint_round,
        ),
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def emit_manifest(manifest: RunManifest, run_dir: Path) -> Path:
    """Write a RunManifest JSON file to the run directory."""
    if manifest.mu_flag_threshold is None:
        raise ManifestEmissionError(
            "mu_flag_threshold must be locked (non-None) before emitting manifest."
        )

    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / ManifestFile.RUN_MANIFEST
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_manifest(run_dir: Path) -> RunManifest:
    """Load a RunManifest from a run directory."""
    path = run_dir / ManifestFile.RUN_MANIFEST
    return RunManifest.model_validate_json(path.read_text(encoding="utf-8"))


class RunLogEntry(BaseModel):
    """Single JSON-line entry in the run log."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset: str
    policy: ThresholdPolicy
    objective: AttackerObjective
    source: PoisoningSourceStrategy
    fraction: float
    training_seed: int
    poisoning_seed: int
    mu_flag_threshold: float
    manifest_path: str
    generated_at_utc: str


def write_run_log_entry(entry: RunLogEntry, log_path: Path) -> None:
    """Append a JSON-line run-log entry to the log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(entry.model_dump_json() + "\n")
