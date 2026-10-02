from __future__ import annotations

from datp.types import (
    ClientId,
    ContentHash,
    NarrativeText,
    RandomSeed,
    Ratio,
    RoundIndex,
)


from dataclasses import dataclass
from pathlib import Path

from datp.config.models import ExperimentStage
from datp.core.enums import CONTROLLED_POLICIES, ScoringStage, ThresholdPolicy
from datp.core.provenance import hash_file
from datp.scoring.manifest import ScoringManifestIdentityFields
from datp.thresholding.metrics_serialization import SweepMetrics

_MODULE = "checkpointing.invariants"
@dataclass(frozen=True, slots=True)
class ScoreManifestIdentity:

    manifest_path: Path
    checkpoint_round: RoundIndex
    checkpoint_identity: ContentHash
    client_ids: tuple[ClientId, ...]
    split_ids: tuple[ScoringStage, ...]


@dataclass(frozen=True, slots=True)
class CheckpointEvaluationInvariant:

    stage: ExperimentStage
    seed: RandomSeed
    checkpoint_round: RoundIndex
    policies: tuple[ThresholdPolicy, ...]
    score_manifest_identity: ContentHash
    checkpoint_identity: ContentHash
    client_ids: tuple[ClientId, ...]
    split_ids: tuple[ScoringStage, ...]
    coverage_ratio: Ratio


@dataclass(frozen=True, slots=True)
class _MetricsInvariantContext:

    stage: ExperimentStage
    seed: RandomSeed
    checkpoint_round: RoundIndex
    score_manifest_path: Path
    score_manifest_identity: ContentHash
    manifest: ScoreManifestIdentity
    expected_policies: set[ThresholdPolicy]
    config_identity: ContentHash | None
    split_manifest_identity: ContentHash | None
    min_coverage_ratio: Ratio


@dataclass(frozen=True, slots=True)
class CheckpointValidationConfig:

    stage: ExperimentStage
    seed: RandomSeed
    checkpoint_round: RoundIndex
    score_manifest_path: Path
    config_identity: ContentHash | None
    split_manifest_identity: ContentHash | None
    min_coverage_ratio: Ratio


def load_score_manifest_identity(manifest_path: Path) -> ScoreManifestIdentity:
    manifest = ScoringManifestIdentityFields.model_validate_json(
        manifest_path.read_text()
    )
    return ScoreManifestIdentity(
        manifest_path=manifest_path,
        checkpoint_round=manifest.checkpoint_round,
        checkpoint_identity=manifest.model_checkpoint_hash,
        client_ids=tuple(sorted(manifest.expected_client_ids)),
        split_ids=tuple(sorted(manifest.expected_splits)),
    )


def load_sweep_metrics(metrics_path: Path) -> SweepMetrics:
    return SweepMetrics.model_validate_json(metrics_path.read_text())


def _validate_manifest_round(
    manifest: ScoreManifestIdentity,
    checkpoint_round: RoundIndex,
) -> None:
    if manifest.checkpoint_round != checkpoint_round:
        raise ValueError(
            f"[{_MODULE}] Mixed-round score manifest. Expected: round {checkpoint_round}. Got: round {manifest.checkpoint_round}."
        )


def _validate_metrics_cell_identity(
    metrics: SweepMetrics,
    context: _MetricsInvariantContext,
) -> None:
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
    if metrics.policy not in context.expected_policies:
        raise ValueError(
            f"[{_MODULE}] Unexpected policy for stage. Expected: {sorted(context.expected_policies)}. Got: {metrics.policy}."
        )


def _check_identity_match(actual: NarrativeText, expected: NarrativeText, label: NarrativeText) -> None:
    if actual != expected:
        raise ValueError(
            f"[{_MODULE}] Metrics use a different {label}. Expected: {expected}. Got: {actual}."
        )


def _check_optional_identity(
    actual: NarrativeText | None, expected: NarrativeText | None, label: NarrativeText
) -> None:
    if expected is not None and actual != expected:
        raise ValueError(
            f"[{_MODULE}] Metrics {label} mismatch. Expected: {expected}. Got: {actual}."
        )


def _validate_metrics_provenance(
    metrics: SweepMetrics,
    context: _MetricsInvariantContext,
) -> None:
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
    metric_clients = tuple(sorted(detail.client_id for detail in metrics.per_client))
    if metric_clients != context.manifest.client_ids:
        raise ValueError(
            f"[{_MODULE}] Metrics client set differs from score manifest. Expected: {context.manifest.client_ids}. Got: {metric_clients}."
        )
    if metrics.coverage_ratio < context.min_coverage_ratio:
        raise ValueError(
            f"[{_MODULE}] Coverage ratio below invariant floor. Expected: {context.min_coverage_ratio}. Got: {metrics.coverage_ratio}."
        )


def _validate_metrics_file(
    metrics_path: Path,
    context: _MetricsInvariantContext,
) -> SweepMetrics:
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
    coverage_values: list[Ratio] = []
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
