# Paper Audit and Review Report

## 1. Executive Verdict

**Overall Grade: 7.8/10**

**Recommendation: Weak Accept (with mandatory revisions)**

**One-Paragraph Verdict:** This paper identifies a legitimate and previously underexplored attack surface in federated IoT anomaly detection—the post-training threshold-calibration stage. The experimental methodology is rigorous with proper controls, paired seeds, and bootstrap confidence intervals. The policy-differentiated vulnerability profile is a genuine contribution. However, the paper suffers from a fundamental scope-discipline issue: the score-level proxy attack is presented as a vulnerability characterization but lacks end-to-end traffic-level realizability, which will be a major point of contention. The claim that this "bypasses all training-phase defenses" is technically correct but overstated, as it simply attacks a different stage. The paper's strongest contribution is the empirical demonstration that policy choice affects both magnitude and blast radius of calibration-stage poisoning, but this finding is narrowly scoped to N-BaIoT with autoencoders.

**Main Reason to Accept:** Novel identification of an undefended attack surface with rigorous experimental characterization across three threshold policies, showing non-trivial downstream detection harm (4.9-7.9 pp TPR degradation) with 95% CIs excluding zero.

**Main Reason to Reject:** The attack is demonstrated at the score level only, not the traffic level. A skeptical reviewer may argue this is just "data poisoning applied to calibration data" with no evidence that an adversary can actually generate network traffic with tail reconstruction scores. The paper acknowledges this in §6 but does not resolve it.

**Fastest Path to Improve:** (1) Reframe all claims about "attack" to "vulnerability characterization" with explicit hedging; (2) Add an ablation showing how the score-level contamination translates to traffic-level feasibility constraints; (3) Strengthen the related work section to more precisely distinguish this from existing calibration poisoning; (4) Add a concrete defense sketch in §6 to demonstrate constructive value.

---

## 2. Scorecard

| Category | Score | Justification |
|----------|-------|---------------|
| Novelty | 7.5/10 | Novel attack surface identification, but related work on calibration poisoning exists; novelty is in FL context and policy differentiation |
| Technical Correctness | 8.5/10 | Protocol is sound; statistics are appropriate; sanity checks are thorough |
| Methodological Rigor | 8.0/10 | Strong experimental design with paired seeds, controls, and bootstrap CIs; but no traffic-level validation |
| Experimental Support | 7.5/10 | Comprehensive within the score-level framework; but the core intervention is a proxy |
| Claim Discipline | 7.0/10 | Generally well-scoped, but occasional overstatement of "attack" vs. "vulnerability characterization" |
| Related Work Positioning | 7.0/10 | Missing key calibration-poisoning work; doesn't sufficiently distinguish from standard data poisoning |
| Reproducibility | 8.5/10 | Detailed experimental protocol; could improve with code/artifact statement |
| Visual Presentation | 7.5/10 | Clean figures but some readability issues (small fonts, missing legend details) |
| Writing Clarity | 8.0/10 | Well-structured but occasionally dense; some terminology needs better definition |
| Reviewer-Proofness | 7.0/10 | Vulnerable to "score-level proxy" objection and scope-overclaim critiques |

---

## 3. Top Strengths

1. **Novel attack surface identification.** The paper correctly identifies that the threshold-calibration stage is structurally outside the scope of training-phase defenses—this is a genuine gap in the FL security literature.

2. **Rigorous experimental design.** The use of 10 paired seeds (training + poisoning + analysis), bootstrap CIs with B=10,000, and three independent statistical gates demonstrates methodological care.

3. **Policy-differentiated vulnerability profile.** The finding that Global dilutes per-victim harm but propagates it federation-wide, while Local confines harm but maximizes per-victim exposure, is practically useful for system designers.

4. **Strong negative controls.** The RANDOM-BENIGN control showing CIs spanning zero across all conditions validates that the effect is due to tail sampling, not position perturbation.

5. **Statistical rigor.** Gate 1 (material shift), Gate 2 (directional excess over control), and Gate 3 (downstream harm) provide a robust three-tier validation framework.

---

## 4. Top Weaknesses

| Severity | Issue | Location | Description |
|----------|-------|----------|-------------|
| **Fatal Risk** | Score-level proxy without traffic-level validation | §1, §3, §6 | The paper demonstrates score replacement programmatically, not through generated traffic. Reviewers will ask: "Can an adversary actually achieve these score values?" |
| **Major** | Overclaim of "attack" vs. "vulnerability characterization" | Abstract, §1, §7 | The paper repeatedly calls this an "attack" but §6 clarifies it's only a score-level proxy. This mismatch invites rejection. |
| **Major** | Missing distinction from standard calibration poisoning | §2 | Calibration poisoning is known in centralized settings; the paper should more precisely state what's new beyond "this happens in FL too" |
| **Major** | No defense proposal | §6 | The paper identifies a vulnerability but offers no defense. The final section says "defense design is out of scope" but doesn't even sketch requirements. |
| **Major** | Global lower attack conditionality is under-explained | §5.3 | The statement "random position replacement achieves this with probability ≈ f" needs formal derivation; also, why doesn't Global lowering work at f=0.1? |
| **Moderate** | Uniqueness detection disclosure suggests attack is detectable | §6 | The admission that duplicate scores at f=0.4 would be flagged by a uniqueness check undermines the attack's practical plausibility |
| **Moderate** | N-BaIoT federation size (N=9) is small | §4.1 | Generalizability to larger federations is unknown; the 1/N dilution might behave differently with N=100 |
| **Moderate** | q=0.95 quantile is fixed; sensitivity analysis missing | §4.1 | The paper never varies q to see if the vulnerability holds at other operating points |
| **Moderate** | Cluster policy assignments vary by seed; may mask effects | §4.2 | The paper acknowledges this but doesn't analyze how assignment variability affects results |
| **Minor** | Figure 1 caption is too long and not self-contained | §5 | The figure caption contains methodological detail that should be in the text |

---

## 5. Fatal or Near-Fatal Risks

### Risk 1: Score-Level Proxy is a Fundamental Limitation (Near-Fatal)

**Location:** Throughout, especially §1, §3, §6

**Description:** The entire experimental intervention—replacing calibration buffer entries with tail-sampled scores—is performed programmatically. The paper acknowledges in §6 that "generating network packets whose autoencoder reconstruction error lands in the target tail" is future work. This is not merely a limitation; it's a potential invalidation of the claim that the "attack" is realistic.

**Why This Could Cause Rejection:** A security paper that defines an attack must demonstrate that the attack is realizable. A skeptical reviewer may argue: "You've shown that if you can manipulate scores, bad things happen. But you haven't shown you can manipulate scores. This is circular."

**What the Paper Currently Says:** "We present this work as a vulnerability-surface characterization, not a deployed attack; traffic-level realizability is future work" (§6). This is honest but insufficient for a security venue.

