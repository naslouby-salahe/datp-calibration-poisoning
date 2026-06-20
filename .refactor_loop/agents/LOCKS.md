# LOCKS.md — Task Lock Registry

Every task that is IN_PROGRESS must have a lock entry here.
Claim a lock before starting work. Release it when done or when stopping.

---

## Lock Format

```
## LOCK-<ID>
- Task ID: <task ID>
- Agent: <agent name>
- Claimed at: <ISO timestamp>
- Expected output file: <path>
- Files expected to modify: <list — "NONE" during inventory phases>
- Status: ACTIVE | RELEASED | RELEASED-PARTIAL | ORPHANED
- Released at: <ISO timestamp or N/A>
```

---

## LOCK-001

- Task ID: DOC-INIT-001
- Agent: Claude Code Sonnet (initialization)
- Claimed at: 2026-06-20T21:27:24Z
- Expected output file: `.refactor_loop/00_LOOP_STATE.md`
- Files expected to modify: `.refactor_loop/**` (scaffold only — no source files)
- Status: RELEASED
- Released at: 2026-06-20T21:27:24Z

---

## Active Locks

*(no active locks — DOC-INIT-001 is complete)*

---

## Orphaned Lock Protocol

If OpenClaw finds a lock in ACTIVE state from a prior session with no corresponding
recent SESSION_LOG entry, it must:
1. Mark the lock ORPHANED.
2. Read the partial output file (if any).
3. Decide whether to re-dispatch or mark the task PARTIAL.
4. Write a decision to `agents/DECISIONS.md`.
