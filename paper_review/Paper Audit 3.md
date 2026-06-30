Now I have a comprehensive picture of the paper, its pre-registered protocol, and its research ecosystem. I can now deliver a full 9-pass review. This will be detailed, direct, and evidence-based.

***

# Paper Audit and Review Report
**Paper:** *Poisoning the Threshold-Calibration Stage in Federated IoT Anomaly Detection: A Policy-Differentiated Vulnerability Analysis*
**Authors:** Naslouby, Lachgar, Hrimech

***

## 1. Executive Verdict

**Overall Grade: 6.8 / 10**
**Recommendation: Borderline / Weak Accept — Conditional on revisions**

This paper identifies a genuinely novel and structurally precise attack surface—the post-training threshold-calibration stage in federated IoT anomaly detection—and delivers a controlled, methodologically self-aware vulnerability characterization. The claim discipline is largely respected: AUROC invariance is correctly framed as a sanity check, the score-level proxy is disclosed, and policy differentiation is empirically demonstrated. These are real strengths.

However, the paper carries a cluster of weaknesses that a skeptical program-committee reviewer will exploit hard: (1) the experiment runs on exactly 9 devices with 10 seeds—a statistically thin substrate that yields CIs over only 10 samples; (2) the lowering attack is structurally weak yet given near-equal billing with the raising attack; (3) the "negative control" design is incompletely specified in the paper (the paper does not explain that RANDOM-BENIGN uses the same replacement positions, only different source scores—readers may not grasp this distinction); (4) no multi-client collusion is evaluated despite it being the most natural attack escalation; (5) the abstract and introduction carry mild overclaiming about what "100% Gate-1 pass rate" actually proves under N=10 seeds; and (6) Table 2 dominates the results but is presented without a companion figure for the downstream ΔCV(FPR) lowering-attack harm, leaving that claim visually underpowered.

**Main reason to accept:** Genuine structural novelty—the calibration stage as a post-training attack surface is not studied in any cited prior work, the policy-differentiated analysis is precisely formulated, and the three-gate evaluation framework is rigorous by FL-security paper standards.

**Main reason to reject:** N=10 seed bootstrap CIs over 9 devices is a fragile statistical basis. Every major empirical claim reduces to 10 data points. A 95% CI from 10,000 bootstrap resamples of a 10-point sample is not a robust 95% CI.

**Fastest path to improve:** (1) Expand to ≥20 seeds (compute is cheap here—only calibration-level operations, not retraining). (2) Add the ΔCV(FPR) lowering-attack result to Figure 3 or a dedicated panel. (3) Add one paragraph explicitly differentiating this from standard data poisoning across three axes—the paper attempts this in §1 but the argument is compressed and will not survive a skeptical reviewer without more precision.

***

## 2. Scorecard

| Category | Score /10 | Notes |
|---|---|---|
| Novelty | 8.0 | Calibration-stage isolation is genuinely new; the policy-differentiation lens adds value |
| Technical correctness | 7.5 | Gate framework is sound; lowering-attack interpretation has a subtle logical gap |
| Methodological rigor | 6.5 | 10-seed bootstrap CIs, 9 devices, no multi-client; cluster decomposition underspecified |
| Experimental support | 6.5 | Raising attack is well-supported; lowering attack is structurally conditional and thinly supported |
| Claim discipline | 7.5 | Generally good; a few abstract/intro sentences still slightly overclaim |
| Related work positioning | 6.0 | The "no prior work" claim is asserted but not defended against adjacent poisoning literature |
| Reproducibility | 6.0 | Seeds, fractions, reservoir size, k-means params disclosed; autoencoder architecture absent |
| Visual presentation | 5.5 | Figure 3 is adequate; Figure 2 uses only seed 0; Table 2 is well-structured but the lowering metric is missing from figures |
| Writing clarity | 7.0 | Mostly clear; §3 threat model mixes mechanism with scope in a way that confuses readers |
| Reviewer-proofness | 5.5 | Multiple lines of attack remain open and undefended in the paper |

***

## 3. Top Strengths

1. **Precise attack surface isolation.** The paper cleanly demonstrates that the calibration stage is structurally outside the scope of every cited defense. This is a true observation, not marketing.
2. **Policy-differentiated vulnerability profile.** The Local/Cluster/Global trichotomy with quantitative blast-radius analysis is the paper's most original contribution and is well-executed.
3. **Three-gate evaluation framework.** Gates 1–3 (material shift → directional excess over control → downstream harm) are a principled, pre-specified hierarchy that is better than most FL-security papers.
4. **AUROC invariance as sanity check, correctly framed.** The paper explicitly says AUROC invariance is a "protocol check, not a contribution"—this is disciplined and reviewer-proofing.
5. **Negative control design.** Including Random-Benign as a control and verifying that it produces CIs spanning zero is methodologically sound and under-common in this literature.
6. **Isolation sanity checks (§4.5).** Bitwise identical weights, unchanged score ordering, AUROC invariance—these three checks are rigorous and should be highlighted more prominently.
7. **Explicit scope boundary.** The paper does not claim deployability, traffic-level realizability, or generalization beyond N-BaIoT—this is rare and creditable.

***

## 4. Top Weaknesses

| # | Severity | Location | Weakness |
|---|---|---|---|
| W1 | **Major** | §4.4, §5 | N=10 seed bootstrap CIs. A 95% percentile CI resampled 10,000 times from 10 observations is severely underpowered. CIs exclude zero, but the effective sample size is 10, not 10,000. |
| W2 | **Major** | §5.3, Abstract | The lowering attack is presented near-symmetrically with the raising attack, but it is structurally conditional, weaker, and explicitly labeled a "lower bound." The abstract and §5.3 do not clearly degrade its epistemic status relative to the raising attack. |
| W3 | **Major** | §3, §5 | Multi-client collusion is not evaluated and is only briefly dismissed. A reviewer will immediately ask: what if two or three clients are compromised simultaneously? |
| W4 | **Major** | §2, §1 | The "no prior work" claim for calibration-stage poisoning is asserted but not defended against broader data poisoning, online learning poisoning (Kloft & Laskov 2012, cited as ), and FL calibration work. The distinction is asserted but not demonstrated comparatively. |
| W5 | **Moderate** | §4.2 | The Cluster policy's K=3 assignment is fixed but the paper does not report what the three clusters actually are (which devices end up in which cluster), making the "intra-cluster spillover" result uninterpretable without supplementary material. |
| W6 | **Moderate** | §5.2 | "−30–80 undetected Mirai flows per 1000 attack packets" (p.8): this translation assumes a specific traffic rate that is not cited or justified. It appears as a concrete harm claim but rests on an undisclosed assumption. |
| W7 | **Moderate** | §6, Fig 3 | Figure 3(b) plots Δτ for the lowering attack but no figure shows ΔCV(FPR)—the metric the paper itself says is the "operational harm metric" for the lowering attack. The most important lowering-attack metric is table-only. |
| W8 | **Moderate** | §4.3 | The paper says "4 source-objective pairs × 3 threshold policies × 4 injection fractions × 9 victim clients × 10 seeds = 4,320 cells" but only 2 attack directions × 2 strategies (Raise/Lower + Random/Tail) = 4 source-objective pairs are described. The 4-pair arithmetic is correct, but the paper never lists all four pairs explicitly. |
| W9 | **Moderate** | §3 | The threat model does not state explicitly and prominently that test scores and test labels remain unchanged. This is mentioned in §4.1 as part of AUROC invariance framing, but should be a first-sentence axiom in §3. |
| W10 | **Minor** | Fig. 2 | Figure 2 uses only "seed 0." It is captioned as a baseline illustration but the text uses it to support a CV(FPR) claim (0.91 vs 0.33). The figure should show the mean across all 10 seeds or be relabeled as illustrative-only. |

