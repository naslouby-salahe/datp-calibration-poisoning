# CP2 Agent Configuration Audit

**Audit type:** Agent/config file inspection before CP2 workflow alignment
**Date:** 2026-06-15
**Auditor:** Copilot agent-config update task
**Source of truth:** `docs/DATP_CP_Roadmap.md`, `docs/tickets/README.md`, `docs/tickets/TICKET_INDEX.md`, audit reports

---

## 1. Files Inspected

| File | Exists | Size (lines) |
|---|---|---|
| `.github/copilot-instructions.md` | yes | 1980 |
| `.claude/settings.json` | yes | ~30 |
| `.claude/settings.local.json` | yes | ~10 |
| `.claude/agents/code-quality-gate-agent.md` | yes | 341 |
| `.claude/agents/drift-enforcer-agent.md` | yes | 254 |
| `.claude/agents/experiment-runner-agent.md` | yes | ~200 |
| `.claude/agents/implementation-agent.md` | yes | 206 |
| `.claude/agents/orchestrator-agent.md` | yes | 260 |
| `.claude/agents/paper-update-agent.md` | yes | ~200 |
| `.claude/agents/refactor-agent.md` | yes | ~200 |
| `.claude/agents/results-audit-agent.md` | yes | ~200 |
| `.claude/agents/reviewer-agent.md` | yes | ~200 |
| `.claude/agents/scientific-contract-agent.md` | yes | 220 |
| `.claude/agents/test-agent.md` | yes | ~200 |
| `.claude/agents/ticket-completion-auditor-agent.md` | yes | 216 |
| `.claude/agents/ticket-planner-agent.md` | yes | ~250 |
| `.claude/skills/artifact-audit-skill.md` | yes | — |
| `.claude/skills/datp-invariant-check-skill.md` | yes | — |
| `.claude/skills/experiment-gate-skill.md` | yes | — |
| `.claude/skills/human-intervention-gate-skill.md` | yes | — |
| `.claude/skills/latex-paper-skill.md` | yes | — |
| `.claude/skills/long-run-monitoring-skill.md` | yes | — |
| `.claude/skills/paper-claim-discipline-skill.md` | yes | — |
| `.claude/skills/refactor-clean-code-skill.md` | yes | — |
| `.claude/skills/results-statistics-skill.md` | yes | — |
| `.claude/skills/schema-enum-constant-skill.md` | yes | — |
| `.claude/skills/static-analysis-quality-gate-skill.md` | yes | — |
| `.claude/skills/test-coverage-skill.md` | yes | — |
| `.claude/skills/ticket-audit-skill.md` | yes | — |
| `.claude/skills/ticket-completion-audit-skill.md` | yes | — |
| `.claude/skills/ticket-generation-skill.md` | yes | — |
| `.claude/skills/ticket-progress-skill.md` | yes | — |
| `CLAUDE.md` | **NO** | — |
| `Claude.md` | **NO** | — |
| `claude.md` | **NO** | — |

---

## 2. Files That Are Missing

| Missing file | Action |
|---|---|
| `CLAUDE.md` | **Create** — must be the root CP2 instruction file |

---

## 3. Files That Are Obsolete / Stale for CP2

None of the existing files are obsolete in the sense of being deletable — they
serve the DATP journal workflow which may resume. However, they all contain stale
references for CP2 work.

---

## 4. Journal-Scope Contamination Found

The following files contain journal-scope references that would mislead agents
working on CP2 tickets:

| File | Stale reference |
|---|---|
| `.github/copilot-instructions.md` | `docs/journal/PRE_CODING_PLAN.md` etc. (journal 4-file plan) |
| `.github/copilot-instructions.md` | `docs/tickets/ticket_inventory.md` — stale CP2 path |
| `.github/copilot-instructions.md` | `docs/tickets/ticket_progress.md` — stale CP2 path |
| `.github/copilot-instructions.md` | legacy DATP journal human-intervention tracker — stale CP2 path |
| `.github/copilot-instructions.md` | "conference-to-journal transition" framing |
| `.github/copilot-instructions.md` | `Journal/Journal_Extension_Master_Roadmap.md` as active |
| `.claude/agents/orchestrator-agent.md` | `docs/journal/*.md`, `docs/tickets/ticket_inventory.md` / `ticket_progress.md` |
| `.claude/agents/drift-enforcer-agent.md` | `docs/journal/*.md` |
| `.claude/agents/scientific-contract-agent.md` | `docs/journal/PRE_CODING_PLAN.md` etc. as source of truth |
| `.claude/agents/ticket-planner-agent.md` | `docs/journal/*.md`, `docs/tickets/ticket_inventory.md` |
| `.claude/agents/implementation-agent.md` | `docs/tickets/ticket_inventory.md` / `ticket_progress.md` |
| `.claude/agents/experiment-runner-agent.md` | `docs/tickets/ticket_progress.md` |
| `.claude/agents/code-quality-gate-agent.md` | `docs/tickets/ticket_inventory.md` / `ticket_progress.md` |
| `.claude/agents/ticket-completion-auditor-agent.md` | `docs/tickets/ticket_inventory.md` / `ticket_progress.md` |
| `.claude/skills/datp-invariant-check-skill.md` | `docs/journal/*.md` |
| `.claude/skills/paper-claim-discipline-skill.md` | `docs/journal/*.md` |
| `.claude/skills/ticket-generation-skill.md` | `docs/journal/*.md`, old ticket progress paths |
| `.claude/skills/ticket-progress-skill.md` | `docs/tickets/ticket_progress.md` / `ticket_inventory.md` |
| `.claude/skills/ticket-completion-audit-skill.md` | old ticket paths |
| `.claude/settings.json` | **missing** `Bash(graphify:*)` permission |

