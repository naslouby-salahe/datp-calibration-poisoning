from __future__ import annotations

import enum


class DatasetID(enum.StrEnum):
    NBAIOT = "nbaiot"
    CICIOT2023 = "ciciot2023"


class ClientIdentity(enum.StrEnum):
    DEVICE_DIRECTORY = "device_directory"
    MERGED_FILE = "merged_file"
    VICTIM_MAC = "victim_mac"
    VIRTUAL_CLIENT = "virtual_client"


class DeviceType(enum.StrEnum):
    """Torch device types — canonical enum for all device resolution."""

    CUDA = "cuda"
    CPU = "cpu"


class ArtifactFile(enum.StrEnum):
    MODEL_CHECKPOINT = "model.pt"
    DECODER_CHECKPOINT = "decoder.pt"
    MODEL_B0_CHECKPOINT = "model_b0.pt"
    SCORING_SENTINEL = "SCORING_DONE.txt"
    SCORING_MANIFEST = "scoring_manifest.json"
    METRICS = "metrics.json"
    METRICS_TMP = "metrics.json.tmp"
    REPORTING_AUDIT = "reporting_audit.json"
    BOOTSTRAP_CIS_JSON = "bootstrap_cis.json"
    BOOTSTRAP_CIS_CSV = "bootstrap_cis.csv"
    METRICS_SCHEMA_VALIDATION = "metrics_schema_validation.json"
    SCALER = "scaler.pkl"
    MANIFEST = "manifest.json"
    LOG = "datp.log"
    CONVERGENCE_CURVE = "convergence_curve.csv"
    CONVERGENCE_SUMMARY = "convergence_summary.json"
    PARAMS_SNAPSHOT = "params.npz"
    JS_DIVERGENCE = "js_divergence.json"
    RUN_IN_PROGRESS = "IN_PROGRESS"
    RUN_DONE = "DONE.txt"
    RUN_ABORTED = "ABORTED.txt"
    RESOLVED_CONFIG = "resolved_config.yaml"


class PathToken(enum.StrEnum):
    PARQUET_EXT = ".parquet"
    PARQUET_GLOB = "*.parquet"
    CSV_GLOB = "*.csv"
    SEED_PREFIX = "seed_"
    ROUND_PREFIX = "round_"
    ALPHA_PREFIX = "alpha_"
    ALPHA_IID = "alpha_iid"


class Baseline(enum.StrEnum):
    B0 = "b0"
    B1 = "b1"
    B2 = "b2"
    B3 = "b3"
    B4 = "b4"


class Regime(enum.StrEnum):
    A = "a"
    B = "b"
    C = "c"


class ClientStatus(enum.StrEnum):
    ELIGIBLE = "eligible"
    CALIBRATION_PENDING = "calibration_pending"


class BaselineRunStatus(enum.StrEnum):
    """Outcome of a single baseline run within a sweep cell."""

    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


class ThresholdAggregationMethod(enum.StrEnum):
    ELIGIBLE_CLIENT_ARITHMETIC_MEAN = "eligible_client_arithmetic_mean"
    PER_CLIENT_PERCENTILE = "per_client_percentile"
    ELIGIBLE_FAMILY_ARITHMETIC_MEAN = "eligible_family_arithmetic_mean"
    ELIGIBLE_CLUSTER_ARITHMETIC_MEAN = "eligible_cluster_arithmetic_mean"
    POOLED_PERCENTILE = "pooled_percentile"


class ThresholdSource(enum.StrEnum):
    """Identifies the calibration scope for a threshold.

    Values intentionally mirror Baseline names — each baseline has a canonical
    ThresholdSource. See BASELINE_THRESHOLD_SOURCE mapping for the relationship.
    """

    B0_POOLED = "pooled_percentile"
    B1_SHARED = "b1"
    B2_PER_CLIENT = "b2"
    B3_FAMILY = "b3"
    B4_CLUSTER = "b4"
    TAU_GLOBAL_FALLBACK = "tau_global_fallback"


class NormalizationScope(enum.StrEnum):
    GLOBAL = "global"
    PER_CLIENT = "per_client"
    PER_CLIENT_ZSCORE = "per_client_zscore"
    POOLED_ZSCORE = "pooled_zscore"


class PipelineStage(enum.StrEnum):
    PREPARE = "prepare"
    TRAIN = "train"
    SCORE = "score"
    THRESHOLD = "threshold"
    EVALUATE = "evaluate"
    REPORT = "report"


class Activation(enum.StrEnum):
    """Autoencoder activation functions — canonical enum for all model configs."""

    RELU = "relu"
    LEAKY_RELU = "leaky_relu"
    ELU = "elu"
    TANH = "tanh"
    SIGMOID = "sigmoid"


class B0NormalizationMode(enum.StrEnum):
    PER_CLIENT_PREPARED = "per_client_prepared"
    POOLED_ZSCORE = "pooled_zscore"


class B4RegimeAMode(enum.StrEnum):
    """B4 cluster-count selection mode for Regime A.

    FIXED uses the configured ``b4_k_regime_a``; SILHOUETTE selects K via
    silhouette score over the candidate Ks.
    """

    FIXED = "fixed"
    SILHOUETTE = "silhouette"


class BaselineRole(enum.StrEnum):
    CONTROLLED_THRESHOLD = "controlled_threshold"
    CENTRALIZED_REFERENCE = "centralized_reference"


class ScoringStage(enum.StrEnum):
    CAL = "cal"
    TEST_BENIGN = "test_benign"
    TEST_ATTACK = "test_attack"

    @property
    def client_data_attr(self) -> str:
        """Attribute name on ``ClientData`` that holds this stage's tensor."""
        if self == ScoringStage.CAL:
            return "val"
        return self.value

    @classmethod
    def all(cls) -> tuple["ScoringStage", ...]:
        return tuple(cls)