**Mitigation Path:** 
- Add an ablation estimating the difficulty of traffic-level score manipulation (e.g., "what fraction of random traffic perturbations achieve tail scores?")
- Reframe the paper as "vulnerability characterization" not "attack," using passive voice throughout
- Add a concrete research agenda item: "Our current evidence establishes an upper bound on harm; future work must establish the lower bound of attack cost"

### Risk 2: Attack Detectability via Uniqueness Check (Moderate-Fatal)

**Location:** §6

**Description:** The paper admits that at f=0.4 with replacement sampling, the calibration buffer would contain duplicate scores that "easily flagged by a uniqueness check." This means a simple defense (checking for duplicate scores) would defeat the attack at high fractions.

**Why This Could Cause Rejection:** If the attack is trivially detectable by a defender who simply checks for duplicate calibration scores, the vulnerability is significantly less concerning.

**Mitigation Path:** 
- Show that without-replacement sampling produces similar effects (or run an ablation)
- Argue that a sophisticated adversary could perturb duplicate scores slightly to evade detection, and quantify the necessary perturbation magnitude

---

## 6. Section-by-Section Review

### Title

**Grade: 8/10**

**What Works:** Clear, descriptive, accurately reflects the paper's focus.

**Issues:** Slightly generic; doesn't convey the policy-differentiation finding, which is the paper's strongest contribution.

**Suggested Fix:** Consider "Policy-Differentiated Vulnerability of Threshold Calibration in Federated IoT Anomaly Detection" or similar to highlight the key finding.

**Priority:** Minor

---

### Abstract

**Grade: 6.5/10**

**What Works:** Succinctly summarizes the problem, attack model, key results (100% Gate-1 pass rate, 2.4-7.9 pp TPR degradation), and policy differentiation.

**What is Unclear:**
- "score-level contamination model" is not defined in the abstract; readers may not know what this means
- "Gate-1 pass rate" is used without definition
- "coefficient-of-variation disparity ΔCV(FPR)" appears without context

**What is Missing:**
- Explicit statement that this is a score-level proxy, not an end-to-end traffic attack
- The N-BaIoT dataset name should appear

**What is Overclaimed:**
- "degrading victim true-positive rates by 2.4 to 7.9 percentage points" — this is true but presented as if it's an attack, not a vulnerability characterization

**Reviewer Questions:**
- "What is a score-level contamination model?" → Currently not answered in abstract
- "Can this actually be realized in practice?" → Not addressed

**Suggested Fix:**
Add one sentence: "We characterize this vulnerability at the score level; traffic-level realizability is out of scope and left as future work."

**Priority:** Major

---

### 1. Introduction

**Grade: 7.5/10**

**What Works:**
- Clear motivation for why threshold calibration is undefended
- Good articulation of the temporal isolation argument
- The three axes of distinctiveness (temporally isolated, phase-specific trust model, policy-dependent effects) are well-articulated

**What is Unclear:**
- "score-level contamination model" needs a brief definition in the introduction
- "REPLACE-FIXED-BUDGET" appears in §3 but is defined later; introduce earlier

**What is Missing:**
- A concrete example of what "tail-sampled benign reconstruction scores" means in practice
- A roadmap of the paper structure at the end

**What is Overclaimed:**
- "No existing FL training-phase or aggregation-phase defense monitors or validates the calibration buffer" — this is true but presented as if calibration-stage attacks are unknown, when they are known in centralized settings

**Reviewer Questions:**
- "How is this different from standard data poisoning?" → The paper addresses this but the answer should be in the introduction, not deferred to §3
- "What exactly is the attack surface?" → Needs a diagram or clearer articulation

**Suggested Fix:** 
Add a paragraph explicitly distinguishing this from standard data poisoning in the introduction (not just §3).
Add a paper roadmap.

**Priority:** Major

---

### 2. Background and Related Work

**Grade: 6.5/10**

**What Works:**
- Concise overview of FL anomaly detection
- Good summary of existing defenses (Krum, Trimmed-Mean, FLTrust, DP)
- Acknowledges that threshold-based anomaly detection is sensitive to calibration distribution

**What is Unclear:**
- The distinction between "poisoning attacks on anomaly detectors" and "calibration-stage poisoning" is not sharp enough
- The paper says "To our knowledge, no prior work characterizes the vulnerability of the post-training threshold-calibration stage in federated threshold-based anomaly detection" — this is a narrow claim that invites challenges from the centralized literature

**What is Missing:**
- **Critical missing citation:** Work on calibration poisoning in centralized settings (e.g., attacks on threshold selection, quantile estimation under contamination). The paper cites [11,7,2] but these are general anomaly detection poisoning papers, not specifically calibration poisoning.
- The paper should cite work on robust quantile estimation or contamination-resistant threshold selection
- No mention of "data poisoning" defenses that might apply to calibration data

**What is Overclaimed:**
- The paper says "To our knowledge, no prior work characterizes the vulnerability..." — this is a knowledge claim that's hard to verify; safer to say "Existing FL defenses do not address this stage" (which is true by definition)

**Reviewer Questions:**
- "What about [Kalai et al., robust statistics] work on quantile contamination?" → Not addressed
- "How is this different from standard data poisoning? You're poisoning the calibration set." → The paper addresses this in §3 but should be in related work too

**Suggested Fix:**
Add a subsection on "Calibration Poisoning in Centralized Settings" to distinguish this work from existing attacks. Include citations to robust quantile estimation and contamination-resistant anomaly detection.

**Priority:** Major

---

### 3. Threat Model

**Grade: 8.5/10**

