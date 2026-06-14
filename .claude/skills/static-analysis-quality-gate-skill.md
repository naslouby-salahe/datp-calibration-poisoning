# Static Analysis Quality Gate Skill

## Purpose

This skill defines the static-analysis and clean-code gate for DATP.

Use this skill after every implementation, repair, refactor, ticket audit, and ticket completion check.

## Non-Negotiable Rule

No ticket, repair, or refactor is complete while any blocking diagnostic remains in the affected code surface.

The affected code surface includes changed files and related existing files.

---

## Tool existence rule

Before using Vulture, Refurb, or Semgrep, check whether they exist:

```bash
uv run vulture --version || vulture --version || true
uv run refurb --version || refurb --version || true
uv run semgrep --version || semgrep --version || true
```

If missing, install them:

```bash
uv add --dev vulture refurb semgrep
```

Verify after installation:

```bash
uv run vulture --version
uv run refurb --version
uv run semgrep --version
```

Record the result in the relevant ticket progress entry or audit report.

Do not claim a tool is available or clean unless it actually ran.

---

## Canonical Commands

Use the cheapest reliable checks first.

| Tool | Command | Default status |
|---|---|---|
| Git status | `git status --short` | Required |
| Ruff lint | `python -m ruff check src/datp tests` | Required after code/test changes |
| Pyright | `python -m pyright` | Required after type/import/interface changes |
| Impacted pytest | `python -m pytest <impacted-test-paths>` | Required after behavior changes |
| CodeScene delta | `make codescene-check` or `cs delta` / `cs review` | Optional/useful |
| Vulture | `uv run vulture src/datp tests --min-confidence 80` | Optional/useful |
| Refurb | `uv run refurb src/datp tests` | Optional/useful |
| Semgrep | `uv run semgrep scan --config auto src/datp tests` | Optional/useful |
| SonarQube lifecycle | `make sonar-up` / `make sonar-health` / `make sonar-down` | Optional final only |
| Full local audit | `make quality-audit-local` | Optional final only if local Sonar is healthy |

Coverage XML must land at `coverage.xml` when coverage is run. `sonar-project.properties` reads from `sonar.python.coverage.reportPaths=coverage.xml`.

Secrets (`SONAR_TOKEN`, `CS_ACCESS_TOKEN`) live only in `.env.local`. `scripts/quality/load_env.sh` sources them. Never echo or log token values.

---

## Sonar reliability rule

Local Sonar has been unreliable in this environment.

Do not make Sonar mandatory for routine work.

Do not claim Sonar passed unless it actually ran successfully.

If Sonar fails for environment reasons, record:

```text
command
failure
environment limitation
fallback checks used
```

Fallback checks are:

```text
Ruff
Pyright
targeted pytest
CodeScene when useful
Vulture when useful
Refurb when useful
Semgrep when useful
source inspection
scientific-contract audit
```

Manual review is not a substitute for a successful Sonar run, and a failed Sonar run must not be described as passed.

---

## Blocking Diagnostic Sources

Treat these as blocking when they affect production code, tests, scripts, configs, or documentation-generated code:

1. Pylance.
2. Pyright.
3. CodeScene when the finding applies to the affected surface and is valid.
4. Ruff.
5. Flake8 if configured.
6. Pylint if configured.
7. MyPy if configured.
8. Pytest.
9. Coverage when coverage is part of the required scope.
10. Semgrep when the finding is valid and relevant.
11. Vulture when the finding is verified as real dead code.
12. Refurb only when the suggestion exposes a clear readability/modernization issue worth changing.
13. Sonar only when it actually ran successfully and produced valid findings.
14. Project-specific invariant checks.

If a configured tool cannot be run, perform a source-level audit and record the tool as unavailable or environmentally blocked.

Do not claim a clean automated pass for a tool that did not run.

---

## Required Static Rules

The affected surface must have:

