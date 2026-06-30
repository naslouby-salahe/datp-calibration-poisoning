# Duplicate Cluster Map

This document records finding-level clusters where multiple audits raised the same critique.
The canonical finding ID (F-*) is used throughout the action register — not per-audit local IDs.

---

## Cluster Methodology

Two findings are clustered when they share the same underlying paper flaw, regardless of whether the reviewer phrased it identically. Findings from duplicate audits (AUDIT-01≡AUDIT-03, AUDIT-06≡AUDIT-07) contribute two votes to the same cluster.

---

## Top-Coverage Clusters (10/10 audits)

These clusters represent universal consensus — every auditor flagged this issue.

| Finding ID | Title | Audit Count |
|------------|-------|-------------|
| F-6a6b0d6949 | Score-level proxy / realism gap | 10/10 |
| F-4e13c25efd | AE architecture missing | 10/10 |
| F-56f3c530ef | No artifact/code availability statement | 10/10 |
| F-1f6dfe00f2 | Lowering attack: positive ΔTPR framing misleading | 10/10 |
| F-bf066608e1 | Figure 2: only seed 0, Cluster absent | 10/10 |
| F-d17dbb4517 | Figure 3: Random-Benign not plotted | 10/10 |
| F-d5257ddef0 | Table 2: Random-Benign not shown as rows | 10/10 |

---

## High-Coverage Clusters (6-9/10 audits)

| Finding ID | Title | Audit Count |
|------------|-------|-------------|
| F-447e660ce4 | FedAvg hyperparameters missing | 8/10 |
| F-5e5517e25d | Spillover not directly quantified | 7/10 |
| F-64588f32e0 | N=10 bootstrap CIs unreliable | 6/10 |
| F-0c0628ecf5 | Table 1: BAP10/P10 undefined | 6/10 |

---

## Medium-Coverage Clusters (3-5/10 audits)

| Finding ID | Title | Audit Count |
|------------|-------|-------------|
| F-53f9f172ea | "every defense" universal claim | 5/10 |
| F-7a835d76b5 | No related-work comparison table | 5/10 |
| F-3ef85e6456 | Train/calibration/test split missing | 5/10 |
| F-9c91e712ec | Kloft & Laskov not explicitly contrasted | 4/10 |
| F-b02c973ba2 | Gate constants unjustified | 4/10 |
| F-bfeb175017 | CV(FPR) defined late/inconsistently | 4/10 |
| F-0b45246ccd | Table 1: bold direction not stated | 4/10 |
| F-1efee522d3 | Figure 1: no color legend | 3/10 |
| F-61c8046eee | Figure 1: "training defended" mislabeling | 3/10 |
| F-8993694ae8 | attack vs. vulnerability characterization | 3/10 |
| F-e617b74787 | gray-box label imprecise | 3/10 |
| F-4ad5dce40c | Feature pipeline missing | 3/10 |
| F-1249c7034d | "no prior work" claim too strong | 3/10 |
| F-95a95d973c | Three-gate framework bespoke | 3/10 |
| F-810820f994 | "30-80 Mirai flows" underived | 2/10 |
| F-adf1c918ff | Cluster assignment varies by seed | 3/10 |
| F-b808e36c15 | Defense sketch missing | 3/10 |
| F-1de8c78e14 | "100% Gate-1 pass rate" before definition | 3/10 |
| F-4521a0a59c | "succeeds" overclaims in abstract | 3/10 |
| F-f80d97cb0e | "4 source-objective pairs" vs. 3 described | 3/10 |
| F-82f9dcceaf | Spillover structural contradiction | 2/10 |
| F-8ae6c046f0 | Cluster policy under-specified | 2/10 |
| F-260ecb76ac | No 2023-2024 citations | 2/10 |
| F-653ddd1df9 | Lowering attack Global conditionality | 2/10 |
| F-b5bfa0c742 | Formal contamination equation absent | 2/10 |
| F-db45a4d07d | Victim-majority condition unjustified | 2/10 |
| F-f8e2e92b2d | No paper roadmap in Introduction | 2/10 |
| F-cd3c497156 | Deployment language out of scope | 3/10 |

---

## Single-Auditor Findings (1/10 — from AUDIT-10, most critical)

These were raised by only AUDIT-10 (grade 6.1, most critical audit). Despite single-source, several are high-severity:

| Finding ID | Severity | Title |
|------------|----------|-------|
| F-a620caf003 | S0 | Reference [12] wrong citation |
| F-0993b70fbb | S0 | Cluster Macro-F1 ± 0.000 unexplained |
| F-16a073b134 | S1 | FedAvg role architecturally ambiguous |
| F-b6a2ecf3ad | S1 | N notation conflict in §6 |
| F-715903e3a8 | S1 | Figure 3: Global line invisible |
| F-489c8b7ce6 | S1 | Victim ΔTPR for Global ambiguous |
| F-79e79bc668 | S1 | Concrete harm scenario missing |
| F-2ea27ded3d | S1 | K-means++ not cited |
| F-f457b6ac9d | S1 | Figures blurry/low-resolution |

---

## Notes on Duplicate Audits

- **AUDIT-01 ≡ AUDIT-03**: Identical text. Their findings are credited to both IDs — the finding_sources field in findings_master.csv lists both. This inflates vote counts for all findings from Audit 1 by 1 (e.g., a finding voted by Audit 1 and no others gets count=2 due to the identical copy).
- **AUDIT-06 ≡ AUDIT-07**: Same treatment.
- **Conservative interpretation**: If vote count matters for prioritization, subtract 1 from counts for clusters sourced exclusively from the {01,03} or {06,07} duplicate pairs.
