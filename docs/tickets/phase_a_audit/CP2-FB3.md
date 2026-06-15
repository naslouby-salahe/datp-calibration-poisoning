# CP2-FB3 — Fallback: B4 Procedure Not Reproducible

**Phase:** A — Read-only audit (fallback)
**Type:** scientific-drift (conditional)
**Priority:** high
**Status:** not started (CONDITIONAL — do NOT activate without trigger)
**Dependencies:** CP2-T011
**Blocks:** —
**Expected test level:** unit, integration
**Graphify required:** conditional
**Paper notes required:** yes

## 1. Purpose
**CONDITIONAL.** Activate only if CP2-T011 shows the frozen B4 procedure cannot be
reproduced from artifacts (per-seed assignments/effective thresholds don't match, or
summary B4 metrics diverge). Downgrades or drops B4 cleanly.

## 2. Pre-start audit
Read CP2-T011 conformance note and `docs/DATP_CP_Roadmap.md` §13 FB3. The cross-seed
ARI (mean 0.79, range [0.64,1.0]) is a stability descriptor, NOT the pass/fail
criterion. Confirm trigger and record in `CP2_DECISION_LOG.md`.

## 3. Scope (only if triggered)
- Downgrade B4 to a secondary diagnostic; if still unstable, drop B4 and run
  **B1 vs B2 only**.
- Update enums/config/plan so B4 is not a primary policy when downgraded.
- Update paper notes and the policy set accordingly.

## 4. Non-goals
- Do not invent a new clustering method.
- Do not change B1/B2 semantics.

## 5. Scientific locks
B4 spec is frozen (K=3, fingerprint order, random_state=42); if it cannot be
reproduced, it is demoted, not modified. Primary contrast falls back to B1 vs B2.

## 6. Coding locks
Typed config flag for B4 role; no wrappers; centralized policy set.

## 7. Implementation guidance
Adjust the CP2 policy enum/config usage (Phase B/C tickets) to treat B4 as secondary
or absent; keep client-indexed delta logic if B4 stays as diagnostic.

## 8. Tests and diagnostics
```text
pytest tests/unit/thresholding/strategies/test_b4_cluster.py -q
```

## 9. Graphify
Optional; record deferral.

## 10. Paper-writing notes
Safe wording: "B4 results are reported as a secondary diagnostic; the primary policy
contrast is B1 vs B2."

## 11. Acceptance criteria
- B4 role decision recorded with evidence; plan/enums/config updated consistently.

## 12. Blocking conditions
If demotion still leaves scientific ambiguity, write a decision record.

## 13. Tracking update
Update Phase-A confirmation #3; log fallback activation.

## 14. Completion evidence
Decision record, updated policy set, tests, paper-notes entry, progress update.
