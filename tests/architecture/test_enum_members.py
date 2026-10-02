import ast
from pathlib import Path

from tests.architecture.source_index import SOURCE_ROOT, scan_production_sources


_ENUM_BASES = {"Enum", "StrEnum", "IntEnum", "Flag", "IntFlag"}


def _module_name(path: Path) -> str:
    try:
        relative = path.relative_to(SOURCE_ROOT)
    except ValueError:
        relative = path
    parts = relative.with_suffix("").parts
    return ".".join(("datp", *(parts[:-1] if parts[-1] == "__init__" else parts)))


def _relative_module(current: str, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    package = current if current.endswith(".__init__") else current.rpartition(".")[0]
    parts = package.split(".")
    base = ".".join(parts[: len(parts) - node.level + 1])
    return ".".join(part for part in (base, node.module or "") if part)


def _attribute_chain(node: ast.AST) -> list[str]:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return list(reversed(parts))


def unused_enum_members(
    sources: dict[Path, ast.Module],
) -> list[tuple[Path, int, str, str]]:
    modules = {_module_name(path): tree for path, tree in sources.items()}
    classes = [
        node
        for tree in modules.values()
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    ]
    model_classes = {
        node.name
        for node in classes
        if any(
            (isinstance(base, ast.Name) and base.id == "BaseModel")
            or (isinstance(base, ast.Attribute) and base.attr == "BaseModel")
            for base in node.bases
        )
    }
    while True:
        inherited = {
            node.name
            for node in classes
            if node.name not in model_classes
            and any(
                (isinstance(base, ast.Name) and base.id in model_classes)
                or (isinstance(base, ast.Attribute) and base.attr in model_classes)
                for base in node.bases
            )
        }
        if not inherited:
            break
        model_classes.update(inherited)
    enum_members: dict[str, tuple[Path, dict[str, int]]] = {}
    imports: dict[str, dict[str, str]] = {}
    module_imports: dict[str, dict[str, str]] = {}

    for path, tree in sources.items():
        module = _module_name(path)
        imports[module] = {}
        module_imports[module] = {}
        enum_aliases = {
            (alias.asname or alias.name): alias.name
            for statement in tree.body
            if isinstance(statement, ast.ImportFrom) and statement.module == "enum"
            for alias in statement.names
        }
        for statement in ast.walk(tree):
            if isinstance(statement, ast.ImportFrom):
                imported_module = _relative_module(module, statement)
                for alias in statement.names:
                    imports[module][alias.asname or alias.name] = (
                        f"{imported_module}.{alias.name}"
                    )
            elif isinstance(statement, ast.Import):
                for alias in statement.names:
                    local = alias.asname or alias.name.split(".")[0]
                    module_imports[module][local] = (
                        alias.name if alias.asname else alias.name.split(".")[0]
                    )

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            bases = {
                base.id if isinstance(base, ast.Name) else base.attr
                for base in node.bases
                if isinstance(base, ast.Name | ast.Attribute)
            }
            if not bases.intersection(_ENUM_BASES | set(enum_aliases)):
                continue
            if not (bases.intersection(_ENUM_BASES) or bases.intersection(enum_aliases)):
                continue
            members = {
                target.id: statement.lineno
                for statement in node.body
                if isinstance(statement, ast.Assign)
                for target in statement.targets
                if isinstance(target, ast.Name)
                and target.id.isupper()
                and not target.id.startswith("_")
            }
            enum_members[f"{module}.{node.name}"] = (path, members)

    # Resolve public re-exports such as datp.artifacts.names.ArtifactFile.
    for _ in range(len(modules) + 1):
        changed = False
        for module, local_imports in imports.items():
            for local, target in tuple(local_imports.items()):
                if (
                    target is not None
                    and target not in enum_members
                    and target.rpartition(".")[0] in imports
                ):
                    parent_module, _, imported_name = target.rpartition(".")
                    replacement = imports.get(parent_module, {}).get(imported_name)
                    if replacement is not None and (
                        replacement in enum_members or replacement != target
                    ):
                        local_imports[local] = replacement
                        changed = True
        if not changed:
            break

    member_references: set[tuple[str, str]] = set()
    iterated_enums: set[str] = set()
    schema_fields: set[str] = set()
    schema_enum_types: set[str] = set()
    for path, tree in sources.items():
        module = _module_name(path)
        local_imports = imports[module]
        module_aliases = module_imports[module]
        parents = {
            child: parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }

        def class_for(node: ast.AST) -> str | None:
            parent = parents.get(node)
            while parent is not None:
                if isinstance(parent, ast.ClassDef):
                    candidate = f"{module}.{parent.name}"
                    return candidate if candidate in enum_members else None
                parent = parents.get(parent)
            return None

        def enum_target(expression: ast.AST) -> str | None:
            if isinstance(expression, ast.Name):
                if expression.id == "cls":
                    return class_for(expression)
                imported = local_imports.get(expression.id)
                candidate = imported or f"{module}.{expression.id}"
                return candidate if candidate in enum_members else None
            chain = _attribute_chain(expression)
            if len(chain) >= 2 and chain[0] in module_aliases:
                candidate = f"{module_aliases[chain[0]]}.{chain[1]}"
                return candidate if candidate in enum_members else None
            return None

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name in model_classes:
                    for field in node.body:
                        if isinstance(field, ast.AnnAssign) and isinstance(
                            field.target, ast.Name
                        ):
                            schema_fields.add(field.target.id)
                            for annotation_node in ast.walk(field.annotation):
                                if isinstance(annotation_node, ast.Name):
                                    if target := enum_target(annotation_node):
                                        schema_enum_types.add(target)
            if isinstance(node, ast.Attribute):
                chain = _attribute_chain(node)
                if len(chain) == 2 and chain[0] == "cls":
                    target = class_for(node)
                elif len(chain) == 2:
                    target = enum_target(ast.Name(id=chain[0]))
                elif len(chain) >= 3 and chain[0] in module_aliases:
                    target = enum_target(ast.Attribute(value=ast.Name(id=chain[0]), attr=chain[1]))
                else:
                    target = None
                if target and chain[-1] in enum_members[target][1]:
                    member_references.add((target, chain[-1]))
            elif isinstance(node, ast.Name) and node.id in local_imports:
                target_module, _, imported_name = local_imports[node.id].rpartition(".")
                target = f"{target_module}.{imported_name}"
                # Directly imported enum members resolve through their class.
                if target_module and target_module in enum_members:
                    if imported_name in enum_members[target_module][1]:
                        member_references.add((target_module, imported_name))
            elif isinstance(node, ast.For):
                if target := enum_target(node.iter):
                    iterated_enums.add(target)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {"tuple", "list", "set", "frozenset"}:
                    for argument in node.args:
                        if target := enum_target(argument):
                            iterated_enums.add(target)

    return [
        (path, line, enum_name, member)
        for enum_name, (path, members) in enum_members.items()
        for member, line in members.items()
        if (enum_name, member) not in member_references
        and enum_name not in iterated_enums
        and enum_name not in schema_enum_types
        and not any(
            isinstance(value, ast.Constant)
            and value.value == member.lower()
            and value.value in schema_fields
            and enum_name == "datp.core.enums.PayloadKey"
            for tree in sources.values()
            for value in ast.walk(tree)
        )
    ]


def test_every_enum_member_has_a_production_use() -> None:
    violations = [
        f"{path.relative_to(SOURCE_ROOT)}:{line}: unused {enum_name}.{member}"
        for path, line, enum_name, member in unused_enum_members(scan_production_sources())
    ]
    assert not violations, violations


def test_dead_enum_member_mutation_fails_and_iteration_is_a_valid_use() -> None:
    dead = Path("synthetic.py")
    dead_tree = ast.parse(
        "from enum import StrEnum\n"
        "class State(StrEnum):\n"
        "    LIVE = 'live'\n"
        "    DEAD = 'dead'\n"
        "def current() -> State:\n"
        "    return State.LIVE\n"
    )
    iterated_tree = ast.parse(
        "from enum import StrEnum\n"
        "class State(StrEnum):\n"
        "    LIVE = 'live'\n"
        "    OTHER = 'other'\n"
        "def choices() -> tuple[State, ...]:\n"
        "    return tuple(State)\n"
    )
    assert any(item[3] == "DEAD" for item in unused_enum_members({dead: dead_tree}))
    assert not unused_enum_members({dead: iterated_tree})


def test_only_real_schema_use_counts_as_an_enum_contract() -> None:
    source = Path("synthetic.py")
    pydantic_contract = ast.parse(
        "from enum import StrEnum\n"
        "class State(StrEnum):\n"
        "    LIVE = 'live'\n"
        "    OTHER = 'other'\n"
        "class Request(BaseModel):\n"
        "    state: State\n"
    )
    dataclass_annotation = ast.parse(
        "from enum import StrEnum\n"
        "class State(StrEnum):\n"
        "    LIVE = 'live'\n"
        "    OTHER = 'other'\n"
        "class Container:\n"
        "    state: State\n"
        "def current() -> State:\n"
        "    return State.LIVE\n"
    )

    assert not unused_enum_members({source: pydantic_contract})
    assert any(
        item[3] == "OTHER"
        for item in unused_enum_members({source: dataclass_annotation})
    )
