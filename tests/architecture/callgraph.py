import ast
from dataclasses import dataclass
from pathlib import Path
import tomllib

from tests.architecture.source_index import SOURCE_ROOT, discover_production_files, parse_source

_EXTERNAL_CALLBACKS = {
    "flwr.client.NumPyClient": {"get_parameters", "fit", "evaluate"},
    "flwr.server.strategy.FedAvg": {
        "aggregate_evaluate",
        "aggregate_fit",
        "configure_evaluate",
        "configure_fit",
    },
}
_PYDANTIC_VALIDATION_METHODS = {"model_validate", "model_validate_json"}


@dataclass(frozen=True)
class Definition:
    module: str
    name: str
    line: int
    path: Path
    kind: str = "function"
    symbol: str | None = None


def module_name(path: Path) -> str:
    parts = path.relative_to(SOURCE_ROOT).with_suffix("").parts
    if parts[-1] == "__init__":
        package = parts[:-1]
        return ".".join(package) or "datp"
    return ".".join(parts)


def _has_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef, names: set[str]) -> bool:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Attribute) and target.attr in names:
            return True
        if isinstance(target, ast.Name) and target.id in names:
            return True
    return False


def is_framework_entry(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return _has_decorator(node, {"command", "callback"})


def references(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            names.add(child.attr)
    return names


def loaded_names(node: ast.AST) -> set[str]:
    return {
        child.id
        for child in ast.walk(node)
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
    }


def _scope_nodes(node: ast.AST) -> list[ast.AST]:
    pending = [node]
    found: list[ast.AST] = []
    while pending:
        current = pending.pop()
        found.append(current)
        if current is not node and isinstance(
            current, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda
        ):
            continue
        pending.extend(ast.iter_child_nodes(current))
    return found


def _module_execution_nodes(node: ast.Module) -> list[ast.AST]:
    pending: list[ast.AST] = list(node.body)
    found: list[ast.AST] = []
    while pending:
        current = pending.pop()
        if isinstance(current, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        found.append(current)
        pending.extend(ast.iter_child_nodes(current))
    return found


def _local_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    arguments = node.args
    names = {
        argument.arg
        for argument in (
            *arguments.posonlyargs,
            *arguments.args,
            *arguments.kwonlyargs,
        )
    }
    if arguments.vararg:
        names.add(arguments.vararg.arg)
    if arguments.kwarg:
        names.add(arguments.kwarg.arg)
    for child in _scope_nodes(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
            names.add(child.id)
        elif isinstance(child, ast.Import):
            names.update(alias.asname or alias.name.split(".")[0] for alias in child.names)
        elif isinstance(child, ast.ImportFrom):
            names.update(alias.asname or alias.name for alias in child.names)
        elif child is not node and isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
            names.add(child.name)
        elif child is not node and isinstance(child, ast.ClassDef):
            names.add(child.name)
    return names


def _enum_classes(paths: list[Path]) -> set[str]:
    enum_bases = {"Enum", "StrEnum", "IntEnum", "Flag", "IntFlag"}
    return {
        node.name
        for path in paths
        for node in ast.walk(parse_source(path))
        if isinstance(node, ast.ClassDef)
        and any(
            (isinstance(base, ast.Name) and base.id in enum_bases)
            or (isinstance(base, ast.Attribute) and base.attr in enum_bases)
            for base in node.bases
        )
    }


def _protocol_class(node: ast.ClassDef) -> bool:
    return any(
        (isinstance(base, ast.Name) and base.id == "Protocol")
        or (isinstance(base, ast.Attribute) and base.attr == "Protocol")
        for base in node.bases
    )


def _import_targets(tree: ast.Module) -> dict[str, str]:
    targets: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                local = alias.asname or alias.name
                base = node.module.removeprefix("datp.")
                targets[local] = ".".join(part for part in (base, alias.name) if part)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                targets[local] = alias.name.removeprefix("datp.")
    return targets


def _reexported_imports(tree: ast.Module) -> dict[str, str]:
    exported = {
        item.value
        for statement in tree.body
        if isinstance(statement, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__all__" for target in statement.targets)
        and isinstance(statement.value, ast.List | ast.Tuple)
        for item in statement.value.elts
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    }
    reexports: dict[str, str] = {}
    for statement in tree.body:
        if not isinstance(statement, ast.ImportFrom) or not statement.module:
            continue
        if not statement.module.startswith("datp."):
            continue
        imported_module = statement.module.removeprefix("datp.")
        for imported in statement.names:
            local = imported.asname or imported.name
            if local in exported:
                reexports[local] = f"{imported_module}.{imported.name}"
    return reexports


def _dynamic_reexports(tree: ast.Module) -> dict[str, str]:
    """Resolve the module-level __getattr__ pattern used for declared exports."""
    exported = {
        item.value
        for statement in tree.body
        if isinstance(statement, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__all__" for target in statement.targets)
        and isinstance(statement.value, ast.List | ast.Tuple)
        for item in statement.value.elts
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    }
    getter = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and node.name == "__getattr__"
        ),
        None,
    )
    if getter is None:
        return {}

    module_aliases: dict[str, str] = {}
    direct_imports: dict[str, str] = {}
    forwards_module_attribute = False
    for node in ast.walk(getter):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("datp."):
            imported_module = node.module.removeprefix("datp.")
            for alias in node.names:
                imported_target = f"{imported_module}.{alias.name}"
                if alias.name == "*":
                    continue
                if alias.name[:1].islower() and alias.asname:
                    module_aliases[alias.asname] = imported_target
                    continue
                direct_imports[alias.asname or alias.name] = (
                    imported_target
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("datp."):
                    module_aliases[alias.asname or alias.name.split(".")[0]] = (
                        alias.name.removeprefix("datp.")
                    )
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.Call):
            call = node.value
            if (
                isinstance(call.func, ast.Name)
                and call.func.id == "getattr"
                and len(call.args) >= 2
                and isinstance(call.args[0], ast.Name)
                and isinstance(call.args[1], ast.Name)
                and call.args[1].id == "name"
            ):
                forwards_module_attribute = True

    result = {
        name: direct_imports[name]
        for name in exported
        if name in direct_imports
    }
    if forwards_module_attribute:
        for node in ast.walk(getter):
            if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Call):
                continue
            call = node.value
            if (
                isinstance(call.func, ast.Name)
                and call.func.id == "getattr"
                and len(call.args) >= 2
                and isinstance(call.args[0], ast.Name)
                and isinstance(call.args[1], ast.Name)
                and call.args[1].id == "name"
                and call.args[0].id in module_aliases
            ):
                module = module_aliases[call.args[0].id]
                result.update(
                    {
                        name: f"{module}.{name}"
                        for name in exported
                        if name not in result
                    }
                )
    return result


def _local_import_targets(
    node: ast.AST, module: str, imports: dict[str, str]
) -> dict[str, str]:
    targets = dict(imports)
    for child in _scope_nodes(node):
        if isinstance(child, ast.ImportFrom) and child.module:
            base = child.module.removeprefix("datp.")
            for alias in child.names:
                targets[alias.asname or alias.name] = ".".join(
                    part for part in (base, alias.name) if part
                )
        elif isinstance(child, ast.Import):
            for alias in child.names:
                if alias.name.startswith("datp."):
                    targets[alias.asname or alias.name.split(".")[0]] = alias.name.removeprefix(
                        "datp."
                    )
    return targets


def _internal_import_modules(node: ast.AST) -> set[str]:
    modules: set[str] = set()
    for child in _scope_nodes(node):
        if (
            isinstance(child, ast.ImportFrom)
            and child.module
            and child.module.startswith("datp")
        ):
            modules.add(child.module.removeprefix("datp."))
            for alias in child.names:
                # ``from datp.package import submodule`` imports that module at
                # runtime even though the AST records only the package name.
                # Restrict this inference to lowercase names, which are the
                # project's module import convention.
                if alias.name[:1].islower():
                    modules.add(
                        f"{child.module.removeprefix('datp.')}.{alias.name}"
                    )
        elif isinstance(child, ast.Import):
            modules.update(
                alias.name.removeprefix("datp.")
                for alias in child.names
                if alias.name.startswith("datp.")
            )
    return modules


def _package_initializers(imported_module: str) -> set[str]:
    if not imported_module:
        return {"datp"}
    parts = imported_module.split(".")
    return {".".join(parts[:index]) for index in range(1, len(parts) + 1)}


def _cli_registered_entries(paths: list[Path]) -> set[str]:
    modules = {module_name(path): parse_source(path) for path in paths}
    imports = {name: _import_targets(tree) for name, tree in modules.items()}
    apps: dict[str, str] = {}

    for module, tree in modules.items():
        for node in tree.body:
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign):
                targets, value = [node.target], node.value
            else:
                continue
            if (
                not isinstance(value, ast.Call)
                or _attribute_chain(value.func)[-1:] != ["Typer"]
            ):
                continue
            for target in targets:
                if isinstance(target, ast.Name):
                    apps[f"{module}.{target.id}"] = f"{module}.{target.id}"

    for module, imported_names in imports.items():
        for local, target in imported_names.items():
            if target in apps:
                apps[f"{module}.{local}"] = target

    mounted_apps: dict[str, set[str]] = {}
    for module, tree in modules.items():
        for node in ast.walk(tree):
            if (
                not isinstance(node, ast.Call)
                or not isinstance(node.func, ast.Attribute)
                or node.func.attr != "add_typer"
                or not isinstance(node.func.value, ast.Name)
                or not node.args
                or not isinstance(node.args[0], ast.Name)
            ):
                continue
            receiver = apps.get(f"{module}.{node.func.value.id}")
            child = apps.get(f"{module}.{node.args[0].id}")
            if receiver is not None and child is not None:
                mounted_apps.setdefault(receiver, set()).add(child)

    reachable_apps = {"cli.app"}
    pending_apps = ["cli.app"]
    while pending_apps:
        parent = pending_apps.pop()
        for child in mounted_apps.get(parent, set()):
            if child not in reachable_apps:
                reachable_apps.add(child)
                pending_apps.append(child)

    entries: set[str] = set()
    for module, tree in modules.items():
        if not module.startswith("cli"):
            continue
        module_imports = imports[module]
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                for decorator in node.decorator_list:
                    target = decorator.func if isinstance(decorator, ast.Call) else decorator
                    if (
                        isinstance(target, ast.Attribute)
                        and target.attr in {"command", "callback"}
                        and isinstance(target.value, ast.Name)
                        and apps.get(f"{module}.{target.value.id}") in reachable_apps
                    ):
                        entries.add(f"{module}.{node.name}")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Call):
                registrar = node.func
                if (
                    not isinstance(registrar.func, ast.Attribute)
                    or registrar.func.attr != "command"
                    or not isinstance(registrar.func.value, ast.Name)
                    or apps.get(f"{module}.{registrar.func.value.id}") not in reachable_apps
                ):
                    continue
                for argument in node.args:
                    if isinstance(argument, ast.Name):
                        entries.add(
                            module_imports.get(argument.id, f"{module}.{argument.id}")
                        )
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _attribute_chain(node.func)[-1:] != ["Typer"]:
                continue
            callback = next(
                (
                    keyword.value
                    for keyword in node.keywords
                    if keyword.arg == "callback"
                ),
                None,
            )
            if not isinstance(callback, ast.Name):
                continue
            assigned_apps = {
                f"{module}.{target.id}"
                for statement in tree.body
                if isinstance(statement, ast.Assign)
                and isinstance(statement.value, ast.Call)
                and statement.value is node
                for target in statement.targets
                if isinstance(target, ast.Name)
            }
            if assigned_apps & reachable_apps:
                entries.add(
                    module_imports.get(callback.id, f"{module}.{callback.id}")
                )
    return entries


def _attribute_chain(node: ast.AST) -> list[str]:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return list(reversed(parts))


def _external_callback_names(node: ast.ClassDef, imports: dict[str, str]) -> set[str]:
    callbacks: set[str] = set()
    for base in node.bases:
        chain = _attribute_chain(base)
        if chain and chain[0] in imports:
            external_base = ".".join((imports[chain[0]], *chain[1:]))
            callbacks.update(_EXTERNAL_CALLBACKS.get(external_base, set()))
    return callbacks


def _qualified_definition(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
    module: str,
    parents: dict[ast.AST, ast.AST],
) -> tuple[str, bool]:
    scope: list[str] = []
    nested_function = False
    parent = parents.get(node)
    while parent is not None:
        if isinstance(parent, ast.FunctionDef | ast.AsyncFunctionDef):
            scope.append(parent.name)
            nested_function = True
        elif isinstance(parent, ast.ClassDef):
            scope.append(parent.name)
        parent = parents.get(parent)
    return ".".join((module, *reversed(scope), node.name)), nested_function


def _resolve_name(
    name: str, module: str, imports: dict[str, str], by_name: dict[str, list[Definition]]
) -> str | None:
    imported = imports.get(name)
    if imported is not None:
        return imported
    local = f"{module}.{name}"
    if local in by_name:
        return local
    candidates = by_name.get(name, [])
    return name if len(candidates) == 1 else None


def _class_target(
    expression: ast.AST | None,
    module: str,
    imports: dict[str, str],
    class_names: set[str],
) -> str | None:
    if isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.BitOr):
        candidates = {
            target
            for side in (expression.left, expression.right)
            if (target := _class_target(side, module, imports, class_names))
        }
        return next(iter(candidates)) if len(candidates) == 1 else None
    if isinstance(expression, ast.Name):
        imported = imports.get(expression.id)
        local = f"{module}.{expression.id}"
        candidate = imported or local
        return candidate if candidate in class_names else None
    if isinstance(expression, ast.Attribute):
        chain = _attribute_chain(expression)
        if chain and chain[0] in imports:
            candidate = ".".join((imports[chain[0]], *chain[1:]))
            return candidate if candidate in class_names else None
    return None