1. No unresolved call signature errors.
2. No missing required arguments.
3. No invalid keyword arguments.
4. No unused imports.
5. No unused variables.
6. No unused local assignments.
7. No unreachable code.
8. No side-effect-free statements.
9. No direct equality checks on floats.
10. No duplicated literals that should be constants.
11. No duplicated code blocks.
12. No needless nested conditional expressions.
13. No cognitive complexity above the configured threshold.
14. No large methods where extraction is reasonable.
15. No deep nesting where guard clauses or helpers are possible.
16. No long argument lists where typed objects are appropriate.
17. No vague names.
18. No dead compatibility wrappers.
19. No hardcoded scientific parameters.
20. No hardcoded artifact path fragments.
21. No hardcoded metric keys.
22. No repeated baseline, regime, stage, status, or artifact type strings.
23. No scattered configs.
24. No scattered constants.
25. No scattered enums.
26. No scattered schemas.
27. No generic dumping-ground utility modules.
28. No misplaced scripts.
29. No silently introduced defaults in input/config models.
30. No blanket diagnostic suppressions.

---

## Optional tool interpretation

### Vulture

Vulture identifies dead-code suspects.

Before deleting anything, verify with:

```text
rg
imports
tests
CLI entry points
scripts
configs
docs
tickets
architecture notes
```

Vulture false positives must be recorded, not blindly fixed.

### Refurb

Refurb suggestions are optional.

Apply only when they improve clarity, readability, maintainability, or idiomatic Python without changing behavior.

Reject suggestions that introduce cleverness or reduce scientific traceability.

### Semgrep

Semgrep findings must be triaged.

Security findings are blocking only when valid and relevant to the affected surface.

Semgrep does not replace tests or scientific-contract checks.

---

## Input and Config Default Rule

Input and config models must not use default values unless all conditions are true:

1. The default is scientifically or operationally required.
2. The default is centralized.
3. The default is documented.
4. The default is tested.
5. The default does not hide missing user intent.
6. The default does not change experimental meaning.
7. The default does not bypass validation.

If any condition is not true, the field must be required.

---

## Float Comparison Rule

Never compare floats directly using equality or inequality for semantic equality.

Use:

1. `math.isclose` for scalar floats.
2. `pytest.approx` in tests.
3. `numpy.isclose` or `numpy.allclose` for NumPy arrays.
4. Domain-specific tolerance constants where needed.

Tolerance values must be named and justified when they are not standard.

---

## Complexity Rule

When a method violates complexity:

1. Extract domain-named helpers.
2. Replace nested conditionals with guard clauses.
3. Replace branching strings with enums.
4. Replace repeated decision tables with typed maps.
5. Replace long argument lists with typed parameter objects.
6. Split I/O, parsing, computation, validation, and reporting.
7. Keep each helper testable.
8. Do not hide complexity by moving the same tangled logic elsewhere.

---

## Literal Ownership Rule

Repeated literals must be centralized according to meaning:

1. Logger names belong near the owning module or logging constants.
2. CLI option names and help text belong in CLI constants or typed CLI option definitions.
3. Artifact filenames belong in artifact constants.
4. Directory names belong in artifact directory/path modules.
5. Metric keys belong in metric key modules.
6. Baseline names belong in baseline enums.
7. Regime names belong in regime enums.
8. Stage names belong in stage enums.
9. Status names belong in status enums.
10. Scientific values belong in config.

---

## Object Boundary Rule

Do not pass many unrelated primitive arguments through the system.

Use typed objects when a function needs a coherent concept such as:

1. Run identity.
2. Dataset identity.
3. Baseline identity.
4. Threshold evaluation request.
5. Analysis request.
6. Plot request.
7. Report request.
8. Artifact location.
9. Metric bundle.
10. Audit result.
11. Validation result.

---

## Test Quality Rule

Tests must also pass the gate.

Tests must not contain:

1. Direct float equality.
2. Unused variables.
3. Unused imports.
4. Side-effect-free statements.
5. Duplicated fixtures.
6. Overly dense setup.
7. Obsolete assertions.
8. Assertions that only test implementation details.
9. Randomness without fixed seed.
10. Hidden filesystem coupling.
11. Unclear test names.
12. Missing edge-case coverage for changed behavior.

---

## Required Audit Output

Every use of this skill must produce:

1. Diagnostics reviewed.
2. Tool existence checks.
3. Tools installed, if any.
4. Root causes identified.
5. Files fixed.
6. Files intentionally not changed.
7. Checks run.
8. Checks not run and why.
9. Vulture findings triaged, if run.
10. Refurb findings triaged, if run.
11. Semgrep findings triaged, if run.
12. Remaining issues.
13. Final verdict.
