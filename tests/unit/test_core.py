from __future__ import annotations

import ast
import dataclasses
import importlib
import random
import re
import typing
from pathlib import Path

import numpy as np
import pytest
import torch

from datp.config import ExperimentStage
from datp.core import (
    PolicyRunId,
    SeedPair,
    SeedRecord,
    TrainingCellId,
    array_hash,
    git_commit,
    hash_file,
    hash_jsonable,
    make_seed_rng,
    seed_segment,
    set_seeds,
    sha256_bytes,
    source_hash,
    utc_timestamp,
)
from datp.data import Split
from datp.enums import (
    CONTROLLED_POLICIES,
    THRESHOLD_AGGREGATION_BY_POLICY,
    ArtifactDir,
    ClientStatus,
    DatasetID,
    EvidenceRole,
    FigureName,
    NormalizationScope,
    ProvenanceSentinel,
    ScoringStage,
    SeedScope,
    ThresholdAggregationMethod,
    ThresholdPolicy,
)


def test_controlled_policies_global_local_cluster() -> None:
    """Ensure controlled policies consist exactly of global, local, and cluster thresholds."""
    assert set(CONTROLLED_POLICIES) == {
        ThresholdPolicy.GLOBAL_THRESHOLD,
        ThresholdPolicy.LOCAL_THRESHOLD,
        ThresholdPolicy.CLUSTER_THRESHOLD,
    }


def test_artifact_dir_names() -> None:
    """Verify directory constants map to their on-disk names."""
    assert ArtifactDir.FIGURES == "figures"
    assert ArtifactDir.TABLES == "tables"
    assert ArtifactDir.ANALYSIS == "analysis"


_SRC_ROOT = Path(__file__).parent.parent.parent / "src" / "datp"


_TESTS_ROOT = Path(__file__).parent.parent


_NAMEDTUPLE_TEST_ALLOWLIST: frozenset[str] = frozenset(
    {
        "e2e/diagnostic/test_diagnostic_e2e.py",
    }
)


_DEFAULTS_ALLOWLIST: frozenset[tuple[str, str, str]] = frozenset(
    {
        ("federated.py", "SimClientConfig", "client_cls"),
        ("federated.py", "SimClientConfig", "client_extra_kwargs"),
        ("federated.py", "SimClientConfig", "encoder_only"),
        ("federated.py", "SimClientConfig", "score_after"),
        ("validation.py", "CellPanel", "cv_fpr"),
        ("validation.py", "CellPanel", "cv_tpr"),
        ("validation.py", "CellPanel", "macro_f1_mean"),
        ("validation.py", "CellPanel", "macro_f1_p10"),
        ("validation.py", "CellPanel", "auroc_mean"),
        ("validation.py", "CellPanel", "pr_auc_mean"),
        ("validation.py", "CellPanel", "mean_fpr"),
        ("validation.py", "CellPanel", "std_fpr"),
        ("validation.py", "CellPanel", "iqr_fpr"),
        ("validation.py", "CellPanel", "worst_client_fpr"),
        ("validation.py", "CellPanel", "worst_client_tpr"),
        ("validation.py", "CellPanel", "worst_client_macro_f1"),
        ("validation.py", "CellPanel", "worst_client_balanced_accuracy"),
        ("validation.py", "CellPanel", "convergence_round"),
        ("validation.py", "CellPanel", "tau_global"),
        ("validation.py", "CellPanel", "coverage_ratio"),
        ("validation.py", "AuditAccumulator", "manifest_records"),
        ("validation.py", "AuditAccumulator", "client_records"),
        ("validation.py", "AuditAccumulator", "attack_records"),
        ("validation.py", "AuditAccumulator", "threshold_records"),
        ("validation.py", "AuditAccumulator", "recon_records"),
        ("validation.py", "AuditAccumulator", "denominator_records"),
        ("validation.py", "AuditAccumulator", "convergence_records"),
        ("validation.py", "AuditAccumulator", "cluster_records"),
        ("validation.py", "AuditAccumulator", "companion_records"),
        ("validation.py", "AuditAccumulator", "worst_client_records"),
        ("validation.py", "AuditAccumulator", "partition_audits"),
        ("validation.py", "AuditAccumulator", "invariant_inputs"),
        ("validation.py", "AuditAccumulator", "score_hashes_by_cell"),
        ("validation.py", "AuditAccumulator", "recomputation_records"),
        ("validation.py", "AuditAccumulator", "cell_panel"),
        ("validation.py", "AuditAccumulator", "warnings"),
        ("validation.py", "AuditAccumulator", "missing_confusion_warned"),
        ("experiments.py", "SweepResult", "total"),
        ("experiments.py", "SweepResult", "completed"),
        ("experiments.py", "SweepResult", "skipped"),
        ("experiments.py", "SweepResult", "failed"),
        ("cli/__init__.py", "_StageReport", "complete"),
        ("cli/__init__.py", "_StageReport", "missing"),
        ("cli/__init__.py", "_StageReport", "aborted"),
        ("cli/__init__.py", "_StatusReport", "stage_reports"),
        ("reporting/figures.py", "ResultTable", "rows"),
        ("reporting/figures.py", "ResultTable", "footnote"),
        ("data.py", "DatasetSpec", "cap_policy"),
        ("data.py", "DatasetSpec", "family_map"),
        ("data.py", "DatasetSpec", "device_ids"),
        ("data.py", "DatasetSpec", "attack_family_dirs"),
        ("data.py", "DatasetSpec", "expected_client_count"),
        ("attacks/metrics/inference.py", "HolmResult", "descriptive_only"),
        ("attacks/injection.py", "ScoreCollection", "n_min"),
        ("attacks/injection.py", "SweepCellSpec", "target_scope"),
        ("attacks/injection.py", "MetricEngineInput", "mu_flag_threshold"),
        ("attacks/injection.py", "MetricEngineInput", "auroc_set"),
        ("attacks/sweep.py", "SweepCellConfig", "auroc_set"),
        ("attacks/sweep.py", "SweepCellConfig", "scope_idx"),
        ("attacks/sweep.py", "SweepCellConfig", "q"),
        ("attacks/sweep.py", "SweepCellConfig", "cluster_seed"),
        ("attacks/sweep.py", "InjectionSpec", "scope_idx"),
        ("attacks/sweep.py", "InjectionSpec", "tail_mass"),
        ("attacks/sweep.py", "InjectionSpec", "draw"),
        (
            "attacks/metrics.py",
            "ClusterHyperparams",
            "k",
        ),
        (
            "attacks/metrics.py",
            "ClusterHyperparams",
            "n_init",
        ),
        (
            "attacks/metrics.py",
            "ClusterHyperparams",
            "max_iter",
        ),
        (
            "attacks/metrics.py",
            "ClusterHyperparams",
            "random_state",
        ),
        (
            "attacks/metrics.py",
            "ClusterHyperparams",
            "n_min",
        ),
        (
            "attacks/metrics.py",
            "ClusterHyperparams",
            "seed",
        ),
        ("attacks/metrics/inference.py", "BootstrapConfig", "ci"),
        ("attacks/metrics/inference.py", "BootstrapConfig", "n_bootstrap"),
        ("attacks/metrics/inference.py", "BootstrapConfig", "analysis_seed"),
        ("attacks/metrics/inference.py", "HolmConfig", "alpha"),
        ("attacks/metrics/inference.py", "InferenceInput", "bootstrap_config"),
        ("attacks/metrics/inference.py", "InferenceInput", "holm_config"),
        ("thresholding.py", "ThresholdDerivation", "seed"),
        ("federated.py", "ClientFactoryConfig", "prepared_dir"),
        ("federated.py", "ClientFactoryConfig", "model_cls"),
        ("federated.py", "ClientFactoryConfig", "client_cls"),
        ("federated.py", "ClientFactoryConfig", "extra_kwargs"),
        ("federated.py", "ClientFactoryConfig", "seed"),
        ("federated.py", "FedAvgConfig", "initial_parameters"),
        ("federated.py", "FlSimulationRequest", "prepared_dir"),
        ("federated.py", "FlSimulationRequest", "client_config"),
        ("testsupport/synthetic_scores.py", "SyntheticClientSpec", "n_cal"),
        ("testsupport/synthetic_scores.py", "SyntheticClientSpec", "n_test_benign"),
        ("testsupport/synthetic_scores.py", "SyntheticClientSpec", "n_test_attack"),
        ("testsupport/synthetic_scores.py", "SyntheticClientSpec", "cal_loc"),
        ("testsupport/synthetic_scores.py", "SyntheticClientSpec", "cal_scale"),
        ("testsupport/synthetic_scores.py", "SyntheticClientSpec", "attack_loc"),
        ("testsupport/synthetic_scores.py", "SyntheticClientSpec", "attack_scale"),
        ("testsupport/synthetic_scores.py", "SyntheticClientSpec", "training_seed"),
        ("testsupport/synthetic_scores.py", "SyntheticClientSpec", "poisoning_seed"),
        ("testsupport/synthetic_scores.py", "SyntheticClientSpec", "client_idx"),
        ("testsupport/synthetic_scores.py", "SyntheticClientSpec", "scope_idx"),
        ("testsupport/synthetic_scores.py", "StandardScoreSetRequest", "n_eligible"),
        ("testsupport/synthetic_scores.py", "StandardScoreSetRequest", "n_pending"),
        (
            "testsupport/synthetic_scores.py",
            "StandardScoreSetRequest",
            "include_degenerate",
        ),
        ("testsupport/synthetic_scores.py", "StandardScoreSetRequest", "training_seed"),
        (
            "testsupport/synthetic_scores.py",
            "StandardScoreSetRequest",
            "poisoning_seed",
        ),
    }
)


