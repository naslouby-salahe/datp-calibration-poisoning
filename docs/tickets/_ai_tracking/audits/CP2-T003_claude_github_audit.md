# CP2-T003 — .claude / skills / .github Audit and Update

**Date:** 2026-06-15
**Ticket:** CP2-T003 (config/docs edits, additive)
**Verdict:** all `.claude/agents/*` and `.claude/skills/*` now carry a concise CP2
alignment block; `.github/copilot-instructions.md` already CP2-aligned; no
automation broken; no journal scope imported.

---

## 1. Pre-edit state

- `.github/` contains only `copilot-instructions.md` (already has a large "CP2
  ACTIVE" section — 52 CP2 references). **No** workflows, PR templates, or issue
  templates exist.
- `.claude/settings.json`: tool allowlist (python, pytest, ruff via uv, graphify,
  vulture, refurb, semgrep, etc.); env `HYDRA_FULL_ERROR=1`,
  `RAY_memory_usage_threshold=0.90`. CP2-safe, no edit needed.
- `.claude/settings.local.json`: Telegram-channel permissions only. Unrelated to
  CP2 science; left unchanged.
- 9 agents already referenced CP2 (orchestrator, implementation, drift-enforcer,
  scientific-contract, code-quality-gate, ticket-planner, ticket-completion-
  auditor, experiment-runner, plus partial). **5 agents** and **10 skills** had no
  CP2 reference.

## 2. Edits applied (additive, reversible)

Inserted a uniform, concise **CP2 alignment block** immediately after the H1 title
of the 15 files that lacked one:

```
agents:  paper-update, refactor, results-audit, reviewer, test
skills:  artifact-audit, experiment-gate, latex-paper, long-run-monitoring,
         paper-claim-discipline, refactor-clean-code, results-statistics,
         schema-enum-constant, static-analysis-quality-gate, test-coverage
```

The block is **centralized by reference** (points to `CLAUDE.md`,
`docs/tickets/README.md` §9, `TICKET_INDEX.md`, `CP2_PROGRESS.md`,
`CP2_PAPER_NOTES_CONSOLIDATED.md`) rather than duplicating full lock text, and
states: calibration-channel-only scope, no-backward-compat, Graphify rule, test
taxonomy (unit→integration→e2e), paper-notes requirement, the forbidden-scope
list, and default policies `{B1, B2, B4}` with **B3 excluded**. The
paper-claim-discipline skill additionally carries the do-not-claim list.

Verification: `for f in .claude/agents/*.md .claude/skills/*.md; do rg -qi CP2 …`
returns **no** uncovered files.

## 3. Removed / obsolete content

No journal-only instruction was found that is *unsafe* for CP2 (the existing
agents reference DATP science generically and the active CP2 docs override). No
deletions were required. Nothing risky was guessed — edits are purely additive
markdown.

## 4. CI note (non-gating, deferred)

No `.github/workflows/` exists. A lightweight lint/typecheck CI could be added
later, but per CP2 rules **no experiment CI** and no heavy CI is added now. This is
recorded as a non-gating, optional follow-up — not a Phase 00 deliverable.

## 5. Tooling sanity (no code changed)

`python -m ruff check src/datp --select E,F` reports **343 pre-existing errors** in
`src/` — these are **not** introduced by this ticket (Phase 00 touched only docs/
config). Code-quality cleanup belongs to Phase A/B/C, not Phase 00. Recorded as a
known pre-existing condition.

## 6. Outcome

Acceptance met: agent/skill/instruction files reference CP2 locks and the ticket
workflow; no useful automation broken; no risky change made.
