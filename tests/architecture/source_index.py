import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src" / "datp"


def discover_production_files(root: Path = SOURCE_ROOT) -> list[Path]:
    if not root.is_dir():
        raise FileNotFoundError(f"production source root does not exist: {root}")
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def assert_complete_scan(expected: set[Path], scanned: set[Path]) -> None:
    missing = sorted(path.as_posix() for path in expected - scanned)
    unexpected = sorted(path.as_posix() for path in scanned - expected)
    if missing or unexpected:
        raise AssertionError(
            f"architecture source scan mismatch; missing={missing}, unexpected={unexpected}"
        )


def parse_source(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def scan_production_sources(root: Path = SOURCE_ROOT) -> dict[Path, ast.Module]:
    expected = set(discover_production_files(root))
    scanned = {path: parse_source(path) for path in sorted(expected)}
    assert_complete_scan(expected, set(scanned))
    return scanned
