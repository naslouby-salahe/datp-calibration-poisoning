# **1\. Executive Verdict**

## **1.1 One-Sentence Verdict**

The current Device-Aware Threshold Personalization (DATP) manuscript represents a rigorously controlled, methodologically elegant conference-level foundation, but remains intrinsically vulnerable to critical peer-review attacks regarding algorithmic triviality under stationary distributions, the absence of temporal degradation analysis, and insufficient isolation from model-level personalization baselines, categorizing the work as journal-near but requiring a high-effort, targeted expansion to survive a top-tier Elsevier review.

## **1.2 Journal Extension Feasibility**

A strong journal extension is highly feasible and strategically sound, provided the manuscript transitions from a static measurement study into a dynamic, deployment-realistic architectural framework. The core identity of the paper—isolating threshold calibration scope from model training under a frozen federated autoencoder—is mathematically clean and successfully addresses a documented gap in federated intrusion detection systems (FL-IDS).1 However, reaching the maturity expected by top-tier Elsevier venues such as *Computers & Security* strictly requires proving that post-training threshold personalization (DATP) remains necessary and effective even when local feature representations shift over time (concept drift) or are inherently adapted during training via model-level personalization (e.g., FedBN).2 Current editorial policies for target Elsevier venues explicitly permit conference extensions, provided the submission contains a minimum of 30% entirely new scientific material and significantly extends the previous work's analytical depth.4

## **1.3 Most Important Upgrade**

The single most critical upgrade is the introduction of a temporal drift and recalibration experiment evaluating threshold aging, juxtaposed against a model-level personalization baseline such as FedBN. This dual expansion forces the manuscript to definitively prove that local percentile thresholding is not merely a trivial artifact of matching calibration and test distributions in a randomized split, but rather an essential, dynamic operational requirement for mitigating false-alarm dispersion in non-stationary IoT environments.6

## **1.4 Main Danger**

The most severe risk to this extension is uncontrolled scope drift—specifically, mutating the manuscript into a generic non-IID federated aggregation or adversarial robustness paper. The identity of the research must remain rigidly anchored to post-training threshold calibration; every added dataset, baseline comparison, and metric must strictly serve to stress-test the thresholding mechanism, entirely avoiding the temptation to benchmark novel encoder architectures or fundamentally alter the underlying federated averaging algorithm.

# **2\. Current Paper Reconstruction**

The current DATP manuscript isolates threshold calibration as a distinct adaptation layer, a nuance frequently overlooked in the broader FL-IDS literature where thresholds are often treated implicitly or applied globally without controlling for encoder convergence.1 The methodology is sound within its highly constrained scope, utilizing a frozen FedAvg autoencoder with a single local epoch (![][image1]) to prevent client weight divergence, thereby ensuring that any observed variance in the False Positive Rate (FPR) is strictly attributable to the thresholding policy. However, this rigorous isolation simultaneously acts as the paper's greatest vulnerability, as reviewers will rapidly identify that the chosen operational parameters suppress the very heterogeneity that federated learning systems are designed to overcome.

| Item | Extracted From Paper | Reviewer Interpretation |
| :---- | :---- | :---- |
| Core contribution | Isolates threshold calibration scope as the sole experimental variable in an FL-IoT anomaly detection pipeline, evaluating shared, per-client, family-mean, and cluster-mean policies. | Methodologically precise, but risks being perceived as a narrow algorithmic footnote or hyperparameter tuning exercise rather than a comprehensive, systemic security solution. |
| Main claim | Per-client calibration (B2) drastically reduces FPR dispersion (CV) under physical device heterogeneity compared to a shared threshold (B1), and cluster-mean (B4) partially recovers this without a taxonomy. | Vulnerable to the "triviality" attack: setting a local p95 threshold mathematically guarantees an approximate 5% FPR by definition, provided the calibration and test distributions are drawn from the same stationary pool. |
| Confirmatory evidence | Regime A (N-BaIoT, 9 physical devices): B2 reduces CV(FPR) from 1.017 to 0.299; B4 recovers approximately 52% of this benefit. | Demonstrates strong internal validity under fixed conditions, but the evidence is fundamentally limited by the small fleet size and the lack of a chronological, temporally drifted test set. |
| Supporting evidence | Regime C (Dirichlet N-BaIoT partitions): Severe non-IID conditions demonstrate the maximum B1/B2 dispersion delta, which converges to near-zero as data becomes increasingly IID. | Confirms expected statistical behavior. This serves as a necessary but unsurprising supplementary proof that validates the core premise of heterogeneity-induced dispersion. |
| Exploratory evidence | Regime B (CICIoT2023): File-level pseudo-clients show near-homogeneous distributions, nullifying the B2 benefit and exposing an applicability boundary. | Honest and rigorous boundary-condition reporting. While a hostile reviewer may attack the artificiality of the partition, the negative result strengthens the manuscript's overall scientific integrity. |
| Main baselines | B1 (Arithmetic mean of local p95 thresholds), B2 (Per-client p95), B3 (Family-mean), B4 (Cluster-mean). B0 (Centralized) is included solely as a reference. | Lacks a critical comparison against model-level personalization (e.g., FedBN) and modern statistical calibration frameworks like conformal prediction or summary-statistic global thresholds.8 |
| Main datasets | N-BaIoT (device-partitioned) and CICIoT2023 (file-partitioned pseudo-clients). | N-BaIoT is aging within the literature. The CICIoT2023 partition is artificial. The study lacks a highly heterogeneous, modern, device-partitioned benchmark such as TON-IoT.1 |
| Main metrics | CV(FPR), mean FPR, mean TPR, worst-client balanced accuracy, and Macro-F1 (including P10 Macro-F1 for tail degradation). | Represents a highly mature, operationally sound claim structure. The inclusion of P10 Macro-F1 accurately captures the lower-tail detection sacrifice inherent in threshold manipulation. |
| Scope boundaries | Employs a frozen FedAvg autoencoder with ![][image1] and full client participation. Explicitly ignores temporal concept drift and adversarial evasion. | The ![][image1] parameter suppresses local weight divergence, artificially favoring post-training calibration. Ignoring temporal drift severely limits the deployment claims of the architecture.3 |
| Current limitations | Restricted to nine devices; limited local drift due to ![][image1]; metadata privacy leakage is acknowledged regarding the B4 cluster fingerprints. | The metadata leakage in B4 is a severe vulnerability. Given that federated learning's primary motivation is privacy, transmitting local distribution moments exposes the system to reconstruction attacks.10 |

# **3\. State of the Art Alignment**

The underlying doctoral thesis context correctly identifies three severe methodological deficits in the current corpus: unquantified heterogeneity, assumed rather than proven privacy, and a lack of deployment-realistic validation.1 The DATP conference paper successfully addresses the heterogeneity deficit by systematically measuring dispersion, but it completely ignores the privacy deficit regarding its B4 variant and fails to address the deployment reality of temporal concept drift. Furthermore, fresh deep research spanning 2024 to 2026 reveals critical new competitors and frameworks that threaten the novelty of the DATP manuscript if left unaddressed. Specifically, the emergence of summary-statistics-based global thresholding by Laridi et al. (2024) 9 directly competes with the B4 clustering mechanism, while the rise of Federated Conformal Prediction (FCP) introduces a level of statistical rigor that exposes the heuristic nature of DATP's simple 95th-percentile approach.8

| Item | Extracted From State of the Art | Relevance to DATP | Needs Fresh Verification? |
| :---- | :---- | :---- | :---- |
| Closest direct papers | The corpus highlights the failure of generic FL to handle IoT heterogeneity (Deficit 1).1 Recent work by Laridi et al. (2024) proposes federated anomaly detection using summary statistics-based thresholding.9 | Laridi et al. (2024) is a direct, highly contemporary competitor to DATP's B4 strategy. DATP must distinguish its cluster-mean approach from Laridi's overlap-region global thresholding. | Yes. Laridi et al. 9 must be deeply analyzed, implemented as a baseline, and cited to preserve B4's novelty and prevent desk rejection. |
| Closest adjacent papers | A growing body of work explores concept drift and threshold recalibration in IoT malware (e.g., FL-MalDrift, DyMETER).3 | Concept drift is the most glaring operational omission in the DATP manuscript. Addressing threshold aging elevates the paper from a static measurement to a dynamic journal-quality study. | Yes. Recent 2024/2026 drift papers confirm that dynamic recalibration is now a baseline expectation for top-tier security journals.7 |
| Transferable FL methods | The literature matrix identifies transferable model-level personalization techniques (FedBN, Ditto, Per-FedAvg).1 Conformal prediction is rapidly emerging for thresholding.8 | A hostile reviewer will inevitably demand to know if applying FedBN makes DATP redundant by aligning feature distributions natively at the model layer. | No, the theoretical necessity is clear from the State of the Art, but empirical validation against FedBN is strictly required for the extension. |
| Dataset gaps | TON-IoT is firmly established for demonstrating severe federation penalties under realistic IP-based or device-based partitioning.1 | DATP relies heavily on the aging N-BaIoT dataset. TON-IoT provides the required modern, hardware-partitioned complexity to validate the claims at a broader scale. | No, TON-IoT's specific utility and superior heterogeneity profile are thoroughly documented and justified in the provided corpus.1 |
| Privacy gaps | Deficit 2: Privacy is widely assumed, but FL updates remain highly vulnerable to reconstruction (DLG, MIA).1 | The B4 variant transmits statistical moments (mean, variance, skew, p95). This is a known vector for distribution reconstruction and property inference attacks.11 | Yes. The exact privacy leakage risk of transmitting these 4-scalar moments requires formal bounding and explicit discussion.20 |
| Heterogeneity gaps | Deficit 1: Performance claims in the literature depend almost entirely on the chosen partition structure.1 | DATP accurately addresses this via the Regime C Dirichlet sweep, but the use of ![][image1] artificially suppresses the weight-divergence aspect of non-IID FL. | No, the heterogeneity gap is properly identified, but DATP's experimental response must be strengthened by increasing local epochs. |
| Deployment gaps | Deficit 3: Hardware constraints and actual deployment mechanics are rarely measured outside of simulation.1 | DATP assumes client-side thresholding is computationally "free." The storage and continuous recalibration overheads must be formalized for operational validity. | No. The theoretical gap is well-established, but the operational translation (e.g., false-alarm burden metrics) must be derived. |
| Claim-support gaps | FL-IDS papers frequently overclaim detection capabilities while entirely ignoring the false alarm burdens placed on security operators.1 | DATP correctly focuses on FPR dispersion, representing a highly mature, operationally sound claim structure that effectively bridges this gap. | No. DATP's current claim bounding is excellent, highly defensible, and must be strictly preserved during the extension process. |

# **4\. Weakness Matrix**

To ensure the manuscript survives the scrutiny of an Elsevier reviewer, the current conference paper must be subjected to a hostile red-team audit. The most critical vulnerabilities lie not in the execution of the experiments, but in the artificial constraints placed upon them. The use of randomized train/test splits mathematically guarantees that calibration and test distributions are identical, reducing the B2 thresholding mechanism to a trivial statistical tautology. Furthermore, the decision to isolate thresholding by freezing the encoder with a single local epoch (![][image1]) shields the system from the realities of client weight divergence, prompting reviewers to question whether the architecture would collapse under standard federated conditions.

