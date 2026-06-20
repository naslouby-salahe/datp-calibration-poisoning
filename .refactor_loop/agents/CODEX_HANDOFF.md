# CODEX_HANDOFF.md — Handoff Template for Codex CLI

Codex CLI is a specialist agent for code-aware refactor proposals, implementation assistance,
and static type/lint cleanup.

---

## Codex's Role in This Campaign

- Code-aware refactor proposals (later implementation phase)
- Implementation of typed contracts where Claude Code is unavailable
- Test failure diagnosis
- Static typing cleanup (`pyright` error resolution)
- Lint-level structural cleanup (`ruff`)

Codex must not take orchestration decisions.
Codex must not make scientific-scope judgments — if a change touches calibration logic,
reservoir logic, threshold policy, or poisoning mechanics, escalate to Hermes for review.

---

## Session Start Checklist for Codex

When invoked for a task in this campaign:

- [ ] Read the specific task entry in `agents/TASK_BOARD.md`.
- [ ] Read `09_SCIENTIFIC_CONTRACT_MAP.md` — do not modify code covered by this contract without escalation.
- [ ] Read the patch plan in `12_PATCH_PLANS/<task-id>.md` if one exists.
- [ ] Confirm the task is IN_PROGRESS and the lock is current in `agents/LOCKS.md`.
- [ ] Read `CLAUDE.md` — particularly the coding rules and scientific locks sections.

---

## Quota Parking Instructions

If Codex runs out of quota or context mid-task:

1. Write partial output or current progress to the designated output file.
2. Mark any partial section `PARTIAL — quota exhausted at <timestamp>`.
3. Write an entry to `agents/QUOTA_USAGE.md`.
4. Write an entry to `agents/SESSION_LOG.md`.
5. Release the lock in `agents/LOCKS.md` as RELEASED-PARTIAL.
6. OpenClaw will re-route to Claude Code as fallback.

---

## Tasks to Avoid

- Scientific scope decisions (reservoir, threshold, policy logic)
- Cross-module architectural decisions
- Orchestration or task board management
- Experiments or data generation

---

## Handoff Format

```
## CODEX-HANDOFF-<ID>
- Date: <ISO timestamp>
- Task: <task ID>
- Status: DONE | PARTIAL | BLOCKED
- Output file written: <path>
- Source files modified: YES / NO — <list if YES>
- Pyright errors before: <count>
- Pyright errors after: <count>
- Ruff issues before: <count>
- Ruff issues after: <count>
- Quota status: OK | EXHAUSTED
- Escalation needed: YES / NO — <reason if YES>
- Next recommended action: <summary>
```

---

## Known Handoffs

*(append entries below as they occur)*
