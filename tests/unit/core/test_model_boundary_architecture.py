"""Enforcement tests: canonical model boundary and architecture invariants.

Confirms correct class types (frozen dataclass vs Pydantic), required fields,
absent forbidden classes, and private/public scoping rules. Fails if old patterns
are reintroduced.
"""

from __future__ import annotations

import dataclasses
import importlib
import typing


class TestCanonicalIdentityTypes:
    def test_training_cell_id_is_frozen_dataclass(self) -> None:
        from datp.core.identity import TrainingCellId

        assert dataclasses.is_dataclass(TrainingCellId)
        assert TrainingCellId.__dataclass_params__.frozen  # type: ignore[attr-defined]

    def test_baseline_run_id_is_frozen_dataclass(self) -> None:
        from datp.core.identity import BaselineRunId

        assert dataclasses.is_dataclass(BaselineRunId)
        assert BaselineRunId.__dataclass_params__.frozen  # type: ignore[attr-defined]

    def test_score_cell_id_is_frozen_dataclass(self) -> None:
        """Score identity uses TrainingCellId (same type as training identity — scores are shared across B1-B4)."""
        from datp.core.identity import TrainingCellId

        assert dataclasses.is_dataclass(TrainingCellId)
        assert TrainingCellId.__dataclass_params__.frozen  # type: ignore[attr-defined]

    def test_experiment_key_absent(self) -> None:
        module = importlib.import_module("datp.core.identity")
        assert not hasattr(module, "ExperimentKey"), (
            "ExperimentKey must not exist — use TrainingCellId/BaselineRunId instead"
        )

    def test_run_identity_absent(self) -> None:
        module = importlib.import_module("datp.core.identity")
        assert not hasattr(module, "RunIdentity"), (
            "RunIdentity must not exist — use BaselineRunId instead"
        )


class TestThresholdResultStructure:
    def test_threshold_result_has_run_field(self) -> None:
        from datp.core.identity import BaselineRunId
        from datp.core.types import ThresholdResult

        fields = {f.name: f for f in dataclasses.fields(ThresholdResult)}
        assert "run" in fields, "ThresholdResult must have a run field"
        hints = typing.get_type_hints(ThresholdResult)
        assert hints["run"] is BaselineRunId, (
            f"ThresholdResult.run must be BaselineRunId, got {hints['run']}"
        )

    def test_threshold_result_no_strategy_field(self) -> None:
        from datp.core.types import ThresholdResult

        field_names = {f.name for f in dataclasses.fields(ThresholdResult)}
        assert "strategy" not in field_names, (
            "ThresholdResult must not have a strategy field — strategy is encoded in run.baseline"
        )

    def test_threshold_result_no_loose_identity(self) -> None:
        from datp.core.types import ThresholdResult

        field_names = {f.name for f in dataclasses.fields(ThresholdResult)}
        forbidden = {"regime", "seed", "alpha", "baseline", "dataset"}
        present = forbidden & field_names
        assert not present, (
            f"ThresholdResult must not have loose identity fields: {present}"
        )

    def test_threshold_metadata_exists(self) -> None:
        module = importlib.import_module("datp.core.types")
        assert hasattr(module, "ThresholdMetadata"), (
            "ThresholdMetadata must exist in datp.core.types"
        )

    def test_threshold_metadata_has_b3_b4(self) -> None:
        from datp.core.types import ThresholdMetadata

        assert dataclasses.is_dataclass(ThresholdMetadata)
        field_names = {f.name for f in dataclasses.fields(ThresholdMetadata)}
        assert "b3" in field_names, "ThresholdMetadata must have b3 field"
        assert "b4" in field_names, "ThresholdMetadata must have b4 field"

    def test_threshold_result_eligible_count_is_property(self) -> None:
        from datp.core.types import ThresholdResult

        field_names = {f.name for f in dataclasses.fields(ThresholdResult)}
        assert "eligible_count" not in field_names, (
            "eligible_count must be a @property, not a stored dataclass field"
        )
        assert isinstance(ThresholdResult.eligible_count, property), (
            "ThresholdResult.eligible_count must be a property"
        )

    def test_threshold_result_pending_count_is_property(self) -> None:
        from datp.core.types import ThresholdResult

        field_names = {f.name for f in dataclasses.fields(ThresholdResult)}
        assert "pending_count" not in field_names, (
            "pending_count must be a @property, not a stored dataclass field"
        )
        assert isinstance(ThresholdResult.pending_count, property), (
            "ThresholdResult.pending_count must be a property"
        )