***

## 5. Fatal or Near-Fatal Risks

### Risk F1 — Statistical basis: N=10 seeds, borderline bootstrap
**Location:** §4.4, §5, all tables
**Problem:** Every confidence interval in the paper is a 95% percentile bootstrap over exactly 10 seed-level aggregates with B=10,000 resamples. The law of large numbers for bootstrap convergence applies to the *sampling* distribution, not the *sample size*. With N=10 observations, the nominal 95% CI coverage is unreliable, especially for asymmetric distributions. A methods reviewer at a top venue will know this.
**What this could cause:** Rejection with the comment "the statistical basis is insufficient; confidence intervals over 10 seeds cannot be meaningfully interpreted as 95% CIs."
**Fix:** Run ≥20 seeds (only calibration re-runs, no retraining required since model weights are frozen). Report bootstrap CIs with explicit power limitations. Alternatively, switch to BCa bootstrap (better small-sample coverage) and add a single sentence acknowledging undercoverage risk at N=10.

### Risk F2 — "No prior work" claim under scrutiny
**Location:** §2, last paragraph: "To our knowledge, no prior work characterizes the vulnerability of the post-training threshold-calibration stage in federated threshold-based anomaly detection."
**Problem:** This claim is almost certainly true, but the paper does not *demonstrate* it is true. It cites  (Kloft & Laskov, online anomaly detection under adversarial impact), which is directly about manipulating thresholds in an online anomaly detector. The paper does not explain why  does not constitute prior work on this surface. If a reviewer knows  well, this could be flagged.
**Fix:** Add one sentence after the claim: "Kloft & Laskov  study adversarial threshold manipulation in *centralized* online anomaly detection; their setting lacks the post-training, client-autonomous calibration phase and the federation-wide policy propagation that distinguish our attack surface."

### Risk F3 — Lowering attack epistemic status
**Location:** Abstract, §5.3
**Problem:** The abstract says the lowering attack "succeeds for Local and Cluster"—but §5.3 describes it as "structurally conditional" and a "lower bound." These characterizations are in tension. A reviewer who reads the abstract will expect a symmetric attack story; §5.3 delivers something considerably weaker. This creates a credibility gap.
**Fix:** Downgrade the abstract's lowering-attack language: change "succeeds" to "produces bounded threshold displacement and significant FPR disparity (as a lower bound under Replace-Fixed-Budget) for Local and Cluster."

***

## 6. Section-by-Section Review

### Title
**Grade: 8/10**
**What works:** "Policy-Differentiated Vulnerability Analysis" is precise and novel-sounding.
**What is missing:** The title says "poisoning" but the paper operates at the score level, not the traffic level. A reader seeing this title at a workshop might expect a deployed attack. Consider: "Score-Level Poisoning of the Threshold-Calibration Stage…" to immediately scope the work.
**Priority:** Minor. Submission-ready as-is.

***

### Abstract
**Grade: 6.5/10**
**What works:** Correctly states the three policy families, the N=10 seed basis, the pp degradation range, the 100% Gate-1 pass rate, and the ΔCVFPR for the lowering attack.
**What is unclear:** "score-level raising attack achieves 100% Gate-1 pass rate at all non-zero fractions" — readers who have not read §4.4 do not know what Gate-1 is. This sounds more impressive than it is (Gate-1 is a within-paper materiality threshold, not an independent benchmark).
**What is overclaimed:** "succeeds" for the lowering attack (see Risk F3).
**What is missing:** No mention of the N=10 seed limitation.
**Fix needed:** Replace "achieves 100% Gate-1 pass rate" with "produces material, correctly-signed threshold shifts (≥8/10 seeds) at all non-zero fractions." Replace "succeeds" with "produces bounded threshold displacement."
**Submission-ready:** No. Two sentences need revision.

***

### Introduction
**Grade: 7.0/10**
**What works:** The "An undefended phase" framing is compelling. The three-axis distinction from standard data poisoning (temporal isolation, phase-specific trust model, policy-dependent effects) is the best conceptual contribution in the paper and is well-written.
**What is unclear:** The phrase "calibration-stage poisoning is structurally distinct" is asserted but the three axes in the following paragraph are compressed. Each axis is one clause. A skeptical reviewer will not find this convincing.
**What a reviewer may ask:** "The temporal isolation argument is not exclusive to your attack—any post-training manipulation would have the same property. What makes calibration specifically vulnerable vs. any other post-training operation?"
**Fix needed:** Expand the three-axis argument by ½ page. Add: for the temporal-isolation axis, note that unlike post-deployment adversarial inputs (test-time attacks), calibration-stage manipulation changes the *operating point* of the detector permanently until recalibration occurs. This is not evasion—it is persistent threshold displacement.
**Priority:** Major.
**Submission-ready:** Marginally, but would benefit from revision.

***

### Contributions
**Grade: 7.5/10**
**What works:** Three contributions are clearly stated and correspond to actual experiments.
**What is overclaimed:** Contribution 1 says "we isolate the post-training threshold-calibration stage as an undefended attack surface." This is a characterization contribution, not a proof—the paper does not show that no defense can address it, only that none of the named defenses monitors the calibration buffer.
**Fix needed:** Change to "we identify and characterize" rather than "we isolate." Add "(§6 discusses defense requirements)" after the first contribution.
**Priority:** Minor.

***

### Background and Related Work (§2)
**Grade: 6.0/10**
**What works:** Correctly describes N-BaIoT, FedAvg, autoencoder-based detection, and the three policy families.
**What is missing:** No comparison with Kloft & Laskov  to explain why it does not constitute prior work on this surface. No comparison with online learning threshold manipulation literature more broadly. The phrase "to our knowledge, no prior work" is unsupported beyond listing what existing work *does* study.
**What a reviewer may ask:** "Kloft & Laskov  study adversarial manipulation of anomaly detection thresholds. What distinguishes your attack from theirs in the FL context?"
**Fix needed:** Add a paragraph explicitly contrasting  with this paper (centralized vs. federated, score replacement vs. online update injection, no per-client policy differentiation in ).
**Priority:** Major.
**Submission-ready:** No.

***

### Threat Model (§3)
**Grade: 7.0/10**
**What works:** Gray-box score-level access is precisely defined. The distinction between poisoned client and victim is clear. The Replace-Fixed-Budget mechanism is named.
**What is missing:** The threat model never explicitly states in one axiom-level sentence: "Training data, model weights, aggregation, test scores, and test labels remain clean and unchanged throughout." This is scattered across §3 and §4.1 but is not a first-principle assertion in the threat model section.
**What a reviewer may ask:** "Does the adversary have access to the test set? How do you ensure no leakage between the calibration buffer and the test set?"
**Fix needed:** Add as the first paragraph of §3: "Non-negotiable isolation axioms: the adversary never modifies (i) training data, (ii) local model updates or global model weights, (iii) the aggregation process, (iv) test scores, or (v) test labels. These are verified as bitwise-identical across all 4,320 experimental cells (§4.5)."
**Priority:** Major.
**Submission-ready:** No, one paragraph missing.

***

### Experimental Protocol (§4)
**Grade: 7.5/10**
**What works:** The 4,320-cell experimental design is explicit and complete. Seed pairing (training seed i, poisoning seed i+100, analysis seed i+300) is principled and well-described. Eligibility threshold (≥100 samples) is stated.
**What is missing:** The autoencoder architecture is never described (layer sizes, activation functions, loss function, optimizer, learning rate, number of rounds, local epochs). A reader cannot reproduce the "per-client autoencoder on benign traffic using FedAvg" without this.
**What a reviewer may ask:** "What is the autoencoder architecture? What is the FedAvg local epoch count? What convergence criterion was used?"
**Fix needed:** Add a one-paragraph or one-table model configuration description (can be compact: input dim, hidden layers, bottleneck, activation, loss = MSE, optimizer = Adam, lr = 1e-3, local epochs = 1, rounds = R).
**Priority:** Major for reproducibility, moderate for acceptance.
**Submission-ready:** Not for reproducibility.

