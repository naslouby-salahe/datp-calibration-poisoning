# Wording, Visuals, and Sections Ledger

This ledger collects every wording, visual, and section-level issue that does not require a new experiment. Each entry has a concrete fix.

---

## WORDING ISSUES

### W-01 — "structurally outside scope of every defense"
- **Location:** §1 Abstract / Introduction
- **Finding:** F-53f9f172ea
- **Audits:** AUDIT-01, AUDIT-03, AUDIT-04, AUDIT-08, AUDIT-09 (5/10)
- **Problem:** Undefendable universal claim. No paper can verify "every defense."
- **Fix:** → "We identify no existing defense that directly monitors the calibration channel."
- **Action:** A-f8c713ec0c (P1)

### W-02 — "operationally meaningful in IoT deployment contexts"
- **Location:** §1 Abstract / Introduction
- **Finding:** F-cd3c497156
- **Audits:** AUDIT-01, AUDIT-03, AUDIT-04 (3/10)
- **Problem:** Deployment language is out of scope per frozen boundary.
- **Fix:** Remove the phrase. The contribution is experimental characterization, not deployment readiness.
- **Action:** A-f8c713ec0c (P1)

### W-03 — "no prior work" (absolute causal claim)
- **Location:** §3 Related Work / §1
- **Finding:** F-1249c7034d
- **Audits:** AUDIT-04, AUDIT-08, AUDIT-10 (3/10)
- **Problem:** Kloft & Laskov 2012 exists; "no prior work" is factually risky.
- **Fix:** → "To the best of our knowledge, no prior work has studied calibration-channel poisoning in federated threshold policies."
- **Action:** A-5ccfae0eed (P1)

### W-04 — "attack" vs "vulnerability characterization" inconsistency
- **Location:** Abstract vs. §6
- **Finding:** F-8993694ae8
- **Audits:** AUDIT-06, AUDIT-07, AUDIT-10 (3/10)
- **Problem:** Framing inconsistency signals epistemic confusion.
- **Fix:** Use "attack" in abstract/contributions. Use "characterization" only in §6 where explicitly scoped, with a bridging sentence.
- **Action:** A-19e2ac96a6 (P2) + A-e102f26659 (P1)

### W-05 — lowering attack "succeeds" overclaims
- **Location:** Abstract
- **Finding:** F-4521a0a59c
- **Audits:** AUDIT-01, AUDIT-03, AUDIT-04 (3/10)
- **Problem:** "Succeeds" without specifying what success means.
- **Fix:** → "achieves statistically significant increase in false positive rate under the GLOBAL_THRESHOLD policy."
- **Action:** A-01a7255dbd (P1)

### W-06 — positive ΔTPR sounds beneficial for lowering attack
- **Location:** Abstract + §5.3
- **Finding:** F-1f6dfe00f2
- **Audits:** All 10
- **Problem:** Increased TPR is usually good; framing lowering attack as ΔTPR-positive is counterintuitive.
- **Fix:** Lead with ΔFPR: "The LOW_SCORE_BENIGN strategy raises the false positive rate by X±Y pp under GLOBAL_THRESHOLD, increasing alarm burden." Move ΔTPR to secondary position.
- **Action:** A-01a7255dbd (P1)

### W-07 — "100% Gate-1 pass rate" before Gate-1 defined
- **Location:** Abstract / §1
- **Finding:** F-1de8c78e14
- **Audits:** AUDIT-04, AUDIT-09, AUDIT-10 (3/10)
- **Fix:** Either (a) forward-reference "Gate-1 (see §6)" or (b) rephrase: "all conditions exceeded the material-shift threshold (Gate-1, defined in §6)."
- **Action:** A-52a92f30db (P2)

### W-08 — "30-80 undetected Mirai flows" claim with no derivation
- **Location:** §5.2
- **Finding:** F-810820f994
- **Audits:** AUDIT-04, AUDIT-10 (2/10)
- **Fix:** Either derive from dataset stats + ΔTPR values, or replace with: "the attack causes a non-trivial fraction of Mirai traffic to evade detection."
- **Action:** A-855a2d7014 (P2)

### W-09 — gray-box label imprecise
- **Location:** §2 Threat Model
- **Finding:** F-e617b74787
- **Fix:** Add definition paragraph: "We assume a gray-box adversary who knows the threshold policy family and the calibration mechanism but does not know: model weights, other clients' calibration data, or the aggregate score distribution."
- **Action:** A-39a0f86ebd (P2)

### W-10 — Global lowering conditionality unexplained
- **Location:** §5 Results
- **Finding:** F-653ddd1df9
- **Fix:** Add a sentence explaining why lowering works for Global but not Local/Cluster: the Global threshold aggregates across all clients; poisoning one client's calibration buffer can pull the global aggregate below the detection quantile. Local and Cluster thresholds are client-scoped, so a single-client attack affects only that client.
- **Action:** A-01a7255dbd (P1, subsumed)

### W-11 — victim ΔTPR for Global ambiguous
- **Location:** §5 / Table 2
- **Finding:** F-489c8b7ce6
- **Fix:** Add subscript notation: ΔTPR_v (victim client) vs. ΔTPR_fleet (average across all 9 clients). Clarify which is reported.
- **Action:** A-8db2e8afa8 (P2)

### W-12 — N notation conflict in §6
- **Location:** §6
- **Finding:** F-b6a2ecf3ad
- **Fix:** Use |F|=9 for federation size and n_cal ≈ 2622 for calibration buffer size.
- **Action:** A-6876713dc4 (P2)

