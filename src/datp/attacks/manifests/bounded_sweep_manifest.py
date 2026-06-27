"""Bounded-sweep manifest: result rows and sweep-level provenance model."""

from __future__ import annotations

import math
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, model_validator

from datp.attacks.constants import ANALYSIS_SEEDS, POISONING_SEEDS, TRAINING_SEEDS
from datp.attacks.enums import (
    AttackerObjective,
    CalibrationInjectionRule,
    PoisoningSourceStrategy,
    PoisoningTargetScope,
)
from datp.attacks.manifests.run_manifest import RESERVOIR_MODE, ProvenanceRecord
from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy
from datp.core.seeds import SeedRecord
from datp.data.catalog import DatasetID


def _undefined_null_to_nan(value: Any) -> Any:
    """Convert None to NaN for Pydantic field validation."""
    return math.nan if value is None else value


NanFloat = Annotated[float, BeforeValidator(_undefined_null_to_nan)]


class BoundedSweepResultRow(BaseModel):
    """Single row in a bounded-sweep result manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy: ThresholdPolicy
    source: PoisoningSourceStrategy
    objective: AttackerObjective
    fraction: float
    target_scope: PoisoningTargetScope
    victim_id: str
    training_seed: int
    poisoning_seed: int
    seed_record: SeedRecord

    delta_tau: float
    delta_tau_rel: float
    is_victim_significant: bool

    cv_fpr_clean: NanFloat
    cv_fpr_poisoned: NanFloat
    delta_cv_fpr: NanFloat
    mean_fpr_clean: NanFloat
    mean_fpr_poisoned: NanFloat
    delta_mean_fpr: NanFloat
    iqr_fpr_clean: NanFloat
    iqr_fpr_poisoned: NanFloat
    delta_iqr_fpr: NanFloat
    max_min_fpr_clean: NanFloat
    max_min_fpr_poisoned: NanFloat
    delta_max_min_fpr: NanFloat
    worst_client_fpr_clean: NanFloat
    worst_client_fpr_poisoned: NanFloat
    delta_worst_client_fpr: NanFloat

    coverage_ratio: float
    n_eligible: int
    mu_flag_triggered: bool
    auroc_invariant: bool
    blast_fraction: float
    n_blast_significant: int
    n_spillover: int
    n_non_victims: int

    victim_tpr_clean: float
    victim_tpr_poisoned: float
    victim_delta_tpr: float
    victim_ba_clean: float
    victim_ba_poisoned: float
    victim_delta_ba: float
    victim_macro_f1_clean: float
    victim_macro_f1_poisoned: float
    victim_delta_macro_f1: float

    cluster_delta_tau_agg: NanFloat
    cluster_delta_tau_churn: NanFloat
    cluster_delta_tau_frozen_scaler: NanFloat
    cluster_delta_tau_normalization_gap: NanFloat
    cluster_victim_effect: NanFloat
    cluster_non_victim_effect: NanFloat


class BoundedSweepManifest(BaseModel):
    """Top-level bounded-sweep manifest with provenance, sweep axes, and result rows."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1"
    generated_at_utc: str
    dataset: DatasetID = DatasetID.NBAIOT
    stage: ExperimentStage = ExperimentStage.NBAIOT_MAIN
    injection_rule: CalibrationInjectionRule = (
        CalibrationInjectionRule.REPLACE_FIXED_BUDGET
    )
    target_scope: PoisoningTargetScope = PoisoningTargetScope.SINGLE_CLIENT
    reservoir_mode: str = RESERVOIR_MODE
    provenance: ProvenanceRecord

    policies: tuple[ThresholdPolicy, ...]
    sources: tuple[PoisoningSourceStrategy, ...]
    source_objective_pairs: tuple[str, ...]
    fractions: tuple[float, ...]
    training_seeds: tuple[int, ...]
    poisoning_seeds: tuple[int, ...]
    analysis_seeds: tuple[int, ...]
    config_hash: str
    artifact_provenance: dict[str, str]

    mu_flag_threshold_by_training_seed: dict[int, float]

    n_cells: int
    results: tuple[BoundedSweepResultRow, ...]

    @model_validator(mode="after")
    def _check_consistency(self) -> BoundedSweepManifest:
        """Validate seed tuples and result-count consistency."""
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
