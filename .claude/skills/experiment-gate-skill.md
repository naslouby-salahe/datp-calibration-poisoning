# experiment-gate-skill

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

Prevent premature coding, premature experiments, and invalid phase transitions.

## Gate Checks

1. Is the current phase known?
2. Is the requested work allowed?
3. Are required files present?
4. Are scientific assumptions frozen?
5. Are configs valid?
6. Are datasets available?
7. Are tests ready?
8. Are artifacts clean?
9. Are logs configured?
10. Is failure handling defined?

## Decisions

Allowed decisions:

1. Proceed
2. Proceed with limited scope
3. Block until prerequisite is fixed
4. Stop and request scientific decision

## Required Output

1. Gate verdict
2. Blocking issues
3. Allowed scope
4. Next required action