***

### Statistical Analysis (§4.4)
**Grade: 7.0/10**
**What works:** Three-gate hierarchy is well-specified. Materiality threshold formula is precisely stated. AUROC invariance as protocol check is correctly positioned.
**What is missing:** The paper does not acknowledge that a 95% percentile bootstrap CI from N=10 observations has unreliable nominal coverage. This is a known limitation in bootstrap theory.
**What a reviewer may ask:** "Why only 10 seeds? What is the statistical power of a 95% CI over 10 observations?"
**Fix needed:** Add one sentence: "With N=10 seeds, bootstrap CI coverage may deviate from the nominal 95% level; we flag this as a limitation in §6 and recommend ≥20 seeds in future work."
**Priority:** Major.

***

### Results (§5)
**Grade: 7.0/10**
**What works:** The raising-attack results are clean, well-supported, and directionally consistent. The ΔτPolicy-dependent magnitude analysis is the paper's most compelling empirical result.
**What is missing:** (1) No figure for ΔCV(FPR) despite it being the "operational harm metric" for the lowering attack. (2) The cluster membership is never reported—which devices are in which cluster?
**What is overclaimed:** The "−30–80 undetected Mirai flows per 1000 attack packets" (p.8) claim uses a traffic rate that is not cited.
**Fix needed:** Add a panel to Figure 3 or a separate Figure 4 for ΔCV(FPR) vs. f for the lowering attack. Add one sentence disclosing the traffic-rate assumption or remove the concrete flow count.
**Priority:** Major (Figure) / Moderate (flow count).

***

### Discussion and Limitations (§6)
**Grade: 7.5/10**
**What works:** Score-level proxy limitation is honestly stated. Duplicate score detectability is disclosed. Policy trade-off is clearly articulated.
**What is missing:** No discussion of what a *minimum viable defense* against calibration-stage poisoning would look like—even at an abstract level. The paper says "defense design is out of scope" but offers nothing even qualitative.
**What a reviewer may ask:** "You have identified the attack but offer no defense even conceptually. What would it take?"
**Fix needed:** Add ½ paragraph: "An effective calibration-stage defense would need to: (a) monitor the score distribution of submitted calibration buffers for tail concentration, (b) validate submitted local thresholds against server-side priors over clean calibration distributions, or (c) impose an integrity constraint such as score-uniqueness checking. Each of these requires the server to maintain or receive distributional metadata from clients—a requirement distinct from training-phase defenses."
**Priority:** Moderate.
**Submission-ready:** Close but missing the defense sketch.

***

### Conclusion (§7)
**Grade: 7.0/10**
**What works:** Correctly scopes all claims to N-BaIoT, FedAvg, autoencoders, q=0.95.
**What is missing:** The conclusion states the raising attack "degrades victim detection rates by 2.4–7.9 pp" but doesn't re-state which policies this spans. A reader skimming to the conclusion may think 7.9 pp is the Global result (it is Local).
**Fix needed:** Add "(Local: −7.9 pp, Global: −6.1 pp, Cluster: −4.9 pp at f=0.4)" after the range claim.
**Priority:** Minor.

***

### References
**Grade: 6.5/10**
**What works:** Standard FL security references are present (Krum, FLTrust, Trimmed-Mean, FedAvg, N-BaIoT).
**What is missing:** (1) No citation for the specific threshold-based anomaly detection sensitivity claim in §2 para 3 beyond , which is a general ML/big-data challenges paper. (2) Kloft & Laskov  is cited but not adequately contrasted. (3) No citation for the "coefficient of variation" as a dispersion metric for FPR equity.
**Priority:** Minor to Moderate.

***

## 7. Reviewer Questions the Paper Must Already Answer

