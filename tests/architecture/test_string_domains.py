import ast

from tests.architecture.source_index import SOURCE_ROOT, scan_production_sources


_DOMAIN_NAMES = {
    "aggregation",
    "artifact",
    "artifact_kind",
    "command",
    "dataset",
    "device",
    "direction",
    "experiment",
    "kind",
    "metric",
    "mode",
    "objective",
    "outcome",
    "policy",
    "repository",
    "split",
    "stage",
    "suffix",
    "state",
    "status",
    "strategy",
    "workflow",
}


def _names(node: ast.AST) -> set[str]:
    return {
        child.id if isinstance(child, ast.Name) else child.attr
        for child in ast.walk(node)
        if isinstance(child, ast.Name | ast.Attribute)
    }


def _literal_strings(node: ast.AST) -> list[ast.Constant]:
    return [
        child
        for child in ast.walk(node)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    ]


def _finite_domain_string_violations(tree: ast.AST) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            compared_names = _names(node.left)
            for comparator in node.comparators:
                compared_names.update(_names(comparator))
            if compared_names & _DOMAIN_NAMES:
                for literal in _literal_strings(node):
                    violations.append((literal.lineno, ast.unparse(node)))
        elif isinstance(node, ast.Match):
            if _names(node.subject) & _DOMAIN_NAMES:
                for case in node.cases:
                    for literal in _literal_strings(case.pattern):
                        violations.append((literal.lineno, ast.unparse(case.pattern)))
    return violations


def _string_domain_annotation_violations(tree: ast.AST) -> list[tuple[int, str]]:
    """Reject str annotations on symbols whose names promise a finite domain."""
    violations: list[tuple[int, str]] = []

    def is_string_annotation(annotation: ast.expr) -> bool:
        return any(
            (isinstance(node, ast.Name) and node.id == "str")
            or (isinstance(node, ast.Attribute) and node.attr == "str")
            or (
                isinstance(node, ast.Subscript)
                and (
                    (isinstance(node.value, ast.Name) and node.value.id == "Literal")
                    or (
                        isinstance(node.value, ast.Attribute)
                        and node.value.attr == "Literal"
                    )
                )
                and any(
                    isinstance(item, ast.Constant) and isinstance(item.value, str)
                    for item in ast.walk(node.slice)
                )
            )
            for node in ast.walk(annotation)
        )

    def is_domain_name(name: str) -> bool:
        lowered = name.lower()
        return any(domain in lowered for domain in _DOMAIN_NAMES)

    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            name = (
                node.target.id
                if isinstance(node.target, ast.Name)
                else ast.unparse(node.target)
            )
            if is_domain_name(name) and is_string_annotation(node.annotation):
                violations.append((node.lineno, f"{name}: {ast.unparse(node.annotation)}"))
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            parameters = (
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            )
            for parameter in parameters:
                if parameter.annotation and is_domain_name(parameter.arg) and is_string_annotation(parameter.annotation):
                    violations.append(
                        (
                            parameter.lineno,
                            f"{parameter.arg}: {ast.unparse(parameter.annotation)}",
                        )
                    )
            if node.returns and is_domain_name(node.name) and is_string_annotation(node.returns):
                violations.append((node.lineno, f"{node.name} -> {ast.unparse(node.returns)}"))

    return violations


def _enum_value_logic_violations(tree: ast.AST) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if any(
            isinstance(child, ast.Attribute) and child.attr == "value"
            for child in ast.walk(node)
        ):
            violations.append((node.lineno, ast.unparse(node)))
    return violations


def _required_enum_field_violations(
    tree: ast.Module, *, class_name: str, field_name: str, enum_name: str
) -> list[tuple[int, str]]:
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for member in node.body:
            if isinstance(member, ast.AnnAssign) and isinstance(
                member.target, ast.Name
            ) and member.target.id == field_name:
                if ast.unparse(member.annotation) == enum_name:
                    return []
                return [(member.lineno, ast.unparse(member.annotation))]
        return [(node.lineno, f"{field_name} missing")]
    return [(0, f"{class_name} missing")]


