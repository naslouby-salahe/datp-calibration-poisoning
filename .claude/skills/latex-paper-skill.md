# latex-paper-skill

> **CP2 active.** This repo is executing the CP2 program — **calibration-channel
> poisoning only**. Locks: `CLAUDE.md` + `docs/tickets/README.md` §9. Workflow:
> `docs/tickets/TICKET_INDEX.md`; progress in
> `docs/tickets/_ai_tracking/progress/CP2_PROGRESS.md`. No backward compatibility
> by default. Run `graphify update .` where applicable. Tests: unit → integration
> → e2e (`tests/`). Manuscript evidence →
> `docs/tickets/_ai_tracking/paper_notes/CP2_PAPER_NOTES_CONSOLIDATED.md`.
> Forbidden: training/model/aggregation/test-data poisoning, Edge-IIoTset,
> FedProx/Ditto/FedRep/FedPer/Laridi/B-FedStatsBenign, conformal/temporal
> recalibration, journal-extension scope. Default policies
> `{B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER}` — B3 excluded.

## Purpose

Update LaTeX paper files safely and minimally.

## Rules

1. Preserve page budget.
2. Preserve figure and table consistency.
3. Avoid bloated text.
4. Avoid generic filler.
5. Keep claims evidence-bound.
6. Keep labels stable unless required.
7. Keep captions accurate.
8. Keep references clean.
9. Do not change scientific meaning casually.
10. Rebuild only when needed.

## Required Checks

1. Abstract claim scope
2. Introduction contribution scope
3. Methods consistency
4. Results consistency
5. Threats and limitations honesty
6. Table alignment
7. Figure caption accuracy
8. Reference validity
9. Page budget
10. Overclaim risk

## Required Output

1. Files changed
2. Sections changed
3. Claims changed
4. Layout risk
5. Required follow-up