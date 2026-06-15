# CP2 Progress Log

Append one row per ticket touch. Newest entries at the bottom.
Format: `date | ticket | status | commands | files | evidence | next action`.

> Do not trust this log alone — every ticket re-inspects real code, tests,
> configs, and outputs (README §3 evidence rule).

Status vocabulary: `not started`, `in progress`, `blocked`, `needs reaudit`,
`done`.

---

## Entries

| Date | Ticket | Status | Commands | Files | Evidence | Next action |
|---|---|---|---|---|---|---|
| 2026-06-15 | CP2-T000 | done | `find docs/tickets`, `ls graphify-out`, `git status`, `graphify --version` | created tracking files under `_ai_tracking/{progress,decisions}/`, `audits/CP2-T000_scaffold_audit.md` | scaffold verified; missing tracking files created (see scaffold audit) | CP2-T001 |
| 2026-06-15 | CP2-T001 | done | `rg` forbidden-terms in src, `cat` attacks/experiments prototype, `make help` | `audits/CP2_INITIAL_REPO_AUDIT.md` | prototype mismatch confirmed (attack_rate/shift_magnitude); no journal comparators in src; `conformal_threshold` substrate flag → T009/T011; B3 absent | CP2-T002 |
| 2026-06-15 | CP2-T002 | done | read `Additional_Docs/Synthesis/*`, roadmap | `audits/CP2-T002_additional_docs_alignment.md`, `paper_notes/CP2_PAPER_NOTES_CONSOLIDATED.md` | DATP→CP2 reuse map; do-not-claim list (privacy/deploy/robustness); journal boundary explicit; no contamination | CP2-T003 |
| 2026-06-15 | CP2-T003 | done | `rg CP2` coverage loop, `ruff check src --select E,F` | 15 `.claude/{agents,skills}/*.md` + `audits/CP2-T003_claude_github_audit.md` | all agents/skills now CP2-aligned (concise pointer block); copilot-instructions already aligned; 343 pre-existing src ruff errors noted (not introduced) | CP2-T004 |
| 2026-06-15 | CP2-T004 | done | `graphify update .` (refused overwrite: 6253<6331) | `graphify/CP2_GRAPHIFY_STATUS.md` | Graphify AVAILABLE 0.8.39; existing 6331-node graph retained; overwrite not forced (avoid chunk loss); fallback policy documented | CP2-T005 |
| 2026-06-15 | CP2-T005 | done | folder/index count verification, broken-link check | `audits/CP2-T005_consistency_checkpoint.md` | 59 numbered + 4 FB confirmed; all 5 tracking links resolve; lock text centralized-by-reference; no stale paths | CP2-T006 |
| 2026-06-15 | CP2-T006 | done | drift scans (B3/forbidden/over-claim/poison-scope) | `audits/CP2-T006_setup_drift_check.md`, paper-notes claim-discipline reminder | NO DRIFT; B3 exclusion-only; all forbidden terms in prohibition context; Phase A cleared | CP2-T007 (Phase A) |
