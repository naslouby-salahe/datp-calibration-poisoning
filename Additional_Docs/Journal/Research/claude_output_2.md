# Extreme Deep-Research Audit: Transforming DATP into an Elsevier Journal Extension

## TL;DR
- **Submit to Computer Networks (Elsevier, JCR IF 4.6, Q1) as the primary venue** — it is the natural home of Rey et al. 2022 (DATP's foundational N-BaIoT FL paper) and its Guide for Authors explicitly invites "enhanced, extended versions of quality papers presented at conferences." **Internet of Things (Elsevier, JCR IF 7.6, Q1)** is the strongest second choice. **Computers & Security must NOT be targeted**: its current (post-early-2024) scope statement explicitly excludes "items directed to the security of AI/ML systems themselves (such as LLM and federated learning)" — DATP, as an FL paper, would be desk-rejected on scope.
- **The single closest threat to DATP's novelty is Laridi, Palmer & Tam (2024, Scientific Reports), which already benchmarks per-client vs. federated thresholds in autoencoder FL anomaly detection** — but on credit-card fraud / Shuttle / Covertype, not IoT, with no physical-device partition, no taxonomy fallback (DATP's B4), no CV(FPR) metric, and no formal privacy-leakage analysis. The second is Sáez-de-Cámara et al. (2023, Comput. Secur. 131), whose clustered-FL pipeline uses "Local Largest-MSE" per-client thresholds but clusters *models*, never *thresholds*, and never isolates threshold scope. DATP's "threshold scope as sole varied factor with quantile q=0.95 calibration, plus a taxonomy-free B4 fallback" wedge remains genuinely open.
- **To clear the journal bar (implicit ≥30% new material), DATP must add five extensions in priority order: (P1) model-personalization baselines (FedBN + FedProx + FedPer) under fixed compute; (P2) a second physical-device dataset (TON-IoT with IP→client partition, per Belarbi et al. 2023); (P3) a privacy-leakage probe of B1/B4 shared statistics via shadow-model MIA; (P4) a temporal-drift / threshold-recalibration regime referencing FLARE (IWCMC 2023) and FLAME (2024); (P5) a federated-conformal B5 variant grounded in Plassier et al. (ICML 2023).**

## Key Findings

### 1. Closest prior/competitor papers — threat assessment