def test_finite_domain_strings_are_not_compared_in_production() -> None:
    violations = [
        f"{path}:{line}: {expression}"
        for path, tree in scan_production_sources().items()
        for line, expression in _finite_domain_string_violations(tree)
    ]

    assert not violations, violations


def test_finite_domain_symbols_are_not_annotated_as_strings() -> None:
    violations = [
        f"{path.relative_to(SOURCE_ROOT)}:{line}: {symbol}"
        for path, tree in scan_production_sources().items()
        for line, symbol in _string_domain_annotation_violations(tree)
    ]
    assert not violations, violations


def test_enum_values_are_not_used_for_internal_comparisons() -> None:
    violations = [
        f"{path.relative_to(SOURCE_ROOT)}:{line}: {expression}"
        for path, tree in scan_production_sources().items()
        for line, expression in _enum_value_logic_violations(tree)
    ]
    assert not violations, violations


def test_internal_calibration_status_uses_the_canonical_enum() -> None:
    expected = (
        ("core/types.py", "ClientThreshold", "status"),
        ("data/contracts.py", "PartitionResult", "status"),
    )
    violations = [
        f"{path}:{line}: {annotation}"
        for path_name, class_name, field_name in expected
        for path, tree in scan_production_sources().items()
        if path.relative_to(SOURCE_ROOT).as_posix() == path_name
        for line, annotation in _required_enum_field_violations(
            tree,
            class_name=class_name,
            field_name=field_name,
            enum_name="ClientStatus",
        )
    ]
    assert not violations, violations


def test_internal_calibration_status_mutation_rejects_boolean_state() -> None:
    boolean_state = ast.parse("class ClientThreshold:\n    calibration_pending: bool\n")
    enum_state = ast.parse("class ClientThreshold:\n    status: ClientStatus\n")
    assert _required_enum_field_violations(
        boolean_state,
        class_name="ClientThreshold",
        field_name="calibration_pending",
        enum_name="ClientStatus",
    )
    assert not _required_enum_field_violations(
        enum_state,
        class_name="ClientThreshold",
        field_name="status",
        enum_name="ClientStatus",
    )


def test_string_domain_mutations_fail_with_free_text_control() -> None:
    invalid_sources = (
        'if policy == "local": pass',
        'if strategy in {"random", "targeted"}: pass',
        'if status != "done": pass',
        'if mode == "dry_run": pass',
        'if objective == "raise": pass',
        'if dataset == "nbaiot": pass',
        'match result.stage:\n    case "training": pass',
    )
    for source in invalid_sources:
        assert _finite_domain_string_violations(ast.parse(source))

    free_text = ast.parse('if description == "dry-run only": pass')
    assert not _finite_domain_string_violations(free_text)

    invalid_annotations = ast.parse(
        "def run(policy: str, strategy: list[str]) -> None: ...\n"
        "class Config:\n    dataset: str\n    status: str\n"
        "def current_mode() -> str: ...\n"
        "from typing import Literal\n"
        "def execute(objective: Literal['raise', 'lower']) -> None: ...\n"
        "def load_repository(repository: str) -> None: ...\n"
    )
    assert len(_string_domain_annotation_violations(invalid_annotations)) == 7
    valid_free_text = ast.parse(
        "def describe(description: str) -> str: ...\n"
        "class Report:\n    narrative: str\n"
    )
    assert not _string_domain_annotation_violations(valid_free_text)


def test_enum_value_comparison_mutations_fail_but_serialization_is_allowed() -> None:
    invalid = ast.parse('if policy.value == "local": pass')
    serialized = ast.parse("payload = [split.value for split in manifest.expected_splits]")

    assert _enum_value_logic_violations(invalid)
    assert not _enum_value_logic_violations(serialized)
