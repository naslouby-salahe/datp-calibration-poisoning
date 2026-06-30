# Paper Audit and Review Report

## 1. Executive Verdict

**Overall grade:** **8.0 / 10**

**Recommendation:** **Borderline / weak accept for a focused IoT-FL or applied security conference; weak reject for a top-tier security/ML venue in its current form.**

**Verdict:** The paper is scientifically disciplined, tightly scoped, and much stronger than a typical “FL security” paper because it isolates one causal channel: calibration-only threshold poisoning. The core experiment is credible: training data, model weights, aggregation, test scores, and test labels are kept unchanged while only the benign calibration buffer is contaminated; the paper also explicitly limits itself to score-level characterization, N-BaIoT, FedAvg, autoencoders, and single-client compromise. That is the paper’s biggest strength. Its biggest remaining weakness is that the empirical evidence is still narrow: one dataset, nine clients, score-level proxy only, no artifact details, limited related-work positioning, and not enough visible control/ablation evidence in the main paper. The paper is close to submission-ready, but not yet “bulletproof.”

**Main reason to accept:** It identifies a real, under-discussed attack surface: post-training threshold calibration, not training/model/aggregation poisoning. The threat model and claim discipline are unusually clean. The abstract and introduction correctly state that the attack shifts thresholds without changing model weights, training data, or test labels, and the paper explicitly bounds claims to the nine-device N-BaIoT/FedAvg/autoencoder setting. 

**Main reason to reject:** A skeptical reviewer can say: “This is a score-level manipulation on one small benchmark, with limited related work and incomplete reproducibility details; show me that this is not just a toy quantile artifact.” That objection is not fully neutralized yet.

**Fastest path to improve:** Add one compact main-text table for **controls + spillover + reproducibility**: Random-Benign control results, non-victim spillover under Global/Cluster, exact split/model/training details, and artifact/code availability.

---

## 2. Scorecard

| Category                 | Score |
| ------------------------ | ----: |
| Novelty                  |   8.0 |
| Technical correctness    |   8.4 |
| Methodological rigor     |   8.0 |
| Experimental support     |   7.4 |
| Claim discipline         |   8.8 |
| Related work positioning |   6.8 |
| Reproducibility          |   6.7 |
| Visual presentation      |   7.6 |
| Writing clarity          |   8.5 |
| Reviewer-proofness       |   7.3 |

**Final integrated grade:** **8.0 / 10**

---

## 3. Top Strengths

1. **Excellent causal isolation.** The paper clearly separates calibration-channel poisoning from training poisoning, model poisoning, aggregation poisoning, backdoors, evasion, and privacy claims.

2. **Strong threat-model discipline.** The adversary only controls one client’s calibration buffer, has score-level access, and does not modify model weights, gradients, other clients’ data, test data, or labels. 

3. **Good policy differentiation.** Global, Local, and Cluster are not treated as interchangeable; the paper explains dilution, isolation, and intra-cluster spillover.

4. **Clear primary result.** Raising attack results are easy to understand: 100% Gate-1 pass at non-zero fractions, threshold increases, and victim TPR decreases.

5. **Honest limitation section.** The score-level proxy and duplicate-score detectability limitation are disclosed instead of hidden. 

---

## 4. Top Weaknesses

| Rank | Weakness                                                          | Severity       | Location                          | Fix                                                                                                                              |
| ---: | ----------------------------------------------------------------- | -------------- | --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
|    1 | Single-dataset, nine-client evidence may look too narrow.         | Major          | Scope, §4.1, §6                   | Add one paragraph explicitly defending why N-BaIoT is the correct first mechanism benchmark; do not overclaim.                   |
|    2 | Score-level proxy may be attacked as unrealistic.                 | Major          | §3, §6                            | Add no-replacement or jittered-score diagnostic, or state why current proxy is an upper-bound mechanism study.                   |
|    3 | Random-Benign control is discussed but not visibly tabulated.     | Major          | §3, §5.2, Fig. 3 caption, Table 2 | Add a compact control row/table with Δτ CI, G1, and ΔTPR for Random-Benign.                                                      |
|    4 | Global/Cluster spillover claim needs direct non-victim evidence.  | Major          | §5.2, §5.4                        | Add mean non-victim ΔTPR/ΔFPR, spillover count, and worst non-victim harm.                                                       |
|    5 | Lowering attack harm framing is confusing because ΔTPR increases. | Major          | Abstract, §5.3, Conclusion        | Lead with ΔFPR or alert burden; call ΔTPR “operating-point displacement,” not harm.                                              |
|    6 | Reproducibility details are incomplete.                           | Major          | §4                                | Add AE architecture, preprocessing, train/cal/test split, normalization, rounds, local epochs, hardware/software, code/manifest. |
|    7 | Statistical inference uses only 10 seed-level aggregates.         | Moderate-major | §4.4                              | Add seed-level plots or exact sign/permutation tests; avoid overconfident CI wording.                                            |
|    8 | Related work is too compact for novelty defense.                  | Major          | §2                                | Add closest-work comparison table: training poisoning vs threshold/calibration poisoning vs anomaly-threshold contamination.     |
|    9 | Clean-baseline fairness/performance tradeoff under-discussed.     | Moderate       | Table 1, §5.1                     | Discuss why Local improves CV(FPR) but has worse P10 Macro-F1 than Global.                                                       |
|   10 | Visuals are readable but not fully self-contained.                | Moderate       | Fig. 2, Fig. 3, Table 2           | Increase figure font/label clarity and add control data.                                                                         |