| # | Paper | Venue | Threat to DATP | Must-cite? | Must-compare? |
|---|---|---|---|---|---|
| 1 | Rey, Sánchez Sánchez, Huertas Celdrán, Bovet & Jaggi (2022). "Federated learning for malware detection in IoT devices." | Computer Networks 204, 108693 (Elsevier) | **Foundational** — same dataset (N-BaIoT, 9 devices), FedAvg, supervised+unsupervised AE. Validates DATP's setup but never separates threshold scope; reports aggregate metrics only. DATP is a methodologically tighter sequel. | Yes (anchor) | Cite as parent baseline; replicate AE |
| 2 | Sáez-de-Cámara, Flores, Arellano, Urbieta & Zurutuza (2023). "Clustered federated learning architecture for network anomaly detection in large scale heterogeneous IoT networks." | Computers & Security 131, 103299 (Elsevier) | **HIGH** — 100-device testbed, clusters devices in FL pipeline, uses per-client "Local Largest-MSE" thresholds. But clustering is at the *model-aggregation* level, not the *threshold-scope* level. They do NOT isolate threshold scope as the experimental variable. DATP must explicitly contrast: "Sáez-de-Cámara cluster the model; we cluster the threshold." | Yes | Yes — replicate Local-Largest-MSE as DATP's "B5" |
| 3 | Laridi, Palmer & Tam (2024). "Enhanced federated anomaly detection through autoencoders using summary statistics-based thresholding." | Scientific Reports 14:26704 (Nature/Springer) | **HIGHEST** — explicitly compares per-client (Local-KQE, Local-IQR, Local-Percentile, Local-Largest-MSE, Local-POT, Local-MinMax) vs. federated/global (Fed-MSE-StD, Fed-Filtered, Fed-MinMax, their Fed-Threshold) on non-IID FL autoencoder anomaly detection. Verbatim: *"the research compares the performance of the proposed FL threshold calculation technique against conventional local and federated methods across various FL and data distribution scenarios."* They report scenarios where local outperforms federated: *"there are scenarios where a client may benefit more from utilizing a local threshold rather than a federated one."* Mitigating factors: datasets are **Credit Card Fraud Detection, Shuttle, Covertype** — none IoT or IDS; no physical-device partition; no taxonomy/cluster fallback (DATP's B4); no CV(FPR); no MIA. Privacy claim is hand-waved: *"summary statistics aggregate this information into a form that reveals general trends without exposing specific data values"* — but the future-work section concedes *"integrating differential privacy techniques may further enhance data protection."* | Yes (positioning) | Yes — replicate Fed-Threshold as DATP's "B6" on N-BaIoT |
| 4 | Nguyen & Beuran (2025). "FedMSE: Semi-supervised federated learning approach for IoT network intrusion detection." | Computers & Security 151, 104337 (Elsevier) | Medium — N-BaIoT + Dirichlet, shrink-AE + centroid OCC + MSEAvg aggregator. Improves model side, not threshold side. Reports accuracy 93.98±2.90 → 97.30±0.49. The remaining gap is FPR dispersion across clients — exactly DATP's target. | Yes | Yes — stack MSEAvg + B2 |
| 5 | Olanrewaju-George & Pranggono (2025). "Federated learning-based intrusion detection system for IoT using unsupervised and supervised deep learning." | Cyber Security and Applications 3, 100068 (Elsevier OA) | Low/Medium — N-BaIoT + FedAvg AE; 90.93% acc, 93.12% F1 across nine IoT devices. Confirms DATP's diagnosis (per-device variance is real) without offering DATP's remedy. | Yes | Optional |
| 6 | Khraisat, Alazab, Alazab, Obeidat, Singh & Jan (2025). "Federated learning for intrusion detection in IoT environments: a privacy-preserving strategy" (PEIoT-DS). | Discover Internet of Things 5:72 (Springer) | Low — FedAvg + FedAvgM; framing is privacy. Does not address threshold scope. | Yes | No |
| 7 | Belarbi, Spyridopoulos, Anthi, Mavromatis, Carnelli, Khan (2023). "Federated Deep Learning for Intrusion Detection in IoT Networks." | arXiv 2306.02715 (preprint) | Medium-positive — gives DATP a TON-IoT physical-device partition recipe ("one IP = one FL client"). | Yes | No |
| 8 | Mavromatis, De Feo, Khan (2024). FLAME: "Adaptive and Reactive Concept Drift Mitigation for Federated Learning Deployments." | arXiv 2410.01386 (preprint) | Medium — defines drift-mitigation framing DATP currently lacks. | Yes (drift section) | No |
| 9 | Chow, Raza, Mavromatis, Khan (2023). FLARE: "Detection and Mitigation of Concept Drift for Federated Learning based IoT Deployments." | **IEEE IWCMC 2023, pp. 989–995, DOI 10.1109/IWCMC58020.2023.10182870** (peer-reviewed conference paper) | Medium — dual-scheduler FL with 5× reduction in data exchange and 16× reduction in drift-detection latency (per 2024 MDPI Electronics systematic review). | Yes (drift section) | No |
| 10 | "Incremental Federated Learning for Intrusion Detection in IoT Networks under Evolving Threat Landscape." | arXiv 2603.10776 (preprint, 2026) | Medium — most recent FL-IDS drift study; LSTM under cumulative incremental learning and representative learning. | Yes (drift section) | No |
| 11 | FedMADE (Krishnan et al., 2024). "Robust Federated Learning for Intrusion Detection in IoT Networks Using a Dynamic Aggregation Method." | arXiv 2408.07152 | Medium — gives a CICIoT2023 device-aware partition strategy and minority-attack-aware aggregation. | Yes | No |
| 12 | AMAFed: "Adaptive Meta-Aggregation Federated Learning for Intrusion Detection in Heterogeneous IoT." | arXiv 2602.12541 | Low — meta-learning aggregator on ToN-IoT/N-BaIoT/BoT-IoT, orthogonal to threshold scope. | Optional | No |
| 13 | FD-IDS (Peng, Wu, Xiao, 2025). "Federated Learning with Knowledge Distillation for Intrusion Detection in Non-IID IoT Environments." | Sensors 25(14):4309 (MDPI) | Low — proximal-term + KD on Edge-IIoT + N-BaIoT. | Optional | No |
| 14 | Chunduru Sri Abhijit et al. (2025). "A personalized federated hypernetworks based aggregation approach for intrusion detection systems" (PerFedHypID). | Scientific Reports (Nature, 2025) | Medium — benchmarks FedAvg, FedPer, FedRoD on UNSW-NB15 + CSE-CIC-IDS2018; reports 26–30% runtime reductions for hypernetwork approach. Useful as a source for FedPer baseline numbers. | Yes | Yes (cost-equivalence with FedPer) |
| 15 | FedDWC (2025). "Dynamic Weighted Clustered Federated Learning for IoT DDoS attack detection." | Scientific Reports (Nature, 2025) | Medium — clusters similar clients + bi-level optimization for IoT DDoS. Like Sáez-de-Cámara, clusters at the model level. | Yes | No |
| 16 | Astillo, Duguma, Park, Kim, Kim, You (2022). "Federated intelligence of anomaly detection agent in IoTMD-enabled Diabetes Management Control System." | Future Generation Computer Systems 128, 395–405 (Elsevier) | Low — FL anomaly detection in IoT-medical | Cite when discussing FGCS fit | No |
| 17 | Ruzafa-Alcázar et al. "Intrusion Detection Based on Privacy-Preserving Federated Learning for the Industrial IoT." | IEEE Transactions on Industrial Informatics 19(2) | Low-Medium — privacy-preserving FL-IDS angle | Cite in privacy section | No |

### 2. Per-client / adaptive threshold calibration — landscape and DATP's wedge

DATP sits at the intersection of two literatures that are mostly disjoint:
- **Threshold methods for AE anomaly detection** (centralized): max-MSE, mean+kσ, percentile/quantile (q=0.95), POT/EVT, Schlegl-style mixture-fit, KQE.
- **FL aggregation methods for IDS**: FedAvg, FedProx, FedAvgM, FedAdam, MSEAvg, SCAFFOLD, clustered FL, FedNova.

Only **two papers (Laridi 2024 and Sáez-de-Cámara 2023)** systematically combine the two, and neither isolates *threshold scope* (B1/B2/B3/B4 in DATP's taxonomy) as the controlled variable. Sáez-de-Cámara control *aggregation scope* (cluster-level model training, verbatim from their arXiv v2: *"an independent FL training process is started for each identified cluster of devices"*) and fix the threshold at per-client Largest-MSE. Laridi control *summary statistic* (federated mean + k·std vs. local quantile) but use non-IoT tabular data and never construct a taxonomy-free fallback. **DATP's wedge — "threshold scope as the sole varied factor under fixed FedAvg/E=1/full participation/quantile-q=0.95 calibration, with a taxonomy-free B4 cluster-mean fallback that recovers ~52% of the per-device gain — remains unoccupied.**

### 3. Model-personalization baseline landscape for IoT/IDS FL

- **FedPer / FedRoD / FedAvg** were directly benchmarked on CSE-CIC-IDS2018 and UNSW-NB15 in Chunduru et al. 2025 (Sci Rep). Runtime savings of 26.3–26.6% for FedPer over FedAvg are reported, with absolute runtimes (244 min on CSE-CIC-IDS2018, 213 min on UNSW-NB15 for 100 rounds of PerFedHypID).
- **FedProx + FedAvg + FedAdam** on CICIoT2023 with 1D-CNN: published in a 2024 IEEE conference (FedProx more stable under heterogeneity; FedAvg sensitive to non-uniform distributions).
- **FedBN / Ditto / APFL / Per-FedAvg**: searches did not surface a single peer-reviewed paper that applies these specifically to N-BaIoT under K=9 physical devices. **This is an open lane and a DATP strength** — DATP can claim to provide the first apples-to-apples FedBN/Ditto-vs-threshold comparison on N-BaIoT.
- **Clustered FL**: Sáez-de-Cámara 2023; FedDWC 2025; lightweight cluster-based FL arXiv 2602.12543 with 2.47× training-time reduction and 99.22/99.02% accuracy on ToN-IoT/CICDDoS2019.

**Recommendation**: add FedBN + FedProx + FedPer under fixed compute. Expected outcome: FedBN+B2 outperforms either alone; B2-alone is within ε of FedPer-alone at a fraction of the communication cost. This converts DATP from "isolated threshold-scope ablation" to "calibration-time personalization is competitive with training-time personalization."

### 4. Temporal drift / recalibration landscape

- **FLARE** (Chow, Raza, Mavromatis, Khan, 2023). Published at **IEEE IWCMC 2023, pp. 989–995, DOI 10.1109/IWCMC58020.2023.10182870**. Dual-scheduler FL with reactive drift detection, 5× reduction in data exchange and 16× reduction in drift-detection latency relative to fixed-interval scheduling (corroborated by the 2024 MDPI Electronics systematic review: *"The framework achieves significant improvements, including a 5× reduction in data exchange and a 16× reduction in detection latency."*).
- **FLAME** (Mavromatis, De Feo, Khan, 2024, arXiv 2410.01386): adaptive + reactive concept-drift mitigation for FL-IoT; PCA-based drift detection with dynamic model depth.
- **Incremental FL for IDS under evolving threats** (arXiv 2603.10776, 2026): LSTM under cumulative incremental learning and representative learning; data/model-based measures against catastrophic forgetting; demonstrates the accuracy-latency trade-off in dynamic IoT environments.

**Feasibility for DATP**: DATP's per-client threshold (B2) is inherently easier to *recalibrate* than model parameters. A journal version can demonstrate this directly via a Regime D ("drift Regime"): freeze the model, recalibrate the threshold every Δt rounds on a rolling benign window, and compare against full-model retraining on worst-client metrics. This is a low-cost, high-novelty extension.

### 5. Privacy-leakage literature relevant to shared calibration statistics

DATP's B1 (shared client-averaged threshold) and B4 (cluster-mean) reveal per-client benign-error summaries. Relevant literature:
- **Bai, Hu, Ye, Li, Wang & Xu (2024). "Membership Inference Attacks and Defenses in Federated Learning: A Survey."** ACM Computing Surveys 57(4), Article 89.
- **Chen et al. "Membership Information Leakage in Federated Contrastive Learning"** (arXiv 2404.16850) — leakage from encoder outputs.
- **Zare & Shamsinejadbabaki (2026). "Res-MIA: A Training-Free Resolution-Based MIA on FL Models"** (arXiv 2601.17378) — frequency-sensitive overfitting as a previously-underexplored leakage source.
- **"Unveiling Client Privacy Leakage from Public Dataset Usage in Federated Distillation"** (arXiv 2502.08001) — label-distribution inference + LiRA-style MIA from inference outputs only.
- **"DP-FL with Adaptive Clipping Thresholds"** (Future Internet 18(3):148, 2026) — dynamic-threshold DP-FL framework using membership-inference ROC-AUC as the privacy metric.

**No published paper yet quantifies privacy leakage from shared reconstruction-error statistics (mean / variance / p95) in FL anomaly detection.** This is a wide-open lane that DATP can claim as a new contribution. Concrete proposed experiment: shadow-model MIA against the B1 aggregated summary; show B2 (no sharing) is privacy-strictly-better than B1 and B4.

### 6. Threshold-variant landscape (conformal, quantile, shrinkage)

- **Conformal anomaly detection (centralized)**: Laxhammar (Diva-Portal PhD dissertation, 2014) is the canonical NCM-based reference; Burnaev & Ishimtsev 2016 conformalized density/distance AD for time-series.
- **Federated conformal prediction**:
  - **Plassier, Makni, Rubashevskii, Moulines & Panov (2023). "Conformal Prediction for Federated Uncertainty Quantification Under Label Shift."** **ICML 2023, PMLR 202:27907–27947.** Per PMLR: *"This method takes advantage of importance weighting to effectively address the label shift between agents and provides theoretical guarantees for both valid coverage of the prediction sets and differential privacy."*
  - Lu & Kalpathy-Cramer (2022). "Distribution-Free Federated Learning with Conformal Predictions."
  - Humbert et al. (2023, arXiv 2302.06322). "One-Shot Federated Conformal Prediction."
  - "Certifiably Byzantine-Robust Federated Conformal Prediction" (arXiv 2406.01960).
  - "Conformal Prediction for Federated Graph Neural Networks with Missing Neighbor Information" (arXiv 2410.14010).
- **Adaptive thresholds in dynamic CPS**: Ghafouri et al. (arXiv 1606.06707) game-theoretic adaptive thresholds.
- **Quantile / POT**: surfaces as Local-POT in Laridi 2024.

**For DATP**: add a **B5 (federated-conformal)** policy implementing per-client calibration sets with federated quantile aggregation à la Plassier et al. (with DP guarantees), and a **B6 (shrinkage / James–Stein)** policy pulling per-device thresholds toward the family/cluster mean. This grows DATP from a 4-policy to a 6-policy comparison and connects it to the conformal-prediction literature, which currently sits orthogonal to FL-IDS.

### 7. Datasets supporting physical-device partition

| Dataset | Year | Physical-device partition? | Recommended use in DATP |
|---|---|---|---|
| **N-BaIoT** | 2018 | **Yes, 9 devices** (DATP primary) | **Keep as primary** |
| **CICIoT2023** | 2023 | Partial — 105 devices captured, but published FL-IDS partitions (FedMADE 2024; Albanbay et al. 2025 J. Sensor Actuator Netw. 14(4):78; Alzubaidi 2025 ETASR) use Dirichlet or random or attack-class partitions, not physical-device. | Keep as Regime B/C "applicability check"; note that a true physical-device partition is not yet standard (open lane). |
| **TON-IoT** | 2020 | **Yes via IP→client mapping** (Belarbi et al. 2023). | **Add as second physical-device dataset.** |
| **Edge-IIoTset** | 2022 | Limited; Dirichlet-partitioned in FD-IDS 2025 (Sensors 25:4309). | Optional secondary. |
| **TII-SSRC-23** | 2023 | Used in "Dataset-centric evaluation of federated intrusion detection models in IoT networks" (PMC 12824137); flow-level, not strictly device. | Mention as additional landscape dataset. |
| **Bot-IoT** | 2019 | Per-source-IP possible but coarse. | Optional. |
| **IoT-23** | 2020 | Per-capture-file (Stratosphere scenarios). | Optional. |
| **UNSW-NB15** | 2015 | Per-source-IP only; not designed for device heterogeneity. | Avoid as primary. |
| **FedAIoT** (Alam et al., DMLR 2024) | 2024 | Eight authentic-IoT datasets curated for FL benchmarking. | Cite as benchmark-landscape positioning. |

**Recommendation**: DATP journal version should report N-BaIoT (primary, K=9), TON-IoT (with explicit IP→client partition as in Belarbi 2023, ≥20 clients), and CICIoT2023 (Regime B + C as the conference paper already does).

### 8. Elsevier venue profile — decision matrix

| Journal | Latest JCR IF (June 2025 release) | CiteScore | SJR | Quartile | Conference-extension policy | Fit for DATP |
|---|---|---|---|---|---|---|
| **Computers & Security** | 5.4 | 13.3 | 1.445 | Q1 | **DISQUALIFYING SCOPE STATEMENT.** As of early 2024, the journal's official scope reads verbatim: *"AI and ML: As of early 2024, we have instituted a moratorium on consideration of submissions that feature AI or ML as significant components. Thus, submissions about applying an AI/ML technique to system security and privacy topics will not be considered. Also, items directed to the security of AI/ML systems themselves (such as LLM and federated learning) are out of scope of the journal."* DATP is a federated-learning paper and would be desk-rejected. | **REMOVED FROM CONSIDERATION.** |
| **Computer Networks** | **4.6** | 9.3 | 1.17 | Q1 | Verbatim Guide for Authors: *"Enhanced, extended versions of quality papers presented at conferences or workshops can be submitted to our journal for review. Note that papers which were already published with the same contents or simultaneous submission of the same paper to other journals or conferences will not be considered for publication in our journal and will be immediately rejected."* No % stated. Published Rey et al. 2022. | **★ Primary choice.** APC USD 2,440. |
| **Internet of Things** (Elsevier) | **7.6** | 12.4 | 1.527 | Q1 | Standard Elsevier "Multiple, redundant or concurrent publication" policy. | **★ Strong secondary** if framing emphasizes IoT systems/heterogeneity. APC $3,020 OA. |
| **Future Generation Computer Systems** | **6.1 (Clarivate JCR 2025)**; Scopus impact score 8.95 (Resurchify) | 18.7 | 1.551 | Q1 | Standard policy. | Possible. Astillo et al. 2022 (FL anomaly detection IoT-Medical) precedent. Less security-focused. APC $3,040. |
| **Journal of Network and Computer Applications** | **8.0** | 11+ | 2.417 | Q1 | Standard policy. | Possible but less IDS-focused. APC $3,140. |
| **Engineering Applications of Artificial Intelligence** | **8.0** | 11.0 | 1.652 | Q1 | Standard policy. | Possible if framed as "AI-method engineering." APC $3,040. Lower topical fit. |
| **Ad Hoc Networks** | **4.8** | 9.7 | 1.21 | Q1 | Standard policy. | Possible but more wireless/MAC-focused. |

**Note on the "30% new material" rule**: No single Elsevier-wide policy mandates a numeric percentage. The 30% figure most often cited originates from the ICPR best-paper-award invitation pipeline to Pattern Recognition Letters: *"The invited PRL submission will have to include at least 30% new scientific contribution and will undergo a new regular review process"* (per the official ICPR 2026 call). This is an ICPR-specific PRL policy, not a freestanding Elsevier-wide rule. Treat 30% as the implicit editorial floor enforced across Elsevier; DATP's planned extensions easily exceed this threshold.

### 9. Novelty threats and supports

**Threats (claims that may already exist):**
1. *"Per-client thresholds reduce FPR dispersion"* is no longer fully novel. Laridi et al. 2024 (Sci Rep) explicitly demonstrates scenarios where local thresholds outperform federated ones. Sáez-de-Cámara et al. 2023 already use per-client Local-Largest-MSE thresholds. DATP's contribution must be reframed as: *threshold scope as a controlled variable, with held-out evaluation, on physical-device partitioning, including a taxonomy fallback (B4) that recovers ~52% of the gain without per-device calibration data.* No prior paper has the B3/B4 fallback construction.
2. *"B2 equalizes FPR by construction"* is a foreseeable reviewer objection. Counter: held-out FPR across 5 seeds (separate calibration/evaluation splits) is *not* equalized by construction; B2 still drives held-out CV(FPR) from 1.017 to 0.299. Demonstrate with leave-one-device-out cross-validation in the journal version.
3. **Clustered-FL papers (Sáez-de-Cámara 2023; FedDWC 2025; lightweight cluster-FL 2026 arXiv 2602.12543) already cluster** — DATP's B4 looks similar at a glance. Distinguish: B4 clusters *thresholds*, not models.
4. **FL conformal prediction has matured** (Lu 2022; Plassier ICML 2023; Humbert 2023). DATP risks looking dated unless it adds a federated-conformal B5 variant.

**Supports (claims that are genuinely DATP's):**
1. CV(FPR) = 1.017 → 0.299 is, to the best of available evidence, the first published CV-of-FPR measurement across physical IoT devices under controlled threshold scope.
2. B4 (family/cluster mean) as a *taxonomy-free* fallback that recovers ~52% of B2's gain has no precedent in the FL-IDS literature.
3. The B1→B2→B3→B4→null (CICIoT2023 Regime B) gradient is a controlled scientific design absent from prior IoT-FL-IDS work, which has been dominated by accuracy/F1 maximization.
4. The negative result on CICIoT2023 (no improvement under near-homogeneous conditions) is, for FL-IDS, an unusually disciplined publication of a null — this should be foregrounded as part of the journal version's contribution.

## Details

### Detailed Elsevier venue recommendations

**Computer Networks (primary)** is now the highest-fit venue because:
1. It published Rey et al. 2022, DATP's foundational predecessor, with the identical dataset and pipeline (Comput. Netw. 204, 108693).
2. Its Guide for Authors *explicitly* invites extended conference versions and gives a verbatim acceptance clause.
3. JCR IF 4.6 (June 2025 release), CiteScore 9.3, SJR 1.17, Q1 in Computer Networks and Communications.
4. APC USD 2,440 — the lowest among the candidate venues.

**Internet of Things, Elsevier (strong secondary)** is appropriate because:
1. JCR IF 7.6 (the highest among in-scope candidates), CiteScore 12.4, Q1.
2. Scope explicitly covers IoT heterogeneity, edge intelligence, anomaly detection, and security.
3. APC $3,020 OA — the journal is fully open-access, which is a constraint to budget for.

**Computers & Security is excluded.** This is the most important shift in the audit relative to a naive read of "publishes FL-IDS papers" — the journal's published works through 2024–early 2025 (Sáez-de-Cámara 2023; Nguyen & Beuran 2025) predate the AI/ML moratorium. New FL submissions are now out of scope. Verify the moratorium status at submission time.

### Detailed required extensions for journal upgrade

To exceed the implicit ≥30% new-material threshold and address every novelty threat:

**(P1) Model-personalization baseline section.** Add FedBN, FedProx, and FedPer under fixed compute. Show worst-client balanced accuracy and CV(FPR) for each, then for each combined with B2. Expected outcome: FedBN + B2 outperforms either alone; B2-alone is within ε of FedPer-alone at a fraction of the communication cost.

**(P2) Second physical-device dataset.** Add TON-IoT with IP→client partition following Belarbi et al. 2023; aim for ≥20 clients. Re-run B1/B2/B3/B4. Expected outcome: B2 again reduces CV(FPR); B4 again recovers a substantial fraction. This breaks the "9 devices only" limitation.

**(P3) Privacy-leakage analysis of B1/B4.** Implement a shadow-model membership-inference attack (Bai et al. 2024 framework) against the shared client-averaged threshold summary statistic (B1) and the cluster-mean (B4); show that B2 (no sharing) is privacy-strictly-better. Use ROC-AUC of the MIA as the leakage metric, as in the DP-FL with Adaptive Clipping Thresholds paper (Future Internet 18(3):148). This makes DATP one of the very first papers to quantify leakage from *calibration* (as opposed to model parameters) in FL-IDS.

**(P4) Temporal-drift / threshold-recalibration regime.** Add Regime D: temporal split of N-BaIoT (or synthetic drift schedule on CICIoT2023), freeze model, recalibrate threshold every Δt rounds on a rolling benign window. Compare full-model retraining vs. threshold-only recalibration on cost and worst-client metrics. Reference FLAME (arXiv 2410.01386, 2024) and FLARE (IEEE IWCMC 2023, DOI 10.1109/IWCMC58020.2023.10182870).

**(P5) Federated-conformal B5 variant + shrinkage B6 variant.** B5: per-client calibration sets with federated quantile aggregation as in Plassier et al. (ICML 2023, PMLR 202:27907–27947), with DP guarantees. B6: James–Stein shrinkage from per-device toward family/cluster mean. Expected outcome: B5 ≈ B2 at q=0.95 but with distribution-free coverage guarantees; B6 dominates B4 when per-device calibration data is moderate.

**(P6) Statistical method upgrade.** Move bootstrap CIs (10,000 resamples) from supplementary to main text. Add per-device worst-case bounds. Run a paired permutation test for B2 vs. B1 across seeds. Add a sensitivity analysis over q ∈ {0.90, 0.95, 0.99}.

**(P7) Reproducibility package.** Public GitHub with seed-locked code, dataset preprocessing scripts, threshold-policy configs, and drift-schedule generator. The FedMSE repo (github.com/dino-chiio/fedmse) is the right reference standard.

### Detailed novelty defense for likely reviewer objections

- **"B2 trivially equalizes FPR — this is by construction."** → Held-out FPR (5 seeds, calibration/evaluation split) is not equalized by construction; that B2 still drives CV(FPR) from 1.017 to 0.299 on the held-out set is an empirical generalization claim, not a definitional one. Add leave-one-device-out cross-validation.
- **"Per-client thresholds are already in Sáez-de-Cámara 2023."** → They use Local-Largest-MSE; DATP uses calibrated quantile q=0.95. More importantly, Sáez-de-Cámara cluster *models*, not thresholds, and never compare threshold scope. Add a head-to-head B2 vs. Local-Largest-MSE.
- **"Laridi 2024 already compares per-client vs. global thresholds."** → Non-IoT tabular data (Credit Card Fraud, Shuttle, Covertype); no physical-device partition; no taxonomy/cluster fallback (DATP's B4); no CV(FPR); no formal privacy leakage analysis. DATP is the IoT-physical-device-partitioned, taxonomy-aware, leakage-tested counterpart.
- **"No comparison to FedBN/Ditto/Per-FedAvg."** → Addressed by P1 above.
- **"E=1 is unrealistic."** → Justify E=1 as a *control choice* (isolating threshold effects from optimization effects); add sensitivity ablation E ∈ {1, 3, 5}.

## Recommendations

**Staged plan:**

**Stage 1 (4–6 weeks): Frame and minimum-viable extensions.**
- Add Section 2.1 ("Position vs. Laridi 2024 and Sáez-de-Cámara 2023") with explicit head-to-head: replicate Local-Largest-MSE as B5 and Fed-Threshold (Laridi) as B6 on N-BaIoT.
- Move bootstrap CIs to main text (P6).
- Target Computer Networks. **Decision benchmark**: if at the end of Stage 1 the head-to-head shows B2 still reduces held-out CV(FPR) below B5/B6 on N-BaIoT, proceed to submission with Stages 2–3 deferred. If not, recompose around B4 (taxonomy fallback) as the headline.

**Stage 2 (6–10 weeks): One major extension out of {P1, P2, P3}.** Pick the one with the highest marginal impact:
- P3 (privacy MIA) if novelty is the binding constraint;
- P2 (TON-IoT) if "9 devices only" is the binding constraint;
- P1 (FedBN/FedPer baseline) if "no personalization comparison" is the binding constraint.

**Stage 3 (parallel, 4 weeks): P5 (federated conformal B5 + shrinkage B6).** Cheap, high-novelty, ties DATP into the respected uncertainty-quantification literature.

**Stage 4 (optional, 8 weeks): P4 (temporal drift).** Defer to a follow-up paper unless reviewers request.

**Submission decision rule:**
- If extensions P1 + P2 + P3 are all done → submit to Computer Networks.
- If P3 + P5 are done but P2 is not → submit to Computer Networks or Internet of Things.
- If P2 + P5 are done but P3 is not → submit to Internet of Things (which has a stronger IoT-systems framing tolerance for less-than-full security analysis).
- Avoid Computers & Security until/unless the AI/ML moratorium is lifted.

**Stop-conditions (signals to change strategy):**
- If, by end of Stage 1, the head-to-head shows Laridi's Fed-Threshold outperforms DATP's B2 on held-out CV(FPR), recompose around B4 + B5 as a "scope-aware calibration framework" rather than a "B2 wins" paper.
- If a 2026 paper appears that does FL-IDS threshold-scope ablation on N-BaIoT, pivot to a benchmarking-and-reproducibility framing and consider Internet of Things or Discover Internet of Things as a faster venue.

## Caveats

1. **JCR Impact Factors quoted are from the June 2025 JCR release** (covering 2024 citations). The June 2026 release was not available at audit time. Several aggregators (Resurchify) quote Scopus-derived composite "impact scores" that differ from the JCR IF. The most consequential correction here: **Future Generation Computer Systems JCR IF is 6.1 (Clarivate 2025), not 8.95** (the 8.95 figure is the Resurchify Scopus composite). For Computers & Security the JCR IF is 5.4; for Computer Networks 4.6; for Internet of Things 7.6; for JNCA 8.0; for EAAI 8.0; for Ad Hoc Networks 4.8.
2. **Computers & Security AI/ML moratorium is the single most important venue finding.** Verify it is still in place at submission time by re-reading the journal's official scope at https://www.sciencedirect.com/journal/computers-and-security/about/aims-and-scope. The verbatim quote retrieved during this audit was: *"AI and ML: As of early 2024, we have instituted a moratorium on consideration of submissions that feature AI or ML as significant components… items directed to the security of AI/ML systems themselves (such as LLM and federated learning) are out of scope of the journal."*
3. **No Elsevier-wide "30% new material" policy exists in writing.** The 30% figure most often cited is the ICPR best-paper invitation pipeline to Pattern Recognition Letters, not an Elsevier-wide rule. Treat 30% as the implicit editorial floor enforced informally across Elsevier journals; DATP's planned extensions exceed it by a wide margin.
4. **Sáez-de-Cámara 2023 verbatim threshold formula** was not retrievable from the ScienceDirect HTML during this audit (publisher blocks programmatic access). The "Local Largest-MSE" characterization is taken from Laridi et al. 2024's verbatim citation of Sáez-de-Cámara as reference 25: *"Other local methods include the Local Largest MSE (Largest-MSE) (Sáez-de-Cámara et al.25), which bases thresholds on the highest observed MSE."* The arXiv v2 preprint of Sáez-de-Cámara corroborates the architecture, but the published Computers & Security version's exact threshold-equation text should be re-verified at draft time.
5. **DATP's claim that "no physical-device partition for CICIoT2023 is standard"** is supported by FedMADE (arXiv 2408.07152), Albanbay et al. 2025 (J. Sensor Actuator Netw. 14(4):78), and Alzubaidi 2025 (ETASR), all of whom use Dirichlet/random/attack-class partitions on CICIoT2023. The underlying capture does include 105 distinct devices; a future paper could build the partition. DATP should note this as a known-but-unimplemented option.
6. **FL conformal prediction has not yet been applied to FL-IDS specifically** in the literature retrievable to this audit. If a 2026 paper appears that does so, the proposed B5 contribution is reduced from "novel" to "first-in-IDS-context."
7. **All cited preprints are flagged as preprints**; published peer-reviewed papers are anchored to ScienceDirect/Nature/Springer/IEEE/PMLR. Some arXiv preprints carry 2026 IDs (2602.12541, 2602.12543, 2603.10776, 2603.21596, 2601.17378, 2601.06200) and have not yet completed peer review; their inclusion is for landscape awareness, not as authoritative baselines.
8. **The FedAvg/E=1/full-participation setup of DATP is atypical** for modern FL-IDS, where E≥3 and partial participation are standard. The journal version should justify E=1 as a control choice and add a small E sensitivity ablation.

## Search Audit Log

| # | Query | Source type | Date | Key finding | Effect on positioning |
|---|---|---|---|---|---|
| 1 | Rey 2022 N-BaIoT FL Computer Networks | ScienceDirect / Semantic Scholar | 2026-05-23 | Confirmed Rey et al. 2022 Comput. Netw. 204, 108693; same 9 N-BaIoT devices. | **Anchors Computer Networks as venue.** |
| 2 | FedMSE Nguyen Beuran 2025 IoT | ScienceDirect / arXiv | 2026-05-23 | SAE-CEN + MSEAvg on N-BaIoT + Dirichlet; 93.98→97.30% acc. | **Identified** stack-partner baseline. |
| 3 | Olanrewaju-George Pranggono 2025 | ScienceDirect | 2026-05-23 | Cyber Security and Applications 3:100068; FL AE on N-BaIoT, 90.93%. | **Supports** DATP diagnosis. |
| 4 | per-client threshold federated anomaly detection | Nature Sci Rep / arXiv | 2026-05-23 | Laridi 2024 Sci Rep 14:26704 — direct threat; per-client vs. federated comparison. | **Changed** novelty story — must explicitly position against Laridi. |
| 5 | FedBN FedPer Ditto IoT IDS | Nature Sci Rep / arXiv | 2026-05-23 | PerFedHypID (Sci Rep 2025) gives FedPer/FedRoD on UNSW-NB15 + CSE-CIC-IDS2018; no FedBN/Ditto specifically on N-BaIoT K=9. | **Supports** DATP — open lane. |
| 6 | conformal anomaly detection IDS | Diva-portal / arXiv | 2026-05-23 | Laxhammar PhD; Burnaev 2016; Plassier ICML 2023 federated conformal under label shift. | **Identified** B5 federated-conformal opportunity. |
| 7 | Sáez-de-Cámara cluster FL IoT | ScienceDirect / arXiv | 2026-05-23 | Comput. Secur. 131:103299 (2023); cluster *models* not thresholds; uses Local Largest-MSE per-client. | **Confirmed** they cluster the model, not the threshold; DATP wedge survives. |
| 8 | CICIoT2023 FL IDS device partition | MDPI / arXiv | 2026-05-23 | FedMADE (arXiv 2408.07152); Albanbay 2025 J. Sensor Actuator Netw. 14(4):78; no physical-device partition standard. | **Confirmed** Regime B framing. |
| 9 | Dirichlet non-IID FL IoT benchmark | MDPI / arXiv / Springer | 2026-05-23 | FedAIoT (DMLR 2024); Dataset-centric eval (PMC 12824137) across Edge-IIoTset + CICIoT2023 + TII-SSRC-23. | **Identified** FedAIoT as benchmark anchor. |
| 10 | Computers & Security IF scope | JournalMetrics / Resurchify / ScienceDirect | 2026-05-23 | IF 5.4 (JCR 2024); 53d to decision after review; 13.3 CiteScore. | (Pre-enrichment: thought it was primary venue.) |
| 11 | Internet of Things Elsevier IF | ScienceDirect / Resurchify | 2026-05-23 | IF 7.6; CiteScore 12.4; APC $3,020 OA. | **Confirmed** secondary venue. |
| 12 | privacy leakage shared calibration statistics FL | ACM / arXiv | 2026-05-23 | Bai et al. 2024 ACM Comput. Surv. 57(4) Art. 89; no paper quantifies leakage from AE-error summaries. | **Opportunity confirmed** — B1 MIA is novel. |
| 13 | Khraisat 2025 FL IoT anomaly | Springer | 2026-05-23 | Discover IoT 5:72; PEIoT-DS FedAvg/FedAvgM. | **Confirmed** cite. |
| 14 | FGCS IF scope | Resurchify / ScienceDirect / BioxBio | 2026-05-23 | Scopus 8.95 vs. JCR 6.1 (Clarivate 2025); CiteScore 18.7; precedent Astillo et al. 2022. | **Confirmed** as option; corrected IF figure. |
| 15 | JNCA IF scope | JournalMetrics / Resurchify | 2026-05-23 | IF 8.0 (JCR June 2025), Q1. | **Confirmed** as option. |
| 16 | drift FL IDS recalibration | arXiv | 2026-05-23 | FLAME 2024 (arXiv 2410.01386); FLARE 2023 (IEEE IWCMC); Incremental FL-IDS 2026 (arXiv 2603.10776). | **Identified** drift-extension feasibility. |
| 17 | conformal prediction FL anomaly | arXiv / ICML PMLR | 2026-05-23 | Plassier ICML 2023 (PMLR 202:27907–27947); Humbert 2023; Byzantine-robust FCP 2024. | **Identified** B5 variant target. |
| 18 | EAAI Elsevier IF scope | Resurchify / ScienceDirect | 2026-05-23 | IF 8.0 (JCR June 2025), Q1; IFAC affiliate. | **Confirmed** low-fit option. |
| 19 | Computer Networks IF + Ad Hoc Networks IF + Elsevier extension policy (subagent) | ScienceDirect / Elsevier Guide for Authors / PRLetters VSI PDF | 2026-05-23 | Computer Networks IF 4.6 + verbatim "Enhanced extended versions… can be submitted" clause; Ad Hoc Networks IF 4.8; no Elsevier-wide 30% policy; 30% rule found only in ICPR→PRL pipeline. | **Confirmed** Computer Networks as candidate venue; clarified 30% rule. |
| 20 | Sáez-de-Cámara + Laridi verbatim threshold details (subagent) | arXiv v2 / Nature Sci Rep | 2026-05-23 | Sáez-de-Cámara: per-client Local Largest-MSE, model-level clustering. Laridi: yes compares per-client vs. federated, datasets Credit Card / Shuttle / Covertype, no formal MIA, future-work flags DP. | **Refined** DATP's distinguishing claims. |
| 21 | Enrichment pass: venue scope + landmark paper venues | Multiple | 2026-05-23 | **Critical: Computers & Security has explicit AI/ML moratorium covering federated learning since early 2024; FLARE is IEEE IWCMC 2023 (DOI 10.1109/IWCMC58020.2023.10182870), not just an arXiv preprint; FGCS Clarivate JCR IF is 6.1 not 8.95; the 30% rule is ICPR-PRL specific, not Elsevier-wide.** | **Contradicted** original primary-venue recommendation; **C&S removed, Computer Networks promoted to primary.** |