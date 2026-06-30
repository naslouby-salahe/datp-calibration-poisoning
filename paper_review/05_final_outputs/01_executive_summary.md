# Executive Summary: DATP-CP Paper Audit Synthesis

**Paper:** "Poisoning the Threshold-Calibration Stage in Federated IoT Anomaly Detection: A Policy-Differentiated Vulnerability Analysis"  
**Synthesis date:** 2026-06-30  
**Audits analyzed:** 10 (8 unique; AUDIT-01≡AUDIT-03, AUDIT-06≡AUDIT-07)  
**Grade range:** 6.1 – 8.2 / 10  
**Recommendations:** 6× weak/borderline accept, 2× weak/borderline reject  

---

## Where the Paper Stands

The paper is **science-sound** but **not yet submission-ready**. Every auditor finds the core contribution valid: DATP-CP is the first study of calibration-channel poisoning in federated threshold policies, using physical N-BaIoT devices, with a three-policy framework (GLOBAL/LOCAL/CLUSTER) and a three-gate statistical analysis. No auditor disputes this contribution.

The problems are in **presentation, reproducibility, and two specific structural errors** — not in the experiments themselves. Most blocking issues are text fixes.

**Estimated effort to reach submission readiness:** 2–3 focused work days.

---

## The 4 Errors That Must Be Fixed Before Submission

These are structural errors that could cause desk-rejection or credibility loss:

| Priority | Action ID | Error | Fix |
|----------|-----------|-------|-----|
| P0 | A-5f02c65612 | Contributions item 3 contradicts §4.2/§5.4 on Cluster spillover | Rewrite Contributions item 3 to state spillover is policy-dependent |
| P0 | A-a098e39ee7 | Reference [12] (L'heureux 2017) is a wrong citation | Verify the paper; find correct citation or remove the claim |
| P0 | A-bc70838a10 | "4 source-objective pairs" but only 3 described | Correct count to 3, or name and describe the 4th pair |
| P0 | A-db7bcc5fcf | Table 1: Cluster Macro-F1 ± 0.000 (zero std impossible) | Investigate results pipeline; correct or explain |

---

## The 11 Required Submission Items (P1)

After P0 fixes, these are required for any submission:

| Action ID | What | Effort |
|-----------|------|--------|
| A-f3e11e1509 | Add reproducibility table (AE arch, FedAvg config, splits, features) | M |
| A-664b8440ed | Add artifact/code availability statement | XS |
| A-e102f26659 | Add score-level proxy caveat; fix attack vs. characterization language | S |
| A-01a7255dbd | Reframe lowering attack: foreground ΔFPR alarm burden, not ΔTPR | S |
| A-1975d011a9 | Add Random-Benign rows to Table 2; add RB line to Figure 3 | M |
| A-984973914d | Fix Figure 2: add Cluster condition; add multiple seeds or justify seed 0 | M |
| A-e31849338f | Add spillover quantification table (victim vs. non-victim) | M |
| A-5ccfae0eed | Expand related work: Kloft & Laskov contrast, comparison table | M |
| A-f8c713ec0c | Remove "every defense" and deployment language | XS |
| A-df1fb64bdd | Add BCa bootstrap caveat for N=10 seeds | S |
| A-9c654c5a5e | Justify gate constants and three-gate framework | S |

---

## What the Auditors Agreed On (Universal Consensus)

Seven findings were flagged by all 10 audits (treating duplicates as independent votes):

1. **Score-level proxy** — attack needs explicit caveat that it is score-level, not traffic-level
2. **AE architecture missing** — experiment is unreproducible without it
3. **No artifact statement** — universal expectation
4. **Lowering attack ΔTPR framing misleading** — positive ΔTPR sounds beneficial; foreground ΔFPR
5. **Figure 2: only seed 0 shown** — not representative; Cluster absent
6. **Figure 3: no Random-Benign line** — control invisible
7. **Table 2: no Random-Benign rows** — control not shown as data

---

## Grade Distribution and Probability of Acceptance

| Grade | Unique Auditor | Recommendation |
|-------|----------------|----------------|
| 8.2 | AUDIT-09 | Weak accept — closest to ready |
| 8.0 | AUDIT-01/03 | Borderline accept |
| 7.8 | AUDIT-05/06 | Weak accept |
| 7.0 | AUDIT-02 | Borderline reject |
| 6.8 | AUDIT-04 | Borderline accept (leaning reject) |
| 6.7 | AUDIT-08 | Weak reject |
| 6.1 | AUDIT-10 | Borderline/weak reject |

**Estimated current acceptance probability at a strong venue:** ~35–45%.  
**Estimated acceptance probability after P0+P1 fixes:** ~70–80%.  
**Estimated acceptance probability after P0+P1+P2 fixes:** ~80–90%.

---

## What NOT to Do

The following critiques are out of scope per the frozen DATP-CP boundary. Do not address them in this paper:

- Multi-client collusion experiments (DEFER to future work)
- Byzantine defense comparisons (REJECT — wrong threat model)
- FedProx / SCAFFOLD evaluation (DEFER to future work)
- Multi-dataset evaluation (DEFER — mention in Limitations)
- Privacy guarantees (REJECT — forbidden)
- Deployment recommendations (REJECT — forbidden)
- Traffic-level attack demonstration (DEFER — acknowledge as future work)

---

## Bottom Line

Fix the 4 P0 errors and 11 P1 items. The core science is valid and the contribution is original. The paper needs presentation work, not experiment re-runs.
