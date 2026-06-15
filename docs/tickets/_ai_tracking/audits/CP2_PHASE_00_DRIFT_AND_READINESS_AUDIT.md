# CP2 Phase 00 Drift and Readiness Audit

**Date:** 2026-06-15  
**Ticket:** CP2-T006  
**Scope:** Setup/planning drift check before Phase A

## Drift Audit Against `docs/DATP_CP_Roadmap.md`

### Calibration-channel-only scope

Pass. Phase 00 tickets and root instructions identify CP2 as calibration-channel
poisoning only. No ticket authorizes training-data poisoning, model poisoning,
aggregation attacks, test-data poisoning, evasion, backdoor, privacy mechanisms,
deployment claims, or hardware claims.

### Dataset and comparator scope

Pass. N-BaIoT is the primary dataset. CICIoT2023 is stretch-only and FB4-gated.
Edge-IIoTset, FedProx, Ditto, FedRep, FedPer, Laridi, and
`B-FedStatsBenign` appear only in forbidden, boundary, archived, or future-ticket
audit contexts.

### Threshold policy scope

Pass. CP2 default policy set is consistently documented as
`B1_GLOBAL`, `B2_PERSONALIZED`, and `B4_CLUSTER`. B3 is allowed only as inherited
DATP context / appendix-only and is excluded from the CP2 default enum.

### Attack mechanics

Pass at planning level. The roadmap and tickets specify `REPLACE_FIXED_BUDGET`,
victim-local benign reservoirs, with-replacement replacement, no in-place
mutation, and no test/training score reservoir. Existing prototype code still
uses `shift_magnitude`, but Phase 00 correctly treats it as stale and schedules
replacement in Phase A/C rather than silently accepting it.

### Statistics and metrics

Pass at planning level. Setup docs preserve the two-layer unit of analysis,
`CV(FPR)=sigma/mu` with no epsilon, coverage reporting, AUROC invariance, and
`mu_flag_threshold` pre-poison lock.

### Venue/deadline strategy

Pass. Phase 00 did not research, modify, or invent venue/deadline decisions.
`CP2_PROGRESS.md` still records the Phase-A venue/deadline confirmation as
unknown, which is the correct setup-state value.

## Post-Edit Consistency Audit

Files changed in Phase 00 execution:

- `docs/tickets/_ai_tracking/graphify/CP2_GRAPHIFY_STATUS.md`
- `docs/tickets/_ai_tracking/audits/CP2_PHASE_00_EXECUTION_AUDIT.md`
- `docs/tickets/_ai_tracking/audits/CP2_ADDITIONAL_DOCS_ALIGNMENT_AUDIT.md`
- `docs/tickets/_ai_tracking/audits/CP2_PHASE_00_DRIFT_AND_READINESS_AUDIT.md`
- `docs/tickets/_ai_tracking/audits/CP2_INITIAL_REPO_AUDIT.md`
- `docs/tickets/_ai_tracking/paper_notes/CP2_PAPER_NOTES_CONSOLIDATED.md`
- `docs/tickets/_ai_tracking/progress/CP2_PROGRESS.md`
- `.github/copilot-instructions.md`
- `.claude/agents/orchestrator-agent.md`
- `.claude/skills/ticket-progress-skill.md`
- `docs/tickets/phase_00_setup/CP2-T000.md`
- `docs/tickets/phase_00_setup/CP2-T001.md`
- `docs/tickets/phase_00_setup/CP2-T002.md`
- `docs/tickets/phase_00_setup/CP2-T003.md`
- `docs/tickets/phase_00_setup/CP2-T004.md`
- `docs/tickets/phase_00_setup/CP2-T005.md`
- `docs/tickets/phase_00_setup/CP2-T006.md`

No production code, experiment code, result artifacts, or venue/deadline strategy
files were changed.

Sidecar-agent findings integrated:

- Corrected stale CP2 routing lines in `.github/copilot-instructions.md`,
  `.claude/agents/orchestrator-agent.md`, and
  `.claude/skills/ticket-progress-skill.md` so CP2 points to
  `TICKET_INDEX.md`, `CP2_PROGRESS.md`, and `CP2_DECISION_LOG.md`.
- Left DATP journal fallback paths only where explicitly labelled as journal
  fallback context.

## Final Phase 00 Readiness

| Ticket | Verdict | Evidence |
|---|---|---|
| CP2-T000 | done | Ticket tree/count audit in `CP2_PHASE_00_EXECUTION_AUDIT.md` |
| CP2-T001 | done | Repository inventory refresh and `CP2_INITIAL_REPO_AUDIT.md` addendum |
| CP2-T002 | done | `CP2_ADDITIONAL_DOCS_ALIGNMENT_AUDIT.md` + paper note |
| CP2-T003 | done, verified | Agent config evidence verified; missing `implementation-agent.md` discrepancy recorded |
| CP2-T004 | done, verified | Graphify 0.8.39 refresh recorded |
| CP2-T005 | done | Setup consistency check and latest Graphify refresh: 6331 nodes, 15668 edges, 397 communities |
| CP2-T006 | done | This drift/readiness audit + paper note |

## Blockers

None for starting Phase A.

Open unknowns remain exactly as Phase-A confirmations, not Phase 00 blockers:

1. Clean score artifacts produced under E=1.
2. DATP bootstrap variant located.
3. B4 procedural reproducibility.
4. Venue deadline + backup confirmed.

## Final Decision

Phase A can start at CP2-T007.
