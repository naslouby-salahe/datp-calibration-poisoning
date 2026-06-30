# Paper Audit and Review Report

I reviewed the full 13-page paper PDF and used your attached audit rubric as the review structure.  

## 1. Executive Verdict

**Overall grade: 8.2 / 10**

**Recommendation: Weak Accept / Borderline Accept**, depending on venue strength.

**One-paragraph verdict:**
This is a strong, focused, and unusually claim-disciplined paper. The core scientific contract is mostly clear: the paper studies **score-level calibration-channel poisoning** after FL training, not model poisoning, not gradient poisoning, not raw-traffic attack deployment, and not a general secure-FL defense paper. The paper’s biggest strength is that it isolates a narrow but real-looking blind spot in federated IoT anomaly detection: post-training threshold calibration. The biggest weakness is that the attack remains a **score-level proxy** with acknowledged detectability through duplicate scores, and the experimental section still lacks enough architectural, preprocessing, artifact, and per-victim detail for a harsh reviewer to feel fully confident. It is close to submission-ready, but not yet bulletproof.

**Main reason to accept:**
The paper has a crisp, differentiated contribution: the same calibration contamination mechanism behaves differently under Global, Local, and Cluster threshold policies, producing a useful security-design trade-off rather than just “attack works.”

**Main reason to reject:**
A skeptical reviewer may say the paper demonstrates a **programmatic score-buffer manipulation artifact**, not a realizable poisoning attack, and that the missing reproducibility details make it hard to verify the claimed effects independently.

**Fastest path to improve:**
Add one compact reproducibility/protocol table, expose the Random-Benign negative-control results numerically, add per-victim/spillover evidence, clarify the ambiguous “4 source-objective pairs,” and tighten the abstract/lowering-attack wording.

---

## 2. Scorecard

| Category                 | Score | Reason                                                                                                                      |
| ------------------------ | ----: | --------------------------------------------------------------------------------------------------------------------------- |
| Novelty                  |   8.3 | Calibration-stage poisoning is well positioned as a neglected surface, but related work comparison needs more precision.    |
| Technical correctness    |   8.2 | The core protocol is coherent; biggest risk is score-level proxy and missing implementation details.                        |
| Methodological rigor     |   8.0 | Paired seeds, gates, sanity checks, and controls are good; n=10 bootstrap and hidden aggregation details weaken confidence. |
| Experimental support     |   7.8 | Results are strong but too aggregated; Random-Benign and per-victim/spillover evidence need to be surfaced.                 |
| Claim discipline         |   8.8 | Very good scoping; some abstract/conclusion claims still need narrowing.                                                    |
| Related work positioning |   7.0 | Adequate but not reviewer-proof; closest-work comparison is missing.                                                        |
| Reproducibility          |   6.5 | Seeds and attack config are present, but model, splits, preprocessing, code/artifacts, and environment are incomplete.      |
| Visual presentation      |   7.2 | Professional overall, but Figure 2, Figure 3, and Table 2 need improvement.                                                 |
| Writing clarity          |   8.5 | Generally clear and direct; a few terms could confuse reviewers.                                                            |
| Reviewer-proofness       |   7.6 | Strong foundation, but several predictable reviewer objections remain.                                                      |

**Final integrated grade: 8.2 / 10**

---

## 3. Top Strengths

1. **Clear scientific contract.**
   The paper repeatedly states that the attack touches the calibration buffer only, leaving training data, model weights, gradients, test scores, and test labels unchanged. This is exactly the right discipline.

2. **Narrow but defensible contribution.**
   The paper does not try to be a generic “secure FL” paper. It focuses on one overlooked channel: threshold calibration.

3. **Policy-differentiated results are valuable.**
   The Global/Local/Cluster comparison is not cosmetic. It gives a real design trade-off: Local maximizes victim-specific exposure, Global dilutes but propagates harm, and Cluster creates intra-cluster spillover.

4. **Good sanity-check framing.**
   AUROC invariance, unchanged score ranks, and unchanged model weights are correctly presented as protocol checks, not as headline contributions.

5. **Honest limitations.**
   The paper openly admits score-level proxy limitations, duplicate-score detectability, lack of traffic-level realizability, and bounded generalization.

6. **Good attack/control separation.**
   High-Score-Benign, Low-Score-Benign, and Random-Benign are conceptually clean.

7. **Readable paper structure.**
   The paper is easy to follow: threat model, protocol, policies, gates, results, limitations.

---

## 4. Top Weaknesses

| Rank | Weakness                                                                                    | Severity       | Exact location                                            | Why it matters                                                                        |
| ---: | ------------------------------------------------------------------------------------------- | -------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------- |
|    1 | Score-level attack may be viewed as too synthetic                                           | Near-fatal     | Abstract; §3 pp. 3–5; §6 pp. 9–10                         | A harsh reviewer may reject the attack as not traffic-realizable.                     |
|    2 | Missing reproducibility details: model architecture, preprocessing, splits, hyperparameters | Major          | §4.1 pp. 5–6                                              | Another researcher cannot fully reproduce the results from the paper.                 |
|    3 | Random-Benign control is described but not numerically shown                                | Major          | §4.4 p. 6; §5.2 p. 7; Table 2 p. 11                       | The negative control is central to causal interpretation; it needs visible evidence.  |
|    4 | “4 source-objective pairs” is ambiguous                                                     | Major          | §4.3 p. 5                                                 | The attack matrix is not fully specified. Reviewers will ask what the four pairs are. |
|    5 | Lowering attack harm is easy to misunderstand                                               | Major          | Abstract p. 1; §5.3 p. 8; Table 2 p. 11; Conclusion p. 12 | Positive ΔTPR sounds like improvement unless FPR/alarm burden is foregrounded.        |
|    6 | Per-victim and non-victim spillover evidence is too thin                                    | Major          | §5.2 pp. 7–8; §5.4 p. 8                                   | Global/Cluster spillover is a key claim but not directly tabled.                      |
|    7 | Bootstrap over only 10 seed-level aggregates needs stronger caveat or supplement            | Moderate/Major | §4.4 p. 6; §6 p. 10                                       | n=10 percentile bootstrap can be fragile; reviewer confidence may drop.               |
|    8 | Related work does not fully lock down closest prior art                                     | Moderate/Major | §2 p. 3                                                   | “To our knowledge” novelty claim needs more protection.                               |
|    9 | Figure 2 is visually weak and only shows seed 0                                             | Moderate       | Figure 2 p. 9                                             | It supports baseline fairness but lacks seed variability and excludes Cluster.        |
|   10 | Table 2 float/layout creates a weak visual impression                                       | Moderate       | Table 2 p. 11                                             | Large white space and dense table hurt camera-ready professionalism.                  |

