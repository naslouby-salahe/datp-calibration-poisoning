
from collections.abc import Sequence
from enum import IntEnum, StrEnum

from datp.config.models import ExperimentStage
from datp.core.enums import ThresholdPolicy


class CliExitCode(IntEnum):

    SUCCESS = 0
    ERROR = 1


class CliCommand(StrEnum):

    AUDIT_RESULTS = "audit results"
    AUDIT_REUSE = "audit reuse"
    CHECKPOINT_PREVIEW = "checkpoint-protocol preview"
    CHECKPOINT_SMOKE = "checkpoint-protocol smoke"
    CHECKPOINT_EVALUATE_FROM_SCORES = "checkpoint-protocol evaluate-from-scores"
    CHECKPOINT_STATUS = "checkpoint-protocol status"
    CHECKPOINT_SUMMARY = "checkpoint-protocol summary"
    CONFIG_PREVIEW = "config preview"
    POISON_PREVIEW = "poison preview"
    POISON_DRY_RUN = "poison dry-run"
    POISON_SMOKE = "poison smoke"
    POISON_RUN_BOUNDED_SWEEP = "poison run-bounded-sweep"
    POISON_RUN_SENSITIVITY = "poison run-sensitivity"
    POISON_STAGES = "poison stages"
    REPORT_STATS = "report stats"
    REPORT_VALIDATE = "report validate"
    REPORT_FIGURES = "report figures"
    REPORT_TABLES = "report tables"
    REPORT_POISONING = "report poisoning"
    REPORT_SENSITIVITY = "report sensitivity"
    REPORT_ALL = "report all"
    STATUS = "status"
    SWEEP = "sweep"

    @classmethod
    def resolve(cls, arguments: Sequence[str]) -> "CliCommand | None":
        for command in cls:
            command_path = command.split()
            if list(arguments[: len(command_path)]) == command_path:
                return command
        return None


class AuditCommand(StrEnum):

    RESULTS = "results"
    REUSE = "reuse"


class AuditColumn(StrEnum):

    ARTIFACT = "Artifact"
    PATH = "Path"


class CheckpointCommand(StrEnum):

    PREVIEW = "preview"
    SMOKE = "smoke"
    EVALUATE_FROM_SCORES = "evaluate-from-scores"
    STATUS = "status"
    SUMMARY = "summary"


class CheckpointSmokeField(StrEnum):

    ARTIFACT_ROOT = "artifact_root"
    ROUNDS = "rounds"
    SELECTED_ROUND = "selected_round"


class CheckpointEvalField(StrEnum):

    CHECKPOINT_ROUND = "checkpoint_round"
    POLICIES = "policies"


class CheckpointStatusField(StrEnum):

    COMPLETE = "complete"
    CHECKPOINT = "checkpoint"
    SCORES = "scores"
    RESULTS = "results"


class CheckpointSummaryField(StrEnum):

    SELECTED_ROUND = "selected_round"


ERROR_NOT_CONFIGURED = "checkpoint_protocol is not configured."
ERROR_MUST_NOT_WRITE_OUTPUTS = "checkpoint protocol smoke must not write to outputs/"
CHECKPOINT_DEFAULT_STAGE = ExperimentStage.NBAIOT_MAIN
CHECKPOINT_SUMMARY_POLICIES = (
    ThresholdPolicy.GLOBAL_THRESHOLD,
    ThresholdPolicy.LOCAL_THRESHOLD,
)


class ConfigCommand(StrEnum):

    PREVIEW = "preview"


class PoisonCommand(StrEnum):

    PREVIEW = "preview"
    DRY_RUN = "dry-run"
    SMOKE = "smoke"
    RUN_BOUNDED_SWEEP = "run-bounded-sweep"
    RUN_SENSITIVITY = "run-sensitivity"
    STAGES = "stages"


class PoisonOutputKey(StrEnum):

    STAGE = "stage"
    DATASET = "dataset"
    ALLOW_RUN = "allow_run"
    GATE = "gate"
    DESCRIPTION = "description"


EXECUTION_GATE_NOTICE = (
    "NOTE: Experiment execution is blocked until this stage's own gate "
    "(see below) is authorized. This command is preview/dry-run only."
)


class ReportCommand(StrEnum):

    STATS = "stats"
    VALIDATE = "validate"
    FIGURES = "figures"
    TABLES = "tables"
    POISONING = "poisoning"
    SENSITIVITY = "sensitivity"
    ALL = "all"


class StatusColumn(StrEnum):

    SCOPE = "Scope"
    COMPLETE = "Complete"
    MISSING = "Missing"
    ABORTED = "Aborted"
    TOTAL = "Total"


class StatusScope(StrEnum):

    OVERALL = "Overall"
