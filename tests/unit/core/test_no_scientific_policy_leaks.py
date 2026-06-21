"""Enforcement tests: detect scientific policy leaks and structural violations.

These tests use AST/source analysis to ensure forbidden patterns do not
return after the canonicalization refactor.
"""

from __future__ import annotations

import re
from pathlib import Path

_SRC_ROOT = Path(__file__).parent.parent.parent.parent / "src" / "datp"


def _all_py_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestNoLocalRegimePolicyConstants:
    """No module-level _REGIME_*_BASELINES definitions outside datp/core."""

    _PATTERN = re.compile(r"^_REGIME_\w*BASELINES\s*=", re.MULTILINE)

    def test_no_local_regime_policy_constants_in_reporting(self) -> None:
        for path in _all_py_files(_SRC_ROOT / "reporting"):
            src = _source(path)
            matches = self._PATTERN.findall(src)
            assert not matches, (
                f"{path.relative_to(_SRC_ROOT)}: "
                f"found local _REGIME_*BASELINES: {matches!r}. "
                "Move to datp.core.enums."
            )

    def test_no_local_regime_policy_constants_in_validation(self) -> None:
        for path in _all_py_files(_SRC_ROOT / "validation"):
            src = _source(path)
            matches = self._PATTERN.findall(src)
            assert not matches, (
                f"{path.relative_to(_SRC_ROOT)}: "
                f"found local _REGIME_*BASELINES: {matches!r}. "
                "Move to datp.core.enums."
            )

    def test_no_local_regime_policy_constants_in_analyses(self) -> None:
        for path in _all_py_files(_SRC_ROOT / "analyses"):
            src = _source(path)
            matches = self._PATTERN.findall(src)
            assert not matches, (
                f"{path.relative_to(_SRC_ROOT)}: "
                f"found local _REGIME_*BASELINES: {matches!r}. "
                "Move to datp.core.enums."
            )


class TestNoLocalStatsBaselines:
    """No module-level _STATS_BASELINES_* definitions outside datp/core."""

    _PATTERN = re.compile(r"^_STATS_BASELINES\w*\s*=", re.MULTILINE)

    def test_no_local_stats_baselines_in_reporting(self) -> None:
        for path in _all_py_files(_SRC_ROOT / "reporting"):
            src = _source(path)
            matches = self._PATTERN.findall(src)
            assert not matches, (
                f"{path.relative_to(_SRC_ROOT)}: "
                f"found local _STATS_BASELINES*: {matches!r}. "
                "Use STATS_REPORTING_BASELINES from datp.core.enums."
            )

    def test_no_local_stats_baselines_in_validation(self) -> None:
        for path in _all_py_files(_SRC_ROOT / "validation"):
            src = _source(path)
            matches = self._PATTERN.findall(src)
            assert not matches, (
                f"{path.relative_to(_SRC_ROOT)}: "
                f"found local _STATS_BASELINES*: {matches!r}. "
                "Use STATS_REPORTING_BASELINES from datp.core.enums."
            )


class TestNoAttrsDefineInSrc:
    """No new attrs.define usage for internal DATP domain specs."""

    _PATTERN = re.compile(r"@attrs\.define|attrs\.define\(")

    def test_no_attrs_define_in_src(self) -> None:
        violations: list[str] = []
        for path in _all_py_files(_SRC_ROOT):
            src = _source(path)
            if self._PATTERN.search(src):
                violations.append(str(path.relative_to(_SRC_ROOT)))
        assert not violations, (
            f"Found attrs.define in {violations}. "
            "Use @dataclass(frozen=True, slots=True) for internal specs."
        )