---

## 5. Fatal or Near-Fatal Risks

### Risk 1 — “This is not a real attack; it is score-array editing.”

**Location:** Abstract; §3 Threat Model; §6 Discussion and Limitations.
**Reviewer objection:** The attacker replaces reconstruction scores directly. In a deployed IDS, the attacker would need to generate traffic that produces those scores.
**Current paper answer:** The paper admits this is score-level and future work.
**Is it enough?** Mostly, but not fully.
**Fix:** Add one explicit sentence in the abstract and threat model:

> “This is a vulnerability-characterization experiment over the calibration-score channel, not a traffic-generation attack.”

Also add a small “Why score-level still matters” paragraph: calibration scores are the direct input to threshold computation; isolating this channel identifies a vulnerability independent of training.

### Risk 2 — “The attack is trivially detectable because of duplicate scores.”

**Location:** §6 p. 9–10.
**Reviewer objection:** At f=0.4, the paper estimates about 2,100 expected collision pairs for the smallest calibration set. That sounds like a broken attack.
**Current paper answer:** The paper discloses detectability and says evasion is open.
**Is it enough?** Good honesty, but reviewer risk remains high.
**Fix:** Either add a no-duplicate sensitivity check, or downgrade language from “attack succeeds” to “score-channel vulnerability exists under the controlled replacement model.” Even one small experiment using without-replacement sampling or tiny jittered scores would greatly reduce this risk.

### Risk 3 — Reproducibility gap.

**Location:** §4.1–§4.4.
**Reviewer objection:** The paper does not specify enough about AE architecture, features, normalization, train/calibration/test split, optimizer, learning rate, batch size, local epochs, FedAvg rounds, or software.
**Current paper answer:** Seeds, policies, fractions, quantile, and attack mechanism are specified.
**Is it enough?** No.
**Fix:** Add a compact reproducibility table.

### Risk 4 — Negative control hidden in prose.

**Location:** §5.2 p. 7; Table 2 p. 11.
**Reviewer objection:** You claim Random-Benign spans zero, but do not show its numbers.
**Current paper answer:** Prose and Table 2 caption mention it.
**Is it enough?** No for a harsh methods reviewer.
**Fix:** Add a Random-Benign mini-table or one extra row group in Table 2.

---

## 6. Section-by-Section Review

### Title

**Grade: 9 / 10**

**What works:**
The title is accurate, scoped, and signals the actual contribution: threshold-calibration poisoning and policy-differentiated vulnerability.

**Unclear/missing:**
Nothing major.

**Overclaimed:**
No.

**Reviewer may ask:**
Does “poisoning” imply traffic-level poisoning or score-level manipulation?

**Exact fix:**
Optional: change to **“Score-Level Poisoning of the Threshold-Calibration Stage…”** if you want maximum precision.

**Priority:** Minor.
**Submission-ready:** Yes.

---

### Abstract

**Grade: 8.2 / 10**

**What works:**
Strong problem framing. It clearly says post-training calibration is outside training defenses. Results are concrete: 2.4–7.9 pp victim TPR degradation, 100% Gate-1 pass rate, and policy-specific behavior.

**Unclear:**
“Gate-1 pass rate” appears before the reader knows what Gate 1 means.
“Detection-rate increase” for lowering sounds beneficial unless the alarm-burden/FPR harm is foregrounded.

**Missing:**
The abstract should explicitly say this is **score-level vulnerability characterization**, not a deployed traffic attack.

**Overclaimed:**
“Federated learning defenses… focus on the training phase” is directionally true but broad. Safer: “Most existing FL defenses considered in this work…”

**Reviewer may ask:**
Is this attack realizable from raw traffic? Are scores directly modifiable in a real deployment?

**Exact fix:**
Add one phrase:

> “We study a controlled score-level vulnerability model, not traffic-level exploit generation.”

Rewrite lowering sentence:

> “The lowering attack shifts thresholds downward for Local and Cluster, increasing alarm burden as reflected by ΔCV(FPR)=0.05–0.06; the associated ΔTPR increase is reported only as an operating-point displacement indicator.”

**Priority:** Major.
**Submission-ready:** Almost.

---

### Introduction

**Grade: 8.6 / 10**

**What works:**
The “undefended phase” framing is good. The three-axis distinction from ordinary data poisoning is strong: temporal isolation, phase-specific trust model, and policy-dependent effects.

**Unclear:**
The sentence “What existing defenses collectively ignore…” may be read as universal over all defenses.

**Missing:**
A short statement that calibration integrity is often assumed implicitly, not always explicitly absent.

**Overclaimed:**
“Every defense that monitors the training or aggregation loop” is safe only for training/aggregation defenses, not for all possible FL security defenses.

**Reviewer may ask:**
Is this really new, or just poisoning validation/calibration data?

**Exact fix:**
Add a sentence near the end of the introduction:

> “The novelty is not that thresholds depend on calibration data; it is the policy-dependent propagation behavior created when independently calibrated clients later aggregate or share thresholds.”

**Priority:** Moderate.
**Submission-ready:** Yes after small edits.

---