### W-13 — FedAvg role architecturally ambiguous
- **Location:** §2
- **Finding:** F-16a073b134
- **Fix:** Replace "using FedAvg for feature extraction" → "FedAvg aggregates the autoencoder weights across clients; each client then uses its local aggregated model for anomaly scoring."
- **Action:** A-f3e11e1509 (P1, subsumed)

### W-14 — CV(FPR) defined late and inconsistently
- **Location:** §2 / §5
- **Finding:** F-bfeb175017
- **Fix:** Add to §2 notation: "CV(FPR) = σ(FPR)/μ(FPR) is the coefficient of variation of the false positive rate, measuring dispersion across threshold conditions."
- **Action:** A-e91b1d847d (P2)

---

## FIGURE ISSUES

### V-01 — Figure 2: only seed 0; Cluster absent
- **Finding:** F-bf066608e1
- **Audits:** 10/10
- **Fix:** Add Cluster condition. Show mean±std across seeds or add justification for seed 0 in caption.
- **Action:** A-984973914d (P1)

### V-02 — Figure 3: Random-Benign not plotted
- **Finding:** F-d17dbb4517
- **Audits:** 10/10
- **Fix:** Add RANDOM_BENIGN as a dashed line to Figure 3.
- **Action:** A-1975d011a9 (P1)

### V-03 — Figure 3: Global line invisible at current scale
- **Finding:** F-715903e3a8
- **Audits:** AUDIT-10 (1/10)
- **Fix:** Dual y-axis, inset, or log scale.
- **Action:** A-213529531a (P2)

### V-04 — Figure 1: no color legend; attack operation unclear
- **Finding:** F-1efee522d3
- **Audits:** AUDIT-01, AUDIT-03, AUDIT-09 (3/10)
- **Fix:** Add color/symbol legend. Clarify data flow arrows.
- **Action:** A-40607a57a6 (P2)

### V-05 — Figure 1: "training phase defended" mislabeling
- **Finding:** F-61c8046eee
- **Audits:** AUDIT-01, AUDIT-03, AUDIT-09 (3/10)
- **Fix:** Relabel to reflect calibration as the attack stage. Training phase is unaffected.
- **Action:** A-40607a57a6 (P2)

### V-06 — All figures blurry/low resolution
- **Finding:** F-f457b6ac9d
- **Audits:** AUDIT-05 (1/10)
- **Fix:** Regenerate as PDF/SVG or 300 DPI PNG.
- **Action:** A-a1dbe8cc63 (P3)

---

## TABLE ISSUES

### T-01 — Table 1: BAP10 / P10 / Worst BA undefined
- **Finding:** F-0c0628ecf5
- **Audits:** AUDIT-04, AUDIT-06, AUDIT-07, AUDIT-08, AUDIT-09, AUDIT-10 (6/10)
- **Fix:** Add footnote to Table 1 defining each abbreviation.
- **Action:** A-741211d451 (P2)

### T-02 — Table 1 + Table 2: bold direction not stated
- **Finding:** F-0b45246ccd
- **Audits:** AUDIT-04, AUDIT-05, AUDIT-09, AUDIT-10 (4/10)
- **Fix:** Add to caption: "Bold indicates [higher/lower] values are [better for attacker / worse for defender]."
- **Action:** A-2849af9957 (P2)

### T-03 — Table 2: Random-Benign not shown as rows
- **Finding:** F-d5257ddef0
- **Audits:** 10/10
- **Fix:** Add RANDOM_BENIGN rows. See A-1975d011a9 (P1).
- **Action:** A-1975d011a9 (P1)

### T-04 — Table 2: dense layout
- **Finding:** F-cc15d7c365
- **Audits:** AUDIT-01, AUDIT-09, AUDIT-10 (3/10)
- **Fix:** Split into raise vs. lower sub-tables, or landscape layout.
- **Action:** A-c5f373c929 (P3)

---

## SECTION / STRUCTURE ISSUES

### S-01 — No paper roadmap in Introduction
- **Finding:** F-f8e2e92b2d
- **Audits:** AUDIT-06, AUDIT-07 (2/10)
- **Fix:** Add "The remainder of the paper is organized as follows: §2…§7…" to §1.
- **Action:** A-01d8c9ea7a (P2)

### S-02 — No formal contamination equation
- **Finding:** F-b5bfa0c742
- **Audits:** AUDIT-06, AUDIT-07 (2/10)
- **Fix:** Add equation defining REPLACE-FIXED-BUDGET in §4.
- **Action:** A-f47168b200 (P2)

### S-03 — No defense sketch in Discussion
- **Finding:** F-b808e36c15
- **Audits:** AUDIT-04, AUDIT-06, AUDIT-07 (3/10)
- **Fix:** Add paragraph in §5/Discussion: monitoring incoming calibration score distributions, threshold server-side validation, secure aggregation of calibration buffers.
- **Action:** A-c8058bdd1f (P2)

### S-04 — Cluster policy under-specified
- **Finding:** F-8ae6c046f0
- **Audits:** AUDIT-02, AUDIT-10 (2/10)
- **Fix:** Add to §4: features used for K-means++, K=3 justification, seed-variance in cluster assignments.
- **Action:** A-e6f405cf6f (P2)

### S-05 — No concrete motivating scenario in §1
- **Finding:** F-79e79bc668
- **Audits:** AUDIT-10 (1/10)
- **Fix:** Add 1-2 sentences painting a concrete attack scenario.
- **Action:** A-d9bc51f540 (P2)
