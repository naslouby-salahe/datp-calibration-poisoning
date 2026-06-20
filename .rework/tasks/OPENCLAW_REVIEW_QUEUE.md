# OpenClaw Review Queue — datp-cp

Scheduled OpenClaw review sessions.

OpenClaw is review-only. It must not edit source files, apply patches, commit, or create PRs.

Full review brief: `.rework/prompts/OPENCLAW_REVIEW_ONLY_PROMPT.md`

Output destination: `.rework/openclaw/OPENCLAW_REVIEW_REPORT.md`

Task output destination: `.rework/tasks/OPENCLAW_TO_IMPLEMENTERS_TASKS.md`

---

## TODO

### OPENCLAW-REVIEW-001 — Initial full repository review
Owner: OpenClaw
Type: audit
Severity: CRITICAL
Scope: full repository
Instructions:
  1. Read .rework/prompts/OPENCLAW_REVIEW_ONLY_PROMPT.md for full brief.
  2. Review all areas: roadmap alignment, code quality, enum/dataclass discipline,
     type safety, hardcoded values, scientific drift, Makefile, tests, docs, .claude/.
  3. Write findings to .rework/openclaw/OPENCLAW_REVIEW_REPORT.md.
  4. Write implementation tasks to .rework/tasks/OPENCLAW_TO_IMPLEMENTERS_TASKS.md.
  5. Do NOT edit any source files.
Status: TODO

### OPENCLAW-REVIEW-002 — Post-implementation review
Owner: OpenClaw
Type: audit
Severity: HIGH
Scope: changed files after Claude's first implementation pass
Instructions:
  1. Review all files changed by Claude since the initial review.
  2. Verify all OPENCLAW-TASK-* items from review 001 are resolved.
  3. Check for regressions or new issues.
  4. Write updated findings to .rework/openclaw/OPENCLAW_REVIEW_REPORT.md (append).
  5. Write new tasks if needed to .rework/tasks/OPENCLAW_TO_IMPLEMENTERS_TASKS.md.
  6. Do NOT edit any source files.
Status: TODO

### OPENCLAW-REVIEW-003 — Paper review
Owner: OpenClaw
Type: paper-audit
Severity: HIGH
Scope: IEEE paper draft
Instructions:
  1. Read .rework/prompts/IEEE_PAPER_LOOP.md for full paper audit checklist.
  2. Review paper draft for scientific accuracy, claim discipline, terminology, and IEEE format.
  3. Write findings to .rework/openclaw/OPENCLAW_REVIEW_REPORT.md (append under "Paper Review").
  4. Write paper tasks to .rework/tasks/OPENCLAW_TO_IMPLEMENTERS_TASKS.md.
  5. Do NOT edit the paper.
Status: TODO

---

## IN_PROGRESS

---

## DONE

---

## BLOCKED
