# CP2-T006 — [DRIFT] Scientific Drift Check: Setup & Planning Scope

**Date:** 2026-06-15
**Ticket:** CP2-T006 (first scientific-drift gate; docs-only)
**Compared:** `docs/tickets/{README.md, TICKET_INDEX.md, phase_*/}` vs
`docs/DATP_CP_Roadmap.md`, `Additional_Docs/Synthesis/{Claims.md, Gap & Limitation
Ledger.md}`.
**Verdict:** ✅ NO DRIFT. The Phase 00 plan and setup artifacts faithfully encode
the CP2 protocol. No journal contamination, no forbidden comparator/dataset, no
poisoning-scope drift, no over-claim. Phase A may begin.

---

## 1. Method

```bash
rg -ni "edge-?iiot|fedprox|ditto|fedrep|fedper|laridi|fedstatsbenign|conformal|temporal recalib|E=5|shift_magnitude" docs/tickets
rg -ni "B3 …default/included"          # must be exclusion-only
rg -ni "first work|privacy guarantee|deployment|broad robustness|generic poisoning"  # over-claims
rg -ni "poison (training|model|weight|aggregation|test)"   # scope drift
```

## 2. Findings

| Check | Result |
|---|---|
| Implementation direction matches CP2 protocol | PASS — `REPLACE_FIXED_BUDGET`, victim-local reservoirs, `{0,0.10,0.20,0.40}`, E=1, SeedSequence child seeds are the planned mechanics (T016–T035). |
| Journal contamination (Edge-IIoTset, FedProx/Ditto/FedRep/FedPer/Laridi, B-FedStatsBenign) | PASS — all hits in `docs/tickets/` are **prohibition/audit** references ("forbidden", "reject", "retire"), never an adopted feature. |
| Conformal / temporal recalibration | PASS — only appears as forbidden-scope guard text. (Substrate `conformal_threshold` flagged in CP2_INITIAL_REPO_AUDIT for T009/T011; CP2 policies must not consume it.) |
| Forbidden datasets / comparators | PASS — N-BaIoT primary; CICIoT2023 stretch-only FB4-gated; Edge-IIoTset forbidden. |
| Training / model / aggregation / test-data poisoning drift | PASS — only occurrence is README §9 "calibration-channel poisoning **only**. Never poison training data…". |
| **B3 not in any default policy enum** | PASS — every B3 mention is an exclusion ("B3 must not be in the default enum"); prototype baselines already `(B1, B2, B4)`. |
| Over-claims (privacy, deployment, generic poisoning, "first work") | PASS — only occurrence is the do-not-claim list in the T002 alignment audit. |
| E=1 artifact lock | PASS — E=5 referenced only as "reject E=5". |

## 3. Drift correction applied

None required — no drift was found in the plan or setup artifacts. No ticket text
needed correction; no decision-log hard-stop triggered.

## 4. Phase A readiness

The CP2 protocol-of-record is cleanly separated from journal-extension scope; the
setup phase introduced no contamination or weakened claim. **Phase A (read-only
scientific & code audit, CP2-T007…T015) is cleared to start** with the standing
flag from CP2-T001 to verify the substrate `conformal_threshold` is not consumed
by CP2 (CP2-T009 / CP2-T011).

## 5. Outcome

Acceptance met: drift report written; no contamination/over-claim in the plan;
claim-discipline reminder appended to `CP2_PAPER_NOTES_CONSOLIDATED.md`.
