# /CleanCode — Safe Non-Committing Code Quality Pass

Perform a thorough code quality inspection and safe cleanup of the repository.
Do **not** commit. Do **not** push. Stop before any change that requires a
scientific or protocol decision.

---

## Step 0 — Environment and repository state

**Working directory:** `/home/naslouby/Projects/datp-calibration-poisoning`

Load `.env.local` safely. Real environment variables override `.env.local` values.

```bash
set -a
source .env.local 2>/dev/null || true
set +a
```

**Token rules:**
- Never print `SONARQUBE_TOKEN`, `CS_ACCESS_TOKEN`, or any token-like value.
- Never copy token values to another file.
- Redact all token-like values in logs and the final report (show only first 4 characters followed by `****`).
- Never commit `.env.local`.
- If `.env.local` is not listed in `.gitignore`, add it before doing anything else.

Print:
- Current branch: `git rev-parse --abbrev-ref HEAD`
- Current commit SHA: `git rev-parse HEAD`
- Working tree snapshot: `git status --short`

Classify the working tree into:
- **Staged** changes
- **Unstaged modified** files
- **Untracked** files

Do **not** touch untracked files that are unrelated to code quality.

---

## Step 1 — Local automated checks

Run each check below in sequence. For each check, record: **PASS**, **FAIL**, or
**SKIPPED** (with reason).

### 1.1 — Formatting

```bash
python -m ruff format src/ tests/
```

### 1.2 — Linting

```bash
python -m ruff check --fix src/ tests/
```

### 1.3 — Static typing (Pyright / Pylance)

```bash
python -m pyright src/ 2>&1 || pyright src/ 2>&1
```

Treat Pylance diagnostics through Pyright. Record the error/warning count.

### 1.4 — Mypy (if configured)

```bash
python -m mypy src/ 2>&1 || echo "SKIPPED: mypy not configured"
```

### 1.5 — Tests

```bash
python -m pytest tests/ -x -q 2>&1
```

### 1.6 — Coverage

```bash
python -m pytest --cov=src --cov-report=xml:coverage.xml -q 2>&1
```

### 1.7 — Security

```bash
python -m bandit -r src/ -q 2>&1 || echo "SKIPPED: bandit not available"
```

### 1.8 — Pylint (if configured)

```bash
python -m pylint src/ 2>&1 || echo "SKIPPED: pylint not configured"
```

### 1.9 — Semgrep (if configured)

```bash
semgrep scan --config auto src/ 2>&1 || echo "SKIPPED: semgrep not configured"
```

---

## Step 2 — SonarCloud query (direct API, no sonar-scanner)

**Forbidden:** `sonar-scanner`. **Forbidden:** `sonar-project.properties`.

Use the SonarCloud REST API directly via `curl` or similar shell commands.

Credentials:
- `SONAR_HOST_URL` (default: `https://sonarcloud.io`)
- `SONAR_PROJECT_KEY` (default: `naslouby-salahe_datp-calibration-poisoning`)
- `SONAR_ORGANIZATION` (default: `naslouby-salahe`)
- `SONARQUBE_TOKEN` — use as Basic auth username with empty password

If `SONARQUBE_TOKEN` is missing or empty: skip all SonarCloud queries, note
"SonarCloud: SKIPPED — token missing", and continue with local checks only.

**Never print the curl command with the token expanded.**
Use a shell variable reference only: `-u "$SONARQUBE_TOKEN:"`.

### 2.1 — Quality gate status

```
GET $SONAR_HOST_URL/api/qualitygates/project_status
  ?projectKey=$SONAR_PROJECT_KEY
  &branch=<current branch>
```

Record: `OK`, `WARN`, `ERROR`, `NONE`, or `UNKNOWN`.

If the API returns a 401: record "auth failure — check SONARQUBE_TOKEN".
If the API returns a 404: record "project not found — check SONAR_PROJECT_KEY".
If the response contains no `analysisId`: record "no analysis found — SonarCloud may not have run yet".

### 2.2 — Open issues with pagination

```
GET $SONAR_HOST_URL/api/issues/search
  ?componentKeys=$SONAR_PROJECT_KEY
  &branch=<current branch>
  &resolved=false
  &ps=100
  &p=<page>
```

Fetch all pages until `total` is exhausted. Record total issue count and the
list of issues (key, severity, type, rule, file, line, message).