### Contributions

**Grade: 8.5 / 10**

**What works:**
The contributions are scoped and measurable. Contribution 2 includes quantitative results. Contribution 3 captures the strongest part of the paper.

**Unclear:**
Contribution 1 says “undefended attack surface” but the paper does not test defenses. Better: “outside the scope of common training/aggregation-phase defenses.”

**Missing:**
No contribution explicitly says the paper provides an isolation/sanity-check protocol proving the intervention is calibration-only.

**Overclaimed:**
“Undefended” can sound universal.

**Reviewer may ask:**
Is “undefended” empirically shown or argued structurally?

**Exact fix:**
Revise contribution 1:

> “We isolate the post-training threshold-calibration stage as an attack surface structurally outside common training- and aggregation-phase defenses.”

**Priority:** Moderate.
**Submission-ready:** Almost.

---

### Related Work

**Grade: 7 / 10**

**What works:**
The categories are logical: FL anomaly detection, defenses, threshold calibration/poisoning, threshold policies.

**Unclear:**
The closest prior work is not singled out sharply enough. The paper says “to our knowledge” but does not include a compact comparison showing what prior work lacks.

**Missing:**
Likely missing or weakly handled areas:

| Area                                             | Why it matters                                                          |
| ------------------------------------------------ | ----------------------------------------------------------------------- |
| Calibration/validation poisoning                 | Reviewers may classify this as validation-set poisoning.                |
| Conformal/calibration attacks                    | Even if not the same, “calibration” security literature may be noticed. |
| Threshold manipulation in IDS/anomaly detection  | Needed to defend novelty.                                               |
| Robust thresholding / robust quantile estimation | Relevant even if defenses are out of scope.                             |
| Federated personalization security               | Important for Local/Cluster policy framing.                             |

**Overclaimed:**
“No prior work characterizes…” may be true, but it needs a stronger closest-work comparison.

**Reviewer may ask:**
What is the nearest paper to this one, and exactly why is yours different?

**Exact fix:**
Add a 4-row related-work comparison table:

| Prior area | Attack surface | FL? | Threshold policy? | Calibration-only? | This paper differs by |
| ---------- | -------------- | --: | ----------------: | ----------------: | --------------------- |

**Priority:** Major.
**Submission-ready:** Needs improvement.

---

### Threat Model

**Grade: 8.7 / 10**

**What works:**
Very good boundary discipline. The paper states the adversary controls one client, modifies local calibration scores, and does not touch model weights, gradients, other clients’ data, test data, test labels, or training labels.

**Unclear:**
The paper uses “victim” to mean the poisoned client under Local, but under Global harm propagates to all clients. This terminology can confuse.

**Missing:**
A short trust-boundary diagram/table would help: what attacker can and cannot modify.

**Overclaimed:**
“This is a strictly weaker capability than model-poisoning adversaries” is mostly right regarding gradient injection, but direct score-buffer modification is a different capability, not necessarily strictly weaker in all deployments.

**Reviewer may ask:**
Why can the attacker modify the calibration buffer but not the test data or model? Is this a realistic client compromise?

**Exact fix:**
Add a capability table:

| Object                   | Can attacker read? | Can attacker modify? |
| ------------------------ | -----------------: | -------------------: |
| Local calibration scores |                Yes |                  Yes |
| Training data            |                 No |                   No |
| Model weights            |                 No |                   No |
| Gradients/updates        |                 No |                   No |
| Test scores/labels       |                 No |                   No |
| Other clients            |                 No |                   No |

**Priority:** Moderate.
**Submission-ready:** Strong, with small terminology fix.

---

### Methodology / Experimental Setup

**Grade: 7.4 / 10**

**What works:**
The policy definitions are clear. The fractions, quantile, seed pairing, and single-client sweep are specified.

**Unclear:**
The phrase “4 source-objective pairs” is not defined. The paper mentions High-Score-Benign Raise, Low-Score-Benign Lower, and Random-Benign. That is not obviously four pairs.

**Missing:**
Model and training details are insufficient:

| Missing item                                       | Location where needed             |
| -------------------------------------------------- | --------------------------------- |
| AE architecture                                    | §4.1                              |
| Input features and preprocessing                   | §4.1                              |
| Normalization/scaling                              | §4.1                              |
| Train/calibration/test split construction          | §4.1                              |
| FedAvg rounds/local epochs/batch size/lr/optimizer | §4.1                              |
| Client sample counts beyond calibration sizes      | §4.1                              |
| Hardware/software                                  | Reproducibility/artifacts section |

**Overclaimed:**
No major overclaim, but “full configuration” is not actually full.

**Reviewer may ask:**
Can I reproduce your 4,320 cells from the paper alone?

**Exact fix:**
Add **Table 0: Experimental Configuration** before results.

**Priority:** Major.
**Submission-ready:** Not fully.

---

### Dataset

**Grade: 7.6 / 10**

**What works:**
N-BaIoT is appropriate and the nine-device federation is clearly defined. Calibration sizes are given.

**Unclear:**
Device class composition and benign/attack split details are missing.

**Missing:**
Exact N-BaIoT variant/source, feature set, preprocessing, train/test/calibration partitions, and whether Mirai/BASHLITE attacks are pooled or separately evaluated.

**Overclaimed:**
No broad dataset generalization is made; that is good.

**Reviewer may ask:**
Are the calibration benign samples disjoint from training benign samples? Are attack samples only in test?

**Exact fix:**
Add one paragraph:

> “For each client, benign samples were partitioned into train/calibration/test as follows… Attack samples were used only for evaluation…”

**Priority:** Major.
**Submission-ready:** Needs detail.

---

### Metrics

**Grade: 7.8 / 10**

**What works:**
Δτ, ΔTPR, CV(FPR), ΔCV(FPR), worst BA, and P10 Macro-F1 are relevant. The paper correctly treats AUROC invariance as a sanity check.

