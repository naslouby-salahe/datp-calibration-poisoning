import ast
from pathlib import Path

from tests.architecture.callgraph import (
    Definition,
    build,
    reachable,
    shortest_paths,
)
from tests.architecture.source_index import REPO_ROOT, scan_production_sources

MAX_FUNCTION_ARGUMENTS = 10
MAX_FUNCTION_LINES = 160
MAX_FUNCTION_FAN_OUT = 25
MAX_FUNCTION_FAN_IN = 30


def _argument_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return (
        len(node.args.posonlyargs)
        + len(node.args.args)
        + len(node.args.kwonlyargs)
        + (node.args.vararg is not None)
        + (node.args.kwarg is not None)
    )


def _function_size_violations(tree: ast.AST) -> list[str]:
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if _argument_count(node) > MAX_FUNCTION_ARGUMENTS:
            violations.append(f"{node.name}: {_argument_count(node)} arguments")
        lines = (node.end_lineno or node.lineno) - node.lineno + 1
        if lines > MAX_FUNCTION_LINES:
            violations.append(f"{node.name}: {lines} lines")
    return violations


def _module_graph(sources: dict[Path, ast.Module]) -> dict[str, set[str]]:
    module_by_path: dict[Path, str] = {}
    for path in sources:
        relative = path.relative_to(REPO_ROOT / "src").with_suffix("")
        parts = relative.parts[:-1] if relative.name == "__init__" else relative.parts
        module_by_path[path] = ".".join(parts)
    modules = set(module_by_path.values())
    graph = {module: set() for module in modules}
    for path, tree in sources.items():
        dependencies: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("datp."):
                    imported = node.module
                    dependencies.add(imported)
                    dependencies.update(
                        f"{imported}.{alias.name}"
                        for alias in node.names
                        if alias.name[:1].islower()
                    )
            elif isinstance(node, ast.Import):
                dependencies.update(
                    alias.name
                    for alias in node.names
                    if alias.name.startswith("datp.")
                )
        graph[module_by_path[path]].update(dependencies & modules)
    return graph


def _dependency_cycles(graph: dict[str, set[str]]) -> list[tuple[str, ...]]:
    active: list[str] = []
    complete: set[str] = set()
    cycles: set[tuple[str, ...]] = set()

    def visit(module: str) -> None:
        if module in active:
            cycle = (*active[active.index(module) :], module)
            cycles.add(cycle)
            return
        if module in complete:
            return
        active.append(module)
        for dependency in sorted(graph[module]):
            visit(dependency)
        active.pop()
        complete.add(module)

    for module in sorted(graph):
        visit(module)
    return sorted(cycles)


def _callable_degree_violations(
    by_name: dict[str, list[Definition]],
    edges: dict[Definition, set[str]],
    roots: list[Definition],
) -> list[str]:
    definitions = {
        definition
        for definition in reachable(by_name, edges, roots)
        if definition.kind == "function"
    }
    callers: dict[Definition, set[Definition]] = {
        definition: set() for definition in definitions
    }
    fan_out: dict[Definition, int] = {}
    for caller in definitions:
        callees = {
            candidate
            for name in edges[caller]
            for candidate in by_name.get(name, ())
            if candidate in definitions
        }
        fan_out[caller] = len(callees)
        for callee in callees:
            callers[callee].add(caller)

    violations = []
    for definition in sorted(definitions, key=lambda item: item.symbol or item.name):
        outgoing = fan_out[definition]
        incoming = len(callers[definition])
        if outgoing > MAX_FUNCTION_FAN_OUT:
            violations.append(
                f"{definition.symbol} at {definition.path}:{definition.line} "
                f"has fan-out {outgoing} (limit {MAX_FUNCTION_FAN_OUT})"
            )
        if incoming > MAX_FUNCTION_FAN_IN:
            violations.append(
                f"{definition.symbol} at {definition.path}:{definition.line} "
                f"has fan-in {incoming} (limit {MAX_FUNCTION_FAN_IN})"
            )
    return violations


def _cli_profile(
    root: Definition,
    by_name: dict[str, list[Definition]],
    edges: dict[Definition, set[str]],
) -> tuple[int, int, int, int, int]:
    paths = shortest_paths(by_name, edges, [root])
    reached = set(reachable(by_name, edges, [root]))
    leaves = sum(
        not any(
            target in reached
            for name in edges[definition]
            for target in by_name.get(name, [])
        )
        for definition in reached
    )
    modules = len({definition.module for definition in reached})
    direct_calls = sum(bool(by_name.get(name)) for name in edges[root])
    depth = max((len(path) for path in paths.values()), default=0)
    return direct_calls, len(reached), depth, leaves, modules