def _all_py_files(root: Path) -> list[Path]:
    """Collect all python files recursively under a given root directory."""
    return sorted(root.rglob("*.py"))


def _source(path: Path) -> str:
    """Read and return the text content of a file."""
    return path.read_text()


_NAMEDTUPLE_PATTERN = re.compile(r"\bclass\s+\w+\s*\(\s*(?:typing\.)?NamedTuple\s*\)")


class TestNoNamedTuplesInSrc:
    """Verify that NamedTuples are not used within source code."""

    def test_no_namedtuples_in_src(self) -> None:
        """Ensure no files in src contain NamedTuple definitions."""
        violations: list[str] = []
        for path in _all_py_files(_SRC_ROOT):
            src = _source(path)
            if _NAMEDTUPLE_PATTERN.search(src):
                violations.append(str(path.relative_to(_SRC_ROOT)))
        assert not violations, (
            f"Found NamedTuple classes in src: {violations}. "
            "Use @dataclass(frozen=True, slots=True) instead."
        )


class TestNoNamedTuplesInTests:
    """Verify that NamedTuple usage in tests is restricted to the allowlist."""

    def test_namedtuples_in_tests_match_allowlist(self) -> None:
        """Ensure only allowed test files define NamedTuple classes."""
        violations: list[str] = []
        for path in _all_py_files(_TESTS_ROOT):
            src = _source(path)
            if not _NAMEDTUPLE_PATTERN.search(src):
                continue
            rel = str(path.relative_to(_TESTS_ROOT))
            if rel not in _NAMEDTUPLE_TEST_ALLOWLIST:
                violations.append(rel)
        assert not violations, (
            f"Unexpected NamedTuple classes in tests (not in allowlist): {violations}."
        )


def _is_dataclass_decorator(decorator: ast.expr) -> bool:
    """Check if a decorator AST node is the dataclass decorator."""
    if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
        return True
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Name) and func.id == "dataclass":
            return True
        if isinstance(func, ast.Attribute) and func.attr == "dataclass":
            return True
    return False


def _class_has_dataclass_decorator(node: ast.ClassDef) -> bool:
    """Check if class AST node contains a dataclass decorator."""
    return any(_is_dataclass_decorator(d) for d in node.decorator_list)


def _collect_defaults_in_class(
    rel: str, node: ast.ClassDef
) -> list[tuple[str, str, str]]:
    """Find all attribute assignments with defaults in a class AST node."""
    results: list[tuple[str, str, str]] = []
    for stmt in node.body:
        if isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            if isinstance(stmt.target, ast.Name):
                results.append((rel, node.name, stmt.target.id))
    return results