def _class_element_target(
    expression: ast.AST | None,
    module: str,
    imports: dict[str, str],
    class_names: set[str],
) -> str | None:
    if not isinstance(expression, ast.Subscript):
        return None
    elements = expression.slice.elts if isinstance(expression.slice, ast.Tuple) else (expression.slice,)
    for element in elements:
        if target := _class_target(element, module, imports, class_names):
            return target
    return None


def _expression_type(
    expression: ast.AST,
    module: str,
    imports: dict[str, str],
    class_names: set[str],
    local_types: dict[str, str],
    class_fields: dict[str, dict[str, str]],
) -> str | None:
    if isinstance(expression, ast.BoolOp):
        candidates = {
            target
            for value in expression.values
            if (
                target := _expression_type(
                    value, module, imports, class_names, local_types, class_fields
                )
            )
        }
        return next(iter(candidates)) if len(candidates) == 1 else None
    if isinstance(expression, ast.IfExp):
        body_type = _expression_type(
            expression.body, module, imports, class_names, local_types, class_fields
        )
        else_type = _expression_type(
            expression.orelse, module, imports, class_names, local_types, class_fields
        )
        return body_type if body_type == else_type else None
    if isinstance(expression, ast.Call):
        return _class_target(expression.func, module, imports, class_names)
    if isinstance(expression, ast.Name):
        return local_types.get(expression.id)
    if isinstance(expression, ast.Attribute):
        chain = _attribute_chain(expression)
        if chain and chain[0] in imports:
            receiver_type = imports[chain[0]]
            members = chain[1:]
            if receiver_type in class_names:
                members = [chain[1], *chain[2:]] if len(chain) > 1 else []
            else:
                receiver_type = ""
        else:
            receiver_type = local_types.get(chain[0], "") if chain else ""
            members = chain[1:]
        for member in members:
            receiver_type = class_fields.get(receiver_type, {}).get(member, "")
            if not receiver_type:
                return None
        return receiver_type or None
    return None