### Threat Model Questions
- TM1: Does the adversary access test data at any point? *(Not stated axiomatically in §3)*
- TM2: Can the adversary see other clients' calibration scores? *(Stated as "no" in §3 but only implicitly)*
- TM3: Why is a single compromised client a realistic threat? *(Not motivated—what is the adversary's goal in a real IoT deployment?)*
- TM4: What is the adversary's motivation? Why raise the threshold rather than poison model weights? *(Not addressed—the paper is a vulnerability characterization, but motivation is not stated)*

### Novelty Questions
- N1: How does this differ from Kloft & Laskov ? *(Inadequately addressed—see §2)*
- N2: Is this just data poisoning applied to calibration data? *(The paper attempts to answer this in §1 but the argument is compressed)*
- N3: Does any existing defense actually cover the calibration buffer if extended? *(Not tested)*

### Methodology Questions
- M1: What is the autoencoder architecture? *(Absent from §4)*
- M2: Why are only 10 seeds used? *(Not justified)*
- M3: How are the Random-Benign and directional attack conditions paired at the seed level? *(Not clearly stated)*
- M4: What does "tail reservoir" mean exactly—top/bottom 10% of the clean calibration distribution? *(Stated in §4.1 but the boundary condition for duplicate generation at high f is buried in §6)*

### Statistical Validity Questions
- S1: What is the statistical power of a 95% bootstrap CI from N=10 samples? *(Not discussed)*
- S2: Why percentile bootstrap rather than BCa? *(Not justified)*
- S3: Are seed-level aggregates truly independent? If the same training result is reused across injection fractions, are the 10 framing seeds actually 10 independent observations? *(Partially addressed by the seed-pairing scheme)*

### Dataset Questions
- D1: Why only N-BaIoT? The paper acknowledges generalizability is not established—but a reviewer may require at least a second dataset or a strong argument for why N-BaIoT is sufficient.
- D2: Calibration set sizes range from 2,622 to 9,909. Does the attack scale with calibration set size? Is there a systematic relationship between n_cal and Δτ?

### Baseline Questions
- B1: Why not include a defense baseline (e.g., a trivial uniqueness check) to show the attack can evade it?
- B2: Why not include multi-client collusion as even a single exploratory result?

### Scope and Limitation Questions
- SC1: Does the attack work equally well across all nine devices, or is there device-specific variance? *(Table 2 reports means over 9 victims, masking this)*
- SC2: What happens at injection fractions below 0.1 (e.g., f=0.01)? Is there a minimum effective fraction?

### Visual/Formatting Questions
- V1: Figure 2 uses "seed 0" only. Why not show mean ± SD across seeds?
- V2: Where is the ΔCV(FPR) figure for the lowering attack?
- V3: Table 2 uses "pp" for percentage points—this is correct but should be footnoted.

***

## 8. Claim Discipline Audit

| Claim | Location | Support Level | Weakness | Safe Rewrite |
|---|---|---|---|---|
| "100% Gate-1 pass rate at all non-zero fractions" | Abstract, §5.2 | Fully supported | Gate-1 is a within-paper criterion; it sounds more impressive than it is | "Material, correctly-signed threshold shifts in ≥8/10 seeds at all non-zero fractions" |
| "Degrading victim true-positive rates by 2.4 to 7.9 pp" | Abstract | Fully supported | Range conflates policies; 2.4 pp is Global at f=0.1, 7.9 pp is Local at f=0.4 | "…2.4–7.9 pp across policies and injection fractions (Local: 7.9 pp, Global: 6.1 pp, Cluster: 4.9 pp at f=0.4)" |
| "Score-level lowering attack succeeds for Local and Cluster" | Abstract | Partially supported | The paper itself calls it "conditional" and a "lower bound" in §5.3 | "produces bounded threshold displacement and FPR disparity as a lower bound under Replace-Fixed-Budget" |
| "Structurally outside the scope of every defense that monitors the training or aggregation loop" | §2 | Fully supported | True by construction; no existing defense monitors the calibration buffer | Keep |
| "No prior work characterizes the vulnerability of the post-training threshold-calibration stage" | §2 | Partially supported | Kloft & Laskov  is not adequately contrasted | Add explicit contrast with  |
| "30–80 undetected Mirai flows per 1000 attack packets" | §5.2 | Unsupported | Traffic rate not cited or justified | Remove or cite a traffic rate source |
| "Global harm (−6.1 pp) is notable" | §5.2 | Fully supported | The word "notable" is subjective | Change to "statistically significant (95% CI excludes zero)" |
| "Proof that calibration buffer is an unmonitored input channel" | §6 | Fully supported | The paper correctly scopes this to tested settings | Keep |
| "AUROC is invariant by construction" | §3, §4.4 | Fully supported | Correct; test data is unchanged | Keep |
| "Local confines harm to the compromised client" | Abstract | Partially supported | Verified only for single-client compromise; multi-client not tested | Add "(under single-client compromise)" |

***

## 9. Methodology and Experiment Audit

| Issue | Location | Why It Matters | Reviewer Risk | Fix | Priority |
|---|---|---|---|---|---|
| N=10 seeds, bootstrap CI coverage | §4.4, all results | Bootstrap coverage unreliable at N=10 | High — methods reviewer will flag | Run ≥20 seeds; switch to BCa bootstrap; add power caveat | Fatal |
| AE architecture not described | §4.1 | Cannot reproduce; cannot assess whether architecture choice drives results | High | Add architecture table or paragraph | Major |
| Cluster membership not reported | §4.2 | "Intra-cluster spillover" is uninterpretable without knowing cluster composition | Moderate | Add a table or footnote listing which 3 devices are in each cluster (for representative seed) | Moderate |
| Duplicate scores at f=0.4 disclosed but not quantified | §6 | "Easily flagged" is asserted but the expected collision count is not in the main paper | Moderate | Move the collision count formula from §6 to §3 or §4.3 | Moderate |
| Traffic-rate assumption for Mirai flow count | §5.2 | Concrete harm claim rests on undisclosed assumption | High | Cite source or remove | Major |
| Lowering-attack ΔCV(FPR) not plotted | §5.3, §6 | Most important lowering-attack metric is table-only; visually underpowered | Moderate | Add Figure panel | Major |
| No device-level attack variance reported | §5.2 | Table 2 reports mean over 9 victims; some devices may show near-zero effects | Moderate | Add per-device breakout table in appendix or footnote high-variance devices | Moderate |
| No multi-client collusion | §3, §5 | Single-client scope is a limitation but no sensitivity analysis exists | High | Add ½-page exploratory result or strong scope statement in §3 | Major |
| f=0.05 not included | §4.3 | Minimum effective fraction is unknown | Low | Note as future work or add a brief note | Minor |
| Figure 2 uses seed 0 only | §5.1 | CV(FPR) claim is made over 10 seeds but illustrated with one | Low | Change to mean±SD bar chart | Minor |

***

## 10. Figures and Tables Audit

### Figure 1 — Attack Surface Diagram
**Grade: 8/10**
**What it communicates:** The structural position of the calibration stage between training and deployment; the three policy families; the adversary's entry point.
**What is confusing:** The box labeled "Calibration Buffer" appears to receive inputs from both the adversary's "tail scores" and the regular calibration pipeline. It is not clear that the adversary *replaces* entries in the buffer rather than *adding* new ones.
**Fix:** Add a brief label: "adversary replaces f·n entries" on the arrow from the adversary to the calibration buffer.
**Verdict:** Keep. Strong figure.

### Figure 2 — Per-client FPR, Clean Baseline, Seed 0
**Grade: 5.5/10**
**What it communicates:** That Global forces a single threshold ill-suited to heterogeneous devices; that Local adapts per-device.
**What is confusing:** "seed 0" is stated in the caption. The CV(FPR) values cited in the text (0.91 and 0.33) are averages over 10 seeds, but the figure shows only one seed's realization.
**Fix:** Either (a) replot as mean±SD over 10 seeds (preferred), or (b) add a caption note: "Seed 0 shown for illustration; CV(FPR) values in the text are averages over 10 seeds."
**Verdict:** Keep but revise.

### Figure 3 — Mean Δτ vs. Injection Fraction
**Grade: 7.5/10**
**What it communicates:** The raising attack dominates; the lowering attack is smaller in magnitude; Global is structurally diluted.
**What is confusing:** The y-axis ranges differ between panels (a) and (b), which is appropriate but should be noted in the caption. The Random-Benign control is stated to produce "CI spanning zero at all fractions" but is not plotted—this leaves the control claim unverifiable from the figure alone.
**Fix:** (a) Add "Note: y-axis scales differ between panels" to caption. (b) Add Random-Benign as a dashed line (near-zero) in each panel to make the control visible.
**Verdict:** Keep with minor fixes.

### Table 1 — Clean Baseline Dispersion Statistics
**Grade: 8/10**
**What it communicates:** Policy ordering on baseline CV(FPR), CV(TPR), Worst-BA, and P10 Macro-F1 under clean conditions.
**What is confusing:** The bolding convention says "bold marks the best value per metric," but for Worst-BA and P10 Macro-F1, the best value depends on whether higher or lower is better. This is not stated in the caption.
**Fix:** Add "(higher=better for Worst-BA and P10 Macro-F1; lower=better for CV metrics)" to the caption.
**Verdict:** Keep.

### Table 2 — Threshold Shift and Detection Harm
**Grade: 7.5/10**
**What it communicates:** This is the paper's primary results table and is dense but well-organized.
**What is confusing:** The "†" footnote for lowering rows says "are a lower bound; see §5 for ΔCV(FPR) harm metric," but ΔCV(FPR) never appears in this table. A reader wants to see ΔCV(FPR) alongside ΔτR and ΔTPR in this table.
**Fix:** Add a ΔCV(FPR) column to the lowering-attack rows (with values +0.053, +0.060, −0.019 at f=0.4 for Local, Cluster, Global respectively).
**Verdict:** Keep but add column.

***

## 11. Visual and Formatting Review

1. **Page layout:** Clean two-column format, standard LNCS/Springer style. No obvious layout issues.
2. **Font sizes:** Figures are readable but Figure 2's device labels on the x-axis are rotated at a steep angle and may be unreadable in print at reduced scale.
3. **Abbreviations:** "pp" (percentage points) is used in Table 2 without a first-use definition. Define at first use in §5.
4. **CV(FPR) definition:** Used throughout but first formally defined only in Table 1's caption (ddof=0). Should be defined in §4.4 or §4.2 where first mentioned.
5. **Section headings:** §5.4 is titled "Policy-Differentiation Summary" — this section's content is strong but it reads as a conclusion within results rather than a summary. Consider renaming to "Policy Vulnerability Profiles."
6. **Algorithm formatting:** No algorithm box is present. The Replace-Fixed-Budget mechanism is described in prose but a 5-line pseudocode algorithm in §4.3 would greatly improve clarity.
7. **Equation formatting:** The materiality threshold formula in §4.4 is presented in text rather than as a displayed equation, making it hard to parse. Should be a \[ \] block.
8. **Spacing:** §5.2 last paragraph ("To contextualize: a victim with clean TPR = 1.0") hangs as a partial paragraph before the section break.

***

## 12. Related Work and Novelty Review

### Top Missing or Weakly Handled Related Work Risks

| Risk | Description | Mitigation |
|---|---|---|
| Kloft & Laskov  | Directly studies adversarial threshold manipulation in anomaly detection. The paper cites but does not contrast. | Add explicit contrast paragraph |
| Barreno et al.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_2068727c-5b13-4337-9ec8-46f9c623d7fe/e2de8bcb-8020-47ee-a7b1-6384b512a5ba/DATP_CP_Roadmap.md?AWSAccessKeyId=ASIA2F3EMEYEZMS7BDDP&Signature=kmygKD1xNG1j7FoU0JitMp1vyrs%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEO3%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJIMEYCIQDb546e084jn4Xs7TQxCwmH4rod3%2BF9i803d4pbsV%2FO0wIhAKYuTVk%2BN21LVAHNCuGKcYt0ta4G2ZcfG8o8gqb%2BiTIKKvwECLb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQARoMNjk5NzUzMzA5NzA1Igyx18GwfyxQBCTQ8Zkq0AS3%2BdtcoPP4KDSgRkfCgreGS5HZT8QUTPMh6k9ALK7Y9nQwT7poUGLsKi%2FneYhXOTe%2FW1KaiwkfIMkymbM82cMjf55Z4eMdzzgUeqNEThOLfWvkaKYtyGJ%2F2upRrwGi4yOeQqM4k5oZAIf5yVc2p2HBhsZ7HG31EHyWdCp0B7zsYf2RgfBgJknSoGEaslOGu6gis5eSpeFF88FC5Jbrs91xG7f8o4IescTfSeHoV%2F72d8uIJY6hRhvXEPb4mAEG%2BOVGPj41%2FjFoM3yBm%2B9b2UQkV5dXNiIy5cw%2BYkyL8GL%2FLuwWqjKRBBzzBhUyNRj0L7rgDziMIXHKAPxZFYkVWNBRl8A3QUP4L00oA38TAhYt%2FZoNVjFmEVTyMIwUR0I2tQJv8UWiwHwpOfSKli9A5MpwqggeL2Pzv9KfmbhA5vVvFqHUJ89dpMrSdeUS%2FJp8x3nC%2BoSi7MShVXBHqc6k29kfiVnIu1skzk5TiSZ%2BGfzmXxuIJHVrOl80dqLWVMuPgMt%2Bhi0AHliZgtHlxN%2FrLVYdKYSI52GDrDXhMu%2BKyNRk3E8O40s2DBO%2FQBu%2FMhRfSqCL12kaSzCo0jrqJXXGAXzpyiq4ewI8t2GRkIeBjGofBO%2BQ2V%2FHafFK3j1UqMNfQWeHL%2F%2Fg4p%2Ft009DbbJZkJ8iQxtbxT9SvUhbBHMOVbA3iqhcKuvBPtMUTiaGb80CsuoXlpW%2FD40DR%2F1%2B23ohIUELMHhdgo69qucyzZtvW7%2F4Qb9h%2FqZsa6sRuhbExzSKGYQxZZ0dOLa6OvhAKcSJEMJSMN6vi9IGOpcBrXzhElVyl0Xq1hmhDutk7qeMuKBsP%2B5ltiUbAJHdjsLQoQ6OM70RWNCLtJAighGRTMzO64UuJ7gg0Qi%2FTAlV7CpTxiLwizRf6WxxYzU1KDVWcKPNRO1SkCHJy8ZMFwVVXW9FJmx0cg1HZyUeTjObJGva8EafMbf7cXLity96FMDKhLWQRt0jUJQmZwz1ETNqOc3u8Bf7ig%3D%3D&Expires=1782769073) | Studies data poisoning in centralized ML. Cited but the "centralized vs. federated" distinction for calibration data is not made explicit. | One sentence in §2 |
| Conformal prediction / threshold calibration literature | Split conformal prediction (e.g., Angelopoulos & Bates) studies threshold-setting under distributional shift. No mention. | Could be a "related non-adversarial work" note; not required |
| FL inference/privacy attacks  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_2068727c-5b13-4337-9ec8-46f9c623d7fe/7b9ed578-7f10-4b17-ad83-4e9b027789cb/Claims.md?AWSAccessKeyId=ASIA2F3EMEYEZMS7BDDP&Signature=yMjh97%2FACQgup8IIF8AIt08NdYs%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEO3%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJIMEYCIQDb546e084jn4Xs7TQxCwmH4rod3%2BF9i803d4pbsV%2FO0wIhAKYuTVk%2BN21LVAHNCuGKcYt0ta4G2ZcfG8o8gqb%2BiTIKKvwECLb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQARoMNjk5NzUzMzA5NzA1Igyx18GwfyxQBCTQ8Zkq0AS3%2BdtcoPP4KDSgRkfCgreGS5HZT8QUTPMh6k9ALK7Y9nQwT7poUGLsKi%2FneYhXOTe%2FW1KaiwkfIMkymbM82cMjf55Z4eMdzzgUeqNEThOLfWvkaKYtyGJ%2F2upRrwGi4yOeQqM4k5oZAIf5yVc2p2HBhsZ7HG31EHyWdCp0B7zsYf2RgfBgJknSoGEaslOGu6gis5eSpeFF88FC5Jbrs91xG7f8o4IescTfSeHoV%2F72d8uIJY6hRhvXEPb4mAEG%2BOVGPj41%2FjFoM3yBm%2B9b2UQkV5dXNiIy5cw%2BYkyL8GL%2FLuwWqjKRBBzzBhUyNRj0L7rgDziMIXHKAPxZFYkVWNBRl8A3QUP4L00oA38TAhYt%2FZoNVjFmEVTyMIwUR0I2tQJv8UWiwHwpOfSKli9A5MpwqggeL2Pzv9KfmbhA5vVvFqHUJ89dpMrSdeUS%2FJp8x3nC%2BoSi7MShVXBHqc6k29kfiVnIu1skzk5TiSZ%2BGfzmXxuIJHVrOl80dqLWVMuPgMt%2Bhi0AHliZgtHlxN%2FrLVYdKYSI52GDrDXhMu%2BKyNRk3E8O40s2DBO%2FQBu%2FMhRfSqCL12kaSzCo0jrqJXXGAXzpyiq4ewI8t2GRkIeBjGofBO%2BQ2V%2FHafFK3j1UqMNfQWeHL%2F%2Fg4p%2Ft009DbbJZkJ8iQxtbxT9SvUhbBHMOVbA3iqhcKuvBPtMUTiaGb80CsuoXlpW%2FD40DR%2F1%2B23ohIUELMHhdgo69qucyzZtvW7%2F4Qb9h%2FqZsa6sRuhbExzSKGYQxZZ0dOLa6OvhAKcSJEMJSMN6vi9IGOpcBrXzhElVyl0Xq1hmhDutk7qeMuKBsP%2B5ltiUbAJHdjsLQoQ6OM70RWNCLtJAighGRTMzO64UuJ7gg0Qi%2FTAlV7CpTxiLwizRf6WxxYzU1KDVWcKPNRO1SkCHJy8ZMFwVVXW9FJmx0cg1HZyUeTjObJGva8EafMbf7cXLity96FMDKhLWQRt0jUJQmZwz1ETNqOc3u8Bf7ig%3D%3D&Expires=1782769073) | Gradient inversion is cited but not contrasted with calibration-stage access (which requires *less* capability than gradient access). | Half sentence in §3 |
| Online learning poisoning (beyond ) | Biggio et al.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_2068727c-5b13-4337-9ec8-46f9c623d7fe/688901cd-ec3c-4854-889e-407d4ff40c59/DATP.pdf?AWSAccessKeyId=ASIA2F3EMEYEZMS7BDDP&Signature=9OkobuJ0OuQGXplmGslLh2yohsQ%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEO3%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJIMEYCIQDb546e084jn4Xs7TQxCwmH4rod3%2BF9i803d4pbsV%2FO0wIhAKYuTVk%2BN21LVAHNCuGKcYt0ta4G2ZcfG8o8gqb%2BiTIKKvwECLb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQARoMNjk5NzUzMzA5NzA1Igyx18GwfyxQBCTQ8Zkq0AS3%2BdtcoPP4KDSgRkfCgreGS5HZT8QUTPMh6k9ALK7Y9nQwT7poUGLsKi%2FneYhXOTe%2FW1KaiwkfIMkymbM82cMjf55Z4eMdzzgUeqNEThOLfWvkaKYtyGJ%2F2upRrwGi4yOeQqM4k5oZAIf5yVc2p2HBhsZ7HG31EHyWdCp0B7zsYf2RgfBgJknSoGEaslOGu6gis5eSpeFF88FC5Jbrs91xG7f8o4IescTfSeHoV%2F72d8uIJY6hRhvXEPb4mAEG%2BOVGPj41%2FjFoM3yBm%2B9b2UQkV5dXNiIy5cw%2BYkyL8GL%2FLuwWqjKRBBzzBhUyNRj0L7rgDziMIXHKAPxZFYkVWNBRl8A3QUP4L00oA38TAhYt%2FZoNVjFmEVTyMIwUR0I2tQJv8UWiwHwpOfSKli9A5MpwqggeL2Pzv9KfmbhA5vVvFqHUJ89dpMrSdeUS%2FJp8x3nC%2BoSi7MShVXBHqc6k29kfiVnIu1skzk5TiSZ%2BGfzmXxuIJHVrOl80dqLWVMuPgMt%2Bhi0AHliZgtHlxN%2FrLVYdKYSI52GDrDXhMu%2BKyNRk3E8O40s2DBO%2FQBu%2FMhRfSqCL12kaSzCo0jrqJXXGAXzpyiq4ewI8t2GRkIeBjGofBO%2BQ2V%2FHafFK3j1UqMNfQWeHL%2F%2Fg4p%2Ft009DbbJZkJ8iQxtbxT9SvUhbBHMOVbA3iqhcKuvBPtMUTiaGb80CsuoXlpW%2FD40DR%2F1%2B23ohIUELMHhdgo69qucyzZtvW7%2F4Qb9h%2FqZsa6sRuhbExzSKGYQxZZ0dOLa6OvhAKcSJEMJSMN6vi9IGOpcBrXzhElVyl0Xq1hmhDutk7qeMuKBsP%2B5ltiUbAJHdjsLQoQ6OM70RWNCLtJAighGRTMzO64UuJ7gg0Qi%2FTAlV7CpTxiLwizRf6WxxYzU1KDVWcKPNRO1SkCHJy8ZMFwVVXW9FJmx0cg1HZyUeTjObJGva8EafMbf7cXLity96FMDKhLWQRt0jUJQmZwz1ETNqOc3u8Bf7ig%3D%3D&Expires=1782769073) study poisoning in SVMs, not threshold-based detectors. The contrast to threshold-based detection should be explicit. | Brief note |

