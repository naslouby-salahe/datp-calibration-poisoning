import ast

from tests.architecture.source_index import SOURCE_ROOT, scan_production_sources


_DYNAMIC_ACCESSORS = {"getattr", "setattr", "hasattr"}


def dynamic_attribute_calls(tree: ast.AST) -> list[tuple[int, str]]:
    return [
        (node.lineno, node.func.id)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _DYNAMIC_ACCESSORS
    ]


def test_production_uses_typed_attribute_access() -> None:
    violations = [
        f"{path.relative_to(SOURCE_ROOT)}:{line}: {accessor}"
        for path, tree in scan_production_sources().items()
        for line, accessor in dynamic_attribute_calls(tree)
    ]
    assert not violations, violations


def test_dynamic_attribute_access_mutations_fail() -> None:
    mutations = (
        "value = getattr(row, metric_name)",
        "setattr(result, status_name, status)",
        "if hasattr(config, mode_name): pass",
    )
    for source in mutations:
        assert dynamic_attribute_calls(ast.parse(source))


def test_direct_typed_attribute_access_remains_valid() -> None:
    assert dynamic_attribute_calls(ast.parse("value = row.delta_tau")) == []
