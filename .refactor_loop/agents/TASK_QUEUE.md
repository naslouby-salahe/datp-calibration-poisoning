# TASK_QUEUE.md — Dependency-Ordered Task Queue

Tasks must be executed in the order below. Groups within a stage may be parallelized
by OpenClaw subagents where dependencies allow.

---

## Stage 1 — Documentation Initialization

These tasks must complete before any inventory work begins.

| Order | Task ID | Description | Status |
|---|---|---|---|
| 1.1 | DOC-INIT-001 | Initialize refactor-loop documentation | DONE |

**Gate:** All scaffold files exist and checklist in `00_LOOP_STATE.md` is complete.

---

## Stage 2 — Read-Only Inventories

Read-only. No source files may be modified. These tasks may be parallelized by OpenClaw.

| Order | Task ID | Description | Depends on | Status |
|---|---|---|---|---|
| 2.1 | INV-001 | Populate file index | DOC-INIT-001 | TODO |
| 2.2 | INV-002 | Populate symbol index | INV-001 | TODO |
| 2.3 | INV-003 | Populate method IO index | INV-002 | TODO |
| 2.4 | INV-004 | Populate dataclass/enum/config index | INV-002 | TODO |
| 2.5 | TEST-001 | Discover safe test/check commands | DOC-INIT-001 | TODO |

**Gate:** All inventory files are COMPLETE (not PARTIAL or PENDING).

---

## Stage 3 — Analysis Ledgers

Synthesize inventory findings into structured debt/duplication ledgers.

| Order | Task ID | Description | Depends on | Status |
|---|---|---|---|---|
| 3.1 | DEBT-001 | Populate type-debt ledger | INV-002 | TODO |
| 3.2 | DEBT-002 | Populate hardcoded-values ledger | INV-001 | TODO |
| 3.3 | DUP-001 | Populate duplication ledger | INV-002 | TODO |

**Gate:** All ledgers populated with evidence-backed entries (no UNKNOWN rows).

---

## Stage 4 — Config and Science Maps

| Order | Task ID | Description | Depends on | Status |
|---|---|---|---|---|
| 4.1 | CONFIG-001 | Populate config flow map | INV-003, INV-004 | TODO |
| 4.2 | SCI-001 | Populate scientific contract map | INV-003, DEBT-001, DEBT-002 | TODO |

**Gate:** Config flow and scientific contract are documented with file+line evidence.
Hermes review of `09_SCIENTIFIC_CONTRACT_MAP.md` must pass before Stage 5.

---

## Stage 5 — Backlog Synthesis

| Order | Task ID | Description | Depends on | Status |
|---|---|---|---|---|
| 5.1 | BACKLOG-001 | Build initial typed-contract refactor backlog | DEBT-001, DEBT-002, DUP-001, CONFIG-001, SCI-001 | TODO |

**Gate:** Backlog is prioritized and scientifically annotated. No fabricated items.

---

## Stage 6 — Harsh Review

| Order | Task ID | Description | Depends on | Status |
|---|---|---|---|---|
| 6.1 | REVIEW-001 | Review backlog for scientific drift and architecture risk | BACKLOG-001 | TODO |

**Gate:** Hermes signs off on backlog. All FAIL items resolved or explicitly deferred.

---

## Stage 7 — Implementation Loops (Future)

Not started. Requires Stage 6 gate to pass.

Implementation tasks will be created in `10_REFACTOR_BACKLOG.md` and promoted to the task board
as individual IMPL-XXX tasks. Each implementation task must:

1. Have a patch plan in `12_PATCH_PLANS/`.
2. Be reviewed before merge.
3. Pass a `14_DRIFT_GATES.md` check.
4. Be verified against the test suite.

---

## Parallelization Notes

- INV-001 → INV-002 is sequential (symbol index needs file index).
- INV-003 and INV-004 can be parallelized once INV-002 is done.
- DEBT-001, DEBT-002, DUP-001 can be parallelized once INV-002 is done.
- CONFIG-001 and SCI-001 should be sequential after Stage 3 completes.
- TEST-001 can run in parallel with Stage 2.
