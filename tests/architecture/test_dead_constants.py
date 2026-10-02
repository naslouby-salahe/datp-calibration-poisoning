import ast
from pathlib import Path

from tests.architecture.source_index import SOURCE_ROOT, scan_production_sources

TEST_SUPPORT_ROOT = SOURCE_ROOT.parents[1] / "tests_support"


def _module_name(path: Path) -> str:
    try:
        relative = path.relative_to(SOURCE_ROOT)
    except ValueError:
        relative = path
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(("datp", *parts))


def _resolve_import(current_path: Path, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    current_module = _module_name(current_path)
    package = current_module if current_path.name == "__init__.py" else current_module.rpartition(".")[0]
    parts = package.split(".")
    if node.level > len(parts):
        return node.module or ""
    base = parts[: len(parts) - node.level + 1]
    return ".".join((*base, *((node.module or "").split("."))))


def _is_exported(name: str, tree: ast.Module) -> bool:
    return any(
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets)
        and any(
            isinstance(value, ast.Constant) and value.value == name
            for value in ast.walk(node.value)
        )
        for node in tree.body
    )


def unused_module_constants(
    sources: dict[Path, ast.Module],
) -> list[tuple[Path, int, str]]:
    definitions: list[tuple[Path, int, str]] = []
    support_sources = {
        path: ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for path in TEST_SUPPORT_ROOT.rglob("*.py")
    }
    usage_sources = sources | support_sources
    modules = {path: _module_name(path) for path in usage_sources}
    for path, tree in sources.items():
        for node in tree.body:
            if isinstance(node, ast.Assign):
                targets = [target for target in node.targets if isinstance(target, ast.Name)]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                targets = [node.target]
            else:
                continue
            definitions.extend(
                (path, node.lineno, target.id)
                for target in targets
                if target.id.isupper() and target.id != "__ALL__"
            )

    unused: list[tuple[Path, int, str]] = []
    for definition_path, line, name in definitions:
        definition_module = modules[definition_path]
        referenced = _is_exported(name, sources[definition_path])
        for path, tree in usage_sources.items():
            if any(
                isinstance(node, ast.Name)
                and node.id == name
                and isinstance(node.ctx, ast.Load)
                for node in ast.walk(tree)
            ):
                referenced = True
                break
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                if _resolve_import(path, node) != definition_module:
                    continue
                if not any(alias.name == name for alias in node.names):
                    continue
                local_name = next(
                    (alias.asname or alias.name for alias in node.names if alias.name == name),
                    name,
                )
                if any(
                    isinstance(use, ast.Name)
                    and use.id == local_name
                    and isinstance(use.ctx, ast.Load)
                    for use in ast.walk(tree)
                ):
                    referenced = True
                    break
            if referenced:
                break
        if not referenced:
            unused.append((definition_path, line, name))
    return unused


def test_production_has_no_unreferenced_module_constants() -> None:
    violations = [
        f"{path.relative_to(SOURCE_ROOT)}:{line}: {name}"
        for path, line, name in unused_module_constants(scan_production_sources())
    ]
    assert not violations, violations


def test_dead_constant_mutation_fails_and_used_constant_passes() -> None:
    dead = Path("dead.py")
    consumer = Path("consumer.py")
    dead_tree = ast.parse("UNUSED_SETTING: int = 5\n")
    used_tree = ast.parse("from datp.dead import UNUSED_SETTING\nvalue = UNUSED_SETTING\n")
    assert unused_module_constants({dead: dead_tree}) == [(dead, 1, "UNUSED_SETTING")]
    assert unused_module_constants({dead: dead_tree, consumer: used_tree}) == []