### Closest Prior Work Comparison Table (paper should include or expand)

| Prior Work | Setting | Attack Surface | Policy Differentiation | Score-Level Only |
|---|---|---|---|---|
| Kloft & Laskov  | Centralized, online | Threshold via score poisoning | No | Yes |
| Biggio et al.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_2068727c-5b13-4337-9ec8-46f9c623d7fe/688901cd-ec3c-4854-889e-407d4ff40c59/DATP.pdf?AWSAccessKeyId=ASIA2F3EMEYEZMS7BDDP&Signature=9OkobuJ0OuQGXplmGslLh2yohsQ%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEO3%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJIMEYCIQDb546e084jn4Xs7TQxCwmH4rod3%2BF9i803d4pbsV%2FO0wIhAKYuTVk%2BN21LVAHNCuGKcYt0ta4G2ZcfG8o8gqb%2BiTIKKvwECLb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQARoMNjk5NzUzMzA5NzA1Igyx18GwfyxQBCTQ8Zkq0AS3%2BdtcoPP4KDSgRkfCgreGS5HZT8QUTPMh6k9ALK7Y9nQwT7poUGLsKi%2FneYhXOTe%2FW1KaiwkfIMkymbM82cMjf55Z4eMdzzgUeqNEThOLfWvkaKYtyGJ%2F2upRrwGi4yOeQqM4k5oZAIf5yVc2p2HBhsZ7HG31EHyWdCp0B7zsYf2RgfBgJknSoGEaslOGu6gis5eSpeFF88FC5Jbrs91xG7f8o4IescTfSeHoV%2F72d8uIJY6hRhvXEPb4mAEG%2BOVGPj41%2FjFoM3yBm%2B9b2UQkV5dXNiIy5cw%2BYkyL8GL%2FLuwWqjKRBBzzBhUyNRj0L7rgDziMIXHKAPxZFYkVWNBRl8A3QUP4L00oA38TAhYt%2FZoNVjFmEVTyMIwUR0I2tQJv8UWiwHwpOfSKli9A5MpwqggeL2Pzv9KfmbhA5vVvFqHUJ89dpMrSdeUS%2FJp8x3nC%2BoSi7MShVXBHqc6k29kfiVnIu1skzk5TiSZ%2BGfzmXxuIJHVrOl80dqLWVMuPgMt%2Bhi0AHliZgtHlxN%2FrLVYdKYSI52GDrDXhMu%2BKyNRk3E8O40s2DBO%2FQBu%2FMhRfSqCL12kaSzCo0jrqJXXGAXzpyiq4ewI8t2GRkIeBjGofBO%2BQ2V%2FHafFK3j1UqMNfQWeHL%2F%2Fg4p%2Ft009DbbJZkJ8iQxtbxT9SvUhbBHMOVbA3iqhcKuvBPtMUTiaGb80CsuoXlpW%2FD40DR%2F1%2B23ohIUELMHhdgo69qucyzZtvW7%2F4Qb9h%2FqZsa6sRuhbExzSKGYQxZZ0dOLa6OvhAKcSJEMJSMN6vi9IGOpcBrXzhElVyl0Xq1hmhDutk7qeMuKBsP%2B5ltiUbAJHdjsLQoQ6OM70RWNCLtJAighGRTMzO64UuJ7gg0Qi%2FTAlV7CpTxiLwizRf6WxxYzU1KDVWcKPNRO1SkCHJy8ZMFwVVXW9FJmx0cg1HZyUeTjObJGva8EafMbf7cXLity96FMDKhLWQRt0jUJQmZwz1ETNqOc3u8Bf7ig%3D%3D&Expires=1782769073) | Centralized, SVM | Training data | No | No |
| Barreno et al.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/collection_2068727c-5b13-4337-9ec8-46f9c623d7fe/e2de8bcb-8020-47ee-a7b1-6384b512a5ba/DATP_CP_Roadmap.md?AWSAccessKeyId=ASIA2F3EMEYEZMS7BDDP&Signature=kmygKD1xNG1j7FoU0JitMp1vyrs%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEO3%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJIMEYCIQDb546e084jn4Xs7TQxCwmH4rod3%2BF9i803d4pbsV%2FO0wIhAKYuTVk%2BN21LVAHNCuGKcYt0ta4G2ZcfG8o8gqb%2BiTIKKvwECLb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQARoMNjk5NzUzMzA5NzA1Igyx18GwfyxQBCTQ8Zkq0AS3%2BdtcoPP4KDSgRkfCgreGS5HZT8QUTPMh6k9ALK7Y9nQwT7poUGLsKi%2FneYhXOTe%2FW1KaiwkfIMkymbM82cMjf55Z4eMdzzgUeqNEThOLfWvkaKYtyGJ%2F2upRrwGi4yOeQqM4k5oZAIf5yVc2p2HBhsZ7HG31EHyWdCp0B7zsYf2RgfBgJknSoGEaslOGu6gis5eSpeFF88FC5Jbrs91xG7f8o4IescTfSeHoV%2F72d8uIJY6hRhvXEPb4mAEG%2BOVGPj41%2FjFoM3yBm%2B9b2UQkV5dXNiIy5cw%2BYkyL8GL%2FLuwWqjKRBBzzBhUyNRj0L7rgDziMIXHKAPxZFYkVWNBRl8A3QUP4L00oA38TAhYt%2FZoNVjFmEVTyMIwUR0I2tQJv8UWiwHwpOfSKli9A5MpwqggeL2Pzv9KfmbhA5vVvFqHUJ89dpMrSdeUS%2FJp8x3nC%2BoSi7MShVXBHqc6k29kfiVnIu1skzk5TiSZ%2BGfzmXxuIJHVrOl80dqLWVMuPgMt%2Bhi0AHliZgtHlxN%2FrLVYdKYSI52GDrDXhMu%2BKyNRk3E8O40s2DBO%2FQBu%2FMhRfSqCL12kaSzCo0jrqJXXGAXzpyiq4ewI8t2GRkIeBjGofBO%2BQ2V%2FHafFK3j1UqMNfQWeHL%2F%2Fg4p%2Ft009DbbJZkJ8iQxtbxT9SvUhbBHMOVbA3iqhcKuvBPtMUTiaGb80CsuoXlpW%2FD40DR%2F1%2B23ohIUELMHhdgo69qucyzZtvW7%2F4Qb9h%2FqZsa6sRuhbExzSKGYQxZZ0dOLa6OvhAKcSJEMJSMN6vi9IGOpcBrXzhElVyl0Xq1hmhDutk7qeMuKBsP%2B5ltiUbAJHdjsLQoQ6OM70RWNCLtJAighGRTMzO64UuJ7gg0Qi%2FTAlV7CpTxiLwizRf6WxxYzU1KDVWcKPNRO1SkCHJy8ZMFwVVXW9FJmx0cg1HZyUeTjObJGva8EafMbf7cXLity96FMDKhLWQRt0jUJQmZwz1ETNqOc3u8Bf7ig%3D%3D&Expires=1782769073) | Centralized | Training data | No | No |
| Bagdasaryan et al.  [ppl-ai-file-upload.s3.amazonaws](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/54884680/9a3ccad2-b04f-4a58-a533-5387c1702fe3/datp-cp.pdf?AWSAccessKeyId=ASIA2F3EMEYEZMS7BDDP&Signature=77DjnOzMI6Y%2F8DRcpUFLlIO%2Bxos%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEO3%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJIMEYCIQDb546e084jn4Xs7TQxCwmH4rod3%2BF9i803d4pbsV%2FO0wIhAKYuTVk%2BN21LVAHNCuGKcYt0ta4G2ZcfG8o8gqb%2BiTIKKvwECLb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEQARoMNjk5NzUzMzA5NzA1Igyx18GwfyxQBCTQ8Zkq0AS3%2BdtcoPP4KDSgRkfCgreGS5HZT8QUTPMh6k9ALK7Y9nQwT7poUGLsKi%2FneYhXOTe%2FW1KaiwkfIMkymbM82cMjf55Z4eMdzzgUeqNEThOLfWvkaKYtyGJ%2F2upRrwGi4yOeQqM4k5oZAIf5yVc2p2HBhsZ7HG31EHyWdCp0B7zsYf2RgfBgJknSoGEaslOGu6gis5eSpeFF88FC5Jbrs91xG7f8o4IescTfSeHoV%2F72d8uIJY6hRhvXEPb4mAEG%2BOVGPj41%2FjFoM3yBm%2B9b2UQkV5dXNiIy5cw%2BYkyL8GL%2FLuwWqjKRBBzzBhUyNRj0L7rgDziMIXHKAPxZFYkVWNBRl8A3QUP4L00oA38TAhYt%2FZoNVjFmEVTyMIwUR0I2tQJv8UWiwHwpOfSKli9A5MpwqggeL2Pzv9KfmbhA5vVvFqHUJ89dpMrSdeUS%2FJp8x3nC%2BoSi7MShVXBHqc6k29kfiVnIu1skzk5TiSZ%2BGfzmXxuIJHVrOl80dqLWVMuPgMt%2Bhi0AHliZgtHlxN%2FrLVYdKYSI52GDrDXhMu%2BKyNRk3E8O40s2DBO%2FQBu%2FMhRfSqCL12kaSzCo0jrqJXXGAXzpyiq4ewI8t2GRkIeBjGofBO%2BQ2V%2FHafFK3j1UqMNfQWeHL%2F%2Fg4p%2Ft009DbbJZkJ8iQxtbxT9SvUhbBHMOVbA3iqhcKuvBPtMUTiaGb80CsuoXlpW%2FD40DR%2F1%2B23ohIUELMHhdgo69qucyzZtvW7%2F4Qb9h%2FqZsa6sRuhbExzSKGYQxZZ0dOLa6OvhAKcSJEMJSMN6vi9IGOpcBrXzhElVyl0Xq1hmhDutk7qeMuKBsP%2B5ltiUbAJHdjsLQoQ6OM70RWNCLtJAighGRTMzO64UuJ7gg0Qi%2FTAlV7CpTxiLwizRf6WxxYzU1KDVWcKPNRO1SkCHJy8ZMFwVVXW9FJmx0cg1HZyUeTjObJGva8EafMbf7cXLity96FMDKhLWQRt0jUJQmZwz1ETNqOc3u8Bf7ig%3D%3D&Expires=1782769073) | FL | Model weights (backdoor) | No | No |
| **This paper** | **FL, post-training** | **Calibration buffer** | **Yes** | **Yes** |

