from __future__ import annotations

import enum


class ConvergenceStatus(enum.StrEnum):
    CONVERGED = "converged"
    NOT_CONVERGED = "not_converged"
    UNKNOWN = "unknown"
    BLOCKED_PENDING_RUN = "BLOCKED_PENDING_RUN"
    MISSING_CHECKPOINT = "MISSING_CHECKPOINT"


class CheckpointProtocolMode(enum.StrEnum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class CheckpointConvergenceMode(enum.StrEnum):
    LOG_ONLY = "log_only"
    EARLY_STOP = "early_stop"


class PrimaryCheckpointSelectionRule(enum.StrEnum):
    GLOBAL_LOWER_TAIL_TRADEOFF_FROM_REGIME_A = (
        "global_lower_tail_tradeoff_from_regime_a"
    )


class CheckpointArtifactPathMode(enum.StrEnum):
    ROUND_AWARE = "round_aware"


class CheckpointArtifactStatus(enum.StrEnum):
    PRESENT = "present"
    MISSING = "missing"
    INVALID = "invalid"
    SUPPRESSED = "suppressed"


class CheckpointSelectionVerdict(enum.StrEnum):
    SELECTED = "selected"
    REJECTED = "rejected"


class ConvergenceSummaryKey(enum.StrEnum):
    """Canonical keys for the convergence summary JSON artifact.

    Shared by the producer (federated/checkpoints.py) and consumer
    (validation/convergence.py).
    """

    ROUNDS_INITIAL = "rounds_initial"
    ROUNDS_MAX = "rounds_max"
    RELATIVE_THRESHOLD = "relative_threshold"
    WINDOW = "window"
    ACTUAL_ROUNDS = "actual_rounds_run"
    CONVERGENCE_ROUND = "convergence_round"
    CONVERGENCE_CRITERION = "convergence_criterion_value"
    CONVERGENCE_STATUS = "convergence_status"
    WEIGHTED_LOSS = "weighted_validation_loss_per_round"


class EvidenceRole(enum.StrEnum):
    """Scientific evidence role for a figure or analysis result."""

    DESCRIPTIVE = "descriptive"
    DESCRIPTIVE_WITH_CONFIRMATORY_SIDECAR_DELTA = (
        "descriptive_with_confirmatory_sidecar_delta"
    )
    SECONDARY = "secondary"
