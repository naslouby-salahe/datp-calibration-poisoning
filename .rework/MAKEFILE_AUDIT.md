# Makefile Audit — datp-cp

Audit of Makefile targets against the canonical public workflow.

---

## Verdict

Not yet audited.

---

## Required Public Targets

Exactly these targets must exist and work:

    help           — lists all public targets with descriptions
    check          — runs ruff check and pyright
    datp-cp-clean  — generates clean baseline artifacts (FL training + scoring)
    datp-cp-smoke  — runs SYNTHETIC_SMOKE stage
    datp-cp-dry-run — safe dry run (no actual experiment output)
    datp-cp-run    — runs NBAIOT_MAIN stage
    datp-cp-report — generates the report from outputs
    clean          — cleans build artifacts (not outputs)

---

## Forbidden Targets (must NOT exist in active Makefile)

    run-regime-a, run-regime-b, run-regime-c
    run-main-matrix
    sweep, sweep-dry-run
    gate0, gate1, gate2, gate3
    poison-bounded, poison-stages
    Any target using B1/B2/B3/B4 naming
    Any target using Regime A/B/C naming

---

## Audit Checks

For each canonical target, verify:

    target exists in Makefile
    target recipe is correct and runnable
    target does not invoke forbidden targets internally
    make help shows the target with a description
    no obsolete environment variables required

---

## Findings

### Status: not yet audited

Agents: inspect the Makefile:

    grep -n "^[a-zA-Z]" Makefile | grep -v "#"

Write findings here and create CLAUDE tasks for violations.
