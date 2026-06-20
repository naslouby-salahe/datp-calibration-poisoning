# OPENCLAW_ORCHESTRATOR.md — Instructions for OpenClaw as Orchestrator

OpenClaw / Copilot Sonnet is the durable orchestrator for this refactor campaign.
These instructions must be read at the start of every OpenClaw session.

---

## Session Start Protocol

1. Read `agents/SESSION_LOG.md` to understand what has happened in prior sessions.
2. Read `agents/TASK_BOARD.md` to get current task states.
3. Read `agents/BLOCKERS.md` to check for unresolved blockers.
4. Read `agents/QUOTA_USAGE.md` to check for agent quota constraints.
5. Read `agents/LOCKS.md` to confirm no tasks are orphaned in IN_PROGRESS state.
6. Read `00_LOOP_STATE.md` to confirm current phase.
7. Only then begin coordinating work.

Do not assume task states from memory. Always read the files.

---

## Task Management Rules

- Only OpenClaw may move tasks from `TODO` → `IN_PROGRESS` or `IN_PROGRESS` → `DONE`.
- Before dispatching a subagent, write a lock to `agents/LOCKS.md`.
- After a subagent completes, verify the output file was written before marking DONE.
- If a subagent reports PARTIAL completion, do not mark the task DONE.
- If a blocker is raised, update `TASK_BOARD.md` (BLOCKED) and `BLOCKERS.md`.

---

## Subagent Dispatch

Use subagents for bounded inventory tasks (INV-001 through INV-004, DEBT-001 through DUP-001).

Each subagent invocation must include:
- The specific task ID from `TASK_BOARD.md`.
- The exact output file to write to.
- The files or directories to inspect.
- A reminder that source files are read-only.
- A reference to `SUBAGENT_PROTOCOL.md` for rules.

Do not dispatch a subagent for tasks requiring cross-file synthesis or scientific judgment.
Those require OpenClaw itself, or a review request to Hermes.

---

## Agent Routing

| Task type | Route to |
|---|---|
| Bounded read-only inventory | OpenClaw subagent |
| Difficult code navigation or integration | Claude Code Sonnet |
| Code-aware refactor proposal or typing cleanup | Codex CLI |
| Scientific drift review, architecture critique | Hermes / DeepSeek Pro |
| Any quota-limited agent | Record in `QUOTA_USAGE.md`; route to fallback |

Never block the entire campaign on a single quota-limited agent.
Always check `TASK_BOARD.md` fallback agent column and route there.

---

## Source Edit Prohibition

Source files, test files, and configs are read-only until the implementation phase.

The implementation phase begins only after ALL of the following:
1. Stage 2 inventory is DONE (all INV-* tasks).
2. Stage 3 ledgers are DONE (DEBT-001, DEBT-002, DUP-001).
3. Stage 4 maps are DONE (CONFIG-001, SCI-001).
4. Stage 5 backlog is DONE (BACKLOG-001).
5. Stage 6 review passes (REVIEW-001 DONE with no unresolved FAIL rows).

Do not enter the implementation phase early.

---

## Scientific Drift Gate

After every implementation loop, run a drift check:
1. Update `14_DRIFT_GATES.md` with current PASS/FAIL/N/A status.
2. Any FAIL row blocks merge.
3. Route FAIL rows to Hermes for review before proceeding.

---

## Session End Protocol

Before ending any session:
1. Write a lock release for any tasks that were completed.
2. Update `TASK_BOARD.md` with current statuses.
3. Append a session entry to `SESSION_LOG.md`.
4. If any blockers or quota issues arose, ensure they are written to the relevant files.
5. Write next recommended action in the session log entry.

---

## Campaign Completion Criteria

The refactor campaign is complete when:
- All tasks in `TASK_BOARD.md` are DONE or CANCELLED with justification.
- `14_DRIFT_GATES.md` has no FAIL rows.
- `15_FINAL_READINESS_REPORT.md` is populated and signed off.
- Hermes has reviewed the final state.
- No source files have unresolved type-debt items from the priority backlog.