---

## 5. Fatal or Near-Fatal Risks

**Near-fatal risk 1 — “This is a toy score-level attack.”**
The paper admits the attack replaces reconstruction scores directly rather than generating traffic. That is honest, but a reviewer can still reject if they demand traffic-level realizability. The safe defense is: “This paper characterizes the calibration mechanism, not deployability.” Add a small diagnostic with no-replacement sampling or score jitter to reduce the “duplicate values make this artificial” objection.

**Near-fatal risk 2 — “One dataset, nine clients.”**
The paper scopes itself correctly, but high-level reviewers may still demand external validation. Since the paper is conference-length, you can survive if you frame N-BaIoT as a mechanism benchmark, not as universal evidence.

**Near-fatal risk 3 — “Novelty is under-positioned.”**
The statement “to our knowledge, no prior work…” is plausible but fragile. You need a stronger related-work table showing why training poisoning, model poisoning, robust aggregation, centralized anomaly poisoning, and threshold calibration are different surfaces.

**Near-fatal risk 4 — “Controls are asserted, not shown.”**
Random-Benign is essential to credibility. It is mentioned repeatedly, but it should be visible in a table or appendix.

---

## 6. Section-by-Section Review

### Title — **8.5/10**

**Works:** Clear, specific, and scoped. “Threshold-Calibration Stage” and “Policy-Differentiated” accurately signal the contribution.

**Weakness:** Slightly long.
**Fix:** Keep unless page header overflow or venue style complains.
**Submission-ready:** Yes.

### Abstract — **8.2/10**

**Works:** Strong summary of attack surface, scope, policies, dataset, and main numbers.

**Issue:** The lowering attack sentence is risky: “victim detection-rate increase” sounds beneficial, not harmful.
**Fix:** Rewrite around alarm burden: “lowering increases false-positive burden and FPR disparity; ΔTPR is reported only as operating-point displacement.”
**Priority:** Major.
**Submission-ready:** Almost.

### Introduction — **8.6/10**

**Works:** The undefended-phase argument is convincing. The three-axis distinction from ordinary data poisoning is strong.

**Issue:** “Structurally outside the scope of every defense…” is almost too broad. Some system-level attestation or calibration-validation defenses could exist.
**Fix:** Use “training-phase and aggregation-phase defenses considered in this literature do not monitor…”
**Priority:** Moderate.
**Submission-ready:** Yes after wording polish.

### Contributions — **8.4/10**

**Works:** Concrete and scoped.

**Issue:** Contribution 1 says “undefended attack surface.” That is strong. Better: “under-analyzed and not addressed by training/aggregation defenses.”
**Fix:** Downgrade “undefended” to “unmonitored by standard training-phase defenses.”
**Priority:** Moderate.

### Related Work — **6.8/10**

**Works:** Covers FL anomaly detection, robust aggregation, threshold calibration, and threshold policies.

**Missing:** Closest-work differentiation is too compressed. A reviewer will ask for calibration poisoning, conformal calibration attacks, anomaly threshold manipulation, and centralized anomaly-detector poisoning.
**Fix:** Add a table:

| Prior work type               | What is attacked                       | Why different from this paper             |
| ----------------------------- | -------------------------------------- | ----------------------------------------- |
| FL model poisoning            | gradients/weights                      | training phase                            |
| Byzantine robust aggregation  | client updates                         | before calibration                        |
| Centralized anomaly poisoning | training/calibration data in one owner | not FL-local autonomous calibration       |
| Threshold calibration methods | threshold selection                    | not adversarial calibration contamination |

