# Action Register

**Total actions:** 36  
**P0 (Do now / reject risk):** 4  
**P1 (Required for submission):** 11  
**P2 (Strongly recommended):** 18  
**P3 (Nice to have):** 3

_Action IDs are deterministic SHA256 hashes: A-<sha256(sorted(finding_ids)|title)[:10]>_

---

## P0 — Do Now or Risk Desk-Rejection

These four actions address structural errors (logical contradiction, wrong citation, counting inconsistency, unexplained anomaly) that could cause immediate rejection without review.

### A-5f02c65612 — Fix Contributions vs. §4.2/§5.4 spillover contradiction
- **Findings:** F-82f9dcceaf
- **Effort:** S (30-90 min)
- **Target:** §1 Contributions item 3 + §4.2 + §5.4
- **Action:** Contributions item 3 states Local and Cluster have "no cross-client spillover." §4.2 and §5.4 describe Cluster as causing intra-cluster spillover to non-victim devices in the same cluster. This is a direct logical contradiction. Choose one: (a) remove the "no spillover" absolute claim from Contributions, replace with "spillover is policy-dependent: Local has none, Cluster has intra-cluster spillover, Global has fleet-wide spillover," or (b) verify Cluster has zero spillover and correct §4.2/§5.4. This is a desk-rejection-level error.

