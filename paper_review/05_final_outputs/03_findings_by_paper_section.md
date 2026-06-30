# Findings by Paper Section

This view organizes all findings by where they appear in the paper, useful for working through the paper section-by-section during revision.

---

## Abstract

| Finding | Severity | Action |
|---------|----------|--------|
| F-1f6dfe00f2 Lowering attack: ΔTPR framing misleading | S1 | A-01a7255dbd (P1) |
| F-4521a0a59c "succeeds" overclaims | S1 | A-01a7255dbd (P1) |
| F-53f9f172ea "every defense" universal claim | S1 | A-f8c713ec0c (P1) |
| F-cd3c497156 Deployment language | S1 | A-f8c713ec0c (P1) |
| F-1de8c78e14 "100% Gate-1 pass rate" before defined | S1 | A-52a92f30db (P2) |
| F-6a6b0d6949 Score-level proxy — needs caveat | S0 | A-e102f26659 (P1) |

---

## §1 Introduction / Contributions

| Finding | Severity | Action |
|---------|----------|--------|
| F-82f9dcceaf Spillover contradiction (Contributions vs. §4.2/§5.4) | S0 | A-5f02c65612 (P0) |
| F-f80d97cb0e "4 source-objective pairs" inconsistency | S0 | A-bc70838a10 (P0) |
| F-56f3c530ef No artifact/code availability statement | S1 | A-664b8440ed (P1) |
| F-79e79bc668 Concrete harm scenario missing | S1 | A-d9bc51f540 (P2) |
| F-f8e2e92b2d No paper roadmap | S1 | A-01d8c9ea7a (P2) |
| F-1249c7034d "no prior work" too strong | S1 | A-5ccfae0eed (P1) |

---

## §2 Threat Model / Setup

| Finding | Severity | Action |
|---------|----------|--------|
| F-4e13c25efd AE architecture missing | S1 | A-f3e11e1509 (P1) |
| F-447e660ce4 FedAvg hyperparameters missing | S1 | A-f3e11e1509 (P1) |
| F-3ef85e6456 Train/calibration/test split missing | S1 | A-f3e11e1509 (P1) |
| F-4ad5dce40c Feature pipeline missing | S1 | A-f3e11e1509 (P1) |
| F-16a073b134 FedAvg role ambiguous | S1 | A-f3e11e1509 (P1) |
| F-e617b74787 gray-box imprecise | S1 | A-39a0f86ebd (P2) |
| F-8993694ae8 attack vs. characterization inconsistency | S1 | A-e102f26659 (P1) |
| F-bfeb175017 CV(FPR) defined late | S1 | A-e91b1d847d (P2) |

---

## §3 Related Work

| Finding | Severity | Action |
|---------|----------|--------|
| F-a620caf003 Reference [12] wrong citation | S0 | A-a098e39ee7 (P0) |
| F-9c91e712ec Kloft & Laskov not contrasted | S1 | A-5ccfae0eed (P1) |
| F-7a835d76b5 No comparison table | S1 | A-5ccfae0eed (P1) |
| F-260ecb76ac No 2023-2024 FL citations | S1 | A-023cc3fd20 (P2) |
| F-2ea27ded3d K-means++ not cited | S1 | A-023cc3fd20 (P2) |

---

## §4 Method

| Finding | Severity | Action |
|---------|----------|--------|
| F-b5bfa0c742 Formal contamination equation absent | S1 | A-f47168b200 (P2) |
| F-8ae6c046f0 Cluster policy under-specified | S1 | A-e6f405cf6f (P2) |
| F-adf1c918ff Cluster assignment varies by seed | S1 | A-e6f405cf6f (P2) |

---

## §5 Results

| Finding | Severity | Action |
|---------|----------|--------|
| F-1f6dfe00f2 Lowering: ΔTPR framing misleading | S1 | A-01a7255dbd (P1) |
| F-653ddd1df9 Lowering: Global conditionality unexplained | S1 | A-01a7255dbd (P1) |
| F-5e5517e25d Spillover not quantified | S1 | A-e31849338f (P1) |
| F-489c8b7ce6 Victim ΔTPR for Global ambiguous | S1 | A-8db2e8afa8 (P2) |
| F-810820f994 "30-80 Mirai flows" unsubstantiated | S1 | A-855a2d7014 (P2) |
| F-b808e36c15 Defense sketch missing | S1 | A-c8058bdd1f (P2) |
| F-cb5cbb01cf Local vs. Global P10 tradeoff undiscussed | S2 | A-418234b961 (P3) |

---

## §6 Statistics

| Finding | Severity | Action |
|---------|----------|--------|
| F-64588f32e0 N=10 bootstrap CIs unreliable | S1 | A-df1fb64bdd (P1) |
| F-b02c973ba2 Gate constants unjustified | S1 | A-9c654c5a5e (P1) |
| F-95a95d973c Three-gate framework bespoke | S1 | A-9c654c5a5e (P1) |
| F-db45a4d07d Victim-majority condition unjustified | S1 | A-2407be7432 (P2) |
| F-b6a2ecf3ad N notation conflict | S1 | A-6876713dc4 (P2) |

---

## Table 1

| Finding | Severity | Action |
|---------|----------|--------|
| F-0993b70fbb Cluster Macro-F1 ± 0.000 | S0 | A-db7bcc5fcf (P0) |
| F-0c0628ecf5 BAP10/P10/Worst BA undefined | S1 | A-741211d451 (P2) |
| F-0b45246ccd Bold direction not stated | S1 | A-2849af9957 (P2) |

---

## Table 2

| Finding | Severity | Action |
|---------|----------|--------|
| F-d5257ddef0 Random-Benign not shown as rows | S1 | A-1975d011a9 (P1) |
| F-0b45246ccd Bold direction not stated | S1 | A-2849af9957 (P2) |
| F-cc15d7c365 Dense layout | S2 | A-c5f373c929 (P3) |

---

## Figure 1

| Finding | Severity | Action |
|---------|----------|--------|
| F-1efee522d3 No color legend | S1 | A-40607a57a6 (P2) |
| F-61c8046eee "training defended" mislabeling | S1 | A-40607a57a6 (P2) |

---

## Figure 2

| Finding | Severity | Action |
|---------|----------|--------|
| F-bf066608e1 Only seed 0; Cluster absent | S1 | A-984973914d (P1) |

---

## Figure 3

| Finding | Severity | Action |
|---------|----------|--------|
| F-d17dbb4517 Random-Benign not plotted | S1 | A-1975d011a9 (P1) |
| F-715903e3a8 Global line invisible at current scale | S1 | A-213529531a (P2) |

---

## All Figures (Visual Quality)

| Finding | Severity | Action |
|---------|----------|--------|
| F-f457b6ac9d Figures blurry/low-resolution | S1 | A-a1dbe8cc63 (P3) |

---

## Revision Order Recommendation

Work through the paper in this order for maximum efficiency:

1. **Abstract** — 6 issues, all text (≈1 hour)
2. **§1 Introduction** — 6 issues, mostly text (≈1 hour)
3. **§2 Setup** — Add reproducibility table (the single biggest action) (≈3 hours)
4. **§3 Related Work** — Reference fix + comparison table (≈2 hours)
5. **§4 Method** — Contamination equation + Cluster spec (≈1 hour)
6. **§5 Results** — Spillover table + lowering framing (≈2 hours)
7. **§6 Statistics** — Gate constants + bootstrap caveat + notation (≈1 hour)
8. **Tables 1+2** — Annotations, Random-Benign rows (≈2 hours)
9. **Figures 1-3** — Legend, scale, RB line, Cluster, seeds (≈3 hours)
