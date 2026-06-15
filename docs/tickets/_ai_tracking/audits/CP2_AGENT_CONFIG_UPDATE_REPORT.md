# CP2 Agent Configuration Update Report

**Date:** 2026-06-15
**Task:** Align `.claude`, `CLAUDE.md`, and `.github` with the CP2 ticket workflow
**Audit input:** `CP2_AGENT_CONFIG_AUDIT.md`
**Result:** COMPLETE — all targeted files updated; validation completed with known pre-existing Ruff E501 warnings (unrelated to this documentation-only update); no new blocking issues introduced.

---

## 1. Files Inspected

| File | Disposition |
|---|---|
| `.github/copilot-instructions.md` | **Updated** — CP2 active section prepended |
| `.claude/settings.json` | **Updated** — added `Bash(graphify:*)` permission |
| `.claude/settings.local.json` | Left unchanged (unrelated telegram permissions) |
| `.claude/agents/orchestrator-agent.md` | **Updated** — CP2 active context block appended |
| `.claude/agents/scientific-contract-agent.md` | **Updated** — CP2 source-of-truth sources added |
| `.claude/agents/drift-enforcer-agent.md` | **Updated** — CP2 planning source corrected |
| `.claude/agents/implementation-agent.md` | **Updated** — CP2 progress paths added |
| `.claude/agents/code-quality-gate-agent.md` | **Updated** — CP2 progress paths added |
| `.claude/agents/ticket-completion-auditor-agent.md` | **Updated** — CP2 progress paths added |
| `.claude/agents/experiment-runner-agent.md` | Left unchanged (generic, CLAUDE.md overrides) |
| `.claude/agents/paper-update-agent.md` | Left unchanged (generic, CLAUDE.md overrides) |
| `.claude/agents/refactor-agent.md` | Left unchanged (generic) |
| `.claude/agents/results-audit-agent.md` | Left unchanged (generic) |
| `.claude/agents/reviewer-agent.md` | Left unchanged (generic) |
| `.claude/agents/test-agent.md` | Left unchanged (generic) |
| `.claude/agents/ticket-planner-agent.md` | Left unchanged (journal-focused by design; tickets already exist for CP2) |
| `.claude/skills/datp-invariant-check-skill.md` | **Updated** — CP2 core invariant block added; journal source updated |
| `.claude/skills/ticket-progress-skill.md` | **Updated** — CP2 file paths added; stale paths kept as DATP-journal fallback |
| `.claude/skills/ticket-completion-audit-skill.md` | Updated via ticket-completion-auditor-agent edit |
| `.claude/skills/artifact-audit-skill.md` | Left unchanged (generic) |
| `.claude/skills/experiment-gate-skill.md` | Left unchanged (generic) |
| `.claude/skills/human-intervention-gate-skill.md` | Left unchanged (generic) |
| `.claude/skills/latex-paper-skill.md` | Left unchanged (generic) |
| `.claude/skills/long-run-monitoring-skill.md` | Left unchanged (generic) |
| `.claude/skills/paper-claim-discipline-skill.md` | Left unchanged (journal refs are context, not commands) |
| `.claude/skills/refactor-clean-code-skill.md` | Left unchanged (correct for CP2) |
| `.claude/skills/results-statistics-skill.md` | Left unchanged (generic; CP2 locks in CLAUDE.md) |
| `.claude/skills/schema-enum-constant-skill.md` | Left unchanged (generic) |
| `.claude/skills/static-analysis-quality-gate-skill.md` | Left unchanged (correct for CP2) |
| `.claude/skills/test-coverage-skill.md` | Left unchanged (correct for CP2) |
| `.claude/skills/ticket-audit-skill.md` | Left unchanged (generic) |
| `.claude/skills/ticket-generation-skill.md` | Left unchanged (not needed; CP2 tickets already exist) |
| `CLAUDE.md` | **Created** — comprehensive CP2 root instruction file |

---

## 2. Files Changed

### `CLAUDE.md` (created, 236 lines)
Root CP2 instruction file. Covers:
- Source-of-truth hierarchy
- Ticket workflow
- All CP2 scientific locks (attack scope, datasets, policies, mechanics, seeds, B4, metrics, statistics, Calibration-Pending)
- Coding rules
- Test taxonomy with escalation order
- Graphify invocation
- Paper notes requirement
- Progress / decision record rules
- Hard stop rules
- DATP journal fallback paths

### `.github/copilot-instructions.md` (1980 → ~2030 lines, prepend only)
Added a prominent "CP2 ACTIVE — Read This First" section at the top with:
- CP2 file paths table
- Working rules including ticket workflow and hard stops
- CP2 scientific locks summary
- No existing content removed

### `.claude/settings.json`
Added `"Bash(graphify:*)"` to the permissions allow list.

### `.claude/agents/orchestrator-agent.md`
Appended "CP2 Active Context" section with:
- CP2 source-of-truth file paths
- Ticket workflow steps
- Greenfield rule
- Hard stops specific to this agent

### `.claude/agents/scientific-contract-agent.md`
Updated the "Required Reading" section to distinguish CP2 (active) from DATP journal (if resuming).

### `.claude/agents/drift-enforcer-agent.md`
Updated the journal-file reference to point to CP2 planning source first.

### `.claude/agents/implementation-agent.md`
Updated pre-implementation reading list and post-completion checklist to use CP2 progress/index paths.

