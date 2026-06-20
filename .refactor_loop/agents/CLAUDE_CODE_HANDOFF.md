# CLAUDE_CODE_HANDOFF.md — Handoff Template for Claude Code Sonnet

Claude Code Sonnet is a **specialist agent**, not the orchestrator.
It should be invoked by OpenClaw for specific bounded tasks in later phases.

---

## Claude Code's Role in This Campaign

- Bounded implementation tasks (during implementation phase only)
- Difficult cross-file code navigation
- Integration review of patches
- Test failure diagnosis
- Final patch review before merge

Claude Code must not take orchestration decisions. It must not move tasks on `TASK_BOARD.md`
unless explicitly delegated to do so by OpenClaw.

---

## Session Start Checklist for Claude Code

When invoked for a task in this campaign:

- [ ] Read the specific task entry in `agents/TASK_BOARD.md` for the task being worked.
- [ ] Read `CLAUDE.md` in the repository root for scientific locks and coding rules.
- [ ] Read `09_SCIENTIFIC_CONTRACT_MAP.md` before touching any poisoning, calibration, or policy code.
- [ ] Read `14_DRIFT_GATES.md` before writing any implementation.
- [ ] Read the patch plan in `12_PATCH_PLANS/<task-id>.md` if one exists.
- [ ] Confirm the task is in IN_PROGRESS state and the lock is current.

---

## Quota Parking Instructions

If Claude Code runs out of quota or context mid-task:

1. Write current findings or partial output to the designated output file.
2. Mark the section `PARTIAL — quota exhausted at <timestamp>`.
3. Write an entry to `agents/QUOTA_USAGE.md`.
4. Write an entry to `agents/SESSION_LOG.md` noting where work stopped.
5. Release the lock in `agents/LOCKS.md` as RELEASED-PARTIAL.
6. Do not attempt to continue — notify the user. OpenClaw will re-route to fallback.

---

## Handoff Format

When Claude Code completes a task and returns control to OpenClaw:

```
## CC-HANDOFF-<ID>
- Date: <ISO timestamp>
- Task: <task ID>
- Status: DONE | PARTIAL | BLOCKED
- Output file written: <path>
- Source files modified: YES / NO — <list if YES>
- Tests run: YES / NO — <commands if YES>
- Drift check: PASSED | FAILED | NOT_RUN
- Quota status: OK | EXHAUSTED
- Next recommended action: <summary>
```

---

## Known Handoffs

*(append entries below as they occur)*
