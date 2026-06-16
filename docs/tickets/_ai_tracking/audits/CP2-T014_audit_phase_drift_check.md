# CP2-T014 — Audit-Phase Scientific Drift Check

**Date:** 2026-06-16
**Ticket:** CP2-T014
**Auditor:** Phase-A read-only audit
**Verdict:** NO DRIFT. All audit conclusions consistent with CP2 protocol.

---

## 1. Method

```bash
rg -ni "edge-?iiot|fedprox|ditto|laridi|E=5|shift_magnitude|B3" docs/tickets _ai_tracking 2>/dev/null
```

Cross-referenced: `docs/DATP_CP_Roadmap.md`, `CP2_PHASE_A_SUMMARY.md`,
all Phase-A audit notes (T007–T013).

---

## 2. Drift scan results

| Term | Hits in audit outputs | Context | Status |
|---|---|---|---|
| `E=5` | T007 audit (multiple) | Flagging forbidden `local_epochs: 5` config; audit correct | PASS — prohibition context |
| `B3` | T000 scaffold, T011 audit | Prohibition/exclusion references; "B3 NOT in default enum" | PASS — exclusion context |
| `FB3` | T011 audit, T014, T015 tickets | "FB3 NOT TRIGGERED" verdict and conditional trigger references | PASS — correct conclusion |
| `shift_magnitude` | T010 audit | "QUARANTINE" prototype; documenting the wrong prototype field | PASS — prohibition context |
| `edge-?iiot` | 0 hits in audit notes | — | PASS |
| `fedprox` | 0 hits in audit notes | — | PASS |
| `ditto` | 0 hits in audit notes | — | PASS |
| `laridi` | 0 hits in audit notes | — | PASS |

---

## 3. Protocol-lock drift checks

### 3.1 Calibration-channel-only

**PASS.** All audit notes correctly scope CP2 to calibration-channel poisoning.
No audit note proposes or enables training/model-weight/aggregation/test poisoning.
The attack prototype (T010) is quarantined; its replacement (T027) is correctly
scoped to `REPLACE_FIXED_BUDGET` on the calibration set only.

### 3.2 E=1 / reject E=5

**PASS.** T007 correctly flags `local_epochs: 5` as forbidden and records FB1
trigger. No audit note proposes using E=5 artifacts. Phase B fix is correctly
identified (T017/T022).

### 3.3 B1/B2/B4 default policies; B3 excluded

**PASS.** T011 confirms B1/B2/B4 infrastructure. No audit note includes B3 in
any default policy enum proposal. T016 plan correctly targets
`ThresholdPolicy = {B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER}` without B3.

### 3.4 No journal contamination

**PASS.** T009 confirmed zero forbidden comparators in src/tests. T013 summary
correctly maps `conformal_threshold` as "substrate — isolate" (not for CP2 use)
and B3 as "substrate — do not remove" (for DATP; excluded from CP2 enum).

### 3.5 No broad claims introduced

**PASS.** Paper notes (T002, T007, T008, T011, T012) consistently frame CP2 as
calibration-channel only, with explicit do-not-claim lists for privacy/DP,
deployment, broad FL robustness, generic poisoning, evasion/backdoor.

### 3.6 SeedSequence (no integer addition)

**PASS.** T010 correctly identifies integer seed (`config.seed: int = 0`) as a
gap and maps it to T017/T019 (`SeedSequence([training_seed, poisoning_seed,
client_id, scope_id])`). No audit note proposes integer seed addition.

### 3.7 B4 conformance conclusions

**PASS.** T011 confirms B4 matches the locked spec (K=3, n_init=10, random_state=42,
fingerprint [mean,std,skew,p95], client-indexed thresholds). The two hardening notes
(explicit init/max_iter, decomposition) are correctly deferred to T031 without
weakening the spec conclusion.

### 3.8 Two-layer statistical unit

**PASS.** T012 correctly identifies that the 9×5=45 pattern is NOT valid and maps
the seed-level aggregate + paired comparison to T035. No audit note treats 45
samples as independent.

### 3.9 CV(FPR) = σ/µ no ε

**PASS.** T012 confirms the `cv.py` implementation returns `nan` (not ε) for
near-zero mean — consistent with the spec.

### 3.10 Reservoir rules (test/training not a reservoir)

**PASS.** T008 explicitly confirms test scores and training scores are excluded from
reservoirs. Source-precedence rule 2 correctly documented.

---

## 4. Verdict

**NO DRIFT.** The Phase-A audit correctly identifies:
- What is reusable (B1/B2/B4 thresholding, scoring infrastructure, stats, dispersion)
- What needs building (enums, config fix, injector, reservoir, metrics, sign test, Holm)
- What is quarantined (4 prototype files)
- Where FB1 is triggered (artifacts absent + E=5 config)
- Where FB3 is NOT triggered (B4 confirmed)

All decisions are traceable to evidence and map to specific Phase-B/C tickets. No
CP2 protocol lock is weakened by any audit conclusion.

---

## 5. Paper-notes refresh

**Do-not-claim reminders (carried from Phase-A):**
- No E=1 artifact claim until FB1 completes
- No B3 in any default policy
- No conformal threshold in any CP2 policy path
- No Wilcoxon/Holm as primary tests
- No 45-sample independence claim
- No broad FL robustness, generic poisoning, or privacy/deployment claims

---

## 6. Evidence Paths

- All T007–T013 audit notes in `_ai_tracking/audits/`
- `_ai_tracking/audits/CP2_PHASE_A_SUMMARY.md`
- `docs/DATP_CP_Roadmap.md` (cross-reference)
