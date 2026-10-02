import ast
from collections import Counter
import io
from pathlib import Path
import re
import tokenize

from tests.architecture.source_index import SOURCE_ROOT, scan_production_sources


_SCALAR_CONSTRUCTORS = {"int", "float", "str", "bool"}
_SUPPRESSION = re.compile(r"#\s*(?:type:\s*ignore|noqa|pyright:\s*ignore)", re.IGNORECASE)
_CAST_BOUNDARIES = Counter(
    {
        ("config/attack_config.py", "validate_fractions", "Sequence[object]"): 1,
        ("config/attack_config.py", "ClusterConfig", "Literal[3]"): 1,
        ("config/attack_config.py", "ClusterConfig", "Literal[42]"): 1,
        ("reporting/figures.py", "_save_figs", "_Figure"): 1,
        ("reporting/figures.py", "generate_figure1", "_Axes"): 1,
        ("reporting/figures.py", "generate_figure2", "_Axes"): 1,
        ("reporting/figures.py", "generate_figure3", "_Axes"): 1,
        ("reporting/figures.py", "generate_figure5", "_Axes"): 2,
        ("reporting/figures.py", "generate_figure6", "_Axes"): 1,
        ("core/seeds.py", "set_seeds", "_TorchSeedApi"): 1,
        ("core/tracking.py", "_import_mlflow", "_MlflowModule"): 1,
        ("validation/metric_reproducer.py", "_validate_json_value", "list[object]"): 1,
        ("validation/metric_reproducer.py", "_validate_json_value", "dict[object, object]"): 1,
        ("validation/metric_reproducer.py", "_validate_json_value", "dict[str, object]"): 1,
        ("federated/parameters.py", "set_parameters", "_TorchArrayFactory"): 1,
        ("federated/simulation.py", "_run_flower_simulation", "BackendConfig"): 1,
        ("federated/local_training.py", "train_local", "_Optimizer"): 1,
        ("federated/local_training.py", "train_local", "_Loss"): 1,
        ("attacks/execution/sensitivity_run.py", "run_sensitivity", "Sequence[_SensitivityTaskResult]"): 1,
    }
)
_SCALAR_BOUNDARIES = Counter(
    {
        ("core/tracking.py", "log_metrics", "str", "prefix"): 1,
        ("core/tracking.py", "_finite_metric_value", "float", "value"): 1,
        ("core/tracking.py", "log_artifact", "str", "artifact_path"): 1,
        ("federated/runtime.py", "ensure_ray_memory_threshold", "str", "threshold"): 1,
        ("experiments/console.py", "print_dry_run_summary", "str", "total_cells"): 1,
        ("validation/metric_reproducer.py", "_optional_score", "float", "value"): 1,
    }
)


def _domain_type_names() -> set[str]:
    canonical_types = ast.parse((SOURCE_ROOT / "types.py").read_text(encoding="utf-8"))
    names = {
        target.id
        for node in canonical_types.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    names.update(
        node.target.id
        for node in canonical_types.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    )
    for tree in scan_production_sources().values():
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and any(
                (isinstance(base, ast.Name) and base.id in {"Enum", "StrEnum", "IntEnum", "Flag", "IntFlag"})
                or (isinstance(base, ast.Attribute) and base.attr in {"Enum", "StrEnum", "IntEnum", "Flag", "IntFlag"})
                for base in node.bases
            ):
                names.add(node.name)
    return names


def _domain_parameter_conversions(
    path: Path, tree: ast.Module, domain_names: set[str]
) -> Counter[tuple[str, str, str, str]]:
    relative = (
        path.relative_to(SOURCE_ROOT).as_posix()
        if path.is_relative_to(SOURCE_ROOT)
        else path.as_posix()
    )
    violations: Counter[tuple[str, str, str, str]] = Counter()
    for function in ast.walk(tree):
        if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        parameters = (
            *function.args.posonlyargs,
            *function.args.args,
            *function.args.kwonlyargs,
        )
        domain_parameters = {
            parameter.arg
            for parameter in parameters
            if parameter.annotation
            and any(
                (isinstance(node, ast.Name) and node.id in domain_names)
                or (isinstance(node, ast.Attribute) and node.attr in domain_names)
                for node in ast.walk(parameter.annotation)
            )
        }
        for call in ast.walk(function):
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id in _SCALAR_CONSTRUCTORS
                and call.args
                and isinstance(call.args[0], ast.Name)
                and call.args[0].id in domain_parameters
            ):
                violations[(relative, function.name, call.func.id, call.args[0].id)] += 1
    return violations