| ID | Weakness | Severity | Evidence From Paper | Why Reviewer Cares | Fix Type | New Experiment Needed | Effort | Scope Drift Risk |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| W01 | Triviality of B2 FPR equalization under stationary distributions | Critical | "FPR equalization is expected by construction..." (Section I) | If calibration and test distributions are strictly IID (due to randomized splitting), taking the 95th percentile guarantees a 5% FPR by definition. The scientific value is only proven if the IID assumption is broken via temporal drift. | Mandatory | Yes (Temporal chronological drift evaluation) | Moderate | Low |
| W02 | Omission of model-personalization baselines | Critical | Section II (Related Work) mentions Per-FedAvg and FedPer but tests none. | FedBN naturally normalizes local features. If FedBN aligns distributions natively during training, threshold personalization (DATP) might be rendered entirely redundant. | Mandatory | Yes (Add FedBN comparison) | Heavy | Medium |
| W03 | Omission of 2024-2026 thresholding SOTA | Major | Section IV details B4 mechanism without contemporary benchmarking. | Laridi et al. (2024) 9 recently published a summary-statistic thresholding method for FL-AEs. Failing to differentiate B4 from this is a fatal literature omission. | Mandatory | Yes (Implement Laridi B5 baseline) | Moderate | Low |
| W04 | ![][image1] masks non-IID weight divergence | Major | Protocol: "![][image1], full participation" (Section V-B) | ![][image1] behaves almost identically to synchronous centralized training. It artificially minimizes client drift, making post-training thresholding look like a complete solution when the model itself hasn't drifted. | Mandatory | Yes (![][image2] ablation sweeps) | Moderate | Low |
| W05 | Unquantified B4 Privacy Leakage | Major | B4 shares a 4-scalar fingerprint (mean, variance, skew, p95). | FL is inherently motivated by privacy. Exposing local distribution moments is a known, exploitable vector for property inference and distribution reconstruction attacks.11 | Mandatory | No (Deep theoretical privacy bounding required) | Low | Low |
| W06 | Arbitrary heuristic thresholding (p95) | Moderate | Calibration uses a fixed ![][image3] heuristic. | Statistical anomaly detection is rapidly transitioning toward distribution-free guarantees (Conformal Prediction) rather than arbitrary empirical percentiles.8 | Recommended | Yes (Add Split Conformal Prediction threshold) | Moderate | Medium |
| W07 | Dataset age and insufficient client scale | Moderate | Relies primarily on N-BaIoT (2018), partitioned into only 9 devices. | Reviewers expect contemporary validation. Nine devices are statistically insufficient to robustly prove the reliability of the B4 unsupervised clustering mechanism.1 | Recommended | Yes (Add TON-IoT dataset) | Heavy | Low |

# **5\. Research-Backed Fix Matrix**

Addressing the weaknesses identified in the red-team audit requires implementing a suite of targeted, research-backed methodologies. The goal is to elevate the manuscript's analytical depth without altering its core identity. By introducing temporal drift, comparing against local feature normalization, and benchmarking against contemporary summary-statistic global thresholds, the extension systematically closes every major theoretical and empirical loophole.

| Weakness ID | Proposed Fix | Literature Support | Exact Experiment or Analysis | Dataset Needed | Baselines Needed | Metrics | Main or Supplement | Expected Reviewer Value |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| W01 | Temporal Threshold Aging & Recalibration | FL-MalDrift 3, Concept drift in IoT 7 | Re-partition N-BaIoT chronologically. Calibrate B2 at ![][image4], evaluate on test windows ![][image5]. Measure how quickly FPR equalization degrades without recalibration, then introduce an EWMA recalibration scheme. | N-BaIoT (chronological) | B1, B2, B2-Recal | CV(FPR), FPR trajectory over time | Main | Proves B2's held-out value in dynamic, non-stationary environments, nullifying the triviality critique. |
| W02 | FedBN Model Personalization Comparison | FedBN literature 17 | Train a FedBN autoencoder. Apply B1 and B2 thresholds. Compare the detection matrix: (FedAvg+B2) versus (FedBN+B1) versus (FedBN+B2). | N-BaIoT | FedBN | CV(FPR), P10 Macro-F1 | Main | Answers definitively if representation personalization at the model layer obsoletes post-training threshold personalization. |
| W03 | Benchmark against Laridi (2024) | Laridi et al. summary-statistic thresholding 9 | Introduce Laridi's global overlap-region threshold algorithm as a new baseline (B5). Explicitly prove B4's clustering superiority in highly non-IID regimes compared to Laridi's global mathematical intersection. | N-BaIoT, TON-IoT | B5 (Laridi overlap threshold) | CV(FPR), Mean F1 | Main | Pre-empts desk rejection for missing the exact closest contemporary state-of-the-art methodology. |
| W04 | Local Epoch (![][image6]) Divergence Sweep | Federated optimization under heterogeneity 2 | Train the standard autoencoder with ![][image7]. Evaluate B1 versus B2 CV(FPR) to determine if threshold calibration survives severe local model drift. | N-BaIoT | B1, B2 | CV(FPR), Client weight divergence norm | Main | Demonstrates that DATP's efficacy is robust against representation drift caused by local model updates. |
| W05 | Privacy Threat Bounding | Inference attacks on FL distributions 10 | Add an analytical section formally assessing the reconstruction/inference threat of the 4-scalar fingerprint transmitted by B4. | None | None | Information theoretic bound / descriptive analysis | Main | Closes the most obvious security reviewer loophole regarding the exposure of metadata. |
| W06 | Conformal Prediction Variant | Federated CP 12, CP 8 | Implement Split Conformal Prediction (SCP) thresholding alongside the empirical p95 to guarantee statistical coverage. | N-BaIoT | SCP threshold | Empirical coverage, Prediction set size | Supplement | Modernizes the statistical rigor of the paper, appealing to mathematically inclined reviewers. |
| W07 | TON-IoT Heterogeneity Expansion | IoT federation penalty literature 1 | Replicate the primary Regime A protocol on the TON-IoT dataset using a strict IP-based hardware partition. | TON-IoT | B1, B2, B4, B5 | CV(FPR), Mean F1 | Main | Scales the core claims to a modern, highly heterogeneous dataset, proving B4's efficacy on larger client populations. |

# **6\. Dataset Expansion Matrix**

To justify a substantial journal extension, the empirical foundation must be broadened beyond the nine devices of N-BaIoT and the artificial pseudo-clients of CICIoT2023. However, adding datasets indiscriminately risks transforming the manuscript into a generic benchmarking paper, diluting the focus on threshold calibration. The selection of new datasets must strictly serve the purpose of stress-testing heterogeneity and temporal drift.

| Dataset | Add or Reject | Reason | Physical Device Split | Temporal Potential | Calibration Suitability | DATP Fit | Preprocessing Burden | Main Risk |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| TON-IoT | Add | Explicitly cited in the FL-IDS literature as exposing severe federation penalties under IP-partitioning.1 Highly relevant for stressing non-IID thresholding policies. | Yes (IP-based telemetry partition) | Moderate | High (Contains sufficient benign traffic windows for calibration) | Excellent | Moderate (Requires standardizing feature vectors to match the existing autoencoder structure or defining a separate encoder) | Significant time consumption for engineering the new data pipeline and ensuring convergence. |
| N-BaIoT (Chronological) | Add | Required to resolve W01 (Triviality of B2). Allows for chronological splitting instead of randomized shuffling, establishing the baseline for concept drift. | Yes | High | High | Perfect | Immediate (Already preprocessed; requires only indexing by original capture timestamps) | None. |
| Bot-IoT | Reject | Too similar to N-BaIoT in scope, age, and attack profile. Does not add orthogonal scientific value regarding physical heterogeneity. | Yes | Low | Moderate | Moderate | Moderate | Fails to provide new structural heterogeneity insights, wasting computational resources. |
| Edge-IIoTset | Reject | An excellent modern dataset, but adding it alongside TON-IoT would violate the strict scope limitation and push the manuscript toward a dataset-survey structure. | Yes | Moderate | High | Moderate | Heavy | Uncontrolled scope drift and severe workload infeasibility. |
| UNSW-NB15 | Reject | Fundamentally an enterprise network dataset, not a dedicated IoT hardware dataset. Poor alignment with the physical device-awareness theme of DATP. | No | Low | Low | Poor | Heavy | Destroys the IoT-specific identity of the research. |

# **7\. Stronger Comparison Matrix**

The transition to a top-tier journal requires isolating the proposed mechanism from adjacent paradigms. Reviewers will question whether adjusting the threshold post-training is necessary if the underlying model is trained using personalized techniques that naturally align local feature distributions. The following comparisons are designed to definitively answer these architectural challenges.