### A-a098e39ee7 — Verify and fix Reference [12] citation
- **Findings:** F-a620caf003
- **Effort:** S (30-90 min)
- **Target:** §3 references + references.bib
- **Action:** AUDIT-10 flags that Reference [12] (L'heureux et al. 2017) does not support the cited claim about threshold sensitivity. Open the paper. If the claim is unsupported: (a) find the correct citation, (b) derive the claim from first principles, or (c) remove it. A mismatched citation is a credibility risk that attentive reviewers will catch.

### A-bc70838a10 — Fix "4 source-objective pairs" inconsistency
- **Findings:** F-f80d97cb0e, F-16a073b134
- **Effort:** XS (<30 min)
- **Target:** §4 / §1 Contributions
- **Action:** The paper refers to "4 source-objective pairs" but describes only 3: HIGH_SCORE_BENIGN×THRESHOLD_RAISE, LOW_SCORE_BENIGN×THRESHOLD_LOWER, RANDOM_BENIGN×(control). Either correct the count to 3, or explicitly name and describe the 4th pair. This inconsistency confused all three audits that noticed it (AUDIT-02, AUDIT-09, AUDIT-10).

### A-db7bcc5fcf — Explain or correct Table 1 Cluster Macro-F1 ± 0.000
- **Findings:** F-0993b70fbb
- **Effort:** M (2-4 hours, includes investigating the results code)
- **Target:** Table 1 + results generation code
- **Action:** Table 1 shows Cluster Macro-F1 = 0.299 ± 0.000. Zero std across 10 seeds implies either a bug (all seeds use same initialization), a copy-paste error (std dropped), or a deterministic construction. Investigate: run the experiment, check the results pipeline, and either fix the value or add a footnote explaining zero variance.

---

## P1 — Required for Submission

### A-f3e11e1509 — Add reproducibility table
- **Findings:** F-4e13c25efd, F-447e660ce4, F-3ef85e6456, F-4ad5dce40c
- **Effort:** M (2-4 hours)
- **Target:** §2 Setup / new Table
- **Action:** Add Table (or structured paragraph): AE layer sizes + activations, FedAvg rounds + local epochs + LR + optimizer, N-BaIoT train/calibration/test sizes per device, feature extraction method (which traffic statistics). This is the single most universally cited gap (10/10 audits note some form of this).

### A-664b8440ed — Add artifact/code availability statement
- **Findings:** F-56f3c530ef
- **Effort:** XS (<30 min)
- **Target:** §1 or §7 Conclusion
- **Action:** Add standard availability statement. If code will be released: URL + license. If not yet: "Code will be made available upon acceptance." All 10 audits flag the absence of this.

### A-e102f26659 — Reframe score-level proxy caveat; fix attack vs. characterization language
- **Findings:** F-6a6b0d6949, F-8993694ae8
- **Effort:** S (30-90 min)
- **Target:** §1 Abstract + §2 Threat Model + §6
- **Action:** (a) Add explicit caveat in §1/abstract: attack is at score-substitution level; traffic-level realization is future work. (b) Standardize: pick "attack" or "vulnerability characterization" and use consistently. Recommended: "attack" in abstract/contributions, "characterization" only in §6 where it explicitly characterizes the vulnerability space, with a bridging sentence in §1.

### A-01a7255dbd — Reframe lowering attack: foreground alarm burden
- **Findings:** F-1f6dfe00f2, F-4521a0a59c, F-653ddd1df9
- **Effort:** S (30-90 min)
- **Target:** Abstract + §5.3
- **Action:** Replace ΔTPR-first framing with ΔFPR-first framing for the lowering attack. The harm is increased false positive rate (alarm burden), not detection improvement. Add sentence: "the adversary's goal is to increase the false alarm rate, creating alert fatigue that may lead operators to disable the anomaly detector." Soften "succeeds" → "achieves elevated alarm rate."

### A-1975d011a9 — Add Random-Benign to Table 2 and Figure 3
- **Findings:** F-d5257ddef0, F-d17dbb4517
- **Effort:** M (2-4 hours, includes re-running analysis and regenerating outputs)
- **Target:** Table 2 + Figure 3
- **Action:** Add RANDOM_BENIGN rows to Table 2 (ΔTPR, ΔFPR, Δτ values for each policy). Add Random-Benign line to Figure 3. This is flagged by all 10 audits and is the most critical missing piece of negative control presentation.

### A-984973914d — Fix Figure 2: add Cluster, add seeds or justify seed 0
- **Findings:** F-bf066608e1
- **Effort:** M (2-4 hours)
- **Target:** Figure 2
- **Action:** Add Cluster condition to Figure 2. Either show mean±std across all 10 seeds, or add a caption justifying why seed 0 is representative (e.g., "seed 0 produces median-outcome ΔTPR; deviation across seeds shown in Appendix").

### A-e31849338f — Add spillover quantification table
- **Findings:** F-5e5517e25d
- **Effort:** M (2-4 hours)
- **Target:** §5.4 + new table
- **Action:** Add table: for Global attack — victim ΔTPR/ΔFPR vs. average non-victim ΔTPR/ΔFPR. For Cluster attack — victim vs. same-cluster non-victims vs. different-cluster clients. This converts prose assertions into data.

### A-5ccfae0eed — Expand related work: Kloft & Laskov contrast, comparison table, soften "no prior work"
- **Findings:** F-9c91e712ec, F-1249c7034d, F-7a835d76b5
- **Effort:** M (2-4 hours)
- **Target:** §3 Related Work
- **Action:** (a) Add explicit Kloft & Laskov contrast paragraph. (b) Add comparison table (4-6 works). (c) Change "no prior work" → "to the best of our knowledge, no prior work."

### A-f8c713ec0c — Remove "every defense" and deployment language
- **Findings:** F-53f9f172ea, F-cd3c497156
- **Effort:** XS (<30 min)
- **Target:** §1 Abstract + Introduction
- **Action:** Replace "structurally outside scope of every defense" → "we identify no defense that directly monitors the calibration channel." Remove "operationally meaningful in IoT deployment contexts." Both are explicitly forbidden by the frozen scientific boundary.

### A-df1fb64bdd — Add BCa bootstrap caveat
- **Findings:** F-64588f32e0
- **Effort:** S (30-90 min)
- **Target:** §6 Statistics
- **Action:** Add footnote: "With N=10 seeds, percentile bootstrap 95% CIs have known coverage deficiencies. We use BCa (bias-corrected accelerated) bootstrap [cite] which achieves better finite-sample coverage." Alternatively, recompute with BCa.

### A-9c654c5a5e — Justify gate constants and three-gate framework
- **Findings:** F-b02c973ba2, F-95a95d973c
- **Effort:** S (30-90 min)
- **Target:** §6 Statistics
- **Action:** Add justification paragraph: cite any prior work using similar gate approach, or explain why 0.1×IQR and 0.01×IQR are appropriate. Disclose if constants were set before or after seeing results.

---

## P2 — Strongly Recommended

| Action ID | Effort | Target | Summary |
|-----------|--------|--------|---------|
| A-741211d451 | XS | Table 1 | Define BAP10/P10/Worst BA in footnotes |
| A-2849af9957 | XS | Table 1+2 captions | State bold direction (higher/lower = better/worse) |
| A-52a92f30db | XS | Abstract + §6 | Define Gate-1 at first use in abstract |
| A-39a0f86ebd | XS | §2 Threat Model | Add precise gray-box definition anchored to FL |
| A-f47168b200 | XS | §4 Method | Add formal contamination equation |
| A-19e2ac96a6 | XS | All sections | Standardize attack vs. vulnerability language |
| A-40607a57a6 | XS | Figure 1 | Add color legend; fix "training defended" label |
| A-855a2d7014 | S | §5.2 | Remove or derive "30-80 Mirai flows" claim |
| A-c8058bdd1f | S | §5 Discussion | Add defense requirements sketch |
| A-e6f405cf6f | S | §4 Method | Specify Cluster: features, K=3 justification, seed variance |
| A-e91b1d847d | XS | §2 notation | Move CV(FPR) definition earlier |
| A-2407be7432 | XS | §4 / §6 | Justify victim-majority (≥5/9) condition |
| A-01d8c9ea7a | XS | §1 Introduction | Add paper roadmap |
| A-213529531a | XS | Figure 3 | Fix Global line scale / add inset |
| A-8db2e8afa8 | XS | §5 / Table 2 | Disambiguate victim vs. fleet ΔTPR in Global |
| A-d9bc51f540 | XS | §1 Introduction | Add concrete motivating harm scenario |
| A-023cc3fd20 | XS | §3 + .bib | Add 2023-2024 FL security citations; K-means++ citation |
| A-6876713dc4 | XS | §6 | Disambiguate N notation (federation size vs. buffer size) |

---

## P3 — Nice to Have

| Action ID | Effort | Target | Summary |
|-----------|--------|--------|---------|
| A-a1dbe8cc63 | XS | paper/figures/ | Regenerate figures at 300 DPI / vector format |
| A-c5f373c929 | S | Table 2 | Improve Table 2 layout density |
| A-418234b961 | XS | §5 | Discuss Local vs. Global P10 Macro-F1 tradeoff |

---

## Effort Summary

| Priority | XS | S | M | L | XL | Total |
|----------|----|----|---|---|----|-------|
| P0 | 1 | 2 | 1 | 0 | 0 | 4 |
| P1 | 2 | 4 | 5 | 0 | 0 | 11 |
| P2 | 14 | 4 | 0 | 0 | 0 | 18 |
| P3 | 2 | 1 | 0 | 0 | 0 | 3 |
| **Total** | **19** | **11** | **6** | | | **36** |

**Estimated total effort:** ~2-3 focused work days for P0+P1+P2. P3 adds ~2-4 hours.