def _cast_target(call: ast.Call, tree: ast.Module) -> str | None:
    if not call.args:
        return None
    if isinstance(call.func, ast.Name) and call.func.id == "cast":
        return ast.unparse(call.args[0])
    if not isinstance(call.func, ast.Attribute) or call.func.attr != "cast":
        return None
    if isinstance(call.func.value, ast.Name) and call.func.value.id in {
        alias.asname or alias.name.split(".")[0]
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
        if alias.name in {"typing", "typing_extensions"}
    }:
        return ast.unparse(call.args[0])
    return None


def _cast_sites(path: Path, tree: ast.Module) -> Counter[tuple[str, str, str]]:
    relative = (
        path.relative_to(SOURCE_ROOT).as_posix()
        if path.is_relative_to(SOURCE_ROOT)
        else path.as_posix()
    )
    sites: Counter[tuple[str, str, str]] = Counter()
    parents = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    for call in ast.walk(tree):
        if not isinstance(call, ast.Call):
            continue
        imported_casts = {
            alias.asname or alias.name
            for node in tree.body
            if isinstance(node, ast.ImportFrom)
            and node.module in {"typing", "typing_extensions"}
            for alias in node.names
            if alias.name == "cast"
        }
        direct_cast = isinstance(call.func, ast.Name) and call.func.id in imported_casts
        target = ast.unparse(call.args[0]) if direct_cast and call.args else _cast_target(call, tree)
        if target is None:
            continue
        owner: ast.AST | None = call
        while owner is not None and not isinstance(
            owner, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        ):
            owner = parents.get(owner)
        if owner is not None and target is not None:
            sites[(relative, owner.name, target)] += 1
    return sites


def _suppression_comments(source: str) -> list[str]:
    return [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type == tokenize.COMMENT and _SUPPRESSION.search(token.string)
    ]


def test_domain_values_are_not_implicitly_converted_inside_project_functions() -> None:
    domain_names = _domain_type_names()
    actual = Counter(
        site
        for path, tree in scan_production_sources().items()
        for site, count in _domain_parameter_conversions(path, tree, domain_names).items()
        for _ in range(count)
    )
    assert actual == _SCALAR_BOUNDARIES


def test_scalar_conversion_mutations_fail_and_external_path_controls_pass() -> None:
    invalid = ast.parse(
        "from datp.types import RandomSeed\n"
        "def run(seed: RandomSeed):\n"
        "    consume(int(seed))\n"
    )
    external_boundary = ast.parse(
        "from pathlib import Path\n"
        "def write(path: Path):\n"
        "    filesystem_api(str(path))\n"
    )
    random_seed = next(
        node
        for node in invalid.body
        if isinstance(node, ast.FunctionDef)
    )
    write = next(
        node
        for node in external_boundary.body
        if isinstance(node, ast.FunctionDef)
    )
    assert _domain_parameter_conversions(Path("synthetic.py"), invalid, {"RandomSeed"})
    assert not _domain_parameter_conversions(Path("synthetic.py"), external_boundary, {"RandomSeed"})
    assert random_seed.name == "run" and write.name == "write"


def test_cast_calls_are_exact_reviewed_boundary_sites() -> None:
    actual = Counter(
        site
        for path, tree in scan_production_sources().items()
        for site, count in _cast_sites(path, tree).items()
        for _ in range(count)
    )
    assert actual == _CAST_BOUNDARIES


def test_cast_mutation_and_suppression_escapes_are_detected() -> None:
    mutation = ast.parse(
        "from typing import cast as static_cast\n"
        "def run(seed: RandomSeed):\n"
        "    return static_cast(int, seed)\n"
    )
    assert _cast_sites(Path("synthetic.py"), mutation)
    assert _suppression_comments("# type: ignore[arg-type]\nvalue = 1")
    assert _suppression_comments("value = 1  # noqa: F401")
    assert _suppression_comments("value = 1  # pyright: ignore\n")
    assert not _suppression_comments("value = '# type: ignore'\n")


def test_production_has_no_type_suppression_comments() -> None:
    violations = [
        f"{path.relative_to(SOURCE_ROOT)}: {comment}"
        for path in SOURCE_ROOT.rglob("*.py")
        for comment in _suppression_comments(path.read_text(encoding="utf-8"))
    ]
    assert not violations, violations