**Priority:** Major.

### Threat Model — **8.8/10**

**Works:** Very strong. It clearly states the attacker’s access and non-access. The score-level boundary is honest.

**Issue:** “Semantically benign” is asserted at score level, but at score level you do not actually have semantic traffic objects, only scores.
**Fix:** Say “scores drawn from benign calibration records” rather than “semantically benign scores.”
**Priority:** Moderate.
**Submission-ready:** Yes after minor wording.

### Methodology / Experimental Protocol — **7.7/10**

**Works:** Policies, fractions, seeds, and attack mechanics are clear.

**Missing:** Model architecture, preprocessing, split construction, normalization, feature set, train/cal/test sizes, FedAvg rounds/local epochs, batch size, optimizer, convergence/checkpoint rule.
**Fix:** Add a “Reproducibility details” paragraph or appendix reference.
**Priority:** Major.

### Dataset — **7.6/10**

**Works:** N-BaIoT physical-device federation is appropriate.

**Weakness:** One dataset and nine clients.
**Fix:** Say explicitly: “N-BaIoT is chosen because physical devices map directly to clients; external datasets are left for future validation.”
**Priority:** Major but acceptable if scoped.

### Metrics — **7.9/10**

**Works:** Δτ, ΔTPR, CV(FPR), AUROC sanity check, and Gate 1/2/3 are aligned with the causal story.

**Issue:** Lowering attack should be evaluated primarily with ΔFPR / alert burden, not ΔTPR. CV(FPR) alone is not enough because it can decrease even when all FPRs worsen proportionally.
**Fix:** Add mean FPR, worst-client FPR, and absolute alert-burden proxy.
**Priority:** Major.

### Statistical Analysis — **7.4/10**

**Works:** Paired seed design is good. The paper correctly avoids treating all 4,320 cells as independent evidence.

**Weakness:** 10 seed-level aggregates are thin for percentile bootstrap CIs.
**Fix:** Add exact sign test, paired permutation test, or seed-level dot plot. Phrase CIs as descriptive uncertainty, not definitive population inference.
**Priority:** Moderate-major.

### Results — **8.0/10**

**Works:** Main raising result is persuasive. Policy ordering is intuitive and supported.

**Weakness:** Spillover claims need explicit table support. Random-Benign needs visible reporting.
**Fix:** Add a compact “Attack summary with controls and spillover” table.
**Priority:** Major.

### Ablations / Controls — **6.9/10**

**Works:** Random-Benign exists conceptually and is essential.

**Weakness:** The control is not shown enough. No no-replacement/jitter/source-size sensitivity.
**Fix:** Add at least one control table and one implementation-realism diagnostic.
**Priority:** Major.

### Discussion and Limitations — **8.7/10**

**Works:** Honest and well-written. Score-level proxy, duplicate detectability, single dataset, and no defense are disclosed.

**Issue:** The conclusion says effects are “operationally meaningful in IoT deployment contexts,” but deployment is explicitly out of scope.
**Fix:** Use “potentially operationally meaningful” or “would be operationally meaningful if such score shifts were realized in traffic.”
**Priority:** Major wording fix.

### Conclusion — **8.0/10**

**Works:** Strong recap.

**Issue:** Same lowering/operational wording risk.
**Fix:** Make the final paragraph more scoped and less deployment-flavored.
**Priority:** Moderate-major.

### References — **6.8/10**

**Works:** Core FL, robust aggregation, N-BaIoT, and poisoning references are present.

**Missing:** More direct threshold/calibration/security references.
**Fix:** Expand closest-work coverage, especially anomaly detector poisoning and calibration-stage/conformal calibration attacks.
**Priority:** Major.

### Appendix / Artifacts — **5.8/10**

**Issue:** No visible appendix. For a 13-page paper this may be okay, but artifact details need a home.
**Fix:** Add artifact appendix or supplementary material.
**Priority:** Major.

---

## 7. Reviewer Questions the Paper Must Already Answer

### Threat model questions

* Can the attacker really modify calibration scores, or only traffic?
* Does the attacker modify training data, gradients, aggregation, model weights, test scores, or labels?
* Are replacement scores from the victim only?
* Are attack-labeled samples ever used in calibration?
* Why is score-level access realistic for a compromised client?

### Novelty questions

* How is this different from ordinary data poisoning?
* How is this different from centralized anomaly-detector poisoning?
* How is this different from threshold personalization or clustered FL?
* Has calibration poisoning been studied in conformal prediction or threshold calibration?

