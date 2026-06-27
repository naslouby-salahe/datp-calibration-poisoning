"""Checkpoint evaluation invariant types and payload parsing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar, cast

from datp.config.models import ExperimentStage
from datp.core.enums import CONTROLLED_POLICIES, ThresholdPolicy
from datp.core.provenance import hash_file
from datp.thresholding.metrics_serialization import SweepMetrics

_MODULE = "checkpointing.invariants"
_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class ScoreManifestIdentity:
    """Parsed identity fields from a score manifest."""

    manifest_path: Path
    checkpoint_round: int
    checkpoint_identity: str
    client_ids: tuple[str, ...]
    split_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CheckpointEvaluationInvariant:
    """Verified invariant snapshot after evaluating a checkpoint across policies."""

    stage: ExperimentStage
    seed: int
    checkpoint_round: int
    policies: tuple[ThresholdPolicy, ...]
    score_manifest_identity: str
    checkpoint_identity: str
    client_ids: tuple[str, ...]
    split_ids: tuple[str, ...]
    coverage_ratio: float


@dataclass(frozen=True, slots=True)
class _MetricsInvariantContext:
    """Internal context bundle for metrics invariant validation."""

    stage: ExperimentStage
    seed: int
    checkpoint_round: int
    score_manifest_path: Path
    score_manifest_identity: str
    manifest: ScoreManifestIdentity
    expected_policies: set[ThresholdPolicy]
    config_identity: str | None
    split_manifest_identity: str | None
    min_coverage_ratio: float


@dataclass(frozen=True, slots=True)
class CheckpointValidationConfig:
    """Input configuration for checkpoint evaluation invariant validation."""

    stage: ExperimentStage
    seed: int
    checkpoint_round: int
    score_manifest_path: Path
    config_identity: str | None
    split_manifest_identity: str | None
    min_coverage_ratio: float


def _read_json_object(path: Path) -> dict[str, object]:
    """Read and validate a JSON file as a dict object."""
    payload: object = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(
            f"[{_MODULE}] JSON payload is not an object. Expected: {str(path)}. Got: {type(payload).__name__}."
        )
    return cast(dict[str, object], payload)


def _get_required_field(
    payload: dict[str, object], key: str, expected_type: type[_T]
) -> _T:
    """Extract a required typed field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, expected_type):
        raise ValueError(
            f"[{_MODULE}] Score manifest lacks {key}. Expected: {expected_type.__name__}. Got: {repr(value)}."
        )
    return cast(_T, value)


