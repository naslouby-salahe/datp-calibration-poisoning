# AGENT_ROSTER.md — Multi-Agent Campaign Roster

All agents in this campaign are listed here. Capabilities and constraints are fixed at campaign start.

---

## OpenClaw / Copilot Sonnet

| Field | Value |
|---|---|
| Role | **Durable orchestrator** |
| Strengths | Long sessions, persistent context, subagent dispatch, task coordination |
| Usage / limit concerns | Monitor session length; checkpoint state to `.refactor_loop/` before context fills |
| Best task types | Orchestration, task routing, reading `.refactor_loop/` state, dispatching subagents, synthesis |
| Tasks to avoid | Deep line-by-line code review; harsh scientific critique; complex test diagnosis |
| Allowed to orchestrate | YES — primary orchestrator |
| Allowed to implement (later phases) | YES — may implement bounded patches if no specialist is available |
| Review-only | NO |

**Notes:**
- Must read the full `.refactor_loop/` workspace at session start before doing anything.
- Must update `TASK_BOARD.md` and `SESSION_LOG.md` at session end.
- Must not proceed to implementation phase until inventory is complete and a drift gate passes.

---

## OpenClaw Subagents

| Field | Value |
|---|---|
| Role | Bounded read-only inventory workers |
| Strengths | Parallelizable; each can be focused on one file/module/ledger |
| Usage / limit concerns | Each subagent has limited context; scope must be tightly bounded |
| Best task types | Single-file symbol extraction, type-debt scan of one module, hardcoded-value scan |
| Tasks to avoid | Cross-file synthesis; decision-making; writing to multiple output files |
| Allowed to orchestrate | NO |
| Allowed to implement (later phases) | NO — inventory only unless explicitly promoted |
| Review-only | YES (during inventory phases) |

**Notes:**
- Must write findings to the single designated output file for the task.
- Must not modify source files at any time.
- See `SUBAGENT_PROTOCOL.md` for full rules.

---

## Claude Code Sonnet

| Field | Value |
|---|---|
| Role | Specialist — implementation, integration review, hard code navigation |
| Strengths | Strong repo navigation, integration-aware edits, test diagnosis, final patch review |
| Usage / limit concerns | Session quota; not always available; do not block campaign if quota is exhausted |
| Best task types | Bounded implementation tasks, difficult cross-file navigation, test failure diagnosis, final patch review |
| Tasks to avoid | Durable orchestration (short session memory); harsh architectural critique |
| Allowed to orchestrate | NO — specialist only |
| Allowed to implement (later phases) | YES |
| Review-only | NO |

**Notes:**
- If Claude Code is quota-limited, record in `QUOTA_USAGE.md` and route to Codex CLI.
- Claude Code should read `CLAUDE_CODE_HANDOFF.md` at the start of every session in this repo.

---

## Codex CLI

| Field | Value |
|---|---|
| Role | Specialist — code-aware refactor proposals, implementation assistance, typing/lint cleanup |
| Strengths | Fast code-aware suggestions, static typing analysis, lint-level cleanup |
| Usage / limit concerns | May have context limits; not always quota-available |
| Best task types | Refactor proposals, implementation of typed contracts, test diagnosis, lint/type cleanup |
| Tasks to avoid | Scientific critique; orchestration; decisions about experiment scope |
| Allowed to orchestrate | NO |
| Allowed to implement (later phases) | YES |
| Review-only | NO |

**Notes:**
- If Codex is quota-limited, record in `QUOTA_USAGE.md` and route to Claude Code.
- See `CODEX_HANDOFF.md` for session entry instructions.

---

## Hermes / DeepSeek Pro

| Field | Value |
|---|---|
| Role | Specialist — harsh scientific and architectural reviewer |
| Strengths | Thorough critique, scientific scope analysis, typed-contract critique, claims-scope review |
| Usage / limit concerns | Reserve for high-value review tasks; monitor usage carefully |
| Best task types | Scientific drift gate review, architecture critique, typed-contract critique, backlog review, claims-scope review |
| Tasks to avoid | Implementation; test running; orchestration |
| Allowed to orchestrate | NO |
| Allowed to implement (later phases) | NO — review-only |
| Review-only | YES |

**Notes:**
- Hermes should be invoked when backlog is ready and after each implementation loop for drift review.
- Record every Hermes invocation in `QUOTA_USAGE.md`.
- See `HERMES_HANDOFF.md` for review request format.
