from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar, cast

from datp.config.stages import ExperimentStage
from datp.core.enums import CONTROLLED_POLICIES
from datp.core.errors import fmt
from datp.thresholding.metrics_serialization import SweepMetrics

_MODULE = "checkpointing.invariants"
_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class ScoreManifestIdentity:
    manifest_path: Path
    checkpoint_round: int
    checkpoint_identity: str
    client_ids: tuple[str, ...]
    split_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CheckpointEvaluationInvariant:
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


def _read_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(
            fmt(
                _MODULE,
                "JSON payload is not an object",
                str(path),
                type(payload).__name__,
            )
        )
    return payload


def _get_required_field(
    payload: dict[str, object], key: str, expected_type: type[_T], _path: Path
) -> _T:
    value = payload.get(key)
    if not isinstance(value, expected_type):
        raise ValueError(
            fmt(
                _MODULE,
                f"Score manifest lacks {key}",
                expected_type.__name__,
                repr(value),
            )
        )
    return cast(_T, value)


def _get_required_str_list(
    payload: dict[str, object], key: str, _path: Path
) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(
            fmt(_MODULE, f"Invalid manifest {key}", "list[str]", repr(value))
        )
    return value


def load_score_manifest_identity(manifest_path: Path) -> ScoreManifestIdentity:
    payload = _read_json_object(manifest_path)
    checkpoint_round = _get_required_field(
        payload, "checkpoint_round", int, manifest_path
    )
    checkpoint_identity = _get_required_field(
        payload, "model_checkpoint_hash", str, manifest_path
    )
    clients = _get_required_str_list(payload, "expected_client_ids", manifest_path)
    splits = _get_required_str_list(payload, "expected_splits", manifest_path)
    return ScoreManifestIdentity(
        manifest_path=manifest_path,
        checkpoint_round=checkpoint_round,
        checkpoint_identity=checkpoint_identity,
        client_ids=tuple(sorted(clients)),
        split_ids=tuple(sorted(splits)),
    )


def load_sweep_metrics(metrics_path: Path) -> SweepMetrics:
    return SweepMetrics.model_validate(_read_json_object(metrics_path))


def _validate_manifest_round(
    manifest: ScoreManifestIdentity,
    checkpoint_round: int,
) -> None:
    if manifest.checkpoint_round != checkpoint_round:
        raise ValueError(
            fmt(
                _MODULE,
                "Mixed-round score manifest",
                f"round {checkpoint_round}",
                f"round {manifest.checkpoint_round}",
            )
        )


def _validate_metrics_cell_identity(
    metrics: SweepMetrics,
    context: _MetricsInvariantContext,
) -> None:
    if metrics.stage != context.stage or metrics.seed != context.seed:
        raise ValueError(
            fmt(
                _MODULE,
                "Metrics cell identity mismatch",
                f"{context.stage}/seed {context.seed}",
                metrics.run_id,
            )
        )
    if metrics.checkpoint_round != context.checkpoint_round:
        raise ValueError(
            fmt(
                _MODULE,
                "Mixed-round metrics",
                f"round {context.checkpoint_round}",
                repr(metrics.checkpoint_round),
            )
        )


def _validate_metrics_policy(
    metrics: SweepMetrics,
    context: _MetricsInvariantContext,
) -> None:
    if metrics.policy not in context.expected_policies:
        raise ValueError(
            fmt(
                _MODULE,
                "Unexpected policy for stage",
                str(sorted(context.expected_policies)),
                metrics.policy.value,
            )
        )


