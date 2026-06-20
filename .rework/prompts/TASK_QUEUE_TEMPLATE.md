# Task Queue Template -- datp-cp

Standard formats for all task queues.

Use these formats for consistency across all agents.

---

## Claude Task Format (CLAUDE_TASK_QUEUE.md)

    ### TASK-NNN -- <title>
    Agent: Claude
    Type: audit / refactor / implement / test / verify / paper
    Severity: CRITICAL / HIGH / MEDIUM / LOW
    Depends on: <task IDs or "none">
    Parallel safe with: <task IDs or "none">
    Files: <list of affected files>
    Instruction: <what must be done>
    Acceptance: <how to verify>
    Status: TODO / IN_PROGRESS / DONE / BLOCKED

---

## Codex Task Format (CODEX_TASK_QUEUE.md)

    ### TASK-NNN -- <title>
    Agent: Codex
    Type: audit / refactor / implement / test / verify / paper
    Severity: CRITICAL / HIGH / MEDIUM / LOW
    Depends on: <task IDs or "none">
    Parallel safe with: <task IDs or "none">
    Files: <list of affected files>
    Instruction: <what must be done>
    Acceptance: <how to verify>
    Status: TODO / IN_PROGRESS / DONE / BLOCKED

---

## Claude-to-Codex Task Format (CLAUDE_TO_CODEX_TASKS.md)

Created by Claude when identifying work for Codex.

    ### C2X-NNN -- <title>
    Created by: Claude
    Source finding: <review report reference>
    Type: audit / refactor / implement / test / verify
    Severity: CRITICAL / HIGH / MEDIUM / LOW
    Files: <list of affected files>
    Instruction: <what Codex must do>
    Acceptance: <how to verify>
    Status: TODO / IN_PROGRESS / DONE / BLOCKED

---

## Codex-to-Claude Task Format (CODEX_TO_CLAUDE_TASKS.md)

Created by Codex when identifying work for Claude.

    ### X2C-NNN -- <title>
    Created by: Codex
    Source finding: <review report reference>
    Type: audit / refactor / implement / test / verify
    Severity: CRITICAL / HIGH / MEDIUM / LOW
    Files: <list of affected files>
    Instruction: <what Claude must do>
    Acceptance: <how to verify>
    Status: TODO / IN_PROGRESS / DONE / BLOCKED

---

## OpenClaw Review Task Format (OPENCLAW_REVIEW_QUEUE.md)

    ### REVIEW-NNN -- <title>
    Agent: OpenClaw
    Scope: <code path or paper section>
    Related task: <task ID or "none">
    Instruction: <what to review>
    Status: TODO / IN_PROGRESS / DONE

---

## Hermes Task Format (HERMES_TASK_QUEUE.md)

    ### H-NNN -- <title>
    Type: orchestration / bootstrap / audit / paper-assembly
    Depends on: <task IDs or "none">
    Instruction: <what Hermes must do>
    Status: TODO / IN_PROGRESS / DONE / BLOCKED

---

## Severity Definitions

    CRITICAL -- blocks all progress; must be fixed before any further work
    HIGH     -- must be fixed in the current cycle
    MEDIUM   -- should be fixed before final sign-off
    LOW      -- fix if time allows; must be documented if deferred

---

## Parallel Safety

Two tasks are parallel-safe when they modify strictly disjoint file sets.

Always check file lists before dispatching parallel tasks.

See HERMES_AUDIT_LOOP.md Section 4 for the full parallelism decision protocol.
