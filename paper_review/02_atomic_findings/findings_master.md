# Atomic Findings Master

**Total findings:** 50  
**S0 (Fatal):** 5  **S1 (Major):** 43  **S2 (Minor):** 2

_ID = SHA256(category|location|title)[:10], prefixed F-_

---

## S0 — Fatal / Near-Fatal

| ID | Category | Location | Finding | Audit Count | Action Type |
|----|----------|----------|---------|-------------|-------------|
| F-82f9dcceaf | CLAIMS | §1 Contributions vs. §4.2/§5.4 | STRUCTURAL CONTRADICTION: Contributions item 3 says Local/Cluster have no cross-client spillover; §4.2/§5.4 say Cluster causes intra-cluster spillover | 2/10 | STRUCTURAL_FIX |
| F-6a6b0d6949 | REALISM | §2 / Abstract | Score-level proxy: attack operates at calibration score level, not traffic level — never shown to be traffic-realizable | 10/10 | PAPER_FIX |
| F-a620caf003 | RELATED_WORK | §3 / references | Reference [12] (L'heureux 2017) is a wrong citation — paper does not support the claimed threshold sensitivity finding | 1/10 | PAPER_FIX |
| F-f80d97cb0e | REPRODUCIBILITY | §4 / §1 | "4 source-objective pairs" stated but only 3 attack conditions described | 3/10 | PAPER_FIX |
| F-0993b70fbb | STATISTICS | Table 1 | Cluster Macro-F1 = 0.299 ± 0.000 — zero standard deviation is statistically impossible unless all seeds identical; may indicate reporting bug | 1/10 | PAPER_FIX |

## S1 — Major Weaknesses

| ID | Category | Location | Finding | Audit Count | Action Type |
|----|----------|----------|---------|-------------|-------------|
| F-1de8c78e14 | CLAIMS | Abstract / §1 | "100% Gate-1 pass rate" cited before Gate-1 is defined | 3/10 | PAPER_FIX |
| F-489c8b7ce6 | CLAIMS | §5.5 | Victim ΔTPR for Global results ambiguous — unclear if per-victim or average across all clients | 1/10 | PAPER_FIX |
| F-53f9f172ea | CLAIMS | §1 / abstract | "structurally outside scope of every defense" — undefendable universal claim | 5/10 | PAPER_FIX |
| F-79e79bc668 | CLAIMS | §5 | Concrete motivating harm scenario (specific attacker goal, IoT context) missing | 1/10 | PAPER_FIX |
| F-810820f994 | CLAIMS | §5.2 | "30-80 undetected Mirai flows" claim has no derivation, no traffic model, no citation | 2/10 | PAPER_FIX |
| F-cd3c497156 | CLAIMS | §1 / abstract | "operationally meaningful in IoT deployment contexts" — deployment claim out of scope per frozen boundary | 3/10 | PAPER_FIX |
| F-1f6dfe00f2 | FRAMING | Abstract / §5.3 | Lowering attack: positive ΔTPR sounds beneficial; harm should be foregrounded as increased ΔFPR / alarm burden | 10/10 | PAPER_FIX |
| F-4521a0a59c | FRAMING | Abstract | Lowering attack "succeeds" in abstract overclaims epistemic status | 3/10 | PAPER_FIX |
| F-653ddd1df9 | FRAMING | §5 / results | Lowering attack: Global conditionality (why lowering works for Global but not Local/Cluster) under-explained | 2/10 | PAPER_FIX |
| F-b808e36c15 | PRESENTATION | §5 / Discussion | Defense requirements sketch / mitigation paragraph completely missing from Discussion | 3/10 | PAPER_FIX |
| F-bfeb175017 | PRESENTATION | §2 | CV(FPR) metric defined inconsistently / introduced late without early definition | 4/10 | PAPER_FIX |
| F-f8e2e92b2d | PRESENTATION | §1 / Introduction | No paper roadmap (section-by-section guide) in Introduction | 2/10 | PAPER_FIX |
| F-8993694ae8 | REALISM | Abstract vs. §6 | "attack" (abstract) vs "vulnerability characterization" (§6) — inconsistent epistemic framing throughout | 3/10 | PAPER_FIX |
| F-b5bfa0c742 | REALISM | §4 / method | Formal contamination equation absent — only informal description of REPLACE-FIXED-BUDGET | 2/10 | PAPER_FIX |
| F-e617b74787 | REALISM | §2 / threat model | "gray-box" label used without precise definition anchored to the FL setup | 3/10 | PAPER_FIX |
| F-1249c7034d | RELATED_WORK | §1 / abstract | "no prior work" causal claim too strong — should be "we find no prior work" | 3/10 | PAPER_FIX |
| F-260ecb76ac | RELATED_WORK | §3 / related work | No 2023-2024 FL security citations — related work likely outdated | 2/10 | PAPER_FIX |
| F-2ea27ded3d | RELATED_WORK | §3 / related work | K-means++ not cited (Arthur & Vassilvitskii 2007) despite its use in cluster formation | 1/10 | PAPER_FIX |
| F-7a835d76b5 | RELATED_WORK | §3 / related work | No related-work comparison table — nearest works not systematically contrasted | 5/10 | PAPER_FIX |
| F-9c91e712ec | RELATED_WORK | §3 / related work | Kloft & Laskov 2012 [11] cited but not explicitly contrasted — novelty claim fragile | 4/10 | PAPER_FIX |
| F-16a073b134 | REPRODUCIBILITY | §2 (setup) | FedAvg role ambiguous: "using FedAvg for feature extraction" is architecturally misleading | 1/10 | PAPER_FIX |
| F-3ef85e6456 | REPRODUCIBILITY | §2 (setup) | Train/calibration/test split not described | 5/10 | PAPER_FIX |
| F-447e660ce4 | REPRODUCIBILITY | §2 (setup) | FedAvg hyperparameters (rounds, local epochs, LR) missing | 8/10 | PAPER_FIX |
| F-4ad5dce40c | REPRODUCIBILITY | §2 (setup) | Feature extraction and preprocessing pipeline not described | 3/10 | PAPER_FIX |
| F-4e13c25efd | REPRODUCIBILITY | §2 (setup) | AE architecture not described — experiment unreproducible | 10/10 | PAPER_FIX |
| F-56f3c530ef | REPRODUCIBILITY | §1 (intro) | No artifact/code availability statement | 10/10 | PAPER_FIX |
| F-5e5517e25d | SPILLOVER | §5.4 | Spillover claims not directly quantified — need victim vs. non-victim ΔTPR/ΔFPR breakdown table | 7/10 | PAPER_FIX |
| F-8ae6c046f0 | SPILLOVER | §4 / §5 | Cluster policy under-specified: K=3 clusters, but feature representation used for assignment not described | 2/10 | PAPER_FIX |
| F-adf1c918ff | SPILLOVER | §4 / §5 | Cluster assignment varies across seeds — this is not documented or discussed | 3/10 | PAPER_FIX |
| F-64588f32e0 | STATISTICS | §6 / statistics | N=10 seeds: percentile bootstrap 95% CIs have unreliable coverage (need n≥30); BCa bootstrap recommended | 6/10 | PAPER_FIX |
| F-95a95d973c | STATISTICS | §6 / statistics | Three-gate framework is entirely bespoke with no citation or principled derivation | 3/10 | PAPER_FIX |
| F-b02c973ba2 | STATISTICS | §6 / statistics | Gate-1 and Gate-2 constants (0.1×IQR, 0.01×IQR) unjustified — appear potentially post-hoc tuned on results | 4/10 | PAPER_FIX |
| F-b6a2ecf3ad | STATISTICS | §6 / notation | N notation conflict in §6: same symbol N used for federation size (9) and calibration buffer size (≈2622) | 1/10 | PAPER_FIX |
| F-db45a4d07d | STATISTICS | §5 / results | Victim-majority condition (≥5/9) for Global THRESHOLD_RAISE unjustified | 2/10 | PAPER_FIX |
| F-0b45246ccd | TABLES | Table 1 | Table 1: bold convention direction not stated (higher-is-better vs. lower-is-better unclear) | 4/10 | PAPER_FIX |
| F-0c0628ecf5 | TABLES | Table 1 | Table 1: BAP10 / P10 / 'Worst BA' abbreviations undefined — no footnote or legend | 6/10 | PAPER_FIX |
| F-d5257ddef0 | TABLES | Table 2 | Table 2: Random-Benign control not shown as explicit rows — control condition invisible | 10/10 | PAPER_FIX |
| F-1efee522d3 | VISUALS | Figure 1 | Figure 1: no color legend; attack operation and data flow unclear | 3/10 | PAPER_FIX |
| F-61c8046eee | VISUALS | Figure 1 | Figure 1: diagram labels "training phase defended" but calibration is the attack stage | 3/10 | PAPER_FIX |
| F-715903e3a8 | VISUALS | Figure 3 | Figure 3: Global line nearly invisible at current y-axis scale — needs inset or separate subplot | 1/10 | PAPER_FIX |
| F-bf066608e1 | VISUALS | Figure 2 | Figure 2: only seed 0 shown without justification that seed 0 is representative; Cluster condition absent | 10/10 | PAPER_FIX |
| F-d17dbb4517 | VISUALS | Figure 3 | Figure 3: Random-Benign control not plotted — invisible control condition | 10/10 | PAPER_FIX |
| F-f457b6ac9d | VISUALS | Figures 1-3 | All figures appear to be blurry/low-resolution screenshots, not vector or high-DPI exports | 1/10 | PAPER_FIX |

## S2 — Minor / Polish

| ID | Category | Location | Finding | Audit Count | Action Type |
|----|----------|----------|---------|-------------|-------------|
| F-cb5cbb01cf | PRESENTATION | §5 | Local vs. Global P10 Macro-F1 tradeoff not discussed in results narrative | 2/10 | PAPER_FIX |
| F-cc15d7c365 | TABLES | Table 2 | Table 2: dense layout makes comparison across threshold policies difficult | 3/10 | PAPER_FIX |

## Detailed Entries

### F-82f9dcceaf — STRUCTURAL CONTRADICTION: Contributions item 3 says Local/Cluster have no cross-client spillover; §4.2/§5.4 say Cluster causes intra-cluster spillover

- **Category:** CLAIMS
- **Severity:** S0
- **Location:** §1 Contributions vs. §4.2/§5.4
- **Audit sources (2/10):** AUDIT-02;AUDIT-10
- **Action type:** STRUCTURAL_FIX
- **Note:** Direct logical contradiction — must be resolved before submission

### F-6a6b0d6949 — Score-level proxy: attack operates at calibration score level, not traffic level — never shown to be traffic-realizable

- **Category:** REALISM
- **Severity:** S0
- **Location:** §2 / Abstract
- **Audit sources (10/10):** AUDIT-01;AUDIT-02;AUDIT-03;AUDIT-04;AUDIT-05;AUDIT-06;AUDIT-07;AUDIT-08;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX
- **Note:** Realism caveat is already acknowledged in discussion; needs stronger framing in §1/abstract per reviewers

### F-a620caf003 — Reference [12] (L'heureux 2017) is a wrong citation — paper does not support the claimed threshold sensitivity finding

- **Category:** RELATED_WORK
- **Severity:** S0
- **Location:** §3 / references
- **Audit sources (1/10):** AUDIT-10
- **Action type:** PAPER_FIX
- **Note:** CRITICAL: citation verification needed before submission

### F-f80d97cb0e — "4 source-objective pairs" stated but only 3 attack conditions described

- **Category:** REPRODUCIBILITY
- **Severity:** S0
- **Location:** §4 / §1
- **Audit sources (3/10):** AUDIT-02;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-0993b70fbb — Cluster Macro-F1 = 0.299 ± 0.000 — zero standard deviation is statistically impossible unless all seeds identical; may indicate reporting bug

- **Category:** STATISTICS
- **Severity:** S0
- **Location:** Table 1
- **Audit sources (1/10):** AUDIT-10
- **Action type:** PAPER_FIX

### F-1de8c78e14 — "100% Gate-1 pass rate" cited before Gate-1 is defined

- **Category:** CLAIMS
- **Severity:** S1
- **Location:** Abstract / §1
- **Audit sources (3/10):** AUDIT-04;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-489c8b7ce6 — Victim ΔTPR for Global results ambiguous — unclear if per-victim or average across all clients

- **Category:** CLAIMS
- **Severity:** S1
- **Location:** §5.5
- **Audit sources (1/10):** AUDIT-10
- **Action type:** PAPER_FIX

### F-53f9f172ea — "structurally outside scope of every defense" — undefendable universal claim

- **Category:** CLAIMS
- **Severity:** S1
- **Location:** §1 / abstract
- **Audit sources (5/10):** AUDIT-01;AUDIT-03;AUDIT-04;AUDIT-08;AUDIT-09
- **Action type:** PAPER_FIX
- **Note:** Forbidden per DATP-CP frozen boundary: do not claim broad defense evasion

### F-79e79bc668 — Concrete motivating harm scenario (specific attacker goal, IoT context) missing

- **Category:** CLAIMS
- **Severity:** S1
- **Location:** §5
- **Audit sources (1/10):** AUDIT-10
- **Action type:** PAPER_FIX

### F-810820f994 — "30-80 undetected Mirai flows" claim has no derivation, no traffic model, no citation

- **Category:** CLAIMS
- **Severity:** S1
- **Location:** §5.2
- **Audit sources (2/10):** AUDIT-04;AUDIT-10
- **Action type:** PAPER_FIX

### F-cd3c497156 — "operationally meaningful in IoT deployment contexts" — deployment claim out of scope per frozen boundary

- **Category:** CLAIMS
- **Severity:** S1
- **Location:** §1 / abstract
- **Audit sources (3/10):** AUDIT-01;AUDIT-03;AUDIT-04
- **Action type:** PAPER_FIX
- **Note:** Explicitly forbidden by frozen boundary: no deployment readiness claims

### F-1f6dfe00f2 — Lowering attack: positive ΔTPR sounds beneficial; harm should be foregrounded as increased ΔFPR / alarm burden

- **Category:** FRAMING
- **Severity:** S1
- **Location:** Abstract / §5.3
- **Audit sources (10/10):** AUDIT-01;AUDIT-02;AUDIT-03;AUDIT-04;AUDIT-05;AUDIT-06;AUDIT-07;AUDIT-08;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-4521a0a59c — Lowering attack "succeeds" in abstract overclaims epistemic status

- **Category:** FRAMING
- **Severity:** S1
- **Location:** Abstract
- **Audit sources (3/10):** AUDIT-01;AUDIT-03;AUDIT-04
- **Action type:** PAPER_FIX

### F-653ddd1df9 — Lowering attack: Global conditionality (why lowering works for Global but not Local/Cluster) under-explained

- **Category:** FRAMING
- **Severity:** S1
- **Location:** §5 / results
- **Audit sources (2/10):** AUDIT-06;AUDIT-07
- **Action type:** PAPER_FIX

### F-b808e36c15 — Defense requirements sketch / mitigation paragraph completely missing from Discussion

- **Category:** PRESENTATION
- **Severity:** S1
- **Location:** §5 / Discussion
- **Audit sources (3/10):** AUDIT-04;AUDIT-06;AUDIT-07
- **Action type:** PAPER_FIX

### F-bfeb175017 — CV(FPR) metric defined inconsistently / introduced late without early definition

- **Category:** PRESENTATION
- **Severity:** S1
- **Location:** §2
- **Audit sources (4/10):** AUDIT-01;AUDIT-03;AUDIT-04;AUDIT-10
- **Action type:** PAPER_FIX

### F-f8e2e92b2d — No paper roadmap (section-by-section guide) in Introduction

- **Category:** PRESENTATION
- **Severity:** S1
- **Location:** §1 / Introduction
- **Audit sources (2/10):** AUDIT-06;AUDIT-07
- **Action type:** PAPER_FIX

### F-8993694ae8 — "attack" (abstract) vs "vulnerability characterization" (§6) — inconsistent epistemic framing throughout

- **Category:** REALISM
- **Severity:** S1
- **Location:** Abstract vs. §6
- **Audit sources (3/10):** AUDIT-06;AUDIT-07;AUDIT-10
- **Action type:** PAPER_FIX

### F-b5bfa0c742 — Formal contamination equation absent — only informal description of REPLACE-FIXED-BUDGET

- **Category:** REALISM
- **Severity:** S1
- **Location:** §4 / method
- **Audit sources (2/10):** AUDIT-06;AUDIT-07
- **Action type:** PAPER_FIX

### F-e617b74787 — "gray-box" label used without precise definition anchored to the FL setup

- **Category:** REALISM
- **Severity:** S1
- **Location:** §2 / threat model
- **Audit sources (3/10):** AUDIT-06;AUDIT-07;AUDIT-10
- **Action type:** PAPER_FIX

### F-1249c7034d — "no prior work" causal claim too strong — should be "we find no prior work"

- **Category:** RELATED_WORK
- **Severity:** S1
- **Location:** §1 / abstract
- **Audit sources (3/10):** AUDIT-04;AUDIT-08;AUDIT-10
- **Action type:** PAPER_FIX

### F-260ecb76ac — No 2023-2024 FL security citations — related work likely outdated

- **Category:** RELATED_WORK
- **Severity:** S1
- **Location:** §3 / related work
- **Audit sources (2/10):** AUDIT-04;AUDIT-10
- **Action type:** PAPER_FIX

### F-2ea27ded3d — K-means++ not cited (Arthur & Vassilvitskii 2007) despite its use in cluster formation

- **Category:** RELATED_WORK
- **Severity:** S1
- **Location:** §3 / related work
- **Audit sources (1/10):** AUDIT-10
- **Action type:** PAPER_FIX

### F-7a835d76b5 — No related-work comparison table — nearest works not systematically contrasted

- **Category:** RELATED_WORK
- **Severity:** S1
- **Location:** §3 / related work
- **Audit sources (5/10):** AUDIT-01;AUDIT-03;AUDIT-05;AUDIT-08;AUDIT-09
- **Action type:** PAPER_FIX

### F-9c91e712ec — Kloft & Laskov 2012 [11] cited but not explicitly contrasted — novelty claim fragile

- **Category:** RELATED_WORK
- **Severity:** S1
- **Location:** §3 / related work
- **Audit sources (4/10):** AUDIT-04;AUDIT-08;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-16a073b134 — FedAvg role ambiguous: "using FedAvg for feature extraction" is architecturally misleading

- **Category:** REPRODUCIBILITY
- **Severity:** S1
- **Location:** §2 (setup)
- **Audit sources (1/10):** AUDIT-10
- **Action type:** PAPER_FIX

### F-3ef85e6456 — Train/calibration/test split not described

- **Category:** REPRODUCIBILITY
- **Severity:** S1
- **Location:** §2 (setup)
- **Audit sources (5/10):** AUDIT-01;AUDIT-03;AUDIT-04;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-447e660ce4 — FedAvg hyperparameters (rounds, local epochs, LR) missing

- **Category:** REPRODUCIBILITY
- **Severity:** S1
- **Location:** §2 (setup)
- **Audit sources (8/10):** AUDIT-02;AUDIT-04;AUDIT-05;AUDIT-06;AUDIT-07;AUDIT-08;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-4ad5dce40c — Feature extraction and preprocessing pipeline not described

- **Category:** REPRODUCIBILITY
- **Severity:** S1
- **Location:** §2 (setup)
- **Audit sources (3/10):** AUDIT-04;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-4e13c25efd — AE architecture not described — experiment unreproducible

- **Category:** REPRODUCIBILITY
- **Severity:** S1
- **Location:** §2 (setup)
- **Audit sources (10/10):** AUDIT-01;AUDIT-02;AUDIT-03;AUDIT-04;AUDIT-05;AUDIT-06;AUDIT-07;AUDIT-08;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-56f3c530ef — No artifact/code availability statement

- **Category:** REPRODUCIBILITY
- **Severity:** S1
- **Location:** §1 (intro)
- **Audit sources (10/10):** AUDIT-01;AUDIT-02;AUDIT-03;AUDIT-04;AUDIT-05;AUDIT-06;AUDIT-07;AUDIT-08;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-5e5517e25d — Spillover claims not directly quantified — need victim vs. non-victim ΔTPR/ΔFPR breakdown table

- **Category:** SPILLOVER
- **Severity:** S1
- **Location:** §5.4
- **Audit sources (7/10):** AUDIT-01;AUDIT-02;AUDIT-03;AUDIT-04;AUDIT-08;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-8ae6c046f0 — Cluster policy under-specified: K=3 clusters, but feature representation used for assignment not described

- **Category:** SPILLOVER
- **Severity:** S1
- **Location:** §4 / §5
- **Audit sources (2/10):** AUDIT-02;AUDIT-10
- **Action type:** PAPER_FIX

### F-adf1c918ff — Cluster assignment varies across seeds — this is not documented or discussed

- **Category:** SPILLOVER
- **Severity:** S1
- **Location:** §4 / §5
- **Audit sources (3/10):** AUDIT-05;AUDIT-06;AUDIT-10
- **Action type:** PAPER_FIX

### F-64588f32e0 — N=10 seeds: percentile bootstrap 95% CIs have unreliable coverage (need n≥30); BCa bootstrap recommended

- **Category:** STATISTICS
- **Severity:** S1
- **Location:** §6 / statistics
- **Audit sources (6/10):** AUDIT-01;AUDIT-03;AUDIT-04;AUDIT-08;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-95a95d973c — Three-gate framework is entirely bespoke with no citation or principled derivation

- **Category:** STATISTICS
- **Severity:** S1
- **Location:** §6 / statistics
- **Audit sources (3/10):** AUDIT-04;AUDIT-08;AUDIT-09
- **Action type:** PAPER_FIX

### F-b02c973ba2 — Gate-1 and Gate-2 constants (0.1×IQR, 0.01×IQR) unjustified — appear potentially post-hoc tuned on results

- **Category:** STATISTICS
- **Severity:** S1
- **Location:** §6 / statistics
- **Audit sources (4/10):** AUDIT-04;AUDIT-08;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-b6a2ecf3ad — N notation conflict in §6: same symbol N used for federation size (9) and calibration buffer size (≈2622)

- **Category:** STATISTICS
- **Severity:** S1
- **Location:** §6 / notation
- **Audit sources (1/10):** AUDIT-10
- **Action type:** PAPER_FIX

### F-db45a4d07d — Victim-majority condition (≥5/9) for Global THRESHOLD_RAISE unjustified

- **Category:** STATISTICS
- **Severity:** S1
- **Location:** §5 / results
- **Audit sources (2/10):** AUDIT-04;AUDIT-10
- **Action type:** PAPER_FIX

### F-0b45246ccd — Table 1: bold convention direction not stated (higher-is-better vs. lower-is-better unclear)

- **Category:** TABLES
- **Severity:** S1
- **Location:** Table 1
- **Audit sources (4/10):** AUDIT-04;AUDIT-05;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-0c0628ecf5 — Table 1: BAP10 / P10 / 'Worst BA' abbreviations undefined — no footnote or legend

- **Category:** TABLES
- **Severity:** S1
- **Location:** Table 1
- **Audit sources (6/10):** AUDIT-04;AUDIT-06;AUDIT-07;AUDIT-08;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-d5257ddef0 — Table 2: Random-Benign control not shown as explicit rows — control condition invisible

- **Category:** TABLES
- **Severity:** S1
- **Location:** Table 2
- **Audit sources (10/10):** AUDIT-01;AUDIT-02;AUDIT-03;AUDIT-04;AUDIT-05;AUDIT-06;AUDIT-07;AUDIT-08;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-1efee522d3 — Figure 1: no color legend; attack operation and data flow unclear

- **Category:** VISUALS
- **Severity:** S1
- **Location:** Figure 1
- **Audit sources (3/10):** AUDIT-01;AUDIT-03;AUDIT-09
- **Action type:** PAPER_FIX

### F-61c8046eee — Figure 1: diagram labels "training phase defended" but calibration is the attack stage

- **Category:** VISUALS
- **Severity:** S1
- **Location:** Figure 1
- **Audit sources (3/10):** AUDIT-01;AUDIT-03;AUDIT-09
- **Action type:** PAPER_FIX

### F-715903e3a8 — Figure 3: Global line nearly invisible at current y-axis scale — needs inset or separate subplot

- **Category:** VISUALS
- **Severity:** S1
- **Location:** Figure 3
- **Audit sources (1/10):** AUDIT-10
- **Action type:** PAPER_FIX

### F-bf066608e1 — Figure 2: only seed 0 shown without justification that seed 0 is representative; Cluster condition absent

- **Category:** VISUALS
- **Severity:** S1
- **Location:** Figure 2
- **Audit sources (10/10):** AUDIT-01;AUDIT-02;AUDIT-03;AUDIT-04;AUDIT-05;AUDIT-06;AUDIT-07;AUDIT-08;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-d17dbb4517 — Figure 3: Random-Benign control not plotted — invisible control condition

- **Category:** VISUALS
- **Severity:** S1
- **Location:** Figure 3
- **Audit sources (10/10):** AUDIT-01;AUDIT-02;AUDIT-03;AUDIT-04;AUDIT-05;AUDIT-06;AUDIT-07;AUDIT-08;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

### F-f457b6ac9d — All figures appear to be blurry/low-resolution screenshots, not vector or high-DPI exports

- **Category:** VISUALS
- **Severity:** S1
- **Location:** Figures 1-3
- **Audit sources (1/10):** AUDIT-05
- **Action type:** PAPER_FIX

### F-cb5cbb01cf — Local vs. Global P10 Macro-F1 tradeoff not discussed in results narrative

- **Category:** PRESENTATION
- **Severity:** S2
- **Location:** §5
- **Audit sources (2/10):** AUDIT-01;AUDIT-03
- **Action type:** PAPER_FIX

### F-cc15d7c365 — Table 2: dense layout makes comparison across threshold policies difficult

- **Category:** TABLES
- **Severity:** S2
- **Location:** Table 2
- **Audit sources (3/10):** AUDIT-01;AUDIT-09;AUDIT-10
- **Action type:** PAPER_FIX

