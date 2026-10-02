import ast

from tests.architecture.source_index import SOURCE_ROOT, scan_production_sources


CONTAINER_TYPES = {"dict", "list", "tuple", "set", "frozenset", "Mapping", "Sequence"}
OBJECT_BOUNDARIES = {
    ("config/attack_config.py", "CalibrationPoisoningConfig.validate_fractions"),
    ("thresholding/eligibility.py", "ClientThresholdsCollection.__eq__"),
    ("validation/metric_reproducer.py", "_validate_json_value"),
}


def annotation_expressions(tree: ast.AST) -> list[tuple[int, ast.expr]]:
    annotations: list[tuple[int, ast.expr]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            annotations.append((node.lineno, node.annotation))
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            arguments = node.args
            parameters = (
                *arguments.posonlyargs,
                *arguments.args,
                *arguments.kwonlyargs,
            )
            annotations.extend(
                (argument.lineno, argument.annotation)
                for argument in parameters
                if argument.annotation is not None
            )
            for argument in (arguments.vararg, arguments.kwarg):
                if argument is not None and argument.annotation is not None:
                    annotations.append((argument.lineno, argument.annotation))
            if node.returns is not None:
                annotations.append((node.returns.lineno, node.returns))
    return annotations


def bare_container_names(annotation: ast.expr) -> list[str]:
    return [
        node.id
        for node in ast.walk(annotation)
        if isinstance(node, ast.Name)
        and node.id in CONTAINER_TYPES
        and not any(
            isinstance(parent, ast.Subscript) and parent.value is node
            for parent in ast.walk(annotation)
        )
    ]


def annotation_escape_hatches(tree: ast.Module) -> list[tuple[int, str, str]]:
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    violations: list[tuple[int, str, str]] = []
    for line, annotation in annotation_expressions(tree):
        owner: ast.AST | None = annotation
        while owner is not None and not isinstance(
            owner, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        ):
            owner = parents.get(owner)
        scope: list[str] = []
        while owner is not None:
            if isinstance(owner, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                scope.append(owner.name)
            owner = parents.get(owner)
        qualified_scope = ".".join(reversed(scope))
        for node in ast.walk(annotation):
            if isinstance(node, ast.Name) and node.id in {"Any", "object"}:
                violations.append((line, node.id, qualified_scope))
    return violations


def test_production_annotations_parameterize_container_types() -> None:
    violations = [
        f"{path}:{line}: bare {name} in {ast.unparse(annotation)}"
        for path, tree in scan_production_sources().items()
        for line, annotation in annotation_expressions(tree)
        for name in bare_container_names(annotation)
    ]
    assert not violations, violations


def test_nested_bare_container_mutations_are_detected() -> None:
    sources = (
        "def run(values: list) -> None: ...",
        "def run(payload: dict[str, tuple]) -> None: ...",
        "class Result:\n    records: Sequence\n",
    )
    for source in sources:
        tree = ast.parse(source)
        assert any(
            bare_container_names(annotation)
            for _, annotation in annotation_expressions(tree)
        )


def test_parameterized_nested_containers_are_valid() -> None:
    tree = ast.parse("def run(values: list[tuple[str, ...]]) -> dict[str, int]: ...")
    assert all(
        not bare_container_names(annotation)
        for _, annotation in annotation_expressions(tree)
    )


def test_domain_annotations_avoid_any_and_unapproved_object() -> None:
    violations = [
        f"{path.relative_to(SOURCE_ROOT)}:{line}: {name} in {scope or '<module>'}"
        for path, tree in scan_production_sources().items()
        for line, name, scope in annotation_escape_hatches(tree)
        if name == "Any"
        or (name == "object" and (path.relative_to(SOURCE_ROOT).as_posix(), scope) not in OBJECT_BOUNDARIES)
    ]
    assert not violations, violations


def test_any_and_object_annotation_mutations_fail_closed() -> None:
    mutations = (
        "from typing import Any\ndef run(value: Any) -> None: ...",
        "def run(value: object) -> None: ...",
        "class Model:\n    value: list[object]\n",
        "class Model:\n    def validate(self, value: dict[str, object]) -> object: ...\n",
    )
    for source in mutations:
        tree = ast.parse(source)
        assert annotation_escape_hatches(tree)


def test_exact_untyped_boundary_controls_remain_available() -> None:
    controls = (
        "class ClientThresholdsCollection:\n    def __eq__(self, other: object) -> bool: ...\n",
        "class CalibrationPoisoningConfig:\n    def validate_fractions(self, value: object) -> object: ...\n",
        "def _validate_json_value(value: object) -> object: ...",
    )
    for source in controls:
        assert all(
            name == "object" and scope in {
                "ClientThresholdsCollection.__eq__",
                "CalibrationPoisoningConfig.validate_fractions",
                "_validate_json_value",
            }
            for _, name, scope in annotation_escape_hatches(ast.parse(source))
        )