### Methodology questions

* What exact autoencoder architecture is used?
* What are the train/calibration/test splits?
* How are features normalized?
* What are FedAvg rounds, local epochs, optimizer, batch size, and checkpoint rule?
* Are clean and poisoned runs paired by seed?

### Dataset questions

* Why only N-BaIoT?
* Does nine clients suffice?
* Are Mirai/BASHLITE results representative?
* Are clients physical devices or pseudo-clients?

### Metric questions

* Why ΔTPR for lowering when increased TPR is not harm?
* Why CV(FPR) rather than absolute FPR or alert count?
* Does CV(FPR) behave badly when mean FPR is near zero?
* What is the practical impact in false alerts/day?

### Statistical validity questions

* Are 4,320 cells treated as independent?
* Why is bootstrap over 10 seeds reliable?
* Are results robust under exact sign tests?
* Are CIs adjusted for multiple policy/fraction comparisons?

### Baseline/control questions

* Where are Random-Benign results?
* What happens with no-replacement sampling?
* What happens with smaller/larger calibration sets?
* What happens at q=0.90 or q=0.99?

### Reproducibility questions

* Is code available?
* Are seeds and manifests available?
* Can another researcher reproduce the exact 4,320 cells?
* Are raw score artifacts available?

### Scope and limitation questions

* Does this prove deployable attack feasibility? No.
* Does this prove FL is insecure? No.
* Does this generalize to other datasets, detectors, or FL algorithms? Not yet.
* Does this evaluate defenses? No.

### Visual/formatting questions

* Are figures readable in print?
* Are abbreviations self-contained?
* Is the control missing from Figure 3?
* Why are tables separated from first mention?

---

## 8. Claim Discipline Audit

| Claim                                                               | Support level                                                    | Location                | Risk                              | Safer wording                                                                                               |
| ------------------------------------------------------------------- | ---------------------------------------------------------------- | ----------------------- | --------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Calibration stage is outside training/aggregation defenses.         | Mostly supported                                                 | Abstract, §1, §3        | “Every defense” too broad.        | “Outside the monitoring scope of standard training/aggregation defenses.”                                   |
| Attack shifts thresholds without changing weights/data/test labels. | Supported                                                        | Abstract, §3, §4.5      | Strong and central.               | Keep.                                                                                                       |
| Raising attack degrades victim TPR by 2.4–7.9 pp.                   | Supported                                                        | Abstract, §5.2, Table 2 | Needs control table visibility.   | Keep with “in N-BaIoT score-level setting.”                                                                 |
| Lowering attack succeeds for Local/Cluster.                         | Partially supported                                              | Abstract, §5.3          | Harm framing confusing.           | “Lowering shifts operating point and increases FPR disparity for Local/Cluster.”                            |
| Global propagates harm to all members.                              | Partially supported                                              | §5.2, §5.4              | Needs non-victim table.           | “Global propagates the threshold change to all members; measured non-victim impact is reported separately.” |
| No prior work characterizes this stage.                             | Plausible but under-supported                                    | §2                      | Related work too thin.            | “We are not aware of prior FL-IoT work that isolates this exact post-training calibration channel.”         |
| Effects are operationally meaningful in IoT contexts.               | Overstated                                                       | Conclusion              | Deployment out of scope.          | “Potentially operationally meaningful if score-level shifts are traffic-realizable.”                        |
| AUROC invariance confirms isolation.                                | Supported as sanity check                                        | §4.4, §4.5              | Must not be contribution.         | Keep as protocol check.                                                                                     |
| Local confines harm to compromised client.                          | Supported by policy definition, needs empirical spillover table. | §4.2, §5.4              | “Harm” should be metric-specific. | “Local confines threshold changes to the compromised client.”                                               |
| Cluster causes intra-cluster spillover.                             | Partially supported                                              | §4.2, §5.4              | Needs co-cluster evidence.        | Add co-cluster spillover count/table.                                                                       |

---

## 9. Methodology and Experiment Audit