def _collect_dataclass_defaults(path: Path) -> list[tuple[str, str, str]]:
    """Find all dataclass fields with default values in a python file."""
    try:
        tree = ast.parse(_source(path))
    except SyntaxError:
        return []

    rel = str(path.relative_to(_SRC_ROOT))
    results: list[tuple[str, str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and _class_has_dataclass_decorator(node):
            results.extend(_collect_defaults_in_class(rel, node))
    return results


class TestNoUnjustifiedDataclassDefaults:
    """Verify that dataclass field defaults are justified and on the allowlist."""

    def test_no_unjustified_defaults_in_src(self) -> None:
        """Ensure all dataclass defaults in src exist in _DEFAULTS_ALLOWLIST."""
        violations: list[str] = []

        for path in _all_py_files(_SRC_ROOT):
            for rel, cls, field in _collect_dataclass_defaults(path):
                if (rel, cls, field) not in _DEFAULTS_ALLOWLIST:
                    violations.append(f"{rel}::{cls}.{field}")
        assert not violations, (
            "Dataclass fields with unjustified defaults found:\n"
            + "\n".join(f" {v}" for v in violations)
            + "\nAdd to _DEFAULTS_ALLOWLIST with a documented reason, or remove the default."
        )


class TestThresholdPolicyEnum:
    """Tests for verifying canonical threshold policies and values."""

    def test_canonical_policies_present(self) -> None:
        """Verify the exact set of supported threshold policies."""
        assert set(ThresholdPolicy) == {
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        }

    def test_policy_values_are_lowercase(self) -> None:
        """Ensure all threshold policy string values are lowercase."""
        for b in ThresholdPolicy:
            assert b.value == b.value.lower()

    def test_policy_is_str_compatible(self) -> None:
        """Confirm policies are string compatible and serialize correctly."""
        assert ThresholdPolicy.GLOBAL_THRESHOLD == "global_threshold"
        assert str(ThresholdPolicy.LOCAL_THRESHOLD) == "local_threshold"


class TestDatasetIDEnum:
    """Tests for validating dataset identifiers."""

    def test_dataset_ids_present(self) -> None:
        """Verify N-BAIOT identifier exists in dataset catalog enum."""
        assert DatasetID.NBAIOT in DatasetID


class TestThresholdAggregationByPolicy:
    """Tests mapping policies to threshold aggregation methods."""

    def test_every_controlled_policy_has_an_entry(self) -> None:
        """Verify every controlled threshold policy maps to an aggregation method."""
        for b in CONTROLLED_POLICIES:
            assert b in THRESHOLD_AGGREGATION_BY_POLICY, (
                f"{b} missing from THRESHOLD_AGGREGATION_BY_POLICY"
            )

    def test_global_is_eligible_client_arithmetic_mean(self) -> None:
        """Confirm GLOBAL_THRESHOLD maps to the unweighted mean over eligible clients."""
        assert THRESHOLD_AGGREGATION_BY_POLICY[ThresholdPolicy.GLOBAL_THRESHOLD] == (
            ThresholdAggregationMethod.ELIGIBLE_CLIENT_ARITHMETIC_MEAN
        )

    def test_local_is_per_client_percentile(self) -> None:
        """Confirm LOCAL_THRESHOLD maps to per-client percentile aggregation."""
        assert THRESHOLD_AGGREGATION_BY_POLICY[ThresholdPolicy.LOCAL_THRESHOLD] == (
            ThresholdAggregationMethod.PER_CLIENT_PERCENTILE
        )

    def test_cluster_is_eligible_cluster_arithmetic_mean(self) -> None:
        """Confirm CLUSTER_THRESHOLD maps to cluster arithmetic mean aggregation."""
        assert THRESHOLD_AGGREGATION_BY_POLICY[ThresholdPolicy.CLUSTER_THRESHOLD] == (
            ThresholdAggregationMethod.ELIGIBLE_CLUSTER_ARITHMETIC_MEAN
        )

    def test_values_are_threshold_aggregation_method_instances(self) -> None:
        """Ensure the mapped targets are indeed valid aggregation enums."""
        for b, v in THRESHOLD_AGGREGATION_BY_POLICY.items():
            assert isinstance(v, ThresholdAggregationMethod), (
                f"{b}: expected ThresholdAggregationMethod, got {type(v)}"
            )


class TestClientStatusEnum:
    """Tests for validating client status enum values."""

    def test_eligible_value(self) -> None:
        """Confirm 'eligible' maps to client eligibility status."""
        assert ClientStatus.ELIGIBLE == "eligible"

    def test_calibration_pending_value(self) -> None:
        """Confirm 'calibration_pending' maps to calibration pending status."""
        assert ClientStatus.CALIBRATION_PENDING == "calibration_pending"


class TestSplitEnum:
    """Tests for validating split enum members."""

    def test_all_four_splits_present(self) -> None:
        """Ensure the exact train, cal, test_benign, test_attack splits exist."""
        assert set(Split) == {
            Split.TRAIN,
            Split.CAL,
            Split.TEST_BENIGN,
            Split.TEST_ATTACK,
        }


class TestNormalizationScopeEnum:
    """Tests for validating normalization scope enum values."""

    def test_normalization_scope_values(self) -> None:
        """Verify global and per-client normalization scope values."""
        assert NormalizationScope.GLOBAL == "global"
        assert NormalizationScope.PER_CLIENT == "per_client"


class TestScoringStageEnum:
    """Tests for validating scoring stage enum values."""

    def test_scoring_stage_values(self) -> None:
        """Verify cal, test_benign, and test_attack scoring stage values."""
        assert ScoringStage.CAL == "cal"
        assert ScoringStage.TEST_BENIGN == "test_benign"
        assert ScoringStage.TEST_ATTACK == "test_attack"


class TestControlledPolicies:
    """Tests for validating controlled policies constant definition."""

    def test_contains_global_local_cluster(self) -> None:
        """Verify controlled policies include global, local, and cluster thresholds."""
        assert set(CONTROLLED_POLICIES) == {
            ThresholdPolicy.GLOBAL_THRESHOLD,
            ThresholdPolicy.LOCAL_THRESHOLD,
            ThresholdPolicy.CLUSTER_THRESHOLD,
        }

    def test_is_tuple(self) -> None:
        """Ensure controlled policies is represented as an immutable tuple."""
        assert isinstance(CONTROLLED_POLICIES, tuple)


class TestEvidenceRole:
    """Tests for validating evidence role enum values."""

    def test_descriptive_value(self) -> None:
        """Verify descriptive evidence role string value."""
        assert EvidenceRole.DESCRIPTIVE == "descriptive"

    def test_descriptive_with_sidecar_delta_value(self) -> None:
        """Verify descriptive confirmatory sidecar delta role string."""
        assert (
            EvidenceRole.DESCRIPTIVE_WITH_CONFIRMATORY_SIDECAR_DELTA
            == "descriptive_with_confirmatory_sidecar_delta"
        )

    def test_is_str_compatible(self) -> None:
        """Ensure all EvidenceRole members are string-compatible."""
        for role in EvidenceRole:
            assert isinstance(role, str)


class TestSeedScope:
    """Tests for validating seed scope enum values."""

    def test_representative_seed_value(self) -> None:
        """Verify representative seed scope string value."""
        assert SeedScope.REPRESENTATIVE_SEED == "representative_seed"

    def test_all_seed_value(self) -> None:
        """Verify all seeds scope string value."""
        assert SeedScope.ALL_SEEDS == "all_seeds"

    def test_is_str_compatible(self) -> None:
        """Ensure all SeedScope members are string-compatible."""
        for scope in SeedScope:
            assert isinstance(scope, str)


class TestFigureName:
    """Tests for validating figure name enum values."""

    def test_six_figures_defined(self) -> None:
        """Verify exactly six figures are defined in the enum."""
        assert len(FigureName) == 5

    def test_figure_values(self) -> None:
        """Verify FigureName mapping values match standard identifiers."""
        assert FigureName.FIGURE_1 == "figure_1"
        assert FigureName.FIGURE_2 == "figure_2"
        assert FigureName.FIGURE_3 == "figure_3"
        assert FigureName.FIGURE_5 == "figure_5"
        assert FigureName.FIGURE_6 == "figure_6"

    def test_is_str_compatible(self) -> None:
        """Ensure all FigureName members are string-compatible."""
        for name in FigureName:
            assert isinstance(name, str)


_STAGE = ExperimentStage.NBAIOT_MAIN


class TestTrainingCellId:
    """Tests verifying representation and invariants of training cell identifiers."""

    def test_label_includes_stage_and_seed(self) -> None:
        """Verify that training cell label formats stage name and seed correctly."""
        key = TrainingCellId(stage=_STAGE, seed=42)
        label = key.label()
        assert "nbaiot_main" in label
        assert "42" in label

    def test_immutable(self) -> None:
        """Confirm TrainingCellId is frozen and cannot be mutated."""
        key = TrainingCellId(stage=_STAGE, seed=42)
        with pytest.raises((AttributeError, TypeError)):
            setattr(key, "stage", ExperimentStage.NBAIOT_MAIN)

    def test_equality(self) -> None:
        """Verify value-based equality for identical training cell inputs."""
        k1 = TrainingCellId(stage=_STAGE, seed=1)
        k2 = TrainingCellId(stage=_STAGE, seed=1)
        assert k1 == k2

    def test_inequality_different_seed(self) -> None:
        """Verify value-based inequality for training cells with different seeds."""
        k1 = TrainingCellId(stage=_STAGE, seed=1)
        k2 = TrainingCellId(stage=_STAGE, seed=2)
        assert k1 != k2

    def test_hashable(self) -> None:
        """Verify TrainingCellId instances are hashable and can form sets."""
        k1 = TrainingCellId(stage=_STAGE, seed=1)
        k2 = TrainingCellId(stage=_STAGE, seed=2)
        s: set[TrainingCellId] = {k1, k2}
        assert len(s) == 2

    def test_stage_field(self) -> None:
        """Confirm stage property exposes the correct experiment stage enum."""
        key = TrainingCellId(stage=_STAGE, seed=1)
        assert key.stage == _STAGE

    def test_used_as_dict_key(self) -> None:
        """Confirm TrainingCellId is hashable for use as dictionary keys."""
        k1 = TrainingCellId(stage=_STAGE, seed=0)
        k2 = TrainingCellId(stage=_STAGE, seed=0)
        d: dict[TrainingCellId, str] = {k1: "shared"}
        assert d[k2] == "shared"


class TestPolicyRunId:
    """Tests verifying representation and invariants of policy run identifiers."""

    def test_construction_and_properties(self) -> None:
        """Confirm PolicyRunId maps back to its training cell and policy fields."""
        cell = TrainingCellId(stage=_STAGE, seed=42)
        run = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        assert run.cell is cell
        assert run.policy == ThresholdPolicy.GLOBAL_THRESHOLD

    def test_equality(self) -> None:
        """Verify value-based equality for identical policy runs."""
        cell = TrainingCellId(stage=_STAGE, seed=1)
        r1 = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        r2 = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        assert r1 == r2

    def test_inequality_different_policy(self) -> None:
        """Verify value-based inequality for runs under different policies."""
        cell = TrainingCellId(stage=_STAGE, seed=1)
        r1 = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        r2 = PolicyRunId(cell=cell, policy=ThresholdPolicy.LOCAL_THRESHOLD)
        assert r1 != r2

    def test_inequality_different_cell(self) -> None:
        """Verify value-based inequality for runs spanning different cells."""
        c1 = TrainingCellId(stage=_STAGE, seed=1)
        c2 = TrainingCellId(stage=_STAGE, seed=2)
        r1 = PolicyRunId(cell=c1, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        r2 = PolicyRunId(cell=c2, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        assert r1 != r2

    def test_immutable(self) -> None:
        """Confirm PolicyRunId is frozen and cannot be mutated."""
        cell = TrainingCellId(stage=_STAGE, seed=42)
        run = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        with pytest.raises((AttributeError, TypeError)):
            setattr(run, "policy", ThresholdPolicy.LOCAL_THRESHOLD)

    def test_hashable(self) -> None:
        """Verify PolicyRunId instances are hashable and can form sets."""
        cell = TrainingCellId(stage=_STAGE, seed=1)
        r1 = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        r2 = PolicyRunId(cell=cell, policy=ThresholdPolicy.LOCAL_THRESHOLD)
        s: set[PolicyRunId] = {r1, r2}
        assert len(s) == 2

    def test_label_includes_stage_policy_seed(self) -> None:
        """Verify run label formatting embeds stage name, policy string, and seed."""
        cell = TrainingCellId(stage=_STAGE, seed=42)
        run = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        label = run.label()
        assert "nbaiot_main" in label
        assert "global_threshold" in label
        assert "42" in label

    def test_audit_id(self) -> None:
        """Verify generated audit ID string matches the canonical format."""
        cell = TrainingCellId(stage=_STAGE, seed=42)
        run = PolicyRunId(cell=cell, policy=ThresholdPolicy.GLOBAL_THRESHOLD)
        assert run.audit_id() == "nbaiot_main_global_threshold_seed42"


class TestSeedSegment:
    """Tests verifying seed directory path segments formatting."""

    def test_returns_seed_prefix(self) -> None:
        """Confirm positive seed formatting returns the correct directory segment prefix."""
        assert seed_segment(42) == "seed_42"

    def test_zero_seed(self) -> None:
        """Confirm seed zero directory segment is correctly formatted."""
        assert seed_segment(0) == "seed_0"


class TestCanonicalIdentityTypes:
    """Tests verifying canonical identity data types and absence of legacy models."""

    def test_training_cell_id_is_frozen_dataclass(self) -> None:
        """Verify that TrainingCellId is defined as a frozen dataclass."""
        from datp.core import TrainingCellId

        assert dataclasses.is_dataclass(TrainingCellId)
        assert getattr(TrainingCellId, "__dataclass_params__").frozen

    def test_policy_run_id_is_frozen_dataclass(self) -> None:
        """Verify that PolicyRunId is defined as a frozen dataclass."""
        from datp.core import PolicyRunId

        assert dataclasses.is_dataclass(PolicyRunId)
        assert getattr(PolicyRunId, "__dataclass_params__").frozen

    def test_experiment_key_absent(self) -> None:
        """Confirm that the obsolete ExperimentKey type is removed."""
        module = importlib.import_module("datp.core")
        assert not hasattr(module, "ExperimentKey"), (
            "ExperimentKey must not exist — use TrainingCellId/PolicyRunId instead"
        )

    def test_run_identity_absent(self) -> None:
        """Confirm that the obsolete RunIdentity type is removed."""
        module = importlib.import_module("datp.core")
        assert not hasattr(module, "RunIdentity"), (
            "RunIdentity must not exist — use PolicyRunId instead"
        )


class TestThresholdResultStructure:
    """Tests verifying the structure and properties of ThresholdResult."""

    def test_threshold_result_has_run_field(self) -> None:
        """Confirm ThresholdResult holds a PolicyRunId reference in the run field."""
        from datp.core import PolicyRunId, ThresholdResult

        fields = {f.name: f for f in dataclasses.fields(ThresholdResult)}
        assert "run" in fields, "ThresholdResult must have a run field"
        hints = typing.get_type_hints(ThresholdResult)
        assert hints["run"] is PolicyRunId, (
            f"ThresholdResult.run must be PolicyRunId, got {hints['run']}"
        )

    def test_threshold_result_no_strategy_field(self) -> None:
        """Confirm ThresholdResult does not duplicate strategy in a loose field."""
        from datp.core import ThresholdResult

        field_names = {f.name for f in dataclasses.fields(ThresholdResult)}
        assert "strategy" not in field_names, (
            "ThresholdResult must not have a strategy field — strategy is encoded in run.policy"
        )

    def test_threshold_result_no_loose_identity(self) -> None:
        """Ensure ThresholdResult does not store legacy unstructured identity fields."""
        from datp.core import ThresholdResult

        field_names = {f.name for f in dataclasses.fields(ThresholdResult)}
        forbidden = {"regime", "seed", "alpha", "baseline", "dataset"}
        present = forbidden & field_names
        assert not present, (
            f"ThresholdResult must not have loose identity fields: {present}"
        )

    def test_threshold_result_carries_cluster_metadata_directly(self) -> None:
        """Keep optional cluster metadata on the result without a forwarding wrapper."""
        from datp.core import ThresholdResult

        field_names = {f.name for f in dataclasses.fields(ThresholdResult)}
        assert "cluster" in field_names
        assert "metadata" not in field_names

    def test_threshold_result_eligible_count_is_property(self) -> None:
        """Verify that eligible_count is exposed as a computed property."""
        from datp.core import ThresholdResult

        field_names = {f.name for f in dataclasses.fields(ThresholdResult)}
        assert "eligible_count" not in field_names, (
            "eligible_count must be a @property, not a stored dataclass field"
        )
        assert isinstance(ThresholdResult.eligible_count, property), (
            "ThresholdResult.eligible_count must be a property"
        )

    def test_threshold_result_pending_count_is_property(self) -> None:
        """Verify that pending_count is exposed as a computed property."""
        from datp.core import ThresholdResult

        field_names = {f.name for f in dataclasses.fields(ThresholdResult)}
        assert "pending_count" not in field_names, (
            "pending_count must be a @property, not a stored dataclass field"
        )
        assert isinstance(ThresholdResult.pending_count, property), (
            "ThresholdResult.pending_count must be a property"
        )


class TestArtifactPathContracts:
    """Tests verifying the interface contracts and schemas of artifact layout paths."""

    def test_artifact_layout_has_required_fields(self) -> None:
        """Confirm ArtifactLayout has base directory and stage fields."""
        from datp.artifacts import ArtifactLayout

        assert dataclasses.is_dataclass(ArtifactLayout)
        field_names = {f.name for f in dataclasses.fields(ArtifactLayout)}
        for required in ("base_dir", "stage"):
            assert required in field_names, (
                f"ArtifactLayout must have {required!r} field"
            )

    def test_artifact_layout_exposes_path_methods(self) -> None:
        """Confirm ArtifactLayout exposes canonical path generation methods."""
        from datp.artifacts import ArtifactLayout

        for method in ("score_cell", "policy_run", "score_file"):
            assert callable(getattr(ArtifactLayout, method, None)), (
                f"ArtifactLayout must expose {method!r}"
            )

    def test_policy_run_paths_has_run(self) -> None:
        """Confirm PolicyRunPaths references PolicyRunId."""
        from datp.artifacts import PolicyRunPaths
        from datp.core import PolicyRunId

        assert dataclasses.is_dataclass(PolicyRunPaths)
        field_names = {f.name for f in dataclasses.fields(PolicyRunPaths)}
        assert "run" in field_names, "PolicyRunPaths must have run field"
        hints = typing.get_type_hints(PolicyRunPaths)
        assert hints["run"] is PolicyRunId, (
            f"PolicyRunPaths.run must be PolicyRunId, got {hints['run']}"
        )

    def test_policy_run_paths_has_metrics_path(self) -> None:
        """Confirm PolicyRunPaths exposes the metrics file path."""
        from datp.artifacts import PolicyRunPaths

        field_names = {f.name for f in dataclasses.fields(PolicyRunPaths)}
        assert "metrics_path" in field_names, (
            "PolicyRunPaths must have metrics_path field"
        )

    def test_policy_run_paths_has_result_dir_and_log_dir(self) -> None:
        """Confirm PolicyRunPaths exposes directories for results and logs."""
        from datp.artifacts import PolicyRunPaths

        field_names = {f.name for f in dataclasses.fields(PolicyRunPaths)}
        assert "result_dir" in field_names, "PolicyRunPaths must have result_dir field"
        assert "log_dir" in field_names, "PolicyRunPaths must have log_dir field"

    def test_score_cell_paths_has_cell(self) -> None:
        """Confirm ScoreCellPaths references TrainingCellId."""
        from datp.artifacts import ScoreCellPaths
        from datp.core import TrainingCellId

        assert dataclasses.is_dataclass(ScoreCellPaths)
        field_names = {f.name for f in dataclasses.fields(ScoreCellPaths)}
        assert "cell" in field_names, "ScoreCellPaths must have cell field"
        hints = typing.get_type_hints(ScoreCellPaths)
        assert hints["cell"] is TrainingCellId, (
            f"ScoreCellPaths.cell must be TrainingCellId, got {hints['cell']}"
        )

    def test_score_cell_paths_has_manifest_path(self) -> None:
        """Confirm ScoreCellPaths exposes the cells manifest path."""
        from datp.artifacts import ScoreCellPaths

        field_names = {f.name for f in dataclasses.fields(ScoreCellPaths)}
        assert "manifest_path" in field_names, (
            "ScoreCellPaths must have manifest_path field"
        )

    def test_score_cell_paths_has_score_dir(self) -> None:
        """Confirm ScoreCellPaths exposes the score storage location."""
        from datp.artifacts import ScoreCellPaths

        field_names = {f.name for f in dataclasses.fields(ScoreCellPaths)}
        assert "score_dir" in field_names, "ScoreCellPaths must have score_dir field"

    def test_score_cell_paths_no_old_fields(self) -> None:
        """Confirm legacy loose naming is not used in ScoreCellPaths."""
        from datp.artifacts import ScoreCellPaths

        field_names = {f.name for f in dataclasses.fields(ScoreCellPaths)}
        old_names = {"checkpoint", "checkpoint_dir", "score_root", "checkpoint_root"}
        present = old_names & field_names
        assert not present, f"ScoreCellPaths must not have old field names: {present}"


class TestDatasetPartitionContracts:
    """Tests verifying data serialization contracts for dataset partitioning."""

    def test_partition_result_is_pydantic(self) -> None:
        """Confirm PartitionResult is a valid Pydantic model for schema verification."""
        from pydantic import BaseModel

        from datp.data import PartitionResult

        assert issubclass(PartitionResult, BaseModel), (
            "PartitionResult is a boundary schema and must be a Pydantic model"
        )

    def test_audit_client_is_pydantic(self) -> None:
        """Confirm AuditClient is a valid Pydantic model for audit logging."""
        from pydantic import BaseModel

        from datp.data import AuditClient

        assert issubclass(AuditClient, BaseModel), (
            "AuditClient is a boundary schema and must be a Pydantic model"
        )


class TestEvaluationResultArchitecture:
    """Tests verifying structured evaluation results metrics and structures."""

    def test_evaluation_result_has_run(self) -> None:
        """Confirm EvaluationResult links back to the PolicyRunId."""
        from datp.core import PolicyRunId
        from datp.evaluation import EvaluationResult

        assert dataclasses.is_dataclass(EvaluationResult)
        field_names = {f.name for f in dataclasses.fields(EvaluationResult)}
        assert "run" in field_names, "EvaluationResult must have run field"
        hints = typing.get_type_hints(EvaluationResult)
        assert hints["run"] is PolicyRunId, (
            f"EvaluationResult.run must be PolicyRunId, got {hints['run']}"
        )

    def test_evaluation_result_has_clients_as_tuple(self) -> None:
        """Confirm clients list is stored as a tuple to ensure immutability."""
        from datp.evaluation import EvaluationResult

        field_names = {f.name for f in dataclasses.fields(EvaluationResult)}
        assert "clients" in field_names, "EvaluationResult must have clients field"
        hints = typing.get_type_hints(EvaluationResult)
        clients_hint = hints["clients"]
        origin = typing.get_origin(clients_hint)
        assert origin is tuple, (
            f"EvaluationResult.clients must be a tuple type, got origin={origin}"
        )

    def test_evaluation_result_has_dispersion(self) -> None:
        """Confirm EvaluationResult exposes client metrics dispersion metrics."""
        from datp.evaluation import DispersionMetrics, EvaluationResult

        field_names = {f.name for f in dataclasses.fields(EvaluationResult)}
        assert "dispersion" in field_names, (
            "EvaluationResult must have dispersion field"
        )
        hints = typing.get_type_hints(EvaluationResult)
        assert hints["dispersion"] is DispersionMetrics, (
            f"EvaluationResult.dispersion must be DispersionMetrics, got {hints['dispersion']}"
        )

    def test_client_metrics_absent(self) -> None:
        """Confirm obsolete ClientMetrics type is removed."""
        module = importlib.import_module("datp.evaluation")
        assert not hasattr(module, "ClientMetrics"), (
            "ClientMetrics must not exist — use ClientEvaluationRecord instead"
        )

    def test_fpr_dispersion_bundle_absent(self) -> None:
        """Confirm obsolete FPRDispersionBundle type is removed."""
        module = importlib.import_module("datp.evaluation")
        assert not hasattr(module, "FPRDispersionBundle"), (
            "FPRDispersionBundle must not exist — use DispersionMetrics instead"
        )


class TestCLIAccumulatorsAllowlisted:
    """Tests verifying that CLI accumulator models are strictly private."""

    def test_stage_report_is_private(self) -> None:
        """Confirm _StageReport class is kept private within the command module."""
        module = importlib.import_module("datp.cli")
        assert hasattr(module, "_StageReport"), (
            "_StageReport must exist as a private CLI accumulator in datp.cli"
        )
        assert not hasattr(module, "StageReport"), (
            "StageReport (without underscore) must not be exported — keep it private as _StageReport"
        )

    def test_status_report_is_private(self) -> None:
        """Confirm _StatusReport class is kept private within the command module."""
        module = importlib.import_module("datp.cli")
        assert hasattr(module, "_StatusReport"), (
            "_StatusReport must exist as a private CLI accumulator in datp.cli"
        )
        assert not hasattr(module, "StatusReport"), (
            "StatusReport (without underscore) must not be exported — keep it private as _StatusReport"
        )


def _all_py_files_no_scientific_policy_leaks(root: Path) -> list[Path]:
    """Collect all python files recursively under a given root directory."""
    return sorted(root.rglob("*.py"))


def _source_no_scientific_policy_leaks(path: Path) -> str:
    """Read and return the text content of a file."""
    return path.read_text()


class TestNoLocalRegimePolicyConstants:
    """Tests verifying that baseline policies are defined centrally, not locally."""

    _PATTERN = re.compile(r"^_REGIME_\w*BASELINES\s*=", re.MULTILINE)

    def test_no_local_regime_policy_constants_in_reporting(self) -> None:
        """Ensure reporting modules do not define local baseline policy lists."""
        for path in _all_py_files_no_scientific_policy_leaks(_SRC_ROOT / "reporting"):
            src = _source_no_scientific_policy_leaks(path)
            matches = self._PATTERN.findall(src)
            assert not matches, (
                f"{path.relative_to(_SRC_ROOT)}: "
                f"found local _REGIME_*BASELINES: {matches!r}. "
                "Move to datp.enums."
            )

    def test_no_local_regime_policy_constants_in_validation(self) -> None:
        """Ensure validation modules do not define local baseline policy lists."""
        for path in _all_py_files_no_scientific_policy_leaks(_SRC_ROOT / "validation"):
            src = _source_no_scientific_policy_leaks(path)
            matches = self._PATTERN.findall(src)
            assert not matches, (
                f"{path.relative_to(_SRC_ROOT)}: "
                f"found local _REGIME_*BASELINES: {matches!r}. "
                "Move to datp.enums."
            )

    def test_no_local_regime_policy_constants_in_analyses(self) -> None:
        """Ensure analyses modules do not define local baseline policy lists."""
        for path in _all_py_files_no_scientific_policy_leaks(_SRC_ROOT / "analyses"):
            src = _source_no_scientific_policy_leaks(path)
            matches = self._PATTERN.findall(src)
            assert not matches, (
                f"{path.relative_to(_SRC_ROOT)}: "
                f"found local _REGIME_*BASELINES: {matches!r}. "
                "Move to datp.enums."
            )


class TestNoLocalStatsBaselines:
    """Tests verifying that stale stats baselines constants are removed."""

    _PATTERN = re.compile(r"^_STATS_BASELINES\w*\s*=", re.MULTILINE)

    def test_no_local_stats_baselines_in_reporting(self) -> None:
        """Ensure reporting does not reference obsolete stats baselines lists."""
        for path in _all_py_files_no_scientific_policy_leaks(_SRC_ROOT / "reporting"):
            src = _source_no_scientific_policy_leaks(path)
            matches = self._PATTERN.findall(src)
            assert not matches, (
                f"{path.relative_to(_SRC_ROOT)}: "
                f"found stale _STATS_BASELINES* constant: {matches!r}. "
                "Remove — policy iteration uses ThresholdPolicy directly."
            )

    def test_no_local_stats_baselines_in_validation(self) -> None:
        """Ensure validation does not reference obsolete stats baselines lists."""
        for path in _all_py_files_no_scientific_policy_leaks(_SRC_ROOT / "validation"):
            src = _source_no_scientific_policy_leaks(path)
            matches = self._PATTERN.findall(src)
            assert not matches, (
                f"{path.relative_to(_SRC_ROOT)}: "
                f"found stale _STATS_BASELINES* constant: {matches!r}. "
                "Remove — policy iteration uses ThresholdPolicy directly."
            )


class TestNoAttrsDefineInSrc:
    """Tests verifying attrs.define is not used in src."""

    _PATTERN = re.compile(r"@attrs\.define|attrs\.define\(")

    def test_no_attrs_define_in_src(self) -> None:
        """Ensure no source code file contains attrs.define decorator calls."""
        violations: list[str] = []
        for path in _all_py_files_no_scientific_policy_leaks(_SRC_ROOT):
            src = _source_no_scientific_policy_leaks(path)
            if self._PATTERN.search(src):
                violations.append(str(path.relative_to(_SRC_ROOT)))
        assert not violations, (
            f"Found attrs.define in {violations}. "
            "Use @dataclass(frozen=True, slots=True) for internal specs."
        )


class TestNoHardcodedOutputPathsInReporting:
    """Tests verifying that reporting module does not use hardcoded folder paths."""

    def _check_no_hardcoded_path(
        self, src: str, literal: str, allow_module: str
    ) -> None:
        """Helper method to verify a path literal is not present in source code."""
        pattern = re.compile(rf'/ "{re.escape(literal)}"')
        matches = pattern.findall(src)
        assert not matches, (
            f"Hardcoded path segment {literal!r} found in {allow_module}. "
            f"Use the canonical directory constant instead."
        )

    def test_no_hardcoded_figures_in_build(self) -> None:
        """Ensure 'figures' directory name is not hardcoded in reporting build."""
        build_py = _SRC_ROOT / "reporting" / "build.py"
        self._check_no_hardcoded_path(
            _source_no_scientific_policy_leaks(build_py), "figures", "reporting/build.py"
        )

    def test_no_hardcoded_tables_in_build(self) -> None:
        """Ensure 'tables' directory name is not hardcoded in reporting build."""
        build_py = _SRC_ROOT / "reporting" / "build.py"
        self._check_no_hardcoded_path(_source_no_scientific_policy_leaks(build_py), "tables", "reporting/build.py")

    def test_no_hardcoded_analysis_in_build(self) -> None:
        """Ensure 'analysis' directory name is not hardcoded in reporting build."""
        build_py = _SRC_ROOT / "reporting" / "build.py"
        self._check_no_hardcoded_path(
            _source_no_scientific_policy_leaks(build_py), "analysis", "reporting/build.py"
        )


class TestNoHardcodedFigureNamesInBuild:
    """Tests verifying that figure output names are not hardcoded."""

    _PATTERN = re.compile(r'"figure_[1-4]"')

    def test_no_hardcoded_figure_names_in_build(self) -> None:
        """Ensure figure names match canonical enums rather than hardcoded strings."""
        build_py = _SRC_ROOT / "reporting" / "build.py"
        src = _source_no_scientific_policy_leaks(build_py)
        matches = self._PATTERN.findall(src)
        assert not matches, (
            f"Hardcoded figure names {matches!r} in reporting/build.py. "
            "Use FigureName enum from datp.enums."
        )


class TestNoOsPathJoinInSrc:
    """Tests verifying that os.path.join is not used in src."""

    _PATTERN = re.compile(r"\bos\.path\.join\b")

    def test_no_os_path_join_in_src(self) -> None:
        """Ensure all source files utilize pathlib.Path rather than os.path.join."""
        violations: list[str] = []
        for path in _all_py_files_no_scientific_policy_leaks(_SRC_ROOT):
            src = _source_no_scientific_policy_leaks(path)
            if self._PATTERN.search(src):
                violations.append(str(path.relative_to(_SRC_ROOT)))
        assert not violations, (
            f"Found os.path.join in {violations}. Use pathlib.Path instead."
        )


class TestAttrsRemovedFromDependencies:
    """Tests verifying attrs package is removed from dependencies."""

    def test_attrs_not_in_pyproject_dependencies(self) -> None:
        """Ensure pyproject.toml does not declare attrs dependency."""
        pyproject = _SRC_ROOT.parent.parent / "pyproject.toml"
        src = pyproject.read_text()

        assert '"attrs"' not in src, (
            "attrs is still listed in pyproject.toml dependencies. "
            "Remove it — all internal specs now use @dataclass."
        )


class TestReportingUsesCorePolicies:
    """Tests verifying that reporting builds depend strictly on canonical core types."""

    def test_build_uses_threshold_policy_not_controlled_baselines(self) -> None:
        """Ensure build.py iterates over ThresholdPolicy rather than legacy baselines."""
        build_py = _SRC_ROOT / "reporting" / "build.py"
        src = _source_no_scientific_policy_leaks(build_py)
        assert "CONTROLLED_BASELINES" not in src, (
            "CONTROLLED_BASELINES is stale; use ThresholdPolicy directly"
        )
        assert "ThresholdPolicy" in src, (
            "reporting/build.py must use ThresholdPolicy for policy iteration"
        )

    def test_build_imports_figure_name(self) -> None:
        """Ensure build.py imports and uses FigureName enum."""
        build_py = _SRC_ROOT / "reporting" / "build.py"
        src = _source_no_scientific_policy_leaks(build_py)
        assert "FigureName" in src, (
            "reporting/build.py must use FigureName from datp.enums"
        )

    def test_build_imports_evidence_role(self) -> None:
        """Ensure build.py imports and uses EvidenceRole enum."""
        build_py = _SRC_ROOT / "reporting" / "build.py"
        src = _source_no_scientific_policy_leaks(build_py)
        assert "EvidenceRole" in src, (
            "reporting/build.py must use EvidenceRole from datp.enums"
        )

    def test_build_imports_seed_scope(self) -> None:
        """Ensure build.py imports and uses SeedScope enum."""
        build_py = _SRC_ROOT / "reporting" / "build.py"
        src = _source_no_scientific_policy_leaks(build_py)
        assert "SeedScope" in src, (
            "reporting/build.py must use SeedScope from datp.enums"
        )


class TestSha256Bytes:
    """Tests verifying the deterministic SHA256 bytes hashing utility."""

    def test_deterministic(self) -> None:
        """Verify that hashing identical bytes yields the identical hash string."""
        payload = b"hello world"
        assert sha256_bytes(payload) == sha256_bytes(payload)

    def test_different_content_different_hash(self) -> None:
        """Ensure distinct byte contents result in different hashes."""
        assert sha256_bytes(b"a") != sha256_bytes(b"b")

    def test_output_is_64_char_hex(self) -> None:
        """Ensure output hash is a valid 64-character hexadecimal representation."""
        assert len(sha256_bytes(b"test")) == 64
        int(sha256_bytes(b"test"), 16)


class TestHashFile:
    """Tests verifying file-based hashing functionality and nonexistent file handling."""

    def test_deterministic(self, tmp_path: Path) -> None:
        """Verify file hashing is deterministic for identical file contents."""
        f = tmp_path / "data.bin"
        f.write_bytes(b"deterministic content")
        assert hash_file(f) == hash_file(f)

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        """Ensure files with different contents yield different hash strings."""
        f1 = tmp_path / "a.bin"
        f2 = tmp_path / "b.bin"
        f1.write_bytes(b"content A")
        f2.write_bytes(b"content B")
        assert hash_file(f1) != hash_file(f2)

    def test_missing_file_returns_missing_sentinel(self, tmp_path: Path) -> None:
        """Confirm hashing a nonexistent file returns the 'MISSING' sentinel."""
        assert hash_file(tmp_path / "nonexistent.bin") == "MISSING"

    def test_empty_file(self, tmp_path: Path) -> None:
        """Verify hashing an empty file returns the correct SHA256 of empty bytes."""
        f = tmp_path / "empty.bin"
        f.write_bytes(b"")
        result = hash_file(f)
        assert len(result) == 64
        assert (
            result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )

    def test_output_is_64_char_hex(self, tmp_path: Path) -> None:
        """Confirm output hash for a valid file is 64 characters long."""
        f = tmp_path / "f.bin"
        f.write_bytes(b"test")
        assert len(hash_file(f)) == 64


class TestHashJsonable:
    """Tests verifying dict/list JSON-serializable object hashing."""

    def test_deterministic(self) -> None:
        """Verify jsonable hashing is deterministic for identical structured payloads."""
        payload = {"a": 1, "b": [2, 3]}
        assert hash_jsonable(payload) == hash_jsonable(payload)

    def test_sort_key_independent(self) -> None:
        """Ensure hashing is independent of key order for dictionary inputs."""
        assert hash_jsonable({"b": 2, "a": 1}) == hash_jsonable({"a": 1, "b": 2})

    def test_different_content_different_hash(self) -> None:
        """Ensure changing JSON dictionary contents changes the hash."""
        assert hash_jsonable({"x": 1}) != hash_jsonable({"x": 2})

    def test_nested_structures(self) -> None:
        """Verify nested structures can be hashed successfully."""
        h = hash_jsonable({"nested": {"list": [1, 2, 3]}, "str": "hello"})
        assert len(h) == 64

    def test_non_serializable_falls_back_to_str(self, tmp_path: Path) -> None:
        """Confirm fallback to string representation for non-serializable types."""
        result = hash_jsonable({tmp_path})
        assert len(result) == 64


class TestGitCommit:
    """Tests verifying Git commit SHA-1 retrieval."""

    def test_returns_hex_or_sentinel(self) -> None:
        """Ensure git commit retrieval returns a valid 40-character hex or fallback string."""
        result = git_commit()
        assert len(result) == 40 or result == "GIT_UNAVAILABLE"


class TestSourceHash:
    """Tests verifying source code file bundle hashing."""

    def test_deterministic(self, tmp_path: Path) -> None:
        """Ensure source hash is deterministic for a constant set of file paths."""
        f = tmp_path / "src.py"
        f.write_text("print(1)")
        assert source_hash([f]) == source_hash([f])

    def test_different_content_different_hash(self, tmp_path: Path) -> None:
        """Verify modifying source file content alters the computed source hash."""
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("x=1")
        f2.write_text("x=2")
        assert source_hash([f1]) != source_hash([f2])

    def test_multiple_files(self, tmp_path: Path) -> None:
        """Verify that source hash accounts for all input files in the list."""
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("x=1")
        f2.write_text("y=2")
        h_both = source_hash([f1, f2])
        h_one = source_hash([f1])
        assert h_both != h_one

    def test_path_order_matters(self, tmp_path: Path) -> None:
        """Confirm file sequence order affects the compiled source hash."""
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("x=1")
        f2.write_text("y=2")
        assert source_hash([f1, f2]) != source_hash([f2, f1])


class TestArrayHash:
    """Tests verifying NumPy array hashing and dtype normalization."""

    def test_deterministic(self) -> None:
        """Verify array hashing is deterministic for a constant NumPy array."""
        arr = np.array([1.0, 2.0, 3.0])
        assert array_hash(arr) == array_hash(arr)

    def test_different_content_different_hash(self) -> None:
        """Ensure distinct array content changes the array hash."""
        assert array_hash(np.array([1.0])) != array_hash(np.array([2.0]))

    def test_dtype_normalization_float32_to_float64(self) -> None:
        """Verify array hashing normalizes float32 and float64 arrays to same hash."""
        arr32 = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        arr64 = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        assert array_hash(arr32) == array_hash(arr64)

    def test_output_is_64_char_hex(self) -> None:
        """Ensure array hash output is a 64-character hex string."""
        assert len(array_hash(np.array([1.0]))) == 64

    def test_multidimensional(self) -> None:
        """Verify multidimensional arrays are flattened or normalized for hashing."""
        arr = np.array([[1.0, 2.0], [3.0, 4.0]])
        assert len(array_hash(arr)) == 64


class TestUtcTimestamp:
    """Tests verifying ISO-formatted UTC timestamp generation."""

    def test_returns_iso_format_string(self) -> None:
        """Confirm utc_timestamp returns a valid ISO-8601 datetime string."""
        ts = utc_timestamp()
        assert isinstance(ts, str)
        assert "T" in ts
        assert "+" in ts or "Z" in ts


class TestProvenanceConstants:
    """Tests verifying static provenance sentinel constants."""

    def test_missing_manifest_hash_is_sentinel_string(self) -> None:
        """Ensure MISSING_MANIFEST_HASH is the correct string sentinel."""
        assert isinstance(ProvenanceSentinel.MISSING_MANIFEST_HASH, str)
        assert "MISSING" in ProvenanceSentinel.MISSING_MANIFEST_HASH


def _seed_record(
    *,
    training_seed: int,
    poisoning_seed: int,
    client_idx: int,
    scope_idx: int,
) -> SeedRecord:
    """Helper function to build a SeedRecord fixture."""
    return SeedRecord(
        pair=SeedPair(
            training_seed=training_seed,
            poisoning_seed=poisoning_seed,
        ),
        client_idx=client_idx,
        scope_idx=scope_idx,
    )


class TestSeedRecord:
    """Tests verifying entropy and immutability properties of SeedRecord."""

    def test_entropy_matches_inputs(self) -> None:
        """Verify that SeedRecord entropy matches the input seeds and indices."""
        record = _seed_record(
            training_seed=0, poisoning_seed=100, client_idx=3, scope_idx=0
        )
        assert record.entropy == (0, 100, 3, 0)

    def test_frozen_immutable(self) -> None:
        """Ensure SeedRecord fields are frozen and cannot be modified."""
        record = _seed_record(
            training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0
        )
        with pytest.raises(Exception):
            setattr(record, "training_seed", 99)

    def test_entropy_is_tuple_of_four(self) -> None:
        """Verify that SeedRecord entropy is represented as a 4-tuple."""
        record = _seed_record(
            training_seed=1, poisoning_seed=101, client_idx=2, scope_idx=1
        )
        assert isinstance(record.entropy, tuple)
        assert len(record.entropy) == 4


class TestDeriveSeedRecord:
    """Tests verifying derivation of SeedRecord from SeedPair."""

    def test_returns_correct_record(self) -> None:
        """Verify derived SeedRecord fields correspond to the source seeds and indices."""
        record = SeedRecord(
            pair=SeedPair(training_seed=2, poisoning_seed=102),
            client_idx=5,
            scope_idx=1,
        )
        assert record.training_seed == 2
        assert record.poisoning_seed == 102
        assert record.client_idx == 5
        assert record.scope_idx == 1


class TestMakeRng:
    """Tests verifying RNG generation and sequence properties using derived seed records."""

    def test_returns_numpy_generator(self) -> None:
        """Verify make_seed_rng return value is a numpy Generator instance."""
        rng = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0)
        )
        assert isinstance(rng, np.random.Generator)

    def test_same_inputs_produce_identical_sequences(self) -> None:
        """Confirm that identical seed records produce identical RNG sequences."""
        rng1 = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0)
        )
        rng2 = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0)
        )
        assert np.array_equal(rng1.random(10), rng2.random(10))

    def test_different_client_idx_produces_different_sequences(self) -> None:
        """Confirm that changing client index changes the generated RNG sequence."""
        rng0 = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0)
        )
        rng1 = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=100, client_idx=1, scope_idx=0)
        )
        assert not np.array_equal(rng0.random(10), rng1.random(10))

    def test_different_training_seed_produces_different_sequences(self) -> None:
        """Confirm that changing training seed changes the generated RNG sequence."""
        rng0 = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0)
        )
        rng1 = make_seed_rng(
            _seed_record(training_seed=1, poisoning_seed=100, client_idx=0, scope_idx=0)
        )
        assert not np.array_equal(rng0.random(10), rng1.random(10))

    def test_different_poisoning_seed_produces_different_sequences(self) -> None:
        """Confirm that changing poisoning seed changes the generated RNG sequence."""
        rng0 = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0)
        )
        rng1 = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=101, client_idx=0, scope_idx=0)
        )
        assert not np.array_equal(rng0.random(10), rng1.random(10))

    def test_different_child_indices_produce_different_sequences(self) -> None:
        """Confirm that specifying a child index produces a distinct RNG sequence."""
        rng0 = make_seed_rng(
            _seed_record(
                training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0
            ),
            child_index=0,
        )
        rng1 = make_seed_rng(
            _seed_record(
                training_seed=0, poisoning_seed=100, client_idx=0, scope_idx=0
            ),
            child_index=1,
        )
        assert not np.array_equal(rng0.random(10), rng1.random(10))

    def test_no_integer_addition_pattern(self) -> None:
        """Ensure no overlaps occur between configurations that sum to the same value."""
        rng_a = make_seed_rng(
            _seed_record(training_seed=0, poisoning_seed=101, client_idx=0, scope_idx=0)
        )
        rng_b = make_seed_rng(
            _seed_record(training_seed=1, poisoning_seed=100, client_idx=0, scope_idx=0)
        )
        assert not np.array_equal(rng_a.random(20), rng_b.random(20))

    def test_all_seed_pairs_produce_distinct_sequences(self) -> None:
        """Confirm that paired seed-sequence generation is globally distinct."""
        training_seeds = tuple(range(10))
        poisoning_seeds = tuple(range(100, 110))
        sequences = []
        for ts, ps in zip(training_seeds, poisoning_seeds):
            rng = make_seed_rng(
                _seed_record(
                    training_seed=ts, poisoning_seed=ps, client_idx=0, scope_idx=0
                )
            )
            sequences.append(rng.random(10).tolist())

        assert len(sequences) == len({tuple(s) for s in sequences})


