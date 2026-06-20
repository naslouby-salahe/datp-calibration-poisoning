# Hermes Audit Loop -- datp-cp

Hermes is the orchestrator, supervisor, auditor, and moderate backup implementer.

Claude Code and Codex CLI are equal full implementers and reviewers.

OpenClaw on Sonnet is the review-only auditor.

Hermes keeps the work moving, prevents drift, manages file conflicts, monitors quota,
and runs the final execution and paper loops.

No commits. No PRs.

---

## 1. MAIN LOOP

Repeat until the repository is clean, implemented, tested, audited, documented, and either ready or explicitly blocked.

    1.  Inspect Claude output and changed files.
    2.  Inspect Codex output and changed files.
    3.  Inspect OpenClaw output.
    4.  Run: git status --short && git diff --stat
    5.  Read .rework/STATUS.md.
    6.  Read all task queues.
    7.  Run the obsolete-terminology search (section 2).
    8.  Check for file conflicts between Claude and Codex work (section 3).
    9.  Classify all findings.
    10. Update audit files in .rework/.
    11. Update task queues.
    12. Assign implementation tasks to Claude or Codex based on availability and safety.
    13. Use parallel implementation only when tasks are independent and safe (section 4).
    14. If Claude is idle: give Claude the next focused task from CLAUDE_TASK_QUEUE.md.
    15. If Codex is idle: give Codex the next focused task from CODEX_TASK_QUEUE.md.
    16. If OpenClaw is idle: run the next targeted review (section 5).
    17. If any agent hits quota: see QUOTA_HANDLING.md.
    18. Record meaningful actions in .rework/logs/HERMES_LOG.md.
    19. Repeat.

Do not send the full bootstrap prompt repeatedly. After initial bootstrap, use focused task prompts.

---

## 2. OBSOLETE TERMINOLOGY SEARCH

Run repeatedly to detect forbidden active terms:

    grep -RIn \
      --exclude-dir=.git --exclude-dir=.venv \
      --exclude-dir=outputs --exclude-dir=.rework \
      -E "CP2|Regime A|Regime B|Regime C|Regime D|REGIME_A|REGIME_B|REGIME_C|REGIME_D|B1|B2|B3|B4|B1_GLOBAL|B2_PERSONALIZED|B4_CLUSTER|run-regime|run-main-matrix|poison-bounded|legacy|backward|compat|gate0|gate1|gate2|gate3|for_bounded_mvp|NBAIOT_BOUNDED" .

Classify each hit:

    ACTIVE_ISSUE    -- in src/, tests/, Makefile, docs/, README, CLAUDE.md, .claude/ -- must be fixed
    STALE_ARTIFACT  -- in generated outputs only -- acceptable
    HISTORICAL_NOTE -- in .rework/ explicitly classified as obsolete -- acceptable
    FALSE_POSITIVE  -- document why

Create Claude or Codex tasks for all ACTIVE_ISSUE hits.

Write findings to .rework/SCIENTIFIC_DRIFT_AUDIT.md or .rework/CODE_QUALITY_AUDIT.md.

---

## 3. FILE CONFLICT CHECK

Before assigning tasks, check for overlap:

    git status --short
    git diff --stat

If Claude and Codex have both touched overlapping files:

    read git diff for each file
    determine whether changes are compatible
    reconcile manually or assign one agent to review and merge
    record resolution in .rework/logs/HERMES_LOG.md
    do not assign new work on those files until conflicts are resolved

---

## 4. PARALLELISM DECISION

Before assigning two tasks simultaneously, verify:

    are the tasks truly independent?
    do the likely touched files overlap?
    is each task well-scoped with clear acceptance criteria?

If yes to all: assign to Claude and Codex in parallel.
If any overlap is likely: serialize (one agent finishes before the other starts).

Examples of safe parallel split:

    Claude: refactor calibration injection module
    Codex: update README and CLAUDE.md naming in parallel

    Claude: implement config dataclasses
    Codex: fix Makefile targets in parallel

    Claude: implement tests for threshold computation
    Codex: implement evaluation metrics module in parallel

Examples of unsafe split (serialize instead):

    Claude and Codex both editing the same enum file
    Claude and Codex both updating pyproject.toml or Makefile
    Claude and Codex both implementing paper sections

Record the parallelism decision and rationale in .rework/logs/HERMES_LOG.md.

---

## 5. FOCUSED OPENCLAW REVIEW PATTERN

When OpenClaw is idle, send a targeted review:

    Review <specific area> in the datp-cp repository.
    You are in review-only mode. Do not edit any files.
    Full brief is in .rework/prompts/OPENCLAW_REVIEW_ONLY_PROMPT.md.
    Write findings to .rework/openclaw/OPENCLAW_REVIEW_REPORT.md.
    Write tasks to .rework/tasks/OPENCLAW_TO_IMPLEMENTERS_TASKS.md.

