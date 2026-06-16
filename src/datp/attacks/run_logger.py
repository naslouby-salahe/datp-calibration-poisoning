"""manifest emission and run logging.

Provides helpers to:
  - Build a RunManifest from cell parameters.
  - Write the manifest as JSON to a run directory.
  - Append a RunLogEntry to a JSONL run log.

mu_flag_threshold must be locked (non-None) before calling emit_manifest;
this module enforces that constraint.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from datp.artifacts.poison_names import ManifestFile
from datp.attacks.poison_enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    ExperimentScale,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ThresholdPolicy,
)
from datp.attacks.run_manifest import (
    RESERVOIR_MODE,
    ProvenanceRecord,
    RunManifest,
    SeedRecordModel,
)
from datp.core.seed_sequence import SeedRecord


class ManifestEmissionError(ValueError):
    """Raised when manifest cannot be emitted due to a lock violation."""


def build_manifest(
    *,
    dataset: str,
    scale: ExperimentScale,
    policy: ThresholdPolicy,
    objective: AttackerObjective,
    source: PoisoningSourceStrategy,
    fraction: float,
    target_scope: PoisoningTargetScope,
    training_seed: int,
    poisoning_seed: int,
    client_idx: int,
    scope_idx: int,
    mu_flag_threshold: float | None,
    repository: str,
    local_epochs: int = 1,
    checkpoint_round: int | None = None,
    injection_rule: CalibrationInjectionRule = (
        CalibrationInjectionRule.REPLACE_FIXED_BUDGET
    ),
    reservoir_mode: str = RESERVOIR_MODE,
) -> RunManifest:
    """Build a RunManifest for one experiment cell.

    mu_flag_threshold may be None only if you intend to update it before any
    poisoned run. Call emit_manifest only after locking mu_flag_threshold.
    """
    record = SeedRecord(
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        client_idx=client_idx,
        scope_idx=scope_idx,
    )
    provenance = ProvenanceRecord(
        local_epochs=local_epochs,
        repository=repository,
        checkpoint_round=checkpoint_round,
    )
    return RunManifest(
        dataset=dataset,
        scale=scale,
        policy=policy,
        objective=objective,
        source=source,
        injection_rule=injection_rule,
        fraction=fraction,
        target_scope=target_scope,
        training_seed=training_seed,
        poisoning_seed=poisoning_seed,
        client_idx=client_idx,
        scope_idx=scope_idx,
        provenance=provenance,
        reservoir_mode=reservoir_mode,
        mu_flag_threshold=mu_flag_threshold,
        seed_record=SeedRecordModel.from_record(record),
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def emit_manifest(manifest: RunManifest, run_dir: Path) -> Path:
    """Write manifest JSON to <run_dir>/run_manifest.json.

    Raises ManifestEmissionError if mu_flag_threshold is None (not yet locked).
    Creates the run_dir if it does not exist.
    """
    if manifest.mu_flag_threshold is None:
        raise ManifestEmissionError(
            "mu_flag_threshold must be locked (non-None) before emitting manifest. "
            "Compute it from clean artifacts and set it first."
        )
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / ManifestFile.RUN_MANIFEST
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_manifest(run_dir: Path) -> RunManifest:
    """Load and validate a manifest from a run directory."""
    path = run_dir / ManifestFile.RUN_MANIFEST
    return RunManifest.model_validate_json(path.read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class RunLogEntry:
    """One record in the JSONL run log.

    Appended after each manifest emission so that an audit trail is maintained
    for all cells run in a session.
    """

    dataset: str
    policy: str
    objective: str
    source: str
    fraction: float
    training_seed: int
    poisoning_seed: int
    mu_flag_threshold: float
    manifest_path: str
    generated_at_utc: str


def write_run_log_entry(entry: RunLogEntry, log_path: Path) -> None:
    """Append one JSON line to the run log at log_path.

    Creates the log file if it does not exist. Each line is a valid JSON object
    so the file can be read line-by-line as JSONL.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "dataset": entry.dataset,
        "policy": entry.policy,
        "objective": entry.objective,
        "source": entry.source,
        "fraction": entry.fraction,
        "training_seed": entry.training_seed,
        "poisoning_seed": entry.poisoning_seed,
        "mu_flag_threshold": entry.mu_flag_threshold,
        "manifest_path": entry.manifest_path,
        "generated_at_utc": entry.generated_at_utc,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