def _local_types(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    module: str,
    imports: dict[str, str],
    class_names: set[str],
    enclosing_class: str | None,
    parents: dict[ast.AST, ast.AST],
    class_fields: dict[str, dict[str, str]],
) -> dict[str, str]:
    types: dict[str, str] = {}
    element_types: dict[str, str] = {}
    if enclosing_class:
        types["self"] = f"{module}.{enclosing_class}"
        types["cls"] = f"{module}.{enclosing_class}"

    enclosing_functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    parent = parents.get(node)
    while parent is not None:
        if isinstance(parent, ast.FunctionDef | ast.AsyncFunctionDef):
            enclosing_functions.append(parent)
        parent = parents.get(parent)
    for outer in reversed(enclosing_functions):
        for argument in (
            *outer.args.posonlyargs,
            *outer.args.args,
            *outer.args.kwonlyargs,
            *((outer.args.vararg,) if outer.args.vararg else ()),
            *((outer.args.kwarg,) if outer.args.kwarg else ()),
        ):
            target = _class_target(argument.annotation, module, imports, class_names)
            if target:
                types[argument.arg] = target
        for child in _scope_nodes(outer):
            if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                target = _class_target(child.annotation, module, imports, class_names)
                if target:
                    types[child.target.id] = target
            elif (
                isinstance(child, ast.Assign)
                and isinstance(child.value, ast.Call)
                and (target := _class_target(child.value.func, module, imports, class_names))
            ):
                for assigned in child.targets:
                    if isinstance(assigned, ast.Name):
                        types[assigned.id] = target
    arguments = (
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
        *((node.args.vararg,) if node.args.vararg else ()),
        *((node.args.kwarg,) if node.args.kwarg else ()),
    )
    for argument in arguments:
        target = _class_target(argument.annotation, module, imports, class_names)
        if target:
            types[argument.arg] = target
        if target := _class_element_target(
            argument.annotation, module, imports, class_names
        ):
            element_types[argument.arg] = target
    scope = _scope_nodes(node)
    for _ in range(2):
        for child in scope:
            if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                target = _class_target(child.annotation, module, imports, class_names)
                if target:
                    types[child.target.id] = target
                if target := _class_element_target(child.annotation, module, imports, class_names):
                    element_types[child.target.id] = target
            elif isinstance(child, ast.Assign):
                target = _expression_type(
                    child.value, module, imports, class_names, types, class_fields
                )
                if target:
                    for assigned in child.targets:
                        if isinstance(assigned, ast.Name):
                            types[assigned.id] = target
                elif isinstance(child.value, ast.Tuple):
                    for assigned in child.targets:
                        if isinstance(assigned, ast.Tuple):
                            for name, value in zip(assigned.elts, child.value.elts, strict=False):
                                item_type = _expression_type(
                                    value, module, imports, class_names, types, class_fields
                                )
                                if isinstance(name, ast.Name) and item_type:
                                    types[name.id] = item_type
            elif (
                isinstance(child, ast.For)
                and isinstance(child.target, ast.Name)
                and isinstance(child.iter, ast.Name)
                and child.iter.id in element_types
            ):
                types[child.target.id] = element_types[child.iter.id]
    return types


