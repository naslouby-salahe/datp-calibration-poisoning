import ast

from tests.architecture.source_index import SOURCE_ROOT, scan_production_sources


def _cli_lifecycle_events(node: ast.AST) -> set[str]:
    return {
        call.args[0].value
        for call in ast.walk(node)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr in {"info", "error", "exception"}
        and call.args
        and isinstance(call.args[0], ast.Constant)
        and isinstance(call.args[0].value, str)
    }


def _contains_builtin_print(tree: ast.AST) -> bool:
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
        for node in ast.walk(tree)
    )


def _structured_log_events(node: ast.AST) -> set[str]:
    return {
        call.args[0].value
        for call in ast.walk(node)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "logger"
        and call.func.attr in {"info", "warning", "error", "exception"}
        and call.args
        and isinstance(call.args[0], ast.Constant)
        and isinstance(call.args[0].value, str)
    }


def _function(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.name == name
    )


def test_cli_entry_has_structured_lifecycle_logging() -> None:
    tree = scan_production_sources()[SOURCE_ROOT / "cli" / "__init__.py"]
    command = _function(tree, "cli_entry")
    events = _cli_lifecycle_events(command)

    assert "CLI invocation started" in events
    assert "CLI invocation completed" in events
    assert "CLI invocation failed" in events


def test_long_running_poisoning_workflows_log_lifecycle_and_failures() -> None:
    sources = scan_production_sources()
    workflows = (
        (
            SOURCE_ROOT / "attacks" / "execution" / "bounded_sweep_run.py",
            "run_nbaiot_main",
            "bounded sweep started",
            "bounded sweep completed",
            "bounded sweep cell execution failed",
        ),
        (
            SOURCE_ROOT / "attacks" / "execution" / "sensitivity_run.py",
            "run_sensitivity",
            "sensitivity analysis started",
            "sensitivity analysis completed",
            "sensitivity analysis task execution failed",
        ),
    )
    for path, name, started, completed, failed in workflows:
        events = _structured_log_events(_function(sources[path], name))
        assert started in events, f"{path}:{name} is missing start logging"
        assert completed in events, f"{path}:{name} is missing completion logging"
        assert failed in events, f"{path}:{name} is missing failure logging"


def test_production_has_no_builtin_print_calls() -> None:
    violations = [
        f"{path.relative_to(SOURCE_ROOT)}:{node.lineno}"
        for path, tree in scan_production_sources().items()
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
    ]

    assert not violations, violations


def test_logging_mutations_fail_and_pure_helper_is_not_required_to_log() -> None:
    unlogged_command = ast.parse("def command():\n    run_workflow()\n")
    logged_command = ast.parse(
        "def command():\n"
        "    logger.info('CLI invocation started')\n"
        "    run_workflow()\n"
        "    logger.info('CLI invocation completed')\n"
    )
    pure_helper = ast.parse("def percentile(values):\n    return sorted(values)[0]\n")
    unlogged_workflow = ast.parse("def run_sweep():\n    execute_cells()\n")
    logged_workflow = ast.parse(
        "def run_sweep():\n"
        "    logger.info('sweep started')\n"
        "    execute_cells()\n"
        "    logger.info('sweep completed')\n"
    )
    def command(tree: ast.Module) -> ast.stmt:
        return tree.body[0]

    assert not _cli_lifecycle_events(command(unlogged_command))
    assert _cli_lifecycle_events(command(logged_command)) == {
        "CLI invocation started",
        "CLI invocation completed",
    }
    assert not _cli_lifecycle_events(command(pure_helper))
    assert not _structured_log_events(_function(unlogged_workflow, "run_sweep"))
    assert _structured_log_events(_function(logged_workflow, "run_sweep")) == {
        "sweep started",
        "sweep completed",
    }


def test_builtin_print_mutation_is_detected() -> None:
    assert _contains_builtin_print(ast.parse("def command():\n    print('started')\n"))
    assert not _contains_builtin_print(
        ast.parse("def command():\n    console.print('started')\n")
    )
