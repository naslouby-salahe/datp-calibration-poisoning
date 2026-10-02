from __future__ import annotations

from datp.types import (
    ClassificationScore,
    ClientId,
    ContentHash,
    FalsePositiveRate,
    ManifestMetricValue,
    NarrativeText,
    PoisonFraction,
    RandomSeed,
    Ratio,
    SampleCount,
    SchemaVersion,
    ScoreValue,
    SignedCount,
    SignedDelta,
    Threshold,
    TruePositiveRate,
)


from pydantic import BaseModel, ConfigDict, model_validator

from datp.attacks.constants import ANALYSIS_SEEDS, POISONING_SEEDS, TRAINING_SEEDS
from datp.attacks.enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    ManifestProvenanceSource,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
    ReservoirMode,
)
from datp.attacks.manifests.run_manifest import ProvenanceRecord
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.seeds import SeedRecord
from datp.data.catalog import DatasetID


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
            raise ValueError("bounded-sweep reporting requires training seeds 0..9")
        if self.poisoning_seeds != POISONING_SEEDS:
            raise ValueError(
                "bounded-sweep reporting requires poisoning seeds 100..109"
            )
        if self.analysis_seeds != ANALYSIS_SEEDS:
            raise ValueError("bounded-sweep reporting requires analysis seeds 300..309")

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
