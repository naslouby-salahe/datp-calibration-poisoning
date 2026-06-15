# CP2 Progress Tracker

**Project:** CP2 — Calibration-Channel Poisoning of Federated Threshold Personalization
**Protocol of record:** `docs/DATP_CP_Roadmap.md`
**Ticket index:** `docs/tickets/TICKET_INDEX.md`

> **Do not trust this progress file alone.** Inspect the actual code, configs,
> tests, manifests, outputs, `Additional_Docs/`, `docs/DATP_CP_Roadmap.md`, and
> prior audit evidence before starting any ticket. If this file contradicts the
> repository, the repository wins — record the contradiction here and continue.

---

## How to update this file

After each ticket touch, append an entry under **Activity Log** with:

```
date | ticket id | status change | commands run | files changed | evidence path | next action
```

Statuses: `not started` | `in progress` | `blocked` | `needs reaudit` | `done`.
A ticket is `done` only with verified code + test + static-check + (where relevant)
scientific-contract evidence, plus a re-audit. Otherwise use `needs reaudit`.

---

## Phase status summary

| Phase | Folder | Tickets | Status |
|---|---|---|---|
| 00 Setup | `phase_00_setup/` | CP2-T000 … CP2-T006 | in progress (T003, T004 done; T000–T002, T005–T006 not started) |
| A Audit | `phase_a_audit/` | CP2-T007 … CP2-T015 (+FB1, FB3) | not started |
| B Protocol lock | `phase_b_protocol_lock/` | CP2-T016 … CP2-T023 | not started |
| C Core impl | `phase_c_core_implementation/` | CP2-T024 … CP2-T037 (+FB2) | not started |
| D Smoke | `phase_d_smoke_validation/` | CP2-T038 … CP2-T041 | not started |
| E MVP | `phase_e_mvp/` | CP2-T042 … CP2-T049 | not started |
| F Full (optional) | `phase_f_full_optional/` | CP2-T050 … CP2-T055 (+FB4) | not started |
| G Experiment & paper | `phase_g_experiment_and_paper/` | CP2-T056 … CP2-T058 | not started |

---

## Open blockers / decisions

See `docs/tickets/_ai_tracking/decisions/CP2_DECISION_LOG.md`. None recorded yet.

---

## Phase-A confirmations (gate the Phase-B protocol lock)

| # | Confirmation | Status | Evidence |
|---|---|---|---|
| 1 | Clean score artifacts produced under **E=1** (else FB1) | unknown | — |
| 2 | DATP bootstrap variant located (else percentile default) | unknown | — |
| 3 | B4 procedural reproducibility (else FB3) | unknown | — |
| 4 | Venue deadline + backup confirmed | unknown | — |

---

## Ticket-program creation status

| Item | State |
|---|---|
| Total CP2 tickets created | **63** (59 numbered T000–T058 + 4 fallback FB1–FB4) |
| README + TICKET_INDEX | present |
| Tracking infrastructure | present (audits, decisions, diagnostics, graphify, manifests, paper_notes, progress, run_logs) |
| Initial repo audit | `_ai_tracking/audits/CP2_INITIAL_REPO_AUDIT.md` |
| Final ticket-creation audit | `_ai_tracking/audits/CP2_TICKET_CREATION_FINAL_AUDIT.md` (verdict: PASS) |
| Tickets executed | **2** — CP2-T003 (done), CP2-T004 (done); all others "not started" |
| Graphify | **AVAILABLE** — graphifyy==0.8.39 installed; initial graph: 6229 nodes, 15572 edges, 406 communities |

Verification performed: `find`/`grep`/`ls` only — confirmed 63 unique IDs, every
ticket has a Graphify section and a `Dependencies:` field, refactor + drift gates
per phase, fallbacks gated, final three = experiment → analysis → paper. No code,
tests, tools, or experiments were run.

---

## Activity Log

```
2026-06-15 | CP2-T000 | bootstrap created (ticket system, tracking, audit) | n/a | docs/tickets/** | start CP2-T001
2026-06-15 | program  | all 63 CP2 tickets created (T000–T058 + FB1–FB4); final ticket-creation audit PASS | find/grep/ls verification | docs/tickets/** | begin execution at CP2-T000
2026-06-15 | CP2-T004 | done | Graphify installed (graphifyy==0.8.39 via uv tool install); initial graph built: 6229 nodes, 15572 edges, 406 communities | graphify-out/ | CP2_GRAPHIFY_STATUS.md updated to AVAILABLE | next: CP2-T003
2026-06-15 | CP2-T003 | done | agent/config alignment done | rg + pyright + graphify update . | CLAUDE.md created; .github/copilot-instructions.md updated (CP2 section prepended); .claude/settings.json (graphify permission added); 6 agent files updated; 2 skill files updated; audit+report written in _ai_tracking/audits/ | next: begin CP2-T000
```
