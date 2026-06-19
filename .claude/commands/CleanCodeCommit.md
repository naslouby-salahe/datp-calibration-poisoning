# /CleanCodeCommit — Iterative Cleanup with Commits

Perform iterative code quality cleanup and commit safe changes. Loop until the
repository is clean or a bounded stop condition is reached.

This command includes the full `/CleanCode` process plus commit and loop
behavior. Read `/CleanCode` first — all of its steps apply here.

---

## Loop limits (default)

```
Maximum iterations:       5
SonarCloud poll interval: 20 seconds
Maximum wait per iteration for SonarCloud: 10 minutes
```

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
- Never commit secrets.
- Never commit datasets, raw data, generated outputs, MLflow runs, or experiment artifacts.
- If `.env.local` is not listed in `.gitignore`, add it before doing anything else.

Print:
- Current branch: `git rev-parse --abbrev-ref HEAD`
- Current commit SHA: `git rev-parse HEAD`
- Working tree snapshot: `git status --short`

Classify the working tree into:
- **Staged** changes
- **Unstaged modified** files
- **Untracked** files

**Isolation check:** If the working tree contains unrelated user work (staged or
unstaged changes unrelated to code quality), refuse to mix them with cleanup
commits. State: "STOPPED — unrelated user work detected. Stash or commit your
work first." Stop here.

---

## Step 1 — Full /CleanCode process (iteration start)

Execute every step from `/CleanCode` (Steps 1–5):

1. Run all local automated checks (ruff format, ruff check, pyright, mypy,
   pytest, coverage, bandit, pylint, semgrep).
2. Query SonarCloud via direct API (no sonar-scanner, no sonar-project.properties).
3. Perform full manual code inspection covering all categories in `/CleanCode`
   Step 3 (dead code, unreachable code, unused params/locals/private symbols,
   exception hygiene, print statements, type annotation discipline, hardcoding,
   enum discipline, dataclass discipline, duplicate constants, architecture
   boundaries, comments/docstrings, naming, research protocol hygiene).
4. Fix safe issues.
5. Re-run affected checks.

---

## Step 2 — Safe validation before commit

Before committing, run the full validation suite:

```bash
python -m ruff format src/ tests/
python -m ruff check --fix src/ tests/
python -m pyright src/ 2>&1 || pyright src/ 2>&1
python -m pytest tests/ -x -q 2>&1
python -m bandit -r src/ -q 2>&1 || true
```

Do **not** commit if `pytest` fails.
Do **not** commit if `pyright` reports new errors introduced by the cleanup.
Do **not** commit if ruff still reports violations after `--fix`.

---

## Step 3 — Commit safe cleanup changes

Stage only files changed as part of code quality cleanup. Do not stage unrelated
files.

Commit message must follow these examples:

```
chore: clean code quality findings
chore: resolve sonar findings
chore: fix lint and governance issues
chore: address remaining quality gate findings
```

Use a message that describes what category of findings was addressed.

**Commit constraints:**
- Do **not** force-push.
- Do **not** amend commits unless explicitly asked by the user.
- Do **not** rewrite history.
- Do **not** commit `.env.local`.
- Do **not** commit any file matching: `*.env*`, `*token*`, `*secret*`,
  `*credential*`, `coverage.xml`, `mlruns/`, `outputs/`, `experiments/`,
  `artifacts/`, `*.parquet`, `*.pkl`, `*.npy`, `*.h5`.

---

## Step 4 — SonarCloud re-query after commit

After committing, check whether CI or SonarCloud analysis is expected to run.

If SonarCloud analysis is CI-triggered:
- Wait up to 10 minutes for a new analysis to appear.
- Poll every 20 seconds using:

  ```
  GET $SONAR_HOST_URL/api/project_analyses/search
    ?project=$SONAR_PROJECT_KEY
    &ps=1
  ```

- Compare the `date` field of the most recent analysis against the current
  commit timestamp.
- If a new analysis appears within 10 minutes, fetch updated issue list and
  quality gate status.
- If no new analysis appears within 10 minutes, record "SonarCloud: STALE —
  no new analysis detected after commit" and continue to next iteration.

**Freshness rule:** If the most recent SonarCloud analysis predates the current
commit, state clearly: "SonarCloud analysis freshness: UNKNOWN — results may
not reflect the current commit."

Do **not** claim SonarCloud is clean unless the analysis `date` is after or
within 2 minutes of the current commit timestamp.

---

## Step 5 — Evaluate loop continuation

After each commit and SonarCloud re-query, evaluate whether to continue:

**Stop immediately if any of the following is true:**

1. **No progress:** The same set of issues is present after a fix attempt.
2. **Repeated failure:** The same specific issue survived two consecutive fix
   attempts.
3. **Scientific/protocol decision required:** The remaining issue requires
   changing calibration-channel, seed, metric, threshold, or experiment
   protocol behavior.
4. **Dataset or artifact change required:** Fixing the issue would require
   modifying datasets, raw data, generated outputs, MLflow runs, or experiment
   artifacts.
5. **SonarCloud permanently stale:** SonarCloud analysis remains unavailable or
   stale after two consecutive iterations.
6. **Maximum iterations reached:** 5 iterations completed.
7. **Isolation impossible:** New unrelated user work appeared in the working
   tree.

If a stop condition is triggered, record it and jump to the Final Report.

**Continue if:**
- New issues were fixed in this iteration.
- SonarCloud returned updated results with fewer open issues.
- Local checks improved.
- Maximum iterations not yet reached.

---

## Step 6 — Next iteration

