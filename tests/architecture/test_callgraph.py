import ast
from pathlib import Path

from tests.architecture.callgraph import (
    Definition,
    _class_target,
    _dynamic_reexports,
    _expression_type,
    _reexported_imports,
    build,
    orphan_diagnostics,
    reachable,
    resolve_attribute,
)
from tests.architecture.source_index import SOURCE_ROOT


def test_every_production_callable_is_reachable_from_a_runtime_root() -> None:
    by_name, edges, roots = build()

    assert any(root.path.is_relative_to(SOURCE_ROOT / "cli") for root in roots)
    assert not orphan_diagnostics(by_name, edges, roots)


def test_enum_property_and_pydantic_model_validators_follow_runtime_calls() -> None:
    by_name, edges, roots = build()
    reachable_symbols = {definition.symbol for definition in reachable(by_name, edges, roots)}

    assert "core.enums.ScoringStage.client_data_attr" in reachable_symbols
    assert "config.compose.ComposeRequest.preprocess" in reachable_symbols
    assert "config.compose.ComposeRequest.validate_scientific_constraints" in reachable_symbols


def test_orphan_mutation_reports_caller_and_root_path() -> None:
    root = Definition("cli", "command", 1, Path("cli.py"))
    orphan = Definition("services", "dead", 5, Path("services.py"))
    by_name = {root.name: [root], orphan.name: [orphan]}
    edges = {root: set(), orphan: set()}

    diagnostics = orphan_diagnostics(by_name, edges, [root])

    assert len(diagnostics) == 1
    assert "services.dead" in diagnostics[0]
    assert "direct callers=['none']" in diagnostics[0]
    assert "shortest CLI path=none" in diagnostics[0]


def test_helper_referenced_only_by_an_orphan_stays_orphaned() -> None:
    root = Definition("cli", "command", 1, Path("cli.py"))
    dead = Definition("services", "dead", 5, Path("services.py"))
    helper = Definition("services", "helper", 10, Path("services.py"))
    by_name = {item.name: [item] for item in (root, dead, helper)}
    edges = {root: set(), dead: {helper.name}, helper: set()}

    diagnostics = orphan_diagnostics(by_name, edges, [root])

    assert len(diagnostics) == 2
    assert any("services.helper" in item for item in diagnostics)


def test_local_import_is_part_of_the_workflow_path() -> None:
    by_name, edges, roots = build()
    cli_roots = [root for root in roots if root.path.is_relative_to(SOURCE_ROOT / "cli")]
    caller = by_name["experiments.stages.train_encoder._run_fl_training"][0]
    target = "federated.protocols.fedavg.run_fl_training"

    assert target in edges[caller]
    edges[caller].remove(target)

    assert any(
        "federated.protocols.fedavg.run_fl_training" in diagnostic
        for diagnostic in orphan_diagnostics(by_name, edges, cli_roots)
    )


def test_registered_typer_commands_are_cli_roots() -> None:
    _, _, roots = build()
    root_names = {(root.module, root.name) for root in roots}

    assert ("cli.commands", "status") in root_names
    assert ("cli.commands", "sweep") in root_names
    assert ("cli.audit", "reuse") in root_names


def test_flower_strategy_callbacks_depend_on_exact_external_base() -> None:
    by_name, edges, roots = build()
    cli_roots = [root for root in roots if root.path.is_relative_to(SOURCE_ROOT / "cli")]
    strategy = by_name["federated.strategies.DatpFedAvg"][0]
    callback = "federated.strategies.DatpFedAvg.aggregate_evaluate"

    assert callback in edges[strategy]
    edges[strategy].remove(callback)

    assert any(
        "DatpFedAvg.aggregate_evaluate" in diagnostic
        for diagnostic in orphan_diagnostics(by_name, edges, cli_roots)
    )


def test_optional_injected_dependency_stays_reachable_through_fallback() -> None:
    module = "experiments"
    imports = {"ScoreProvider": "scoring.loading.ScoreProvider"}
    class_names = {"scoring.loading.ScoreProvider"}
    provider_annotation = ast.parse("ScoreProvider | None", mode="eval").body
    provider_type = _class_target(provider_annotation, module, imports, class_names)

    assert provider_type == "scoring.loading.ScoreProvider"
    fallback = ast.parse("provider or ScoreProvider(root)", mode="eval").body
    assert (
        _expression_type(
            fallback,
            module,
            imports,
            class_names,
            {"provider": provider_type},
            {},
        )
        == provider_type
    )


def test_declared_public_reexports_resolve_to_the_original_callable() -> None:
    module = ast.parse(
        "from datp.attacks.metrics.mu_flag import compute_mu_flag_threshold\n"
        "__all__ = ['compute_mu_flag_threshold']\n"
    )

    assert _reexported_imports(module) == {
        "compute_mu_flag_threshold": "attacks.metrics.mu_flag.compute_mu_flag_threshold"
    }


def test_private_imports_are_not_treated_as_public_reexports() -> None:
    module = ast.parse(
        "from datp.attacks.metrics.mu_flag import compute_mu_flag_threshold\n"
        "__all__ = ['another_name']\n"
    )

    assert not _reexported_imports(module)


def test_dynamic_exports_follow_getattr_module_forwarding() -> None:
    module = ast.parse(
        "__all__ = ['compute_fpr', 'validate_metrics_payload']\n"
        "def __getattr__(name):\n"
        "    if name == 'validate_metrics_payload':\n"
        "        from datp.evaluation.artifact_validation import validate_metrics_payload\n"
        "        return validate_metrics_payload\n"
        "    if name in __all__:\n"
        "        from datp.evaluation import metrics as _m\n"
        "        return getattr(_m, name)\n"
    )

    assert _dynamic_reexports(module) == {
        "compute_fpr": "evaluation.metrics.compute_fpr",
        "validate_metrics_payload": "evaluation.artifact_validation.validate_metrics_payload",
    }


def test_local_class_method_call_resolves_from_class_name() -> None:
    call = ast.parse("ThresholdState.empty(policy)", mode="eval").body
    assert isinstance(call, ast.Call)
    assert isinstance(call.func, ast.Attribute)
    method = Definition(
        "synthetic",
        "empty",
        1,
        Path("synthetic.py"),
        "function",
        "synthetic.ThresholdState.empty",
    )
    class_definition = Definition(
        "synthetic",
        "ThresholdState",
        1,
        Path("synthetic.py"),
        "class",
        "synthetic.ThresholdState",
    )

    target = resolve_attribute(
        call.func,
        {},
        {"ThresholdState": [class_definition], "synthetic.ThresholdState.empty": [method]},
        {},
        {},
    )

    assert target == "synthetic.ThresholdState.empty"


def test_pydantic_validation_entry_resolves_to_model_class() -> None:
    call = ast.parse("ComposeRequest.model_validate(data)", mode="eval").body
    assert isinstance(call, ast.Call)
    assert isinstance(call.func, ast.Attribute)
    model = Definition(
        "synthetic", "ComposeRequest", 1, Path("synthetic.py"), "class", "synthetic.ComposeRequest"
    )

    target = resolve_attribute(
        call.func,
        {"ComposeRequest": "synthetic.ComposeRequest"},
        {"synthetic.ComposeRequest": [model]},
        {},
        {},
    )

    assert target == "synthetic.ComposeRequest"
