"""Sensitivity manifest: cluster stability, scale normalization, and distinct-draw rows."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datp.attacks.enums import AttackerObjective, PoisoningSourceStrategy, ReservoirDraw
from datp.attacks.manifests.bounded_sweep_manifest import NanFloat
from datp.attacks.manifests.run_manifest import ProvenanceRecord
from datp.core.enums import ThresholdPolicy


class _SensitivityRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    training_seed: int
    victim_id: str
    source: PoisoningSourceStrategy
    objective: AttackerObjective
    fraction: float


class ClusterStabilityRow(_SensitivityRow):
    """Cluster-policy victim effect and assignment transitions for one K, init, and seed setting."""

    k: int
    n_init: int
    random_state: int
    victim_delta_tau: NanFloat
    fixed_victim_delta_tau: NanFloat
    victim_size_clean: int
    victim_size_poisoned: int
    n_reassigned: int
    silhouette_clean: NanFloat
    silhouette_poisoned: NanFloat
    sizes_clean: tuple[int, ...]
    sizes_poisoned: tuple[int, ...]


class ScaleNormalizationRow(_SensitivityRow):
    """Raw versus scale-normalized GLOBAL_THRESHOLD effect and clean per-client scale dispersion."""

    tau_local_cv_clean: NanFloat
    tau_local_max_min_ratio_clean: NanFloat
    score_scale_cv_clean: NanFloat
    raw_global_victim_delta_tau: NanFloat
    normalized_global_victim_delta_tau: NanFloat
    raw_global_victim_delta_fpr: NanFloat
    normalized_global_victim_delta_fpr: NanFloat
    raw_global_cv_fpr_clean: NanFloat
    normalized_global_cv_fpr_clean: NanFloat
    raw_global_cv_fpr_poisoned: NanFloat
    normalized_global_cv_fpr_poisoned: NanFloat


class DrawVariantRow(_SensitivityRow):
    """Threshold shift under an alternative draw mode versus the with-replacement baseline."""

    policy: ThresholdPolicy
    draw: ReservoirDraw
    requested_n_replaced: int
    effective_n_replaced: int
    pool_size: int
    delta_tau_with_replacement: NanFloat
    delta_tau_variant: NanFloat
    duplicate_rate_with_replacement: NanFloat
    duplicate_rate_variant: NanFloat


class TrustBoundaryRow(_SensitivityRow):
    """Score-buffer attack versus trimmed-calibration defenses and a direct threshold-overwrite reference."""

    policy: ThresholdPolicy
    delta_tau_undefended: NanFloat
    delta_tau_trim_primary: NanFloat
    delta_tau_trim_appendix: NanFloat
    residual_vs_clean_trim_primary: NanFloat
    residual_vs_clean_trim_appendix: NanFloat
    overwrite_reference_shift: NanFloat
    buffer_to_overwrite_ratio: NanFloat


class SensitivityManifest(BaseModel):
    """Top-level sensitivity manifest with provenance and result rows."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1"
    generated_at_utc: str
    provenance: ProvenanceRecord
    config_hash: str
    cluster_stability: tuple[ClusterStabilityRow, ...]
    scale_normalization: tuple[ScaleNormalizationRow, ...]
    draw_variants: tuple[DrawVariantRow, ...]
    trust_boundary: tuple[TrustBoundaryRow, ...]