def _get_required_str_list(payload: dict[str, object], key: str) -> list[str]:
    """Extract a required list[str] field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(
            f"[{_MODULE}] Invalid manifest {key}. Expected: list[str]. Got: {repr(value)}."
        )
    return value


def load_score_manifest_identity(manifest_path: Path) -> ScoreManifestIdentity:
    """Parse a score manifest JSON file into a ScoreManifestIdentity."""
    payload = _read_json_object(manifest_path)
    checkpoint_round = _get_required_field(payload, "checkpoint_round", int)
    checkpoint_identity = _get_required_field(payload, "model_checkpoint_hash", str)
    clients = _get_required_str_list(payload, "expected_client_ids")
    splits = _get_required_str_list(payload, "expected_splits")
    return ScoreManifestIdentity(
        manifest_path=manifest_path,
        checkpoint_round=checkpoint_round,
        checkpoint_identity=checkpoint_identity,
        client_ids=tuple(sorted(clients)),
        split_ids=tuple(sorted(splits)),
    )


def load_sweep_metrics(metrics_path: Path) -> SweepMetrics:
    """Load and validate sweep metrics from a JSON path."""
    return SweepMetrics.model_validate(_read_json_object(metrics_path))


def _validate_manifest_round(
    manifest: ScoreManifestIdentity,
    checkpoint_round: int,
) -> None:
    """Ensure the manifest round matches the expected checkpoint round."""
    if manifest.checkpoint_round != checkpoint_round:
        raise ValueError(
            f"[{_MODULE}] Mixed-round score manifest. Expected: round {checkpoint_round}. Got: round {manifest.checkpoint_round}."
        )


def _validate_metrics_cell_identity(
    metrics: SweepMetrics,
    context: _MetricsInvariantContext,
) -> None:
    """Ensure metrics stage and seed match the expected context."""
    if metrics.stage != context.stage or metrics.seed != context.seed:
        raise ValueError(
            f"[{_MODULE}] Metrics cell identity mismatch. Expected: {context.stage}/seed {context.seed}. Got: {metrics.run_id}."
        )
    if metrics.checkpoint_round != context.checkpoint_round:
        raise ValueError(
            f"[{_MODULE}] Mixed-round metrics. Expected: round {context.checkpoint_round}. Got: {repr(metrics.checkpoint_round)}."
        )


def _validate_metrics_policy(
    metrics: SweepMetrics,
    context: _MetricsInvariantContext,
) -> None:
    """Ensure the metrics policy is within the expected set."""
    if metrics.policy not in context.expected_policies:
        raise ValueError(
            f"[{_MODULE}] Unexpected policy for stage. Expected: {str(sorted(context.expected_policies))}. Got: {metrics.policy.value}."
        )


def _check_identity_match(actual: str, expected: str, label: str) -> None:
    """Raise if the actual identity does not match the expected one."""
    if actual != expected:
        raise ValueError(
            f"[{_MODULE}] Metrics use a different {label}. Expected: {expected}. Got: {actual}."
        )


def _check_optional_identity(
    actual: str | None, expected: str | None, label: str
) -> None:
    """Raise if an optional identity is present and mismatched."""
    if expected is not None and actual != expected:
        raise ValueError(
            f"[{_MODULE}] Metrics {label} mismatch. Expected: {str(expected)}. Got: {str(actual)}."
        )


def _validate_metrics_provenance(
    metrics: SweepMetrics,
    context: _MetricsInvariantContext,
) -> None:
    """Validate metrics provenance against the invariant context."""
    provenance = metrics.provenance
    _check_identity_match(
        provenance.score_artifact_identity,
        context.score_manifest_identity,
        "score manifest",
    )
    _check_identity_match(
        provenance.model_checkpoint_identity,
        context.manifest.checkpoint_identity,
        "checkpoint identity",
    )
    _check_optional_identity(
        provenance.config_identity,
        context.config_identity,
        "config hash",
    )
    _check_optional_identity(
        provenance.split_manifest_identity,
        context.split_manifest_identity,
        "split manifest hash",
    )


def _validate_metrics_clients_and_coverage(
    metrics: SweepMetrics,
    context: _MetricsInvariantContext,
) -> None:
    """Validate client set and coverage ratio against manifest invariants."""
    metric_clients = tuple(sorted(detail.client_id for detail in metrics.per_client))
    if metric_clients != context.manifest.client_ids:
        raise ValueError(
            f"[{_MODULE}] Metrics client set differs from score manifest. Expected: {str(context.manifest.client_ids)}. Got: {str(metric_clients)}."
        )
    if metrics.coverage_ratio < context.min_coverage_ratio:
        raise ValueError(
            f"[{_MODULE}] Coverage ratio below invariant floor. Expected: {str(context.min_coverage_ratio)}. Got: {str(metrics.coverage_ratio)}."
        )


def _validate_metrics_file(
    metrics_path: Path,
    context: _MetricsInvariantContext,
) -> SweepMetrics:
    """Load and run all invariant checks on a single metrics file."""
    metrics = load_sweep_metrics(metrics_path)
    _validate_metrics_cell_identity(metrics, context)
    _validate_metrics_policy(metrics, context)
    _validate_metrics_provenance(metrics, context)
    _validate_metrics_clients_and_coverage(metrics, context)
    return metrics


def validate_checkpoint_evaluation_invariants(
    config: CheckpointValidationConfig,
    *,
    metrics_paths: tuple[Path, ...],
) -> CheckpointEvaluationInvariant:
    """Validate evaluation invariants across all policy metrics for a checkpoint."""
    if not metrics_paths:
        raise ValueError(
            f"[{_MODULE}] No metrics paths provided. Expected: at least one metrics.json. Got: empty."
        )

    manifest = load_score_manifest_identity(config.score_manifest_path)
    _validate_manifest_round(manifest, config.checkpoint_round)

    context = _MetricsInvariantContext(
        stage=config.stage,
        seed=config.seed,
        checkpoint_round=config.checkpoint_round,
        score_manifest_path=config.score_manifest_path,
        score_manifest_identity=hash_file(config.score_manifest_path),
        manifest=manifest,
        expected_policies=set(CONTROLLED_POLICIES),
        config_identity=config.config_identity,
        split_manifest_identity=config.split_manifest_identity,
        min_coverage_ratio=config.min_coverage_ratio,
    )

    seen_policies: list[ThresholdPolicy] = []
    coverage_values: list[float] = []
    for metrics_path in metrics_paths:
        metrics = _validate_metrics_file(metrics_path, context)
        seen_policies.append(metrics.policy)
        coverage_values.append(metrics.coverage_ratio)

    return CheckpointEvaluationInvariant(
        stage=config.stage,
        seed=config.seed,
        checkpoint_round=config.checkpoint_round,
        policies=tuple(sorted(seen_policies)),
        score_manifest_identity=context.score_manifest_identity,
        checkpoint_identity=manifest.checkpoint_identity,
        client_ids=manifest.client_ids,
        split_ids=manifest.split_ids,
        coverage_ratio=min(coverage_values),
    )