class TestValidationCheckArchitecture:
    def test_validation_check_exists(self) -> None:
        module = importlib.import_module("datp.validation.schemas")
        assert hasattr(module, "ValidationCheck"), (
            "ValidationCheck must exist in datp.validation.schemas"
        )

    def test_validation_check_has_code_status_detail(self) -> None:
        from datp.validation.schemas import ValidationCheck

        field_names = set(ValidationCheck.model_fields.keys())
        assert "code" in field_names, "ValidationCheck must have code field"
        assert "status" in field_names, "ValidationCheck must have status field"
        assert "detail" in field_names, "ValidationCheck must have detail field"

    def test_metric_check_result_absent(self) -> None:
        module = importlib.import_module("datp.validation.metric_reproducer")
        assert not hasattr(module, "MetricCheckResult"), (
            "MetricCheckResult must be deleted — use ValidationCheck instead"
        )

    def test_score_check_result_absent(self) -> None:
        module = importlib.import_module("datp.validation.metric_reproducer")
        assert not hasattr(module, "ScoreCheckResult"), (
            "ScoreCheckResult must be deleted — use ValidationCheck instead"
        )

    def test_verdict_reason_entry_absent(self) -> None:
        for mod_name in ("datp.validation.verdicts", "datp.validation.schemas"):
            module = importlib.import_module(mod_name)
            assert not hasattr(module, "VerdictReasonEntry"), (
                f"VerdictReasonEntry must not exist in {mod_name} — use ValidationCheck instead"
            )

    def test_score_cell_verification_uses_training_cell_id(self) -> None:
        from datp.core.identity import TrainingCellId
        from datp.validation.score_manifest import ScoreCellVerification

        field_names = set(ScoreCellVerification.model_fields.keys())
        assert "cell" in field_names, "ScoreCellVerification must have cell field"
        annotation = ScoreCellVerification.model_fields["cell"].annotation
        assert annotation is TrainingCellId, (
            f"ScoreCellVerification.cell must be TrainingCellId, got {annotation}"
        )

    def test_cell_verdict_uses_training_cell_id(self) -> None:
        from datp.core.identity import TrainingCellId
        from datp.validation.verdicts import CellVerdict

        field_names = set(CellVerdict.model_fields.keys())
        assert "cell" in field_names, "CellVerdict must have cell field"
        annotation = CellVerdict.model_fields["cell"].annotation
        assert annotation is TrainingCellId, (
            f"CellVerdict.cell must be TrainingCellId, got {annotation}"
        )

    def test_score_cell_verification_no_loose_identity(self) -> None:
        from datp.validation.score_manifest import ScoreCellVerification

        field_names = set(ScoreCellVerification.model_fields.keys())
        forbidden = {"regime", "seed", "alpha", "dataset", "cell_dir"}
        present = forbidden & field_names
        assert not present, (
            f"ScoreCellVerification must not have loose identity fields: {present}. "
            "Use cell: TrainingCellId instead."
        )

    def test_cell_verdict_no_loose_identity(self) -> None:
        from datp.validation.verdicts import CellVerdict

        field_names = set(CellVerdict.model_fields.keys())
        forbidden = {"regime", "seed", "alpha", "dataset", "cell_dir"}
        present = forbidden & field_names
        assert not present, (
            f"CellVerdict must not have loose identity fields: {present}. "
            "Use cell: TrainingCellId instead."
        )


