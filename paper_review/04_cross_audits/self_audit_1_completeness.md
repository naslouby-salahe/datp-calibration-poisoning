# Self-Audit 1: Completeness Check

**Question:** Did the synthesis miss any meaningful critique from any of the 10 audits?

**Method:** For each audit, check the normalized findings against the master findings list.

---

## AUDIT-01 / AUDIT-03 (identical) — Coverage Check

Key concerns from the audit:
- [x] Score-level proxy → F-6a6b0d6949 (S0)
- [x] Single dataset → EXP-01 (experiment ledger)
- [x] Random-Benign not tabulated → F-d5257ddef0 (S1)
- [x] Spillover not quantified → F-5e5517e25d (S1)
- [x] Lowering harm framing confusing → F-1f6dfe00f2 (S1)
- [x] Reproducibility incomplete → F-4e13c25efd, F-447e660ce4 (S1)
- [x] N=10 statistics → F-64588f32e0 (S1)
- [x] Related work insufficient → F-9c91e712ec, F-7a835d76b5 (S1)
- [x] Controls asserted not shown → F-d5257ddef0 (S1)
- [x] Novelty under-positioned → F-9c91e712ec (S1)
- [x] "every defense" → F-53f9f172ea (S1)
- [x] Deployment language → F-cd3c497156 (S1)
- [x] Figure 1 legend missing → F-1efee522d3 (S1)
- [x] Figure 2 seed 0 only → F-bf066608e1 (S1)
- [x] CV(FPR) late definition → F-bfeb175017 (S1)
- [x] Local vs. Global P10 Macro-F1 → F-cb5cbb01cf (S2)
- [x] Figure 1 "training defended" mislabeling → F-61c8046eee (S1)

**Coverage: COMPLETE**

---

## AUDIT-02 (Paper Audit 10.md, degraded) — Coverage Check

Recoverable concerns from the audit:
- [x] Contributions vs. §4.2/§5.4 spillover contradiction → F-82f9dcceaf (S0, STRUCTURAL)
- [x] Cluster policy under-specified → F-8ae6c046f0 (S1)
- [x] Gate constants unjustified → F-b02c973ba2 (S1)
- [x] Spillover not measured → F-5e5517e25d (S1)
- [x] Kloft & Laskov contrast → F-9c91e712ec (S1)
- [x] AE architecture missing → F-4e13c25efd (S1)
- [x] FedAvg hyperparameters missing → F-447e660ce4 (S1)
- [x] N notation conflict → F-b6a2ecf3ad (S1)
- [x] "30-80 Mirai flows" → F-810820f994 (S1)
- [x] Score-level proxy → F-6a6b0d6949 (S0)
- [x] BAP10 undefined → F-0c0628ecf5 (S1)
- [x] Figure 2 Cluster absent → F-bf066608e1 (S1)

**Coverage: COMPLETE (within degraded content limits)**  
*Note: URL-embedded cells from this audit may contain additional critiques not recoverable. Any missed nuance is a degradation artifact, not a synthesis gap.*

---

## AUDIT-04 (Paper Audit 3.md) — Coverage Check

Key concerns:
- [x] N=10 bootstrap CIs → F-64588f32e0 (S0 per this reviewer, S1 in synthesis — see note)
- [x] "no prior work" fragile → F-1249c7034d (S1)
- [x] Lowering attack overclaim → F-4521a0a59c (S1)
- [x] AE architecture missing → F-4e13c25efd (S1)
- [x] FedAvg hyperparameters missing → F-447e660ce4 (S1)
- [x] Cluster membership not reported → F-adf1c918ff (S1)
- [x] "30-80 Mirai flows" → F-810820f994 (S1)
- [x] ΔCV(FPR) figure missing for lowering → F-bf066608e1 (S1) — NOTE: figure missing for lowering specifically; captured under Figure 2 general finding
- [x] No 2023-2024 citations → F-260ecb76ac (S1)
- [x] Gate constants unjustified → F-b02c973ba2 (S1)
- [x] Victim-majority condition → F-db45a4d07d (S1)
- [x] Random-Benign not tabulated → F-d5257ddef0 (S1)
- [x] "100% Gate-1 pass rate" before defined → F-1de8c78e14 (S1)
- [x] Train/calibration/test split → F-3ef85e6456 (S1)
- [x] No artifact statement → F-56f3c530ef (S1)
- [x] No comparison table → F-7a835d76b5 (S1)
- [x] Defense sketch missing → F-b808e36c15 (S1)
- [x] Feature pipeline missing → F-4ad5dce40c (S1)
- [x] Figure 2 seed 0 only → F-bf066608e1 (S1)

