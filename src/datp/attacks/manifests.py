from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from datp.config import ANALYSIS_SEEDS, POISONING_SEEDS, TRAINING_SEEDS, ExperimentStage
from datp.core import SeedRecord, git_commit
from datp.enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    DatasetID,
    ManifestProvenanceSource,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ReservoirDraw,
    ReservoirMode,
    SplitSemantics,
    ThresholdPolicy,
)
from datp.types import (
    ClassificationScore,
    ClientId,
    ClusterCount,
    ContentHash,
    FalsePositiveRate,
    IterationCount,
    ManifestMetricValue,
    NarrativeText,
    PoisonFraction,
    RandomSeed,
    Ratio,
    RepositoryName,
    RoundCount,
    SampleCount,
    SchemaVersion,
    ScoreValue,
    SignedCount,
    SignedDelta,
    Threshold,
    TruePositiveRate,
)


class ProvenanceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    local_epochs: RoundCount
    pipeline_generated: bool = True
    repository: RepositoryName
    code_commit: NarrativeText = Field(default_factory=git_commit)
    split_semantics: SplitSemantics = (
        SplitSemantics.CHRONOLOGICAL_BENIGN_ONLY_60_1_20_1_18
    )

    @field_validator("local_epochs")
    @classmethod
    def enforce_e1(cls, v: RoundCount) -> RoundCount:
        if v != 1:
            raise ValueError(
                f"provenance.local_epochs must be 1; got {v} — E={v} rejected"
            )
        return v


class BoundedSweepResultRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy: ThresholdPolicy
    source: PoisoningSourceStrategy
    objective: AttackerObjective
    fraction: PoisonFraction
    target_scope: PoisoningTargetScope
    victim_id: ClientId
    training_seed: RandomSeed
    poisoning_seed: RandomSeed
    seed_record: SeedRecord

    delta_tau: SignedDelta
    delta_tau_rel: SignedDelta
    is_victim_significant: bool

    cv_fpr_clean: ManifestMetricValue
    cv_fpr_poisoned: ManifestMetricValue
    delta_cv_fpr: ManifestMetricValue
    mean_fpr_clean: ManifestMetricValue
    mean_fpr_poisoned: ManifestMetricValue
    delta_mean_fpr: ManifestMetricValue
    iqr_fpr_clean: ManifestMetricValue
    iqr_fpr_poisoned: ManifestMetricValue
    delta_iqr_fpr: ManifestMetricValue
    max_min_fpr_clean: ManifestMetricValue
    max_min_fpr_poisoned: ManifestMetricValue
    delta_max_min_fpr: ManifestMetricValue
    worst_client_fpr_clean: ManifestMetricValue
    worst_client_fpr_poisoned: ManifestMetricValue
    delta_worst_client_fpr: ManifestMetricValue

    coverage_ratio: Ratio
    n_eligible: SampleCount
    mu_flag_triggered: bool
    auroc_invariant: bool
    blast_fraction: PoisonFraction
    n_blast_significant: SampleCount
    n_spillover: SampleCount
    n_non_victims: SampleCount

    victim_tpr_clean: TruePositiveRate
    victim_tpr_poisoned: TruePositiveRate
    victim_delta_tpr: SignedDelta
    victim_ba_clean: ScoreValue
    victim_ba_poisoned: ScoreValue
    victim_delta_ba: SignedDelta
    victim_macro_f1_clean: ClassificationScore
    victim_macro_f1_poisoned: ClassificationScore
    victim_delta_macro_f1: SignedDelta

    cluster_delta_tau_agg: ManifestMetricValue
    cluster_delta_tau_churn: ManifestMetricValue
    cluster_delta_tau_frozen_scaler: ManifestMetricValue
    cluster_delta_tau_normalization_gap: ManifestMetricValue
    cluster_victim_effect: ManifestMetricValue
    cluster_non_victim_effect: ManifestMetricValue

    victim_fpr_clean: FalsePositiveRate
    victim_fpr_poisoned: FalsePositiveRate
    victim_delta_fpr: SignedDelta
    victim_fp_clean: SignedCount
    victim_fp_poisoned: SignedCount
    victim_fn_clean: SignedCount
    victim_fn_poisoned: SignedCount
    victim_n_test_benign: SignedCount
    victim_n_test_attack: SignedCount

    nonvictim_mean_tpr_clean: ManifestMetricValue
    nonvictim_mean_tpr_poisoned: ManifestMetricValue
    nonvictim_mean_delta_tpr: ManifestMetricValue
    nonvictim_worst_delta_tpr: ManifestMetricValue
    nonvictim_mean_fpr_clean: ManifestMetricValue
    nonvictim_mean_fpr_poisoned: ManifestMetricValue
    nonvictim_mean_delta_fpr: ManifestMetricValue
    nonvictim_worst_delta_fpr: ManifestMetricValue
    nonvictim_mean_delta_ba: ManifestMetricValue
    nonvictim_mean_delta_macro_f1: ManifestMetricValue
    nonvictim_delta_fp_total: SignedCount
    nonvictim_delta_fn_total: SignedCount

    victim_delta_tau_scale_base: ManifestMetricValue
    iqr_median_clean: ManifestMetricValue
    delta_tau_bound_utilization: ManifestMetricValue

    n_replaced: SampleCount
    reservoir_draw: ReservoirDraw = ReservoirDraw.WITH_REPLACEMENT
    donor_feature_unique_fraction: ManifestMetricValue | None = None
    cal_duplicate_rate_clean: ManifestMetricValue
    cal_duplicate_rate_poisoned: ManifestMetricValue

    cluster_sizes_clean: tuple[SignedCount, ...]
    cluster_sizes_poisoned: tuple[SignedCount, ...]
    cluster_victim_size_clean: ManifestMetricValue
    cluster_victim_size_poisoned: ManifestMetricValue
    cluster_n_reassigned: ManifestMetricValue
    cluster_silhouette_clean: ManifestMetricValue
    cluster_silhouette_poisoned: ManifestMetricValue

    fixed_cluster_victim_delta_tau: ManifestMetricValue
    fixed_cluster_victim_delta_tpr: ManifestMetricValue
    fixed_cluster_victim_delta_fpr: ManifestMetricValue
    fixed_cluster_delta_cv_fpr: ManifestMetricValue
    fixed_cluster_delta_mean_fpr: ManifestMetricValue
    fixed_cluster_nonvictim_mean_delta_tpr: ManifestMetricValue
    fixed_cluster_nonvictim_mean_delta_fpr: ManifestMetricValue


class ArtifactProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: ManifestProvenanceSource


class BoundedSweepManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: SchemaVersion = "2"
    generated_at_utc: NarrativeText
    dataset: DatasetID = DatasetID.NBAIOT
    stage: ExperimentStage = ExperimentStage.NBAIOT_MAIN
    injection_rule: CalibrationInjectionRule = (
        CalibrationInjectionRule.REPLACE_FIXED_BUDGET
    )
    target_scope: PoisoningTargetScope = PoisoningTargetScope.SINGLE_CLIENT
    reservoir_mode: ReservoirMode = (
        ReservoirMode.VICTIM_LOCAL_BENIGN_CAL_SOURCE_PRECEDENCE_RULE_2
    )
    provenance: ProvenanceRecord

    policies: tuple[ThresholdPolicy, ...]
    sources: tuple[PoisoningSourceStrategy, ...]
    source_objective_pairs: tuple[NarrativeText, ...]
    fractions: tuple[PoisonFraction, ...]
    training_seeds: tuple[RandomSeed, ...]
    poisoning_seeds: tuple[RandomSeed, ...]
    analysis_seeds: tuple[RandomSeed, ...]
    config_hash: ContentHash
    artifact_provenance: ArtifactProvenance

    mu_flag_threshold_by_training_seed: dict[RandomSeed, Threshold]

    n_cells: SampleCount
    results: tuple[BoundedSweepResultRow, ...]

    @model_validator(mode="after")
    def _check_consistency(self) -> BoundedSweepManifest:
        if self.training_seeds != TRAINING_SEEDS:
            raise ValueError("bounded-sweep reporting requires training seeds 0..19")
        if self.poisoning_seeds != POISONING_SEEDS:
            raise ValueError(
                "bounded-sweep reporting requires poisoning seeds 100..119"
            )
        if self.analysis_seeds != ANALYSIS_SEEDS:
            raise ValueError("bounded-sweep reporting requires analysis seeds 300..319")

        if len(self.training_seeds) != len(self.poisoning_seeds):
            raise ValueError("training_seeds and poisoning_seeds must be paired 1:1")
        if len(self.training_seeds) != len(self.analysis_seeds):
            raise ValueError("training_seeds and analysis_seeds must be paired 1:1")

        if len(self.results) != self.n_cells:
            raise ValueError(
                f"n_cells={self.n_cells} does not match len(results)={len(self.results)}"
            )

        if set(self.mu_flag_threshold_by_training_seed) != set(self.training_seeds):
            raise ValueError(
                "mu_flag_threshold_by_training_seed must have exactly one entry per training seed"
            )

        return self


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