---

## 5. Stale DATP-Only Assumptions

- All agents and the copilot-instructions.md assume the DATP journal 4-file plan
  (`docs/journal/*.md`) is the active planning layer. For CP2, this is **wrong**;
  CP2's protocol is `docs/DATP_CP_Roadmap.md`.
- All agents reference `docs/tickets/ticket_inventory.md` and
  `docs/tickets/ticket_progress.md` — these do not exist; the CP2 equivalents are
  `docs/tickets/TICKET_INDEX.md` and `docs/tickets/_ai_tracking/progress/CP2_PROGRESS.md`.
- Scientific-contract-agent's stop conditions reference journal-scope drift (regime
  B-a, regime C) but do not mention CP2-specific stops (calibration-channel only,
  REPLACE_FIXED_BUDGET, victim-local, E=1, SeedSequence, etc.).

---

## 6. Graphify Status in Config Files

- `.claude/settings.json`: does **not** allow `Bash(graphify:*)`.
- `.github/copilot-instructions.md`: has Graphify installation steps but references
  the old "not installed" state; does not reference `CP2_GRAPHIFY_STATUS.md` or
  the fact that Graphify is now AVAILABLE.
- Agents: none reference Graphify explicitly.
- Skills: none reference Graphify explicitly.

---

## 7. Test Taxonomy

- The copilot-instructions.md and agent files do not explicitly state the
  `tests/unit` → `tests/integration` → `tests/e2e` escalation order.
- `test-agent.md` and `code-quality-gate-agent.md` cover test quality but not the
  CP2 escalation order.

---

## 8. Paper Notes

No existing file explicitly references `CP2_PAPER_NOTES_CONSOLIDATED.md` or
instructs agents to append paper notes for CP2.

---

## 9. Files to Edit

| File | Edit type |
|---|---|
| `CLAUDE.md` | **Create** — comprehensive CP2 root guide |
| `.github/copilot-instructions.md` | **Prepend** CP2 active section (do not rewrite) |
| `.claude/settings.json` | **Add** `Bash(graphify:*)` permission |
| `.claude/agents/orchestrator-agent.md` | **Add** CP2 context block |
| `.claude/agents/scientific-contract-agent.md` | **Add** CP2 context block |
| `.claude/agents/drift-enforcer-agent.md` | **Add** CP2 context block |
| `.claude/agents/implementation-agent.md` | **Add** CP2 progress paths |
| `.claude/agents/code-quality-gate-agent.md` | **Add** CP2 progress paths |
| `.claude/agents/ticket-completion-auditor-agent.md` | **Add** CP2 progress paths |
| `.claude/skills/ticket-progress-skill.md` | **Add** CP2 file paths |
| `.claude/skills/datp-invariant-check-skill.md` | **Add** CP2 invariant block |

---

## 10. Files Left Untouched (or Intentionally Unchanged)

| File | Reason |
|---|---|
| `.claude/settings.local.json` | Telegram-channel permissions; unrelated to CP2 |
| `.claude/skills/refactor-clean-code-skill.md` | Content is correct for CP2 coding rules |
| `.claude/skills/static-analysis-quality-gate-skill.md` | Content is correct for CP2 quality gates |
| `.claude/skills/test-coverage-skill.md` | Content is correct |
| `.claude/skills/artifact-audit-skill.md` | Content is artifact-generic; not stale |
| `.claude/skills/experiment-gate-skill.md` | Content is generic; updated through CLAUDE.md |
| `.claude/skills/latex-paper-skill.md` | Content is generic paper-editing; not stale |
| `.claude/skills/long-run-monitoring-skill.md` | Content is generic |
| `.claude/skills/human-intervention-gate-skill.md` | Content is generic |
| `.claude/skills/schema-enum-constant-skill.md` | Content is generic |
| `.claude/skills/results-statistics-skill.md` | Content is generic; CP2 additions in CLAUDE.md |
| `.claude/skills/paper-claim-discipline-skill.md` | Only minor journal refs; core is correct |
| `.claude/agents/ticket-planner-agent.md` | Journal-focused by design; not needed for CP2 (tickets already exist) |
| `.claude/agents/reviewer-agent.md` | Generic; no harmful stale references |
| `.claude/agents/refactor-agent.md` | Generic; no harmful stale references |
| `.claude/agents/paper-update-agent.md` | Generic; CP2 additions in CLAUDE.md |
| `.claude/agents/results-audit-agent.md` | Generic; CP2 additions in CLAUDE.md |
| `.claude/agents/experiment-runner-agent.md` | Updated via CLAUDE.md |

---

## 11. Risky Edits Deferred

| Risk | Decision |
|---|---|
| Wholesale replacing `.github/copilot-instructions.md` | DEFERRED — would destroy valid DATP journal workflow; prepend CP2 section instead |
| Rewriting `scientific-contract-agent.md` stop conditions | DEFERRED — add CP2 block only; old stops still valid for DATP journal work |
| Deleting journal references from all agent files | DEFERRED — too risky; add CP2 context blocks instead |
| Creating `.github/workflows/` | DEFERRED — no clear lightweight target; decision recorded in update report |

---

## 12. Summary

**Critical gaps:**
1. `CLAUDE.md` does not exist.
2. No file points agents to `docs/DATP_CP_Roadmap.md` or `docs/tickets/TICKET_INDEX.md`.
3. `graphify` not in settings.json permissions.
4. All agents use stale ticket-progress paths.
5. No paper-notes instruction anywhere.

**Approach:** targeted additions (prepend / append CP2 blocks), not wholesale replacement.
