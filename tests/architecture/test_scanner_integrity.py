import ast
from pathlib import Path

import pytest
from setuptools.config.pyprojecttoml import read_configuration

from tests.architecture.source_index import (
    REPO_ROOT,
    SOURCE_ROOT,
    assert_complete_scan,
    discover_production_files,
    scan_production_sources,
)


def test_every_production_python_file_is_scanned() -> None:
    expected = set(discover_production_files())
    scanned = scan_production_sources()
    assert set(scanned) == expected
    assert all(isinstance(tree, ast.Module) for tree in scanned.values())


def test_every_setuptools_package_root_is_inside_the_scanned_source_root() -> None:
    project = read_configuration(REPO_ROOT / "pyproject.toml", expand=True)
    setuptools = project["tool"]["setuptools"]
    package_base = REPO_ROOT / setuptools["package-dir"][""]
    package_roots = {
        package_base / package.split(".", maxsplit=1)[0]
        for package in setuptools["packages"]
    }

    assert package_roots
    assert all(root == SOURCE_ROOT or SOURCE_ROOT in root.parents for root in package_roots)
    packaged_files = {
        path for root in package_roots for path in discover_production_files(root)
    }
    assert packaged_files == set(scan_production_sources())


def test_new_nested_production_file_is_discovered(tmp_path: Path) -> None:
    nested = tmp_path / "new_package" / "deeply" / "nested.py"
    nested.parent.mkdir(parents=True)
    nested.write_text("def run() -> None:\n    return None\n", encoding="utf-8")

    assert discover_production_files(tmp_path) == [nested]
    assert set(scan_production_sources(tmp_path)) == {nested}


def test_scanner_fails_when_a_production_file_is_omitted(tmp_path: Path) -> None:
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("first = 1\n", encoding="utf-8")
    second.write_text("second = 2\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="missing="):
        assert_complete_scan({first, second}, {first})


def test_scanner_fails_closed_on_parse_errors(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.py"
    invalid.write_text("def broken(:\n    pass\n", encoding="utf-8")

    with pytest.raises(SyntaxError):
        scan_production_sources(tmp_path)


def test_valid_source_is_scanned_without_blanket_rejection(tmp_path: Path) -> None:
    valid = tmp_path / "valid.py"
    valid.write_text("def value() -> int:\n    return 1\n", encoding="utf-8")

    scanned = scan_production_sources(tmp_path)
    assert scanned[valid].body
