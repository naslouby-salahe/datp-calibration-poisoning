from __future__ import annotations
from datp.attacks.enums import ThresholdPolicy

import dataclasses
import typing
from pathlib import Path


def test_threshold_result_types_importable():
    import typing

    from datp.core.types import (
        ThresholdResult,
        ClientEvalResult,
        ClientEvalResultWithAuroc,
    )

    for cls in (ThresholdResult, ClientEvalResult, ClientEvalResultWithAuroc):
        assert len(typing.get_type_hints(cls)) > 0, f"{cls.__name__} has no type hints"


def test_client_metrics_is_frozen_dataclass():
    import dataclasses

    from datp.evaluation.metrics import ClientEvaluationRecord

    assert dataclasses.is_dataclass(ClientEvaluationRecord)
    assert ClientEvaluationRecord.__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_evaluation_result_is_frozen_dataclass():
    import dataclasses

    from datp.evaluation.metrics import EvaluationResult

    assert dataclasses.is_dataclass(EvaluationResult)
    assert EvaluationResult.__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_threshold_result_required_keys():
    from datp.core.types import ThresholdResult

    hints = typing.get_type_hints(ThresholdResult)
    expected = {
        "run",
        "tau_global",
        "client_thresholds",
        "metadata",
    }
    assert expected.issubset(hints.keys()), f"Missing keys: {expected - hints.keys()}"


def test_client_eval_result_with_auroc_keys():
    from datp.core.types import ClientEvalResultWithAuroc

    hints = typing.get_type_hints(ClientEvalResultWithAuroc)
    expected = {
        "fpr",
        "tpr",
        "balanced_accuracy",
        "macro_f1",
        "n_benign",
        "n_attack",
        "auroc",
    }
    assert expected.issubset(hints.keys()), f"Missing keys: {expected - hints.keys()}"


def test_client_metrics_dict_keys():
    import dataclasses as dc

    from datp.evaluation.metrics import ClientEvaluationRecord

    field_names = {f.name for f in dc.fields(ClientEvaluationRecord)}
    expected = {
        "client_id",
        "metrics",
        "confusion",
        "n_benign",
        "n_attack",
        "threshold",
        "evaluation_incomplete",
    }
    assert expected.issubset(field_names), f"Missing keys: {expected - field_names}"


# --- Architecture guard tests ---


def test_threshold_result_is_frozen_dataclass():
    from datp.core.types import ThresholdResult

    assert dataclasses.is_dataclass(ThresholdResult)
    assert ThresholdResult.__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_client_threshold_is_frozen_dataclass():
    from datp.core.types import ClientThreshold

    assert dataclasses.is_dataclass(ClientThreshold)
    assert ClientThreshold.__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_threshold_result_client_thresholds_is_tuple():
    """Guard: client_thresholds must be tuple, not list."""
    from datp.core.types import ThresholdResult

    hints = typing.get_type_hints(ThresholdResult)
    assert "tuple" in str(hints["client_thresholds"])


def test_cluster_metadata_is_frozen_dataclass():
    from datp.core.types import ClusterInfo, ClusterMetadata

    for cls in (ClusterInfo, ClusterMetadata):
        assert dataclasses.is_dataclass(cls), f"{cls.__name__} must be a dataclass"
        assert cls.__dataclass_params__.frozen, f"{cls.__name__} must be frozen"  # type: ignore[attr-defined]


def test_identity_classes_are_frozen_dataclasses():
    from datp.core.identity import PolicyRunId, TrainingCellId

    for cls in (TrainingCellId, PolicyRunId):
        assert dataclasses.is_dataclass(cls), f"{cls.__name__} must be a dataclass"
        assert cls.__dataclass_params__.frozen, f"{cls.__name__} must be frozen"  # type: ignore[attr-defined]


def test_serialization_boundary_classes_are_pydantic():
    """Guard: classes that need model_dump() must remain Pydantic."""
    from pydantic import BaseModel

    from datp.core.types import PolicyResult, ClientEvalResult

    for cls in (PolicyResult, ClientEvalResult):
        assert issubclass(cls, BaseModel), (
            f"{cls.__name__} must remain Pydantic (serialization boundary)"
        )


def test_score_cell_id_is_frozen_dataclass():
    """Score identity uses TrainingCellId directly — no separate ScoreCellId wrapper."""
    from datp.core.identity import TrainingCellId

    assert dataclasses.is_dataclass(TrainingCellId)
    assert TrainingCellId.__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_score_cell_id_delegates_to_cell():
    from datp.config.stages import ExperimentStage
    from datp.core.identity import TrainingCellId

    cell = TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=42)
    sc = cell
    assert sc.stage == ExperimentStage.NBAIOT_MAIN
    assert sc.seed == 42


def test_dispersion_metrics_is_frozen_dataclass():
    from datp.evaluation.metrics import DispersionMetrics

    assert dataclasses.is_dataclass(DispersionMetrics)
    assert DispersionMetrics.__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_confusion_counts_is_frozen_dataclass():
    from datp.evaluation.metrics import ConfusionCounts

    assert dataclasses.is_dataclass(ConfusionCounts)
    assert ConfusionCounts.__dataclass_params__.frozen  # type: ignore[attr-defined]
    cc = ConfusionCounts(tp=10, fp=2, tn=88, fn=5)
    assert cc.fp + cc.tn == 90
    assert cc.tp + cc.fn == 15


def test_client_evaluation_record_is_frozen_dataclass():
    from datp.evaluation.metrics import ClientEvaluationRecord

    assert dataclasses.is_dataclass(ClientEvaluationRecord)
    assert ClientEvaluationRecord.__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_artifact_layout_is_frozen_dataclass():
    from datp.artifacts.layout import ArtifactLayout

    assert dataclasses.is_dataclass(ArtifactLayout)
    assert ArtifactLayout.__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_score_cell_paths_is_frozen_dataclass():
    from datp.artifacts.layout import ScoreCellPaths

    assert dataclasses.is_dataclass(ScoreCellPaths)
    assert ScoreCellPaths.__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_policy_run_paths_is_frozen_dataclass():
    from datp.artifacts.layout import PolicyRunPaths

    assert dataclasses.is_dataclass(PolicyRunPaths)
    assert PolicyRunPaths.__dataclass_params__.frozen  # type: ignore[attr-defined]


def test_path_contracts_compose_with_identity(tmp_path: Path):
    """Guard: path contracts must accept identity types."""
    from datp.artifacts.layout import ArtifactLayout
    from datp.config.stages import ExperimentStage
    from datp.core.identity import PolicyRunId, TrainingCellId

    cell = TrainingCellId(stage=ExperimentStage.NBAIOT_MAIN, seed=1)
    layout = ArtifactLayout(
        base_dir=tmp_path / "out", stage=ExperimentStage.NBAIOT_MAIN
    )

    sc_paths = layout.score_cell(cell)
    assert "seed_1" in str(sc_paths.checkpoint_dir)

    run = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
    br_paths = layout.policy_run(run)
    assert "global_threshold" in str(br_paths.result_dir)
