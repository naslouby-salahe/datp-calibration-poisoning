import ast
import re

from tests.architecture.source_index import SOURCE_ROOT, scan_production_sources


_DOMAIN_NAME = re.compile(
    r"(?:POLIC(?:Y|IES)|STRATEG(?:Y|IES)|STATUS|STATE|MODE|OBJECTIVE|DATASET|STAGE|SPLIT|KIND|TYPE|"
    r"DIRECTION|OUTCOME|COMMAND|DEVICE|METRIC|WORKFLOW|STEM|COLUMN|PREFIX|SUFFIX|SCHEMA)",
    re.IGNORECASE,
)


def _is_domain_literal(value: ast.expr) -> bool:
    if isinstance(value, ast.Constant):
        return isinstance(value.value, (str, int, float)) and not isinstance(
            value.value, bool
        )
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
        return value.func.id in {"str", "int", "float"} and any(
            isinstance(argument, ast.Constant)
            and isinstance(argument.value, (str, int, float))
            for argument in value.args
        )
    if isinstance(value, ast.Tuple | ast.List | ast.Set):
        return bool(value.elts) and all(
            isinstance(item, ast.Constant)
            and isinstance(item.value, (str, int, float))
            and not isinstance(item.value, bool)
            for item in value.elts
        )
    if isinstance(value, ast.Dict):
        return any(
            isinstance(key, ast.Constant) and isinstance(key.value, str)
            for key in value.keys
        )
    return False


def semantic_constant_violations(tree: ast.Module) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []
    scopes = [tree.body]
    scopes.extend(
        node.body
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and not any(
            (isinstance(base, ast.Name) and base.id in {"Enum", "StrEnum", "IntEnum", "Flag", "IntFlag"})
            or (isinstance(base, ast.Attribute) and base.attr in {"Enum", "StrEnum", "IntEnum", "Flag", "IntFlag"})
            for base in node.bases
        )
    )
    for scope in scopes:
        for statement in scope:
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                target = statement.targets[0]
                value = statement.value
                annotation = None
            elif isinstance(statement, ast.AnnAssign):
                target = statement.target
                value = statement.value
                annotation = statement.annotation
            else:
                continue
            if not isinstance(target, ast.Name) or not target.id.removeprefix("_").isupper():
                continue
            if target.id.endswith("_MODULE") or not _DOMAIN_NAME.search(target.id) or value is None:
                continue
            schema_version = (
                "SCHEMA_VERSION" in target.id
                and annotation is not None
                and any(
                    isinstance(node, ast.Name) and node.id == "SchemaVersion"
                    for node in ast.walk(annotation)
                )
            )
            if not schema_version and _is_domain_literal(value):
                violations.append((statement.lineno, target.id))
    return violations


def test_production_has_no_loose_semantic_domain_constants() -> None:
    violations = [
        f"{path.relative_to(SOURCE_ROOT)}:{line}: {name}"
        for path, tree in scan_production_sources().items()
        for line, name in semantic_constant_violations(tree)
    ]
    assert not violations, violations


def test_semantic_constant_mutations_fail_closed() -> None:
    mutations = (
        'POLICY = "local"',
        'STRATEGIES = ("random", "targeted")',
        'STATUS: Final[str] = "done"',
        'MODE_ID = 3',
        'OBJECTIVES = {"raise": 1, "lower": 2}',
        'SCHEMA_VERSION = "1"',
        'class Settings:\n    MODE: Final[str] = "batch"',
    )
    for source in mutations:
        assert semantic_constant_violations(ast.parse(source))


def test_enum_maps_narrative_text_and_schema_versions_are_valid_controls() -> None:
    controls = (
        'from typing import Final\nfrom datp.core.enums import ThresholdPolicy\n'
        'POLICY_LABELS: Final = {ThresholdPolicy.LOCAL_THRESHOLD: "Local"}',
        'from enum import StrEnum\nclass Policy(StrEnum):\n    LOCAL = "local"',
        'WARNING: str = "Representative seed only; descriptive evidence."',
        'from datp.types import SchemaVersion\nSCORING_SCHEMA_VERSION: SchemaVersion = "1"',
    )
    for source in controls:
        assert semantic_constant_violations(ast.parse(source)) == []
