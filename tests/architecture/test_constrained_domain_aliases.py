import ast

from tests.architecture.source_index import SOURCE_ROOT, scan_production_sources


FORBIDDEN_GENERIC_NAMES = {
    "NonNegativeInt",
    "PositiveInt",
    "NonNegativeFloat",
    "PositiveFloat",
    "UnitInterval",
    "OpenUnitInterval",
    "FiniteFloat",
    "SignedInt",
}
CANONICAL_TYPES = SOURCE_ROOT / "types.py"


def forbidden_generic_references(tree: ast.AST) -> list[tuple[int, str]]:
    references = [
        (node.lineno, node.id)
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id in FORBIDDEN_GENERIC_NAMES
    ]
    references.extend(
        (node.lineno, node.attr)
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_GENERIC_NAMES
    )
    references.extend(
        (node.lineno, alias.name)
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
        if alias.name in FORBIDDEN_GENERIC_NAMES
    )
    return references


def primitive_alias_declarations(tree: ast.Module) -> list[tuple[int, str]]:
    aliases: list[tuple[int, str]] = []
    builders = {"NewType", "TypeAliasType", "Annotated"}
    type_alias_markers = {"TypeAlias", "TypeAliasType"}
    primitive_names = {
        "str", "int", "float", "bool", "dict", "list", "tuple", "set",
        "frozenset", "Mapping", "Sequence", "Dict", "List", "Tuple",
        "Set", "FrozenSet", "Any", "object",
        *FORBIDDEN_GENERIC_NAMES,
    }
    imported_names: dict[str, str] = {}
    known_aliases: set[str] = set()
    for statement in ast.walk(tree):
        if isinstance(statement, ast.ImportFrom):
            for imported in statement.names:
                local_name = imported.asname or imported.name
                imported_names[local_name] = imported.name
                if imported.name in builders:
                    builders.add(local_name)
                if imported.name in type_alias_markers:
                    type_alias_markers.add(local_name)

    def expression_names(expression: ast.AST) -> set[str]:
        names = {
            node.id if isinstance(node, ast.Name) else node.attr
            for node in ast.walk(expression)
            if isinstance(node, ast.Name | ast.Attribute)
        }
        return names | {imported_names[name] for name in names if name in imported_names}

    for statement in ast.walk(tree):
        if isinstance(statement, ast.Assign):
            names = [target.id for target in statement.targets if isinstance(target, ast.Name)]
            value = statement.value
            type_expression = isinstance(
                value, ast.Name | ast.Attribute | ast.Subscript
            ) or (isinstance(value, ast.BinOp) and isinstance(value.op, ast.BitOr))
            is_alias = type_expression and bool(
                expression_names(value) & (primitive_names | known_aliases)
            )
            is_alias |= any(
                isinstance(node, ast.Call) and expression_names(node.func) & builders
                for node in ast.walk(value)
            )
            if is_alias:
                aliases.extend((statement.lineno, name) for name in names)
                known_aliases.update(names)
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            annotation = statement.annotation
            marker = (
                annotation.id
                if isinstance(annotation, ast.Name)
                else annotation.attr
                if isinstance(annotation, ast.Attribute)
                else ""
            )
            if marker in type_alias_markers:
                aliases.append((statement.lineno, statement.target.id))
    return aliases


def test_generic_constrained_aliases_are_confined_to_canonical_types_module() -> None:
    violations = [
        f"{path.relative_to(SOURCE_ROOT)}:{line} references {name}"
        for path, tree in scan_production_sources().items()
        if path != CANONICAL_TYPES
        for line, name in forbidden_generic_references(tree)
    ]
    assert not violations, violations


def test_nested_and_renamed_generic_alias_mutations_are_detected() -> None:
    mutations = (
        "def f(value: PositiveInt) -> None: ...",
        "CountLike = NonNegativeInt\ndef f(values: list[CountLike]) -> None: ...",
        "def f(value: dict[str, tuple[float, UnitInterval]]) -> None: ...",
        "Threshold = PositiveFloat\ndef f(value: Threshold) -> None: ...",
        "from datp.types import PositiveInt as ClientCount\ndef f(value: ClientCount) -> None: ...",
        "import datp.types as types\ndef f(value: types.PositiveFloat) -> None: ...",
    )
    for source in mutations:
        assert forbidden_generic_references(ast.parse(source))


def test_valid_semantic_type_annotations_remain_allowed() -> None:
    source = "def execute(seed: RandomSeed, threshold: Threshold) -> None: ..."
    assert forbidden_generic_references(ast.parse(source)) == []


def test_primitive_type_aliases_are_confined_to_canonical_types_module() -> None:
    violations = [
        f"{path.relative_to(SOURCE_ROOT)}:{line} aliases primitive as {name}"
        for path, tree in scan_production_sources().items()
        if path != CANONICAL_TYPES
        for line, name in primitive_alias_declarations(tree)
    ]
    assert not violations, violations


def test_alias_laundering_mutations_are_detected() -> None:
    mutations = (
        "ClientLike = str",
        "CountLike = NewType('CountLike', int)",
        "MetricLike = Annotated[float, 'metadata']",
        "Payload = dict[str, Any]",
        "BaseCount = int\nCountLike = BaseCount",
        "from typing import Mapping\nPayload = Mapping[str, object]",
        "from typing import TypeAlias\nPolicyLike: TypeAlias = str",
        "from typing import NewType as DomainAlias\nClientLike = DomainAlias('ClientLike', str)",
        "from pydantic import PositiveInt as Count\nCountLike = Count",
        "import typing as t\nPayload = t.Dict[str, t.Any]",
        "CountUnion = int | None",
        "class Aliases:\n    CountLike = int",
        "from typing import Optional\nPayload = Optional[dict[str, object]]",
    )
    for source in mutations:
        assert primitive_alias_declarations(ast.parse(source))