If branch issues are unavailable (e.g. branch analysis not configured), fall
back to default branch query without the `&branch=` parameter and note that
branch specificity could not be confirmed.

### 2.3 — Analysis metadata

```
GET $SONAR_HOST_URL/api/project_analyses/search
  ?project=$SONAR_PROJECT_KEY
  &ps=1
```

Record the most recent analysis date. If the most recent analysis predates the
current commit by more than 1 hour, state: "Analysis freshness: UNKNOWN —
SonarCloud may not reflect the current commit."

### 2.4 — Distinguish these states clearly

- `MISSING_TOKEN` — skip gracefully
- `AUTH_FAILURE` — report, do not retry
- `NETWORK_FAILURE` — report, continue with local results
- `PROJECT_NOT_FOUND` — report, do not retry
- `NO_ANALYSIS` — report clearly
- `ANALYSIS_STALE` — report with date delta
- `ZERO_ISSUES` — report as clean
- `OPEN_ISSUES` — list all, categorize below

### 2.5 — CS_ACCESS_TOKEN

If `CS_ACCESS_TOKEN` is set: note that it is present but do not fabricate an
endpoint. If this repository defines a CS integration, follow that definition.
If no CS integration is defined in the repository, state: "CS: SKIPPED — no
repo-defined CS integration found."

---

## Step 3 — Manual code inspection

Inspect the following directly. Do not rely solely on automated tools for this
section. Read the relevant source files and reason about them.

### 3.1 — Dead and unreachable code

- Functions, classes, or methods that are defined but never called or imported
- Variables assigned but never read
- Branches guarded by conditions that can never be true
- `return` statements before all reachable code
- Code after an unconditional `return`, `raise`, `break`, or `continue`

### 3.2 — Unused parameters and locals

- Function parameters that are never used inside the function body
- Local variables assigned once and never read
- Loop variables that are never used (prefer `_` naming)

### 3.3 — Unused private symbols

- Private functions (`_foo`) defined but never called within the module
- Private classes defined but never instantiated or referenced

### 3.4 — Exception hygiene

- Bare `except:` clauses — must be `except SpecificException`
- Overbroad `except Exception:` that silently swallows errors
- `except` blocks that `pass` or log and continue without re-raising when the
  error is not genuinely recoverable
- `except` blocks that catch and discard diagnostic information

### 3.5 — Production print statements

- `print()` calls outside of CLI entry points, report writers, or test helpers
- Logging calls that print secrets, tokens, full paths, or raw data

### 3.6 — Type annotation discipline

- `Any` usage that is not justified with a comment
- `dict[str, Any]` used where a typed dataclass or TypedDict is clearly better
- Missing return type annotations on public API functions
- Missing parameter type annotations on public API functions
- `Enum | str`, `Path | str`, `SomeDataclass | dict`, `SomeDataclass | str`
  union types in non-boundary function signatures (forbidden in production code;
  only the true external boundary — CLI parsing, Hydra YAML loading, JSON
  deserialization — may accept raw strings and coerce them to typed values)
- Backwards-compatibility helpers that accept weak types and coerce internally
  (e.g. `path = Path(path)` after `path: Path | str`); remove both the union
  and the coercion — callers must pass the correct type
- Runtime validators that duplicate static type enforcement already caught by
  pyright — prefer static typing over runtime guards where pyright is the
  enforcement mechanism

### 3.7 — Hardcoding

Detect inappropriate hardcoding. Apply judgment — see classification below.

**Scan for raw occurrences of:**
- Dataset names (e.g. `"nbaiot"`, `"ciciot"`, `"N-BaIoT"`)
- Threshold policy names (e.g. `"B1"`, `"B2"`, `"B4"`, `"global"`)
- Baseline names
- Metric names (e.g. `"fpr"`, `"auroc"`, `"cv_fpr"`)
- Attack objectives (e.g. `"THRESHOLD_RAISE"`, `"THRESHOLD_LOWER"`)
- Source strategies (e.g. `"RANDOM_BENIGN"`, `"HIGH_SCORE_BENIGN"`)
- Regime names (e.g. `"REGIME_A"`, `"REGIME_B"`)
- Split names (e.g. `"train"`, `"calibration"`, `"test"`)
- Seed lists or seed values outside canonical seed modules
- Output root paths
- Artifact directory fragments
- Protocol labels
- Stage names: `"smoke"`, `"mvp"`, `"full"`, `"stretch"`, `"bounded"`
- Magic numeric thresholds
- Repeated string literals used as identifiers (not messages)
- Repeated path fragments

