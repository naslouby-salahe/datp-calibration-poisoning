# Quota Handling -- Claude / Codex / OpenClaw

Hermes monitors quota and rate-limit events for Claude Code, Codex CLI, and OpenClaw.
Claude and Codex are equal peers. When one is quota-limited, Hermes shifts work to the other.

No commits. No PRs. Never sit idle during quota waits.

---

## 1. When Claude hits quota

If Claude reports quota, rate limit, or 5-hour reset:

    1. Record the exact message in .rework/logs/HERMES_LOG.md.
    2. Record: timestamp, agent, session, message, reset time if shown,
       current task, last useful output, files likely touched.
    3. Do not kill the tmux session.
    4. Do not restart Claude repeatedly.
    5. Assign Claude's pending implementation tasks to Codex if safe and non-overlapping.
    6. Ask OpenClaw for review if available.
    7. Hermes continues audits and task preparation.
    8. When Claude resets, send a focused resume task (not the full bootstrap prompt).

Focused resume example:

    Continue datp-cp rework.
    Focus only on TASK-NNN from .rework/tasks/CLAUDE_TASK_QUEUE.md.
    Rules: follow roadmap, strict enums/dataclasses, no backwards compat, update tests,
    run ruff + pyright + impacted tests, update STATUS.md, do not commit.

---

## 2. When Codex hits quota

If Codex reports quota, rate limit, or reset:

    1. Record the exact message in .rework/logs/HERMES_LOG.md.
    2. Record: timestamp, agent, session, message, reset time if shown,
       current task, last useful output, files likely touched.
    3. Do not kill the tmux session.
    4. Do not restart Codex repeatedly.
    5. Assign Codex's pending implementation tasks to Claude if safe and non-overlapping.
    6. Ask OpenClaw for review if available.
    7. Hermes continues audits and task preparation.
    8. When Codex resets, send a focused resume task.

---

## 3. When both Claude and Codex hit quota

If both Claude and Codex are quota-limited or unavailable:

    1. Record both events in .rework/logs/HERMES_LOG.md.
    2. Hermes enters moderate backup implementation mode.
    3. Hermes implements only safe, bounded, focused tasks (see HERMES_MASTER_ORCHESTRATION.md
       section on Hermes Backup Implementation for allowed tasks).
    4. Record every Hermes change in .rework/logs/HERMES_LOG.md.
    5. Mark Hermes as implementer in the task queue.
    6. Queue all Hermes changes for later Claude/Codex review.
    7. Ask OpenClaw for review if available.
    8. When either Claude or Codex resets, send them a review task for Hermes work first,
       then continue with new implementation tasks.

---

## 4. When OpenClaw hits quota

If OpenClaw reports quota, rate limit, or reset:

    1. Record in .rework/logs/HERMES_LOG.md.
    2. Continue Claude/Codex implementation.
    3. Hermes performs the review tasks OpenClaw would have done.
    4. Prepare the next OpenClaw review prompt for when it resets.
    5. Retry OpenClaw after reset.

---

## 5. When all model agents hit quota

If Claude, Codex, and OpenClaw are all on quota:

Hermes continues with non-model work:

    inspect repository with git status
    inspect changed files for obvious issues
    classify obsolete terminology hits
    review tests for stale references
    review Makefile for obsolete targets
    review README and CLAUDE.md
    review .claude/ agents, commands, and skills
    update .rework audit files
    update task queues
    prepare focused prompts for each agent's next session
    prepare IEEE paper audit checklist if outputs exist

Quota waiting is never idle time.

---

## 6. Task migration rules

When shifting a task from Claude to Codex (or vice versa):

    verify the task files do not overlap with Codex's (or Claude's) active work
    run git status --short and git diff --stat first
    update the task queue: move task from CLAUDE_TASK_QUEUE to CODEX_TASK_QUEUE (or reverse)
    record the migration in .rework/logs/HERMES_LOG.md

---

## 7. Quota log format

Use this format in .rework/logs/HERMES_LOG.md:

    ## Quota Event -- <timestamp>
    Agent: Claude / Codex / OpenClaw
    Session: <tmux session name>
    Message: <exact quota/rate-limit message>
    Reset time: <if shown>
    Current task: <task ID and description>
    Last useful output: <summary>
    Tasks migrated: <list or none>
    Action taken: <what Hermes did>
    Follow-up prepared: <next prompt or task ID>

---

## 8. Productive waiting rule

During quota waits, Hermes must produce at least one of:

    updated audit file (.rework/ audit files)
    updated task queue
    updated STATUS.md
    focused resume prompt for Claude
    focused resume prompt for Codex
    focused review prompt for OpenClaw
    classification of obsolete terminology hits
    analysis of failing tests or command outputs
    Makefile review
    README or CLAUDE.md review
    .claude/ review
    IEEE paper review or checklist update
