"""Architecture tests ensuring no policy definitions, hardcoded paths, or external dependencies leak into submodules."""

from __future__ import annotations

import re
from pathlib import Path

_SRC_ROOT = Path(__file__).parent.parent.parent.parent / "src" / "datp"


def _all_py_files(root: Path) -> list[Path]:
    """Collect all python files recursively under a given root directory."""
    return sorted(root.rglob("*.py"))


def _source(path: Path) -> str:
    """Read and return the text content of a file."""
    return path.read_text()


class TestNoLocalRegimePolicyConstants:
    """Tests verifying that baseline policies are defined centrally, not locally."""

    _PATTERN = re.compile(r"^_REGIME_\w*BASELINES\s*=", re.MULTILINE)

    def test_no_local_regime_policy_constants_in_reporting(self) -> None:
        """Ensure reporting modules do not define local baseline policy lists."""
        for path in _all_py_files(_SRC_ROOT / "reporting"):
            src = _source(path)
            matches = self._PATTERN.findall(src)
            assert not matches, (
                f"{path.relative_to(_SRC_ROOT)}: "
                f"found local _REGIME_*BASELINES: {matches!r}. "
                "Move to datp.core.enums."
            )

    def test_no_local_regime_policy_constants_in_validation(self) -> None:
        """Ensure validation modules do not define local baseline policy lists."""
        for path in _all_py_files(_SRC_ROOT / "validation"):
            src = _source(path)
            matches = self._PATTERN.findall(src)
            assert not matches, (
                f"{path.relative_to(_SRC_ROOT)}: "
                f"found local _REGIME_*BASELINES: {matches!r}. "
                "Move to datp.core.enums."
            )

    def test_no_local_regime_policy_constants_in_analyses(self) -> None:
        """Ensure analyses modules do not define local baseline policy lists."""
        for path in _all_py_files(_SRC_ROOT / "analyses"):
            src = _source(path)
            matches = self._PATTERN.findall(src)
            assert not matches, (
                f"{path.relative_to(_SRC_ROOT)}: "
                f"found local _REGIME_*BASELINES: {matches!r}. "
                "Move to datp.core.enums."
            )


class TestNoLocalStatsBaselines:
    """Tests verifying that stale stats baselines constants are removed."""

    _PATTERN = re.compile(r"^_STATS_BASELINES\w*\s*=", re.MULTILINE)

    def test_no_local_stats_baselines_in_reporting(self) -> None:
        """Ensure reporting does not reference obsolete stats baselines lists."""
        for path in _all_py_files(_SRC_ROOT / "reporting"):
            src = _source(path)
            matches = self._PATTERN.findall(src)
            assert not matches, (
                f"{path.relative_to(_SRC_ROOT)}: "
                f"found stale _STATS_BASELINES* constant: {matches!r}. "
                "Remove — policy iteration uses ThresholdPolicy directly."
            )

    def test_no_local_stats_baselines_in_validation(self) -> None:
        """Ensure validation does not reference obsolete stats baselines lists."""
        for path in _all_py_files(_SRC_ROOT / "validation"):
            src = _source(path)
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
        for path in _all_py_files(_SRC_ROOT):
            src = _source(path)
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
            _source(build_py), "figures", "reporting/build.py"
        )

    def test_no_hardcoded_tables_in_build(self) -> None:
        """Ensure 'tables' directory name is not hardcoded in reporting build."""
        build_py = _SRC_ROOT / "reporting" / "build.py"
        self._check_no_hardcoded_path(_source(build_py), "tables", "reporting/build.py")

    def test_no_hardcoded_analysis_in_build(self) -> None:
        """Ensure 'analysis' directory name is not hardcoded in reporting build."""
        build_py = _SRC_ROOT / "reporting" / "build.py"
        self._check_no_hardcoded_path(
            _source(build_py), "analysis", "reporting/build.py"
        )


class TestNoHardcodedFigureNamesInBuild:
    """Tests verifying that figure output names are not hardcoded."""

    _PATTERN = re.compile(r'"figure_[1-4]"')

    def test_no_hardcoded_figure_names_in_build(self) -> None:
        """Ensure figure names match canonical enums rather than hardcoded strings."""
        build_py = _SRC_ROOT / "reporting" / "build.py"
        src = _source(build_py)
        matches = self._PATTERN.findall(src)
        assert not matches, (
            f"Hardcoded figure names {matches!r} in reporting/build.py. "
            "Use FigureName enum from datp.core.enums."
        )


class TestNoOsPathJoinInSrc:
    """Tests verifying that os.path.join is not used in src."""

    _PATTERN = re.compile(r"\bos\.path\.join\b")

    def test_no_os_path_join_in_src(self) -> None:
        """Ensure all source files utilize pathlib.Path rather than os.path.join."""
        violations: list[str] = []
        for path in _all_py_files(_SRC_ROOT):
            src = _source(path)
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
        src = _source(build_py)
        assert "CONTROLLED_BASELINES" not in src, (
            "CONTROLLED_BASELINES is stale; use ThresholdPolicy directly"
        )
        assert "ThresholdPolicy" in src, (
            "reporting/build.py must use ThresholdPolicy for policy iteration"
        )

    def test_build_imports_figure_name(self) -> None:
        """Ensure build.py imports and uses FigureName enum."""
        build_py = _SRC_ROOT / "reporting" / "build.py"
        src = _source(build_py)
        assert "FigureName" in src, (
            "reporting/build.py must use FigureName from datp.core.enums"
        )

    def test_build_imports_evidence_role(self) -> None:
        """Ensure build.py imports and uses EvidenceRole enum."""
        build_py = _SRC_ROOT / "reporting" / "build.py"
        src = _source(build_py)
        assert "EvidenceRole" in src, (
            "reporting/build.py must use EvidenceRole from datp.core.enums"
        )

    def test_build_imports_seed_scope(self) -> None:
        """Ensure build.py imports and uses SeedScope enum."""
        build_py = _SRC_ROOT / "reporting" / "build.py"
        src = _source(build_py)
        assert "SeedScope" in src, (
            "reporting/build.py must use SeedScope from datp.core.enums"
        )