**Classify each occurrence as one of:**
- `CENTRALIZE` — same meaning, same value repeated; move to a domain constant
- `ENUM` — closed vocabulary; wrap in an existing or new enum
- `CONFIG_CONSTANT` — protocol-locked scientific value; move to canonical config
- `ARTIFACT_LAYOUT` — repeated path fragment; move to path/artifact layout module
- `ALLOWED_BOUNDARY` — serialization, CLI parsing, manifest output; leave as-is
- `ALLOWED_FIXTURE` — test fixture value; leave as-is
- `ALLOWED_MESSAGE` — human-readable string; leave as-is
- `DIFFERENT_SEMANTICS` — same value but different meaning; keep separate, rename for clarity

Do not blindly replace every string or number. Apply judgment.

### 3.8 — Enum discipline

Closed vocabularies must use enums or existing canonical enum types. Scan for:

Likely enum concepts:
`DatasetID`, `ThresholdPolicy`, `Baseline`, `AttackObjective`, `SourceStrategy`,
`TargetScope`, `MetricName`, `ExperimentRegime`, `SplitKind`, `ArtifactKind`,
`RunMode`, `DefenseStrategy`, `AggregationPolicy`, `SeedRole`,
`CheckStatus`, `FindingSeverity`, `IssueSource`

Rules:
- Parse strings into enums at system/API/CLI/file boundaries
- Compare enums inside core logic; use `.value` only at serialization, CLI,
  report, manifest, and path-rendering boundaries
- Do not duplicate enum mappings manually
- Do not create a giant unrelated enum file; put enums near their owning domain

### 3.9 — Dataclass and dict discipline

Stable domain structures must use typed dataclasses or typed config models.

**Prefer `@dataclass(frozen=True, slots=True)`** for: config, spec, manifest,
record, result, plan objects — unless mutation is necessary and justified.

Candidates to check:
`AttackConfig`, `PoisoningPlan`, `VictimPlan`, `SeedSequenceSpec`,
`ThresholdResult`, `MetricRecord`, `ArtifactLayout`, `RunManifest`,
`DatasetSpec`, `PolicyEvaluation`, `B4ClusterSpec`, `ExperimentCell`,
`AuditFinding`, `GovernanceRule`, `SonarIssue`, `QualityRunResult`

Classify each dict usage:
- `DATACLASS` — stable domain object crossing module boundaries; convert
- `ALLOWED_LOCAL` — temporary local dict; leave as-is
- `ALLOWED_BOUNDARY` — JSON serialization payload at boundary; leave as-is
- `ALLOWED_FIXTURE` — test parametrization dict; leave as-is
- `DYNAMIC_METADATA` — sparse, optional, unstructured metadata; may remain mapping
- `TYPED_DICT` — acceptable for external JSON-like shapes

Do not blindly convert every dict.

### 3.10 — Duplicate constants and repeated values

Classify every repeated value:
- `CENTRALIZE` — same semantic meaning, same value → move to one constant
- `KEEP_SEPARATE` — same value but different meaning → keep, rename for clarity
- `ENUM` — domain vocabulary string → wrap in enum
- `CONFIG_CONSTANT` — protocol-locked numeric/string → move to canonical config
- `PATH_LAYOUT` — repeated path fragment → layout helper
- `ALLOWED_TEST` — repeated in tests → acceptable
- `ALLOWED_MESSAGE` — repeated in user messages → acceptable

Do not create a giant dumping-ground constants file. Constants belong near their
owning domain.

### 3.11 — Architecture boundaries

Check and flag violations:

- Core must not import CLI modules
- Core must not import test modules
- Generic runtime modules must not import experiment runners
- Metrics must not depend on CLI
- Artifact layout must not depend on attack execution
- Serialization/reporting may depend on enums/dataclasses; core logic must not
  depend on report writers
- Tests may import production code; production must not import tests
- Domain-specific code must not leak into generic utilities
- `utils.py` and `helpers.py` must not become dumping grounds; prefer
  domain-specific modules

### 3.12 — Comments and docstrings