class TestNoHardcodedOutputPathsInReporting:
    """Reporting/build.py must not hardcode 'figures', 'tables', 'analysis' path strings."""

    def _check_no_hardcoded_path(
        self, src: str, literal: str, allow_module: str
    ) -> None:
        """Check that `literal` does not appear as a standalone path join operand."""
        pattern = re.compile(rf'/ "{re.escape(literal)}"')
        matches = pattern.findall(src)
        assert not matches, (
            f"Hardcoded path segment {literal!r} found in {allow_module}. "
            f"Use the canonical directory constant instead."
        )

    def test_no_hardcoded_figures_in_build(self) -> None:
        build_py = _SRC_ROOT / "reporting" / "build.py"
        self._check_no_hardcoded_path(
            _source(build_py), "figures", "reporting/build.py"
        )

    def test_no_hardcoded_tables_in_build(self) -> None:
        build_py = _SRC_ROOT / "reporting" / "build.py"
        self._check_no_hardcoded_path(_source(build_py), "tables", "reporting/build.py")

    def test_no_hardcoded_analysis_in_build(self) -> None:
        build_py = _SRC_ROOT / "reporting" / "build.py"
        self._check_no_hardcoded_path(
            _source(build_py), "analysis", "reporting/build.py"
        )


class TestNoHardcodedFigureNamesInBuild:
    """reporting/build.py must not hardcode figure name strings; use FigureName enum."""

    _PATTERN = re.compile(r'"figure_[1-4]"')

    def test_no_hardcoded_figure_names_in_build(self) -> None:
        build_py = _SRC_ROOT / "reporting" / "build.py"
        src = _source(build_py)
        matches = self._PATTERN.findall(src)
        assert not matches, (
            f"Hardcoded figure names {matches!r} in reporting/build.py. "
            "Use FigureName enum from datp.core.enums."
        )


class TestNoOsPathJoinInSrc:
    """No os.path.join usage in datp src (use pathlib)."""

    _PATTERN = re.compile(r"\bos\.path\.join\b")

    def test_no_os_path_join_in_src(self) -> None:
        violations: list[str] = []
        for path in _all_py_files(_SRC_ROOT):
            src = _source(path)
            if self._PATTERN.search(src):
                violations.append(str(path.relative_to(_SRC_ROOT)))
        assert not violations, (
            f"Found os.path.join in {violations}. Use pathlib.Path instead."
        )


class TestAttrsRemovedFromDependencies:
    """attrs must not be a project dependency after full dataclass migration."""

    def test_attrs_not_in_pyproject_dependencies(self) -> None:
        pyproject = _SRC_ROOT.parent.parent / "pyproject.toml"
        src = pyproject.read_text(encoding="utf-8")
        # Check in the [project].dependencies section only
        # A simple but reliable check: the string '"attrs",' or '"attrs"' should not appear
        assert '"attrs"' not in src, (
            "attrs is still listed in pyproject.toml dependencies. "
            "Remove it — all internal specs now use @dataclass."
        )


class TestReportingUsesCorePolicies:
    """reporting/build.py imports policies from datp.core, not locally."""

    def test_build_imports_controlled_baselines(self) -> None:
        build_py = _SRC_ROOT / "reporting" / "build.py"
        src = _source(build_py)
        assert "CONTROLLED_BASELINES" not in src, (
            "CONTROLLED_BASELINES is stale; use ThresholdPolicy directly"
        )
        assert "ThresholdPolicy" in src, (
            "reporting/build.py must use ThresholdPolicy for policy iteration"
        )

    def test_build_imports_figure_name(self) -> None:
        build_py = _SRC_ROOT / "reporting" / "build.py"
        src = _source(build_py)
        assert "FigureName" in src, (
            "reporting/build.py must use FigureName from datp.core.enums"
        )

    def test_build_imports_evidence_role(self) -> None:
        build_py = _SRC_ROOT / "reporting" / "build.py"
        src = _source(build_py)
        assert "EvidenceRole" in src, (
            "reporting/build.py must use EvidenceRole from datp.core.enums"
        )

    def test_build_imports_seed_scope(self) -> None:
        build_py = _SRC_ROOT / "reporting" / "build.py"
        src = _source(build_py)
        assert "SeedScope" in src, (
            "reporting/build.py must use SeedScope from datp.core.enums"
        )
