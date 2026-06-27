"""Checkpoint protocol enums for convergence, selection, and artifact status."""

from __future__ import annotations

import enum


class ConvergenceStatus(enum.StrEnum):
    """Outcome of a convergence check on federated training."""

    CONVERGED = "converged"
    NOT_CONVERGED = "not_converged"
    UNKNOWN = "unknown"
    BLOCKED_PENDING_RUN = "BLOCKED_PENDING_RUN"
    MISSING_CHECKPOINT = "MISSING_CHECKPOINT"


class CheckpointProtocolMode(enum.StrEnum):
    """Toggle for the checkpoint protocol."""

    ENABLED = "enabled"
    DISABLED = "disabled"


class CheckpointConvergenceMode(enum.StrEnum):
    """Behaviour when convergence is detected."""

    LOG_ONLY = "log_only"
    EARLY_STOP = "early_stop"


class PrimaryCheckpointSelectionRule(enum.StrEnum):
    """Rule for selecting the primary global checkpoint."""

    GLOBAL_LOWER_TAIL_TRADEOFF_FROM_NBAIOT_MAIN = (
        "global_lower_tail_tradeoff_from_nbaiot_main"
    )


class CheckpointArtifactPathMode(enum.StrEnum):
    """Path layout mode for checkpoint artifacts."""

    ROUND_AWARE = "round_aware"


class CheckpointArtifactStatus(enum.StrEnum):
    """Filesystem status of a checkpoint artifact."""

    PRESENT = "present"
    MISSING = "missing"
    INVALID = "invalid"
    SUPPRESSED = "suppressed"


class CheckpointSelectionVerdict(enum.StrEnum):
    """Whether a checkpoint was SELECTED or REJECTED by a selection rule."""

    SELECTED = "selected"
    REJECTED = "rejected"


class ConvergenceSummaryKey(enum.StrEnum):
    """Keys shared by checkpoints producer and audit consumer."""

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
    """Evidential role of a metric used during audit and reporting."""

    DESCRIPTIVE = "descriptive"
    DESCRIPTIVE_WITH_CONFIRMATORY_SIDECAR_DELTA = (
        "descriptive_with_confirmatory_sidecar_delta"
    )
    SECONDARY = "secondary"
