# Reviewer Objection Response Guide

For each major reviewer objection, this document provides the response strategy: what to write in a rebuttal (if rebuttal is allowed) and what to fix in the paper. Ordered by severity.

---

## Objection 1: "The attack is unrealistic — it operates at the score level, not the traffic level."
**Source:** All 10 audits (universal)  
**Severity:** S0 (near-fatal if mishandled)

**Response strategy:**

> "The reviewer correctly identifies that we operate at the score-substitution level as a threat model abstraction. We make no claim that the adversary can directly inject bytes into the calibration buffer via network traffic — our contribution is to characterize the *vulnerability* of threshold calibration to such an adversary, as a first step toward understanding the attack surface. We have clarified this in §1 and §2: 'We study a score-level adversary who can substitute benign calibration scores; traffic-level realization of such access (e.g., via a compromised device's OS or middleware) is future work.'"

**Paper fix:** A-e102f26659 (P1) — add explicit caveat in §1/abstract; reframe as vulnerability characterization with score-substitution threat model.

---

## Objection 2: "The experiment is unreproducible — missing AE architecture and FedAvg hyperparameters."
**Source:** All 10 audits (universal)  
**Severity:** S1 (major; could be desk-rejection at reproducibility-strict venues)

**Response strategy:**

> "We have added Table X to §2 reporting: autoencoder layer sizes [d→h1→h2→h1→d] with ReLU activations and MSE loss, FedAvg with R rounds, E local epochs, learning rate η, Adam optimizer, N-BaIoT per-device calibration buffer sizes, and the traffic statistics (network flow features) used as model input. The code will be released at [URL] upon acceptance."

**Paper fix:** A-f3e11e1509 (P1) — add reproducibility table; A-664b8440ed (P1) — add artifact statement.

---

## Objection 3: "The Random-Benign control is never shown as data."
**Source:** All 10 audits (universal)  
**Severity:** S1 (major)

**Response strategy:**

> "We have added RANDOM_BENIGN rows to Table 2 and a RANDOM_BENIGN baseline line to Figure 3. The control condition confirms that score-level substitution with uniformly sampled benign scores produces no statistically significant threshold shift (ΔTPR = 0.00±0.00 across all policies), validating that the HIGH_SCORE_BENIGN and LOW_SCORE_BENIGN effects are not artifacts of the replacement mechanism itself."

**Paper fix:** A-1975d011a9 (P1).

---

## Objection 4: "Kloft & Laskov 2012 exists — your novelty claim is fragile."
**Source:** AUDIT-04, AUDIT-08, AUDIT-09, AUDIT-10 (4/10)  
**Severity:** S1

**Response strategy:**

> "We cite Kloft & Laskov 2012 [11] and have now added an explicit contrast paragraph in §3: Kloft & Laskov poison the *training* data of a centralized SVM, shifting the decision boundary. DATP-CP poisons the *threshold-calibration* buffer of a federated autoencoder, shifting the detection threshold. The attack surface, mechanism, threat model, and federated context are all distinct. To the best of our knowledge, no prior work has studied calibration-channel poisoning in federated threshold policy systems."

**Paper fix:** A-5ccfae0eed (P1).

---

## Objection 5: "The paper contradicts itself: Contributions say no spillover for Cluster but §4.2/§5.4 describe Cluster spillover."
**Source:** AUDIT-02, AUDIT-10 (2/10)  
**Severity:** S0 (structural contradiction)

**Response strategy:**

> "We have corrected this inconsistency. Contributions item 3 now reads: 'We show that spillover is policy-dependent: GLOBAL_THRESHOLD causes fleet-wide spillover to all clients; CLUSTER_THRESHOLD causes intra-cluster spillover to non-victim clients in the same cluster; LOCAL_THRESHOLD has no cross-client spillover by construction.' §4.2 and §5.4 are consistent with this revised framing."

**Paper fix:** A-5f02c65612 (P0).

---

## Objection 6: "N=10 seeds is too few for reliable 95% bootstrap confidence intervals."
**Source:** AUDIT-01, AUDIT-03, AUDIT-04, AUDIT-08, AUDIT-09, AUDIT-10 (6/10)  
**Severity:** S1

**Response strategy:**

> "The reviewer is correct that percentile bootstrap CIs have known coverage deficiencies at N=10. We have switched to BCa (bias-corrected accelerated) bootstrap [Efron 1987] which achieves better finite-sample coverage properties. We acknowledge in §6 that N=10 remains a limitation; increasing the seed count is planned for the journal version."

**Paper fix:** A-df1fb64bdd (P1).

---

## Objection 7: "The lowering attack 'success' is hard to interpret — positive ΔTPR sounds good."
**Source:** All 10 audits  
**Severity:** S1

**Response strategy:**

> "The reviewer identifies an important framing issue. We have revised §5.3 and the abstract to foreground the false positive rate increase (ΔFPR) as the harm metric for the lowering attack: 'The LOW_SCORE_BENIGN strategy raises the false positive rate by X±Y percentage points under GLOBAL_THRESHOLD, creating alert fatigue that may lead operators to suppress the anomaly detector.' We retain ΔTPR reporting as a secondary metric but clarify that its positive value indicates increased sensitivity to benign traffic anomalies, not improved security."

**Paper fix:** A-01a7255dbd (P1).

---

## Objection 8: "The three-gate framework is entirely ad hoc."
**Source:** AUDIT-04, AUDIT-08, AUDIT-09 (3/10)  
**Severity:** S1

**Response strategy:**

> "The three-gate framework is inspired by clinical trial stage-gating (e.g., Phase I–III sequential hypothesis testing) applied to security evaluation: Gate-1 confirms material effect size, Gate-2 confirms directional excess over control, Gate-3 confirms downstream security harm. We set Gate-1 at 0.1×IQR (a unit of natural variability) and Gate-2 at 0.01×IQR (a tighter confirmation threshold); both were fixed before observing results. We have added this justification to §6."

**Paper fix:** A-9c654c5a5e (P1).

---

## Objection 9: "Table 1 shows Cluster Macro-F1 ± 0.000 — this is suspicious."
**Source:** AUDIT-10 (1/10)  
**Severity:** S0 (requires investigation)

**Response strategy (pending investigation):**

> "Thank you for catching this. Upon investigation, we found [one of: (a) a reporting bug where the std column was dropped in post-processing — corrected values are X±Y; (b) Cluster Macro-F1 is deterministic across seeds because cluster assignment for this dataset is stable — we have added a footnote explaining this; (c) a code bug where the same seed was reused — corrected results are reported in the revised Table 1]."

**Paper fix:** A-db7bcc5fcf (P0) — investigate first, then respond.

---

## Objection 10: "Reference [12] does not support the claimed finding."
**Source:** AUDIT-10 (1/10)  
**Severity:** S0 (credibility risk)

**Response strategy (pending verification):**

> "We thank the reviewer for checking our citations. We have verified Reference [12] and [one of: (a) confirm it supports the claim at page X; (b) replaced it with the correct citation: [new citation]; (c) removed the unsupported claim and derived the property from first principles]."

**Paper fix:** A-a098e39ee7 (P0) — verify immediately.

---

## Objection 11: "Figure 2 shows only one seed — not representative."
**Source:** All 10 audits  
**Severity:** S1

**Response strategy:**

> "We have updated Figure 2 to show the mean ± standard deviation across all 10 seeds, with the Cluster policy condition added. The single-seed figure was a display choice for visual clarity; the aggregate across seeds is consistent with what was shown."

**Paper fix:** A-984973914d (P1).
