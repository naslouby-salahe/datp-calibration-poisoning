"""CLI enumerations: exit codes, command names, column headers, and output keys."""

from enum import IntEnum, StrEnum

from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy


class CliExitCode(IntEnum):
    """CLI process exit codes."""

    SUCCESS = 0
    ERROR = 1


class AuditCommand(StrEnum):
    """Subcommands for the audit CLI group."""

    RESULTS = "results"


class AuditColumn(StrEnum):
    """Column headers for the audit results table."""

    ARTIFACT = "Artifact"
    PATH = "Path"


class CheckpointCommand(StrEnum):
    """Subcommands for the checkpoint-protocol CLI group."""

    PREVIEW = "preview"
    SMOKE = "smoke"
    EVALUATE_FROM_SCORES = "evaluate-from-scores"
    STATUS = "status"
    SUMMARY = "summary"


class _CheckpointSmokeField(StrEnum):
    """JSON keys for the checkpoint smoke test output."""

    ARTIFACT_ROOT = "artifact_root"
    ROUNDS = "rounds"
    SELECTED_ROUND = "selected_round"


class _CheckpointEvalField(StrEnum):
    """JSON keys for the checkpoint evaluate-from-scores output."""

    CHECKPOINT_ROUND = "checkpoint_round"
    POLICIES = "policies"


class _CheckpointStatusField(StrEnum):
    """JSON keys for the checkpoint status output."""

    COMPLETE = "complete"
    CHECKPOINT = "checkpoint"
    SCORES = "scores"
    RESULTS = "results"


class _CheckpointSummaryField(StrEnum):
    """JSON keys for the checkpoint summary output."""

    SELECTED_ROUND = "selected_round"


_SMOKE_TEMP_DIR_PREFIX = "datp_checkpoint_protocol_smoke_"
_ERROR_NOT_CONFIGURED = "checkpoint_protocol is not configured."
_ERROR_MUST_NOT_WRITE_OUTPUTS = "checkpoint protocol smoke must not write to outputs/"
_CHECKPOINT_DEFAULT_STAGE = ExperimentStage.NBAIOT_MAIN
_CHECKPOINT_SUMMARY_POLICIES = (
    ThresholdPolicy.GLOBAL_THRESHOLD,
    ThresholdPolicy.LOCAL_THRESHOLD,
)


class ConfigCommand(StrEnum):
    """Subcommands for the config CLI group."""

    PREVIEW = "preview"


class PoisonCommand(StrEnum):
    """Subcommands for the poison CLI group."""

    PREVIEW = "preview"
    DRY_RUN = "dry-run"
    SMOKE = "smoke"
    RUN_BOUNDED_SWEEP = "run-bounded-sweep"
    STAGES = "stages"


class PoisonOutputKey(StrEnum):
    """JSON keys for poison command output."""

    STAGE = "stage"
    DATASET = "dataset"
    ALLOW_RUN = "allow_run"
    GATE = "gate"
    DESCRIPTION = "description"


_EXECUTION_GATE_NOTICE = (
    "NOTE: Experiment execution is blocked until this stage's own gate "
    "(see below) is authorized. This command is preview/dry-run only."
)


class ReportCommand(StrEnum):
    """Subcommands for the report CLI group."""

    STATS = "stats"
    VALIDATE = "validate"
    FIGURES = "figures"
    TABLES = "tables"
    POISONING = "poisoning"
    ALL = "all"


class StatusColumn(StrEnum):
    """Column headers for the status table."""

    SCOPE = "Scope"
    COMPLETE = "Complete"
    MISSING = "Missing"
    ABORTED = "Aborted"
    TOTAL = "Total"