Remove or rewrite:
- AI-looking filler (e.g. "This module provides…", "Here we…")
- Obvious comments that restate the code
- Stale phase/ticket/MVP/`CP2` references in source files (belongs only in docs)
- Overclaiming adjectives: `robust`, `perfect`, `comprehensive`, `optimal`,
  `production-ready` without evidence
- Docstrings that only restate the function name
- Obsolete comments describing old behavior
- Comments that contradict code
- Vague `TODO`/`FIXME` that are not actionable

Preserve:
- Comments explaining invariants
- Boundary conversion notes
- Calibration/test separation guards
- Deterministic seeding explanations
- Artifact reproducibility notes
- Scientific protocol locks
- Non-obvious research assumptions
- Serialization contracts
- Security assumptions
- Intentional duplication where semantics differ (with explanation)

### 3.13 — Naming discipline

Flag weak or stale names:
`mvp`, `tmp`, `temp`, `old`, `new`, `final`, `backup`, `misc`, `stuff`,
`helper`, `helpers`, `utils`, `phase_a`, `ticket`, `scratch`, `draft`

Do not rename public APIs blindly unless all references and tests can be safely
updated.

### 3.14 — Research protocol hygiene

Detect boundary confusion:
- Test data used as calibration source
- Training scores used where calibration candidates are expected
- Seed lists duplicated outside canonical seed modules
- Metrics implemented outside canonical metric modules
- Experiment paths bypassing artifact layout
- Protocol labels leaking into generic code
- Comments suggesting training/model/test poisoning in a calibration-channel-only project
- Claims in comments that exceed what the code proves
- Silent changes to scientific behavior

Do **not** modify scientific protocol behavior unless a clear bug exists and
tests validate the fix.

---

## Step 4 — Fix safe issues

Fix issues that are safe to fix without scientific or protocol judgment:

**Safe to fix automatically:**
- Formatting and linting (already done by ruff)
- Unused imports
- Obvious dead code with no callers (verify with grep before removing)
- Obsolete/AI-looking comments when replacement is clear
- Missing type annotations when the correct type is unambiguous
- Constants that clearly have one owner and one meaning
- `dict[str, Any]` replaceable with an existing typed dataclass
- Architecture imports that clearly violate the rules above

**Do not fix without explicit instruction:**
- Issues that require changing scientific protocol behavior
- Issues where the correct constant/enum value is ambiguous
- Issues requiring dataset or experiment artifact changes
- Issues where fixing would break the test/calibration/training boundary
- Issues where the same-looking value has different semantic meanings

---

## Step 5 — Re-run relevant checks

After fixing, re-run the affected checks from Step 1. Record new results.

---

## Step 6 — Final report

Print a structured report. Redact all token-like values.

```
=== /CleanCode Report ===

Branch:       <branch>
Commit:       <sha>
Date:         <date>

--- Checks ---
ruff format:           PASS | FAIL | SKIPPED
ruff check:            PASS | FAIL | SKIPPED
pyright:               PASS | FAIL (<N> errors) | SKIPPED
mypy:                  PASS | FAIL | SKIPPED
pytest:                PASS | FAIL (<N> failures) | SKIPPED
pytest-cov:            PASS | FAIL | SKIPPED
bandit:                PASS | FAIL | SKIPPED
pylint:                PASS | FAIL | SKIPPED
semgrep:               PASS | FAIL | SKIPPED

--- SonarCloud ---
Token present:         YES | NO
Auth result:           OK | AUTH_FAILURE | NETWORK_FAILURE | NOT_CHECKED
Quality gate:          OK | WARN | ERROR | NONE | UNKNOWN | NOT_CHECKED
Analysis freshness:    CURRENT | STALE (<delta>) | UNKNOWN | NOT_CHECKED
Open issues:           <N> | NOT_CHECKED

--- CS ---
CS_ACCESS_TOKEN:       PRESENT | MISSING
CS status:             SKIPPED — no repo-defined CS integration

--- Files changed ---
<list of files modified>

--- Issues fixed ---
<categorized list>

--- Issues remaining ---
<categorized list with severity and location>

--- Manual inspection findings ---
<findings that require human judgment>

--- Risks and follow-ups ---
<anything the agent deems risky or deferred>

=== End of Report ===
```

Do **not** claim the repository is clean unless every check above passed and
SonarCloud shows zero open issues on the current commit.
