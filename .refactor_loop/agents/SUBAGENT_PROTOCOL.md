# SUBAGENT_PROTOCOL.md — Subagent Rules

Subagents are dispatched by OpenClaw to perform bounded, read-only inventory tasks.
Each subagent handles exactly one task and writes to exactly one output file.

---

## Before Starting

1. Read `agents/TASK_BOARD.md` to confirm the task is assigned to you.
2. Read `agents/LOCKS.md` to confirm no other agent has claimed the task.
3. Write a lock entry to `agents/LOCKS.md` before doing any work.
4. Read the task's listed dependencies — do not proceed if a dependency is incomplete.

---

## Scope Rules

- **One task per subagent.** Do not expand scope beyond the assigned task.
- **One output file per task.** Write all findings to the designated output file only.
- **Do not overwrite another agent's output.** If the output file exists, append under a new dated section.
- **Read-only by default.** Do not modify any source file, test file, config, or script during inventory phases.
- **Stop when the task is complete.** Do not continue to adjacent tasks.

---

## Required Output Structure

Each subagent output file must include:

```
## Task: <TASK_ID>
## Agent: <agent name>
## Date: <ISO timestamp>
## Status: COMPLETE | PARTIAL | BLOCKED

### Files Inspected
- <list of files read, with line ranges if partial>

### Findings
<structured findings per the ledger or index template>

### Uncertainty
<anything the subagent could not determine, or found ambiguous>

### Recommended Next Steps
<what the orchestrator or next subagent should do>
```

---

## Uncertainty Rules

- If a finding is uncertain, mark it `UNCERTAIN` in the ledger row.
- Do not infer values from names or comments alone — read the actual code.
- If a file was not fully inspected, mark the entry `PARTIAL`.
- If a dependency is missing, mark the task `BLOCKED` and write to `agents/BLOCKERS.md`.

---

## On Completion

1. Update the output file with final status.
2. Release the lock in `agents/LOCKS.md` (set status to RELEASED).
3. Update `agents/TASK_BOARD.md` (set task status to DONE or BLOCKED).
4. Append an entry to `agents/SESSION_LOG.md`.
5. Do not start another task without being re-dispatched by the orchestrator.

---

## Scientific Safety

- Never speculate about scientific correctness — report what the code does, not what it should do.
- If you find a potential scientific drift (e.g., clean array mutation, test score used as reservoir,
  wrong seed scheme), record it in `agents/BLOCKERS.md` with severity HIGH.
- Do not attempt to fix scientific issues during inventory — record only.
