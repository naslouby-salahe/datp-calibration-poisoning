# OPENCLAW_HANDOFF.md — Handoff Template for OpenClaw

Use this template when handing off orchestration between OpenClaw sessions
or when a prior session ended before completing its tasks.

---

## Handoff Format

```
## HANDOFF-<ID>
- Date: <ISO timestamp>
- Handing off from: <prior agent / session>
- Handing off to: OpenClaw
- Current phase: <phase name>
- Last completed task: <task ID>
- Last written output: <file path>
- Tasks in progress (possibly orphaned): <list or NONE>
- Orphaned locks: <list or NONE>
- Open blockers: <list or NONE>
- Quota issues: <list or NONE>
- Next recommended action: <summary>
- Files to read at session start: <list>
```

---

## Session Start Checklist for OpenClaw

- [ ] Read `agents/SESSION_LOG.md`
- [ ] Read `agents/TASK_BOARD.md`
- [ ] Read `agents/BLOCKERS.md`
- [ ] Read `agents/QUOTA_USAGE.md`
- [ ] Read `agents/LOCKS.md` — confirm no orphaned locks
- [ ] Read `00_LOOP_STATE.md` — confirm phase
- [ ] Read `OPENCLAW_ORCHESTRATOR.md` — re-read instructions
- [ ] Resolve any orphaned locks before dispatching new work
- [ ] Identify next task(s) to dispatch based on `TASK_QUEUE.md`

---

## Known Handoffs

*(append entries below as they occur)*