def resolve_attribute(
    node: ast.Attribute,
    imports: dict[str, str],
    by_name: dict[str, list[Definition]],
    local_types: dict[str, str],
    class_fields: dict[str, dict[str, str]],
) -> str | None:
    chain = _attribute_chain(node)
    if not chain:
        return None
    imported = imports.get(chain[0])
    if imported is not None:
        qualified = ".".join((imported, *chain[1:]))
        if qualified in by_name:
            return qualified
        if (
            chain[1:] and chain[-1] in _PYDANTIC_VALIDATION_METHODS
            and any(item.kind == "class" for item in by_name.get(imported, ()))
        ):
            return imported

        return None
    classes = [item for item in by_name.get(chain[0], ()) if item.kind == "class"]
    if len(classes) == 1:
        qualified = ".".join((classes[0].symbol or classes[0].module, *chain[1:]))
        if qualified in by_name:
            return qualified
        if chain[1:] and chain[-1] in _PYDANTIC_VALIDATION_METHODS:
            return classes[0].symbol or classes[0].module
    receiver_type = local_types.get(chain[0])
    if receiver_type:
        for member in chain[1:]:
            qualified = f"{receiver_type}.{member}"
            if qualified in by_name:
                receiver_type = qualified
                continue
            receiver_type = class_fields.get(receiver_type, {}).get(member, "")
            if not receiver_type:
                return None
        return receiver_type or None

    return None