class TestArtifactPathContracts:
    def test_artifact_layout_has_required_fields(self) -> None:
        from datp.artifacts.layout import ArtifactLayout

        assert dataclasses.is_dataclass(ArtifactLayout)
        field_names = {f.name for f in dataclasses.fields(ArtifactLayout)}
        for required in ("base_dir", "regime"):
            assert required in field_names, (
                f"ArtifactLayout must have {required!r} field"
            )

    def test_artifact_layout_exposes_path_methods(self) -> None:
        from datp.artifacts.layout import ArtifactLayout

        for method in ("score_cell", "baseline_run", "checkpoint_dir", "score_file"):
            assert callable(getattr(ArtifactLayout, method, None)), (
                f"ArtifactLayout must expose {method!r}"
            )

    def test_baseline_run_paths_has_run(self) -> None:
        from datp.artifacts.layout import BaselineRunPaths
        from datp.core.identity import BaselineRunId

        assert dataclasses.is_dataclass(BaselineRunPaths)
        field_names = {f.name for f in dataclasses.fields(BaselineRunPaths)}
        assert "run" in field_names, "BaselineRunPaths must have run field"
        hints = typing.get_type_hints(BaselineRunPaths)
        assert hints["run"] is BaselineRunId, (
            f"BaselineRunPaths.run must be BaselineRunId, got {hints['run']}"
        )

    def test_baseline_run_paths_has_metrics_path(self) -> None:
        from datp.artifacts.layout import BaselineRunPaths

        field_names = {f.name for f in dataclasses.fields(BaselineRunPaths)}
        assert "metrics_path" in field_names, (
            "BaselineRunPaths must have metrics_path field"
        )

    def test_baseline_run_paths_has_result_dir_and_log_dir(self) -> None:
        from datp.artifacts.layout import BaselineRunPaths

        field_names = {f.name for f in dataclasses.fields(BaselineRunPaths)}
        assert "result_dir" in field_names, (
            "BaselineRunPaths must have result_dir field"
        )
        assert "log_dir" in field_names, "BaselineRunPaths must have log_dir field"

    def test_score_cell_paths_has_cell(self) -> None:
        from datp.artifacts.layout import ScoreCellPaths
        from datp.core.identity import TrainingCellId

        assert dataclasses.is_dataclass(ScoreCellPaths)
        field_names = {f.name for f in dataclasses.fields(ScoreCellPaths)}
        assert "cell" in field_names, "ScoreCellPaths must have cell field"
        hints = typing.get_type_hints(ScoreCellPaths)
        assert hints["cell"] is TrainingCellId, (
            f"ScoreCellPaths.cell must be TrainingCellId, got {hints['cell']}"
        )

    def test_score_cell_paths_has_manifest_path(self) -> None:
        from datp.artifacts.layout import ScoreCellPaths

        field_names = {f.name for f in dataclasses.fields(ScoreCellPaths)}
        assert "manifest_path" in field_names, (
            "ScoreCellPaths must have manifest_path field"
        )

    def test_score_cell_paths_has_checkpoint_dir_and_score_dir(self) -> None:
        from datp.artifacts.layout import ScoreCellPaths

        field_names = {f.name for f in dataclasses.fields(ScoreCellPaths)}
        assert "checkpoint_dir" in field_names, (
            "ScoreCellPaths must have checkpoint_dir field"
        )
        assert "score_dir" in field_names, "ScoreCellPaths must have score_dir field"

    def test_score_cell_paths_no_old_fields(self) -> None:
        from datp.artifacts.layout import ScoreCellPaths

        field_names = {f.name for f in dataclasses.fields(ScoreCellPaths)}
        old_names = {"checkpoint", "score_root", "checkpoint_root"}
        present = old_names & field_names
        assert not present, f"ScoreCellPaths must not have old field names: {present}"


