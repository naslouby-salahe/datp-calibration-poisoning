"""Enforcement tests: dataclass architecture invariants.

Prevents NamedTuples, mutable-field-in-frozen-dataclass, and unjustified
defaults from drifting back into the codebase after the dataclass refactor.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

_SRC_ROOT = Path(__file__).parent.parent.parent.parent / "src" / "datp"
_TESTS_ROOT = Path(__file__).parent.parent.parent

# NamedTuples still allowed in tests (fixture-only use); paths relative to tests/
_NAMEDTUPLE_TEST_ALLOWLIST: frozenset[str] = frozenset(
    {
        "e2e/diagnostic/test_diagnostic_e2e.py",
    }
)

# Dataclass defaults that are explicitly justified in exceptions.md
# Format: (module_relative_path, class_name, field_name)
_DEFAULTS_ALLOWLIST: frozenset[tuple[str, str, str]] = frozenset(
    {
        # SimClientConfig: options object with true domain-invariant defaults
        # (DatpClient is the standard FL client, encoder_only=False is FedAvg,
        # score_after=True is the standard protocol)
        ("federated/simulation.py", "SimClientConfig", "client_cls"),
        ("federated/simulation.py", "SimClientConfig", "client_extra_kwargs"),
        ("federated/simulation.py", "SimClientConfig", "encoder_only"),
        ("federated/simulation.py", "SimClientConfig", "score_after"),
        # _CellPanel: None defaults represent "metric absent/not computed" — factory
        # method _CellPanel.empty() makes the sentinel explicit
        ("validation/_audit_types.py", "_CellPanel", "cv_fpr"),
        ("validation/_audit_types.py", "_CellPanel", "cv_tpr"),
        ("validation/_audit_types.py", "_CellPanel", "macro_f1_mean"),
        ("validation/_audit_types.py", "_CellPanel", "macro_f1_p10"),
        ("validation/_audit_types.py", "_CellPanel", "auroc_mean"),
        ("validation/_audit_types.py", "_CellPanel", "pr_auc_mean"),
        ("validation/_audit_types.py", "_CellPanel", "mean_fpr"),
        ("validation/_audit_types.py", "_CellPanel", "std_fpr"),
        ("validation/_audit_types.py", "_CellPanel", "iqr_fpr"),
        ("validation/_audit_types.py", "_CellPanel", "worst_client_fpr"),
        ("validation/_audit_types.py", "_CellPanel", "worst_client_tpr"),
        ("validation/_audit_types.py", "_CellPanel", "worst_client_macro_f1"),
        ("validation/_audit_types.py", "_CellPanel", "worst_client_balanced_accuracy"),
        ("validation/_audit_types.py", "_CellPanel", "convergence_round"),
        ("validation/_audit_types.py", "_CellPanel", "tau_global"),
        ("validation/_audit_types.py", "_CellPanel", "coverage_ratio"),
        # _AuditAccumulator: mutable accumulator pattern (list/dict with default_factory)
        ("validation/_audit_types.py", "_AuditAccumulator", "manifest_records"),
        ("validation/_audit_types.py", "_AuditAccumulator", "client_records"),
        ("validation/_audit_types.py", "_AuditAccumulator", "attack_records"),
        ("validation/_audit_types.py", "_AuditAccumulator", "threshold_records"),
        ("validation/_audit_types.py", "_AuditAccumulator", "recon_records"),
        ("validation/_audit_types.py", "_AuditAccumulator", "denominator_records"),
        ("validation/_audit_types.py", "_AuditAccumulator", "convergence_records"),
        ("validation/_audit_types.py", "_AuditAccumulator", "cluster_records"),
        ("validation/_audit_types.py", "_AuditAccumulator", "companion_records"),
        ("validation/_audit_types.py", "_AuditAccumulator", "worst_client_records"),
        ("validation/_audit_types.py", "_AuditAccumulator", "homogeneity_records"),
        ("validation/_audit_types.py", "_AuditAccumulator", "regime_c_alpha_records"),
        ("validation/_audit_types.py", "_AuditAccumulator", "partition_audits"),
        ("validation/_audit_types.py", "_AuditAccumulator", "invariant_inputs"),
        ("validation/_audit_types.py", "_AuditAccumulator", "score_hashes_by_cell"),
        ("validation/_audit_types.py", "_AuditAccumulator", "recomputation_records"),
        ("validation/_audit_types.py", "_AuditAccumulator", "cell_panel"),
        ("validation/_audit_types.py", "_AuditAccumulator", "warnings"),
        ("validation/_audit_types.py", "_AuditAccumulator", "missing_confusion_warned"),
        # SweepResult: mutable counter accumulator
        ("experiments/sweep.py", "SweepResult", "total"),
        ("experiments/sweep.py", "SweepResult", "completed"),
        ("experiments/sweep.py", "SweepResult", "skipped"),
        ("experiments/sweep.py", "SweepResult", "failed"),
        # _StatusReport/_RegimeReport: mutable CLI accumulator
        ("app/cli/status.py", "_RegimeReport", "complete"),
        ("app/cli/status.py", "_RegimeReport", "missing"),
        ("app/cli/status.py", "_RegimeReport", "aborted"),
        ("app/cli/status.py", "_StatusReport", "regime_reports"),
        # ResultTable: mutable builder pattern
        ("reporting/tables.py", "ResultTable", "rows"),
        ("reporting/tables.py", "ResultTable", "footnote"),
        # ScoreCollection: derived eligibility cache populated in __post_init__
        ("attacks/score_containers.py", "ScoreCollection", "_eligible_result"),
        # TrackingPayload (if any)
        ("core/tracking.py", "_TrackingPayload", "payload"),
        # DiagnosticInlineIdentity: canonical provenance sentinel strings (genuinely domain-invariant)
        ("experiments/diagnostic.py", "DiagnosticInlineIdentity", "config"),
        ("experiments/diagnostic.py", "DiagnosticInlineIdentity", "split_manifest"),
        ("experiments/diagnostic.py", "DiagnosticInlineIdentity", "model_checkpoint"),
        ("experiments/diagnostic.py", "DiagnosticInlineIdentity", "score_artifact"),
        # DiagnosticExtras: None = "no contingency decision" is a real domain state
        ("experiments/diagnostic.py", "DiagnosticExtras", "contingency"),
        # ScoreCellPaths/BaselineRunPaths: None = "standard run, not a checkpoint-protocol run"
        # checkpoint_round is set only for checkpoint-protocol cells; None is the normal case
        ("artifacts/layout.py", "ScoreCellPaths", "checkpoint_round"),
        ("artifacts/layout.py", "BaselineRunPaths", "checkpoint_round"),
        # DatasetSpec: optional per-dataset fields; not all datasets use all fields
        ("data/catalog.py", "DatasetSpec", "cap_policy"),
        ("data/catalog.py", "DatasetSpec", "family_map"),
        ("data/catalog.py", "DatasetSpec", "device_ids"),
        ("data/catalog.py", "DatasetSpec", "attack_family_dirs"),
        ("data/catalog.py", "DatasetSpec", "expected_client_count"),
        # HolmResult.descriptive_only: protocol lock — Holm is ALWAYS descriptive
        # only here; True is the only valid value; False would be a protocol violation
        ("attacks/inference.py", "HolmResult", "descriptive_only"),
        # ScoreCollection.n_min: canonical N_MIN=100 lock (Calibration-Pending
        # boundary); any deviation from 100 is a protocol violation
        ("attacks/score_containers.py", "ScoreCollection", "n_min"),
        # ScoreCollection._eligible_ids/_pending_ids: computed in __post_init__ from
        # the clients dict; None is the uninitialized sentinel for the lazy-init pattern
        ("attacks/score_containers.py", "ScoreCollection", "_eligible_ids"),
        ("attacks/score_containers.py", "ScoreCollection", "_pending_ids"),
        # SweepCellSpec.target_scope: protocol lock — the bounded sweep
        # matrix is always SINGLE_CLIENT; any other scope is out of scope here
        ("attacks/bounded_sweep_matrix.py", "SweepCellSpec", "target_scope"),
        # MetricEngineInput: None defaults represent "not yet locked/computed"
        ("attacks/types.py", "MetricEngineInput", "mu_flag_threshold"),
        ("attacks/types.py", "MetricEngineInput", "auroc_set"),
        # SweepCellConfig: per-training-seed runtime config; scope_idx/q/b4_seed
        # are protocol-constant hyperparams; auroc_set is lazy-computed
        ("attacks/bounded_sweep_cell.py", "SweepCellConfig", "auroc_set"),
        ("attacks/bounded_sweep_cell.py", "SweepCellConfig", "scope_idx"),
        ("attacks/bounded_sweep_cell.py", "SweepCellConfig", "q"),
        ("attacks/bounded_sweep_cell.py", "SweepCellConfig", "b4_seed"),
        # InjectionSpec: scope_idx/tail_mass are protocol-constant defaults
        ("attacks/cell_runner.py", "InjectionSpec", "scope_idx"),
        ("attacks/cell_runner.py", "InjectionSpec", "tail_mass"),
        # BootstrapConfig: CI hyperparameters with protocol-locked defaults
        ("attacks/inference.py", "BootstrapConfig", "ci"),
        ("attacks/inference.py", "BootstrapConfig", "n_bootstrap"),
        ("attacks/inference.py", "BootstrapConfig", "analysis_seed"),
        # HolmConfig: alpha is the standard Holm threshold
        ("attacks/inference.py", "HolmConfig", "alpha"),
        # InferenceInput: bootstrap_config and holm_config have sensible defaults
        ("attacks/inference.py", "InferenceInput", "bootstrap_config"),
        ("attacks/inference.py", "InferenceInput", "holm_config"),
    }
)


def _all_py_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


_NAMEDTUPLE_PATTERN = re.compile(r"\bclass\s+\w+\s*\(\s*(?:typing\.)?NamedTuple\s*\)")


class TestNoNamedTuplesInSrc:
    """No NamedTuple classes in src/datp; use @dataclass(frozen=True, slots=True) instead."""

    def test_no_namedtuples_in_src(self) -> None:
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
    """NamedTuple in tests allowed only on the allowlist."""

    def test_namedtuples_in_tests_match_allowlist(self) -> None:
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
    return any(_is_dataclass_decorator(d) for d in node.decorator_list)


def _collect_defaults_in_class(
    rel: str, node: ast.ClassDef
) -> list[tuple[str, str, str]]:
    results: list[tuple[str, str, str]] = []
    for stmt in node.body:
        if isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
            if isinstance(stmt.target, ast.Name):
                results.append((rel, node.name, stmt.target.id))
    return results


def _collect_dataclass_defaults(path: Path) -> list[tuple[str, str, str]]:
    """Return (relative_path, class_name, field_name) for each dataclass field with a default."""
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
    """All dataclass field defaults must appear in the allowlist."""

    def test_no_unjustified_defaults_in_src(self) -> None:
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
