# CP2 Paper Notes (Consolidated)

Append manuscript-relevant evidence as it is produced. Each note records:
**claim enabled / claim blocked / limitation / figure-table / reviewer-risk /
do-not-claim** with an **evidence path**. CP2-T058 consolidates and audits these.

> A claim is only writable if it is traceable to a real evidence path. Phase 00
> notes are scope/boundary reminders, not results.

---

## CP2-T002 — Additional_Docs alignment (scope & boundary seeds)

### Claims CP2 may build on (DATP conference identity, reuse)

- **DATP substrate is N-BaIoT physical-device federated AE anomaly detection**
  (Rey et al. lineage; Claims.md P003). CP2 reuses the fixed encoder, FL split, and
  per-client benign calibration scores — poisoning is the *only* added variable.
- **B1 (global) vs B2 (personalized) vs B4 (cluster) threshold policies** and
  **CV(FPR)** as the personalization-dispersion metric are DATP-owned and reused.
- Evidence path: `docs/DATP_CP_Roadmap.md`, `Additional_Docs/Synthesis/Claims.md`.

### Claims CP2 must NOT restate or make (do-not-claim list)

- **No privacy/DP claim.** Every corpus paper (P001-C4, P002-C3, P003-C7, P004-C4,
  P034-C2, P035-C4, P039-C3, P040-C3) lacks formal privacy; CP2 adds no privacy
  mechanism and must not imply one. (`Claims.md` privacy-gap pattern.)
- **No deployment / on-device / hardware-overhead claim** (P005/P036/P037/P040
  hardware gaps). CP2 runs on saved artifacts; it is not a deployment study.
- **No broad FL-robustness or generic-poisoning claim.** CP2 is *calibration-
  channel* poisoning only — never training-data, model-weight, aggregation, or
  test-data poisoning (contrast P003-C4/C5 model-poisoning, P036/P037 defenses).
- **No "first work" / novelty-supremacy overclaim.** Frame as a focused,
  policy-differentiated calibration-channel vulnerability analysis.
- **No evasion / backdoor claim.** Out of scope.

### CP2 / journal boundary (must NOT import)

Forbidden imports from `Additional_Docs/Journal/Journal_Extension_Master_Roadmap.md`
(context-only): **Edge-IIoTset**, **FedProx / Ditto / FedRep / FedPer / Laridi /
B-FedStatsBenign** comparators, **conformal thresholding**, **temporal
recalibration**. CICIoT2023 is stretch-only and FB4-gated.

### Reviewer-risk reminders (carry into analysis & paper)

- **Statistics unit:** never treat 9×5 victim-seed deltas as 45 independent
  samples; use seed-level aggregates; bootstrap CI on the 5 seed-level aggregates;
  sign test supporting only; Holm descriptive only.
- **Coverage:** always report coverage ratio alongside `CV(FPR) = σ/µ` (no ε).
- **AUROC invariance:** test scores are unchanged by calibration-channel attack →
  AUROC must be reported as invariant (sanity check, not a result).
- **B4 deltas** are client-indexed effective-threshold deltas; never compare raw
  k-means label IDs across runs.
- Evidence path: `Additional_Docs/Synthesis/Gap & Limitation Ledger.md`,
  `docs/DATP_CP_Roadmap.md` §14–§15.

---

## CP2-T006 — Claim-discipline reminder (drift gate)

**Do-not-claim (locked before any implementation/experiment):**

- Do **not** claim privacy or differential-privacy protection.
- Do **not** claim deployment, on-device, or hardware-overhead results.
- Do **not** claim broad FL robustness or generic poisoning resistance/attack.
- Do **not** claim evasion or backdoor capability.
- Do **not** claim "first work" / novelty supremacy.
- Do **not** restate DATP conference results as new CP2 contributions.

**Always pair with evidence (when results exist):** coverage ratio with every
`CV(FPR)`; AUROC reported invariant; seed-level statistics (never 9×5 = 45
independent); B4 deltas client-indexed.

Drift gate result: **no drift** at setup (see
`_ai_tracking/audits/CP2-T006_setup_drift_check.md`). Evidence path:
`docs/DATP_CP_Roadmap.md`, `Additional_Docs/Synthesis/Claims.md`.
