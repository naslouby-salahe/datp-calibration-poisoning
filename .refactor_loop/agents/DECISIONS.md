# DECISIONS.md — Campaign Decision Log

Record all significant decisions made during the campaign here.

---

## Decision Format

```
## DEC-<ID>
- Decision ID: DEC-<ID>
- Date: <ISO timestamp>
- Owner: <agent or human>
- Context: <what situation prompted this decision>
- Decision: <what was decided>
- Alternatives rejected: <list with reasons>
- Scientific impact: <how this affects CP2 scientific protocol, or NONE>
- Engineering impact: <how this affects code structure or test coverage>
```

---

## DEC-001

- Decision ID: DEC-001
- Date: 2026-06-20T21:27:24Z
- Owner: Claude Code Sonnet (initialization) / user
- Context: Campaign initialization. Need a durable orchestrator that can coordinate long multi-agent refactor sessions without losing state.
- Decision: OpenClaw / Copilot Sonnet designated as durable orchestrator. All persistent state lives in `.refactor_loop/`. No agent relies on chat memory.
- Alternatives rejected: Claude Code Sonnet as orchestrator (quota limits; not durable across long sessions). Hermes as orchestrator (review-only role; not suitable for coordination).
- Scientific impact: NONE — this is an organizational decision only.
- Engineering impact: All agents must read `.refactor_loop/` at session start. No implicit chat-session state.