class TestDatasetPartitionContracts:
    def test_partition_result_is_pydantic(self) -> None:
        from pydantic import BaseModel

        from datp.data.contracts import PartitionResult

        assert issubclass(PartitionResult, BaseModel), (
            "PartitionResult is a boundary schema and must be a Pydantic model"
        )

    def test_audit_client_is_pydantic(self) -> None:
        from pydantic import BaseModel

        from datp.data.common.audit import AuditClient

        assert issubclass(AuditClient, BaseModel), (
            "AuditClient is a boundary schema and must be a Pydantic model"
        )

    def test_regime_c_client_summary_is_pydantic(self) -> None:
        from pydantic import BaseModel

        from datp.data.contracts import RegimeCClientSummary

        assert issubclass(RegimeCClientSummary, BaseModel), (
            "RegimeCClientSummary is a boundary schema and must be a Pydantic model"
        )


class TestEvaluationResultArchitecture:
    def test_evaluation_result_has_run(self) -> None:
        from datp.core.identity import BaselineRunId
        from datp.evaluation.metrics import EvaluationResult

        assert dataclasses.is_dataclass(EvaluationResult)
        field_names = {f.name for f in dataclasses.fields(EvaluationResult)}
        assert "run" in field_names, "EvaluationResult must have run field"
        hints = typing.get_type_hints(EvaluationResult)
        assert hints["run"] is BaselineRunId, (
            f"EvaluationResult.run must be BaselineRunId, got {hints['run']}"
        )

    def test_evaluation_result_has_clients_as_tuple(self) -> None:
        from datp.evaluation.metrics import EvaluationResult

        field_names = {f.name for f in dataclasses.fields(EvaluationResult)}
        assert "clients" in field_names, "EvaluationResult must have clients field"
        hints = typing.get_type_hints(EvaluationResult)
        clients_hint = hints["clients"]
        origin = typing.get_origin(clients_hint)
        assert origin is tuple, (
            f"EvaluationResult.clients must be a tuple type, got origin={origin}"
        )

    def test_evaluation_result_has_dispersion(self) -> None:
        from datp.evaluation.metrics import DispersionMetrics, EvaluationResult

        field_names = {f.name for f in dataclasses.fields(EvaluationResult)}
        assert "dispersion" in field_names, (
            "EvaluationResult must have dispersion field"
        )
        hints = typing.get_type_hints(EvaluationResult)
        assert hints["dispersion"] is DispersionMetrics, (
            f"EvaluationResult.dispersion must be DispersionMetrics, got {hints['dispersion']}"
        )

    def test_client_metrics_absent(self) -> None:
        module = importlib.import_module("datp.evaluation.metrics")
        assert not hasattr(module, "ClientMetrics"), (
            "ClientMetrics must not exist — use ClientEvaluationRecord instead"
        )

    def test_fpr_dispersion_bundle_absent(self) -> None:
        module = importlib.import_module("datp.evaluation.metrics")
        assert not hasattr(module, "FPRDispersionBundle"), (
            "FPRDispersionBundle must not exist — use DispersionMetrics instead"
        )


class TestCLIAccumulatorsAllowlisted:
    def test_regime_report_is_private(self) -> None:
        module = importlib.import_module("datp.app.cli.status")
        assert hasattr(module, "_RegimeReport"), (
            "_RegimeReport must exist as a private CLI accumulator in datp.app.cli.status"
        )
        assert not hasattr(module, "RegimeReport"), (
            "RegimeReport (without underscore) must not be exported — keep it private as _RegimeReport"
        )

    def test_status_report_is_private(self) -> None:
        module = importlib.import_module("datp.app.cli.status")
        assert hasattr(module, "_StatusReport"), (
            "_StatusReport must exist as a private CLI accumulator in datp.app.cli.status"
        )
        assert not hasattr(module, "StatusReport"), (
            "StatusReport (without underscore) must not be exported — keep it private as _StatusReport"
        )
