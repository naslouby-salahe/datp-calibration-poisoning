# 13_TEST_RUNS.md — Test Run Log

**Status:** PENDING — awaiting TEST-001
**Owner:** OpenClaw (TEST-001)
**Last updated:** 2026-06-20T21:27:24Z (scaffold only)

> WARNING: Do not edit source files during this inventory.
> This is a read-only analysis document.

---

## Purpose

Discover safe test and check commands. Record all test run outputs from
implementation loops for traceability.

---

## Instructions for TEST-001 Agent

1. Identify the test runner from `pyproject.toml`, `setup.cfg`, or `Makefile`.
2. Confirm the following commands work without running experiments:
   ```
   python -m pytest tests/unit/ -x -q
   python -m pytest tests/integration/ -x -q
   python -m pyright src/
   python -m ruff check src/
   ```
3. Run only read-only checks (pyright, ruff) at this stage.
4. Do not run experiment tests or e2e tests.
5. Record output here.

---

## Safe Commands Discovered

*(to be populated by TEST-001)*

| Command | Purpose | Safe to run? | Notes |
|---|---|---|---|
| PENDING | — | — | TEST-001 not yet run |

---

## Tool Version Check

*(from CLAUDE.md §10 — run at session start)*

| Tool | Version | Status |
|---|---|---|
| graphify | PENDING | — |
| ruff | PENDING | — |
| pyright | PENDING | — |
| pytest | PENDING | — |
| uv | PENDING | — |

---

## Test Run History

*(record all test runs below — one section per run)*

### Format

```
## RUN-<ID>
- Date: <ISO timestamp>
- Agent: <agent>
- Phase: <campaign phase>
- Task: <task ID>
- Command: <exact command>
- Exit code: <0 = pass>
- Summary: <pass/fail counts>
- New failures: NONE / <list>
- Notes: <any relevant observations>
```

---

## Run Entries

*(no runs yet — implementation phase has not started)*