### `.claude/agents/code-quality-gate-agent.md`
Updated required-reading list and final output section to use CP2 progress path.

### `.claude/agents/ticket-completion-auditor-agent.md`
Updated required-reading list and output section to use CP2 progress path.

### `.claude/skills/datp-invariant-check-skill.md`
- Updated "Required Inputs" to list CP2 Roadmap + README §9 first.
- Added "CP2 Core Invariants" section (12 numbered invariants covering all CP2 scientific locks).

### `.claude/skills/ticket-progress-skill.md`
Updated file paths throughout to use CP2 paths; stale DATP-journal paths kept as labelled fallback.

---

## 3. Stale Instructions Removed or Corrected

- Stale `docs/tickets/ticket_inventory.md` / `ticket_progress.md` / `human_interventions.md` paths → replaced with CP2 equivalents in all updated files.
- `docs/journal/*.md` as primary CP2 source → labelled as DATP-journal fallback, not CP2 active.
- Graphify "not available" assumption → corrected to AVAILABLE in CLAUDE.md and copilot-instructions.md.
- No file was deleted; stale content was labelled and contextualized.

---

## 4. Journal-Scope Contamination

- **No CP2-scope contamination was introduced** by these edits.
- Existing mentions of `FedProx`, `Ditto`, `B-FedStatsBenign`, `Edge-IIoTset` in agent/skill files are in "do-not-do / forbid" context — correct.
- `ticket-planner-agent.md` retains journal references — appropriate (that agent's job is journal planning, not CP2; CP2 tickets are already created).
- `CLAUDE.md` explicitly forbids journal-scope creep into CP2.

---

## 5. Graphify Status

- Graphify: **AVAILABLE** (graphifyy==0.8.39).
- Historical run at the time of this update report:
  `graphify update .` → **6266 nodes, 15607 edges, 407 communities**
  (37 new nodes from the new docs).
- Phase 00 later refreshed Graphify after sidecar cleanup:
  **6331 nodes, 15668 edges, 397 communities**. See
  `CP2_GRAPHIFY_STATUS.md`.

---

## 6. Validation Commands Run

| Command | Result |
|---|---|
| `rg -n "Edge-IIoTset\|...\|shift_magnitude" .claude CLAUDE.md` | All matches are in "forbid/do-not-do" context — clean |
| `rg -n "docs/tickets\|DATP_CP_Roadmap\|Graphify\|CP2_PROGRESS\|TICKET_INDEX" CLAUDE.md .github .claude/agents/orchestrator-agent.md .claude/agents/implementation-agent.md` | Historical command included a now-missing `implementation-agent.md`; CP2 paths were present in available files |
| `grep graphify .claude/settings.json` | `Bash(graphify:*)` present |
| `python -m ruff check src/datp --select E,F --quiet` | Historical run found pre-existing E501 issues; Phase 00 re-run found 342 E501 + 1 F401 across source files, unrelated to this documentation/config update |
| `pyright src/datp/attacks src/datp/core src/datp/config` | **0 errors, 0 warnings, 0 informations** |
| `graphify update .` | Historical: 6266 nodes, 15607 edges, 407 communities; Phase 00 refresh after sidecar cleanup: 6331 nodes, 15668 edges, 397 communities |

---

## 7. Remaining Risks

| Risk | Status |
|---|---|
| `ticket-planner-agent.md` still references `docs/journal/*.md` | Accepted — that agent is not used for CP2 (CP2 tickets already exist) |
| Several skills reference `ticket_progress.md` / `ticket_inventory.md` | Accepted — these are labelled as DATP-journal fallback; CP2 paths added |
| No `.github/workflows/` created | Deferred per §11 — no clear lightweight target that doesn't risk running experiments |
| `paper-claim-discipline-skill.md` still has journal context | Accepted — core claim-discipline content is correct; journal framing doesn't mislead CP2 claim audits |

---

## 8. Next Recommended Ticket

**CP2-T000** — Ticket System Bootstrap

This is the first ticket in Phase 00 Setup. It bootstraps the ticket system itself
(verifies the ticket program is sound, checks structure, confirms tracking files),
and is a prerequisite for all subsequent tickets. It has no dependencies.

---

## 9. Phase 00 Verification Addendum

**Date:** 2026-06-15
**Context:** CP2-T003 re-verification during Phase 00 execution.

Corrections to the historical update report:

- `.claude/agents/implementation-agent.md` is referenced in the audit/update
  narrative but is not present in the current repository tree. CP2 guidance is
  still covered by `CLAUDE.md`, `.github/copilot-instructions.md`, and the
  available relevant agents/skills.
- Graphify was refreshed after this report. Current graph:
  6331 nodes, 15668 edges, 397 communities, built from commit `27c1dc31`.
- The Ruff `E,F` check currently reports 343 pre-existing diagnostics:
  342 `E501` line-length findings and one `F401` unused import in
  `src/datp/experiments/calibration_poisoning.py`. These are not caused by
  Phase 00 documentation/config work.
- Additional stale CP2 routing lines were corrected in
  `.github/copilot-instructions.md`,
  `.claude/agents/orchestrator-agent.md`, and
  `.claude/skills/ticket-progress-skill.md`.

Updated verdict: CP2-T003 remains **done, verified with discrepancy recorded**.