**Unclear:**
For the lowering attack, ΔTPR is a displacement indicator, but the real harm is FPR/alarm burden. Table 2 still foregrounds ΔTPR.

**Missing:**
False-positive rate changes for lowering should be directly tabled, not only ΔCV(FPR) in prose.

**Overclaimed:**
“Detection-rate increase” can sound beneficial.

**Reviewer may ask:**
Why is increased TPR harmful?

**Exact fix:**
For lowering, replace or supplement ΔTPR with:

| Policy |  f | ΔFPR victim | ΔCV(FPR) | Δτ |
| ------ | -: | ----------: | -------: | -: |

**Priority:** Major.
**Submission-ready:** Almost, but needs relabeling.

---

### Statistical Analysis

**Grade: 7.2 / 10**

**What works:**
Gates are explicit. Seed pairing is good. Bootstrap CI over seed-level aggregates is reasonable as a compact approach.

**Unclear:**
Why the materiality threshold is exactly `0.1 × IQR` with a fallback of `0.01 × median IQR` is not justified.

**Missing:**
No sensitivity analysis for gate threshold. No paired statistical test. No direct indication of whether victim variation is included in uncertainty or only seed-level aggregate variation.

**Overclaimed:**
“Statistically distinguishable” based on bootstrap CIs over 10 seeds should be phrased carefully.

**Reviewer may ask:**
Are 10 seeds enough for percentile bootstrap CIs? What is the unit of resampling?

**Exact fix:**
Add:

> “The bootstrap resamples seed-level aggregates, not individual experimental cells; therefore CIs quantify seed-to-seed variability after aggregation over victims.”

Also add a one-sentence caveat in §4.4, not only §6.

**Priority:** Moderate/Major.
**Submission-ready:** Needs clarification.

---

### Results

**Grade: 8.1 / 10**

**What works:**
The results are strong and easy to understand. Table 2 gives concrete effect sizes. Figure 3 supports the policy-differentiated magnitude story.

**Unclear:**
The Global harm story mixes victim-specific and federation-wide effects. It says harm propagates to all federation members, but the table reports victim ΔTPR.

**Missing:**
Need a spillover table:

| Policy | Poisoned client harm | Non-victim mean harm | Max non-victim harm | Spillover count |
| ------ | -------------------: | -------------------: | ------------------: | --------------: |

**Overclaimed:**
“Federation-wide propagation” is plausible from policy design, but the measured downstream harm should be shown.

**Reviewer may ask:**
For Global, are all non-victim clients harmed equally? Are some helped?

**Exact fix:**
Add one compact table or appendix figure showing victim vs non-victim ΔTPR/FPR.

**Priority:** Major.
**Submission-ready:** Good but not bulletproof.

---

### Controls / Ablations

**Grade: 6.8 / 10**

**What works:**
Random-Benign is the correct negative control. AUROC invariance and bitwise model-weight identity are excellent sanity checks.

**Unclear:**
Random-Benign is not shown numerically.

**Missing:**
Possible reviewer-requested ablations:

| Ablation                                 | Why                                                          |
| ---------------------------------------- | ------------------------------------------------------------ |
| Without-replacement sampling             | Addresses duplicate detectability.                           |
| Jittered score replacement               | Tests whether duplicate-free score perturbation still works. |
| Different quantile q                     | Tests whether q=0.95 is special.                             |
| Targeted upper-tail removal for lowering | Clarifies lower-bound nature.                                |
| Per-victim susceptibility ranking        | Shows device heterogeneity.                                  |

**Overclaimed:**
No, but current controls are underexposed.

**Reviewer may ask:**
Does the attack still work without duplicates?

**Exact fix:**
If no new experiment is possible, explicitly label duplicate-free attack as future work and downgrade deployability language.

**Priority:** Major.
**Submission-ready:** Needs at least Random-Benign table.

---

### Discussion and Limitations

**Grade: 9 / 10**

**What works:**
This is one of the strongest sections. The paper honestly discusses score-level proxy, detectability, Global dilution, lowering conditionality, and generalization limits.

**Unclear:**
The duplicate collision estimate is very stark. It may scare reviewers unless followed by a constructive interpretation.

**Missing:**
A short defense of why the score-level experiment is still scientifically meaningful despite detectability.

**Overclaimed:**
No. This section is appropriately careful.

**Reviewer may ask:**
Why should we care if the attack is detectable?

**Exact fix:**
Add:

> “Detectability does not eliminate the vulnerability claim; it means the present replacement mechanism is not stealthy. The result still shows that the calibration-score channel has enough leverage to alter deployed operating points.”

**Priority:** Moderate.
**Submission-ready:** Strong.

---

### Ethics / Reproducibility / Artifacts

**Grade: 5 / 10**

**What works:**
There is a disclosure-of-interests statement.

**Missing:**
No artifact availability statement. No ethics statement. No code/data availability. No environment. No reproducibility checklist.

**Exact fix:**
Add a short section before references:

> “Artifacts and Reproducibility. Code, configuration files, seed lists, and result manifests will be released at … The experiments use N-BaIoT …”

If no public release yet, say:

> “The artifact package includes scripts for generating all tables and figures from saved manifests.”

**Priority:** Major.
**Submission-ready:** Weak.

---

### Conclusion

**Grade: 8.2 / 10**

**What works:**
The conclusion restates the core results and limitations.

**Unclear:**
The lowering attack again risks sounding like improved detection because it mentions increased TPR.

**Missing:**
A stronger final scoped sentence:

> “These findings do not establish traffic-level exploitability; they establish calibration-score-channel leverage under controlled contamination.”

**Overclaimed:**
“Operationally meaningful in IoT deployment contexts” may be a little strong without deployment cost modeling.

**Priority:** Moderate.
**Submission-ready:** Almost.

---

### References

**Grade: 7.2 / 10**

**What works:**
Citations include FedAvg, N-BaIoT, Byzantine robust aggregation, FLTrust, clustered FL, and anomaly detection.

