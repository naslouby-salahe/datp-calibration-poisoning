# QUOTA_USAGE.md — Agent Quota Log

Record every quota issue or agent context exhaustion here.
OpenClaw must consult this file before dispatching agents.

---

## Log Format

```
## QUOTA-<ID>
- Timestamp: <ISO>
- Agent: <agent name>
- Task ID: <task ID>
- Status: EXHAUSTED | RATE_LIMITED | CONTEXT_FULL | PARTIAL_COMPLETE
- What was completed: <summary>
- What remains: <summary>
- Output file state: WRITTEN | PARTIAL | NOT_WRITTEN
- Fallback agent: <agent name from TASK_BOARD.md>
- Resume note: <what the fallback agent needs to know to continue>
- Next action: <ROUTE_TO_FALLBACK | WAIT_AND_RETRY | SPLIT_TASK | ESCALATE>
```

---

## Log Entries

*(no quota issues recorded — append below as they occur)*
