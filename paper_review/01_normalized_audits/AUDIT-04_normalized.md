# AUDIT-04 Normalized

**Source file:** Paper Audit 3.md  
**SHA-256:** 9ef6181358fe79c68f33a7fa92a201a3ee9bdd19588abc1a132109b2643d359a  
**Grade:** 6.8 / 10  
**Recommendation:** Borderline / Weak Accept (leaning reject)  
**Duplicate flag:** None  
**Content quality:** Full — no URL embedding degradation

---

## Reviewer Summary

This reviewer is more critical than AUDIT-01/03, identifying several near-fatal risks and issuing a lower grade. Key concerns: (a) N=10 bootstrap CIs have unreliable 95% coverage, (b) "no prior work" claim is fragile given Kloft & Laskov 2012, (c) the lowering attack claim in the abstract overclaims, (d) AE architecture and FedAvg hyperparameters are missing making experiments unreproducible, (e) Cluster membership not reported per-device, (f) "30-80 undetected Mirai flows" is an uncited/underived claim, (g) ΔCV(FPR) figure missing for lowering attack, (h) no multi-client collusion analysis, (i) gate constants lack citation.

---

## Findings Extracted

### S0 — Near-Fatal Risks

| # | Location | Finding |
|---|----------|---------|
| NF-A04-01 | §6 / statistics | N=10 seeds — bootstrap 95% CIs not reliable with this sample size; BCa bootstrap preferred |
| NF-A04-02 | §3 / related work | "No prior work" claim fragile: Kloft & Laskov 2012 [11] cited but not explicitly contrasted |
| NF-A04-03 | Abstract | Lowering attack "succeeds" overclaims — positive ΔTPR can be misread as beneficial |
| NF-A04-04 | §2 | AE architecture missing → experiment unreproducible |
| NF-A04-05 | §2 | FedAvg hyperparameters (rounds, local epochs, learning rate) missing |

### S1 — Major Weaknesses

| # | Location | Finding |
|---|----------|---------|
| MW-A04-01 | §4/§5 | Cluster membership per device not reported; cluster assignment varies by seed |
| MW-A04-02 | §5.2 | "30-80 undetected Mirai flows" claim: no derivation, no citation, no traffic model |
| MW-A04-03 | Figure 3 | ΔCV(FPR) figure missing for lowering attack |
| MW-A04-04 | §3 | No 2023-2024 FL security citations — related work potentially outdated |
| MW-A04-05 | §6 | Gate constants (0.1 × IQR for Gate-1, 0.01 for Gate-2) unjustified — potentially post-hoc |
| MW-A04-06 | §1 | Victim-majority condition (≥5/9) unjustified — why majority? |
| MW-A04-07 | §5 | Random-Benign control not tabulated; present only in prose/captions |
| MW-A04-08 | Abstract/§1 | "100% Gate-1 pass rate" cited before Gate-1 defined |
| MW-A04-09 | §1/§2 | Train/calibration/test split not described |
| MW-A04-10 | §1 | No artifact/code availability statement |
| MW-A04-11 | §3 | No closest-prior-work comparison table |
| MW-A04-12 | §5.4 | Spillover not directly tabulated with victim vs. non-victim breakdown |
| MW-A04-13 | §2 | Feature extraction pipeline / preprocessing not described |
| MW-A04-14 | §4/§5 | Defense sketch / mitigation requirements paragraph missing |

### S2 — Minor

| # | Location | Finding |
|---|----------|---------|
| MI-A04-01 | Figure 2 | Only seed 0 shown; Cluster condition absent |
| MI-A04-02 | Figure 3 | Random-Benign not plotted |
| MI-A04-03 | Table 1 | BAP10/P10/"Worst BA" undefined abbreviations |
| MI-A04-04 | Table 1 | Bold convention direction not stated |
| MI-A04-05 | §2 | CV(FPR) introduced without early definition |
| MI-A04-06 | Abstract | Realism caveat missing from abstract |

---

## Experiment-Scope Critiques (OUTSIDE_FROZEN_SCOPE)

- No multi-client collusion — explicitly outside scope per roadmap
- Single dataset — would require additional datasets
- q=0.95 sensitivity not analyzed
- No additional FL algorithms

---

## Reviewer Verdict

> "Borderline accept. The missing architecture details alone could be a desk-reject at venues requiring reproducibility. The N=10 bootstrap is statistically fragile. Kloft & Laskov must be explicitly contrasted. If these core issues are addressed, the paper has a path to acceptance."