| Comparison | Mandatory? | Scientific Question | Implementation Cost | Reviewer Value | Scope Drift Risk | Recommended Placement |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| FedAvg+B2 vs. FedBN+B1 | Yes | Does model-level feature personalization (via FedBN's local batch normalization) naturally align reconstruction error distributions, rendering post-training threshold personalization (B2) obsolete? | Moderate (FedBN is a direct structural replacement for FedAvg; replace global BN layers with local BN state) | Extremely High. Addresses the most likely architectural objection from the distributed learning community. | Low | Main paper |
| DATP B4 vs. Laridi's Summary-Stat Threshold (B5) | Yes | How does B4's unsupervised clustering algorithm compare to the 2024 state-of-the-art method of aggregating summary statistics to calculate a global overlap intersection? 9 | Moderate (Requires implementing Laridi's overlap heuristic algorithm and running it over the existing local score artifacts) | High. Establishes and defends B4's novelty against the exact closest contemporary methodology. | Low | Main paper |
| FedAvg+B2 (![][image1]) vs. FedAvg+B2 (![][image8]) | Yes | Does threshold personalization maintain its efficacy when local models are permitted to diverge heavily between global aggregation rounds? | Moderate (Requires executing new FL training routines with ![][image8]) | High. Removes the artificial stability of the current ![][image1] training protocol, proving robustness. | Low | Main paper |
| DATP p95 vs. Conformal Prediction | No (Recommended) | Does a distribution-free statistical coverage guarantee provide superior operational performance compared to empirical heuristic percentiles? | Moderate (Post-hoc application of conformal non-conformity scores to existing calibration arrays) | High for statistics-focused reviewers; moderate for applied security reviewers. | Medium | Supplementary |
| FedAvg vs. FedProx | No (Reject) | Does proximal regularization improve the underlying autoencoder convergence? | Moderate | Low. Proximal regularization targets weight convergence, not the post-training threshold geometry that DATP addresses. | High | Do not include |

# **8\. Threshold Variant Matrix**

The exploration of threshold policies must be expanded to include contemporary approaches that account for non-stationary environments and advanced statistical aggregation. This matrix filters potential variants to ensure only those that directly strengthen the core narrative of DATP are included in the final extension.

| Variant | Definition | Why It Matters | Mandatory? | Risk | Main or Supplement |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Laridi Global Overlap (B5) | A global threshold calculated by identifying the intersection of local normal and anomalous summary statistics across clients.9 | Represents the direct 2024 state-of-the-art competitor to the B4 clustering policy. | Yes | Low | Main paper |
| Drift-Aware Recalibrated Threshold (B2-Recal) | An Exponentially Weighted Moving Average (EWMA) of the local p95 threshold, continuously updated over sliding temporal test windows.3 | Directly addresses the reality of concept drift and threshold aging without necessitating full model retraining. | Yes | Low | Main paper |
| ![][image9]\-sensitivity sweep | Varying the target calibration percentile across ![][image10]. | Proves that the observed dispersion equalization is a systemic property and not an artifact of selecting ![][image3]. | Yes | Low (Already partially verified by the authors in the original text) | Supplement |
| Conformal Prediction (CP) | A dynamic threshold set via conformal non-conformity scores to guarantee a strict ![][image11] coverage probability.8 | Provides the rigorous statistical guarantees that are fundamentally lacking in heuristic empirical percentiles.18 | No | Expands theoretical scope significantly, potentially overshadowing the systems-level claims. | Supplement |
| Peak Over Threshold (POT) | Extreme Value Theory applied dynamically to the right tail of the local reconstruction error distribution.23 | Topologically aware thresholding utilized in recent deep learning anomaly pipelines. | No | Mathematically dense; highly redundant if Conformal Prediction is also included. | Reject |

# **9\. Temporal Drift and Recalibration Plan**

The most significant theoretical flaw in the current DATP manuscript is the reliance on randomized train/test splits. Randomized shuffling virtually guarantees that the calibration data and the test data are drawn from identical, stationary distributions. Under such conditions, applying a 95th-percentile threshold to the calibration set mathematically guarantees a 5% FPR on the test set. To prove that DATP has actual operational value, it must be evaluated in a dynamic environment where distributions shift over time.

## **9.1 Feasibility**

The current N-BaIoT dataset fully supports real temporal analysis. The original network captures span extensive timeframes, and by abandoning the randomized shuffle in favor of a strict chronological partition, the manuscript can naturally induce and evaluate proxy concept drift.7

## **9.2 Minimum Viable Temporal Experiment**

Re-partition the N-BaIoT benign data chronologically into five sequential blocks: ![][image12], ![][image13], ![][image14], ![][image15], and ![][image16]. The federated autoencoder is trained strictly on ![][image12]. The B1 and B2 thresholds are calibrated exclusively on ![][image13]. The evaluation of CV(FPR) is then conducted sequentially across the three test windows. The objective is to demonstrate that CV(FPR) and mean FPR degrade over time as device behavior naturally drifts, establishing that a static B2 threshold is insufficient for long-term deployment.

## **9.3 Strong Temporal Experiment**

Implement the chronological evaluation detailed above, but introduce a **Drift-Aware Recalibration Policy (B2-Recal)**. Drawing methodological inspiration from recent literature on IoT concept drift such as FL-MalDrift 3 and DyMETER 14, apply an Exponentially Weighted Moving Average (EWMA) to update the local threshold over sliding windows of the incoming test data stream. Compare the performance degradation of the aging, static B2 threshold against the continuously recalibrated B2-Recal threshold.

## **9.4 Metrics**

1. **FPR Degradation Slope**: The mathematical rate of absolute FPR increase across the sequential time windows ![][image17] through ![][image18].  
2. **CV(FPR) Trajectory**: A longitudinal measurement of whether relative cross-client dispersion worsens as the local models age.  
3. **Recalibration Frequency / Delta**: The magnitude of the threshold shift required to restore the target ![][image3] operating point.

## **9.5 Interpretation Rules**

* **Positive Outcome**: The static B2 threshold degrades over time, but the dynamic B2-Recal policy successfully restores CV(FPR) to the baseline. This proves that while local calibration is initially highly effective, dynamic operational environments mandate the proposed recalibration scheme, firmly cementing the paper as a robust, deployment-ready systems architecture.  
* **Negative Outcome**: The static B2 threshold does not degrade over time. Interpretation: The physical devices within N-BaIoT exhibit highly stationary benign behavior over the capture period. The temporal experiment essentially acts as an extended robustness check, confirming long-term stability rather than demonstrating drift.  
* **Mixed Outcome**: The B2 threshold degrades, but recalibrating it to fix the FPR simultaneously swallows the TPR (i.e., it begins ignoring attacks). Interpretation: Concept drift affects both the benign and anomalous distributions concurrently; threshold recalibration alone cannot salvage severe model aging, indicating the absolute limit of post-training calibration and signaling the necessity for global model retraining. This represents a highly nuanced, journal-quality finding.

# **10\. Deeper Analysis Plan**

To transition the manuscript from merely reporting results to providing deep, journal-level understanding, the extension must analyze the mechanical causes of its outcomes. The following analyses decompose the observed metrics into actionable insights regarding feature geometry, privacy, and operational costs.

| Analysis | Purpose | Required Data | Figure or Table | Expected Insight | Priority |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **![][image1]** vs ![][image8] Weight Divergence Assessment | Prove that DATP maintains its efficacy even when local feature representations drift during the training phase. | New training artifacts resulting from ![][image8] runs on N-BaIoT. | Line chart: CV(FPR) progression versus training epochs for both B1 and B2. | The B1 dispersion worsens significantly under ![][image8] due to accelerated local drift; B2 remains highly stable, proving DATP's necessity in standard, asynchronous FL environments. | High |
| B4 Metadata Privacy Leakage Bound | Directly address the metadata exposure vulnerability of the cluster fingerprints.11 | The current 4-scalar fingerprint data structures. | Text/Equation block: Information theoretic privacy risk formalization. | B4 inherently leaks property distribution moments; formalizing the risk versus communication efficiency trade-off provides necessary security context. | High |
| Worst-Client Floor Effect (Ennio Diagnostics) | Mechanically explain the observed drop in the P10 Macro-F1 metric. | Current Regime A reconstruction score arrays. | Scatter/Density plot: Benign versus Attack score overlaps for the Ennio doorbell versus a high-performing client. | The B2 threshold is forced above the attack mass due to fundamentally poor feature separability for that specific camera hardware, illustrating the limits of thresholding. | High |
| JS Divergence vs. B2 Benefit Correlation | Mathematically correlate distributional heterogeneity with the necessity of deploying DATP. | Pairwise JS divergence matrices from Regimes A, B, and C. | Scatter plot: Fleet-wide JS Divergence versus the B1-B2 CV(FPR) Delta. | Quantifies exactly *when* an operational deployment requires DATP (high JS divergence) versus when a shared B1 threshold is perfectly adequate (low JS divergence). | Medium |
| Operational False Alarm Burden Translation | Translate the abstract CV(FPR) metric into tangible Security Operations Center (SOC) terminology. | Current Regime A FPRs extrapolated against a standard 24-hour traffic volume. | Table: Projected daily false alerts generated per device. | B1 floods the SOC with massive alert volumes from a single high-variance device; B2 distributes the alert burden equitably across the fleet, proving massive operational value. | Medium |

# **11\. Journal Originality and Conference Extension Plan**

Elsevier enforces strict guidelines regarding the extension of conference papers. Submissions must not only contain substantial new material but must fundamentally advance the analytical narrative. The extension must be carefully crafted to avoid self-plagiarism while cleanly disclosing its origins.

## **11.1 What Can Be Reused**

The core scientific identity (isolating threshold scope under a frozen autoencoder), the formal mathematical definitions of the B1–B4 policies, the primary dispersion metric (CV(FPR)), the CICIoT2023 applicability boundary check (Regime B), and the Dirichlet non-IID severity sweep (Regime C) can safely remain as the foundational architecture of the paper.

## **11.2 What Must Be New**

To definitively meet the strict ![][image19] novelty threshold mandated by Elsevier venues (such as *Computers & Security* or *Internet of Things*) 4, the manuscript must introduce:

1. **New Baseline**: The FedBN comparison, serving to isolate threshold-level personalization from model-level personalization.  
2. **New Competitor**: The Laridi et al. (2024) 9 summary-statistic overlap threshold, benchmarking B4 against the current state of the art.  
3. **New Dataset**: The TON-IoT dataset, providing a modern, realistic IP-based heterogeneity challenge.1  
4. **New Dimension**: The temporal drift and threshold aging analysis, transitioning the methodology from static measurement to dynamic evaluation.

## **11.3 Self-Plagiarism Risk**

Elsevier heavily utilizes iThenticate to screen submissions. Verbatim copying of large text blocks from the original DATP conference paper (if it has already been published and indexed) will invariably trigger desk rejection. To mitigate this, the introduction, related work, and methodology prose must be entirely rewritten to frame the work around the *dynamic and temporal* aspects of thresholding, shifting the narrative focus from static cross-client measurement to longitudinal operational stability.

## **11.4 Cover Letter Disclosure**

"Dear Editor, this manuscript represents a substantial and rigorous extension of our prior conference paper, 'Device-Aware Threshold Personalization...'. In strict accordance with Elsevier policy, this journal submission contains well over 30% entirely new scientific material and deeply expands upon the preliminary findings. Specifically, we have fundamentally shifted the evaluation paradigm to address the critical operational challenges of temporal concept drift and threshold aging in non-stationary IoT environments. Furthermore, we have incorporated a new highly heterogeneous dataset (TON-IoT) and rigorously benchmarked our threshold-level personalization framework against modern model-level personalization paradigms (FedBN) and recent state-of-the-art summary-statistic estimators (Laridi et al., 2024). The original conference paper is appropriately cited throughout, and the newly added dimensions successfully transition the work from a static measurement study into a dynamic, deployment-ready architectural framework."

# **12\. Elsevier Venue Target Matrix**

The selection of the target venue dictates the required framing of the extension. The manuscript currently sits at the intersection of network security, distributed systems, and applied machine learning.

| Rank | Journal | Scope Match | Indexing Status To Verify | Best Framing Angle | Required Upgrades | Desk-Rejection Risk | Recommendation |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| 1 | Computers & Security (COSE) | Perfect. The journal heavily prioritizes pragmatic, deployment-ready security architectures and operational metrics.24 | SCIE, JCR Q1 | Emphasize operational false-alarm burden reduction, fairness, and recalibration under adversarial FL settings. | Temporal drift analysis, Laridi competitor comparison, FedBN baseline. | Low, provided the 30% novelty extension rule is explicitly documented and met.4 | **High Priority**. |
| 2 | Internet of Things (IoT) | Excellent. Focuses extensively on IoT architectures, edge constraints, and distributed intelligence.25 | SCIE, JCR Q1/Q2 | Frame as handling severe hardware and telemetry heterogeneity at the IoT edge via highly lightweight threshold calibration. | TON-IoT dataset addition, rigorous B4 communication overhead analysis. | Low. | Secondary Target. |
| 3 | Journal of Network and Computer Applications (JNCA) | Strong. Focuses broadly on network applications and distributed computing infrastructures.27 | SCIE, JCR Q1 | Focus on the network-level mechanics and efficiency of transmitting B4 statistical fingerprints versus localized B2 storage. | Temporal drift implementation, ![][image8] local epoch ablation. | Moderate (Applied security is a sub-topic, not the exclusive focus of the journal). | Fallback. |
| 4 | Future Generation Computer Systems (FGCS) | Moderate. Focuses on massive-scale distributed systems and high-performance computing.28 | SCIE, JCR Q1 | Frame around the FL infrastructure scalability of distributed thresholding mechanics. | Requires massive scaling modifications (e.g., simulating 1,000+ simultaneous clients). | High (DATP currently focuses on 9-63 clients, which is vastly too small for FGCS scale). | Do not submit. |

# **13\. Three-Level Expansion Roadmap**

The following roadmaps delineate the exact engineering and analytical effort required to expand the DATP manuscript into a journal-ready state.

## **13.1 Minimal Journal Extension**

| Component | Required Action | Why It Is Needed | Effort | Risk |
| :---- | :---- | :---- | :---- | :---- |
| Baselines | Implement Laridi (2024) B5 overlap threshold algorithm. | It is the direct 2024 state-of-the-art competitor to the B4 policy.9 | Low | High risk of desk rejection if omitted by knowledgeable reviewers. |
| Ablation | Execute new FL training runs utilizing ![][image8]. | Proves the robustness of the thresholding architecture against local weight divergence. | Moderate | Increasing local epochs might degrade the overall global Macro-F1 score. |
| Analysis | Calculate and correlate fleet JS Divergence with the CV(FPR) delta. | Quantitatively establishes exactly when DATP is mathematically required for a deployment. | Low | None. |

## **13.2 Strong Journal Extension**

| Component | Required Action | Why It Is Needed | Effort | Risk |
| :---- | :---- | :---- | :---- | :---- |
| All Minimal | Fully implement the Minimal tier actions. | Represents the absolute core literature and robustness requirements. | \- | \- |
| Temporal | Execute the chronological N-BaIoT split and threshold aging analysis. | Definitively solves the "triviality" critique of static p95 equalization on randomized splits. | Moderate | The natural concept drift within the N-BaIoT capture window might be statistically negligible. |
| Baselines | Add the FedBN model-level personalization comparison. | Proves that representation personalization does not render threshold personalization obsolete. | Heavy | FedBN might unexpectedly outperform the DATP architecture entirely. |
| Privacy | Formalize the B4 metadata privacy leakage risk. | Closes a glaring security loophole regarding the exposure of distribution moments.11 | Low | None. |

## **13.3 Ambitious Journal Extension**

| Component | Required Action | Why It Is Needed | Effort | Risk |
| :---- | :---- | :---- | :---- | :---- |
| All Strong | Fully implement the Strong tier actions. | Represents the top-tier operational requirements for COSE. | \- | \- |
| Dataset | Integrate the TON-IoT dataset utilizing an IP-based partition. | Modernizes the evidence base and provides a severe test of heterogeneity.1 | Heavy | High probability of pipeline failure or extreme hyperparameter tuning required for convergence. |
| Thresholds | Implement Split Conformal Prediction (SCP) thresholding. | Massively upgrades the statistical rigor of the boundary definitions.8 | Moderate | Creates severe math-heavy scope drift away from systems security. |

# **14\. Final Recommended Package**

The optimal journal-extension package relies on the execution of the **Strong** plan, heavily augmented with selective elements from the Ambitious tier to ensure it is untouchable by an aggressive Elsevier reviewer.

1. **Dataset additions:** The manuscript must incorporate the TON-IoT dataset, specifically utilizing an IP-partitioned client structure. This modernizes the aging empirical foundation provided by N-BaIoT and introduces a highly heterogeneous telemetry environment recognized in the literature for exposing severe federation penalties.  
2. **Baseline additions:** The extension requires the addition of FedBN (to represent model-level personalization) and the Laridi et al. (2024) Summary-Statistic Overlap Threshold (B5). This dual inclusion proves that DATP is neither rendered obsolete by advanced neural architectures nor surpassed by the latest mathematical global heuristics.  
3. **Threshold additions:** The introduction of the B2-Recal (EWMA drift-aware sliding threshold) is strictly necessary to bridge the gap between static measurement and dynamic, real-world deployment operations.  
4. **Temporal/recalibration additions:** The implementation of a chronological N-BaIoT split measuring threshold aging and ![][image9]\-degradation over sequential time windows. This definitively answers the most critical methodological weakness regarding the triviality of static percentile calibration.  
5. **Deeper analyses:** The manuscript must include the ![][image8] local epoch divergence impact study, the Fleet JS-Divergence correlation analysis, the formal B4 Metadata Privacy Leakage assessment, and the translation of metrics into an Operational False-Alarm Burden calculation for Security Operations Centers.  
6. **New figures:** The visual narrative must be expanded with a Temporal FPR Degradation Line Chart illustrating threshold aging, and a FedAvg versus FedBN CV(FPR) Bar Chart to highlight the architectural comparisons.  
7. **New tables:** A Daily False Alarm translation table must be added to provide tangible, pragmatic context for SOC operators, converting abstract CV metrics into actionable engineering data.  
8. **New sections:** The introduction of two major sections is required: "Impact of Temporal Concept Drift on Calibration Stability" and "Model-Level vs. Threshold-Level Personalization". These sections will carry the bulk of the 30% novelty requirement.  
9. **Supplementary material:** The inclusion of a ![][image9]\-sweep sensitivity analysis (evaluating ![][image20] and ![][image21]) provides necessary statistical thoroughness without bloating the main text.  
10. **Claims to strengthen:** The narrative must aggressively strengthen claims regarding B2's systemic resilience to local model drift (via the ![][image8] evidence) and its ultimate deployment viability (via the temporal recalibration evidence).  
11. **Claims to avoid:** The authors must strictly avoid claiming that the B4 cluster-mean strategy is a privacy-preserving mechanism. It must be explicitly classified and defended as a communication-efficient, but inherently privacy-leaking, operational heuristic.

# **15\. Artifact and Claim Consistency Check**

| Proposed Claim | Current Support Status | Required Evidence | Artifact Needed | Safe Wording |
| :---- | :---- | :---- | :---- | :---- |
| B2 maintains FPR equalization under model drift. | 3\. Requires new experiments. | New FL training runs with ![][image8] demonstrating that B1 degrades while B2 maintains stability. | New FL simulation logs and score arrays for the ![][image8] condition. | "Even under increased local epochs (![][image8]), per-client calibration sustains FPR equalization where shared thresholds fundamentally deteriorate." |
| B4 outperforms existing global summary-stat thresholds. | 3\. Requires new experiments. | A direct empirical comparison of B4 CV(FPR) against the Laridi (2024) B5 overlap algorithm. | Recomputed threshold boundary logs utilizing existing calibration arrays. | "B4's unsupervised grouping achieves lower CV(FPR) than global overlap-region heuristics in highly heterogeneous partitions." |
| Threshold aging necessitates dynamic recalibration. | 3\. Requires new experiments. | An ascending FPR trajectory observed on chronological N-BaIoT data splits. | Time-indexed evaluation score arrays. | "Under chronological evaluation, static calibration ages predictably, underscoring the necessity of sliding-window recalibration in dynamic IoT networks." |
| Threshold personalization complements FedBN. | 3\. Requires new experiments. | Empirical results showing FedBN+B2 significantly outperforms FedBN+B1. | FedBN model checkpoints and localized test score arrays. | "While model-level feature normalization (FedBN) reduces inherent skew, post-hoc threshold personalization remains requisite for optimal false-alarm equity." |

# **16\. Reviewer-Loophole Closure Table**

| Loophole | Closed By | Remaining Risk | Final Wording Discipline |
| :---- | :---- | :---- | :---- |
| "B2 is trivially mathematically guaranteed to equalize FPR." | The Temporal Drift experiment, demonstrating that B2 fails if the incoming test data drifts. This proves it is a dynamic operational variable requiring maintenance, not a mathematical given. | A hostile reviewer may argue that the induced drift is artifactual. | Emphasize relentlessly that chronological deployment naturally breaks the IID assumption of standard percentile estimators. |
| "Laridi 2024 already published federated summary-thresholds." | Direct implementation and rigorous comparison against Laridi's global overlap heuristic.9 | Laridi's method might empirically outperform the B4 clustering mechanism. | If Laridi proves superior, pivot B4's primary claim to "computational efficiency" rather than statistical superiority, preserving absolute scientific honesty. |
| "B4 leaks distribution privacy." | An explicit Information Theory privacy bounding section addressing metadata exposure. | Reviewers might demand the implementation of Secure Aggregation (SecAgg) architectures. | "While SecAgg integration remains orthogonal to this study, we formally quantify the baseline metadata exposure to establish operational risk bounds." |
| "The N-BaIoT dataset is outdated." | The addition of the TON-IoT dataset utilizing strict IP-based partitioning. | TON-IoT non-IID tuning is notoriously difficult to stabilize. | Explicitly report the TON-IoT results as a "severe heterogeneity stress test" rather than demanding perfect global Macro-F1 convergence. |

# **17\. Final Recommended Decision Gate**

## **17.1 Best Target Journal**

**Computers & Security (COSE)**. The journal explicitly values the intersection of applied security algorithms, operational architectures, and practical deployment metrics (such as tangible false-alarm burden reduction). COSE readily accepts conference extensions that successfully demonstrate a minimum of 30% novelty and deepen the architectural and operational robustness of the original concept.4

## **17.2 Best Expansion Level**

**Strong**. Attempting the Ambitious level in its entirety (adding Conformal Prediction *and* TON-IoT concurrently) risks catastrophic scope drift and threatens to delay the PhD publication timeline indefinitely. The Strong level fixes the critical scientific flaws (methodological triviality, concept drift, SOTA omission) while remaining executable within a reasonable, focused research window.

## **17.3 Exact Must-Do List Before Submission**

1. Recode the N-BaIoT dataloader to support strict chronological Train/Calib/Test1/Test2 sequential splits.  
2. Execute the B2 Threshold Aging (temporal drift) and EWMA recalibration experiment.  
3. Code, train, and evaluate a FedBN baseline to directly compare against the existing FedAvg architecture.  
4. Calculate Laridi's 2024 overlap-threshold (B5) using the existing local summary statistics and benchmark it against B4.  
5. Execute the ![][image8] ablation sweep on the existing N-BaIoT pipeline.  
6. Draft the formal B4 metadata privacy leakage theoretical assessment.

## **17.4 Exact Do-Not-Do List**

1. Do not convert the manuscript into a Conformal Prediction or pure statistics paper; maintain the applied systems-security focus.  
2. Do not attempt to engineer a fix for the Ennio Doorbell Macro-F1 floor (leave it as an honest, mechanically sound diagnostic limitation of reconstruction-based anomaly detection).  
3. Do not add the Edge-IIoTset or Bot-IoT datasets, as they will cause uncontrolled benchmarking bloat.  
4. Do not implement complex cryptographic Secure Aggregation protocols for B4, as this completely fractures the scope.

## **17.5 Should the Journal Extension Wait Until Conference Acceptance?**

**Yes.** Elsevier policy for conference extensions relies heavily on the original conference paper existing as a formal, accepted, and citable entity.29 Submitting the journal extension prior to conference acceptance risks severe dual-submission policy violations and critically undermines the ability to accurately disclose and map the \>30% analytical delta against a finalized, immutable prior publication.

# **18\. Search Audit Log**

| Search Query or Source | Source Type | Date Checked | Key Findings | Confirmed / Changed / Contradicted SoA | Used in Final Recommendation? |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Elsevier conference paper extension policy | Publisher Policy | May 2026 | Extensions are permitted if they contain \>30% new material and the original is clearly cited. | Confirmed (aligns with standard academic practice). | Yes |
| "Enhanced federated anomaly detection through autoencoders using summary statistics" | Academic Paper (Laridi, 2024\) | May 2026 | Identified a direct competitor utilizing normal/anomaly summary stats for global thresholding. | Contradicted SoA (The original SoA missed this exact, highly contemporary thresholding competitor). | Yes (Mandatory B5 comparison) |
| FL-MalDrift / Concept drift federated malware | Academic Papers (2024-2025) | May 2026 | Concept drift and threshold recalibration are dominant contemporary security themes. | Expanded SoA (Highlighted drift as a critical, previously unaddressed gap). | Yes (Temporal drift experiment) |
| Federated Conformal Prediction | Academic Papers (2024-2026) | May 2026 | CP provides distribution-free thresholding, emerging as highly relevant to FL. | Expanded SoA. | Yes (Included as an optional/supplementary variant) |

# **19\. Final Red-Team Verdict**

## **19.1 Would This Survive a Strong Elsevier Review?**

Yes, but strictly conditionally. It will survive only if the Temporal Drift and FedBN experiments are executed flawlessly. In its current conference form, a COSE reviewer would swiftly desk-reject the DATP manuscript for theoretical triviality (the inherent logic of B2 equalization under IID splits) and for ignoring modern, highly relevant FL competitors (Laridi 2024). By incorporating the Strong Roadmap, the manuscript directly anticipates, absorbs, and neutralizes these exact Reviewer 2 attacks, successfully transitioning the narrative from a "static measurement curiosity" to a "dynamic systems evaluation."

## **19.2 What Would Still Be Attacked?**

1. **The Artificiality of Regime B**: Hostile reviewers may continue to attack CICIoT2023's file-level partition as fundamentally unrealistic. Defense strategy: Maintain strict honesty that it is solely a homogeneous algorithmic boundary-check, not a physical simulation.  
2. **B4's Practicality**: If Laridi's method (B5) mathematically matches B4's performance without requiring K-Means clustering, B4's necessity will be aggressively questioned. Defense strategy: Pivot rapidly to computational cost comparisons or communication overhead efficiencies.

## **19.3 Final Priority Order**

1. Implement the Laridi 2024 baseline (B5) on the existing score artifacts (Immediate/Low Effort).  
2. Code the chronological N-BaIoT data split pipeline (Moderate Effort).  
3. Run the Temporal Drift and Threshold Aging longitudinal evaluation (Moderate Effort).  
4. Code, train, and extract scores for the FedBN autoencoder (Heavy Effort).  
5. Run the ![][image8] local epoch ablation (Moderate Effort).  
6. Calculate the Fleet JS Divergence correlations (Low Effort).  
7. Calculate the SOC False-Alarm Burden translation metrics (Low Effort).  
8. Write the formal B4 Privacy Leakage analysis (Low Effort).  
9. Integrate the TON-IoT dataset if the timeline permits (Heavy Effort, Optional but highly recommended).  
10. Comprehensively rewrite the Introduction and Methodology to emphasize the \>30% dynamic systems extension (Heavy Effort).

#### **Works cited**

1. State\_of\_the\_Art.md  
2. StatAvg: Mitigating Data Heterogeneity in Federated Learning for Intrusion Detection Systems \- Flower Baselines 1.30.0, accessed May 23, 2026, [https://flower.ai/docs/baselines/statavg.html](https://flower.ai/docs/baselines/statavg.html)  
3. (PDF) FL-MalDrift: a federated learning framework for malware detection under local concept drift \- ResearchGate, accessed May 23, 2026, [https://www.researchgate.net/publication/398700901\_FL-MalDrift\_a\_federated\_learning\_framework\_for\_malware\_detection\_under\_local\_concept\_drift](https://www.researchgate.net/publication/398700901_FL-MalDrift_a_federated_learning_framework_for_malware_detection_under_local_concept_drift)  
4. IFIPSEC2026: 41st IFIP TC11 International Conference on Information Security & Privacy \- CFP, accessed May 23, 2026, [https://easychair.org/cfp/IFIPSEC2026](https://easychair.org/cfp/IFIPSEC2026)  
5. Call for Papers: ELSEVIER Journal of Parallel and Distributed Computing | ICC Blog, accessed May 23, 2026, [https://blogs.mtu.edu/icc/2022/09/call-for-papers-elsevier-journal-of-parallel-and-distributed-computing/](https://blogs.mtu.edu/icc/2022/09/call-for-papers-elsevier-journal-of-parallel-and-distributed-computing/)  
6. FL-MalDrift: Federated learning with client side drift detection and thresholded aggregation, accessed May 23, 2026, [https://www.researchgate.net/figure/FL-MalDrift-Federated-learning-with-client-side-drift-detection-and-thresholded\_fig1\_398700901](https://www.researchgate.net/figure/FL-MalDrift-Federated-learning-with-client-side-drift-detection-and-thresholded_fig1_398700901)  
7. Concept Drift Detection in Federated Networked Systems | Request PDF \- ResearchGate, accessed May 23, 2026, [https://www.researchgate.net/publication/359512406\_Concept\_Drift\_Detection\_in\_Federated\_Networked\_Systems](https://www.researchgate.net/publication/359512406_Concept_Drift_Detection_in_Federated_Networked_Systems)  
8. valeman/awesome-conformal-prediction \- GitHub, accessed May 23, 2026, [https://github.com/valeman/awesome-conformal-prediction](https://github.com/valeman/awesome-conformal-prediction)  
9. \[2410.09284\] Enhanced Federated Anomaly Detection Through Autoencoders Using Summary Statistics-Based Thresholding \- arXiv, accessed May 23, 2026, [https://arxiv.org/abs/2410.09284](https://arxiv.org/abs/2410.09284)  
10. Boosting Gradient Leakage Attacks: Data Reconstruction in Realistic FL Settings \- USENIX, accessed May 23, 2026, [https://www.usenix.org/system/files/usenixsecurity25-fan-boosting.pdf](https://www.usenix.org/system/files/usenixsecurity25-fan-boosting.pdf)  
11. Defending against Reconstruction Attacks through Differentially Private Federated Learning for Classification of Heterogeneous Chest X-ray Data \- PMC, accessed May 23, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC9320045/](https://pmc.ncbi.nlm.nih.gov/articles/PMC9320045/)  
12. Exploring Uncertainty in Medical Federated Learning: A Survey \- MDPI, accessed May 23, 2026, [https://www.mdpi.com/2079-9292/14/20/4072](https://www.mdpi.com/2079-9292/14/20/4072)  
13. \[Literature Review\] Enhanced Federated Anomaly Detection Through Autoencoders Using Summary Statistics-Based Thresholding \- Moonlight | AI Colleague for Research Papers, accessed May 23, 2026, [https://www.themoonlight.io/en/review/enhanced-federated-anomaly-detection-through-autoencoders-using-summary-statistics-based-thresholding](https://www.themoonlight.io/en/review/enhanced-federated-anomaly-detection-through-autoencoders-using-summary-statistics-based-thresholding)  
14. Catching Every Ripple: Enhanced Anomaly Awareness via Dynamic Concept Adaptation, accessed May 23, 2026, [https://arxiv.org/html/2604.14726v1](https://arxiv.org/html/2604.14726v1)  
15. FL-MalDrift: a federated learning framework for malware detection under local concept drift, accessed May 23, 2026, [https://pubmed.ncbi.nlm.nih.gov/41398209/](https://pubmed.ncbi.nlm.nih.gov/41398209/)  
16. FIRCE: A Framework for Intrusion Response and Conformal Evaluation \- arXiv, accessed May 23, 2026, [https://arxiv.org/html/2605.01962v1](https://arxiv.org/html/2605.01962v1)  
17. Securing Networks: Anomaly-Based Network Intrusion Detection with Federated Learning \- Meryem Janati Idrissi, accessed May 23, 2026, [https://janati.me/files/Dissertation.pdf](https://janati.me/files/Dissertation.pdf)  
18. \[D\] Conformal Prediction vs naive thresholding to represent uncertainty : r/MachineLearning, accessed May 23, 2026, [https://www.reddit.com/r/MachineLearning/comments/1r37m2f/d\_conformal\_prediction\_vs\_naive\_thresholding\_to/](https://www.reddit.com/r/MachineLearning/comments/1r37m2f/d_conformal_prediction_vs_naive_thresholding_to/)  
19. Defending Against Data Reconstruction Attacks in Federated Learning: An Information Theory Approach \- USENIX, accessed May 23, 2026, [https://www.usenix.org/system/files/usenixsecurity24-tan.pdf](https://www.usenix.org/system/files/usenixsecurity24-tan.pdf)  
20. PRIVEE: Privacy-Preserving Vertical Federated Learning Against Feature Inference Attacks, accessed May 23, 2026, [https://arxiv.org/html/2512.12840v1](https://arxiv.org/html/2512.12840v1)  
21. Personalized Federated Learning with Hierarchical Two-Branch Aggregation for Few-Shot Scenarios \- PMC, accessed May 23, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC12900011/](https://pmc.ncbi.nlm.nih.gov/articles/PMC12900011/)  
22. Federated Conformal Predictors for Distributed Uncertainty Quantification \- MIT Media Lab, accessed May 23, 2026, [https://www.media.mit.edu/publications/federated-conformal-predictors-for-distributed-uncertainty-quantification/](https://www.media.mit.edu/publications/federated-conformal-predictors-for-distributed-uncertainty-quantification/)  
23. Enhancing anomaly detection in distributed power systems using autoencoder-based federated learning \- PMC, accessed May 23, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC10437833/](https://pmc.ncbi.nlm.nih.gov/articles/PMC10437833/)  
24. Computer science journals \- page 6 \- Elsevier, accessed May 23, 2026, [https://shop.elsevier.com/journals/subjects/physical-sciences-and-engineering/computer-science?page=5](https://shop.elsevier.com/journals/subjects/physical-sciences-and-engineering/computer-science?page=5)  
25. Journals in Software general \- Elsevier, accessed May 23, 2026, [https://shop.elsevier.com/journals/subjects/physical-sciences-and-engineering/computer-science/software/software-general](https://shop.elsevier.com/journals/subjects/physical-sciences-and-engineering/computer-science/software/software-general)  
26. Guidelines for Authors \- IEEE Internet of Things Journal, accessed May 23, 2026, [https://ieee-iotj.org/guidelines-for-authors/](https://ieee-iotj.org/guidelines-for-authors/)  
27. Computer communication networks journals \- page 2 \- Elsevier, accessed May 23, 2026, [https://shop.elsevier.com/journals/subjects/physical-sciences-and-engineering/computer-science/computer-systems-organization/computer-communication-networks?page=1](https://shop.elsevier.com/journals/subjects/physical-sciences-and-engineering/computer-science/computer-systems-organization/computer-communication-networks?page=1)  
28. IEEE CIT 2016 \- NSCLab, accessed May 23, 2026, [http://nsclab.org/cit2016/](http://nsclab.org/cit2016/)  
29. “I've seen this somewhere before\!” What counts as prior publication? \- Elsevier, accessed May 23, 2026, [https://www.elsevier.com/connect/ive-seen-this-somewhere-before-what-counts-as-prior-publication](https://www.elsevier.com/connect/ive-seen-this-somewhere-before-what-counts-as-prior-publication)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAXCAYAAABNq8wJAAABNElEQVR4Xu2WzSpFURSAl1CEwkS6A5E5MVKGJkYkAzeewPBOrhfwADJSSjKTB/AOvIJCMmCmTPzEt+5e29l3d9K57sAe7K++Tmuts27nZ53VFclkMiGr+FXRhvUkySm+43KU78EFvMONqJYMY3iFt1hrL/1wjCtxMhXm8AUvsM9yepzHfosP7Lwk2RY3480gp29Cn/qQxTo+o0U5LfRCP3AdJ3EKj3A/PClV/Px/4gPe45PFncx8XVxvVa9xttXZJYv4Ku3zP4LnOGNxr+WSxM9/uOMn8BAHLN7C3aKcDrrjT6R8/3uG8Qyn40KE3qx+P1XVh+Q33J/x838j7gfL2BH3NvRmf0M//M0OXMPxVmcXlM2/R9fnHj7jUlT7d3S7PErxHyfcQOpbULvEQdeWyWQyGZFvuHhJLfM1IjwAAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAXCAYAAABNq8wJAAABg0lEQVR4Xu2WSytFURiGP6HIJUaSgfgDxEgZiYERGSlGhibEgIHM/ACMlJLM5AeYmSolKUOFZMBMmbjE+7a/Za+92od99uU4aj31tFvrW+ey13rPt4+Ix+OxGYefCV3S11Ql+/ANDjvzNXAA3sIpp1Y1tMMzeAO7oqVvduGoO2nBG23Ra8Xpg8/wCNbpHK/9sF7Hm7quFFy/CE/gCKyNlotlRoKMr1hzPAnuepOOGZ+2sFwSrl+A53Bawg0oFH7RdzgJO2E33IEb9qIyaYRz8EKvHBeCyf8HvId38FHHP2U+KTwBnsQlXIOt0XJ2BuGLRPPPH+Mh7NUx88y5LPA9JiTYrHXJ8UZM/u0e3wG3YYOOuYPzYTk1vIkxeAWXnVoq2PL2JL7/G5rhAexxC2Vgdv9Uco6Ryf+1BLsex6wEp5Gmv5v884uzM5mOlhtx+Tfww1bhExxyar9ReCtld3mQ8D+O3YHoq1U7luQtkNFgRLjjjExFH2ZZYZfakj94Cns8nn/GF9cZSg+gUwghAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEoAAAAaCAYAAAAQXsqGAAADIElEQVR4Xu2YW4hNURzGP6HI/RK5lBlJKSkJKSS5JpdQSDFPlJSiMJ6UJMKDIokYJSkePBDl4cgDIqXwQHLJJQpPlOTyfee/l73Onr33OTvNcWh99WvOXmfNWnt96///rzUDBAUFBQUVVScymRwiR8gC0rmiR7Z6k03kGNkRPfvqRtaQsdFnjTucrCNNcbfGl0zaSq6TZjKAnIEtvKvXL01jyCOymQwh66Pn0V6fvuQ2+ZlgP6qP31CaQN6RqV7bSPKCzPPakupJSuQK6R61dSHnydnos6R+l8gD8pScgkWvNuif0m6YKYoIp17kBjmJ7AXNIj9IW6J9G/kAizZJRqmPP35hKV814BzSAxaK2s16STVDu500ykXLHdLPa/e1EJZCaUapXd9Lf2yU8vgW2QMrbKoR92A7XC85Q7KMSrb7qmaU6paksc6Rg7D0e00uosZCPoI8Jq2IQ7sFNsGi6DlNq8jLAtwlo8q/mS6ZIDOShtRiVDN5BSv8bg2uRmkdMkzSWFfJiqif2AVbv3zIlAY7DptEkzklc7seGgwrsElDajFKC9Zp+QRxdKhIf0SlUeqnmufMlCaSL2Sn19ZOMkKGyHl3MridKMFesl7KMiSrPSnV2I2w6H0Ou4MpWvwalSadtJ/JNVhtTpXLbd05nIbBJtKFL08qvnrxWlHE5N1V3AYlDXFG6eRTNBSR1uBnxl7yjcz+3SM2qoScwHBGzffadIf5ivz6JCmnlxdgMelf/s1spaX8QPIQlRvXhwxFZT06QC5E30nOYP8e1Ua+o9Iol3p514/yVV4v5kzRJArB5MvWSyr2qpcrvbZp5D2ZEj3rtn4ftpmuzZni19pl5C0ZHz1LGnc7YkP0s5V8IpNcpzSpo/JaE5+AXQveoEoYdrCWkmewa8pa2J8hGxAvTu91Ge1Pqi3kJlkNiz6NMdP7XlLqH4ZFnsY+DQsKP6NypckHwcJZJ0+1+tTRUtSoLAh9rkUysoksIdORXQ/VT/dGlYMZsFpbWKpPKnba1aAUyX2dSvtghW0u/l7qNbTGkaOwf2c4FL5BQUFBQUH/h34BYh+vWgg4JNsAAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAXCAYAAAA7kX6CAAABAElEQVR4XmNgGAVEgyQg3g3EwugS+AAHEG+FYhCbaCADxE+AuBVdAhfgAWJJIA4F4t9AHAHE4kDMiqwIG4gH4llAfB+IfwLxUiCeBMTKyIpwAZr4DyRXA8TNQKyFJsfgAsS/oDQyAGnaDMQKQMwPxKuBWBtZQRUQPwdiJWRBIIgG4oVI/HIGJFfB/LcHiLkZIKHZxQCxDRRI6BrXADELiCMCxFcZECYFAXEBEDMyQDShazzAAIlCsIJGIL4DxCuhbFgc4tUIAwJQjAxAfkfXCIpnkGV4gQcQL2eA+okB4ud0hDRuAHLyZAaIYh8GiG2gaCEKgJwFymZiQMyMJkdHAADt8CoaEOoVPQAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADoAAAAXCAYAAABaiVzAAAACF0lEQVR4Xu2WPUgcQRiGv6AB/4qA4g8owYRgI2grgkhIq6AgJAENpElhijQRFEEsRLFSCwtJY+BAwc6fRovrUgiCYEBCwCaQPpAiEU3e92bmbna83b3d22KFfeDhbudb3tuZnf32RDIyMjJSyFt4DJvdQgKkJrsOHmr5PUlSld0Jf8Alt5AAqchugh1wAl7Dl7ANPrRPikmqst/ALXgF/8Ac3IBP7ZNikrrsyPs8AqnKDtvnrXBKKgxzCMpmjeObcAg+8JZDCcueh8uisgu8gH/1p00P3IcHMC/quYiKXzYvZAHWw2fwG3ztOSMcv2zemD3YLeqVc2oKc/AnfGIGHEYk/kT9spn5C/bpY96VE9hYPCMcv+zH8DscE3XNeQ6afW5+hF1rVdSKG4ImyjGuWrltF5TN40E9RthI3GctbrZNr6jdIi3wq5T2+Tj8IN5wv4nyIs5Fdb0Bp0YqySZd8AKOWmPVZjfAdXgJJznAwqKoW72rv5tVNvhNlMdH8BZ+dGqkkmwer4l6H9oLkEQ2YQ9gTpFH2nL4TdTAZvDeHbTwy+aF8Tl7ro/ZlGpL5QJxsttFNTbzvG9btUDCJjoj5bdXELwj06Ky+Q+HHX5Wj9vEyX4npUbHvJy3fBeu1Ar8An/Dz7Dfc4YK+yRqi0RhGN7Af5a8uzZxs9l1d0Qt4it45i3Hg2Fup0uKarJrRL1PA///ZtxX/gN51YAmGfHJoAAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAYCAYAAADKx8xXAAAA80lEQVR4XmNgGHnAE4j/E4mxgoVA/BuIbdDEGYHYCIgfoomDgSAQnwbiB0AsjSoFB3PQBUBAH4g/AfEaIGaBioFoAyBmhfInQmkUEM0A8UM5khjIZpAt3FB+EJIcHIAU/AHiACCWBGJ5IJ4JxK3IitABzH9/gfgJED8C4ldQvguSOgxgDMRfGVD9xwvEq4BYCcpnhoqhALI1wgKmCElMHIgnAzEHlB8BxFkIaUjkzmfAHvEwwAPEi4FYEVkQFjB3GSC2YAMxDBDbQZbAATb/wQAo/iqA+DUQW8IEQcH8jAGReJGjAoR/IcntAGJOiLZRQH0AAAnVOlVKagfwAAAAAElFTkSuQmCC>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGsAAAAXCAYAAAAMX7G2AAABpklEQVR4Xu2YzysFURTHj1CE/NhIlLDBhlgpSxs7yUKh7JSlDf+AjZ1kQUqyUGJvofwB/gEbhWTBTtn4Ed/TvWPuXOPNzHvDo76f+vS699y7mfvOuWdGhBBCCPmfjMP3lC7ZPaTM7MEXOOrNV8AheA0nvRgpA83wHF7B9mjokx045k8mUA/bPHWOlMAAfIRHsMrO6e8grLbjdbsuDf3wDJ7CbesinIJ9zjpSBDNi7qRlZ04zTLOpzo61BDaF4Vi0ZM7DQ9gRDZG80EN5hRNiSlUn3IKr7qIUDMNj2OgHSD4E99UbvIU38N6Os9xRmlVrcMQPkPzQbHiS6H3VIKaUddtxpZ0rhDYOm7BXvjYVrjXBBpKd4L5y36Fa4YaED3ZaTINQCD0sPeBdCZuKOPW9jhSBli59uHHvVwF6CPuwyw946MFqZn3X+pMSCe6rSzHZFMesmCzTg01iwUp+gLj7KkBb9hX4IOmbBu0CtRRmaUxIAvow7yT85ud2guqzEzuBtWZbKlrggZiS2COmOSF/GC2ZmrX61eNCwj+BOuesI4QQQgghv80Hhf1P3HpgRDIAAAAASUVORK5CYII=>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADYAAAAaCAYAAAD8K6+QAAAB6ElEQVR4Xu2WPShGURjHH6EIhUWifCSTIkLKYGAwkRQiNoPRgk3JoKQkg1K+JmIwKMpgFaNJKYSBpBSDj/j/nXvc8973vlzJFZ1f/Xrd8+G9zznPc84rYrFYwqQRvgS035kTFkmwG5Y4f8fDXNgL891hH7MAH2Gtpz0OlsMT2OLp+2nS4a5EL/A4TDTGxSQD7sFjmBPZ9c4srPc2/jCpcAMewCM4D6tFLXYgSuEtXIUJThs/y8RdmUlnXJgwMGZStrcjKJ2itnjAaOPOcZdSnGemIVMjTL4dGAN4gs2i/kkenIGj5qBfgIEtwwlR6XgO1yXgwaHr6xmewVN46Tx/paY6RM0N6j4sepsZGwa2BdtE1RUdgYeiFv9DKuCdRNZXGlyBhc4zj1m2hQ0D4feah0UlvIfDRpsvur7MOyoLTom6O0g77HO7fxW9Edvi1n8UXIk58b+/NEyHJVjg7fDARWB9BpWL99ldNCbq3RqMNh3Yjqh380XXF+8IfpEfXaJ277O7gznf+gWbYObbzNjwRGStm4HpVOSGxHwnv/rScJsH4RWs8fSFBUuA76AD4OcQvIFVepAJT7sLcX+imCcifTD6NmGymhY6TNVpuAZ74CK8FvX79s/DXSoWlb514h5oFovFYrH8K14BXyds1FCxeCEAAAAASUVORK5CYII=>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAaCAYAAACO5M0mAAAA10lEQVR4Xu3RMQsBYRzH8b8wUTaKQQxKySuQkQwMXoGJxS4vQMpokngHXoKBzaSsShlksyoZ+P49d3pcjBb51ae7+91zPf+7E/nnG/EjixJCCCL9soJksEIfTSyxRs9elMQWXficroEbas61BDDBASm3JB2cxIzyiJ5oMRPzkEaPer1A2OmkKmaLlluQBPYYWt1zYcXqCriINZ8mJ2Zrt4xg7nTP+TT6lm1sMBXzWY7imc+OllHEsRPPfO+i811R995wo78rhgHOKMuHrfMYYWwpvqz4ldwBPwAkC14X0V8AAAAASUVORK5CYII=>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAANMAAAAXCAYAAACRfnp7AAABlElEQVR4Xu3avyuFURzH8a9QilIG8qOEEpLFpGQSGRhkVXeiZJc/QMpGKYmMSvwHCptJ2aSUJJtVycDn2/Hk3Mft3rty3q96p/ucczen5znnuWYAAAAAAAAA0tWk2nP5NQBVGlIX6lztf7eiFtRgNA9IQq2Ff/wp1ajqVW/RjN9qVEGdqK7iISBN/epabaoldaVu1EY8qYRRdaaa8wNAirrVvVq3cKdxBfWp5r4/l+Jzt9RYfgBIUZ06UM+qJ7q+pl6t/H7HDxZ21YD9PnSIa8i+APxnvlh80ZxaWFjO//rnSyt/Eudjvlc6sp9Dh1LNZF8A/rNZC49zy9G1TvWodqJrpfgdx+9MPh9IXraY4rvHuHq38vuljC/CeCECyRq28JiXLRw/lfN3RZX2Sxmf7496k/kBIDV+IreqbtWhhSPxF6u8X4q1qGMLj3x9Ft5XAcnyhdOqOtSDVd4v5fmi9HdO2+pOPUUtRvOAZPh+6UPN5wcAVMd/OtRm4SXsm5q26h/zAERG1J4Vvx+aKJoBAACAP+ILCo87DKklzZ4AAAAASUVORK5CYII=>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAAXCAYAAACS5bYWAAAAi0lEQVR4XmNgGAWjYOgDBSCOQBccTEATiLOAeB8Q/wXihajSgwuAHBsAxFZA/IRhkDsWBiSB+CHDqGOpD0YdSytAqmM5GCB6iMHCQMwI0UYdQKpjPYF4FpG4A4gFINqoA0h17ICCIenYpQxUTl/UBC4MkJoLVNX+h+IvQHwJiHWR1I2CUTAKRsEgAACY8iIpobDpcwAAAABJRU5ErkJggg==>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC4AAAAaCAYAAADIUm6MAAACV0lEQVR4Xu2WT0hVQRTGv+gPGYVEkUGBJpiJ/SEkIhEC03ChLoxAqEAK0kUtqkXUooXQpmX0RyQIihIjLAgUMVJQLAqCNrkSol2bFlGrIP0+zgx3GrNezwf3RfeDH+/NmblzzzlzZuYCmTL9H2oks+RjjjTZY+lqGblBBkmFa0t3yA/S4trLyUHygexztlRVRh6RTYFtPXkDc3JLYF9L7pOtgS01adnPRbY95At5TFYEdgV0nawLbKnpKNke2Y6ROXIxsm8gp5GUU9FJ9f2dNMQdxazF6rvoVUe+YWF9h1pFVsbGPHTIURAtVt9eCmaAtMUdfynNc5U0xx35SJvuLn5f3zo+X5KauCNN/am+T5En5BMswN1kG3lIOslJco9UuvG6tI6QIXKC1MMyvZncIr2wkpNNp1UfqSKXyQg5jByVS313w85ySSt0FvaC92Q/eQcLQs/fJGfcODmjeeVoF+yumCblZC9pJQ/IbVIC8+Up7NL7pXSGvyWfYbXt+UpmYBN4yRm9vCNoK0MKRiugDGvV9HuAvIaVlqRgzwfPtMNubLV1a8uPKSTvU/8zstq1l6SNZBw/17ffF9rUobS5lUH1K2vDSPaNnPXl5SWHx2CB++8nJaQg0otHYVf+cVh9K5hJ2NKHkuP+ZNpJXsFWQc4qcLVl9zexAlcC9F/7S3Oq/wIKkPVaMkEuIflqlMPKZqlre+2ClVUPbNM9J9dgTleTF7DNucON70eyAvqI04a+goUJyVuKPsyA6nlN0A6lPv9Bpk2pi8srnkdzaLxXPD5Tpkz/guYBYPlmIz0vf20AAAAASUVORK5CYII=>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAAaCAYAAAAue6XIAAACOUlEQVR4Xu2WQUgVURSGf0mj0BBTSilIRSJXLUTQEAITqkUJhSAobqKE2mQLRZdBiLuI3EQQKYGGKFGaKyVyJyi4EYIg2gotolZB9v+de5nb9B5vyMfrCfPDx3DPzB3uOee/cwdIlWp/qpN8JJ8T0mXTCq8S8pjMkno3lp6Sn+SSGx8g58kn0upiBddx8pIcC2JVZB22sBNBvIJMk5NBrKBSS4disbPkK5kjpUFcSTwiR4JYQdVDTsdifWSXjMTi1eQWIqsUheTXH6QjfqPYlM2vRakW8h1/+/VfJf9/IO8Reb2M3IRtVFlrheyQZnc/sbL5dS8ahG1MLy1SVqtzY9ntHayriaWN8wz59au6oy6pCNl0D38mk0hJ/KqEdFDoe6vE/JfkMKyC+mZfg9lJqiGriFqsIrwil93YJ/OQPId9bWSTnMrlVy10mIyRcrIAq4oOizewJPTMC/LAzQlbrIOnn1yHnZg6FZXMhotp7hS5+ntmBqkyevgLzKueb2QbUYWkdrIFq7pefBRWhV6yBKvuIfIaUeVCv+r5WlhHvC3CZHyV87Jf9JJMVVf7VG1JiWjnNyKzXxvImrtKSkabTVKVN5GnHyW1fDIYV5IzsMVecTFZ4S25QLphfj1Hbrj7Wpwqqy7px0jv9JXU3EWYrfasUzCfDpA7ZALW2ouwDXeXPCHLZJw0kXlyn7TBpEXPkFGYbfROLf62i+f1Jyn0aiiNtemkg24cj3vpcNDm8tIz6lKqVKn+l34BVYtoa7OYN/UAAAAASUVORK5CYII=>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADMAAAAaCAYAAAAaAmTUAAACQUlEQVR4Xu2WT0gVURTGPykjU+mPYoZGtQkiUETcCZko2CKQIgiqTUFBi8KFlEKua+FCcVcQIpKJ4EKhf2BBixZCtbJNQbRrExS1Eqzv49zB+66+eTOSMA/mgx+8e+7MvHvmnu/MBXLlyrUVdZMv5FtCeuy27KmCTJCn5KgbS4/IGulz4x3kFPlKOlwsczpIZkmDF9tPlmELb/LiNWSKNHuxTEklMxDEWskvMkd2enElOU5qvVimdIEcD2KXyF9yJ4jXketYL8WykPyySjrDiXJTMb+UpdrJH2z0i69dpDIMptQeWIdMompylewLJ0qpmF8iKcEn5Gw4kUJ7yXPYi4uTPKr/WiAr5FDhdLxk7MeI94ta+TtyIpxIIXXLt6Q+nCgiJf0RKZMp5ZdrZJ58hyXd4uJV5CKsNEdhb17Sy+kni+Q+7EUMkpewk8QYOeyujdOWkknilxuwb00kLVwJnndjLf6M+91LRshuMkO6XFz36zlJlTgZfWPekx8wr0T8Jp9QWNdKUIme82Ja1GdyBeYzf2c09xO2A20ww2v3l5DuSJQ4mTRSjb9GoV8myQNs/iFVF7pFPjhkaN2rZyT1i7QtyagpvIAdZy6TY7CS8TtfIzkC85cWrfOcznI6/2nH1C2nYa39pouV0rYkc5K8IUNYP01r4fKDFqmk7sIaQhdsx9QYHpLT7nr56BUZhpVenOQ1NYxnsA6rEo/8+F+kPxC+5AWVTfgh1fgANpagyi+6Vrt9bxNuI8MH2ly5cmVM/wC5P2goDwflzAAAAABJRU5ErkJggg==>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADMAAAAaCAYAAAAaAmTUAAACd0lEQVR4Xu2WT0hVQRTGv+gPZUWUkYWJtaiIQIloVdgrDHRRiBFEf1ZBQUHhQtSgWgW1CFKkTUFEiBpCm4SsyKBFi6A2QRAJ0q6NYNRKrL6PM1fnje/d5zUX98H94Afvnpl73zkz55wZIFOmTAvRETJGvs+TRnstfVpCeskg2eaepYfkD2lyz0vJITJO9jtb6lRFnpJNnm09+QBzvNqzryFPyFbPliopZdoCWz35SYbIMs+uIHvIWs+WKp0kOwPbGfKXdAT2SnIBs6lYFlK9TJGD4UC5qVi9lKX2kd+YWy++VpDloTGhKmAdspTUbG6R+6QBCVO8WL1EUoD95Fg4kEDryAvYwsVJgdwkq8gO8pWczpsRI0X9CPH1olb+nuwOBxJI3fId2RgOBNKCqatqvqQdek1Wz8yIUal6OU+ekR+woOucXSt3Cpaad2ErL2lxWshzchu2EO3kJewm0U1q3NxCktMHMJvSOhaGycqZGTGaT71chH00khxXgCfcs5xvdr+PkhuwPx8gOWfX+/pOEinoz+R4OOBLZ8xHMgGrlYhf5Avy81oBKtBWzyanvpFzsDrzd0Zjk7Ad2AsreO3+GyS7Emln7sHOxEQNIE7K8VHk18tjcgeF/0RpcoV8cujQ1bv6Rql6iaRArsEuw5IaQbGsSSQ1hRHYdeYs2Q5LGb/zbSa1sPqS07rPqSvp/qcdU7fsgzl5ydmKSQt0GdYItpBdpMvZ/1t7yFvYB6PbtBxXPchJBdUJawg52I6pMTwgh9181dEr2Gor9eKUI9PIT3+9t2hSMYfdRLWgtAkPUj1vwNyVVPpFc7Xb1wtwFSm+0GbKlCll+gcJS2yFUH3D8wAAAABJRU5ErkJggg==>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADMAAAAaCAYAAAAaAmTUAAACcElEQVR4Xu2WS8hNURiGX7nkmlxCIUyUyCWZiZ8oBsol5TpSlAEZuIaZMDAgM0qSXFImyKVQBgaKkUiUzEwUMVJ4n751+vdZ/3/OPsc/Oaf2W0+d/a2911mX7/3WkipVqvQ/Wmk+mS8tsio+6zwNMhfNLTMzPaPL5o9Zk54Hm+Xms1mSYh2nyea2mVSIjTOvFAOfWoiPNtfMtEKso0TKHMhiC8wPc8cMKcSZ5AUzphDrKG02s7PYdvPXHM7iE8xu9aZiVwi//DZL84ZuUyO/dKUWm1/q65eihpmhebBNjVRUyDJRbI6b02aZ2kzxRn6piQneMOvyhjY01jxULFwzUWFZ1FkKv5IxW+reaCJmfUXN/UIpf2nm5A1tiGr5wkzMGzLNMB/NBsWx8NycKr7QTGV+2WXumq+KSc9P8RGKFWMVzylWHrE46809c0axEAfNY8VN4ryZnt4t0zzzwSzKGxqpFb/sUZw1NTFwJrgpPTP4ten3anPSDDc3TU+K8z39tCK8xaTfm50q8QxnzGvzTeGVGj/NO9XnNRNkohsLMQZFKvBH+Ky4M7R9VwyGFcXw7P5TtX8lYvcfmEMqmVCrIsefqd4vV81Z9f8Ho8w+8yaBifmWPsr8gqaYbYp+EP/1Vq19WyqKwiPFdWaHosqQMsXKxwAwLv5i0BiX8sr9jx2jWl5XlPa9KdZI7CzXKgoGi8V39xVpO2DNVVSUo+q9TTNw/MAgmdQRRUr0KHaMwnDJrEjv46Mn5pjKzVzrm2Ngq8IOC+veGKBYlXxl8AJbnx+kPI9X3xQkbWrvstsn+mG/IgPom/OGSpj3X6lSpUqhf6BXbWeuncesAAAAAElFTkSuQmCC>

[image17]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAaCAYAAAC3g3x9AAABAUlEQVR4XmNgGAXUAk5AfBeIHxGJXSDasANGIJ4CxCuBWAHKB4E5QPwPiD2gfGYgtgfiB0BsChXDCsSBeBUQiyGJCQLxaQaIZmkkcR4gXgzEMkhiGADk/EI0MX0g/gTEa4CYBUkcZNEkIOZFEsMAoUCshiYWDcT/gbgcTVwYiNMYEMFCNACF328gtkGXIAfgCj+ygTEQf2XADD9kwA3ESUAsgC6BDeAKPxAAheFyIN4MxNeAWBJVGhOAAns+A+HwA/niAgMRBhIbfkQbSEz4gQBeA0Fp8BwQv2OAhB0MfwHi6wwQzegAr4HkgMFrIAcQlwLxdgZISgCFtSeKilEwAgAAqeQ4oLSj0bYAAAAASUVORK5CYII=>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAaCAYAAAC3g3x9AAABS0lEQVR4Xu3UzysEYRzH8a+WsovDRktRuDgpK7mJkoOLg4PyI1fOLlxc5WxzVJIUcl1nd+UmEiV/gIM4Kby/PbPr2WeeyczksIf91Osw3+eZeWa+88yINPJfmcYTXmKaMaf504R9nGEgONYc4AuzwXEGU3jGeFDzphvnKFi1PK7FnNxr1dtxjD6rFore/oZTG8EbLtBs1XWhEjqsWigLGHJqK/jGllPvxJr8tiV2tH+fmHAH0iSqf6kzhg8J968SfSHb2MWkxHj8qP5pdCfoQoNi+qlPslgzw4mudijR/evHI+bFbKEr7NgT3CTp3zAeMOoO2Pmrf5oc9nCPVfH0UPfgDV7F9K7iHXdiFvEli0tsiueicdODZbQFx0e4RVd1RsKsi/kk9dPUuzpBGa32pCTRt3yKOSyJaVWxZkaK6G9M96P+pVqcsUbqMT+9sj3fg2ipowAAAABJRU5ErkJggg==>

[image19]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADsAAAAZCAYAAACPQVaOAAADDUlEQVR4Xu2WS8hNURiGX6EIuUaK/L9CJijJBBkQBiS3hJkZM5KSGXJJcr8bGBEpQnIpfxgoAymXgRGREEoYGOB9+vay99nO8Z/z+yN13nraZ++1z1rfu9a3v7Wkppr61+pnBpou5YaCupte5Yf/kzC31lwwO8wRVTfU0xww88oNf0MEOdnsNQfNYtUOcpk5qjAzprJZE81jM1LR5ybz0qw2I8wwRd/3zSHTLf7298SAe8wWRTCjzC3zUBFgUl9zXWGgt5mgMLaw8M4ac9v0ye6nmHVmrFlqlpsl5rxirHbVI6OzRCDvzDWFCURQ3xUrnbTe3DP9C89474kZkt2fNG3K+2Gl92W/Eau9XQ2kLynCDPMnisCfilR8bR4o72+Bwuzx7B6DGMVMUZPMJ+XBb1ClWdo3Z7/RTLNbDaYvMzTOXDEnTGtlc8OieqYA6Xu/+aYwjdLql82ycp8VnwCabp4qT9FVyidisDlTaOuQWJmzGeWC0agwOsu8NzsV2wNKpmqZTc95n8JDLBSl04pJZCVZ0brTtz2xuqwyxYXK+rs9rppmmOfmjWLLGFRom6tI6/bMIsYdr0hZqjfCZEpf2olvl5md3XdYQxV7WEdNdzVbzQfFBKA5qt9sWaTtueyKqN43FFV/o/JPpcOi0JBOd0xLZVNdorB8UWw/fGu1TNV6nlROX7avu4oqjqjih5XXi4bEqlJcbqr+VaXQscVwTaKfZwojGGIHeKVfTSWzVOFqKqYvIr0/Kj4LRHzbFOPVrVZzzFxSBF2PySQMlFM0maACU4mZ+TZzWZV7PGn+NbuWVU5flPpNZhFmi4eXqsJQZ2w/HBbeKopF0grFBBSPdDyjgKVxGJ/TFGlJehaV0pciVRTGXyg3yyQyRrEYVohBSFFSlZRtKAWqiEBPKYrGSsVBnoMC20bRRNpWGHe+wugjxbGxLNKXQ085w5gEDiqpbari0FF+76eojFTLzjg9JTFYi8IEDK9ozcV7o80iM035PlwUcWGoVnwDFJN71VzUHx4ymmqqqaaaaqqT9ANR6Y/vYu0d9QAAAABJRU5ErkJggg==>

[image20]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEoAAAAaCAYAAAAQXsqGAAACrElEQVR4Xu2YTahNURTH/0KRr3xEGHhPUkpKBlIYSD6SjzAgA0aUlKKIqaSUiYEkkoFMGJKBwZPBe0XKgAHJRyKKoZLC/3/XWe4+555z3rn31HHT/tWv3ln33nX2XmfvdTZAJBKJRLplDF1JL9JLdAsdm/pGMVPpUXqFnk6us9TJ3zdoEifoQzpIZ9KbsImPD76XxxL6gh6jc+mh5Hpx8J06+fuKFfQzXR3EFtJ3dFMQyzKZDtH7dGISG0dv01vJ36LX/H3HWdigtSKcKfQRvQ5bEXmsp7/ojUz8JP0KW22i1/wptE+VcAOdBFuKqnZTTKB30TkRXy2P6fQgHrKV/kZ+oRTX53Xy/0X7eISeowdhe/gp7Ak0hQ+4aCLZeMhohVLfKspTFO9gAX1JT6G99A7AbrAtuc5jL33fhU/ootYv89EgNdjsgKtMZJB+gDVmn4P3KM1DBauTv5XsKuwmupmT3dtNMIe+RueAq0xExdHb7BUdSGI6AnxDu1B18rcKoYKo8v5m8CcxBEvSFEUDLopnUY89Alu9b2FnpDNo96iiPEXxFL63deZw5sNupANZGWqOSlxVPdGys4o/oOyAfSJ6M+kN1Q2ag++MWvm9UJuDmM4YP1Den4R62+4u3E5ntH5ZTN6Wn0WfI/3gptF5SPejC/RO8pnwAoTnqKr5O1gK+6EXRTd5kMSa7E+Omr365Z4gtoZ+oauSa52mn8Eepse8KGGv3UU/0eXJtaiSPxc9Ee1r3fga7FjwEc33p5Cd9A3smLIf9s+Qw2ivHo3rHuxNrVXtHKfDdB9sdSjHuuBzZ7T8pejms2HLWW+G0mXYAFo1agtSf1dBEx2gO+halPfDXvKnUH/6Cat6JAdVX2+l8/Q73Yh/t/X6mmX0Muy/G1wt30gkEolE/g/+AAoLtI2xSgcAAAAAAElFTkSuQmCC>

[image21]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEoAAAAaCAYAAAAQXsqGAAADE0lEQVR4Xu2YS6hNYRTH/0KRVx6RV+6VlPJIkm4hSR7JIwxIom5RUooiRleSUiYGSHQzkAlDMjC4MiDkMWBA8sgjihmFwv9/1rc639l37332KY57tf/1q/Otvc/3WN9a6/vOAUqVKlWqVKPqQ+aRE+QkWUn61ryRraFkNzlDDoZ2Usn+FwZbr5ImvI/cIK1kJLkAW3j/6L00TSNPyB4yluwI7anRO+qjg9whM2Df0ViH0MucNYd8IPMj22TyiiyPbEkNJl3kGhkYbP3IJXIxfJbWke+o7UtjfSJtka3H6wjMKYoI1xByk3Qie9eXkJ/kfMK+H+YERc4AcoV8gW2IS2NpTKViIakOqMOlZBAsTLWbzZIvJOkoj5a7ZHhkj7WK/EK6o2TXc+8ny1F6pndypTy+TY6S7bC8vQ/b4WbJF5LlqKQ9Vj1HqW7Vc9RzMiayd9Mk8pQcQDW0t8EGWB3aadpEXjfAPTKl8s10+YSTDiniqFbyBlb4fQ1eo7QOOUzqIF/J3NCWVKN+IL//SmdnYYNoMFec282SdlO7mpxwEUfJOTotn5GWYNMV4DNqHZUMCpUXrV/v5PVfcYQcIs/7yeA70YUCOfsHleWQLHtSqrG7YNH7EnZHOoxqjXK1kOvkLXlAtqBAjfLc1p3DNR42UL1TQMVXEy+KIibvLuQblHSIO0onn07ARqQ11MsMD5bc9bqjVkQ25ew35NcnSWG8oQHWkBGVb2YrLeVHkceoXcgwMg619eg4uRyeSe7g+B41izwka0Nb0jpVt9oiWzdNh03MnaJBFJbJyTZLKvaqlxsj2wLyEdWF6Lb+CLaZbnOnxLV2PXlPZoe25IHREdq+3lOoOjNV2hHltQY+B7sWvEOdfP3L0u35BeyashX2M2QnqtGjeV2FFWVFtWsvuUU2w6JPfSyOnksTYKevald7+NwJuzcWkgYfDQtnnTy5+doEKWq0+0Kfi0iObIGllX7oZtVD1dZFsPcm1j4qLr9TaFdLpUje16l0DFbYluHfpV6P1kxyGvZ3hqPwLVWqVKlSpf4P/QaAV7Zf/6/djQAAAABJRU5ErkJggg==>