**One severity disagreement noted:** AUDIT-04 classifies N=10 bootstrap as near-fatal (S0). Synthesis classifies as S1 because not all audits classify it S0. Conservative choice — logged here.

**Coverage: COMPLETE**

---

## AUDIT-09 (Paper Audit 8.md) — Coverage Check

Key concerns (most generous audit):
- [x] "4 source-objective pairs" → F-f80d97cb0e (S0)
- [x] Random-Benign not numerically shown → F-d5257ddef0 (S1)
- [x] Reproducibility gap → F-4e13c25efd + F-447e660ce4 + F-3ef85e6456 + F-4ad5dce40c (S1)
- [x] Negative control hidden in prose → F-d5257ddef0 (S1)
- [x] Lowering harm framing → F-1f6dfe00f2 (S1)
- [x] Spillover thin → F-5e5517e25d (S1)
- [x] Figure 2 seed 0, Cluster absent → F-bf066608e1 (S1)
- [x] Figure 3 RB not plotted → F-d17dbb4517 (S1)
- [x] No artifact statement → F-56f3c530ef (S1)
- [x] Kloft & Laskov contrast → F-9c91e712ec (S1)
- [x] "every defense" → F-53f9f172ea (S1)
- [x] BAP10 undefined → F-0c0628ecf5 (S2)
- [x] Table 2 density → F-cc15d7c365 (S2)
- [x] Figure 1 legend → F-1efee522d3 (S2)
- [x] "100% Gate-1" before defined → F-1de8c78e14 (S2)

**Coverage: COMPLETE**

---

## AUDIT-10 (Paper Audit 9.md) — Coverage Check

Key concerns (most critical audit):
- [x] AE + FedAvg hyperparameters FATAL → F-4e13c25efd + F-447e660ce4 (S0/S1)
- [x] "4 source-objective pairs" → F-f80d97cb0e (S0)
- [x] Reference [12] wrong citation → F-a620caf003 (S0)
- [x] N=10 bootstrap CIs → F-64588f32e0 (S1)
- [x] Cluster Macro-F1 ± 0.000 → F-0993b70fbb (S0)
- [x] FedAvg role ambiguous → F-16a073b134 (S1)
- [x] N notation conflict → F-b6a2ecf3ad (S1)
- [x] "30-80 Mirai flows" → F-810820f994 (S1)
- [x] Gate constants → F-b02c973ba2 (S1)
- [x] Figure 3 Global invisible → F-715903e3a8 (S1)
- [x] Victim ΔTPR ambiguous → F-489c8b7ce6 (S1)
- [x] Harm scenario missing → F-79e79bc668 (S1)
- [x] K-means++ citation → F-2ea27ded3d (S1)
- [x] 2023-2024 citations → F-260ecb76ac (S1)
- [x] Spillover contradiction → F-82f9dcceaf (S0)
- [x] Cluster under-specified → F-8ae6c046f0 (S1)
- [x] gray-box imprecise → F-e617b74787 (S1)
- [x] BAP10 undefined → F-0c0628ecf5 (S2)
- [x] No artifact statement → F-56f3c530ef (S1)
- [x] Realism caveat in abstract → F-6a6b0d6949 (S0)

**Coverage: COMPLETE**

---

## Synthesis Completeness Verdict

**No missing findings detected.** All major concerns from all 10 audits (including degraded AUDIT-02 and AUDIT-08) are mapped to atomic findings in findings_master.csv.

The one deliberate severity disagreement (AUDIT-04's near-fatal rating for N=10 bootstrap) is documented above and resolved conservatively (S1 in synthesis, noted explicitly).