**Weakness:**
Reference [16] is a federated learning healthcare survey, which is not the best support for “FL for IoT anomaly detection.” The related-work basis needs closer IDS/IoT/threshold-calibration work.

**Exact fix:**
Replace or supplement weakly matched citations with closer FL-IDS and anomaly threshold calibration/security papers.

**Priority:** Moderate.
**Submission-ready:** Adequate but not bulletproof.

---

### Appendix

**Grade: 4 / 10**

No appendix is present. That is acceptable only if the venue has strict limits, but the current paper would benefit heavily from supplemental material.

**Needed appendix items:**

| Appendix item                               | Why                                          |
| ------------------------------------------- | -------------------------------------------- |
| Full per-victim results                     | Supports spillover and heterogeneity claims. |
| Random-Benign control table                 | Supports causal attribution.                 |
| Hyperparameter table                        | Reproducibility.                             |
| Cluster assignments by seed                 | Supports Cluster-policy claims.              |
| Sensitivity to q or duplicate-free sampling | Reduces reviewer risk.                       |

---

## 7. Reviewer Questions the Paper Must Already Answer

### Threat model questions

1. Can the attacker directly edit reconstruction scores in a real deployment?
2. Why can the attacker alter calibration but not training or testing?
3. Does the server ever see calibration data?
4. Is the compromised client also the victim?
5. Under Global, who exactly is harmed: the poisoned client, all clients, or both?
6. Are duplicate calibration scores detectable?
7. Is score-level access weaker, stronger, or simply different from model-poisoning access?

### Novelty questions

1. How is this different from validation-set poisoning?
2. How is this different from ordinary anomaly-detector threshold manipulation?
3. Has calibration-set poisoning been studied in conformal prediction or centralized anomaly detection?
4. What is the closest prior work?
5. Is the novelty the attack mechanism, the FL calibration setting, or the policy-differentiated propagation?

### Methodology questions

1. What are the exact four source-objective pairs?
2. Are clean and poisoned runs paired by the same training seed?
3. Are calibration samples disjoint from training and test samples?
4. Are replacement positions sampled uniformly?
5. Are replacement scores sampled with or without replacement?
6. Does the attack preserve calibration set size?
7. Does Cluster recompute clusters after poisoning or only after clean calibration?
8. Are thresholds recomputed from poisoned buffers only?

### Dataset questions

1. Which exact N-BaIoT files/devices are used?
2. Are Mirai and BASHLITE pooled?
3. What are the benign/attack sample counts per client?
4. How are train/calibration/test splits created?
5. Are all nine devices always eligible?

### Metric questions

1. Why is ΔTPR the right harm metric for raising?
2. Why is ΔTPR positive under lowering, and why is that harmful?
3. Why use CV(FPR) rather than mean FPR or max FPR?
4. What is the practical meaning of 0.05–0.06 ΔCV(FPR)?
5. Are Macro-F1 and BA affected by lowering?

### Statistical validity questions

1. Why 10 seeds?
2. Why percentile bootstrap with n=10?
3. What exactly is resampled?
4. Why is Gate-1 threshold set to 0.1 × IQR?
5. Are victims treated as independent observations?
6. Are CIs paired across clean/poisoned conditions?

### Baseline/control questions

1. Where are the Random-Benign numbers?
2. Does f=0 reproduce clean exactly?
3. What happens with without-replacement tail sampling?
4. What happens with q=0.90 or q=0.99?
5. Are results robust to a different Cluster K?

### Reproducibility questions

1. What is the AE architecture?
2. What are FedAvg hyperparameters?
3. What preprocessing is applied?
4. What software versions are used?
5. Is code available?
6. Are result manifests available?
7. Can tables and figures be regenerated?

### Scope and limitation questions

1. Does this generalize beyond N-BaIoT?
2. Does it generalize beyond autoencoders?
3. Does it generalize beyond nine clients?
4. Is traffic-level realizability shown?
5. Is stealth shown?
6. Are defenses evaluated?

### Visual/formatting questions

1. Why is Figure 2 only seed 0?
2. Why is Cluster missing from Figure 2?
3. Why is Random-Benign not plotted in Figure 3?
4. Why does Table 2 occupy a mostly empty page?
5. Are figures readable in printed LNCS format?

---

## 8. Claim Discipline Audit

| Claim                                                      | Location                | Support level                      | Weakness                                     | Safe wording                                                                           | Keep?              |
| ---------------------------------------------------------- | ----------------------- | ---------------------------------- | -------------------------------------------- | -------------------------------------------------------------------------------------- | ------------------ |
| Calibration stage is outside training/aggregation defenses | Abstract, Intro, §3     | Fully supported conceptually       | “Defenses” sounds universal                  | “Outside common training- and aggregation-phase defenses”                              | Yes                |
| Single client score replacement shifts thresholds          | Abstract, §3, §5        | Fully supported                    | Only score-level                             | “Under score-level replacement…”                                                       | Yes                |
| Raising attack achieves 100% Gate-1 pass rate              | Abstract, §5.2, Table 2 | Supported                          | Gate-1 not defined in abstract               | “Under the paper’s Gate-1 criterion…”                                                  | Yes                |
| Raising degrades victim TPR by 2.4–7.9 pp                  | Abstract, §5.2, Table 2 | Supported                          | Aggregation details hidden                   | Keep with “in this protocol”                                                           | Yes                |
| Lowering succeeds for Local and Cluster                    | Abstract, §5.3, Table 2 | Supported                          | Harm metric confusing                        | “Shifts thresholds downward and increases alarm burden indicators…”                    | Yes                |
| Global lowering is structurally bounded                    | Abstract, §5.3          | Mostly supported                   | Only shown under current mechanism/fractions | “Bounded under Replace-Fixed-Budget in this setting”                                   | Yes                |
| Local confines harm to compromised client                  | §5.4                    | Partially supported                | Needs explicit spillover table               | “By policy definition, threshold changes are confined; measured harm should be tabled” | Yes, with evidence |
| Global propagates harm to all members                      | §5.2, §5.4              | Partially supported                | Needs non-victim harm data                   | “Propagates the threshold shift to all members”                                        | Yes, revise        |
| Cluster creates intra-cluster spillover                    | §4.2, §5.4              | Partially supported                | Co-cluster data not shown                    | “Can create intra-cluster spillover” unless measured table added                       | Yes, revise        |
| AUROC is invariant by construction                         | §3, §4.4, §4.5          | Fully supported by protocol        | Should remain sanity check only              | Keep as sanity check                                                                   | Yes                |
| No existing work characterizes this stage                  | §2                      | Ambiguous                          | Needs stronger related-work support          | “We are not aware of prior work that…”                                                 | Yes, soften        |
| Operationally meaningful in IoT deployment                 | §7                      | Partially supported                | No deployment cost model                     | “Potentially operationally meaningful”                                                 | Yes, soften        |
| Policy designer must choose between risk types             | §5.4, §6                | Supported as design interpretation | Needs explicit spillover evidence            | Keep after adding spillover table                                                      | Yes                |
| Defense must address calibration buffer                    | §6                      | Supported as implication           | No defenses tested                           | “Suggests defenses should…”                                                            | Yes, soften        |

