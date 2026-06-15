# long-run-monitoring-skill

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

Monitor long-running commands and experiments safely.

## Progress State

Maintain:

1. Command
2. Start time
3. Current stage
4. Completed work
5. Failed work
6. Retried work
7. Last log checked
8. Last artifact produced
9. Current risk
10. Next action

## Monitoring Checklist

1. Logs are updating
2. No repeated crash loop
3. No memory failure
4. No GPU mismatch
5. No path drift
6. No missing artifact loop
7. No invalid metric pattern
8. No baseline retraining violation
9. No unexpected overwrite
10. No silent partial success

## Failure Classification

Classify failures as:

1. Operational
2. Config
3. Data
4. Code
5. Artifact
6. Scientific

## Required Output

1. Progress summary
2. Failures detected
3. Fixes attempted
4. Reruns performed
5. Remaining risks
6. Handoff to another agent if needed