def _validate_metrics_provenance(
    metrics: SweepMetrics,
    context: _MetricsInvariantContext,
    *,
    metrics_path: Path,
) -> None:
    provenance = metrics.provenance
    _check_identity_match(
        provenance.score_artifact_identity,
        context.score_manifest_identity,
        "score manifest",
        str(context.score_manifest_path),
    )
    _check_identity_match(
        provenance.model_checkpoint_identity,
        context.manifest.checkpoint_identity,
        "checkpoint identity",
        metrics_path.name,
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


def _check_identity_match(
    actual: str, expected: str, label: str, _path_hint: str
) -> None:
    if actual != expected:
        raise ValueError(
            fmt(_MODULE, f"Metrics use a different {label}", expected, actual)
        )


def _check_optional_identity(
    actual: str | None, expected: str | None, label: str
) -> None:
    if expected is not None and actual != expected:
        raise ValueError(
            fmt(_MODULE, f"Metrics {label} mismatch", str(expected), str(actual))
        )


def _validate_metrics_clients_and_coverage(
    metrics: SweepMetrics,
    context: _MetricsInvariantContext,
) -> None:
    metric_clients = tuple(sorted(detail.client_id for detail in metrics.per_client))
    if metric_clients != context.manifest.client_ids:
        raise ValueError(
            fmt(
                _MODULE,
                "Metrics client set differs from score manifest",
                str(context.manifest.client_ids),
                str(metric_clients),
            )
        )
    if metrics.coverage_ratio < context.min_coverage_ratio:
        raise ValueError(
            fmt(
                _MODULE,
                "Coverage ratio below invariant floor",
                str(context.min_coverage_ratio),
                str(metrics.coverage_ratio),
            )
        )


def _validate_metrics_file(
    metrics_path: Path,
    context: _MetricsInvariantContext,
) -> SweepMetrics:
    metrics = load_sweep_metrics(metrics_path)
    _validate_metrics_cell_identity(metrics, context)
    _validate_metrics_policy(metrics, context)
    _validate_metrics_provenance(
        metrics,
        context,
        metrics_path=metrics_path,
    )
    _validate_metrics_clients_and_coverage(metrics, context)
    return metrics


@dataclass(frozen=True, slots=True)
class CheckpointValidationConfig:
    """Fixed metadata for a checkpoint evaluation invariant check.

    Bundles stage, seed, checkpoint round, identity hashes, and coverage
    floor — the parameters that are shared across all policy metrics files
    for one training seed.
    """

    stage: ExperimentStage
    seed: int
    checkpoint_round: int
    score_manifest_path: Path
    config_identity: str | None
    split_manifest_identity: str | None
    min_coverage_ratio: float


def validate_checkpoint_evaluation_invariants(
    config: CheckpointValidationConfig,
    *,
    metrics_paths: tuple[Path, ...],
) -> CheckpointEvaluationInvariant:
    if not metrics_paths:
        raise ValueError(
            fmt(
                _MODULE,
                "No metrics paths provided",
                "at least one metrics.json",
                "empty",
            )
        )
    manifest = load_score_manifest_identity(config.score_manifest_path)
    _validate_manifest_round(manifest, config.checkpoint_round)

    context = _MetricsInvariantContext(
        stage=config.stage,
        seed=config.seed,
        checkpoint_round=config.checkpoint_round,
        score_manifest_path=config.score_manifest_path,
        score_manifest_identity=_hash_file(config.score_manifest_path),
        manifest=manifest,
        expected_policies=set(CONTROLLED_POLICIES),
        config_identity=config.config_identity,
        split_manifest_identity=config.split_manifest_identity,
        min_coverage_ratio=config.min_coverage_ratio,
    )
    seen: list[ThresholdPolicy] = []
    coverage_values: list[float] = []
    for metrics_path in metrics_paths:
        metrics = _validate_metrics_file(metrics_path, context)
        seen.append(metrics.policy)
        coverage_values.append(metrics.coverage_ratio)

    return CheckpointEvaluationInvariant(
        stage=config.stage,
        seed=config.seed,
        checkpoint_round=config.checkpoint_round,
        policies=tuple(sorted(seen)),
        score_manifest_identity=context.score_manifest_identity,
        checkpoint_identity=manifest.checkpoint_identity,
        client_ids=manifest.client_ids,
        split_ids=manifest.split_ids,
        coverage_ratio=min(coverage_values),
    )


def _hash_file(path: Path) -> str:
    from datp.core.provenance import hash_file

    return hash_file(path)
