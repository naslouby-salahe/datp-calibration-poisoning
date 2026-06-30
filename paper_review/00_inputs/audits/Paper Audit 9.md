The PDF is fully in context. All nine passes executed internally before writing. Here is the full audit.

---

# Paper Audit and Review Report
### *Poisoning the Threshold-Calibration Stage in Federated IoT Anomaly Detection: A Policy-Differentiated Vulnerability Analysis*

---

## 1. Executive Verdict

**Overall grade: 6.1 / 10**
**Recommendation: Borderline / Weak Reject** at competitive security venues (USENIX Security, IEEE S&P, CCS). **Borderline Accept** at ESORICS, RAID, or a specialized FL-security workshop after targeted fixes.

**Verdict paragraph.** The paper identifies a genuinely novel and structurally coherent attack surface — the post-training threshold-calibration stage in federated IoT anomaly detection — and characterizes its vulnerability under a clean score-level contamination model with a careful gating framework and honest scope disclosure. The contribution is real: no prior work appears to have studied this phase as an independent attack surface with policy-differentiated analysis. However, the paper as submitted cannot be reproduced by a third party because the autoencoder architecture and FedAvg training hyperparameters are never specified. The bootstrap confidence intervals rest on n=10 seed-level aggregates, which is too small for reliable 95th-percentile interval estimation. A counting inconsistency — "4 source-objective pairs" in §4.3 while only 3 conditions are ever described — introduces a credibility flag that a skeptical reviewer will seize on. Reference [12] (L'heureux 2017, a general ML survey) is cited to support a specific claim about threshold sensitivity that the cited paper does not make. Table 1 reports Cluster Macro-F1 = 0.299 ± 0.000, a zero standard deviation that is never explained. Figure 2 displays a single seed without disclosing that fact in the caption. Taken together, these are not cosmetic issues: several are reviewer-blocking. The paper's conceptual framing and claim discipline are strong; its experimental documentation and statistical scaffolding are not.

**Main reason to accept:** First systematic characterization of the post-training threshold-calibration stage as a policy-differentiated attack surface; the three-gate analysis and negative control are methodologically honest; scope limitations are explicitly bounded.

**Main reason to reject:** The autoencoder architecture and FedAvg training protocol are absent, making the experiment unreproducible. Bootstrap CIs at n=10 are unreliable at the stated 95% level. Single dataset (N-BaIoT, 9 clients), score-level only.

**Fastest path to improve:** Add a one-paragraph model and training specification (architecture, FedAvg rounds, epochs, LR, optimizer, normalization); fix the "4 source-objective pairs" inconsistency; replace Reference [12]; explain the ±0.000 in Table 1.

---

## 2. Scorecard

| Category | Score | Notes |
|---|---|---|
| Novelty | 7.0 / 10 | Real novelty; score-level limit caps it |
| Technical correctness | 7.5 / 10 | Mostly correct; notation conflict in §6; ambiguous FedAvg role |
| Methodological rigor | 5.0 / 10 | Gating system is thoughtful; n=10 and unjustified constants hurt |
| Experimental support | 5.5 / 10 | Results solid within scope; missing architecture prevents verification |
| Claim discipline | 7.5 / 10 | Generally well-hedged; two overstatements flagged |
| Related work positioning | 5.5 / 10 | Wrong citation [12]; thin for threshold-policy literature |
| Reproducibility | 3.5 / 10 | Architecture and training protocol absent; fatal gap |
| Visual presentation | 6.0 / 10 | Figure 2 single-seed; Table 1 undefined abbreviations |
| Writing clarity | 7.5 / 10 | Clear prose; FedAvg phrasing ambiguous; one notation conflict |
| Reviewer-proofness | 5.0 / 10 | Multiple easy attack points for a skeptical reviewer |
| **Overall** | **6.1 / 10** | |

---

## 3. Top Strengths

1. **Genuine novelty:** The threshold-calibration stage is not addressed by any cited training-phase or aggregation-phase defense. The claim "no prior work characterizes this stage" is credibly defended and appropriately hedged with "to our knowledge."
2. **Clean scope architecture:** The paper explicitly delineates what it does not claim — no traffic-level realizability, no defense design, no multi-client collusion, no generalization beyond N-BaIoT — and maintains this discipline throughout.
3. **Three-gate analysis with a negative control:** The Gate-1/Gate-2/Gate-3 framework with the Random-Benign negative control is methodologically sound. Confirming that the random-benign control spans zero at all fractions directly supports causal attribution to tail sampling.
4. **Policy-differentiated framing:** The finding that the same injection fraction produces qualitatively different vulnerability profiles (Local = isolated maximum harm; Global = diluted federation-wide propagation; Cluster = intra-cluster spillover) is a concrete and useful contribution for deployment designers.
5. **Explicit isolation sanity checks:** AUROC invariance across all 4,320 cells, per-client rank ordering unchanged, and bitwise-identical model weights before and after calibration are all verified and reported. This strongly rules out protocol contamination.
6. **Bootstrap CIs with paired seeds:** Using statistically independent seed offsets (training seed i, poisoning seed i+100, analysis seed i+300) is a thoughtful design that reduces seed-level correlation.
7. **Detectability disclosure:** The paper honestly flags that with-replacement tail sampling at f=0.4 produces ≈2,100 expected collision pairs detectable by a uniqueness check — a limitation that many adversarial ML papers would omit.

---

## 4. Top Weaknesses

**W1 — FATAL: Missing autoencoder architecture and FedAvg training protocol (§4.1)**
The paper says "each client trains a per-client autoencoder on benign traffic using FedAvg." It never specifies: encoder/decoder layer sizes, hidden dimensions, activation functions, reconstruction loss, number of FedAvg communication rounds, local epochs per round, learning rate, batch size, optimizer, or aggregation weighting. The experiment cannot be reproduced. Any security conference reviewer will immediately notice this.

**W2 — FATAL: "4 source-objective pairs" is not explained; arithmetic conflict with 3 described conditions (§4.3)**
The paper states "4 source-objective pairs × 3 threshold policies × 4 injection fractions × 9 victim clients × 10 seeds = 4,320 cells." Only three conditions are described: Raise (High-Score-Benign), Lower (Low-Score-Benign), Random-Benign (negative control). A fourth is never named. This is either an error or an incomplete description that will be flagged by every careful reviewer.

**W3 — MAJOR: Reference [12] (L'heureux et al., 2017) is cited incorrectly (§2)**
The claim "Threshold-based anomaly detection is sensitive to the calibration distribution: small shifts in the quantile-defining score set translate directly to missed detections or false alarms [12]" cites L'heureux 2017 (IEEE Access: "Machine learning with big data: Challenges and approaches"), which is a general ML survey paper. It makes no specific claim about threshold sensitivity in anomaly detection. A reviewer familiar with the literature will flag this as a fabricated citation alignment. Replace with a paper that actually makes this specific claim (e.g., Kloft & Laskov 2012 [11] is a better fit).

**W4 — MAJOR: n=10 bootstrap CIs at 95% are statistically unreliable**
Bootstrap percentile confidence intervals require large B (here B=10,000, which is fine), but their coverage accuracy depends on having enough observations n. With n=10 seed-level aggregates, a 95% percentile bootstrap CI is interpolated from the 0.5th and 9.5th order statistics — unreliable at the tails. This does not invalidate the directional findings, but the paper states "[95% CI]" as if these are valid frequentist intervals. This will be challenged. At minimum, a caveat about the n=10 coverage limitation should be added, ideally alongside BCa (bias-corrected and accelerated) bootstrap CIs.

**W5 — MAJOR: Table 1 reports Cluster Macro-F1 = 0.299 ± 0.000; zero standard deviation is unexplained**
Zero variance across 10 seeds for a metric that depends on cluster assignment (which the paper says varies each seed because "calibration fingerprints vary with training") is either a reporting error or requires an explicit mechanistic explanation. A reviewer will treat this as a data quality flag.

**W6 — MAJOR: Autoencoder role under FedAvg is ambiguous (§4.1)**
§2 says "each client trains a local encoder-decoder on benign traffic" (suggesting local, not federated). §4.1 says "The federation trains a per-client autoencoder on benign traffic using FedAvg for feature extraction." FedAvg is an aggregation protocol, not a feature extraction method. The sentence "using FedAvg for feature extraction" is either a grammatical error or reveals an architectural misunderstanding. What is actually being federated — model weights? gradients? only during training? does each client end up with the same model or a personalized one? This must be clarified.

**W7 — MODERATE: Figure 2 shows only seed 0 without disclosing this in the caption**
The caption reads "Per-client FPR under clean baseline, Global vs. Local threshold (seed 0)" — the "(seed 0)" qualifier is in the caption text but not visually prominent. More importantly, no justification is given for using seed 0 as the representative seed. A reviewer may ask whether this seed was chosen because it best illustrates the point. Either show mean FPR ± CI across all seeds or explicitly state "seed 0 is representative; other seeds show the same device ordering."

**W8 — MODERATE: N notation conflict in §6**
In §6, the paper uses N in two incompatible senses within the same discussion: "With reservoir size R≈10%·N" where N appears to mean the calibration set size of the smallest device (≈2,622), while throughout the rest of the paper N=9 denotes the number of federation clients. The calculation (N·f)²/(2R) ≈ 2,100 works out only if N=2,622. Rename one of these variables.

**W9 — MODERATE: Table 1 abbreviations P10 and Worst BA are undefined**
The column header "Worst BA" is never defined in the caption or anywhere in the paper body. "P10" likewise appears without definition (10th-percentile balanced accuracy? something else?). The caption says "Bold marks the best value per metric" — but for "Worst BA," lower would be better for the adversary and higher would be better for the defender, yet the bold convention applies without acknowledging this direction ambiguity.

**W10 — MODERATE: "30–80 undetected Mirai flows per 1000 attack packets" is stated without derivation (§5.2)**
This is a potentially powerful harm contextualization. But "at representative traffic rates" is undefined, and the calculation is not shown. A reviewer cannot verify it and may treat it as speculation. Either provide a one-sentence derivation in a footnote or remove the claim.

---

## 5. Fatal or Near-Fatal Risks

**Risk 1 — Unreproducible experiment** (W1): Missing architecture and hyperparameters. Any reviewer attempting to reproduce even a single cell will fail. At competitive venues, this alone causes desk rejection or reviewer vote of "reject." *Fix: Add one paragraph to §4.1 with complete model and training specifications.*

**Risk 2 — Arithmetic inconsistency in cell count** (W2): "4 source-objective pairs" with only 3 described conditions is a credibility-damaging inconsistency. A methodologically rigorous reviewer will conclude either that an undescribed condition exists and was silently included, or that the total cell count is wrong. Either way, the experimental scope is unverified. *Fix: Name all four source-objective pairs explicitly, or correct "4" to "3" and adjust the total.*

**Risk 3 — Fabricated citation alignment** (W3): Reference [12] does not support the cited claim. If a reviewer checks — and for a claim this central to the paper's framing, many will — the paper will appear to be padding its citations. *Fix: Replace [12] with a specific paper on threshold sensitivity in anomaly detection.*

**Risk 4 — Bootstrap CI coverage at n=10** (W4): If a statistics-literate reviewer calls this out, the paper's primary quantitative claims lose their stated precision. The directional findings are still credible, but the specific interval widths are not. *Fix: Add a sentence acknowledging that n=10 percentile bootstrap CIs may undercover at the tails; consider reporting BCa CIs.*

**Risk 5 — Score-level-only attack** (combined across §3, §6): The attack is implemented programmatically, not through generated traffic. A security reviewer may argue this makes the contribution a theoretical framing rather than a demonstrated vulnerability. The paper preempts this honestly, but the objection remains a credible rejection reason. *Fix: Not eliminable without new experiments; reinforce the preemption language in §1 and ensure the abstract's phrasing is precise.*

---

## 6. Section-by-Section Review

### 6.1 Title
**Grade: 8 / 10 | Submission-ready: Yes**

"Poisoning the Threshold-Calibration Stage in Federated IoT Anomaly Detection: A Policy-Differentiated Vulnerability Analysis" is precise and informative. It correctly scopes to a stage (threshold-calibration), a setting (federated IoT anomaly detection), and a framing (vulnerability analysis). "Policy-Differentiated" is the right differentiator and will appear in keyword searches.

**Minor issue:** The subtitle "A Policy-Differentiated Vulnerability Analysis" is technically a qualifier of what type of analysis is presented, not of what the paper found. This is fine; no fix required.

**What is missing:** Dataset is not named in the title. Some LNCS-format venues prefer dataset-agnostic titles; others prefer specificity. No fix needed, but the authors should ensure alignment with the venue's author instructions.

---

### 6.2 Abstract
**Grade: 7.0 / 10 | Submission-ready: After minor fix**

**What works:** Specifies the attack surface, the attack mechanism, the policies evaluated, the dataset, and the primary results with specific numbers. The phrasing "score-level contamination model" is precise. The scope boundary ("without altering model weights, training data, or test labels") is stated upfront.

**What is unclear:** "coefficient-of-variation disparity ΔCV(FPR) increasing 0.05–0.06" is presented in the abstract without any prior definition of CV(FPR) or ΔCV(FPR). A reader unfamiliar with this metric cannot assess whether 0.05–0.06 is a large or small effect. The metric must be interpreted in-abstract or dropped from the abstract in favor of the ΔTPR statement alone.

**What is missing:** The abstract does not state the evaluation dataset explicitly by name (N-BaIoT), even though the paper otherwise names it freely. This weakens reproducibility signaling.

**What is overclaimed:** None — the scope is well-bounded.

**Fix needed:** Replace "coefficient-of-variation disparity ΔCV(FPR) increasing 0.05–0.06" with "producing a false-positive-rate disparity increase of 0.05–0.06 (CV of FPR) across clients." Add "N-BaIoT nine-device" somewhere in the first sentence's experimental description (it already exists — this is fine).

**Priority:** Minor.

---

### 6.3 Introduction
**Grade: 7.5 / 10 | Submission-ready: After minor fix**

**What works:** The problem motivation is clear. The three-axis differentiation argument ("temporally isolated," "phase-specific trust model," "policy-dependent effects") is concise and preemptive. The "An undefended phase" bold paragraph is effective framing.

**What is unclear:** The introduction mentions "Gate-1 pass rate" in Contribution 2 before the term is defined (it is defined in §4.4). A reviewer reading the introduction will not know what "100% Gate-1 pass rate" means. Define it parenthetically at first use: "Gate-1 pass rate (fraction of seeds showing material threshold shift above a calibration-specific threshold; see §4.4)."

**What is missing:** A concrete motivating scenario. The introduction argues that calibration-stage poisoning is possible and structurally distinct, but does not give an intuitive harm case (e.g., "An attacker who controls a smart thermostat in a hospital IoT federation can silently disable malware detection on all devices sharing its cluster — without touching any model weight or gradient"). Such a two-sentence harm scenario would strengthen the motivation.

**What is overclaimed:** "structurally outside the scope of every defense that monitors the training or aggregation loop" — this is a logical claim, not an empirical one, and it's stated too categorically. A reviewer may argue that some defense could monitor calibration scores as a side channel. Rephrase: "structurally outside the scope of every defense in the cited literature that targets the training or aggregation loop."

**Priority:** Moderate (Gate-1 definition), Minor (scope phrase), Nice-to-have (harm scenario).

---

### 6.4 Contributions
**Grade: 6.5 / 10 | Submission-ready: After moderate fix**

**What works:** Three numbered contributions; each is specific and falsifiable. Contribution 2 includes specific numbers with section pointers.

**What is unclear:** Contribution 1 claims to "isolate the post-training threshold-calibration stage as an undefended attack surface." This is a conceptual/framing contribution rather than a result. At competitive venues, a framing contribution must be supported by a formal argument or structural proof, not just a literature review. The paper's argument is mostly logical (defenses complete before calibration begins), which is sufficient for a position paper, but may be challenged at a research track.

**What is missing:** The methodological contributions — the three-gate analysis framework, the paired-seed design, the negative control — are not listed as contributions. They are implicit in Contribution 2 but deserve explicit mention or at least a parenthetical: "(using a three-gate empirical validation framework with a Random-Benign negative control)."

**What is overclaimed:** Contribution 3 says "the score-level lowering attack succeeds for Local and Cluster but is conditionally bounded for Global." The word "succeeds" is appropriate for this secondary attack only if the reader understands that "success" here means a measurable threshold shift, not a practically devastating one. The paper correctly labels lowering results as lower bounds and secondary findings elsewhere, but the contribution statement does not carry those qualifiers. Add "as a lower bound under Replace-Fixed-Budget" to the lowering claim.

**Priority:** Moderate.

---

### 6.5 Related Work
**Grade: 5.5 / 10 | Submission-ready: No — wrong citation is blocking**

**What works:** Good topical organization into four subsections; covers FL anomaly detection, defenses, centralized poisoning, and threshold policies. The segmentation makes the gap visible.

**What is unclear:** Nothing is ambiguous in the related work, but it is thin.

**What is missing:**
- Any recent (2021–2024) work on FL anomaly detection security. The most recent cited paper is Nguyen et al. 2022 (FL for healthcare). For a security paper submitted in 2025-2026, this is conspicuously dated.
- A comparison table distinguishing this paper's setup from [1], [7], [11] along the dimensions: phase targeted, policy-awareness, score-level vs. gradient-level, federated vs. centralized. Even a sentence-level contrast for each would strengthen positioning.
- Reference to conformal prediction / quantile regression literature on threshold selection, which is increasingly used in FL anomaly detection and represents an adjacent approach the adversary's model implicitly attacks.
- MQTT-IoT-IDS2020, CICIoT2023, or similar as acknowledged out-of-scope datasets.

**What is overclaimed:** None — the "to our knowledge" hedge is appropriately used.

**Exact fix needed:**
- Replace Reference [12] (L'heureux 2017) with a paper that specifically discusses threshold calibration sensitivity in anomaly detection. Kloft & Laskov 2012 [11] is already in the bibliography and its framing ("online anomaly detection under adversarial impact") is actually closer. Alternatively, cite Zhang et al. 2021 on threshold selection in deep anomaly detection, or a similar specific paper.
- Add 2–3 recent FL-IoT security citations.

**Priority:** Fatal (wrong citation), Major (recency gap).

---

### 6.6 Threat Model (§3)
**Grade: 7.5 / 10 | Submission-ready: After minor fix**

**What works:** The most precisely specified section in the paper. The explicit list of what the adversary does NOT do (model weights, gradients, other clients' data, test data, test labels, training labels) is exactly what reviewers need. The scope boundary ("score-level characterization is a controlled experiment, not a deployed attack") is stated clearly.

**What is unclear — adversary policy knowledge:** The threat model never states whether the adversary knows the federation's threshold policy (Global, Local, or Cluster). For a policy-differentiated analysis, this is a material assumption. If the adversary is policy-blind, the attack's effectiveness is reduced in certain settings; if policy-aware, the adversary can choose the optimal injection strategy. As written, the experiments implicitly assume a policy-aware adversary (since different analyses are run for each policy), but this is not stated. Add one sentence: "The adversary is assumed to know the federation's threshold-aggregation policy; a policy-blind variant is future work."

**What is unclear — "gray-box":** The paper labels the access model "gray-box score-level access" but also states "since the adversary controls the client." A fully controlled client normally implies white-box access. The "gray-box" qualification refers specifically to the restriction that the adversary operates at the score level rather than at the model weight level — this restriction is a modeling choice imposed by the paper, not a technical constraint of client control. Reframe: "The adversary controls the client's calibration buffer (white-box access to calibration data) but is constrained to score-level operations — it does not directly inject model weights or access the global aggregation." This is more precise than "gray-box."

**Fix needed:** Add policy-knowledge assumption sentence; revise "gray-box" framing.

**Priority:** Moderate.

---

### 6.7 Experimental Protocol (§4)
**Grade: 4.5 / 10 | Submission-ready: No — major reproducibility gaps are blocking**

**What works:** Injection fractions, quantile, seed structure, cluster K and initialization, gate definitions, bootstrap parameters, negative control, and the cell count formula are all documented. The paired-seed design (training i, poisoning i+100, analysis i+300) is thoughtful.

**Issue 1 — Missing autoencoder specification (fatal):** No architecture is given. Layer count, hidden dimensions, bottleneck size, activation functions, reconstruction loss, optimizer, learning rate, batch size, local training epochs per FedAvg round, number of FedAvg rounds, and aggregation weighting are all absent. Without these, the experiment cannot be reproduced.

**Issue 2 — FedAvg role is ambiguous:** §4.1 says "The federation trains a per-client autoencoder on benign traffic using FedAvg for feature extraction." FedAvg is an aggregation protocol. What is being aggregated? Do all clients receive the same global model after FedAvg, or does each client retain a personalized model? Is FedAvg used only to train a shared encoder, with the decoder being local? Does the "per-client autoencoder" mean each client trains locally and the local model is never aggregated? This is architecturally ambiguous and must be resolved.

**Issue 3 — "4 source-objective pairs" vs. 3 described conditions:** Three attack conditions are described (Raise, Lower, Random-Benign). The total cell count formula requires 4. The most likely explanation is that Random-Benign is paired separately with each of Raise and Lower (making 4: Raise+High, Lower+Low, Raise+RandomBenign-control, Lower+RandomBenign-control), but this is never stated. Either enumerate all four explicitly or correct "4" to "3."

**Issue 4 — Gate-1 constants unjustified:** δτ_v = max(0.1 × IQR(C_v^clean), 0.01 × median_j(IQR(C_j^clean))). The constants 0.1 and 0.01 are arbitrary. No rationale is given for why these specific constants define "material shift." A reviewer will ask whether these were tuned on the results, which would invalidate the gating. Add a sentence stating these constants were defined prior to running any poisoning experiments (or cite a prior work that uses the same formula).

**Issue 5 — Missing data preprocessing:** How is raw N-BaIoT traffic converted to reconstruction scores? What features are used? Is the data normalized? What is the train/calibration split? The calibration set sizes are stated (2,622 to 9,909 benign samples) but the construction protocol is not.

**Priority:** Issues 1, 2, and 3 are fatal. Issues 4 and 5 are major.

---

### 6.8 Results (§5)
**Grade: 6.5 / 10 | Submission-ready: After moderate fix**

**What works:** Results are organized by attack type; specific CI values are given with directional consistency described seed-by-seed; the policy-differentiated summary is the clearest part of the paper. The "30–80 undetected Mirai flows" contextualization is a good instinct.

**Issue 1 — Table 1 Cluster Macro-F1 = 0.299 ± 0.000:** Zero standard deviation for a metric that should vary with cluster assignment across seeds is unexplained. One possible explanation: K-means++ with fixed random_state=42 always produces the same cluster assignments because the N-BaIoT device types are well-separated in calibration-score space, so the "variation with training" is too small to change assignments. If this is the case, state it explicitly: "Cluster Macro-F1 shows zero variance across seeds because K-means++ assignments are stable across all training seeds at K=3 in this dataset." If it is a reporting error, fix it.

**Issue 2 — The Cluster ΔTPR plateau at f=0.2 (raising attack):** Table 2 shows Cluster ΔTPR = −4.9 pp at both f=0.2 and f=0.4. This plateau is mentioned ("plateauing from f=0.2") but never explained. Why does Cluster stop responding to additional injection at f=0.2 while Local continues to increase? This is a mechanistically interesting result. One plausible explanation: at f=0.2, the shared cluster threshold has already saturated the detection-rate loss for co-cluster members whose calibration distributions are different from the victim's — further injection on the victim's threshold is diluted across cluster members. Add one sentence of mechanistic reasoning.

**Issue 3 — "30–80 undetected Mirai flows per 1000 attack packets" lacks derivation:** This is stated in §5.2 for "representative traffic rates" but the derivation is not shown. This is either verifiable (in which case, show it in a footnote) or it is speculation (in which case, remove it). A reviewer who cannot verify this number will treat it as an unsupported claim.

**Issue 4 — Global at f=0.1 Gate-1 near-failure:** The paper states that at f=0.1, two devices are "intermittently non-significant (2/10 and 4/10 seeds respectively)" for Global. This is reported accurately and the victim-majority condition still holds. However, it suggests that Global's Gate-1 claim of "100% at all non-zero fractions" is device-level inconsistent. The phrasing should be precise: "100% seed-level Gate-1 pass rate at all non-zero fractions" (meaning 10/10 seeds pass, not 9/9 devices), which is what the paper means but does not always say.

**Priority:** Issue 1 is major (potential data error). Issues 2 and 3 are moderate. Issue 4 is minor wording.

---

### 6.9 Discussion and Limitations (§6)
**Grade: 7.0 / 10 | Submission-ready: After minor fix**

**What works:** The score-level proxy limitation is acknowledged precisely. Detectability (duplicate score problem) is disclosed with a quantitative estimate. Scope limitations are explicitly listed. Defense properties are sketched without overclaiming.

**Issue 1 — N notation conflict (as flagged in W8):** In the collision count formula, N appears to mean the calibration set size (≈2,622 for the smallest device), while elsewhere N=9 (number of clients). The formula is: (N·f)² / (2R) ≈ 2,100, where if N=2,622, f=0.4, R≈262, then m=N·f=1,049 replacement draws from a pool of R=262 entries; expected collisions ≈ m²/(2R) = 1,049²/524 ≈ 2,099. This is correct arithmetic — but only if the reader correctly infers N=2,622 here. Use n_v or |C_v| for the calibration set size throughout the discussion section.

**Issue 2 — "evading requires score perturbation at the cost of leaving the exact tail boundary" is opaque:** What does this mean concretely? That an adversary trying to avoid the uniqueness check must add noise to the duplicated scores, which shifts them away from the top-10% tail? If so, say that explicitly.

**Priority:** Issue 1 is moderate. Issue 2 is minor.

---

### 6.10 Conclusion (§7)
**Grade: 7.5 / 10 | Submission-ready: After minor fix**

**What works:** Accurately summarizes the main findings. Scoped correctly. Future work directions (traffic-level realizability, defense design, generalization) are appropriate.

**Issue:** "calibration-stage hardening must match the aggregation design, not only the training-phase defense" — this is a good insight, but "match the aggregation design" is vague. Specify what it means: "a defense against Local-policy calibration poisoning can monitor single-client threshold shifts; a defense against Global-policy poisoning must inspect federated averages against server-side distribution priors." Even one concrete example would give the conclusion actionable content.

**Priority:** Minor.

---

### 6.11 References
**Grade: 5.5 / 10**

**Issue 1 (fatal):** Reference [12] — L'heureux A. et al., "Machine learning with big data: Challenges and approaches," IEEE Access, 2017 — is cited in §2 to support the claim that "threshold-based anomaly detection is sensitive to the calibration distribution." This paper is a general ML survey that does not make this specific claim. Replace it.

**Issue 2:** K-means++ is used but the Arthur & Vassilvitskii (2007) paper is not cited. Standard practice requires citing the algorithm's origin.

**Issue 3:** 21 references total, all from 2010–2022. No 2023–2024 papers appear, which is conspicuous for a 2025-2026 submission in a rapidly evolving field.

**Issue 4:** No defense paper specifically for calibration-stage or post-training integrity (e.g., FLAME, FedRecover, or similar) is cited in the defense sketch in §6. Even if none exists for this exact stage, citing the closest analogous defense work would strengthen the related-work positioning.

**Priority:** Issue 1 is fatal. Issues 2–4 are moderate.

---

## 7. Reviewer Questions the Paper Must Already Answer

### Threat Model Questions
- **Q-TM1:** Does the adversary know the federation's threshold-aggregation policy (Global/Local/Cluster) before mounting the attack? *(Paper does not answer — add one sentence)*
- **Q-TM2:** If the adversary controls the client's execution environment (as stated), why is the attack restricted to the calibration buffer? Could the same adversary more easily poison model weights? *(Paper addresses this: calibration poisoning is structurally distinct and bypasses gradient defenses. The answer is in §1 but should be made explicit in §3)*
- **Q-TM3:** Can a server detect the calibration poisoning by checking submitted thresholds against historical priors? *(Paper mentions this in §6 as a future defense property; should be stated earlier in §3 as a known defense gap)*
- **Q-TM4:** Is single-client compromise the right scope? What if even one compromised client is unrealistic for IoT deployments? *(Partially addressed in §6; should add one sentence in §3 explaining why single-client is the appropriate baseline scope)*

### Novelty Questions
- **Q-N1:** Is this just data poisoning applied to calibration data? *(Paper explicitly preempts this in §1 with three-axis argument — adequate)*
- **Q-N2:** Does Kloft & Laskov 2012 [11] not already cover score-distribution poisoning? *(Paper distinguishes the federated, phase-isolated, and policy-dependent aspects; should add a sentence in §2 making this contrast explicit)*
- **Q-N3:** Is the contribution a characterization paper (acceptable) or an attack paper (requires more experiments)? *(Paper frames as characterization in §6 but contributions are partly framed as "attack achieves X" — needs consistent framing throughout)*

### Methodology Questions
- **Q-M1:** What is the autoencoder architecture? *(Not answered — fatal gap)*
- **Q-M2:** What are the FedAvg hyperparameters? *(Not answered — fatal gap)*
- **Q-M3:** What are the 4 source-objective pairs? Only 3 are described. *(Not answered — inconsistency)*
- **Q-M4:** How were the constants 0.1 and 0.01 in the Gate-1 formula chosen? Were they set before or after observing results? *(Not answered)*
- **Q-M5:** Why is the maximum injection fraction f=0.4? Does the attack saturate before f=0.5 or beyond? *(Not answered; add one sentence)*
- **Q-M6:** How is "victim" defined when measuring ΔTPR for Global policy, where all 9 clients receive the poisoned threshold? *(Partially answered: §3 uses "victim client v" and "non-victim clients." But Table 2's ΔTPR for Global is averaged across what — all 9 clients, or just the poisoned client? This is ambiguous.)*

### Dataset Questions
- **Q-D1:** Why only N-BaIoT? Why not CICIoT2023 or other IoT traffic datasets? *(Paper explicitly acknowledges N-BaIoT-only scope in §6; adequate as scoped)*
- **Q-D2:** How were the calibration sets constructed — is the calibration data held out from training or drawn from the same distribution? *(Not answered explicitly in §4.1)*
- **Q-D3:** Are the 9 devices truly heterogeneous in calibration-score distributions, or do some cluster naturally? *(Implied by Figure 2 and the cluster assignment logic, but not directly stated)*

### Metric Questions
- **Q-ME1:** What is "P10" and "Worst BA" in Table 1? *(Not defined — fix required)*
- **Q-ME2:** Why is CV(FPR) the primary harm metric for the lowering attack rather than absolute FPR or detection latency? *(Not explained — add one sentence justifying the choice)*
- **Q-ME3:** Why is ΔTPR the primary downstream harm metric for the raising attack, given that other metrics (F1, BA) are also reported in Table 1? *(The rationale is clear: ΔTPR directly measures missed attack detections. This is fine — but state it explicitly.)*

### Statistical Validity Questions
- **Q-S1:** Are bootstrap CIs at n=10 reliable at the 95% level? *(Paper does not address this. Add a caveat — BCa CIs would be better.)*
- **Q-S2:** How were multiple testing issues addressed across 4,320 cells? *(Paper does not address multiple comparisons. For a characterization paper, this is less critical, but should be acknowledged.)*
- **Q-S3:** Why is the victim-majority condition set at ≥5/9 (simple majority)? Why not ≥7/9 or ≥9/9? *(Not justified)*

### Baseline Questions
- **Q-B1:** Is there a comparison against existing calibration poisoning attacks in centralized settings? *(Paper distinguishes federated vs. centralized settings in §2; no centralized baseline needed)*
- **Q-B2:** Why is the threshold quantile fixed at q=0.95? Does the vulnerability profile change at q=0.90 or q=0.99? *(Not addressed — at minimum, should be listed as a scope limitation)*

### Reproducibility Questions
- **Q-R1:** Is code available? *(Not stated — should be added as a reproducibility statement)*
- **Q-R2:** Are dataset splits fixed and specified? *(Calibration set sizes are given; train/test split construction is not)*

### Scope and Limitation Questions
- **Q-SC1:** Do the findings generalize beyond autoencoders to isolation forest, LOF, or VAE? *(Explicitly out of scope — adequately stated in §6)*
- **Q-SC2:** Do the findings generalize to federations larger than N=9? *(Explicitly out of scope — adequately stated; but note that the Global policy's 1/N dilution argument would become more severe at N=100)*

### Visual/Formatting Questions
- **Q-V1:** Why is Figure 2 showing only a single seed? Is seed 0 representative? *(Not addressed in caption)*
- **Q-V2:** Why is the Random-Benign control not plotted in Figure 3? *(Mentioned in caption as "not plotted" but no reason given — consider adding a flat reference line)*

---

## 8. Claim Discipline Audit

| # | Claim (paraphrased) | Location | Support level | Weakness | Safe rewrite | Status |
|---|---|---|---|---|---|---|
| C1 | "The threshold-calibration stage is structurally outside the scope of every defense that monitors the training or aggregation loop." | §1, §2 | **Partially supported** (logical argument + literature survey) | Reviewer may know of a defense that incidentally covers calibration | Add "among all defenses reviewed here" | Needs wording downgrade |
| C2 | "Raising attack achieves 100% Gate-1 pass rate at all non-zero fractions." | Abstract, Contribution 2 | **Fully supported** — Table 2 confirms 10/10 seeds | "100%" holds at the seed level, not at the per-device level (two Global devices intermittently fail at f=0.1) | Add "(seed-level)" qualifier | Partially supported — needs precision |
| C3 | "No prior work characterizes the vulnerability of the post-training threshold-calibration stage in federated threshold-based anomaly detection." | §2 | **Adequately hedged** with "to our knowledge" | Reviewer may know obscure prior work | Keep as-is | Appropriate |
| C4 | "Degrading victim true-positive rates by 2.4 to 7.9 percentage points across injection fractions." | Abstract | **Fully supported** — Table 2 | None; range is correct across all non-zero fractions and all three policies | Keep as-is | Fully supported |
| C5 | "FPR disparity ΔCV(FPR) increasing 0.05–0.06" (lowering attack) | Abstract | **Partially supported** — 10/10 seeds for Local, 8/10 for Cluster | 8/10 Cluster success is presented as if it were as strong as Local | Add "(8/10 seeds for Cluster, 10/10 for Local)" | Needs precision |
| C6 | "Translating to an additional ≈30–80 undetected Mirai flows per 1000 attack packets at representative traffic rates." | §5.2 | **Unsupported** — no derivation shown | "Representative traffic rates" is undefined; no calculation is shown | Remove or add a footnote derivation | Needs experiment (or removal) |
| C7 | "Local achieves the lowest CV(FPR) (0.333 ± 0.034)… confirming per-client thresholds suppress false-positive heterogeneity most effectively." | §5.1 | **Fully supported** within N-BaIoT scope | CV(FPR) measures heterogeneity, not magnitude; Local could still have high per-client FPRs | Add "(in terms of heterogeneity; absolute FPR values are shown in Figure 2)" | Fully supported with caveat |
| C8 | "Global harm (−6.1 pp) is notable." | §5.2 | **Partially supported** — mathematically real but "notable" is subjective | Whether −6.1 pp is notable depends on baseline FPR and operational context | Replace "notable" with "measurable despite 1/N dilution" | Overclaimed (word choice) |
| C9 | "Lowering attack succeeds for Local and Cluster; is conditionally bounded for Global." | Abstract, §5.3, Conclusion | **Fully supported** with the "lower bound" qualifier | Abstract and conclusion do not always carry the lower-bound qualifier | Ensure "as a lower bound under Replace-Fixed-Budget" appears in every summary | Needs consistent qualification |
| C10 | "Calibration-stage poisoning is structurally distinct along three axes." | §1 | **Partially supported** | Axes 1-2 are definitional; Axis 3 (policy-dependent effects) is empirical. The "distinctness" claim would be stronger with a formal argument for Axes 1-2 | Add: "Axes 1–2 follow from the temporal structure of FL protocols; Axis 3 is demonstrated empirically in §5." | Partially supported — needs framing |
| C11 | "Any effective defense must address the calibration buffer as an unmonitored input channel, validate submitted thresholds against server-side priors, or impose calibration-set integrity constraints." | §6 | **Adequately supported** (logical deduction from threat model) | These are necessary, not sufficient conditions for a defense | Add "necessary" before "requirements" | Appropriate with one word fix |

---

## 9. Methodology and Experiment Audit

| Issue | Location | Why it matters | Reviewer risk | Fix | Priority |
|---|---|---|---|---|---|
| Autoencoder architecture absent | §4.1 | Experiment cannot be reproduced | High — blocks acceptance | Add full specification (layers, dims, activation, loss) | **Fatal** |
| FedAvg training hyperparameters absent | §4.1 | Experiment cannot be reproduced | High — blocks acceptance | Add rounds, epochs, LR, optimizer, weights | **Fatal** |
| "4 source-objective pairs" vs. 3 described conditions | §4.3 | Credibility inconsistency | High | Name all 4 pairs or correct count to 3 | **Fatal** |
| FedAvg role is architecturally ambiguous | §4.1 | Reviewer cannot determine what is federated | High | Clarify: global model vs. personalized model post-FedAvg | **Major** |
| Calibration set construction protocol missing | §4.1 | Is calibration data held out from training? | Moderate | Add one sentence describing train/calibration split | **Major** |
| Data preprocessing/normalization absent | §4.1 | Reconstruction scores depend on normalization | Moderate | Specify preprocessing pipeline | **Major** |
| Gate-1 constants (0.1, 0.01) unjustified | §4.4 | May appear to be tuned on results | Moderate | State pre-specification or cite precedent | **Major** |
| Victim-majority condition (≥5/9) unjustified | §4.4 | Arbitrary threshold affects Gate-1 claim | Moderate | Justify as simple majority or cite precedent | **Moderate** |
| n=10 bootstrap CIs: coverage unreliable at 95% | §4.4 | Stated precision is overstated | High | Add caveat; consider BCa CIs | **Major** |
| ΔTPR for Global policy averaging ambiguity | §5.2, Table 2 | Is ΔTPR averaged over all 9 clients or just the poisoned one? | Moderate | Add one sentence defining what "victim ΔTPR" means under Global policy | **Moderate** |
| Cluster ΔTPR plateau at f=0.2 unexplained | §5.2 | Interesting finding left without mechanism | Low | Add one sentence | **Minor** |
| "30–80 undetected Mirai flows" not derived | §5.2 | Unsupported quantitative claim | Moderate | Add footnote derivation or remove | **Moderate** |
| Multiple comparisons not addressed | §4.4 | 4,320 cells × 3 gates: inflation risk | Low (characterization paper) | Acknowledge briefly in limitations | **Minor** |
| f=0.4 as maximum: saturation behavior unknown | §4.3 | Truncated design space | Low | Add one sentence noting f>0.4 is future work | **Minor** |
| q=0.95 as only quantile: sensitivity unknown | §4.1 | Results may not generalize to q=0.90 | Low | Add as scope limitation | **Minor** |
| Random-Benign control: same design for Raise and Lower? | §4.3 | Control condition unclear if different baselines needed | Moderate | Clarify whether one or two Random-Benign conditions are run | **Moderate** |
| No second dataset | §4.1 | Single-dataset results: generalizability unknown | High | Acknowledge as primary scope limitation | **Major (scope)** |

---

## 10. Figures and Tables Audit

### Figure 1: Attack surface diagram
**Grade: 7.0 / 10**

**What it communicates:** The temporal sequence (training phase → aggregation → calibration stage) and the adversary's entry point.

**What is confusing:** The three policy boxes (Global, Local, Cluster) at the bottom are very small and the font is barely readable at print scale. The adversary arrow points to "Calibration Buffer" but the spatial relationship between the adversary, the buffer, and the three policies is not explicit — does the adversary target the buffer before or after policy application?

**Visual fix needed:** Increase font size in the three policy boxes. Add a small annotation clarifying the arrow direction: "adversary modifies buffer → threshold policy aggregates result → deployment threshold shifts."

**Should stay / move / merge / remove:** Stay in main paper.

---

### Figure 2: Per-client FPR under clean baseline
**Grade: 4.5 / 10**

**What it communicates:** That Global policy produces high FPR heterogeneity across 9 devices while Local produces low heterogeneity.

**What is confusing:** Seed 0 is shown without explanation or justification. No error bars are shown. Readers cannot assess whether this seed is representative.

**What visual fix is needed:** Either (a) show mean FPR per client (averaged over 10 seeds) with ±1 SD error bars, or (b) keep seed 0 but add to the caption: "Device ordering is stable across all 10 seeds; seed 0 shown as representative." The current figure is misleading in the absence of this qualification.

**Additional issue:** Two devices with nearly zero FPR for both policies (visible at bottom of chart) make the scale dominated by the two high-FPR Global devices, compressing the range for the others. Consider a log-scale or a secondary inset.

**Should stay / move / merge / remove:** Stay in main paper after fix.

---

### Figure 3: Mean Δτ vs. injection fraction
**Grade: 8.0 / 10**

**What it communicates:** The dose-response relationship between injection fraction and threshold shift for both attacks and all three policies. The policy-differentiated profile is immediately visible.

**What is confusing:** Panel (a) has a y-axis scale of 0.0 to 0.8, making the Global line (≈0.03 to 0.10) nearly invisible as a flat line near zero. A reader skimming the figure will not see the Global result. The Random-Benign control is mentioned in the caption as "not plotted" — a thin dashed flat line at y≈0 would reinforce the control's behavior without adding clutter.

**Visual fix needed:** Add an inset panel in (a) zoomed to the Global range (y: 0.00–0.15) or use a broken y-axis. Add a thin gray dashed reference line for Random-Benign labeled "control (CI spans 0)."

**Should stay / move / merge / remove:** Stay in main paper after fix.

---

### Table 1: Clean-baseline dispersion statistics
**Grade: 5.0 / 10**

**What it communicates:** Policy comparison on baseline fairness metrics (CV(FPR), CV(TPR), Worst BA, P10, Macro-F1).

**What is confusing:**
- "Worst BA" is never defined. It appears to be the Worst-case Balanced Accuracy — if so, define it. In what sense is it "worst"? Worst across seeds? Worst across devices? Worst across attack conditions?
- "P10" is undefined. 10th percentile of what?
- Cluster Macro-F1 = 0.299 ± 0.000 is suspicious (see W5).
- The bold convention ("Bold marks the best value per metric") is stated in the caption, but for "Worst BA" the "best" direction is ambiguous (higher BA = better detection, but "worst" case means the designer cares about the minimum — so higher Worst BA is better, but the caption doesn't say).

**Visual fix needed:** Define all abbreviations in the caption or in a table footnote. Add a direction indicator (↑ better / ↓ better) for each column. Explain ± 0.000 for Cluster Macro-F1.

**Should stay / move / merge / remove:** Stay in main paper after fix.

---

### Table 2: Main results table
**Grade: 8.0 / 10**

**What it communicates:** The primary results of the paper — threshold shift and downstream detection harm for all policy × attack × fraction combinations.

**What is confusing:**
- The f=0.0 baseline (clean, no poisoning) is not shown as a row, making it harder to contextualize absolute harm without reading §5.1.
- The Random-Benign control is described in the caption footer but not shown as rows. At minimum, add one row per policy for f=0.4 Random-Benign showing ΔCI spans zero, G1 ≤ 30%.
- ΔTPR for Global: it is unclear from the table whether this is the per-victim ΔTPR (only the poisoned client's detection rate) or the federation-average ΔTPR. The text in §5.2 suggests it is the per-victim value, but the paper also states that Global propagates the poisoned threshold to all 9 clients — which raises the question of whether the 9-client-average harm is reported or just the originally poisoned client's harm.

**Visual fix needed:** Add f=0.0 rows as a clean baseline reference. Add Random-Benign control rows. Add a footnote clarifying "ΔTPR (pp)" measurement scope for Global.

**Should stay / move / merge / remove:** Stay in main paper.

---

## 11. Visual and Formatting Review

**Page layout (LNCS format):** Correct. 13 pages including references is within typical LNCS conference page budget (15 pages).

**Font sizes:** Adequate in body text. Figure 1's internal box text is small. Table 1 and Table 2 appear at appropriate font size.

**Equations:** Cleanly formatted. The Gate-1 formula for δτ_v is typeset correctly with nested max() and IQR().

**Algorithm formatting:** The attack mechanism (Replace-Fixed-Budget) is described in prose, not as a pseudocode block. For a methods paper, an algorithm box would improve clarity and directly answer "how exactly is the injection performed?" in one scannable block.

**Section balance:** Introduction (1 page), Background (0.8 page), Threat Model (1.3 pages), Experimental Protocol (1.5 pages), Results (3 pages), Discussion (1.5 pages), Conclusion (0.5 page), References (2 pages). The Results section is appropriately dominant. The Discussion is adequately long for a limitations paper.

**Abbreviations:** The paper introduces abbreviations (CV, IQR, BA, G1, G2, G3, AUROC, CI, pp) without a glossary. Most are standard, but "BA" (Balanced Accuracy) and "pp" (percentage points) should be defined on first use.

**Color consistency across figures:** Figure 2 uses orange/blue for Local/Global. Figure 3 uses blue/orange/green for Global/Local/Cluster. The color assignment is different between Figure 2 and Figure 3 — in Figure 2, blue = Global; in Figure 3, blue = Global (consistent), orange = Local (consistent). This appears consistent on inspection, but the legend in Figure 3 should be confirmed against Figure 2's color scheme.

**Spacing:** No visible typesetting errors. Section headers are correctly formatted.

**Page budget:** Tight but not over budget. Fixes (architecture specification, algorithm box, Table 1 fixes) will add approximately 0.5–1 page. The authors should plan for this.

---

## 12. Related Work and Novelty Review

### Missing or Weakly Handled Related-Work Risks

1. **Reference [12] (L'heureux 2017) is the wrong paper for the cited claim** — this is a blocking issue, as described in W3.
2. **No 2023–2024 citations** — in a submission to a 2025/2026 venue, this is conspicuous.
3. **Threshold calibration in anomaly detection literature** — there is a body of work on threshold selection for deep anomaly detectors (e.g., Perera et al. 2019, Ruff et al. 2021) that the paper does not engage. Reviewers with this background may challenge the novelty of manipulating a quantile-based threshold.
4. **Conformal prediction and coverage guarantees** — conformal anomaly scores are increasingly used in federated settings and represent an adjacent mechanism that could either mitigate or be exploited by calibration-stage poisoning. Not mentioning conformal prediction will appear as a gap to reviewers from that community.
5. **Calibration poisoning in non-federated settings** — [11] (Kloft & Laskov 2012) is cited but the comparison is shallow. The paper should explicitly contrast the centralized setting (where a server can sanitize calibration data) with the federated setting (where calibration data never leaves the client).

### Closest-Work Comparison Table (the paper should include this)

| Work | Setting | Attack phase | Score-level? | Policy-aware? | Federated? |
|---|---|---|---|---|---|
| Kloft & Laskov 2012 [11] | Centralized | Training (online) | Yes | No | No |
| Cretu et al. 2008 [7] | Centralized | Training | No | No | No |
| Bagdasaryan et al. 2020 [1] | Federated | Training | No | No | Yes |
| Tolpegin et al. 2020 [19] | Federated | Training | No | No | Yes |
| **This paper** | Federated | Post-training calibration | Yes | Yes | Yes |

**Novelty score: 7.0 / 10.** The novelty is real and defensible. The paper is the first to characterize the calibration stage as a federated, policy-dependent attack surface. The score-level limitation and single-dataset scope prevent a higher novelty assessment.

**Safe novelty statement (to use verbatim in the paper):** "To our knowledge, this is the first work to systematically characterize the post-training threshold-calibration stage as a policy-dependent attack surface in federated IoT anomaly detection, showing that policy choice determines not just attack magnitude but blast radius — findings that are not predictable from training-phase or centralized-setting theory."

---

## 13. Reproducibility Checklist

**Reproducibility grade: 3.5 / 10**

| Item | Status | Severity if missing |
|---|---|---|
| Dataset name and source (N-BaIoT, [15]) | ✅ Provided | — |
| Per-device calibration set sizes | ✅ Provided (2,622–9,909) | — |
| Injection fractions {0.0, 0.1, 0.2, 0.4} | ✅ Provided | — |
| Threshold quantile q=0.95 | ✅ Provided | — |
| K-means parameters (K=3, k-means++, random_state=42) | ✅ Provided | — |
| Seed structure (i, i+100, i+300) | ✅ Provided | — |
| Bootstrap parameters (B=10,000, percentile, 95%) | ✅ Provided | — |
| Gate-1/2/3 definitions | ✅ Provided | — |
| Tail reservoir definition (top/bottom 10%) | ✅ Provided | — |
| Replace-Fixed-Budget mechanism | ✅ Provided | — |
| **Autoencoder architecture** | ❌ Missing | **Fatal** |
| **FedAvg hyperparameters (rounds, epochs, LR, batch, optimizer)** | ❌ Missing | **Fatal** |
| **Data preprocessing and normalization** | ❌ Missing | **Fatal** |
| **Train/calibration/test split protocol** | ❌ Missing | **Major** |
| **What exactly is federated (global model? local models?)** | ❌ Ambiguous | **Major** |
| Code or pseudocode for attack implementation | ❌ Missing | **Major** |
| Code or pseudocode for gating analysis | ❌ Missing | **Major** |
| Pre-trained model weights or checkpoint | ❌ Not offered | Moderate |
| Artifact availability statement | ❌ Not stated | Moderate |
| Hardware/software environment | ❌ Not stated | Moderate |
| Gate-1 constant pre-specification documentation | ❌ Not stated | Moderate |
| K-means++ citation (Arthur & Vassilvitskii 2007) | ❌ Missing | Minor |

**Minimum artifact checklist before submission:**
- [ ] Full autoencoder specification (at minimum: layer count, hidden dimensions, activation, loss)
- [ ] FedAvg training protocol (rounds, local epochs, learning rate, batch size, optimizer)
- [ ] Data preprocessing pipeline (feature selection, normalization)
- [ ] Train/calibration/test split construction
- [ ] Clarification of what the federation shares (global vs. personalized model)
- [ ] Pseudocode or algorithm box for Replace-Fixed-Budget mechanism
- [ ] Statement of whether code will be released (even "Code available upon request" is acceptable)
- [ ] Software environment (Python version, framework, key library versions)

---

## 14. Action Plan to Reach 10/10

### Must Fix Before Submission (blocking issues)

1. **Add model and training specification.** Insert a complete paragraph in §4.1 specifying: autoencoder architecture (encoder layers and dimensions, bottleneck dimension, decoder layers, activation, reconstruction loss), FedAvg configuration (number of rounds, local epochs per round, learning rate, batch size, optimizer, client aggregation weighting), and what is shared globally vs. kept local. Without this, the paper cannot be accepted at any peer-reviewed venue.

2. **Resolve the "4 source-objective pairs" inconsistency (§4.3).** Either enumerate all four pairs explicitly (the most likely explanation is: Raise+High-Score, Lower+Low-Score, Raise+Random-Benign-control, Lower+Random-Benign-control), or correct "4" to "3" and adjust the total from 4,320 to 3,240.

3. **Replace Reference [12] (L'heureux 2017).** It does not support the cited claim. Replace with a paper specifically about threshold sensitivity in anomaly detection. Kloft & Laskov 2012 [11] is already in the bibliography and is closer; alternatively, identify a recent paper on anomaly threshold selection.

4. **Define P10 and Worst BA in Table 1.** Add a footnote or caption definition. Add direction indicators (↑/↓ better).

5. **Explain Cluster Macro-F1 = 0.299 ± 0.000.** If cluster assignments are stable across all seeds (likely, given N-BaIoT device separation), state this explicitly as the mechanism. If it is a reporting error, fix it.

6. **Clarify Figure 2 as single-seed.** Add to the caption: "(Seed 0; device ordering is stable across all 10 seeds — full cross-seed FPR is summarized in Table 1 CV(FPR) statistics.)" or replace with a mean-across-seeds visualization.

7. **Fix N notation conflict in §6.** Rename the calibration set size variable to n_v or |C_v| to eliminate the conflict with N=9 (number of federation clients).

8. **Add adversary policy-knowledge assumption in §3.** One sentence: "The adversary is assumed to know the federation's threshold-aggregation policy; a policy-blind variant is future work."

9. **Add data preprocessing and train/calibration/test split description.** At minimum: how are raw N-BaIoT features preprocessed? Is the calibration data disjoint from training data?

### Should Fix If Page Budget Allows (major improvements)

10. **Add algorithm box for Replace-Fixed-Budget.** A 5-line pseudocode block in §3 or §4 would replace two paragraphs of prose and make the attack mechanism immediately clear to any reviewer.

11. **Add f=0.0 rows and Random-Benign control rows to Table 2.** This gives the reader absolute context and confirms the negative control is properly captured.

12. **Add BCa bootstrap CI caveat.** In §4.4, acknowledge that n=10 percentile bootstrap CIs may undercover at the 95% level. Consider reporting BCa CIs in parallel, or at least stating that the directional findings are robust even if the precise interval widths are approximate.

13. **Add a closest-work comparison table to §2.** A 4-column table (Setting / Attack phase / Score-level / Federated) contrasting this paper against [1], [7], [11], [19] would sharpen the novelty claim and preempt reviewer objections.

14. **Fix Figure 3, panel (a): make Global visible.** Add a zoomed inset or secondary y-axis for Global. Add a thin gray dashed reference line for the Random-Benign control labeled "control (CIs span zero)."

15. **Add derivation for the "30–80 undetected Mirai flows" claim** or remove it. If derivable, a one-sentence footnote is sufficient.

16. **Add Gate-1 constant pre-specification statement.** Add: "These constants were set before any poisoning experiments were run, based on the criterion that a shift smaller than 10% of the device's own score IQR should not be counted as materially harmful."

17. **Add 2–3 recent (2023–2024) FL-IoT security references** to §2 to update the bibliography and demonstrate awareness of recent developments.

18. **Cite Arthur & Vassilvitskii 2007 for k-means++.**

### Nice to Fix (polish)

19. Define all abbreviations on first use: BA (Balanced Accuracy), pp (percentage points), CV (coefficient of variation).
20. Add a brief harm scenario to the Introduction (2 sentences) to make the problem vivid.
21. Add explanation for the Cluster raising-attack ΔTPR plateau at f=0.2 (§5.2).
22. Clarify "match the aggregation design" in the Conclusion with a concrete example.
23. Clarify "evading requires score perturbation at the cost of leaving the exact tail boundary" in §6.
24. Rephrase the "gray-box" model in §3 to more precisely describe what the adversary controls.

### Do Not Touch — Already Strong

- The three-gate framework with a negative control. It is methodologically sound and adds credibility. Do not simplify or remove it.
- The scope boundary language. The paper's discipline in stating what it does not claim is exemplary. Do not weaken it.
- The policy-differentiated summary in §5.4. It is clear, accurate, and the most cited-ready part of the paper.
- The detectability disclosure (duplicate scores at f=0.4). This level of honesty about an attack's limitations is rare and improves reviewer trust.
- The AUROC invariance sanity check across all 4,320 cells. This is a gold-standard protocol check. Do not remove it.
- The paired-seed design (training i, poisoning i+100, analysis i+300). This is thoughtful and should be highlighted, not buried.

---

## 15. Final Reviewer Simulation

---

### Reviewer 1 — Supportive Expert Reviewer
**Score: 6 / 10 (Weak Accept)**

**Summary:** "This paper addresses a real and underexplored attack surface in federated anomaly detection. The framing is careful, the scope limitations are honestly stated, and the three-gate analysis with a negative control is methodologically responsible. The policy-differentiated vulnerability profile is a genuine and useful contribution. However, the reproducibility is insufficient: the autoencoder architecture and FedAvg training protocol are not specified, and I cannot reproduce a single experimental cell from the information provided. I also note that 'n=10 bootstrap CIs' at the 95% level have known coverage issues, and the paper does not acknowledge this. With these issues fixed, this is a publishable contribution."

**Main objections:** Missing architecture; missing training protocol; n=10 coverage caveat missing.

**Questions:** "What is the autoencoder architecture? What are the FedAvg training parameters? Were the Gate-1 constants set before or after observing results? What are P10 and Worst BA in Table 1?"

**Current answer in paper:** None for architecture; partial for Gate-1. **Sufficient? No.**

**What would neutralize:** Add §4.1 model specification paragraph and a pre-specification statement for Gate-1 constants.

---

### Reviewer 2 — Skeptical Methods Reviewer
**Score: 4 / 10 (Weak Reject)**

**Summary:** "The experimental design contains multiple unexplained design choices that appear arbitrary or potentially result-driven. The Gate-1 materiality formula uses constants (0.1, 0.01) with no prior justification. The victim-majority condition (≥5/9) is simple majority with no rationale. The bootstrap confidence intervals rest on n=10 — a sample size that makes percentile CIs unreliable at 95%. The paper claims '4 source-objective pairs' but describes only 3, and the cell count formula cannot be verified. Additionally, Table 1 reports a zero standard deviation for a metric that the paper says varies across seeds due to cluster-assignment variability — this is either a data error or an unexplained coincidence. The autoencoder architecture is absent, making the experiment unreproducible. I acknowledge the paper's honest scope framing, but the methodological documentation is insufficient for a research paper."

**Main objections:** n=10 bootstrap reliability; unjustified Gate-1 constants; "4 source-objective pairs" inconsistency; Table 1 zero variance; missing architecture.

**Questions:** "How were 0.1 and 0.01 chosen for the Gate-1 formula? Were they chosen before or after results were observed? What is the fourth source-objective pair? Why does Cluster Macro-F1 have zero variance? Are BCa CIs available?"

**Current answer in paper:** None. **Sufficient? No.**

**What would neutralize:** Pre-specification statement for Gate-1 constants; enumerate all 4 pairs; explain ± 0.000; provide BCa CIs or caveat.

---

### Reviewer 3 — Security / Adversarial ML Reviewer
**Score: 5 / 10 (Borderline)**

**Summary:** "The paper identifies an interesting attack surface: the calibration stage is indeed structurally isolated from training-phase defenses, and the policy-dependent blast radius is an insightful observation. However, the attack is implemented at the score level only. The adversary controls the client — meaning they have full access to the client's execution environment — yet the paper restricts the attack to programmatic score injection rather than traffic generation. This raises the obvious question: if an adversary controls the client, can they not also perform more damaging model poisoning? The paper argues that calibration poisoning bypasses model-level defenses, but a reviewer can ask why a rational adversary who controls the client would prefer this limited attack over directly poisoning gradients. This question is not answered. Additionally, the paper does not address why a policy-blind adversary (who does not know whether the federation uses Global, Local, or Cluster) would or would not attempt this attack. The detection analysis (duplicate score collision problem) is correctly disclosed but the mitigation discussion is thin. Overall, the contribution is interesting but the paper needs to better justify why this adversary model (score-level, single-client, policy-aware) is a realistic threat scenario."

**Main objections:** Why score-level instead of model poisoning? Why would a rational adversary choose this? No traffic-level demonstration. Adversary policy-knowledge assumption unstated.

**Questions:** "If the adversary controls the client and could also perform model poisoning, what makes calibration-stage poisoning the preferable or necessary attack vector? Is there a setting where the adversary has calibration buffer access but not model weight access? Can you show at least one example of naturally occurring tail scores in N-BaIoT traffic to support the realizability of the injection model?"

**Current answer in paper:** The paper argues temporal isolation and defense bypass — this is a strong argument but is not explicitly directed at the rational-adversary question. **Sufficient? Partially.** Add one paragraph in §3 directly addressing: "An adversary who controls the client has multiple attack options; we focus on calibration-stage poisoning because it (a) operates after all training-phase defenses complete, (b) requires no gradient injection or model modification — making it potentially undetectable by defenses that monitor only the training loop, and (c) is effective even against gradient-level defenses like differential privacy."

---

### Reviewer 4 — Presentation / Clarity Reviewer
**Score: 6 / 10 (Borderline Accept)**

**Summary:** "The paper is clearly written overall, with good use of precise terminology and honest limitation disclosure. However, several presentation issues reduce clarity and professional quality. Figure 2 shows only seed 0 without explicit justification. Table 1 uses undefined abbreviations (P10, Worst BA). The Global line in Figure 3(a) is nearly invisible due to the y-axis scale. The Random-Benign control is mentioned in figure captions but never plotted, leaving readers to take on faith that it is flat. The 'N notation conflict' in §6 (using N for both federation size and calibration set size) causes real confusion in the collision count formula. The 'gray-box' label for the adversary model is inconsistent with the description of the adversary 'controlling the client.' These are fixable issues that do not undermine the science but will be visible to a camera-ready reviewer."

**Main objections:** Table 1 undefined abbreviations; Figure 2 single-seed; Figure 3 Global visibility; N conflict; gray-box inconsistency.

**Questions:** "What do P10 and Worst BA mean? Why is Random-Benign not plotted? Why does N in §6 refer to calibration set size when N=9 is used for federation size throughout the rest of the paper?"

**Current answer in paper:** None. **Sufficient? No.**

**What would neutralize:** Define all abbreviations in Table 1 caption; fix Figure 3 scale; add Random-Benign reference line; fix N notation.

---

### Consolidated Verdict

The paper is **not currently submission-ready** for any competitive security venue (USENIX Security, CCS, IEEE S&P) and is **borderline** for mid-tier venues (ESORICS, RAID). It is **almost ready** (one revision round) if the five must-fix items — architecture specification, "4 source-objective pairs" resolution, reference [12] replacement, Table 1 abbreviations, and Cluster Macro-F1 ± 0.000 explanation — are addressed. The scientific contribution is real, the scope discipline is exemplary, and the policy-differentiated vulnerability profile is a genuine finding. The paper's weaknesses are documentation and statistical scaffolding deficiencies, not flawed science. After one focused revision round targeting the fatal and major items, the paper's expected grade rises to approximately **7.5–8.0 / 10**, placing it in weak-accept territory at ESORICS-level venues.