---

## 9. Methodology and Experiment Audit

| Issue                                  | Location             | Why it matters                               | Reviewer risk | Fix                                                     | Priority       |
| -------------------------------------- | -------------------- | -------------------------------------------- | ------------- | ------------------------------------------------------- | -------------- |
| Model architecture missing             | §4.1 p. 5            | Cannot reproduce detector                    | High          | Add AE architecture and hyperparameters                 | Major          |
| Preprocessing/splits missing           | §4.1 p. 5            | Leakage risk cannot be ruled out             | High          | Add split and preprocessing table                       | Major          |
| “4 source-objective pairs” undefined   | §4.3 p. 5            | Attack matrix unclear                        | High          | Explicitly list all four pairs                          | Major          |
| Random-Benign not numerically reported | §5.2, Table 2        | Weakens causal claim                         | High          | Add control rows/table                                  | Major          |
| n=10 bootstrap fragile                 | §4.4 p. 6            | CI confidence may be challenged              | Medium        | Clarify resampling unit and add caveat/sensitivity      | Moderate       |
| Materiality threshold arbitrary        | §4.4 p. 6            | Gate-1 may look custom-made                  | Medium        | Justify or add sensitivity                              | Moderate       |
| Lowering harm metric confusing         | §5.3, Table 2        | Reviewer may see positive TPR as improvement | High          | Foreground ΔFPR/ΔCV(FPR)                                | Major          |
| Spillover not directly shown           | §5.2–§5.4            | Policy-differentiation claim underexposed    | High          | Add victim/non-victim harm table                        | Major          |
| Duplicate detectability unresolved     | §6 p. 9–10           | Could undermine attack validity              | High          | Add without-replacement/jitter sensitivity or downgrade | Major          |
| Cluster assignment details incomplete  | §4.2 p. 5            | Cluster results may be hard to reproduce     | Medium        | Add fingerprint formula and assignment table/supplement | Moderate       |
| No artifact statement                  | End matter           | Reproducibility weak                         | Medium        | Add artifact/data availability paragraph                | Major          |
| No defense baseline                    | §6 says out of scope | Acceptable but reviewer may ask              | Medium        | Keep out of scope; do not add unless space              | Minor/Moderate |

---

## 10. Figures and Tables Audit

### Figure 1 — Attack surface diagram, page 7

**Grade: 8.5 / 10**

**Communicates:**
Training phase is defended; calibration stage is undefended; adversary acts on score-level calibration buffer.

**Confusing:**
“Training phase defended” could imply all training threats are solved. Better label: “training/aggregation defenses operate here.”

**Visual fix:**
Add “model/test unchanged” as a small annotation.

**Keep/move/remove:**
Keep in main paper.

---

### Figure 2 — Per-client FPR clean baseline, page 9

**Grade: 6.5 / 10**

**Communicates:**
Global has more heterogeneous per-client FPR than Local.

**Confusing:**
Only seed 0 is shown, while the text discusses average CV(FPR) over 10 seeds. Cluster is absent. Device labels are small and angled. The figure is useful but not self-contained enough.

**Visual fix:**
Use a grouped boxplot or dot plot across seeds for Global, Local, and Cluster. At minimum, add Cluster or explicitly state why excluded.

**Keep/move/remove:**
Keep only if improved. Otherwise move to appendix and replace with a cleaner baseline summary figure.

---

### Figure 3 — Mean threshold shift vs injection fraction, page 9

**Grade: 7.6 / 10**

**Communicates:**
Clear policy-dependent threshold shift under raising and lowering. Global is diluted.

**Confusing:**
Random-Benign is central but not plotted. Error bars are small and hard to inspect. Lowering plot could be visually misread without operational-harm context.

**Visual fix:**
Add Random-Benign as a gray dashed/control line or shaded zero-centered CI band. Add a note: “Lowering Δτ shown; operational harm reported via ΔFPR/ΔCV(FPR).”

**Keep/move/remove:**
Keep in main paper, improve.

---

### Table 1 — Clean-baseline dispersion statistics, page 10

**Grade: 8 / 10**

**Communicates:**
Clean baseline policy differences are statistically and practically meaningful.

**Confusing:**
Bold marks best value, but “best” is not obvious for all metrics. For CV(FPR), lower is best; for Worst BA and P10 Macro-F1, higher is best.

**Visual fix:**
Add caption phrase: “For CV metrics lower is better; for BA and Macro-F1 higher is better.”

**Keep/move/remove:**
Keep in main paper.

---

### Table 2 — Threshold shift and detection harm, page 11

**Grade: 7 / 10**

