import ast
import io
import tokenize
from pathlib import Path

from tests.architecture.callgraph import build
from tests.architecture.source_index import SOURCE_ROOT, scan_production_sources


SCIENTIFIC_DOCSTRINGS = {
    (Path("attacks/metrics/mu_flag.py"), "compute_mu_flag_threshold")
}
REQUIRED_COMMENTS = {
    (
        Path("core/seeds.py"),
        "# Ensure deterministic cuBLAS operations by fixing the workspace size.",
    ),
    (
        Path("statistics/constants.py"),
        "# Cliff's delta magnitude boundaries (Romano et al., 2006).",
    ),
    (
        Path("attacks/constants.py"),
        "# At least 8/10 seed aggregates in expected direction",
    ),
}


def _docstring_nodes(
    tree: ast.Module,
) -> list[ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
        and ast.get_docstring(node, clean=False) is not None
    ]


def _comment_texts(source: str) -> list[str]:
    return [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type == tokenize.COMMENT
    ]


def _docstring_violations(
    path: Path,
    tree: ast.Module,
    cli_roots: set[tuple[Path, str]],
) -> list[str]:
    relative = path.relative_to(SOURCE_ROOT)
    violations = []
    for node in _docstring_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
            relative, node.name
        ) in cli_roots:
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
            relative, node.name
        ) in SCIENTIFIC_DOCSTRINGS:
            continue
        symbol = getattr(node, "name", "<module>")
        violations.append(f"{relative}:{node.lineno} unnecessary docstring on {symbol}")
    return violations


def test_production_comments_and_docstrings_are_justified() -> None:
    _, _, roots = build()
    cli_roots = {
        (root.path.relative_to(SOURCE_ROOT), root.name)
        for root in roots
        if root.module.startswith("cli") and root.kind == "function"
    }
    sources = scan_production_sources()
    docstrings = [
        violation
        for path, tree in sources.items()
        for violation in _docstring_violations(path, tree, cli_roots)
    ]
    comments = {
        (path.relative_to(SOURCE_ROOT), text)
        for path, tree in sources.items()
        for text in _comment_texts(path.read_text(encoding="utf-8"))
    }
    assert not docstrings, docstrings
    assert comments == REQUIRED_COMMENTS


def test_hygiene_scanner_rejects_narrative_docstrings_and_comments() -> None:
    source = "# obvious narration\ndef run():\n    \"\"\"Runs the operation.\"\"\"\n    return 1\n"
    tree = ast.parse(source)
    assert _docstring_violations(SOURCE_ROOT / "run.py", tree, set())
    assert _comment_texts(source) == ["# obvious narration"]


def test_cli_help_and_scientific_rationale_are_valid_controls() -> None:
    tree = ast.parse('def command():\n    """Build the report for the selected run."""\n    return None\n')
    command = next(node for node in tree.body if isinstance(node, ast.FunctionDef))
    assert not _docstring_violations(
        SOURCE_ROOT / "cli" / "report.py",
        tree,
        {(Path("cli/report.py"), command.name)},
    )
    scientific = ast.parse(
        'def compute_mu_flag_threshold():\n    """The fixed scientific gate divides CV(FPR) by its protocol divisor."""\n'
    )
    assert not _docstring_violations(
        SOURCE_ROOT / "attacks/metrics/mu_flag.py", scientific, set()
    )
