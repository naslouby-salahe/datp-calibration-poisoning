# Experiment Critique Ledger

This ledger records all critiques about the experimental setup and scope that are **outside the frozen DATP-CP scientific boundary**. Each entry is classified as:

- `ROADMAP_ONLY` — could be addressed in a future paper; not addressable now
- `ACKNOWLEDGE_IN_LIMITATIONS` — should be disclosed as a limitation in §7 or §5, but no experiment change needed
- `ALREADY_SCOPED` — explicitly out of scope per CLAUDE.md / roadmap; reject firmly

**None of these should trigger paper changes beyond limitations text.**

---

## EXP-01 — Single Dataset (N-BaIoT only)

- **Sources:** AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05, AUDIT-06, AUDIT-07, AUDIT-08, AUDIT-09, AUDIT-10 (10/10)
- **Critique:** All audits note that generalizability is limited by single-dataset evaluation.
- **Classification:** `ACKNOWLEDGE_IN_LIMITATIONS`
- **Action:** Check that §7 or Discussion explicitly acknowledges N-BaIoT as the sole dataset and notes that generalizability to other federated IoT datasets is an open question. Add one sentence if missing.
- **Paper change needed:** Minimal — only if limitations section is silent on this.

---

## EXP-02 — Nine Clients Only

- **Sources:** AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-07, AUDIT-08, AUDIT-09, AUDIT-10 (8/10)
- **Critique:** Nine-device federation is small; behavior at larger federation sizes unknown.
- **Classification:** `ACKNOWLEDGE_IN_LIMITATIONS`
- **Action:** Verify §7 mentions this. Add if absent: "Our federation comprises nine physical N-BaIoT devices. Scaling behavior at larger federation sizes remains to be studied."
- **Paper change needed:** Minimal — sentence in limitations if missing.

---

## EXP-03 — No Multi-Client Collusion

- **Sources:** AUDIT-04, AUDIT-05, AUDIT-06, AUDIT-07, AUDIT-09 (5/10)
- **Critique:** Only single-client compromise evaluated; multi-client collusion could amplify effects.
- **Classification:** `ALREADY_SCOPED` + `ACKNOWLEDGE_IN_LIMITATIONS`
- **Frozen boundary:** DATP-CP is single-client compromise by design. The roadmap explicitly scopes this.
- **Action:** Verify §7/Discussion mentions single-client scope. Add: "We study the single-compromised-client setting; multi-client collusion is a natural extension."
- **Paper change needed:** One sentence in limitations if absent.

---

## EXP-04 — No Defense Baseline Evaluated

- **Sources:** AUDIT-04, AUDIT-05, AUDIT-06, AUDIT-07, AUDIT-08 (5/10)
- **Critique:** Paper does not evaluate any defense against the attack.
- **Classification:** `ALREADY_SCOPED`
- **Frozen boundary:** DATP-CP characterizes the attack surface; defense evaluation is out of scope. Adding a defense sketch to Discussion (Action A-c8058bdd1f) addresses the narrative gap without running new experiments.
- **Paper change needed:** None beyond the defense sketch paragraph (already in action register as A-c8058bdd1f, P2).

---

## EXP-05 — q=0.95 Fixed; No Sensitivity Analysis

- **Sources:** AUDIT-04, AUDIT-09, AUDIT-10 (3/10)
- **Critique:** The quantile q=0.95 for threshold computation is fixed; no sensitivity analysis shows how results vary with q.
- **Classification:** `ACKNOWLEDGE_IN_LIMITATIONS`
- **Action:** Add a sentence in §4 or §7: "We fix q=0.95 throughout; sensitivity to q is a dimension for future investigation."
- **Paper change needed:** Minimal.

---

## EXP-06 — No Additional FL Algorithms (FedProx, SCAFFOLD, FedRep)

- **Sources:** AUDIT-07, AUDIT-08 (2/10)
- **Critique:** Only FedAvg evaluated; other FL algorithms may have different vulnerability profiles.
- **Classification:** `ROADMAP_ONLY`
- **Action:** No paper change needed. Optionally add to Future Work: "Extending to FedProx and other personalized FL protocols is a natural direction."
- **Paper change needed:** Optional sentence in Future Work.

---

## EXP-07 — No Alternative Anomaly Detectors

- **Sources:** AUDIT-07, AUDIT-08 (2/10)
- **Critique:** Only autoencoder-based detection studied; isolation forest, LOF, one-class SVM untested.
- **Classification:** `ALREADY_SCOPED`
- **Frozen boundary:** The contribution is N-BaIoT + FedAvg autoencoders by design.
- **Action:** No change needed. Optionally note in Future Work.
- **Paper change needed:** None.

---

## EXP-08 — No Realistic Traffic-Level Adversary

- **Sources:** AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-07, AUDIT-08 (6/10)
- **Critique:** No adversary capable of crafting calibration-level score injections via real network traffic is demonstrated.
- **Classification:** `ACKNOWLEDGE_IN_LIMITATIONS` (overlaps with Action A-e102f26659 in P1)
- **Action:** Already addressed by A-e102f26659 (reframe score-level proxy). The limitations text should explicitly note: "We assume direct write access to the calibration buffer as a threat model; traffic-level realization of such access remains future work."
- **Paper change needed:** Covered by P1 action A-e102f26659.

---

## EXP-09 — No Temporal / Online Analysis

- **Sources:** AUDIT-08 (1/10)
- **Critique:** Attack is evaluated at a single calibration round; temporal dynamics not studied.
- **Classification:** `ROADMAP_ONLY`
- **Action:** No paper change needed.
- **Paper change needed:** None.

---

## Summary Table

| ID | Critique | Audits | Classification | Paper Change |
|----|----------|--------|----------------|--------------|
| EXP-01 | Single dataset | 10/10 | ACKNOWLEDGE_IN_LIMITATIONS | Sentence in §7 |
| EXP-02 | Nine clients | 8/10 | ACKNOWLEDGE_IN_LIMITATIONS | Sentence in §7 |
| EXP-03 | No multi-client collusion | 5/10 | ALREADY_SCOPED + ACKNOWLEDGE | Sentence in §7 |
| EXP-04 | No defense baseline | 5/10 | ALREADY_SCOPED | None (defense sketch in A-c8058bdd1f) |
| EXP-05 | q=0.95 fixed | 3/10 | ACKNOWLEDGE_IN_LIMITATIONS | Sentence in §4/§7 |
| EXP-06 | No other FL algorithms | 2/10 | ROADMAP_ONLY | Optional Future Work |
| EXP-07 | No other detectors | 2/10 | ALREADY_SCOPED | None |
| EXP-08 | No traffic-level adversary | 6/10 | ACKNOWLEDGE_IN_LIMITATIONS | Covered by A-e102f26659 |
| EXP-09 | No temporal analysis | 1/10 | ROADMAP_ONLY | None |