**Novelty Score: 7.5/10.** The calibration-stage isolation is real and novel. The policy differentiation is the strongest novelty axis. The main vulnerability of novelty-positioning is the insufficient contrast with .

**Safe Novelty Statement:** "To our knowledge, this is the first work to (a) isolate the post-training threshold-calibration stage as a structurally distinct attack surface in federated anomaly detection, (b) characterize it under a controlled score-level contamination model, and (c) analyze the policy-dependent vulnerability profile across Global, Local, and Cluster threshold families. Prior work on adversarial threshold manipulation  addresses centralized, online settings without the post-training calibration-phase structure or federation-wide policy propagation studied here."

***

## 13. Reproducibility Checklist

| Item | Status | Action Needed |
|---|---|---|
| Dataset: N-BaIoT with citation  | ✅ Present | None |
| Federation: 9 physical device clients | ✅ Present | None |
| Calibration set sizes per device | ✅ Present | None |
| Threshold quantile q=0.95 | ✅ Present | None |
| Injection fractions {0, 0.1, 0.2, 0.4} | ✅ Present | None |
| Seed scheme (training i, poisoning i+100, analysis i+300) | ✅ Present | None |
| Injection rule: Replace-Fixed-Budget | ✅ Present | None |
| Reservoir: top/bottom 10% tail | ✅ Present | None |
| Bootstrap: 95% percentile, B=10,000 | ✅ Present | None |
| Cluster policy: K=3, k-means++, random_state=42 | ✅ Present | None |
| **AE architecture (layers, bottleneck, activation)** | ❌ Absent | Add model config table |
| **FedAvg hyperparameters (local epochs, rounds, lr)** | ❌ Absent | Add to §4.1 |
| **Convergence criterion** | ❌ Absent | Add to §4.1 |
| **Loss function** | ❌ Absent | Add to §4.1 |
| **Hardware/software environment** | ❌ Absent | Add footnote or §4 note |
| **Code/artifact availability** | ❌ Absent | Add GitHub/Zenodo link or note |
| Materiality threshold formula | ✅ Present (§4.4) | Should be displayed equation |
| AUROC invariance check | ✅ Present (§4.5) | None |
| Isolation sanity checks | ✅ Present (§4.5) | None |

