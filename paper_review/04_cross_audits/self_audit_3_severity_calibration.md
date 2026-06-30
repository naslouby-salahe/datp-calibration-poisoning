# Self-Audit 3: Severity Calibration Check

**Question:** Are the S0/S1/S2 severity assignments appropriate? Are any S0s too lenient or any S1s over-promoted?

---

## S0 Findings Review (5 findings)

### F-82f9dcceaf — Contributions vs. §4.2/§5.4 spillover contradiction
- **Assignment:** S0
- **Justification:** A logical contradiction in the Contributions is a structural error. Reviewers may reject on this basis alone without reviewing the experimental results.
- **Verdict:** **S0 CONFIRMED**

### F-6a6b0d6949 — Score-level proxy
- **Assignment:** S0
- **Justification:** 10/10 audits flag this. Two audits (AUDIT-07, AUDIT-08) classify it as near-fatal. The paper's entire experimental validity rests on whether the attack mechanism is realistic. Without a caveat or reframing, strong conferences may reject.
- **Counter-argument:** AUDIT-09 (grade 8.2) classifies this as a P1 fix (reframe, not reject). The paper CAN survive this with appropriate framing.
- **Resolution:** Keep S0 to ensure priority. The paper can survive with the right framing (A-e102f26659), but under-addressing it risks rejection.
- **Verdict:** **S0 CONFIRMED** (with note that A-e102f26659 is the practical fix)

### F-a620caf003 — Reference [12] wrong citation
- **Assignment:** S0
- **Justification:** A single-auditor finding (AUDIT-10 only). However, a provably wrong citation is a factual error that undermines credibility. If the claim it supports is load-bearing, this could force paper withdrawal post-publication.
- **Counter-argument:** Only 1/10 auditors flagged this. May be a misidentification by that auditor.
- **Resolution:** Keep S0 pending verification. If AUDIT-10's identification of [12] is wrong (i.e., the paper does support the claim), downgrade to S2. MUST VERIFY.
- **Verdict:** **S0 CONDITIONAL — verify before resubmission**

### F-f80d97cb0e — "4 source-objective pairs" vs. 3 described
- **Assignment:** S0
- **Justification:** 3/10 audits flag this (AUDIT-02, AUDIT-09, AUDIT-10). An internal inconsistency in the experimental design description is a structural error.
- **Counter-argument:** Could be a simple typo ("4" should be "3"). Easy fix.
- **Resolution:** S0 maintained because it signals to reviewers that the author miscounted their own experimental conditions — which raises questions about result validity.
- **Verdict:** **S0 CONFIRMED**

### F-0993b70fbb — Cluster Macro-F1 ± 0.000
- **Assignment:** S0
- **Justification:** Zero standard deviation across 10 independent seeds is statistically suspicious. Could indicate a code bug (all seeds same), a reporting bug (std column missing), or a genuine degeneracy.
- **Counter-argument:** Only 1/10 auditors flagged this. Could be genuine if Cluster Macro-F1 is insensitive to seed (e.g., deterministic clustering).
- **Resolution:** S0 maintained. Zero std is either a bug or requires explicit explanation. Either outcome demands attention before submission.
- **Verdict:** **S0 CONFIRMED** (pending investigation)

---

## S1 Findings Over-Promotion Check

Any S1 finding that might deserve downgrade to S2:

| Finding ID | Title | Audits | Is S1 Appropriate? |
|------------|-------|--------|--------------------|
| F-16a073b134 | FedAvg role ambiguous | 1/10 | BORDERLINE — single auditor. Could be S2, but architectural clarity matters. Keep S1. |
| F-b6a2ecf3ad | N notation conflict | 1/10 | BORDERLINE — single auditor. Notation conflicts are minor but important for §6. Keep S1. |
| F-715903e3a8 | Figure 3 Global invisible | 1/10 | APPROPRIATE — a figure where a key result is invisible is a significant visual issue. |
| F-79e79bc668 | Harm scenario missing | 1/10 | BORDERLINE — P2 is already assigned. Single auditor. Consider S2 reassignment. See note. |
| F-489c8b7ce6 | Victim ΔTPR ambiguous | 1/10 | APPROPRIATE — results interpretation ambiguity deserves S1. |

**Note on F-79e79bc668:** This could be downgraded to S2 since only AUDIT-10 flagged it and the action (A-d9bc51f540) is already P2. The synthesis keeps S1 because the absence of a motivating harm scenario is a significant rhetorical weakness for a security paper.

---

## S2 Findings Under-Promotion Check

Any S2 finding that might deserve upgrade to S1:

| Finding ID | Title | Current | Should Upgrade? |
|------------|-------|---------|-----------------|
| F-cb5cbb01cf | Local vs. Global P10 Macro-F1 tradeoff | S2 | NO — minor discussion gap, 2/10 auditors |
| F-cc15d7c365 | Table 2 dense layout | S2 | NO — visual presentation issue |

---

## Verdict

S0 assignments are appropriate and justified. Three of the five S0 findings require verification before being downgraded (F-a620caf003 especially). No S1 findings require upgrade to S0. No S2 findings require upgrade to S1.

**One action item from this self-audit:** F-a620caf003 (wrong citation) must be independently verified by opening the cited paper before the action is marked complete.