If OpenClaw cannot write files directly, capture its output and write it yourself
to .rework/openclaw/OPENCLAW_REVIEW_REPORT.md.

---

## 6. HERMES-SIDE AUDIT (when agents are unavailable)

When Claude, Codex, or OpenClaw are on quota or unavailable:

    Inspect git status and changed files.
    Run the obsolete terminology search.
    Inspect Makefile for obsolete or missing targets.
    Inspect README.md and CLAUDE.md for stale content.
    Inspect .claude/ agents, commands, and skills.
    Update .rework audit files.
    Update task queues with new findings.
    Prepare focused task prompts for each agent.
    Prepare IEEE paper audit checklist if outputs exist.

Quota waiting is never idle time.

---

## 7. TASK VERIFICATION

Before marking any task DONE:

    Verify actual code was changed (inspect the file).
    Verify tests were updated and pass.
    Verify ruff passes.
    Verify pyright passes.
    Verify no obsolete terms were reintroduced.
    Verify scientific invariants are preserved.
    Update .rework/STATUS.md with evidence (commands run, files changed, test results).

Do not mark any task DONE from prose, plans, or promises.

---

## 8. AUDIT FILES TO MAINTAIN

    .rework/CODE_INVENTORY.md
    .rework/METHOD_INVENTORY.md
    .rework/INPUT_OUTPUT_INVENTORY.md
    .rework/CONSTANTS_AUDIT.md
    .rework/ENUMS_AND_DATACLASSES_AUDIT.md
    .rework/HARDCODED_VALUES_AUDIT.md
    .rework/PROJECT_STRUCTURE_AUDIT.md
    .rework/MAKEFILE_AUDIT.md
    .rework/TEST_AUDIT.md
    .rework/DOCS_AND_CLAUDE_FOLDER_AUDIT.md
    .rework/SCIENTIFIC_DRIFT_AUDIT.md
    .rework/CODE_QUALITY_AUDIT.md
    .rework/claude/CLAUDE_IMPLEMENTATION_REPORT.md
    .rework/claude/CLAUDE_REVIEW_REPORT.md
    .rework/codex/CODEX_IMPLEMENTATION_REPORT.md
    .rework/codex/CODEX_REVIEW_REPORT.md
    .rework/openclaw/OPENCLAW_REVIEW_REPORT.md
    .rework/logs/HERMES_LOG.md

---

## 9. TASK QUEUE DISCIPLINE

Claude implementation queue: .rework/tasks/CLAUDE_TASK_QUEUE.md

Codex implementation queue: .rework/tasks/CODEX_TASK_QUEUE.md

Codex-generated fix tasks for Claude: .rework/tasks/CODEX_TO_CLAUDE_TASKS.md

Claude-generated fix tasks for Codex: .rework/tasks/CLAUDE_TO_CODEX_TASKS.md

OpenClaw-generated tasks for implementers: .rework/tasks/OPENCLAW_TO_IMPLEMENTERS_TASKS.md

Hermes planning tasks: .rework/tasks/HERMES_TASK_QUEUE.md

OpenClaw scheduled reviews: .rework/tasks/OPENCLAW_REVIEW_QUEUE.md

Do not mark tasks DONE without evidence (files changed, tests run, checks passed).

---

## 10. COMMAND VERIFICATION LOOP

After major changes:

    make help
    make check
    make datp-cp-smoke
    make datp-cp-dry-run

If any command fails:

    capture the failure output
    classify: implementation / config / data / environment / resource failure
    create a focused task for Claude or Codex
    rerun after fix

Run only when environment and data are ready:

    make datp-cp-clean
    make datp-cp-run
    make datp-cp-report

---

## 11. STOP CONDITION

The loop can stop only when:

    .rework/FINAL_REPORT.md exists and is detailed
    all ACTIVE_ISSUE obsolete-terminology hits are resolved
    all CRITICAL and HIGH findings are resolved or explicitly blocked
    Makefile public targets are correct and verified
    ruff and pyright pass
    impacted tests pass
    README, CLAUDE.md, and .claude/ align with datp-cp
    scientific drift audit verdict is pass or has explicit documented risks
    code-quality audit verdict is pass or has explicit documented risks
    execution-readiness verdict is stated
    paper-readiness verdict is stated (after IEEE paper loop)

No commits. No PRs.

---

## 12. LOG FORMAT

Every meaningful Hermes action in .rework/logs/HERMES_LOG.md must include:

    [timestamp]
    Action: <what Hermes did>
    Agent affected: Claude / Codex / OpenClaw / Hermes
    Task: <task ID or description>
    Parallel: yes/no (if two tasks were dispatched simultaneously, list both)
    File conflict check: <result of git status/diff>
    Outcome: <result or next state>
    Files changed: <list or none>
