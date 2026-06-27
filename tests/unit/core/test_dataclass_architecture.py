"""Architecture compliance tests for dataclass conventions and invariants."""

from __future__ import annotations

import ast
import re
from pathlib import Path

_SRC_ROOT = Path(__file__).parent.parent.parent.parent / "src" / "datp"
_TESTS_ROOT = Path(__file__).parent.parent.parent


_NAMEDTUPLE_TEST_ALLOWLIST: frozenset[str] = frozenset(
    {
        "e2e/diagnostic/test_diagnostic_e2e.py",
    }
)


_DEFAULTS_ALLOWLIST: frozenset[tuple[str, str, str]] = frozenset(
    {
        ("federated/simulation.py", "SimClientConfig", "client_cls"),
        ("federated/simulation.py", "SimClientConfig", "client_extra_kwargs"),
        ("federated/simulation.py", "SimClientConfig", "encoder_only"),
        ("federated/simulation.py", "SimClientConfig", "score_after"),
        ("validation/results.py", "CellPanel", "cv_fpr"),
        ("validation/results.py", "CellPanel", "cv_tpr"),
        ("validation/results.py", "CellPanel", "macro_f1_mean"),
        ("validation/results.py", "CellPanel", "macro_f1_p10"),
        ("validation/results.py", "CellPanel", "auroc_mean"),
        ("validation/results.py", "CellPanel", "pr_auc_mean"),
        ("validation/results.py", "CellPanel", "mean_fpr"),
        ("validation/results.py", "CellPanel", "std_fpr"),
        ("validation/results.py", "CellPanel", "iqr_fpr"),
        ("validation/results.py", "CellPanel", "worst_client_fpr"),
        ("validation/results.py", "CellPanel", "worst_client_tpr"),
        ("validation/results.py", "CellPanel", "worst_client_macro_f1"),
        ("validation/results.py", "CellPanel", "worst_client_balanced_accuracy"),
        ("validation/results.py", "CellPanel", "convergence_round"),
        ("validation/results.py", "CellPanel", "tau_global"),
        ("validation/results.py", "CellPanel", "coverage_ratio"),
        ("validation/results.py", "AuditAccumulator", "manifest_records"),
        ("validation/results.py", "AuditAccumulator", "client_records"),
        ("validation/results.py", "AuditAccumulator", "attack_records"),
        ("validation/results.py", "AuditAccumulator", "threshold_records"),
        ("validation/results.py", "AuditAccumulator", "recon_records"),
        ("validation/results.py", "AuditAccumulator", "denominator_records"),
        ("validation/results.py", "AuditAccumulator", "convergence_records"),
        ("validation/results.py", "AuditAccumulator", "cluster_records"),
        ("validation/results.py", "AuditAccumulator", "companion_records"),
        ("validation/results.py", "AuditAccumulator", "worst_client_records"),
        ("validation/results.py", "AuditAccumulator", "partition_audits"),
        ("validation/results.py", "AuditAccumulator", "invariant_inputs"),
        ("validation/results.py", "AuditAccumulator", "score_hashes_by_cell"),
        ("validation/results.py", "AuditAccumulator", "recomputation_records"),
        ("validation/results.py", "AuditAccumulator", "cell_panel"),
        ("validation/results.py", "AuditAccumulator", "warnings"),
        ("validation/results.py", "AuditAccumulator", "missing_confusion_warned"),
        ("experiments/sweep.py", "SweepResult", "total"),
        ("experiments/sweep.py", "SweepResult", "completed"),
        ("experiments/sweep.py", "SweepResult", "skipped"),
        ("experiments/sweep.py", "SweepResult", "failed"),
        ("cli/commands.py", "_StageReport", "complete"),
        ("cli/commands.py", "_StageReport", "missing"),
        ("cli/commands.py", "_StageReport", "aborted"),
        ("cli/commands.py", "_StatusReport", "stage_reports"),
        ("reporting/tables.py", "ResultTable", "rows"),
        ("reporting/tables.py", "ResultTable", "footnote"),
        ("core/tracking.py", "_TrackingPayload", "payload"),
        ("artifacts/layout.py", "ScoreCellPaths", "checkpoint_round"),
        ("artifacts/layout.py", "PolicyRunPaths", "checkpoint_round"),
        ("data/specs.py", "DatasetSpec", "cap_policy"),
        ("data/specs.py", "DatasetSpec", "family_map"),
        ("data/specs.py", "DatasetSpec", "device_ids"),
        ("data/specs.py", "DatasetSpec", "attack_family_dirs"),
        ("data/specs.py", "DatasetSpec", "expected_client_count"),
        ("attacks/metrics/inference.py", "HolmResult", "descriptive_only"),
        ("attacks/score_containers.py", "ScoreCollection", "n_min"),
        ("attacks/planning/bounded_sweep_matrix.py", "SweepCellSpec", "target_scope"),
        ("attacks/types.py", "MetricEngineInput", "mu_flag_threshold"),
        ("attacks/types.py", "MetricEngineInput", "auroc_set"),
        ("attacks/execution/bounded_sweep_cell.py", "SweepCellConfig", "auroc_set"),
        ("attacks/execution/bounded_sweep_cell.py", "SweepCellConfig", "scope_idx"),
        ("attacks/execution/bounded_sweep_cell.py", "SweepCellConfig", "q"),
        ("attacks/execution/bounded_sweep_cell.py", "SweepCellConfig", "cluster_seed"),
        ("attacks/execution/cell_runner.py", "InjectionSpec", "scope_idx"),
        ("attacks/execution/cell_runner.py", "InjectionSpec", "tail_mass"),
        (
            "attacks/threshold_recomputation/cluster_threshold_recompute.py",
            "ClusterHyperparams",
            "k",
        ),
        (
            "attacks/threshold_recomputation/cluster_threshold_recompute.py",
            "ClusterHyperparams",
            "n_init",
        ),
        (
            "attacks/threshold_recomputation/cluster_threshold_recompute.py",
            "ClusterHyperparams",
            "max_iter",
        ),
        (
            "attacks/threshold_recomputation/cluster_threshold_recompute.py",
            "ClusterHyperparams",
            "random_state",
        ),
        (
            "attacks/threshold_recomputation/cluster_threshold_recompute.py",
            "ClusterHyperparams",
            "n_min",
        ),
        (
            "attacks/threshold_recomputation/cluster_threshold_recompute.py",
            "ClusterHyperparams",
            "seed",
        ),
        ("attacks/metrics/inference.py", "BootstrapConfig", "ci"),
        ("attacks/metrics/inference.py", "BootstrapConfig", "n_bootstrap"),
        ("attacks/metrics/inference.py", "BootstrapConfig", "analysis_seed"),
        ("attacks/metrics/inference.py", "HolmConfig", "alpha"),
        ("attacks/metrics/inference.py", "InferenceInput", "bootstrap_config"),
        ("attacks/metrics/inference.py", "InferenceInput", "holm_config"),
        ("thresholding/thresholds.py", "_DeriveInput", "seed"),
        ("attacks/manifests/run_logger.py", "ManifestBuildRequest", "local_epochs"),
        ("attacks/manifests/run_logger.py", "ManifestBuildRequest", "checkpoint_round"),
        ("attacks/manifests/run_logger.py", "ManifestBuildRequest", "injection_rule"),
        ("attacks/manifests/run_logger.py", "ManifestBuildRequest", "reservoir_mode"),
        ("federated/factories.py", "ClientFactoryConfig", "prepared_dir"),
        ("federated/factories.py", "ClientFactoryConfig", "model_cls"),
        ("federated/factories.py", "ClientFactoryConfig", "client_cls"),
        ("federated/factories.py", "ClientFactoryConfig", "extra_kwargs"),
        ("federated/factories.py", "ClientFactoryConfig", "seed"),
        ("federated/strategies.py", "FedAvgConfig", "initial_parameters"),
        ("federated/strategies.py", "FedAvgConfig", "checkpoint_milestones"),
        ("federated/strategies.py", "FedAvgConfig", "convergence_mode"),
        ("federated/strategies.py", "FedAvgConfig", "checkpoint_disk_dirs"),
        ("federated/simulation.py", "FlSimulationRequest", "prepared_dir"),
        ("federated/simulation.py", "FlSimulationRequest", "client_config"),
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