**Communicates:**
This is the central results table. It contains the key numbers needed for the paper.

**Confusing:**
Random-Benign control is only in caption. Lowering rows report ΔTPR, which can be misunderstood. The table occupies a page with large white space and looks visually isolated.

**Visual fix:**
Split into two compact tables: Raising and Lowering. For Lowering, add ΔFPR or ΔCV(FPR). Add Random-Benign summary rows or a separate mini-table.

**Keep/move/remove:**
Keep in main paper, but reformat.

---

## 11. Visual and Formatting Review

**Overall visual grade: 7.2 / 10**

### What looks professional

* LNCS-style layout is clean.
* Title and abstract are readable.
* Equations are generally understandable.
* Tables use consistent formatting.
* Figure 1 has a clear conceptual purpose.
* The paper avoids excessive visual clutter.

### What weakens the visual impression

1. **Page 11 has too much white space around Table 2.**
   This looks like float-placement damage. Fix the table placement or split the table.

2. **Figure 2 is too small for device-level comparison.**
   Device labels are hard to read. Seed-0-only evidence is visually weaker than the text’s 10-seed claim.

3. **Figure 3 should include Random-Benign.**
   The control is too important to leave out of the figure.

4. **No compact protocol table.**
   A one-page methods table would significantly improve reviewer trust.

5. **No artifact/reproducibility box.**
   For a methods/security paper, this absence is noticeable.

6. **Section balance is slightly off.**
   The paper spends reasonable space on limitations, but too little on implementation details.

---

## 12. Related Work and Novelty Review

**Novelty score: 8.3 / 10**

The novelty is real, but it is not yet maximally defended.

### Top related-work risks

1. **Validation/calibration poisoning literature may be missing.**
   A reviewer may say this is validation-set poisoning under another name.

2. **Centralized anomaly threshold attacks may be under-discussed.**
   The paper mentions poisoning anomaly detectors, but should more directly distinguish threshold calibration manipulation.

3. **Robust threshold/quantile estimation is relevant.**
   Even if defenses are out of scope, reviewers may expect awareness.

4. **Federated threshold personalization literature is thin.**
   The Global/Local/Cluster policy taxonomy is central and should be better grounded.

5. **Some current citations are adjacent rather than close.**
   For example, general FL healthcare or generic big-data ML citations are less persuasive than specific FL-IDS/IoT/anomaly threshold works.

### Closest-work comparison table the paper should include

| Work type                         | Similarity to this paper                            | Key difference                                                                    |
| --------------------------------- | --------------------------------------------------- | --------------------------------------------------------------------------------- |
| FL model poisoning                | Attacker compromises FL client                      | Attacks gradients/model updates, not post-training calibration thresholds         |
| Byzantine robust aggregation      | Defends aggregation stage                           | Does not inspect autonomous calibration buffers                                   |
| Centralized anomaly poisoning     | Manipulates data distribution                       | Usually assumes centralized data owner/sanitizer, not client-local FL calibration |
| Threshold calibration sensitivity | Shows thresholds depend on calibration distribution | Does not study adversarial single-client FL policy spillover                      |
| Clustered/personalized FL         | Uses client grouping/personalization                | Usually studies accuracy/personalization, not calibration-channel security        |

### Safe novelty statement

> “To our knowledge, this is the first controlled study of score-level poisoning of the post-training threshold-calibration channel in federated IoT anomaly detection, with explicit comparison of Global, Local, and Cluster threshold policies under a single-client compromise model.”

This is strong but appropriately scoped.

---

## 13. Reproducibility Checklist

**Reproducibility grade: 6.5 / 10**

### Present and good

* Dataset named: N-BaIoT.
* Number of clients: nine physical devices.
* Threshold quantile: q=0.95.
* Policies defined: Global, Local, Cluster.
* Attack fractions: 0.0, 0.1, 0.2, 0.4.
* Attack mechanism: Replace-Fixed-Budget.
* Reservoir: top/bottom 10%.
* Seeds: training, poisoning, analysis seed pairing.
* Bootstrap count: B=10,000.
* Sanity checks: AUROC, score ranks, bitwise model weights.

### Missing or insufficient

| Missing item                                        | Priority   |
| --------------------------------------------------- | ---------- |
| Autoencoder architecture                            | Must fix   |
| Input features                                      | Must fix   |
| Normalization/preprocessing                         | Must fix   |
| Train/calibration/test split                        | Must fix   |
| FedAvg rounds/local epochs/batch size/optimizer/lr  | Must fix   |
| Exact device sample counts                          | Should fix |
| Attack matrix listing all source-objective pairs    | Must fix   |
| Cluster fingerprint exact formula and preprocessing | Should fix |
| Cluster assignments per seed                        | Should fix |
| Random-Benign numeric outputs                       | Must fix   |
| Full per-victim results                             | Should fix |
| Code/artifact availability                          | Must fix   |
| Hardware/software environment                       | Should fix |
| Script/manifest provenance                          | Should fix |

### Minimum artifact checklist before submission

* `config.yaml` or equivalent full experiment config.
* Seed list and seed-pairing file.
* Dataset preprocessing script.
* Train/calibration/test split manifests.
* Threshold-policy implementation.
* Attack injection implementation.
* Raw result CSV/Parquet.
* Figure/table regeneration scripts.
* Environment file: `requirements.txt`, `environment.yml`, or Dockerfile.
* README with exact commands.

---

## 14. Action Plan to Reach 10/10

### Must fix before submission

1. **Add a reproducibility table in §4.**
   Include AE architecture, features, preprocessing, splits, FedAvg hyperparameters, optimizer, batch size, local epochs, rounds, and software.

2. **Define the “4 source-objective pairs.”**
   Right now this is ambiguous in §4.3. List them explicitly.

3. **Expose Random-Benign results numerically.**
   Add a mini-table or include it in Table 2. Do not leave the control only in prose/caption.

