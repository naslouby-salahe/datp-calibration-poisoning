# AUDIT-10 Normalized

**Source file:** Paper Audit 9.md  
**SHA-256:** c3abc4abbb3463b12365c986bc8d7d089a4312f6e2a679db05ff1c78ea345fb5  
**Grade:** 6.1 / 10  
**Recommendation:** Borderline / Weak Reject (most critical audit)  
**Duplicate flag:** None  
**Content quality:** Full — no URL embedding degradation

---

## Reviewer Summary

The most critical audit with three explicitly "FATAL" flags. This reviewer has the deepest technical engagement. Fatal issues: (a) AE architecture + FedAvg hyperparameters missing — experiment unreproducible, (b) "4 source-objective pairs" inconsistency — only 3 described, (c) Reference [12] (cited as L'heureux 2017) is a wrong citation — the cited paper does not support the claimed finding about threshold sensitivity. Major issues: (d) N=10 bootstrap CIs have unreliable 95% coverage (percentile bootstrap needs n≥30), (e) Table 1 Cluster Macro-F1 = 0.299 ± 0.000 is unexplained (zero std impossible unless all seeds agree exactly), (f) FedAvg role architecturally ambiguous ("using FedAvg for feature extraction" is misleading), (g) N notation conflict in §6 (N=9 federation vs. N=calibration set size). Also identified: "30-80 undetected Mirai flows" claim with no derivation, gate constants unjustified.

---

## Findings Extracted

### S0 — FATAL Issues

| # | Location | Finding |
|---|----------|---------|
| NF-A10-01 | §2 | **AE architecture + FedAvg hyperparameters missing** — makes experiment unreproducible at a fundamental level |
| NF-A10-02 | §4 / §1 | **"4 source-objective pairs" inconsistency** — only 3 attack conditions described; counting error or missing description |
| NF-A10-03 | §3 / references | **Reference [12] is a wrong citation** — L'heureux et al. 2017 is cited as supporting "threshold sensitivity to calibration data" but does not contain this claim. Citation fabrication or misassignment. |

### S1 — Major Weaknesses

| # | Location | Finding |
|---|----------|---------|
| MW-A10-01 | §6 / statistics | N=10 bootstrap CIs: percentile bootstrap needs n≥30 for reliable 95% coverage; BCa recommended |
| MW-A10-02 | Table 1 | Cluster Macro-F1 = 0.299 ± **0.000** — zero standard deviation unexplained; implies all 10 seeds give identical Macro-F1, which is suspicious |
| MW-A10-03 | §2 | FedAvg role ambiguous: "using FedAvg for feature extraction" is architecturally misleading — FedAvg aggregates weights, not features |
| MW-A10-04 | §6 | N notation conflict: same symbol N used for federation size (9) and calibration set size (≈2622) in same section |
| MW-A10-05 | §5.2 | "30-80 undetected Mirai flows" — no derivation, no traffic model, no citation |
| MW-A10-06 | §6 | Gate constants (0.1 × IQR, 0.01 × IQR) unjustified — appear post-hoc |
| MW-A10-07 | Figure 3 | Global line nearly invisible at current y-axis scale — needs inset or separate subplot |
| MW-A10-08 | §5 | Victim ΔTPR for Global ambiguous — unclear if reporting poisoned client's ΔTPR or average across all 9 clients |
| MW-A10-09 | §5 | Concrete motivating harm scenario (e.g., specific IoT attacker goal) missing |
| MW-A10-10 | §3 | K-means++ not cited (Arthur & Vassilvitskii 2007) |
| MW-A10-11 | §3 | No 2023-2024 FL security citations |

### S2 — Minor

| # | Location | Finding |
|---|----------|---------|
| MI-A10-01 | §1 Contributions item 3 | Bold convention not stated |
| MI-A10-02 | Figure 2 | Cluster condition absent; seed 0 only |
| MI-A10-03 | Table 1 | BAP10/P10 undefined |
| MI-A10-04 | §2 | gray-box definition anchoring missing |
| MI-A10-05 | §1 | Realism caveat missing from abstract |
| MI-A10-06 | §1 | No artifact/code availability statement |

### STRUCTURAL CONTRADICTION (deserves separate flag)

| # | Location | Finding |
|---|----------|---------|
| SC-A10-01 | §1 Contributions vs. §4.2/§5.4 | **Cluster spillover contradiction**: Contributions item 3 states Local and Cluster have "no cross-client spillover" but §4.2 and §5.4 describe Cluster as causing intra-cluster spillover to non-victim devices within same cluster — direct logical contradiction |

---

## Experiment-Scope Critiques (OUTSIDE_FROZEN_SCOPE)

- Single dataset (N-BaIoT only)
- Nine clients too small for generalization
- No multi-client collusion
- No defense baseline
- q=0.95 fixed, no sensitivity analysis

---

## Reviewer Verdict

> "Borderline reject, grade 6.1. Three fatal issues prevent acceptance in current form: missing architecture (unreproducible), '4 pairs' inconsistency (internal inconsistency), wrong citation [12] (credibility risk). The zero-std Cluster Macro-F1 is alarming and may indicate a data or reporting bug. Fix all three fatal issues and the Table 1 anomaly before resubmission."