**What Works:**
- Clearly defines the attack surface (post-training, pre-deployment calibration)
- Explicitly states what the adversary does NOT access (model weights, gradients, other clients' data, test data, labels)
- REPLACE-FIXED-BUDGET mechanism is well-specified
- Negative control (RANDOM-BENIGN) is a strong methodological feature
- Scope boundary is stated early: "score-level characterization is a controlled experiment, not a deployed attack"

**What is Unclear:**
- "Gray-box score-level access" — does this mean the adversary knows the score distribution? Can they choose specific scores? The description "can read and modify the local calibration buffer" suggests white-box for that client's data.
- The exact mechanism for sampling from the tail is underspecified: "replacement scores are sampled with replacement from the top-10% tail" — how is the tail defined? Top 10% by value? Top 10% by percentile?
- "RANDOM-BENIGN: replacement scores are sampled uniformly from the full calibration distribution" — does this mean with or without replacement?
- "At high fractions (f=0.4), this may produce duplicate scores in the calibration buffer, which is detectable by a uniqueness check" — this is buried in the attack mechanics section but should be highlighted as a limitation

**What is Missing:**
- Formal definition of the contamination model (e.g., \(\tilde{\mathcal{C}}_i = (1-f)\mathcal{C}_i^{\text{clean}} \cup f\mathcal{C}_i^{\text{poison}}\))
- Discussion of whether the adversary can choose which positions to replace (vs. random selection)
- The "single compromised client" assumption needs justification: why not multiple compromised clients?

**What is Overclaimed:**
- "The adversary has gray-box score-level access" — but if they can read and modify the calibration buffer, this is effectively white-box for the calibration set

**Reviewer Questions:**
- "Why only one compromised client?" → The paper doesn't justify this; multi-client collusion is dismissed as "future work" but no reason is given
- "Can the adversary choose which positions to replace?" → Not specified; the REPLACE-FIXED-BUDGET suggests random positions, but it says "replaces m randomly selected positions"
- "What does 'gray-box' mean precisely?" → The term is ambiguous

**Suggested Fix:**
- Define "gray-box" more precisely: "The adversary knows the score distribution of the victim client but does not have access to the underlying traffic or model parameters"
- Add a formal contamination equation
- Add a justification for the single-client assumption: "We consider the single-compromise case as a lower-bound on damage; multi-client collusion would only amplify the effect and is left as future work"

**Priority:** Moderate

---

### 4. Experimental Protocol

**Grade: 8.0/10**

**What Works:**
- Detailed dataset description with calibration set sizes
- Clear definition of the three threshold policies with equations
- Injection fractions \(f \in \{0.0, 0.1, 0.2, 0.4\}\) are reasonable
- 10 paired seeds with independent stochasticity (training, calibration, bootstrap) is excellent
- 4,320 experimental cells is comprehensive

**What is Unclear:**
- The relationship between calibration set size and attack effect: smallest is 2,622 (Ecobee), largest is 9,909 (Danmni). Does attack effect vary with calibration set size?
- "10 paired (training + poisoning) seeds" — how are the seeds paired? The paper says "training seed i is paired with poisoning seed i+100 and analysis seed i+300" but doesn't explain why
- "All nine devices are eligible for calibration" — what's the eligibility threshold? The paper mentions \(\geq 100\) samples in §4.1 but not explicitly as a threshold
- "Cluster assignments recomputed each seed as calibration fingerprints vary with training" — this introduces extra variance; why not fix cluster assignments?

**What is Missing:**
- The autoencoder architecture is not described; what layers, dimensions, activation functions?
- FedAvg details: communication rounds, learning rate, optimizer, batch size?
- The feature extraction process: what features are extracted from network traffic?
- How are calibration sets split? Are they disjoint from training sets?

**What is Overclaimed:**
- "4320 experimental cells total" — this is a large number but doesn't necessarily translate to statistical power; the effective sample size is 10 seeds per condition

**Reviewer Questions:**
- "What autoencoder architecture did you use?" → Not specified
- "How many FedAvg rounds?" → Not specified
- "Are the calibration sets disjoint from the training sets?" → Not specified
- "Why do cluster assignments vary across seeds? This makes the Cluster policy results noisier." → The paper acknowledges this but doesn't justify it

**Suggested Fix:**
Add a subsection "4.1.1 Model Architecture and Training Protocol" with all hyperparameters. This is essential for reproducibility.

**Priority:** Major

---

### 5. Results

**Grade: 8.0/10**

**What Works:**
- Clean-baseline policy profile (Table 1) establishes that policies are statistically distinguishable
- Gate 1 results: 100% pass rate at all non-zero fractions for all policies
- Clear policy-dependent magnitude profile: Local and Cluster show larger shifts; Global shows 1/N dilution
- Downstream harm (Gate 3) quantified in percentage points
- Lowering attack results documented with conditionality acknowledged
- Figure 3 visualizes the raising/lowering trends effectively

**What is Unclear:**
- Table 1: "Worst BAP10" — what is BAP? This needs definition in the caption or text
- "Macro-F1" — is this averaged across clients or across anomaly classes?
- Figure 2: "seed 0" is shown; why not average across seeds?
- Figure 3: The RANDOM-BENIGN control is "not plotted" but should be shown for visual comparison
- "CV(FPR)" and "CV(TPR)" — the caption says CV is coefficient of variation (ddof=0); ddof=0 means population standard deviation; why not ddof=1 for sample standard deviation?

**What is Missing:**
- Statistical tests for Table 2 differences: are the TPR changes significantly different across policies at the same f?
- Effect size or practical materiality: 7.9 pp TPR degradation is significant, but what's the detection threshold? The paper doesn't define what constitutes "operationally meaningful"
- The "Global harm (-6.1 pp)" is notable but the paper doesn't explain why it's less than Local (-7.9 pp) but more than Cluster (-4.9 pp) at f=0.4

**What is Overclaimed:**
- "100% Gate-1 pass rate" — this is based on the Gate-1 criterion of \(\geq 8/10\) seeds; this is a designed threshold, not a natural finding

**Reviewer Questions:**
- "What is BAP?" → The paper uses "BAP10" without definition; this needs to be in the caption or text
- "Why does Cluster plateau from f=0.2 to f=0.4 for the raising attack?" → The paper doesn't explain this
- "Are the TPR changes statistically different between policies?" → Not tested

**Suggested Fix:**
- Define BAP in Table 1 caption
- Add an ANOVA or pairwise comparison test to Table 2
- Include the RANDOM-BENIGN control in Figure 3 as a dashed line for visual comparison
- Explain the Cluster plateau: "We suspect this is due to cluster assignment variability; at f=0.4, the contamination is saturated within the cluster"

**Priority:** Moderate

---

### 6. Discussion and Limitations

**Grade: 7.5/10**

**What Works:**
- Honest acknowledgment of the score-level proxy limitation
- Disclosure of the duplicate-score detectability issue
- Discussion of the 1/N dilution and lowering attack conditionality
- Policy-differentiation summary is clear and useful

**What is Unclear:**
- "score-level proxy" — the paper acknowledges this but doesn't explain what it would take to bridge the gap
- "Evading requires score perturbation at the cost of leaving the exact tail boundary" — this is interesting but under-explained; what perturbation magnitude is needed?

**What is Missing:**
- Concrete research agenda for bridging score-level to traffic-level
- Discussion of potential defenses, even if out of scope. The paper says "defense design is out of scope" but a paragraph on "what a defense would need to satisfy" would increase practical value
- Discussion of alternative threshold policies (e.g., median instead of mean for Global, weighted averages)
- Discussion of how calibration set size affects vulnerability (noted as a limitation but not explored)

**What is Overclaimed:**
- "The lowering attack's conditionality stems from the percentile mechanism" — this is stated but not formally proven

**Reviewer Questions:**
- "What are the properties a defense would need to satisfy?" → Not answered
- "How would a defender detect this attack in practice?" → Not addressed
- "Can this attack be extended to other anomaly detectors (isolation forest, LOF)?" → Acknowledged as future work but no speculation

**Suggested Fix:**
Add a paragraph: "Defense implications. A defense against calibration-stage poisoning would need to satisfy three properties: (1) validation that the calibration set is representative of the client's benign traffic distribution; (2) protection against score-level manipulation; and (3) detection of score duplication or unnatural concentration. We leave the design of such a defense as future work."

**Priority:** Moderate

---

### 7. Conclusion

**Grade: 7.0/10**

**What Works:**
- Summarizes the key findings
- Policy ordering is restated
- Future work directions are listed

**What is Overclaimed:**
- The conclusion still uses the language of "attack" rather than "vulnerability characterization"
- "This paper demonstrated..." — suggests a complete attack demonstration, which it isn't

**What is Missing:**
- A clear statement of what the paper adds to the field beyond the empirical characterization
- A note on practical implications for system designers

**Suggested Fix:**
Rewrite to emphasize the vulnerability characterization nature:
"This paper demonstrates that the threshold-calibration stage is vulnerable to score-level manipulation, establishing an upper bound on potential harm. We characterize this vulnerability under a controlled protocol and document policy-dependent effects. For system designers, the choice between Local and Global represents a trade-off between per-victim exposure and federation-wide propagation. Calibration-stage hardening must be designed to match the aggregation policy, not only the training-phase defense."

**Priority:** Major

---

### References

**Grade: 7.0/10**

**What Works:**
- Citations are generally appropriate for FL security
- Recent references included (2020, 2022)

**What is Missing:**
- **Critical missing citations:**
  - Kalai, A. et al., robust quantile estimation (e.g., "Robust estimation of quantiles under contamination")
  - Recent work on calibration poisoning in FL (e.g., any paper on threshold manipulation in FL)
  - N-BaIoT paper is cited [15] but not described in detail
  - FL threshold personalization literature beyond [10,18] needs more depth

**Reviewer Questions:**
- "Why didn't you cite [X] on robust quantile estimation?" → If a reviewer knows this literature, missing citations will be noticed

**Suggested Fix:**
Add citations to:
- Robust statistics / quantile estimation under contamination
- Calibration poisoning in other ML contexts (beyond [11,7,2])
- More recent FL threshold personalization work

**Priority:** Moderate

---

### Figures and Tables Audit

#### Figure 1: Attack Surface Diagram

**Grade: 7.5/10**

**Communicates:** The temporal sequence of FL training, calibration, and deployment, with training-phase defenses (green) and the undefended calibration stage (red).

**What is Confusing:**
- The figure shows "FL Training" → "Threshold Calibration" → "Detection" but doesn't show where the adversary injects the poison
- The caption says "An adversary with score-level access to one client's calibration buffer can shift τ" but the figure doesn't show this operation
- The colors are not defined in a legend (though "green" and "red" are mentioned in caption)

**Visual Fix:**
- Add an inset showing the attack operation (a client with a red "poison" label on its calibration buffer)
- Add a color legend
- Ensure figure is readable in grayscale (use patterns or labels)

**Verdict:** Keep but improve

---

#### Figure 2: Per-Client FPR Under Clean Baseline

**Grade: 8.0/10**

**Communicates:** Global forces a single threshold, producing highly variable FPRs; Local fits each client, producing more uniform FPRs.

**What is Confusing:**
- X-axis is "Device" but labels are abbreviated (e.g., "Danmni", "Ecobee") — some may not be immediately recognizable
- "seed 0" only; why not show average across seeds or a representative seed?

**Visual Fix:**
- Use full device names or provide a legend
- Add error bars or show multiple seeds as faint lines
- Ensure the "Global" and "Local" labels are clear

**Verdict:** Keep

---

#### Figure 3: Mean Threshold Shift vs. Injection Fraction

**Grade: 8.5/10**

**Communicates:** Raising attack (a) shows increasing Δτ with f; Local and Cluster have larger magnitudes than Global. Lowering attack (b) shows Local and Cluster succeed; Global is marginal.

**What is Confusing:**
- The RANDOM-BENIGN control is "not plotted" — this is a missed opportunity; showing it as a dashed line near zero would visually demonstrate the control
- The error bars are 95% bootstrap CIs but some are very small (effectively invisible) — this suggests high precision but may be due to the seed-level aggregation
- The y-axis scales differ between (a) and (b), making visual comparison difficult

**Visual Fix:**
- Add the RANDOM-BENIGN control as a dashed gray line at y=0
- Ensure CIs are visible (maybe use thicker bars or larger point sizes)
- Consider using the same y-axis scale for (a) and (b) to show the magnitude difference

**Verdict:** Keep with improvements

---

#### Table 1: Clean-Baseline Dispersion Statistics

**Grade: 7.5/10**

**Communicates:** CV(FPR), CV(TPR), Worst BAP10, Macro-F1 across three policies.

**What is Confusing:**
- "Worst BAP10" is undefined in the caption; what is BAP?
- "Macro-F1" — is this averaged across clients or anomaly types?
- "CV" is defined as coefficient of variation with ddof=0; why not ddof=1?
- The table shows mean ± std; are these across seeds or across clients?

**Visual Fix:**
- Define all acronyms in the caption
- Add a footnote explaining BAP
- Add a column explaining what each metric measures
- Ensure units are clear

**Verdict:** Keep with improved caption

---

#### Table 2: Threshold Shift and Detection Harm

**Grade: 8.0/10**

**Communicates:** Δτ, Gate-1 pass rate, and ΔTPR for raising and lowering attacks across policies and fractions.

**What is Confusing:**
- The table is dense; the three policy blocks (Global, Local, Cluster) for each attack are not visually separated
- "G1" is defined but "Gate-1 pass rate" could be misinterpreted as the number of seeds passing, not the pass rate
- The lowering rows have a dagger \((\dagger)\) but the footnote says "see §5 for ΔCV(FPR) harm metric" — this is not explanatory
- The "RANDOM-BENIGN control" is mentioned in the caption but not shown in the table

**Visual Fix:**
- Add visual separation between raising and lowering sections (e.g., a horizontal line)
- Define all abbreviations in the caption
- Add the RANDOM-BENIGN results as a row for comparison
- Use color or shading to highlight significant results

**Verdict:** Keep with improvements

---

## 7. Reviewer Questions the Paper Must Already Answer

### Threat Model Questions

| Question | Current Answer | Sufficiency | Fix Needed |
|----------|---------------|-------------|------------|
| "Can the adversary choose which calibration scores to replace?" | Yes, randomly selected positions (REPLACE-FIXED-BUDGET) | Sufficient | None |
| "Why only one compromised client?" | "Single-client attack scope" stated but not justified | Insufficient | Add justification: single client as lower bound |
| "What does 'gray-box' mean precisely?" | Described as "can read and modify local calibration buffer" | Ambiguous | Define precisely |
| "Does the adversary know the score distribution?" | Implicitly yes (gray-box access) | Implicit | State explicitly |
| "Can the adversary target specific victims?" | Under Global, all are affected; under Local, only the compromised client | Sufficient | None |

### Novelty Questions

| Question | Current Answer | Sufficiency | Fix Needed |
|----------|---------------|-------------|------------|
| "How is this different from standard data poisoning?" | Three axes: temporal isolation, trust model, policy-dependent effects | Addressed in §3 | Move to introduction or related work |
| "Isn't calibration poisoning known in centralized settings?" | Acknowledged in §2 but not distinguished | Weak | Add explicit distinction in related work |
| "What's new beyond applying a known attack to FL?" | Policy-differentiated vulnerability profile | Sufficient | Emphasize more |

### Methodology Questions

| Question | Current Answer | Sufficiency | Fix Needed |
|----------|---------------|-------------|------------|
| "What autoencoder architecture?" | Not specified | Insufficient | Add architecture details |
| "How many FedAvg rounds?" | Not specified | Insufficient | Add training protocol |
| "Are calibration sets disjoint from training sets?" | Not specified | Insufficient | Clarify |
| "Why q=0.95 only?" | Not explained | Insufficient | Add sensitivity analysis or justification |
| "Why 10 seeds?" | Not justified | Minor | Add power analysis or citation |

### Dataset Questions

| Question | Current Answer | Sufficiency | Fix Needed |
|----------|---------------|-------------|------------|
| "Why N-BaIoT?" | Widely used evaluation platform | Sufficient | None |
| "Why only 9 devices?" | Dataset has 9 physical device types | Sufficient | None |
| "Are results generalizable to other IoT datasets?" | Acknowledged as future work | Sufficient | None |

### Metric Questions

| Question | Current Answer | Sufficiency | Fix Needed |
|----------|---------------|-------------|------------|
| "What is BAP10?" | Not defined | Insufficient | Define in Table 1 caption |
| "Why use CV(FPR) as fairness metric?" | Not justified | Minor | Add explanation |
| "Why use population std (ddof=0) instead of sample std (ddof=1)?" | Not addressed | Minor | Explain or change |
| "What constitutes 'operationally meaningful' harm?" | Not defined | Major | Add practical thresholds |

### Statistical Validity Questions

| Question | Current Answer | Sufficiency | Fix Needed |
|----------|---------------|-------------|------------|
| "Why 95% bootstrap CIs with 10 seeds?" | Not justified | Minor | Add citation or explanation |
| "Are the 10 seeds enough for distributional assumptions?" | Not addressed | Minor | Add power analysis |
| "Why paired seeds (i, i+100, i+300)?" | "Statistically independent stochasticity" stated | Sufficient | None |
| "Are the Gate criteria arbitrary?" | "≥8/10 seeds" and "≥5/9 victims" chosen | Potentially arbitrary | Add justification |

### Baseline Questions

| Question | Current Answer | Sufficiency | Fix Needed |
|----------|---------------|-------------|------------|
| "Why no other FL algorithm (FedProx, SCAFFOLD)?" | Acknowledged as future work | Sufficient | None |
| "Why no other anomaly detector?" | Acknowledged as future work | Sufficient | None |
| "Why no comparison to training-phase defenses?" | Defenses are structurally blind | Sufficient | None |

### Reproducibility Questions

| Question | Current Answer | Sufficiency | Fix Needed |
|----------|---------------|-------------|------------|
| "Is code available?" | Not stated | Insufficient | Add artifact statement |
| "Are seeds specified?" | Yes, i, i+100, i+300 | Sufficient | None |
| "Hardware/software environment?" | Not specified | Insufficient | Add |

### Scope and Limitation Questions

| Question | Current Answer | Sufficiency | Fix Needed |
|----------|---------------|-------------|------------|
| "Is this a real attack or a vulnerability characterization?" | "Vulnerability characterization" in §6, but "attack" elsewhere | Inconsistent | Consistent language throughout |
| "What would a defense look like?" | Out of scope | Weak | Add defense requirements paragraph |
| "Can this be extended to other FL settings?" | Acknowledged as future work | Sufficient | None |

### Visual/Formatting Questions

| Question | Current Answer | Sufficiency | Fix Needed |
|----------|---------------|-------------|------------|
| "What is BAP in Table 1?" | Not defined | Insufficient | Define |
| "Why is RANDOM-BENIGN control not shown in Figure 3?" | "Not plotted" stated | Weak | Add it |
| "Why is Figure 1 not self-contained?" | Caption contains methodology detail | Minor | Simplify caption |

---

## 8. Claim Discipline Audit

| Claim (paraphrased) | Location | Support Level | Weakness | Safe Rewrite | Stay in Paper? |
|---------------------|----------|---------------|----------|--------------|----------------|
| "The threshold-calibration stage is an undefended attack surface" | Abstract, §1 | **Fully supported** | None | No change needed | Yes |
| "FL defenses are structurally blind to this stage" | §1, §3 | **Fully supported** | None | No change needed | Yes |
| "100% Gate-1 pass rate at all non-zero fractions" | Abstract, §5 | **Fully supported** | Gate-1 criterion is arbitrary | Keep as empirical result with definition | Yes |
| "Victim TPR degrades by 2.4-7.9 pp" | Abstract, §5 | **Fully supported** | None | No change needed | Yes |
| "The lowering attack succeeds for Local and Cluster but is structurally bounded for Global" | Abstract, §5.3 | **Fully supported** | Lowering for Global is marginal at f=0.1 | No change needed | Yes |
| "This is structurally distinct from data poisoning" | §1 | **Partially supported** | The three axes are conceptual, not experimental | Add evidence or soften to "conceptually distinct" | Yes, with softening |
| "A complete end-to-end attack would additionally require generating network traffic" | §6 | **Fully supported** | This is an honest limitation | No change needed | Yes |
| "Traffic-level realizability is future work" | §6 | **Fully supported** | Honest acknowledgment | No change needed | Yes |
| "The attack bypasses all training-phase defenses" | Abstract, §1 | **Partially supported** | It doesn't "bypass" them; it attacks a different stage | Change to "is structurally outside the scope of" | Yes, with rewording |
| "AUROC invariance verifies the attack is confined to calibration" | §4.5 | **Fully supported** | None | No change needed | Yes |
| "Policy choice determines not just per-victim magnitude but blast radius" | Abstract | **Fully supported** | None | No change needed | Yes |
| "The adversary has strictly weaker capability than model-poisoning adversaries" | §3 | **Fully supported** | None | No change needed | Yes |
| "The lowering results are a lower bound under REPLACE-FIXED-BUDGET" | §5.3, §6 | **Fully supported** | None | No change needed | Yes |
| "Random position replacement achieves lowering with probability ≈ f" | §5.3 | **Partially supported** | No formal derivation | Add derivation or citation | Yes, with derivation |
| "At f=0.4, duplicates are easily flagged by a uniqueness check" | §6 | **Fully supported** | This undermines attack plausibility | Acknowledge as limitation | Yes, with emphasis |

---

## 9. Methodology and Experiment Audit

| Issue | Location | Why It Matters | Reviewer Risk | Fix | Priority |
|-------|----------|----------------|---------------|-----|----------|
| **Score-level proxy** | Throughout | Core intervention is not traffic-realizable | High | Add traffic feasibility ablation | **Fatal** |
| **Missing autoencoder architecture** | §4.1 | Cannot reproduce | High | Add architecture details | **Major** |
| **Missing FedAvg hyperparameters** | §4.1 | Cannot reproduce | High | Add training details | **Major** |
| **Calibration set overlap with training** | §4.1 | Potential data leakage | High | Clarify disjointness | **Major** |
| **No defense design or requirements** | §6 | Paper identifies vulnerability but no solution | Moderate | Add defense requirements paragraph | Major |
| **BAP10 undefined** | Table 1 | Metric uninterpretable | Moderate | Define in caption | Major |
| **q=0.95 fixed without justification** | §4.1 | Generalizability unknown | Moderate | Add sensitivity analysis | Moderate |
| **Cluster assignments vary by seed** | §4.2 | Extra variance; results noisier | Moderate | Justify or fix assignments | Moderate |
| **Only N=9 clients** | §4.1 | Generalizability to larger federations | Moderate | Acknowledge in limitations | Moderate |
| **RANDOM-BENIGN control not shown in Figure 3** | §5.2 | Visual comparison missing | Minor | Add to figure | Moderate |
| **No multiple comparison correction** | §5 | Many comparisons; potential false positives | Minor | Add Bonferroni or similar | Moderate |
| **Effect size materiality threshold not defined** | §4.4 | What's "operationally meaningful"? | Minor | Define practical thresholds | Minor |
| **Power analysis missing** | §4.4 | Are 10 seeds enough? | Minor | Add power analysis or citation | Minor |

---

## 10. Figures and Tables Audit (Detailed)

### Figure 1: Attack Surface Diagram

**Grade: 7.5/10**

**What It Communicates:** Temporal sequence of FL phases; training-phase defenses (green) vs. undefended calibration (red).

**What Is Confusing:**
- No visual depiction of the actual attack operation
- Colors may not be distinguishable in grayscale
- Caption contains methodological detail that should be in text

**Visual Fix:**
- Add an attack operation inset
- Use patterns or labels for grayscale readability
- Simplify caption

**Verdict:** Keep but improve

---

### Figure 2: Per-Client FPR Under Clean Baseline

**Grade: 8.0/10**

**What It Communicates:** Global threshold forces high FPR variability; Local fits each client's distribution.

**What Is Confusing:**
- Only seed 0 shown; not representative?
- Device labels abbreviated
- No error bars

**Visual Fix:**
- Show multiple seeds as faint lines or average with error bars
- Full device names

**Verdict:** Keep

---

### Figure 3: Mean Threshold Shift vs. Injection Fraction

**Grade: 8.5/10**

**What It Communicates:** Raising attack magnitudes; lowering attack conditionality.

**What Is Confusing:**
- RANDOM-BENIGN control not shown
- Y-axis scales differ
- Some CIs are very small

**Visual Fix:**
- Add control as dashed line
- Use consistent y-axis scale
- Make CIs more visible

**Verdict:** Keep with improvements

---

### Table 1: Clean-Baseline Dispersion Statistics

**Grade: 7.5/10**

**What It Communicates:** Policy differences in baseline FPR/TPR dispersion.

**What Is Confusing:**
- BAP10 undefined
- Macro-F1 unclear
- ddof=0 vs. ddof=1 not justified

**Visual Fix:**
- Define all acronyms in caption
- Add footnote explaining BAP
- Justify ddof choice

**Verdict:** Keep with improved caption

---

### Table 2: Threshold Shift and Detection Harm

**Grade: 8.0/10**

**What It Communicates:** Quantitative results for all attack-policy-fraction combinations.

**What Is Confusing:**
- Dense; policy blocks not visually separated
- RANDOM-BENIGN control only in caption
- Lowering dagger footnote unclear

**Visual Fix:**
- Add horizontal separation between raising/lowering
- Show control results as a row
- Clarify dagger footnote

**Verdict:** Keep with improvements

---

## 11. Visual and Formatting Review

### Overall Layout
**Grade: 7.5/10**

**Positive:**
- Consistent formatting
- Clear section headings
- Appropriate use of bold and italic

**Issues:**
- Page 4: "Scope boundary" paragraph is dense; consider breaking into bullet points
- Page 5: Cluster policy description says "assignments recomputed each seed" — this should be in a footnote or parenthetical
- Page 6: Gate definitions are dense; consider a table or bullet points
- Page 8: "Policy-Differentiation Summary" uses bullet points but could be a table for clarity
- Page 9: Figure 3 caption is long; move some detail to text

### Font Sizes and Readability
**Grade: 8.0/10**

**Positive:**
- Body text is readable
- Equations are clearly formatted

**Issues:**
- Figure 1 may be too small when printed
- Figure 3 error bars may not be visible at some zoom levels
- Table 2 is dense; font size may be borderline

### Captions
**Grade: 7.0/10**

**Positive:**
- Captions are informative

**Issues:**
- Figure 1 caption: too long and contains methodology
- Table 1 caption: BAP undefined
- Table 2 caption: RANDOM-BENIGN control mentioned but not shown
- Figure 3 caption: "Random-Benign negative control (not plotted)" — should be plotted

### Color and Accessibility
**Grade: 7.5/10**

**Positive:**
- Color use is appropriate for digital viewing

**Issues:**
- Grayscale readability is unknown (Figure 1 relies on green/red)
- No mention of color accessibility

---

## 12. Related Work and Novelty Review

### Closest Prior Work

| Work | Similarity | Key Difference | How the Paper Distinguishes |
|------|------------|----------------|----------------------------|
| Bagdasaryan et al. (2020) - Backdoor FL | FL poisoning | Attacks training phase, not calibration | §2 mentions but doesn't fully distinguish |
| Blanchard et al. (2017) - Krum | Byzantine-robust aggregation | Defends training phase | §2 mentions |
| Cao et al. (2020) - FLTrust | Byzantine-robust FL | Server-trusted dataset | §2 mentions |
| Cretu et al. (2008) - Calibration poisoning in centralized setting | Calibration poisoning | Not FL; single-owner data | §2 mentions but doesn't distinguish fully |
| Kloft & Laskov (2012) - Online anomaly detection under adversarial impact | Anomaly detection poisoning | Not FL; different attack model | §2 mentions |

### Missing Citations

1. **Kalai, A. et al.** - Robust quantile estimation under contamination (would be relevant to the lowering attack conditionality)
2. **Recent FL threshold personalization work** beyond [10,18] - The paper cites two works but this is a growing area
3. **Data poisoning defenses for calibration sets** - If any exist, they should be mentioned
4. **Contamination-resistant anomaly detection** - Work on robust anomaly detection under data contamination
5. **Physical-layer attack feasibility** - Any work on generating network traffic to achieve target reconstruction scores

### Novelty Score: 7.5/10

**Justification:** The paper identifies a legitimate gap (post-training threshold calibration is undefended) and provides empirical characterization across three policy families. However, the novelty is somewhat narrow:
- The concept of calibration poisoning is known in centralized settings
- The FL-specific aspect is the policy-differentiated vulnerability profile
- The score-level proxy is a controlled experiment, not a full attack demonstration

**Safe Novelty Statement:** "This paper presents the first characterization of the post-training threshold-calibration stage as an attack surface in federated IoT anomaly detection, and documents policy-dependent vulnerability profiles that are distinct from training-phase security considerations."

---

## 13. Reproducibility Checklist

| Item | Status | Missing Detail | Priority |
|------|--------|----------------|----------|
| **Dataset** | Partial | N-BaIoT version, download location | Major |
| **Data splits** | Missing | Train/calibration/test split percentages | Major |
| **Train/calibration disjointness** | Missing | Are they disjoint or overlapping? | Major |
| **Autoencoder architecture** | Missing | Layers, dimensions, activations | **Critical** |
| **FedAvg hyperparameters** | Missing | Rounds, learning rate, optimizer, batch size | **Critical** |
| **Feature extraction** | Missing | What features from network traffic? | **Critical** |
| **Threshold quantile q** | Specified | q=0.95 | Sufficient |
| **Injection fractions** | Specified | f∈{0.0, 0.1, 0.2, 0.4} | Sufficient |
| **Seeds** | Specified | i, i+100, i+300 | Sufficient |
| **Cluster policy details** | Specified | K=3, k-means++, random_state=42 | Sufficient |
| **Attack mechanism** | Specified | REPLACE-FIXED-BUDGET | Sufficient |
| **Statistical methods** | Specified | Bootstrap CIs, 10,000 resamples | Sufficient |
| **Hardware/software** | Missing | GPUs, libraries, versions | Minor |
| **Code availability** | Missing | No artifact statement | Major |
| **Evaluation metrics** | Specified | CV(FPR), CV(TPR), BAP10, Macro-F1 | BAP10 undefined |

### Reproducibility Grade: 7.5/10

**Missing Critical Items:**
- Autoencoder architecture
- FedAvg hyperparameters
- Feature extraction details
- Train/calibration/test split details
- Code/artifact availability

---

## 14. Action Plan to Reach 10/10

### Must Fix Before Submission (Critical)

1. **Reframe all "attack" language to "vulnerability characterization"** - Throughout the paper, distinguish between the controlled experiment (score-level contamination) and a real attack (traffic-level realization). The paper repeatedly says "the attack achieves X" but §6 admits it's a proxy. This inconsistency will be caught by reviewers.

2. **Add autoencoder architecture and FedAvg hyperparameters** - A paper reviewer cannot reproduce the results without these. Add a new subsection "4.1.1 Model Architecture and Training Protocol" with layer dimensions, activations, optimizer, learning rate, batch size, number of communication rounds, and feature list.

3. **Clarify train/calibration/test disjointness** - Add a statement: "Calibration sets are drawn from benign traffic separate from the training set; test sets are held out from both."

4. **Add traffic-feasibility ablation** - Even a simple experiment would help: "We attempted to generate traffic variations that achieve tail reconstruction scores and found that only X% of random perturbations succeed." This would strengthen the argument that the score-level proxy is a meaningful upper bound.

5. **Add defense requirements paragraph** - In §6, add: "A defense against calibration-stage poisoning would need to satisfy three properties: (1) validation that the calibration set is representative of the client's benign traffic distribution; (2) protection against score-level manipulation; and (3) detection of score duplication or unnatural concentration."

### Should Fix If Page Budget Allows (Major)

6. **Define BAP10 in Table 1 caption** - Add a footnote explaining what "Worst BAP10" means.

7. **Show RANDOM-BENIGN control in Figure 3** - Add as a dashed line or separate panel to visually demonstrate the control effect.

8. **Add multiple comparison correction** - For the many comparisons in Table 2, add Bonferroni or similar to justify the 95% CIs.

9. **Add sensitivity analysis for q** - Vary q (e.g., 0.90, 0.95, 0.99) to show the vulnerability holds across operating points.

10. **Formalize the lowering attack probability derivation** - Show mathematically why random position replacement achieves lowering with probability ≈ f.

11. **Add power analysis** - Justify that 10 seeds are sufficient for the bootstrap CIs.

12. **Improve related work section** - Add explicit distinction from centralized calibration poisoning and robust quantile estimation literature.

### Nice to Fix (Minor)

13. **Add cluster assignment justification** - Explain why cluster assignments are recomputed each seed rather than fixed.

14. **Use consistent ddof** - If using population std (ddof=0), justify; otherwise use sample std (ddof=1).

15. **Improve Figure 1 clarity** - Add attack operation inset and color legend.

16. **Add hardware/software environment** - Include GPU model, library versions.

17. **Add artifact statement** - State whether code will be available.

### Do Not Touch / Already Strong

- The experimental protocol with 10 paired seeds is a strength; do not change.
- The three-gate statistical framework is robust; do not overcomplicate.
- The policy-differentiated vulnerability summary is clear; do not remove.
- The negative control (RANDOM-BENIGN) is well-designed; do not alter.
- The AUROC invariance check is a strong sanity check; keep.

---

## 15. Final Reviewer Simulation

### Reviewer 1: Supportive Expert (FL/IoT Security)

**Likely Score: 8/10**

**Summary Judgment:** "This paper identifies a legitimate gap in FL security research and presents a well-controlled experimental characterization. The policy-differentiated vulnerability profile is a genuine contribution. However, the score-level proxy limitation is significant and prevents this from being a complete attack demonstration."

**Main Objections:**
1. "The attack is demonstrated at score level, not traffic level. Can an adversary actually generate traffic with tail reconstruction scores?"
2. "The paper claims this is 'structurally distinct from data poisoning' but the distinction is conceptual, not experimental."

**Questions They Would Ask:**
- "What would a defender need to do to detect or prevent this?"
- "How does the attack effect vary with calibration set size?"
- "Why is the attack only demonstrated on one FL algorithm (FedAvg) and one detector (autoencoder)?"

**Answer the Paper Gives:**
- Score-level limitation is acknowledged in §6
- Defense is out of scope
- Generalization is acknowledged as future work

**Sufficiency:** Partial - the paper acknowledges but doesn't resolve the main objection.

**Neutralization:** Add a traffic-feasibility ablation and a defense requirements paragraph.

---

### Reviewer 2: Skeptical Methods Reviewer

**Likely Score: 6/10**

**Summary Judgment:** "This is essentially a data poisoning attack on calibration data, which is known. The only novelty is that it's applied in an FL context and shows policy-dependent effects. The score-level proxy is a fatal flaw."

**Main Objections:**
1. "This is just data poisoning on a different phase. The paper overclaims novelty."
2. "The score-level proxy means this is not a real attack; it's a simulation."
3. "The duplicates at f=0.4 would be detectable, so the attack is trivially defeated."
4. "No comparison to training-phase defenses that might also protect calibration data."

**Questions They Would Ask:**
- "Can you demonstrate that the attack is actually feasible?"
- "Why should we care if a simple uniqueness check defeats it?"
- "What about robust quantile estimation as a defense?"

**Answer the Paper Gives:**
- Distinction from data poisoning is in §3
- Score-level limitation is in §6
- Uniqueness check is disclosed in §6
- No comparison to defenses

**Sufficiency:** Insufficient - the core methodology objection (score-level proxy) is not resolved.

**Neutralization:** 
- Add a traffic-feasibility ablation showing that even if not fully realizable, the score-level proxy provides an upper bound
- Show that without-replacement sampling avoids detection and produces similar results
- Add a defense requirements paragraph

---

### Reviewer 3: Security/Adversarial ML Reviewer

**Likely Score: 7/10**

**Summary Judgment:** "This is a well-executed vulnerability characterization. The paper correctly identifies a phase that training-phase defenses don't cover. The statistical protocol is rigorous. However, the practical attack feasibility is unproven, and the duplicates issue undermines the attack at high fractions."

**Main Objections:**
1. "The attack requires the adversary to have the ability to manipulate calibration scores, which is not demonstrated."
2. "The 'gray-box' assumption is under-specified."
3. "The paper doesn't consider multi-client collusion, which could amplify the effect."

**Questions They Would Ask:**
- "What is the threat model for data collection? Does the client have a secure enclave?"
- "Can this be extended to targeted attacks (e.g., suppressing alarms for specific attack types)?"
- "Would differential privacy for calibration data defeat this?"

**Answer the Paper Gives:**
- Threat model is in §3
- Multi-client collusion is future work
- DP is mentioned as a training-phase defense but not applied to calibration

**Sufficiency:** Partial - the threat model is well-specified but the practical feasibility is not.

**Neutralization:** 
- Add a more detailed threat model for how an adversary gains score-level access
- Add a small experiment showing targeted suppression

---

### Reviewer 4: Presentation/Clarity Reviewer

**Likely Score: 7.5/10**

**Summary Judgment:** "The paper is well-structured but dense. Some terminology is undefined (BAP10, Gate-1). The figures are clean but not fully self-contained. The abstract and introduction could more clearly distinguish between vulnerability characterization and deployed attack."

**Main Objections:**
1. "BAP10 in Table 1 is undefined."
2. "Figure 3 doesn't show the RANDOM-BENIGN control."
3. "The paper calls it an 'attack' throughout but §6 says it's a 'vulnerability characterization' - inconsistent language."
4. "The conclusion is too brief and doesn't state the practical implications clearly."

**Questions They Would Ask:**
- "What does BAP10 mean?"
- "Why is the control not shown?"
- "Is this a real attack or a vulnerability characterization?"

**Answer the Paper Gives:**
- BAP10 not defined
- Control "not plotted" in Figure 3
- Language is inconsistent ("attack" vs. "vulnerability characterization")
- Conclusion is brief

**Sufficiency:** Insufficient - these are easy fixes.

**Neutralization:** 
- Define BAP10 in Table 1 caption
- Add control to Figure 3
- Use consistent language throughout
- Expand conclusion with practical implications

---

## Consolidated Reviewer Questions That Must Already Be Answered

| Category | Question | Location Answered | Sufficiency | Fix |
|----------|----------|-------------------|-------------|-----|
| Threat Model | "Why only one compromised client?" | §3 | Insufficient | Add justification |
| Threat Model | "What does gray-box mean precisely?" | §3 | Ambiguous | Define precisely |
| Novelty | "How is this different from standard data poisoning?" | §3 | Partial | Move to introduction |
| Methodology | "What autoencoder architecture?" | §4 | Missing | Add details |
| Methodology | "How many FedAvg rounds?" | §4 | Missing | Add details |
| Methodology | "Are calibration sets disjoint from training?" | §4 | Missing | Clarify |
| Methodology | "Why q=0.95 only?" | §4 | Missing | Add sensitivity analysis |
| Dataset | "Are results generalizable to other IoT datasets?" | §6 | Acknowledged | Keep as limitation |
| Metric | "What is BAP10?" | Table 1 | Missing | Define in caption |
| Metric | "What constitutes operationally meaningful harm?" | §4.4 | Missing | Add practical thresholds |
| Statistical | "Why 95% CIs with 10 seeds?" | §4.4 | Implicit | Add power analysis |
| Baseline | "Why no comparison to other FL algorithms?" | §6 | Acknowledged | Keep as limitation |
| Scope | "Is this a real attack or vulnerability characterization?" | Throughout | Inconsistent | Consistent language |
| Scope | "What would a defense look like?" | §6 | Missing | Add requirements paragraph |
| Visual | "What is BAP?" | Table 1 | Missing | Define |

---

# Final Verdict

**Current Submission Status: Almost Ready (with revisions)**

**Probability of Acceptance (current): 60%**

**Probability of Acceptance (after fixes): 85%**

**Primary Barrier to Acceptance:** The score-level proxy limitation. This is the one issue that could cause a desk reject or strong rejection. The paper must either:
1. Show that score-level manipulation is feasible (traffic-level validation), OR
2. Explicitly frame the paper as a "vulnerability characterization" with all claims softened accordingly

**What Score the Paper Could Reach After Fixes: 9.0/10**

**The exact top-priority fixes needed to reach 9/10:**
1. Consistent language: "vulnerability characterization" not "attack"
2. Add autoencoder architecture and FedAvg hyperparameters
3. Add traffic-feasibility ablation or explicit upper-bound argument
4. Add defense requirements paragraph in §6
5. Define BAP10 in Table 1 caption
6. Show RANDOM-BENIGN control in Figure 3

**The exact fixes needed to reach 10/10:**
All of the above, plus:
7. Traffic-level realizability demonstration (future work, but if done now, would be a major boost)
8. Sensitivity analysis for q (0.90, 0.95, 0.99)
9. Formal derivation of lowering attack probability
10. Multi-client collusion simulation