4. **Clarify lowering-attack harm.**
   In Abstract, §5.3, Table 2, and Conclusion, foreground FPR/alarm burden. Treat positive ΔTPR only as threshold displacement.

5. **Add spillover evidence.**
   For Global and Cluster, table victim vs non-victim effects. The policy-differentiation claim depends on this.

6. **Downgrade or clarify score-level language.**
   Say clearly: “controlled score-level vulnerability characterization, not traffic-level exploit.”

7. **Add artifact/reproducibility statement.**
   Even a short statement helps.

### Should fix if page budget allows

1. Add closest-work comparison table in Related Work.
2. Add without-replacement or jittered-score sensitivity check.
3. Add per-victim susceptibility table in appendix/supplement.
4. Add q sensitivity or justify q=0.95 more strongly.
5. Add Cluster assignment summary.
6. Reformat Table 2 to avoid page 11 visual weakness.

### Nice to fix

1. Improve Figure 2 with all policies and seed variability.
2. Add Random-Benign to Figure 3.
3. Add a small attack-capability table in §3.
4. Add a practical interpretation of ΔCV(FPR).
5. Replace weakly adjacent citations with closer IDS/calibration/security citations.

### Do not touch / already strong

1. Do not broaden the claim to general FL security.
2. Do not claim raw-traffic realizability unless tested.
3. Do not remove the limitations section; it is a strength.
4. Do not overemphasize AUROC invariance as a contribution.
5. Do not add unrelated defenses unless they are tightly scoped.
6. Keep the Global/Local/Cluster framing; it is the paper’s core value.

---

## 15. Final Reviewer Simulation

### Reviewer 1 — Supportive expert reviewer

**Likely score: 8 / 10**

**Summary judgment:**
Clear, focused, and useful paper identifying a neglected calibration-stage vulnerability in FL-based IoT anomaly detection.

**Main objections:**

* Needs stronger reproducibility detail.
* Random-Benign control should be shown.
* Score-level limitation should be explicit in abstract.

**Questions they would ask:**

* Can the authors release the exact configs?
* Are the Random-Benign results numerically negligible?
* How sensitive are results to q?

**Current answer sufficient?**
Mostly, but not fully.

**Neutralizing fix:**
Add protocol table, Random-Benign table, and one sentence clarifying score-level scope.

---

### Reviewer 2 — Skeptical methods reviewer

**Likely score: 6.5 / 10**

**Summary judgment:**
Interesting idea, but experimental reporting is incomplete and the statistical treatment is somewhat fragile.

**Main objections:**

* n=10 bootstrap CIs are not fully convincing.
* Unit of aggregation/resampling is unclear.
* Materiality gate seems arbitrary.
* Model/training details missing.
* Controls are not shown.

**Questions they would ask:**

* Why 0.1 × IQR for Gate 1?
* Are victims independent?
* Where are raw per-victim results?
* Can the results be reproduced?

**Current answer sufficient?**
No.

**Neutralizing fix:**
Add resampling-unit clarification, sensitivity/caveat for Gate 1, full reproducibility table, and Random-Benign numbers.

---

### Reviewer 3 — Security/adversarial ML reviewer

**Likely score: 6.8 / 10**

**Summary judgment:**
The attack surface is plausible, but the attack model may be too artificial because it directly edits score buffers and creates detectable duplicates.

**Main objections:**

* Score-level access may not correspond to real attacker capability.
* Duplicate scores make the attack easy to detect.
* No stealth, no traffic-level generation, no defense evaluation.

**Questions they would ask:**

* Why is this not just a toy proxy?
* Can the attacker generate traffic with target reconstruction scores?
* Does the attack work without duplicate scores?
* What minimal defense catches it?

**Current answer sufficient?**
Partially. The paper is honest, but it needs a stronger defense of why score-level characterization is still publishable.

**Neutralizing fix:**
Add without-replacement/jitter sensitivity if possible. Otherwise, downgrade “attack succeeds” language to “score-channel leverage exists under controlled contamination.”

---

### Reviewer 4 — Presentation/clarity reviewer

**Likely score: 7.5 / 10**

**Summary judgment:**
The paper is readable and mostly well structured, but several visual and terminology issues reduce polish.

**Main objections:**

* Figure 2 is weak and too seed-specific.
* Figure 3 omits Random-Benign.
* Table 2 is dense and badly floated.
* Lowering attack wording is confusing.
* Some terms appear before definition.

**Questions they would ask:**

* Why is Gate 1 in the abstract?
* Why is positive ΔTPR called harm?
* Why is Table 2 on a mostly empty page?

**Current answer sufficient?**
Mostly on writing, not on visuals.

**Neutralizing fix:**
Reformat Table 2, revise lowering wording, improve figures, and add clearer captions.

---

# Final Verdict

**Current state: almost ready, but not fully submission-ready if the target is a strong conference or journal.**

For a focused workshop or mid-level applied security/IoT/FL venue, this is likely competitive after minor-to-moderate fixes. For a high-level venue, the paper needs stronger reproducibility, visible negative controls, per-victim/spillover evidence, and a more robust response to the score-level-realizability objection.

**Expected reviewer confidence:** medium-high after fixes; currently medium.

**Estimated acceptance probability, with caveats:**

| Venue type                                              | Current estimate | After must-fixes |
| ------------------------------------------------------- | ---------------: | ---------------: |
| Focused workshop / doctoral / applied FL-security venue |           60–75% |           75–85% |
| Solid international conference                          |           45–60% |           60–75% |
| High-level security / ML venue                          |           15–30% |           30–45% |

**Potential score after fixes:**
Around **9.0 / 10** with reporting, control, and visual fixes.
Around **9.5+ / 10** only if you add at least one duplicate-free or traffic-realizability sensitivity experiment.

**Do not chase endless polishing before fixing the core reviewer risks. The paper’s foundation is strong. The main job now is to make the methodology and evidence impossible to misunderstand.**