| Issue                               | Location       | Why it matters                 | Reviewer risk | Fix                                                                         | Priority       |
| ----------------------------------- | -------------- | ------------------------------ | ------------- | --------------------------------------------------------------------------- | -------------- |
| Reproducibility details missing     | §4             | Cannot replicate               | High          | Add architecture, preprocessing, split, rounds, epochs, optimizer, hardware | Major          |
| Random-Benign not tabulated         | §5, Fig. 3     | Control is central             | High          | Add control table/appendix                                                  | Major          |
| Spillover not quantified directly   | §5.2, §5.4     | Policy claim depends on it     | High          | Add victim vs non-victim harm table                                         | Major          |
| Lowering harm metric ambiguous      | Abstract, §5.3 | Positive TPR sounds good       | High          | Use ΔFPR/alert burden as primary                                            | Major          |
| Bootstrap over n=10                 | §4.4           | CI may look overconfident      | Medium-high   | Add exact sign/permutation tests                                            | Moderate-major |
| Duplicate scores at f=0.4           | §6             | Realism attack                 | Medium-high   | Add no-replacement/jitter diagnostic                                        | Major          |
| Single dataset                      | §4, §6         | Generality limited             | Medium-high   | Stronger scope defense or supplementary dataset                             | Major          |
| q=0.95 fixed                        | §3, §4         | Threshold sensitivity          | Medium        | Add q sensitivity or explicitly defer                                       | Moderate       |
| Calibration size sensitivity absent | §4.1           | Low-data client realism        | Medium        | Add subsampling sensitivity if possible                                     | Moderate       |
| No defense evaluated                | §6             | Reviewer may expect mitigation | Medium        | State out of scope; optionally add defense requirements table               | Moderate       |

---

## 10. Figures and Tables Audit

### Figure 1 — Attack surface diagram — **8.0/10**

**Communicates:** Training phase is separate from calibration stage; attack happens after FedAvg.
**Works:** Clear conceptual diagram.
**Confusing:** “Training phase defended” may imply those defenses are actually implemented or universally sufficient.
**Fix:** Rename to “training/aggregation defense surface” and “calibration surface not monitored by those defenses.”
**Keep:** Yes.

### Figure 2 — Clean FPR Global vs Local — **7.2/10**

**Communicates:** Global threshold creates heterogeneous FPR; Local reduces dispersion.
**Works:** Useful visual.
**Confusing:** Device labels are cramped; only seed 0 is plotted while caption references average CV.
**Fix:** Increase font size, shorten labels consistently, and add “seed 0 illustrative; Table 1 reports 10-seed aggregate.”
**Keep:** Yes.

### Figure 3 — Threshold shift vs fraction — **7.8/10**

**Communicates:** Raising/lowering shifts scale with fraction; Global is diluted.
**Works:** Good central figure.
**Confusing:** Random-Benign is not plotted; panel b lacks its own legend; downstream harm is not shown.
**Fix:** Add dashed Random-Benign line or supplementary control panel.
**Keep:** Yes, but improve.

### Table 1 — Clean baseline policy profile — **7.7/10**

**Communicates:** Local best CV(FPR), Global worst, Cluster middle.
**Works:** Compact and useful.
**Confusing:** Local has worse P10 Macro-F1 than Global, but this tradeoff is not discussed enough.
**Fix:** Add one sentence: “FPR equity improves at the cost of lower P10 Macro-F1 in this clean baseline.”
**Keep:** Yes.

### Table 2 — Poisoning results — **8.0/10**

**Communicates:** Main quantitative result.
**Works:** Strong and compact.
**Confusing:** Random-Benign only appears in note; lowering rows use ΔTPR as if harm.
**Fix:** Add Random-Benign rows or a companion control table; add ΔFPR/ΔCV(FPR) column for lowering.
**Keep:** Yes.

---

## 11. Visual and Formatting Review

The paper looks professional and close to LNCS-style readiness. The figures are clean, the tables are not visually broken, and the page count is controlled. Main presentation problems are not catastrophic, but they matter for reviewer confidence:

* Figure 2 device labels are too small and angled.
* Figure 3 should include the negative control visually or in a nearby table.
* Table 2 is dense; adding Random-Benign rows may require moving detailed rows to appendix.
* Page 9 has substantial whitespace caused by float placement, but it is acceptable.
* Abbreviations like CV(FPR), ΔTPR, G1, and BA should be defined in every table caption where possible.
* The paper would benefit from a one-line “artifact availability” statement before references.

---

## 12. Related Work and Novelty Review

**Novelty score:** **8.0 / 10 conceptually, 6.8 / 10 in written positioning.**

The novelty is real enough if framed carefully: this is not training poisoning, not model poisoning, not backdoor injection, not evasion, and not privacy leakage. It is threshold-calibration channel poisoning after training. That is a defensible contribution.

The related-work section currently does not work hard enough to protect that novelty. Add a closest-work comparison table.