def build() -> tuple[dict[str, list[Definition]], dict[Definition, set[str]], list[Definition]]:
    by_name: dict[str, list[Definition]] = {}
    edges: dict[Definition, set[str]] = {}
    roots: list[Definition] = []
    imports_by_module: dict[str, dict[str, str]] = {}
    class_by_node: dict[int, str] = {}
    scope_by_definition: dict[Definition, str] = {}
    class_fields: dict[str, dict[str, str]] = {}
    reexports: dict[str, str] = {}
    public_exports: set[str] = set()
    class_names: set[str] = set()
    parents_by_node: dict[ast.AST, ast.AST] = {}
    paths = discover_production_files()
    registered_cli_entries = _cli_registered_entries(paths)
    project_config = tomllib.loads((SOURCE_ROOT.parent.parent / "pyproject.toml").read_text())
    configured_scripts = project_config.get("project", {}).get("scripts", {})
    script_entries = {
        f"{target_module.removeprefix('datp.')}.{target_name}"
        for target in configured_scripts.values()
        if isinstance(target, str) and ":" in target
        for target_module, target_name in [target.split(":", maxsplit=1)]
    }
    nodes: dict[Definition, ast.AST] = {}
    module_definitions: dict[str, Definition] = {}
    for path in paths:
        tree = parse_source(path)
        module = module_name(path)
        imports_by_module[module] = _import_targets(tree)
        reexports.update(
            {
                f"{module}.{name}": target
                for name, target in (
                    _reexported_imports(tree) | _dynamic_reexports(tree)
                ).items()
            }
        )
        public_exports.update(
            f"{module}.{item.value}"
            for statement in tree.body
            if isinstance(statement, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "__all__"
                for target in statement.targets
            )
            and isinstance(statement.value, ast.List | ast.Tuple)
            for item in statement.value.elts
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        )
        if _dynamic_reexports(tree):
            public_exports.add(f"{module}.__getattr__")
        module_definition = Definition(
            module, "<module>", 1, path, "module", f"{module}.__module__"
        )
        module_definitions[module] = module_definition
        by_name.setdefault(f"{module}.__module__", []).append(module_definition)
        edges[module_definition] = set()
        nodes[module_definition] = tree
        if module == "cli":
            roots.append(module_definition)
        if module.endswith(".__main__"):
            roots.append(module_definition)
        parents: dict[ast.AST, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent
        parents_by_node.update(parents)
        for node in tree.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if (
                not isinstance(target, ast.Name)
                or not target.id[:1].isupper()
                or target.id.isupper()
            ):
                continue
            definition = Definition(
                module_name(path),
                target.id,
                node.lineno,
                path,
                "alias",
                f"{module}.{target.id}",
            )
            by_name.setdefault(target.id, []).append(definition)
            by_name.setdefault(f"{module}.{target.id}", []).append(definition)
            edges[definition] = set()
            nodes[definition] = node.value
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                qualified, nested = _qualified_definition(node, module, parents)
                definition = Definition(
                    module_name(path), node.name, node.lineno, path, "class", qualified
                )
                if not nested:
                    by_name.setdefault(node.name, []).append(definition)
                by_name.setdefault(qualified, []).append(definition)
                class_names.add(qualified)
                edges[definition] = set()
                nodes[definition] = node
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                parent = parents.get(node)
                while parent is not None and not isinstance(parent, ast.ClassDef):
                    parent = parents.get(parent)
                qualified, nested = _qualified_definition(node, module, parents)
                definition = Definition(
                    module_name(path), node.name, node.lineno, path, symbol=qualified
                )
                if not nested:
                    by_name.setdefault(node.name, []).append(definition)
                by_name.setdefault(qualified, []).append(definition)
                scope_by_definition[definition] = qualified
                edges[definition] = set()
                nodes[definition] = node
                class_by_node[id(node)] = parent.name if isinstance(parent, ast.ClassDef) else ""
                if (
                    qualified in registered_cli_entries
                    or (module == "cli" and node.name == "cli_entry")
                    or qualified in script_entries
                ):
                    roots.append(definition)

    for definition, node in nodes.items():
        if not isinstance(node, ast.ClassDef):
            continue
        fields: dict[str, str] = {}
        module_imports = imports_by_module[definition.module]
        for field in node.body:
            if isinstance(field, ast.AnnAssign) and isinstance(field.target, ast.Name):
                target = _class_target(
                    field.annotation, definition.module, module_imports, class_names
                )
                if target:
                    fields[field.target.id] = target
        class_key = scope_by_definition.get(definition, f"{definition.module}.{definition.name}")
        class_fields[class_key] = fields

    for definition, node in nodes.items():
        if not isinstance(node, ast.ClassDef):
            continue
        class_key = scope_by_definition.get(definition, f"{definition.module}.{definition.name}")
        module_imports = imports_by_module[definition.module]
        initializer = next(
            (
                member
                for member in node.body
                if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef)
                and member.name == "__init__"
            ),
            None,
        )
        if initializer is None:
            continue
        local_types = _local_types(
            initializer,
            definition.module,
            module_imports,
            class_names,
            definition.name,
            parents_by_node,
            class_fields,
        )
        for child in _scope_nodes(initializer):
            if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Attribute):
                if isinstance(child.target.value, ast.Name) and child.target.value.id == "self":
                    target = _class_target(
                        child.annotation,
                        definition.module,
                        module_imports,
                        class_names,
                    )
                    if target:
                        class_fields[class_key][child.target.attr] = target
            elif isinstance(child, ast.Assign):
                target = _expression_type(
                    child.value,
                    definition.module,
                    module_imports,
                    class_names,
                    local_types,
                    class_fields,
                )
                if target:
                    for assigned in child.targets:
                        if (
                            isinstance(assigned, ast.Attribute)
                            and isinstance(assigned.value, ast.Name)
                            and assigned.value.id == "self"
                        ):
                            class_fields[class_key][assigned.attr] = target

    enum_names = _enum_classes(paths)
    for definition, node in nodes.items():
        module_imports = imports_by_module[definition.module]
        if definition.kind == "module" and isinstance(node, ast.Module):
            for statement in node.body:
                if isinstance(statement, ast.ImportFrom) and statement.module:
                    imported_module = (
                        statement.module.removeprefix("datp.")
                        if statement.module.startswith("datp.")
                        else ""
                    )
                    imported_modules = {imported_module}
                    if imported_module:
                        imported_modules.update(
                            f"{imported_module}.{alias.name}"
                            for alias in statement.names
                            if alias.name[:1].islower()
                        )
                    edges[definition].update(
                        f"{package}.__module__"
                        for imported in imported_modules
                        for package in _package_initializers(imported)
                        if package in module_definitions
                    )
                elif isinstance(statement, ast.Import):
                    for alias in statement.names:
                        if alias.name.startswith("datp."):
                            imported_module = alias.name.removeprefix("datp.")
                            edges[definition].update(
                                f"{package}.__module__"
                                for package in _package_initializers(imported_module)
                                if package in module_definitions
                            )
            for child in _module_execution_nodes(node):
                if not isinstance(child, ast.Call):
                    continue
                if isinstance(child.func, ast.Name):
                    target = _resolve_name(
                        child.func.id, definition.module, module_imports, by_name
                    )
                    if target:
                        edges[definition].add(target)
                elif isinstance(child.func, ast.Attribute):
                    target = resolve_attribute(
                        child.func, module_imports, by_name, {}, class_fields
                    )
                    if target:
                        edges[definition].add(target)
            continue
        if definition.kind == "alias":
            edges[definition].update(
                target
                for name in references(node) - {definition.name}
                if (target := _resolve_name(name, definition.module, module_imports, by_name))
            )
            continue
        if isinstance(node, ast.ClassDef):
            edges[definition].update(
                target
                for base in node.bases
                for name in references(base)
                if (target := _resolve_name(name, definition.module, module_imports, by_name))
            )
            for field in node.body:
                if isinstance(field, ast.AnnAssign):
                    edges[definition].update(
                        target
                        for name in references(field.annotation)
                        if (
                            target := _resolve_name(
                                name, definition.module, module_imports, by_name
                            )
                        )
                    )
                if isinstance(field, ast.FunctionDef | ast.AsyncFunctionDef) and (
                    field.name == "__init__"
                    or _has_decorator(field, {"model_validator", "field_validator"})
                    or _protocol_class(node)
                    or (
                        field.name.startswith("__")
                        and field.name.endswith("__")
                    )
                ):
                    edges[definition].add(f"{definition.module}.{definition.name}.{field.name}")
            callbacks = _external_callback_names(node, module_imports)
            for field in node.body:
                if (
                    isinstance(field, ast.FunctionDef | ast.AsyncFunctionDef)
                    and field.name in callbacks
                ):
                    edges[definition].add(
                        f"{definition.module}.{definition.name}.{field.name}"
                    )
            continue

        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            module_imports = _local_import_targets(
                node, definition.module, module_imports
            )
            edges[definition].update(
                f"{package}.__module__"
                for imported_module in _internal_import_modules(node)
                for package in _package_initializers(imported_module)
                if package in module_definitions
            )
            local_names = _local_names(node)
            enclosing_class = class_by_node.get(id(node)) or None
            local_types = _local_types(
                node,
                definition.module,
                module_imports,
                class_names,
                enclosing_class,
                parents_by_node,
                class_fields,
            )
            nested_callable_names = {
                child.name
                for child in _scope_nodes(node)
                if child is not node and isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef)
            }
            for child in _scope_nodes(node):
                if (
                    isinstance(child, ast.Return)
                    and isinstance(child.value, ast.Name)
                    and child.value.id in nested_callable_names
                ):
                    edges[definition].add(
                        f"{scope_by_definition[definition]}.{child.value.id}"
                    )
            for annotation in (
                *(argument.annotation for argument in node.args.posonlyargs),
                *(argument.annotation for argument in node.args.args),
                *(argument.annotation for argument in node.args.kwonlyargs),
                node.args.vararg.annotation if node.args.vararg else None,
                node.args.kwarg.annotation if node.args.kwarg else None,
                node.returns,
            ):
                if annotation is not None:
                    edges[definition].update(
                        target
                        for name in references(annotation)
                        if (
                            target := _resolve_name(
                                name, definition.module, module_imports, by_name
                            )
                        )
                    )
            edges[definition].update(
                target
                for name in _decorator_references(node)
                if (target := _resolve_name(name, definition.module, module_imports, by_name))
            )
            for child in _scope_nodes(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        if (
                            child.func.id not in local_names
                            or child.func.id in nested_callable_names
                            or child.func.id in module_imports
                        ):
                            target = (
                                f"{scope_by_definition[definition]}.{child.func.id}"
                                if child.func.id in nested_callable_names
                                else _resolve_name(
                                    child.func.id, definition.module, module_imports, by_name
                                )
                            )
                            if target:
                                edges[definition].add(target)
                    elif isinstance(child.func, ast.Attribute):
                        target = resolve_attribute(
                            child.func,
                            module_imports,
                            by_name,
                            local_types,
                            class_fields,
                        )
                        if target:
                            edges[definition].add(target)
                    for argument in (
                        *child.args,
                        *(keyword.value for keyword in child.keywords),
                    ):
                        edges[definition].update(
                            target
                            for name in loaded_names(argument)
                            if (name not in local_names or name in nested_callable_names)
                            if (
                                target := (
                                    f"{scope_by_definition[definition]}.{name}"
                                    if name in nested_callable_names
                                    else _resolve_name(
                                        name, definition.module, module_imports, by_name
                                    )
                                )
                            )
                        )
                elif isinstance(child, ast.Attribute):
                    target = resolve_attribute(
                        child,
                        module_imports,
                        by_name,
                        local_types,
                        class_fields,
                    )
                    if target:
                        edges[definition].add(target)
                elif isinstance(child, ast.Name) and child.id in enum_names:
                    target = _resolve_name(child.id, definition.module, module_imports, by_name)
                    if target:
                        edges[definition].add(target)
                elif isinstance(child, ast.AnnAssign):
                    edges[definition].update(
                        target
                        for name in references(child.annotation)
                        if (
                            target := _resolve_name(
                                name, definition.module, module_imports, by_name
                            )
                        )
                    )
    protocol_methods: dict[str, set[str]] = {}
    concrete_methods: dict[str, set[str]] = {}
    for definition, node in nodes.items():
        if not isinstance(node, ast.ClassDef):
            continue
        class_name = f"{definition.module}.{definition.name}"
        method_names = {
            member.name
            for member in node.body
            if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef)
        }
        if _protocol_class(node):
            protocol_methods[class_name] = method_names
        else:
            concrete_methods[class_name] = method_names
    for protocol, required in protocol_methods.items():
        implementations = {
            candidate
            for candidate, provided in concrete_methods.items()
            if required <= provided
        }
        for method in required:
            protocol_method = f"{protocol}.{method}"
            if protocol_method not in by_name:
                continue
            for definition in by_name[protocol_method]:
                for implementation in implementations:
                    target = f"{implementation}.{method}"
                    if target in by_name:
                        edges[definition].add(target)

    for alias, target in reexports.items():
        if resolved := by_name.get(target):
            by_name.setdefault(alias, []).extend(resolved)

    for public_name in public_exports:
        roots.extend(
            definition
            for definition in by_name.get(public_name, [])
            if definition.kind != "module"
        )

    return by_name, edges, roots


