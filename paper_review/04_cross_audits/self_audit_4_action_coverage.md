# Self-Audit 4: Action Coverage Check

**Question:** Does every S0 and S1 finding have at least one action? Are any actions orphaned (no finding)?

---

## S0 Findings → Actions

| Finding ID | Title | Action(s) | Covered? |
|------------|-------|-----------|----------|
| F-82f9dcceaf | Spillover contradiction | A-5f02c65612 (P0) | YES |
| F-6a6b0d6949 | Score-level proxy | A-e102f26659 (P1) | YES |
| F-a620caf003 | Reference [12] wrong | A-a098e39ee7 (P0) | YES |
| F-f80d97cb0e | "4 pairs" inconsistency | A-bc70838a10 (P0) | YES |
| F-0993b70fbb | Cluster Macro-F1 ±0.000 | A-db7bcc5fcf (P0) | YES |

**All S0 findings covered. ✓**

---

## S1 Findings → Actions

| Finding ID | Title | Action(s) | Covered? |
|------------|-------|-----------|----------|
| F-1de8c78e14 | Gate-1 before defined | A-52a92f30db (P2) | YES |
| F-489c8b7ce6 | Victim ΔTPR ambiguous | A-8db2e8afa8 (P2) | YES |
| F-53f9f172ea | "every defense" | A-f8c713ec0c (P1) | YES |
| F-79e79bc668 | Harm scenario missing | A-d9bc51f540 (P2) | YES |
| F-810820f994 | "30-80 Mirai flows" | A-855a2d7014 (P2) | YES |
| F-cd3c497156 | Deployment language | A-f8c713ec0c (P1) | YES |
| F-1f6dfe00f2 | Lowering ΔTPR framing | A-01a7255dbd (P1) | YES |
| F-4521a0a59c | "succeeds" overclaims | A-01a7255dbd (P1) | YES |
| F-653ddd1df9 | Lowering Global cond. | A-01a7255dbd (P1) | YES |
| F-b808e36c15 | Defense sketch missing | A-c8058bdd1f (P2) | YES |
| F-bfeb175017 | CV(FPR) late | A-e91b1d847d (P2) | YES |
| F-f8e2e92b2d | No paper roadmap | A-01d8c9ea7a (P2) | YES |
| F-8993694ae8 | Attack vs. vuln language | A-e102f26659 (P1) + A-19e2ac96a6 (P2) | YES |
| F-b5bfa0c742 | Formal equation missing | A-f47168b200 (P2) | YES |
| F-e617b74787 | gray-box imprecise | A-39a0f86ebd (P2) | YES |
| F-1249c7034d | "no prior work" | A-5ccfae0eed (P1) | YES |
| F-260ecb76ac | No 2023-2024 citations | A-023cc3fd20 (P2) | YES |
| F-2ea27ded3d | K-means++ not cited | A-023cc3fd20 (P2) | YES |
| F-7a835d76b5 | No comparison table | A-5ccfae0eed (P1) | YES |
| F-9c91e712ec | Kloft & Laskov | A-5ccfae0eed (P1) | YES |
| F-16a073b134 | FedAvg role ambiguous | A-f3e11e1509 (P1) | YES |
| F-3ef85e6456 | Train/cal/test split | A-f3e11e1509 (P1) | YES |
| F-447e660ce4 | FedAvg hyperparams | A-f3e11e1509 (P1) | YES |
| F-4ad5dce40c | Feature pipeline | A-f3e11e1509 (P1) | YES |
| F-4e13c25efd | AE architecture | A-f3e11e1509 (P1) | YES |
| F-56f3c530ef | No artifact statement | A-664b8440ed (P1) | YES |
| F-5e5517e25d | Spillover not quantified | A-e31849338f (P1) | YES |
| F-8ae6c046f0 | Cluster under-specified | A-e6f405cf6f (P2) | YES |
| F-adf1c918ff | Cluster seed variance | A-e6f405cf6f (P2) | YES |
| F-64588f32e0 | N=10 bootstrap CIs | A-df1fb64bdd (P1) | YES |
| F-95a95d973c | Three-gate bespoke | A-9c654c5a5e (P1) | YES |
| F-b02c973ba2 | Gate constants unjust. | A-9c654c5a5e (P1) | YES |
| F-b6a2ecf3ad | N notation conflict | A-6876713dc4 (P2) | YES |
| F-db45a4d07d | Victim-majority cond. | A-2407be7432 (P2) | YES |
| F-0b45246ccd | Bold direction | A-2849af9957 (P2) | YES |
| F-0c0628ecf5 | BAP10 undefined | A-741211d451 (P2) | YES |
| F-d5257ddef0 | RB not in Table 2 | A-1975d011a9 (P1) | YES |
| F-1efee522d3 | Figure 1 no legend | A-40607a57a6 (P2) | YES |
| F-61c8046eee | Fig 1 "training" label | A-40607a57a6 (P2) | YES |
| F-715903e3a8 | Fig 3 Global invisible | A-213529531a (P2) | YES |
| F-bf066608e1 | Figure 2 seed 0 + Cluster | A-984973914d (P1) | YES |
| F-d17dbb4517 | Figure 3 RB not plotted | A-1975d011a9 (P1) | YES |
| F-f457b6ac9d | Figures blurry | A-a1dbe8cc63 (P3) | YES |
| F-489c8b7ce6 | Victim ΔTPR ambiguous | A-8db2e8afa8 (P2) | YES |

**All S1 findings covered. ✓**

---

## S2 Findings → Actions

| Finding ID | Title | Action | Covered? |
|------------|-------|--------|----------|
| F-cb5cbb01cf | Local vs. Global P10 | A-418234b961 (P3) | YES |
| F-cc15d7c365 | Table 2 dense | A-c5f373c929 (P3) | YES |

**All S2 findings covered. ✓**

---

## Orphaned Actions Check

Scan all 36 actions to ensure each references at least one finding:

All 36 actions were constructed with explicit finding_id references. Cross-checking the action register CSV: no orphaned actions detected.

---

## Experiment Critique Ledger Coverage

| EXP-ID | Critique | Disposition | Paper Consequence |
|--------|----------|-------------|-------------------|
| EXP-01 | Single dataset | ACKNOWLEDGE | Sentence in §7 — not in action register (low-effort text addition) |
| EXP-02 | Nine clients | ACKNOWLEDGE | Sentence in §7 |
| EXP-03 | No multi-client | ALREADY_SCOPED + ACKNOWLEDGE | Sentence in §7 |
| EXP-04 | No defense baseline | ALREADY_SCOPED | Defense sketch via A-c8058bdd1f |
| EXP-05 | q=0.95 fixed | ACKNOWLEDGE | Sentence in §4/§7 |
| EXP-06 | No other FL algorithms | ROADMAP_ONLY | Optional Future Work |
| EXP-07 | No other detectors | ALREADY_SCOPED | None |
| EXP-08 | No traffic adversary | ACKNOWLEDGE | Covered by A-e102f26659 |
| EXP-09 | No temporal analysis | ROADMAP_ONLY | None |

The experiment critique ledger items (EXP-01 through EXP-05, EXP-08) that require a sentence in §7 are not individually tracked as actions because they are all subsumed by a single, implied edit: "review and strengthen the limitations section." This is by design — limitations text changes are too fine-grained to track at action level.

---

## Verdict

**100% coverage: all 50 findings are addressed by at least one action or an explicit REJECT/DEFER decision.** No orphaned actions detected. The experiment critique ledger items requiring text changes are acknowledged without requiring dedicated action entries.
