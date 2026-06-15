# artifact-audit-skill

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

Validate artifact paths, files, manifests, markers, and result layout.

## Checks

1. Canonical path used
2. Required parent directory exists
3. Required input artifact exists
4. Empty files are rejected
5. Temporary files are ignored
6. Partial files are not treated as complete
7. Manifest is valid
8. Config provenance is present
9. Failure markers are meaningful
10. Resume behavior is safe

## Required Output

1. Valid artifacts
2. Missing artifacts
3. Invalid artifacts
4. Unsafe resume risks
5. Required fixes