def _decorator_references(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    return {name for decorator in node.decorator_list for name in references(decorator)}


def reachable(
    by_name: dict[str, list[Definition]],
    edges: dict[Definition, set[str]],
    roots: list[Definition],
) -> set[Definition]:
    seen: set[Definition] = set()
    pending = list(roots)
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        for name in edges[current]:
            pending.extend(by_name.get(name, []))
    return seen


def shortest_paths(
    by_name: dict[str, list[Definition]],
    edges: dict[Definition, set[str]],
    roots: list[Definition],
) -> dict[Definition, tuple[Definition, ...]]:
    paths: dict[Definition, tuple[Definition, ...]] = {root: (root,) for root in roots}
    pending = list(roots)
    while pending:
        current = pending.pop(0)
        for name in sorted(edges[current]):
            for target in by_name.get(name, []):
                if target not in paths:
                    paths[target] = (*paths[current], target)
                    pending.append(target)
    return paths


def direct_callers(
    by_name: dict[str, list[Definition]], edges: dict[Definition, set[str]]
) -> dict[Definition, set[Definition]]:
    callers: dict[Definition, set[Definition]] = {definition: set() for definition in edges}
    for caller, names in edges.items():
        for name in names:
            for target in by_name.get(name, []):
                if caller != target:
                    callers[target].add(caller)
    return callers


def orphan_diagnostics(
    by_name: dict[str, list[Definition]],
    edges: dict[Definition, set[str]],
    roots: list[Definition],
) -> list[str]:
    paths = shortest_paths(by_name, edges, roots)
    callers = direct_callers(by_name, edges)
    diagnostics: list[str] = []
    for definition in sorted(set(edges) - set(paths), key=lambda item: (item.module, item.line)):
        symbol = definition.symbol or f"{definition.module}.{definition.name}"
        where = f"{symbol} ({definition.path}:{definition.line})"
        direct = sorted(
            item.symbol or f"{item.module}.{item.name}" for item in callers[definition]
        )
        root_names = sorted(item.symbol or f"{item.module}.{item.name}" for item in roots)
        diagnostics.append(
            f"{where}; direct callers={direct or ['none']}; CLI roots={root_names}; "
            "shortest CLI path=none; reason=not reachable from a registered CLI command"
        )
    return diagnostics
