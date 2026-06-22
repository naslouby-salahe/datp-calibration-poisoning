from __future__ import annotations

import enum


class DatasetID(enum.StrEnum):
    NBAIOT = "nbaiot"
    CICIOT2023 = "ciciot2023"


class ThresholdPolicy(enum.StrEnum):
    """Canonical threshold policies for datp-cp."""

    GLOBAL_THRESHOLD = "global_threshold"
    LOCAL_THRESHOLD = "local_threshold"
    CLUSTER_THRESHOLD = "cluster_threshold"


class ClientIdentity(enum.StrEnum):
    DEVICE_DIRECTORY = "device_directory"
    MERGED_FILE = "merged_file"
    VICTIM_MAC = "victim_mac"
    VIRTUAL_CLIENT = "virtual_client"


class DeviceType(enum.StrEnum):
    """Torch device types — canonical enum for all device resolution."""

    CUDA = "cuda"
    CPU = "cpu"


class ClientStatus(enum.StrEnum):
    ELIGIBLE = "eligible"
    CALIBRATION_PENDING = "calibration_pending"


class ThresholdAggregationMethod(enum.StrEnum):
    ELIGIBLE_CLIENT_ARITHMETIC_MEAN = "eligible_client_arithmetic_mean"
    PER_CLIENT_PERCENTILE = "per_client_percentile"
    ELIGIBLE_CLUSTER_ARITHMETIC_MEAN = "eligible_cluster_arithmetic_mean"


class ThresholdSource(enum.StrEnum):
    """Identifies the calibration scope for a threshold.

    These are internal routing tags for threshold result objects. The values
    use compact shorthand (``"global"``, ``"local"``, ``"cluster"``) distinct
    from the canonical policy enum string values. TAU_GLOBAL_FALLBACK is an
    internal fallback tag, not a threshold policy.
    """

    GLOBAL = "global"
    LOCAL = "local"
    CLUSTER = "cluster"
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


# Derived maps — do not duplicate in other modules; import from here.

MAIN_BODY_POLICIES: frozenset[ThresholdPolicy] = frozenset(
    {
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    }
)

THRESHOLD_AGGREGATION_BY_POLICY: dict[ThresholdPolicy, ThresholdAggregationMethod] = {
    ThresholdPolicy.GLOBAL_THRESHOLD: ThresholdAggregationMethod.ELIGIBLE_CLIENT_ARITHMETIC_MEAN,
    ThresholdPolicy.LOCAL_THRESHOLD: ThresholdAggregationMethod.PER_CLIENT_PERCENTILE,
    ThresholdPolicy.CLUSTER_THRESHOLD: ThresholdAggregationMethod.ELIGIBLE_CLUSTER_ARITHMETIC_MEAN,
}

POLICY_THRESHOLD_SOURCE: dict[ThresholdPolicy, ThresholdSource] = {
    ThresholdPolicy.GLOBAL_THRESHOLD: ThresholdSource.GLOBAL,
    ThresholdPolicy.LOCAL_THRESHOLD: ThresholdSource.LOCAL,
    ThresholdPolicy.CLUSTER_THRESHOLD: ThresholdSource.CLUSTER,
}

# Threshold ladder — the three controlled policies being compared.
CONTROLLED_POLICIES: tuple[ThresholdPolicy, ...] = (
    ThresholdPolicy.GLOBAL_THRESHOLD,
    ThresholdPolicy.LOCAL_THRESHOLD,
    ThresholdPolicy.CLUSTER_THRESHOLD,
)

# Cluster fingerprint feature order: locked per scientific contract.
# Locked per scientific protocol — do not reorder.
CLUSTER_FINGERPRINT_FEATURES: tuple[str, ...] = ("mean", "std", "skew", "p95")


class RunKind(enum.StrEnum):
    CORE_LADDER = "core_ladder"


class SeedScope(enum.StrEnum):
    """Which seeds a figure or result covers."""

    REPRESENTATIVE_SEED = "representative_seed"
    ALL_SEEDS = "all_seeds"
