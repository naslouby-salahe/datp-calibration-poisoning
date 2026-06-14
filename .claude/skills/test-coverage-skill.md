# Test Coverage Skill

## Purpose

Use this skill to ensure DATP behavior is covered by clear, deterministic, maintainable tests.

Coverage is not only line coverage. Coverage must protect scientific behavior, artifact contracts, edge cases, and regressions.

## Required Test Categories

Depending on the changed behavior, cover:

1. Unit behavior.
2. Integration behavior.
3. Config validation.
4. Schema validation.
5. Enum behavior.
6. Constant usage.
7. Artifact path construction.
8. Dataset audit behavior.
9. Score manifest behavior.
10. Threshold behavior.
11. Metric behavior.
12. CLI behavior.
13. Script behavior.
14. Error handling.
15. Determinism.
16. Regression from previous diagnostics.

## Required Edge Cases

Consider:

1. Empty inputs.
2. Missing files.
3. Missing columns.
4. Invalid config.
5. Invalid baseline.
6. Invalid regime.
7. Invalid stage.
8. Invalid seed.
9. Missing alpha.
10. Calibration-pending clients.
11. No eligible clients.
12. Single eligible client.
13. All clients eligible.
14. Zero denominator cases.
15. Float tolerance cases.
16. Nonexistent artifacts.
17. Existing artifacts.
18. Partial artifact sets.
19. Corrupt manifests.
20. Unsupported dataset metadata.

## Test Quality Requirements

Tests must have:

1. Deterministic inputs.
2. Clear names.
3. Minimal setup.
4. Explicit assertions.
5. Domain-specific fixtures.
6. Temporary directories for filesystem behavior.
7. Approximate comparisons for floats.
8. No direct float equality.
9. No unused variables.
10. No unused imports.
11. No side-effect-free statements.
12. No duplicated fixtures.
13. No obsolete tests.
14. No assertion-only coverage padding.
15. No hidden global state.
16. No dependency on execution order.
17. No unseeded randomness.

## Float Assertion Rule

Use:

1. `pytest.approx` for scalar floats.
2. `numpy.testing.assert_allclose` for arrays.
3. `math.isclose` for helper-level scalar checks.
4. Domain-specific tolerance constants when required.

Never use direct equality for float semantic equality.

## Static-Analysis Rule For Tests

Tests are part of the quality gate.

Fix SonarLint, Pylance, CodeScene, Ruff, Pyright, or Pytest issues in tests. Do not ignore them because they are tests.

## Coverage Expansion Rule

When production code changes:

1. Add tests for new behavior.
2. Add regression tests for fixed bugs.
3. Adapt tests for refactored interfaces.
4. Delete tests for deleted dead code.
5. Merge duplicate tests.
6. Keep behavior coverage stable.
7. Avoid testing private implementation details unless required to protect a contract.

## Refactor-Aware Testing

When a complex method is split:

1. Keep public behavior tests.
2. Add helper tests only if the helper has nontrivial domain behavior.
3. Do not overfit tests to extraction structure.
4. Use typed objects in tests when production uses typed objects.
5. Remove obsolete mocks.

## Required Commands

Discover actual commands from project configuration.

Prefer:

1. Targeted tests first.
2. Related integration tests second.
3. Full relevant suite third.
4. Coverage only after behavior tests pass.
5. Type/static checks when tests or interfaces change.

## Canonical Coverage Command

Coverage XML must land at `coverage.xml` (repo root) so SonarQube can consume it via `sonar.python.coverage.reportPaths=coverage.xml`. The canonical invocation:

```
.venv/bin/pytest --cov=src/datp --cov-report=xml:coverage.xml --cov-report=term-missing
```

Or via the full audit which also runs this step:

```
make quality-audit-local
```

Do not move the coverage report path without also updating `sonar-project.properties`.

## Required Report

Report:

1. Test files inspected.
2. Test files changed.
3. Tests added.
4. Tests updated.
5. Tests deleted.
6. Edge cases covered.
7. Coverage gaps closed.
8. Commands run.
9. Failures found.
10. Failures fixed.
11. Remaining coverage risks.