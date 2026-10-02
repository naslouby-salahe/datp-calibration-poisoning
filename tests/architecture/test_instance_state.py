import ast
from pathlib import Path

from tests.architecture.source_index import SOURCE_ROOT, scan_production_sources


EXTERNAL_INSTANCE_STATE = {
    (Path("federated/clients.py"), "DatpClient", "cid"),
    (Path("types.py"), "_Concept", "name"),
}


class _InstanceAttributeVisitor(ast.NodeVisitor):
    def __init__(self, root: ast.ClassDef) -> None:
        self.root = root
        self.receivers = {
            argument.arg
            for member in root.body
            if isinstance(member, ast.FunctionDef | ast.AsyncFunctionDef)
            for argument in (*member.args.posonlyargs, *member.args.args)
            if argument.arg in {"self", "cls"}
        }
        self.stores: set[str] = set()
        self.loads: set[str] = set()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if node is self.root:
            self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Name) and node.value.id in self.receivers:
            if isinstance(node.ctx, ast.Store | ast.Del):
                self.stores.add(node.attr)
            else:
                self.loads.add(node.attr)
        self.generic_visit(node)


def unused_instance_attributes(tree: ast.Module) -> list[tuple[str, str, int]]:
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        visitor = _InstanceAttributeVisitor(node)
        visitor.visit(node)
        for name in sorted(visitor.stores - visitor.loads):
            line = min(
                child.lineno
                for child in ast.walk(node)
                if isinstance(child, ast.Attribute)
                and child.attr == name
                and isinstance(child.value, ast.Name)
                and child.value.id in visitor.receivers
                and isinstance(child.ctx, ast.Store | ast.Del)
            )
            violations.append((node.name, name, line))
    return violations


def test_production_has_no_unread_instance_state() -> None:
    violations = [
        f"{relative}:{class_name}.{name}:{line}"
        for path, tree in scan_production_sources().items()
        for class_name, name, line in unused_instance_attributes(tree)
        for relative in [path.relative_to(SOURCE_ROOT)]
        if (relative, class_name, name) not in EXTERNAL_INSTANCE_STATE
    ]
    assert not violations, violations


def test_unread_instance_state_mutation_fails() -> None:
    tree = ast.parse(
        "class Service:\n"
        "    def __init__(self):\n"
        "        self.unused = 1\n"
        "    def execute(self):\n"
        "        return 2\n"
    )
    service = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    assert unused_instance_attributes(ast.Module(body=[service], type_ignores=[])) == [
        ("Service", "unused", 3)
    ]


def test_read_instance_state_remains_valid() -> None:
    tree = ast.parse(
        "class Service:\n"
        "    def __init__(self):\n"
        "        self.value = 1\n"
        "    def execute(self):\n"
        "        return self.value\n"
    )
    service = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    assert unused_instance_attributes(ast.Module(body=[service], type_ignores=[])) == []