def test_function_argument_and_size_limits_match_the_reviewed_source() -> None:
    sources = scan_production_sources()
    violations = [
        f"{path}:{node.lineno} {violation}"
        for path, tree in sources.items()
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        for violation in _function_size_violations(node)
    ]
    assert not violations, violations


def test_argument_and_size_mutations_fail_with_valid_controls() -> None:
    oversized_arguments = ast.parse(
        "def invalid(a,b,c,d,e,f,g,h,i,j,k):\n    return None\n"
    )
    oversized_function = ast.parse(
        "def invalid():\n" + "\n".join("    pass" for _ in range(160))
    )
    valid = ast.parse("def valid(value):\n    return value\n")

    assert _function_size_violations(oversized_arguments)
    assert _function_size_violations(oversized_function)
    assert not _function_size_violations(valid)


def test_ruff_enforces_the_complexity_rule_and_detects_a_mutation(tmp_path: Path) -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "ruff check --select C901 src/datp/" in makefile
    too_complex = tmp_path / "too_complex.py"
    too_complex.write_text(
        "def invalid(value):\n"
        + "\n".join(f"    if value == {index}: pass" for index in range(11))
        + "\n",
        encoding="utf-8",
    )
    from shutil import which
    from subprocess import run

    ruff = which("ruff")
    assert ruff is not None
    result = run(
        [ruff, "check", "--select", "C901", str(too_complex)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "C901" in result.stdout


def test_dependency_graph_has_no_cycles_and_detects_cycle_mutation() -> None:
    production = _module_graph(scan_production_sources())
    assert not _dependency_cycles(production)
    assert _dependency_cycles({"first": {"second"}, "second": {"first"}})
    assert not _dependency_cycles({"first": {"second"}, "second": set()})


def test_cli_reachable_function_fan_in_and_fan_out_stay_bounded() -> None:
    by_name, edges, roots = build()
    assert not _callable_degree_violations(by_name, edges, roots)


def test_function_degree_mutations_fail_and_boundary_controls_pass() -> None:
    root = Definition("cli", "run", 1, Path("cli.py"))
    targets = [
        Definition("service", f"target_{index}", index + 1, Path("service.py"))
        for index in range(MAX_FUNCTION_FAN_OUT + 1)
    ]
    by_name = {target.name: [target] for target in targets}
    by_name[root.name] = [root]
    edges = {root: {target.name for target in targets}, **{target: set() for target in targets}}

    assert _callable_degree_violations(by_name, edges, [root])
    assert not _callable_degree_violations(
        by_name,
        {root: {target.name for target in targets[:MAX_FUNCTION_FAN_OUT]}, **{target: set() for target in targets}},
        [root],
    )

    crowded = Definition("service", "crowded", 100, Path("service.py"))
    callers = [
        Definition("cli", f"caller_{index}", index + 1, Path("cli.py"))
        for index in range(MAX_FUNCTION_FAN_IN + 1)
    ]
    by_name = {crowded.name: [crowded], **{caller.name: [caller] for caller in callers}}
    edges = {caller: {crowded.name} for caller in callers}
    edges[crowded] = set()
    assert _callable_degree_violations(by_name, edges, callers)

    limited_callers = callers[:MAX_FUNCTION_FAN_IN]
    by_name = {crowded.name: [crowded], **{caller.name: [caller] for caller in limited_callers}}
    edges = {caller: {crowded.name} for caller in limited_callers}
    edges[crowded] = set()
    assert not _callable_degree_violations(by_name, edges, limited_callers)


def test_every_cli_command_reaches_a_leaf_across_runtime_modules() -> None:
    by_name, edges, roots = build()
    cli_roots = [
        root
        for root in roots
        if root.kind == "function" and root.path.is_relative_to(REPO_ROOT / "src" / "datp" / "cli")
    ]
    assert cli_roots
    profiles = {root.symbol: _cli_profile(root, by_name, edges) for root in cli_roots}
    violations = {
        command: profile
        for command, profile in profiles.items()
        if profile[0] == 0 or profile[1] < 2 or profile[2] < 2 or profile[3] == 0 or profile[4] < 2
    }
    assert not violations, violations


def test_disconnected_cli_mutation_has_no_runtime_leaf() -> None:
    root = Definition("cli", "command", 1, Path("cli.py"))
    by_name = {root.name: [root]}
    edges = {root: set()}

    assert _cli_profile(root, by_name, edges) == (0, 1, 1, 1, 1)