**Reproducibility Grade: 5.5/10.** The calibration-attack protocol is reproducible. The model training protocol is not.

**Minimum artifact checklist before submission:**
1. AE architecture specification (can be a single table)
2. FedAvg hyperparameter table (local epochs, rounds, learning rate, loss)
3. Code availability statement (even "code available upon request" is better than silence)
4. Per-device clean calibration set statistics (already partially present as a range; a table would be better)

***

## 14. Action Plan to Reach 10/10

### Must Fix Before Submission

1. **Add AE architecture and FedAvg training config** (§4.1 or a new §4.1.1 table). Without this, the paper fails reproducibility review at any serious venue.

2. **Upgrade the statistical basis.** Run ≥20 seeds (only calibration re-runs, no retraining). Switch to BCa bootstrap. Add one sentence in §4.4 acknowledging undercoverage risk at N=10.

3. **Add the ΔCV(FPR) column to Table 2** for lowering-attack rows. The most important lowering-attack metric is absent from the primary results table.

4. **Add or draw the Random-Benign control in Figure 3.** Even as a flat near-zero line, this makes the control visible and more convincing.

5. **Fix the lowering-attack overclaim in the Abstract.** Replace "succeeds" with "produces bounded threshold displacement and significant FPR disparity (as a lower bound)."

