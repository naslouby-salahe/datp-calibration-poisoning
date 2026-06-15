# CP2-T000 — Ticket System Bootstrap: Scaffold Audit

**Date:** 2026-06-15
**Ticket:** CP2-T000
**Type:** structural verification (docs-only)
**Result:** scaffold present and internally consistent; missing tracking files created.

---

## 1. What was checked

- Phase folders under `docs/tickets/`.
- Tracking folders under `docs/tickets/_ai_tracking/`.
- `README.md` and `TICKET_INDEX.md` coherence (IDs unique, final three correct).
- Cross-references from README/tickets to tracking files.

Commands:

```bash
find docs/tickets -type f | sort
find docs/tickets/_ai_tracking -type d | sort
git status --short        # clean working tree at HEAD 0a5e380
graphify --version        # graphify 0.8.39
```

## 2. Phase folders — PRESENT

All eight phase folders exist and match `README.md` §1:

```
phase_00_setup/            CP2-T000 … CP2-T006
phase_a_audit/             CP2-T007 … CP2-T015 (+ CP2-FB1, CP2-FB3)
phase_b_protocol_lock/     CP2-T016 … CP2-T023
phase_c_core_implementation/  CP2-T024 … CP2-T037 (+ CP2-FB2)
phase_d_smoke_validation/  CP2-T038 … CP2-T041
phase_e_mvp/               CP2-T042 … CP2-T049
phase_f_full_optional/     CP2-T050 … CP2-T055 (+ CP2-FB4)
phase_g_experiment_and_paper/  CP2-T056 … CP2-T058
```

## 3. Index integrity — PASS

- Ticket IDs `CP2-T000 … CP2-T058` are unique (59 numbered + 4 fallbacks).
- Final three are fixed and correct: CP2-T056 (experiment), CP2-T057 (analysis),
  CP2-T058 (paper).
- Refactor checkpoints and drift checks listed in the index counts match the
  per-phase tables.

## 4. Discrepancy found and resolved

`README.md` and several tickets reference tracking files that **did not yet
exist** on disk (only `_ai_tracking/{diagnostics,manifests,run_logs}/README.md`
were present). The referenced-but-missing files were therefore broken links:

```
_ai_tracking/progress/CP2_PROGRESS.md
_ai_tracking/decisions/CP2_DECISION_LOG.md
_ai_tracking/graphify/CP2_GRAPHIFY_STATUS.md
_ai_tracking/paper_notes/CP2_PAPER_NOTES_CONSOLIDATED.md
_ai_tracking/audits/CP2_INITIAL_REPO_AUDIT.md
```

**Resolution:** these tracking files are created during Phase 00 by the tickets
that own them (T000: progress + decision log; T001: initial repo audit; T002:
alignment + paper notes; T004: graphify status). This is expected first-run
bootstrap behaviour, not a structural break of the plan. No ticket text or
production code changed for this fix.

## 5. Scientific locks (unchanged)

CP2 is calibration-channel poisoning only; default policies
`{B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER}`, **B3 not in the default enum**.
Nothing in the scaffold contradicts `docs/DATP_CP_Roadmap.md`.

## 6. Graphify

Not applicable to docs-only scaffolding (deferral). Graphify status documented in
`_ai_tracking/graphify/CP2_GRAPHIFY_STATUS.md` (CP2-T004).

## 7. Outcome

Acceptance criteria met: all phase/tracking folders exist; README and index are
consistent; IDs unique; final three correct; discrepancy recorded here.
