from __future__ import annotations

from datp.types import (
    ClientId,
    ClusterCount,
    ContentHash,
    IterationCount,
    ManifestMetricValue,
    NarrativeText,
    PoisonFraction,
    RandomSeed,
    SampleCount,
    SchemaVersion,
    SignedCount,
)


from pydantic import BaseModel, ConfigDict

from datp.attacks.enums import AttackerObjective, PoisoningSourceStrategy, ReservoirDraw
from datp.attacks.manifests.run_manifest import ProvenanceRecord
from datp.core.enums import ThresholdPolicy


class _SensitivityRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    training_seed: RandomSeed
    victim_id: ClientId
    source: PoisoningSourceStrategy
    objective: AttackerObjective
    fraction: PoisonFraction


class ClusterStabilityRow(_SensitivityRow):

    k: ClusterCount
    n_init: IterationCount
    random_state: RandomSeed
    victim_delta_tau: ManifestMetricValue
    fixed_victim_delta_tau: ManifestMetricValue
    victim_size_clean: SignedCount
    victim_size_poisoned: SignedCount
    n_reassigned: SampleCount
    silhouette_clean: ManifestMetricValue
    silhouette_poisoned: ManifestMetricValue
    sizes_clean: tuple[SignedCount, ...]
    sizes_poisoned: tuple[SignedCount, ...]


class ScaleNormalizationRow(_SensitivityRow):

    tau_local_cv_clean: ManifestMetricValue
    tau_local_max_min_ratio_clean: ManifestMetricValue
    score_scale_cv_clean: ManifestMetricValue
    raw_global_victim_delta_tau: ManifestMetricValue
    normalized_global_victim_delta_tau: ManifestMetricValue
    raw_global_victim_delta_fpr: ManifestMetricValue
    normalized_global_victim_delta_fpr: ManifestMetricValue
    raw_global_cv_fpr_clean: ManifestMetricValue
    normalized_global_cv_fpr_clean: ManifestMetricValue
    raw_global_cv_fpr_poisoned: ManifestMetricValue
    normalized_global_cv_fpr_poisoned: ManifestMetricValue


class DrawVariantRow(_SensitivityRow):

    policy: ThresholdPolicy
    draw: ReservoirDraw
    requested_n_replaced: SignedCount
    effective_n_replaced: SignedCount
    pool_size: SignedCount
    delta_tau_with_replacement: ManifestMetricValue
    delta_tau_variant: ManifestMetricValue
    duplicate_rate_with_replacement: ManifestMetricValue
    duplicate_rate_variant: ManifestMetricValue


class TrustBoundaryRow(_SensitivityRow):

    policy: ThresholdPolicy
    delta_tau_undefended: ManifestMetricValue
    delta_tau_trim_primary: ManifestMetricValue
    delta_tau_trim_appendix: ManifestMetricValue
    residual_vs_clean_trim_primary: ManifestMetricValue
    residual_vs_clean_trim_appendix: ManifestMetricValue
    overwrite_reference_shift: ManifestMetricValue
    buffer_to_overwrite_ratio: ManifestMetricValue


class SensitivityManifest(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: SchemaVersion = "1"
    generated_at_utc: NarrativeText
    provenance: ProvenanceRecord
    config_hash: ContentHash
    cluster_stability: tuple[ClusterStabilityRow, ...]
    scale_normalization: tuple[ScaleNormalizationRow, ...]
    draw_variants: tuple[DrawVariantRow, ...]
    trust_boundary: tuple[TrustBoundaryRow, ...]