6. **Add the Kloft & Laskov contrast paragraph in §2.** One paragraph, ∼80 words.

7. **Remove or cite the "30–80 undetected Mirai flows" claim.** Cite a traffic rate source or replace with a percentage-based translation.

8. **Add isolation axioms as the first paragraph of §3.** Three sentences, verbatim or close to: "The adversary never modifies: (i) training data, (ii) model weights or gradients, (iii) aggregation, (iv) test scores, (v) test labels. These invariants are verified in §4.5."

### Should Fix If Page Budget Allows

9. **Add a 5-line pseudocode for Replace-Fixed-Budget** in §4.3. This dramatically improves clarity.

10. **Report cluster membership** (which devices fall in which cluster for representative seeds). Footnote or small table in §4.2.

11. **Expand the defense sketch in §6** to ½ paragraph listing three candidate defense properties.

12. **Fix Figure 2** to show mean±SD over 10 seeds instead of seed 0 only.

13. **Add ΔCV(FPR) panel to Figure 3** (lowering attack).

14. **Display the materiality threshold formula as an equation** (§4.4).

15. **Add per-device attack result variance** as supplementary table or footnote in §5.2.

### Nice to Fix

16. Add a brief note on why f=0.05 was not tested (out of pre-registered scope, or compute).

17. Rename §5.4 to "Policy Vulnerability Profiles" for clarity.

18. Fix Figure 2 x-axis label rotation for print readability.

19. Define "pp" (percentage points) and CV(FPR) on first use.

### Do Not Touch — Already Strong

- The three-gate evaluation framework (§4.4): do not weaken or change.
- The AUROC invariance framing as a protocol check, not a contribution: keep exactly as-is.
- The isolation sanity check (§4.5): keep and consider giving it slightly more prominence.
- The 4,320-cell factorial design description: precise and complete.
- The seed-pairing scheme (training i, poisoning i+100, analysis i+300): principled; do not change.
- The scope limitation disclosure (§6 first paragraph): honest and precise.
- The policy-differentiation summary (§5.4): well-organized, keep structure.

***

## 15. Final Reviewer Simulation

***

### Reviewer 1 — Supportive Expert in FL Security
**Score: 7/10 (Accept with revisions)**

*"This paper makes a clean and defensible contribution: isolating the threshold-calibration stage as a post-training attack surface and demonstrating that three different policy families have qualitatively different vulnerability profiles. The three-gate evaluation design is better than average for this venue. The isolation sanity checks (bitwise-identical weights, AUROC invariance) are rigorous. My main concerns are (1) the N=10 seed basis, which is too thin for a 95% CI claim, and (2) the absence of the AE architecture and training configuration, which makes the paper non-reproducible. The lowering attack results are also weaker than their billing in the abstract suggests. These are fixable. I recommend accept conditional on adding the model config, expanding the seed count, and revising the abstract's lowering-attack language."*

**Main objection answered in paper?** N=10 seeds: not adequately addressed. AE architecture: not present. Lower-attack overclaim: partially, but inconsistently.

***

### Reviewer 2 — Skeptical Methods Reviewer
**Score: 4/10 (Weak Reject)**

*"The experimental substrate is extremely thin. Nine devices, 10 seeds—this is a case study, not a generalizable vulnerability characterization. The 95% bootstrap CI from 10 observations is not a reliable 95% CI, and the authors do not acknowledge this. The 4,320-cell count sounds large, but the cells are not independent—they share model weights across all calibration conditions. The lowering attack is labeled 'secondary, conditional' in the threat model but is presented as a co-equal attack in the results. The 'no prior work' claim about calibration-stage poisoning is not supported by a systematic literature review—just by listing what other papers study. I would reject and encourage resubmission with ≥20 seeds, BCa bootstrap, and a proper related work contrast."*

**What would neutralize this objection?** 20+ seeds, BCa bootstrap, explicit power acknowledgment, Kloft & Laskov contrast.

***

### Reviewer 3 — Security/Adversarial ML Reviewer
**Score: 6/10 (Borderline)**

*"The attack surface identification is novel and the policy differentiation story is the best part of this paper. But I have two concerns. First, the attack operates at the score level—the authors cannot claim this is a real attack without showing traffic-level realizability, which they explicitly defer to future work. This is acceptable for a vulnerability characterization paper, but the abstract's phrasing 'achieves 100% Gate-1 pass rate' makes it sound like a deployed attack capability. Second, the threat model assumes a single compromised client. In federated learning, the realistic concern is a small fraction of compromised clients acting collusively. Even a two-client collusion result would make this paper significantly stronger. The 'no defense' aspect is also unsatisfying—even a naive defense baseline (uniqueness check) would help establish the lower bound of attacker-defender dynamics."*

**What would neutralize this objection?** Clarify abstract language; add one exploratory 2-client collusion result; add a naive defense (uniqueness check) baseline.

***

### Reviewer 4 — Presentation/Clarity Reviewer
**Score: 6/10 (Borderline)**

*"The paper is technically readable but has several presentation problems. Figure 2 illustrates a claim about 10-seed averages using only seed 0—this is misleading. Table 2 describes ΔCV(FPR) as the 'operational harm metric' for the lowering attack but then omits it from the table. The Random-Benign control is stated to produce CIs spanning zero but is not plotted—readers cannot verify this visually. The AE architecture and FedAvg configuration are absent from the paper, which is a critical reproducibility gap. The materiality threshold formula in §4.4 is presented in inline prose and is difficult to parse. These are fixable presentation issues, but together they create an impression of underpolished experimental reporting."*

**What would neutralize this objection?** Add ΔCV(FPR) to Table 2; fix Figure 2 to show mean±SD; plot Random-Benign in Figure 3; display the materiality formula as an equation.

***

## Final Verdict

**The paper is not currently submission-ready for a top-tier venue but is close.** The scientific contribution is genuine, the claim discipline is above average for FL security papers, and the three-gate framework is a real methodological asset. The blocking issues are: (1) missing model configuration (non-negotiable for any reproducibility-aware venue), (2) N=10 seed statistical fragility (needs acknowledgment at minimum, expansion ideally), (3) the lowering-attack overclaim in the abstract, and (4) the absence of the Kloft & Laskov contrast. These four fixes are a half-day of writing. With them, the paper reaches **weak accept / accept** territory at a workshop or second-tier security conference and **borderline** at a top venue.

**Current overall score: 6.8/10.** After the must-fix list: **8.2/10.** After the full recommended list: **8.8–9.0/10.** Reaching 9.5+/10 would additionally require either a second dataset or multi-client collusion results, which are out of scope for the current paper but would be the natural journal extension. 