def test_set_seeds_makes_python_random_deterministic() -> None:
    """Verify set_seeds sets a deterministic python random state."""
    set_seeds(0)
    first = random.getstate()
    set_seeds(0)
    second = random.getstate()
    assert first == second


def test_numpy_generator_fixture_is_deterministic() -> None:
    """Verify numpy default_rng instantiation behaves deterministically after setting seeds."""
    set_seeds(0)
    rng = np.random.default_rng(0)
    first = rng.random(4)
    set_seeds(0)
    rng = np.random.default_rng(0)
    second = rng.random(4)
    assert np.array_equal(first, second)


def test_set_seeds_makes_torch_deterministic() -> None:
    """Verify set_seeds makes PyTorch CPU/GPU operations deterministic."""
    set_seeds(0)
    first = torch.randn(4)
    set_seeds(0)
    second = torch.randn(4)
    assert torch.equal(first, second)


def test_set_seeds_sets_cudnn_flags() -> None:
    """Verify set_seeds enables cuDNN determinism and disables benchmark flags."""
    set_seeds(0)
    assert torch.backends.cudnn.deterministic is True
    assert torch.backends.cudnn.benchmark is False


def test_set_seeds_sets_matmul_precision() -> None:
    """Verify set_seeds configures float32 matmul precision to high."""
    set_seeds(0)
    assert torch.get_float32_matmul_precision() == "high"