SCORING_STAGES: tuple[ScoringStage, ...] = ScoringStage.all()


class AbsorptionClass(enum.StrEnum):
    """Absorption ratio classification per scientific protocol.

    Ratio = Δ_personalized / Δ_FedAvg where each Δ = CV(FPR)[B1] − CV(FPR)[B2].
    """

    STRONG_RETENTION = "strong_retention"
    PARTIAL = "partial"
    NEAR_FULL = "near_full"


def classify_absorption(
    ratio: float,
    *,
    strong_retention_threshold: float,
    partial_threshold: float,
) -> AbsorptionClass:
    """Classify absorption ratio into the locked categories.

    Thresholds are config-driven — read from
    ``ExperimentConfig.absorption_strong_retention`` and
    ``ExperimentConfig.absorption_partial``. Do not hardcode.
    """
    if ratio >= strong_retention_threshold:
        return AbsorptionClass.STRONG_RETENTION
    if ratio >= partial_threshold:
        return AbsorptionClass.PARTIAL
    return AbsorptionClass.NEAR_FULL





# Derived maps — do not duplicate in other modules; import from here.

REGIME_BASELINES: dict[Regime, frozenset[Baseline]] = {
    Regime.A: frozenset(
        {Baseline.B0, Baseline.B1, Baseline.B2, Baseline.B3, Baseline.B4}
    ),
    Regime.B: frozenset({Baseline.B0, Baseline.B1, Baseline.B2, Baseline.B4}),
    Regime.C: frozenset({Baseline.B1, Baseline.B2, Baseline.B4}),
}

MAIN_BODY_BASELINES: frozenset[Baseline] = frozenset(
    {
        Baseline.B0,
        Baseline.B1,
        Baseline.B2,
        Baseline.B3,
        Baseline.B4,
    }
)

ISOLATED_BASELINES: frozenset[Baseline] = frozenset({Baseline.B0})

THRESHOLD_AGGREGATION_BY_BASELINE: dict[Baseline, ThresholdAggregationMethod] = {
    Baseline.B0: ThresholdAggregationMethod.POOLED_PERCENTILE,
    Baseline.B1: ThresholdAggregationMethod.ELIGIBLE_CLIENT_ARITHMETIC_MEAN,
    Baseline.B2: ThresholdAggregationMethod.PER_CLIENT_PERCENTILE,
    Baseline.B3: ThresholdAggregationMethod.ELIGIBLE_FAMILY_ARITHMETIC_MEAN,
    Baseline.B4: ThresholdAggregationMethod.ELIGIBLE_CLUSTER_ARITHMETIC_MEAN,
}

BASELINE_THRESHOLD_SOURCE: dict[Baseline, ThresholdSource] = {
    Baseline.B0: ThresholdSource.B0_POOLED,
    Baseline.B1: ThresholdSource.B1_SHARED,
    Baseline.B2: ThresholdSource.B2_PER_CLIENT,
    Baseline.B3: ThresholdSource.B3_FAMILY,
    Baseline.B4: ThresholdSource.B4_CLUSTER,
}

BASELINE_ROLE: dict[Baseline, BaselineRole] = {
    Baseline.B0: BaselineRole.CENTRALIZED_REFERENCE,
    Baseline.B1: BaselineRole.CONTROLLED_THRESHOLD,
    Baseline.B2: BaselineRole.CONTROLLED_THRESHOLD,
    Baseline.B3: BaselineRole.CONTROLLED_THRESHOLD,
    Baseline.B4: BaselineRole.CONTROLLED_THRESHOLD,
}

# Threshold ladder — the four controlled baselines being compared.
# B0 is a centralized reference, not part of the ladder.
# B5 is a local-only ablation, not part of the ladder.
CONTROLLED_BASELINES: tuple[Baseline, ...] = (
    Baseline.B1,
    Baseline.B2,
    Baseline.B3,
    Baseline.B4,
)

# B4 fingerprint feature order: locked per scientific contract.
# Locked per scientific protocol — do not reorder.
B4_FINGERPRINT_FEATURES: tuple[str, ...] = ("mean", "std", "skew", "p95")


class RunKind(enum.StrEnum):
    CORE_LADDER = "core_ladder"
    STRESS_TEST = "stress_test"
    CENTRALIZED_REFERENCE = "centralized_reference"
    COMPARATOR = "comparator"


def controlled_baselines_for_regime(regime: Regime) -> tuple[Baseline, ...]:
    """Return controlled threshold-ladder baselines for a regime.

    B3 (family threshold) applies only in Regime A (N-BaIoT device families).
    """
    if regime == Regime.A:
        return CONTROLLED_BASELINES
    return tuple(b for b in CONTROLLED_BASELINES if b != Baseline.B3)


class SeedScope(enum.StrEnum):
    """Which seeds a figure or result covers."""

    REPRESENTATIVE_SEED = "representative_seed"
    ALL_SEED = "all_seed"


# Baselines used for statistical comparisons per regime.
# Excludes isolated B0; excludes B3 in Regime A (family threshold, not part of the
# causal B1/B2/B4 ladder comparisons).
STATS_REPORTING_BASELINES: dict[Regime, frozenset[Baseline]] = {
    Regime.A: REGIME_BASELINES[Regime.A] - ISOLATED_BASELINES - {Baseline.B3},
    Regime.B: REGIME_BASELINES[Regime.B] - ISOLATED_BASELINES,
    Regime.C: REGIME_BASELINES[Regime.C] - ISOLATED_BASELINES,
}