If continuing: go back to Step 1. Carry forward the iteration counter and the
set of known-unfixable issues to avoid re-attempting them.

---

## Final report

Print a structured report after the loop exits. Redact all token-like values.

```
=== /CleanCodeCommit Report ===

Branch:                 <branch>
Initial commit:         <sha before first commit>
Final commit:           <sha after last commit>
Date:                   <date>
Iterations completed:   <N> / 5

--- Commits created ---
<commit sha>  <message>
<commit sha>  <message>
...

--- Checks (final state) ---
ruff format:            PASS | FAIL | SKIPPED
ruff check:             PASS | FAIL | SKIPPED
pyright:                PASS | FAIL (<N> errors) | SKIPPED
mypy:                   PASS | FAIL | SKIPPED
pytest:                 PASS | FAIL (<N> failures) | SKIPPED
pytest-cov:             PASS | FAIL | SKIPPED
bandit:                 PASS | FAIL | SKIPPED
pylint:                 PASS | FAIL | SKIPPED
semgrep:                PASS | FAIL | SKIPPED

--- SonarCloud (final state) ---
Token present:          YES | NO
Auth result:            OK | AUTH_FAILURE | NETWORK_FAILURE | NOT_CHECKED
Quality gate:           OK | WARN | ERROR | NONE | UNKNOWN | NOT_CHECKED
Analysis freshness:     CURRENT | STALE (<delta>) | UNKNOWN | NOT_CHECKED
Open issues remaining:  <N> | NOT_CHECKED

--- CS ---
CS_ACCESS_TOKEN:        PRESENT | MISSING
CS status:              SKIPPED — no repo-defined CS integration

--- Issues fixed (all iterations) ---
<categorized list>

--- Remaining Sonar issues ---
<key, severity, rule, file:line, message>

--- Remaining local issues ---
<categorized list>

--- Manual inspection findings ---
<findings that require human judgment>

--- Skipped and why ---
<list of skipped checks and reason>

--- Stop condition triggered ---
<which condition, which iteration>

--- Repository quality verdict ---
CLEAN — all local checks pass, SonarCloud quality gate OK, zero open issues on current commit.
| or |
NOT CLEAN — <list of remaining blockers>

=== End of Report ===
```

**Do not claim 10/10 or "clean" unless:**
- All local checks pass (ruff, pyright, pytest)
- SonarCloud quality gate status is `OK`
- SonarCloud open issue count is `0`
- SonarCloud analysis is confirmed fresh (analysis date ≥ current commit timestamp)
- Manual inspection found nothing requiring action

---

## Reference — SonarCloud API (direct, no sonar-scanner)

**Forbidden:** `sonar-scanner`. **Forbidden:** `sonar-project.properties`.

Load credentials from environment (set in Step 0). Defaults:
- `SONAR_HOST_URL=https://sonarcloud.io`
- `SONAR_PROJECT_KEY=naslouby-salahe_datp-calibration-poisoning`
- `SONAR_ORGANIZATION=naslouby-salahe`

Use Basic auth: `SONARQUBE_TOKEN` as username, empty password.
Never expand the token in printed output. Always reference via shell variable.

**Quality gate:**
```
GET $SONAR_HOST_URL/api/qualitygates/project_status
  ?projectKey=$SONAR_PROJECT_KEY
  &branch=<branch>
```

**Issues (paginated):**
```
GET $SONAR_HOST_URL/api/issues/search
  ?componentKeys=$SONAR_PROJECT_KEY
  &branch=<branch>
  &resolved=false
  &ps=100
  &p=<page>
```
Fetch all pages until `total` is exhausted.

**Latest analysis:**
```
GET $SONAR_HOST_URL/api/project_analyses/search
  ?project=$SONAR_PROJECT_KEY
  &ps=1
```

**Distinguish these states:**
- `MISSING_TOKEN` — skip gracefully, continue local-only
- `AUTH_FAILURE` — report, do not retry
- `NETWORK_FAILURE` — report, continue with local results
- `PROJECT_NOT_FOUND` — report, do not retry
- `NO_ANALYSIS` — report clearly
- `ANALYSIS_STALE` — report with date delta
- `ZERO_ISSUES` — report as clean
- `OPEN_ISSUES` — list all, categorize

---

## Reference — Manual inspection checklist (both iterations)

Inspect directly on each iteration for items not caught by automated tools:

**Dead and unreachable code:**
- Functions/classes never called or imported
- Variables assigned but never read
- Branches that can never be true
- Code after unconditional `return`/`raise`/`break`/`continue`

**Unused symbols:**
- Unused parameters (prefer `_` prefix)
- Unused locals
- Unused private functions/classes

**Exception hygiene:**
- Bare `except:` clauses
- Overbroad `except Exception:` swallowing errors silently
- `pass`-only exception handlers for non-recoverable errors

**Type annotation discipline:**
- Unjustified `Any`
- `dict[str, Any]` where a typed structure is clearly better
- Missing public API annotations

**Hardcoding (see full classification in /CleanCode Step 3.7)**

**Enum discipline (see full rules in /CleanCode Step 3.8)**

**Dataclass discipline (see full rules in /CleanCode Step 3.9)**

**Duplicate constants (see full classification in /CleanCode Step 3.10)**

**Architecture boundaries (see full rules in /CleanCode Step 3.11)**

**Comments and docstrings (see full rules in /CleanCode Step 3.12)**

**Naming (see full rules in /CleanCode Step 3.13)**

**Research protocol hygiene (see full rules in /CleanCode Step 3.14)**