**Safe novelty statement:**

> “We isolate a post-training calibration-channel attack in federated threshold-based IoT anomaly detection. Unlike FL model poisoning or robust aggregation work, the intervention occurs after model convergence and modifies only the benign calibration buffer used to derive detection thresholds. Our claims are limited to score-level contamination on N-BaIoT under FedAvg autoencoders.”

---

## 13. Reproducibility Checklist

**Reproducibility grade:** **6.7 / 10**

Minimum items to add before submission:

* Exact N-BaIoT files/devices used.
* Feature preprocessing and normalization.
* Train/calibration/test split rule.
* Calibration sizes per client.
* Test benign/attack counts per client.
* Autoencoder architecture.
* Loss, optimizer, learning rate, batch size.
* FedAvg rounds, local epochs, participation rule.
* Checkpoint selection rule.
* Threshold quantile and implementation details.
* Attack seeds and pairing.
* Bootstrap seed and resampling implementation.
* Code repository or artifact statement.
* Output manifest/hash policy, at least in supplementary material.

---

## 14. Action Plan to Reach 10/10

### Must fix before submission

* Add Random-Benign control results visibly.
* Add non-victim spillover table for Global and Cluster.
* Rewrite lowering-attack harm framing around FPR/alert burden, not positive ΔTPR.
* Add missing reproducibility details.
* Strengthen related work with closest-work comparison.
* Tone down “operationally meaningful in deployment” language.
* Add exact sign/permutation test or seed-level plot to support bootstrap results.

### Should fix if page budget allows

* Add no-replacement or jittered-score diagnostic.
* Add q sensitivity at q ∈ {0.90, 0.95, 0.99}.
* Add calibration-size sensitivity.
* Add mean FPR / worst-client FPR / alert-burden translation.
* Add cluster spillover decomposition or co-cluster impact table.

### Nice to fix

* Improve device-label readability in Figure 2.
* Add a graphical Random-Benign line to Figure 3.
* Add one artifact-availability sentence.
* Clarify whether Table 2 values are seed-level aggregates or victim-seed aggregates.

### Do not touch / already strong

* Do not broaden the claim to “secure FL.”
* Do not add privacy claims.
* Do not claim raw-traffic realizability.
* Do not move into training/model poisoning.
* Keep the clean calibration-stage isolation. That is the paper’s identity.

---

## 15. Final Reviewer Simulation

### Reviewer 1 — Supportive expert reviewer

**Likely score:** 8 / 10
**Judgment:** Weak accept.
**Main view:** The paper identifies a real blind spot in FL-IoT anomaly detection and evaluates it cleanly.
**Objections:** Wants more related work and Random-Benign controls shown.
**Current answer sufficient?** Mostly, but not fully.
**Neutralizing fix:** Add control table and closest-work comparison.

### Reviewer 2 — Skeptical methods reviewer

**Likely score:** 6.5 / 10
**Judgment:** Borderline / weak reject.
**Main view:** The causal isolation is good, but one dataset, score-level proxy, and 10 seeds are not enough for broad conclusions.
**Objections:** Bootstrap over 10 seeds; no external dataset; no raw-traffic feasibility.
**Current answer sufficient?** Partially.
**Neutralizing fix:** Add exact tests, stronger scope language, no-replacement/jitter diagnostic, and avoid deployment phrasing.

### Reviewer 3 — Security/adversarial ML reviewer

**Likely score:** 6.8 / 10
**Judgment:** Borderline.
**Main view:** Interesting attack surface, but realism is weak.
**Objections:** Score-level replacement, duplicate scores, no traffic generation, no adaptive attacker/defense.
**Current answer sufficient?** The limitation is honest, but the reviewer may still reject.
**Neutralizing fix:** Explicitly frame as vulnerability-surface characterization and add detectability/realism diagnostics.

### Reviewer 4 — Presentation/clarity reviewer

**Likely score:** 7.8 / 10
**Judgment:** Weak accept after revisions.
**Main view:** Well-written and professional, but some figures/tables are not self-contained.
**Objections:** Missing controls in figures, dense Table 2, confusing lowering language.
**Current answer sufficient?** Almost.
**Neutralizing fix:** Improve captions, add control rows, and clarify lowering attack harm.

---

**Final readiness verdict:** **Almost ready, but not yet bulletproof.**
For a focused conference, this is close. For a high-level venue, the paper needs stronger visible controls, related-work positioning, spillover quantification, reproducibility details, and more careful lowering-attack language.
