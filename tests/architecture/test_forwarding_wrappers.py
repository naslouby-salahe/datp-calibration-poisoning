import ast

from tests.architecture.source_index import scan_production_sources


def _forwarding_wrapper(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    body = [
        statement
        for statement in node.body
        if not (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        )
    ]
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return False
    call = body[0].value
    if not isinstance(call, ast.Call):
        return False
    positional = [
        argument.arg
        for argument in (*node.args.posonlyargs, *node.args.args)
        if argument.arg not in {"self", "cls"}
    ]
    keyword_only = [argument.arg for argument in node.args.kwonlyargs]
    parameters = [*positional]
    if node.args.vararg is not None:
        parameters.append(f"*{node.args.vararg.arg}")
    parameters.extend(keyword_only)
    if node.args.kwarg is not None:
        parameters.append(f"**{node.args.kwarg.arg}")

    forwarded: list[str | None] = []
    for argument in call.args:
        if isinstance(argument, ast.Name):
            forwarded.append(argument.id)
        elif isinstance(argument, ast.Starred) and isinstance(argument.value, ast.Name):
            forwarded.append(f"*{argument.value.id}")
        else:
            forwarded.append(None)
    for keyword in call.keywords:
        if keyword.arg is None and isinstance(keyword.value, ast.Name):
            forwarded.append(f"**{keyword.value.id}")
        elif keyword.arg is not None and isinstance(keyword.value, ast.Name):
            forwarded.append(keyword.value.id)
        else:
            forwarded.append(None)
    if not parameters and not (
        isinstance(call.func, ast.Name)
        or (
            isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id in {"self", "cls"}
        )
    ):
        return False
    return forwarded == parameters


def _framework_override(
    node: ast.FunctionDef | ast.AsyncFunctionDef, parents: dict[ast.AST, ast.AST]
) -> bool:
    if node.name != "forward":
        return False
    parent = parents.get(node)
    if not isinstance(parent, ast.ClassDef):
        return False
    return any(
        isinstance(base, ast.Attribute) and base.attr in {"Module", "LightningModule"}
        for base in parent.bases
    )


def forwarding_wrappers(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and _forwarding_wrapper(node)
        and not _framework_override(node, parents)
    ]


def test_production_has_no_forwarding_only_wrappers() -> None:
    offenders = [
        f"{path}:{node.lineno} {node.name}"
        for path, tree in scan_production_sources().items()
        for node in forwarding_wrappers(tree)
    ]
    assert not offenders, offenders


def test_forwarding_wrapper_mutation_is_detected() -> None:
    tree = ast.parse(
        "def load(path):\n    return read(path)\n"
        "def delegate(*args, **kwargs):\n    return execute(*args, **kwargs)\n"
    )
    assert [node.name for node in forwarding_wrappers(tree)] == ["load", "delegate"]


def test_semantic_transform_and_framework_override_are_valid() -> None:
    tree = ast.parse(
        """
class Model(pl.LightningModule):
    def forward(self, value):
        return self.model(value)

def normalize(value):
    return transform(value) + 1
"""
    )
    assert not forwarding_wrappers(tree)


def test_class_forwarder_without_framework_contract_is_reported() -> None:
    tree = ast.parse(
        """
class Wrapper:
    def forward(self, value):
        return self.model(value)
"""
    )
    assert [node.name for node in forwarding_wrappers(tree)] == ["forward"]
