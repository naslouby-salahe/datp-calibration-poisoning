# DATP Journal-Extension Audit Report
*Device-Aware Threshold Personalization — Elsevier journal transformation strategy*

---

# 1. Executive Verdict

## 1.1 One-Sentence Verdict
DATP is publishable as an Elsevier journal extension if and only if the authors (a) **abandon Computers & Security (COSE) as the target** because of its explicit early-2024 moratorium on AI/ML and federated-learning submissions, (b) **reposition the paper around the B2-equalizes-by-construction counter-argument** with a calibration-set-size and split-conformal threshold analysis that no existing FL-IoT AE paper has performed, and (c) add **one real device-partitionable dataset (Edge-IIoTset)** plus **one temporal recalibration minimum-viable experiment** — keeping DATP's threshold-personalization identity strictly intact.

## 1.2 Journal Extension Feasibility
**Feasible at the "Strong" level, not Ambitious.** The conference paper is methodologically narrow (threshold scope only, fixed encoder, 9 devices, 5 seeds) — fine for a conference, but currently below the bar of an Elsevier Q1 IoT/security journal. The CV(FPR) finding (1.017 → 0.299) is a real, defensible empirical effect that is *not* claimed anywhere in the federated autoencoder threshold-calibration literature surveyed (Wang et al. Fed-MSE-StD; Sánchez et al. Fed-Filtered; Cao et al. *Scientific Reports* 2024 summary-statistics thresholding — none report per-client FPR dispersion). With the targeted additions below (max 2 datasets, 3 baseline families, 4 threshold variants, 1 temporal family, 6 deeper analyses), this becomes a viable Q1 submission.

## 1.3 Most Important Upgrade
**Pre-empt the "B2 equalizes by construction" reviewer attack** with: (i) a formal derivation in Appendix A showing the construction-implied FPR equalization is bounded by calibration-set size and benign-tail shape; (ii) an empirical calibration-size sensitivity sweep (n_cal ∈ {100, 500, 1k, 5k, 20k} per client); (iii) a **split-conformal B2 variant** (B2-conf) demonstrating that B2's empirical benefit is not a trivial tautology but depends on tail structure that varies across devices. Without these three additions, a strong reviewer will dismiss the headline 71.8% CV(FPR) reduction as a mathematical artifact.

## 1.4 Main Danger
The paper's framing risks two reviewer-fatal critiques: (a) "B2 trivially equalizes FPR by construction — empirical result is a definition, not a contribution"; (b) "Threshold policies are not novel; they are tabulated in Cao et al. (*Scientific Reports* 2024) and used in Sáez-de-Cámara et al. (COSE 2023) — you compare them only as ablations." Both can be neutralized but only by reframing DATP as a **controlled mechanistic study of threshold scope under non-IID**, with calibration-size and conformal extensions, and by explicitly citing the existing federated-threshold landscape.

---

# 2. Current Paper Reconstruction

| Element | Description |
|---|---|
| **Core contribution** | Threshold-scope-only controlled comparison: identical FedAvg autoencoder (E=1, full participation) trained once per seed, encoder + per-client score artifacts reused across four threshold policies B1 (shared-mean), B2 (per-client), B3 (family-mean), B4 (cluster-mean). |
| **Main claim** | Per-client threshold calibration (B2) collapses per-client FPR dispersion (CV(FPR)) under non-IID without changing the encoder; the effect is monotone in heterogeneity (Dirichlet α sweep) and absent under near-homogeneous file-level partitions. |
| **Confirmatory evidence** | Regime A (N-BaIoT, K=9 physical devices, 5 seeds): CV(FPR) 1.017 → 0.299, Δ=0.718, bootstrap CI [0.647, 0.769], all 5 seed deltas positive; B4 recovers ≈52% without taxonomy. |
| **Supporting evidence** | Regime C (Dirichlet α∈{0.1, 0.3, 0.5, 1.0, 10.0, IID}, K=20 synthetic clients): personalization benefit monotone in α; collapses under IID. |
| **Exploratory evidence** | Regime B (CICIoT2023, 63 file-level pseudo-clients, mean pairwise JS=0.004): no improvement; B1 already optimal — interpreted as applicability boundary, not failure. |
| **Main baselines** | Shared-mean (B1), B3 family-mean (negative result, 0.964 vs 1.017), B4 cluster-mean within the threshold family. No external personalized-FL baseline (FedPer/Ditto/FedBN) tested. |
| **Main datasets** | N-BaIoT (Meidan 2018, 9 physical devices); CICIoT2023 (Neto 2023, 105 devices but used at file level); N-BaIoT Dirichlet repartition. |
| **Main metrics** | CV(FPR) primary; P10 Macro-F1, per-client AUROC, BCa bootstrap CIs, per-seed deltas. P10 F1 drops 0.344 → 0.300 under B2 (Ennio Doorbell, AUROC 0.931 — low separability). |
| **Scope boundaries** | Threshold scope is the **sole experimental variable**; encoder, optimizer, rounds, seed pool are fixed. Not a new-method paper for aggregation or model-side personalization. |
| **Current limitations** | 9 physical devices; E=1; 5 seeds; no adversarial robustness; no formal privacy; no hardware/edge evaluation; no concept drift; CICIoT2023 partition randomized at file level (not device level). |

---

# 3. State of the Art Alignment

| Category | Closest Work | Relevance to DATP | Fresh Verification? |
|---|---|---|---|
| **Direct (threshold in FL AE)** | Cao et al. "Enhanced federated AD through AE using summary statistics-based thresholding," *Scientific Reports* 2024 (PMC11535521; arXiv 2410.09284). Surveys Local-KQE (Huong), Local-IQR, Local-Percentile (Novoa-Paradela), Local Largest-MSE (Sáez-de-Cámara), Local-POT (Kea), Local-MinMax (Schlegl), Fed-MSE-StD (Wang), Fed-Filtered (Sánchez). | They survey local vs federated thresholds but do **not** isolate threshold scope on a fixed encoder, and do **not** measure CV(FPR) across clients. DATP fills a clear methodological gap. | No — review available online. |
| **Direct (FL AE on N-BaIoT)** | Rey, Sánchez Sánchez, Huertas Celdrán, Bovet, Jaggi (2022). "Federated Learning for Malware Detection in IoT Devices," *Computer Networks* 204:108693, DOI 10.1016/j.comnet.2021.108693. Federated MLP + AE on N-BaIoT; threshold determination explicitly flagged as open FL challenge. | DATP directly addresses Rey's open challenge of threshold determination in FL. Must cite as motivation. | No — paper read. |
| **Direct (clustered FL IoT AE)** | Sáez-de-Cámara, Flores, Arellano, Urbieta, Zurutuza (2023). "Clustered federated learning architecture for network anomaly detection in large scale heterogeneous IoT networks," *Computers & Security* 131:103299, DOI 10.1016/j.cose.2023.103299. 78-client Gotham testbed; unsupervised AE; dynamic model-parameter clustering. | DATP's B4 cluster-mean threshold is conceptually adjacent but operates on **score statistics**, not model parameters. Must compare and differentiate explicitly. | No. |
| **Adjacent (semi-supervised FL on N-BaIoT)** | Nguyen & Beuran (2025). "FedMSE: Semi-supervised federated learning approach for IoT network intrusion detection," *Computers & Security* 151:104337, DOI 10.1016/j.cose.2025.104337. Shrink-AE + Centroid + MSEAvg aggregation on N-BaIoT + Dirichlet. | Same dataset, same Dirichlet protocol family; DATP can cite as the de-facto 2025 N-BaIoT FL benchmark and contrast with its threshold-scope-only claim. | No. |
| **Adjacent (FL IDS unsupervised+supervised on N-BaIoT)** | Olanrewaju-George & Pranggono (2025). "Federated learning-based intrusion detection system for the IoT using unsupervised and supervised deep learning models," *Cyber Security and Applications* 3:100068, DOI 10.1016/j.csa.2024.100068. Reports 90.93% accuracy, 93.12% F-score on N-BaIoT with FL AE+DNN — aggregate metrics only; no per-client FPR dispersion. | DATP's CV(FPR) result is methodologically orthogonal. | No. |
| **Adjacent (PEIoT-DS)** | Khraisat, Alazab, Alazab, Obeidat, Singh, Jan (2025). "Federated learning for intrusion detection in IoT environments: a privacy-preserving strategy," *Discover Internet of Things* 5(1):72, DOI 10.1007/s43926-025-00169-7. FedAvg + FedAvgM. | Confirms ongoing interest in privacy-preserving FL IDS but no threshold-scope analysis. | No. |
| **Adjacent (DIoT progenitor)** | Nguyen, Marchal, Miettinen, Fereidooni, Asokan, Sadeghi (2019). "DÏoT: A Federated Self-learning Anomaly Detection System for IoT," ICDCS 2019, pp. 756–767, DOI 10.1109/ICDCS.2019.00080. Reports a 95.6% detection rate with zero false positives against Mirai-infected devices in a real smart-home deployment. | Foundational reference but aggregate-level only. | No. |
| **Transferable FL methods** | FedBN (Li et al. ICLR 2021); FedPer (Arivazhagan 2019); Ditto (Li et al. ICML 2021); Per-FedAvg (Fallah 2020); APFL; pFedMe; FedProx; FedAvgM; FedYogi; IFCA. | Most are model-personalization, not threshold-personalization. With a **frozen encoder**, only Ditto-style local heads, FedBN-style local BN statistics, and FedProx-style proximal aggregation are implementable without breaking DATP's isolation discipline. Recommended baselines: FedBN-stats, Ditto-head, FedProx. | No. |
| **Dataset gaps** | DATP uses N-BaIoT (9 devices) and CICIoT2023 at file level. Edge-IIoTset (Ferrag 2022) and ToN-IoT enable device/application-type federation. Pradhan et al. *Scientific Reports* 2025 ("Dataset-centric evaluation of federated intrusion detection models in IoT networks," DOI 10.1038/s41598-025-32567-w) explicitly partition Edge-IIoTset by device/application type and partition CICIoT2023 into 10 device-group clients (verbatim: *"CIC-IoT2023, larger in scale, was partitioned into 10 clients grouped by subsets of devices, resulting in somewhat more uniform distributions"*). | Edge-IIoTset is the single strongest addition; CICIoT2023 device-group repartition is a directly precedented fix. | No. |
| **Fairness / CV-of-FPR provenance** | Pentyala et al. (2024). "Federated Fairness Analytics," arXiv 2408.08214 — defines per-client fairness using Jain's Fairness Index (a bounded nonlinear function of CV across clients), including per-client TPR and FPR differences. Qiu et al. (2026). "FedBEF: Federated Learning With Balance of Performance and Fairness," *Expert Systems*, DOI 10.1111/exsy.70247 — uses "coefficient of variation (standard deviation over mean) of per-client accuracies." FinP (2025, arXiv 2502.17748) — CoV(Loss). FedIDA (2025, arXiv 2505.09295) — variance of FPR-based disparities. | Provide metric provenance; cite alongside CV(FPR). **No peer-reviewed work measures CV(FPR) or per-device FPR equity for federated IoT anomaly detection** — DATP's primary metric is genuinely novel in this application domain. | No. |
| **Privacy** | "Membership Inference Attacks and Defenses in Federated Learning: A Survey," ACM Computing Surveys 2024, DOI 10.1145/3704633. Threshold-based MIA exploitation of model outputs; defenses include partial sharing, secure aggregation, noise perturbation, anomaly detection. Per-example quantile MIA (arXiv 2312.05140) shows per-example threshold MIA outperforms uniform-threshold attacks. | DATP must add a leakage analysis: bounded-summary disclosure, MIA-style probe, DP-noise on shared p95. | No. |
| **Deployment** | No hardware/edge profiling, no Flower/FedML implementation, no Raspberry-Pi benchmark. | Optional; recommend skipping to preserve scope — note as future work. | — |

---

# 4. Weakness Matrix

| ID | Weakness | Severity | Evidence From Paper | Why Reviewer Cares | Fix Type | New Experiment? | Effort | Scope Drift Risk |
|---|---|---|---|---|---|---|---|---|
| W01 | B2 "equalizes by construction" tautology risk | **Critical** | B2 sets per-client q-th percentile → FPR ≈ 1−q on calibration set by definition. | Strongest single attack vector. | Mandatory | Yes — calibration-size sweep + held-out-tail evaluation + conformal variant + Appendix A derivation. | Moderate | Low |
| W02 | Encoder frozen; no model-side personalization baseline | **Critical** | Paper isolates threshold scope only. | Reviewer will ask "Would FedBN/Ditto/FedPer make B2 unnecessary?" | Mandatory | Yes — 3 baselines (FedBN-stats, Ditto-head, FedProx) under same threshold rules. | Heavy | Low (encoder remains frozen within each baseline) |
| W03 | Only 9 physical-device clients | Major | N-BaIoT confirmatory; Regime C is synthetic Dirichlet K=20. | Reviewer wants ≥15–30 real device-partitioned clients. | Mandatory | Yes — Edge-IIoTset device-type partition (6–15 clients). | Moderate | Low |
| W04 | CICIoT2023 file-level partition is not federated-realistic | Major | Pseudo-clients via file shards; mean JS=0.004 hides device heterogeneity. | "You disproved your own claim with the wrong partition." | Mandatory | Yes — re-partition CICIoT2023 by device-MAC / device-group (Pradhan et al., *Scientific Reports* 2025, used 10 device-group clients on this dataset, DOI 10.1038/s41598-025-32567-w). | Moderate | Low |
| W05 | 5 seeds only | Major | BCa CIs reported, but seed count is below community norm. | Statistical-rigor reviewers. | Recommended | Yes — extend to 10 seeds; recomputable from existing pipeline. | Immediate | None |
| W06 | E=1 only; no local-epoch ablation | Major | Single training regime; unclear whether threshold gain survives stronger personalization via local epochs. | Reviewer suspects E>1 narrows B1↔B2 gap. | Recommended | Yes — E ∈ {1, 5, 10} ablation under fixed seeds. | Moderate | Medium |
| W07 | No concept drift / temporal recalibration | Major | Acknowledged in paper. | Operational realism. | Recommended | Yes — chronological-split MVE on CICIoT2023 or Edge-IIoTset. | Moderate | Medium |
| W08 | No formal privacy / leakage analysis of shared p95 | Major | DATP shares per-client statistics for B3/B4. | Privacy reviewer at FL journal demands DP/leakage discussion. | Mandatory | Yes — MIA-probe + DP-noise on shared p95; supplement acceptable. | Moderate | Low |
| W09 | No hardware evaluation | Moderate | Acknowledged. | Optional for a method paper. | Optional | No. | — | High (drifts scope) |
| W10 | No adversarial robustness | Moderate | Acknowledged. | Increasingly expected. | Optional | One label-flip sanity check. | Moderate | High |
| W11 | B3 family-mean negative result under-explained | Major | 0.964 vs B1 1.017 reported, but failure narrative thin. | Reviewer suspects cherry-picked taxonomy. | Mandatory | No experiment — write taxonomy-failure analysis. | Immediate | None |
| W12 | Single dataset for confirmatory result | Major | N-BaIoT only. | Generalization concern. | Mandatory | Yes — Edge-IIoTset as second confirmatory. | Moderate | Low |
| W13 | No comparison with Sáez-de-Cámara model-parameter clustering | Major | DATP's B4 is score-stats clustering; closest prior art is COSE 2023 model-parameter clustering. | Reviewer who knows COSE 2023 will demand differentiation. | Mandatory | Optional rerun; minimum acceptable is explicit qualitative/quantitative comparison table. | Moderate | Low |
| W14 | CV(FPR) is novel as primary metric but unjustified | Major | No metric provenance cited. | Reviewer demands fairness-literature grounding. | Mandatory | No experiment — cite Pentyala 2024 (JFI), FedBEF 2026 (CoV-accuracy), FinP 2025 (CoV-Loss). Report JFI(FPR) alongside CV(FPR). | Immediate | None |
| W15 | No calibration-set size sensitivity | Major | Calibration size fixed. | "What if a client has 200 benign samples?" | Mandatory | Yes — n_cal ∈ {100, 500, 1k, 5k, 20k}. | Moderate | None |
| W16 | No conformal threshold variant | Major | Only empirical quantile (q≈0.95). | Conformal calibration gives finite-sample coverage guarantees. | Mandatory | Yes — split-conformal B2-conf with marginal coverage check. | Moderate | None |
| W17 | No q-sensitivity sweep | Major | q implicit. | Trivial reviewer ask. | Mandatory | Yes — q ∈ {0.90, 0.95, 0.975, 0.99}. | Immediate | None |
| W18 | No shrinkage threshold variant | Moderate | B4 cluster-mean is "hard" assignment; shrinkage interpolates B1↔B2. | Reviewer demands principled interpolation. | Recommended | Yes — α∈{0, 0.25, 0.5, 0.75, 1}. | Immediate | None |
| W19 | P10 F1 degradation under B2 (0.344→0.300) is under-claimed | Moderate | Concentrated in Ennio Doorbell (AUROC 0.931). | Hidden cost of B2. | Mandatory | No experiment — add explicit "failure mode" subsection. | Immediate | None |
| W20 | No "operational FPR burden" quantification | Moderate | CV(FPR) is abstract. | Practitioners want alerts/day. | Recommended | No experiment — multiply per-client FPR × traffic volume. | Immediate | None |
| W21 | No FedAvgM / FedProx / FedYogi sensitivity | Minor | FedAvg only. | Aggregation choice may interact. | Optional | One alternate aggregator. | Moderate | Medium |
| W22 | Limited ablation of B4 cluster features | Moderate | B4 features not exposed. | Reviewer demands interpretability. | Recommended | Re-run B4 with feature subsets (mean / std / skewness / p95). | Immediate | None |

---

# 5. Research-Backed Fix Matrix

| W-ID | Proposed Fix | Literature Support | Exact Experiment / Analysis | Dataset | Baselines | Metrics | Placement | Reviewer Value |
|---|---|---|---|---|---|---|---|---|
| W01 | B2-conformal + calibration-size sweep + formal Appendix A | Cao et al. 2024 (*Scientific Reports*, PMC11535521); split-conformal (Vovk); per-example conformal MIA (arXiv 2312.05140). | Appendix A: B2 derivation showing FPR≈1−q on calibration; add B2-conf with marginal coverage at α=0.05 on held-out benign; n_cal sweep. | N-BaIoT + Edge-IIoTset | B2, B2-conf, B2-shrink | CV(FPR), marginal coverage, F1, P10 F1 | Main | **Critical** — closes biggest attack |
| W02 | 3 personalized-FL baselines under same threshold grid | Ditto (Li 2021); FedBN (Li 2021); FedProx (Li 2020). | Train FedBN encoder (local BN stats), Ditto local heads (frozen body), FedProx encoder. Apply B1–B4 to each. | N-BaIoT | FedAvg, FedBN, Ditto, FedProx | CV(FPR), F1, AUROC | Main table + supplement | High |
| W03, W04, W12 | Edge-IIoTset device-type partition; CICIoT2023 device-MAC repartition | Ferrag 2022 *IEEE Access*; Pradhan et al. *Scientific Reports* 2025 (DOI 10.1038/s41598-025-32567-w) used 6-client device-type partition for Edge-IIoTset and 10-client device-group partition for CICIoT2023. | Regime A' (Edge-IIoTset, K∈{6,15}); Regime B' (CICIoT2023 device-MAC, K≈10). | Edge-IIoTset, CICIoT2023 | Same | Same | Main | High |
| W07 | Temporal recalibration via chronological split | Triplet-AE 2024 (arXiv 2507.00348); CUMAD (arXiv 2404.13690 reports N-BaIoT AE FPR 3.57% → 0.5% with SPRT). | Train-early/test-late chronological split; threshold-aging vs recalibration. | CICIoT2023 or Edge-IIoTset | Frozen vs recalibrated threshold | CV(FPR) over time windows | Main + Supplement | Medium-high |
| W08 | Bounded-disclosure + MIA probe + DP-noise on p95 | ACM Computing Surveys 2024 (DOI 10.1145/3704633); arXiv 2312.05140. | (a) Tabulate disclosures per policy; (b) MIA classifier on tail-quantile leakage; (c) DP-noise on shared p95 with ε∈{1, 5, 10}. | N-BaIoT | DP-noise variants | MIA AUC, CV(FPR) under noise | Supplement | High at IoT journals |
| W14 | Cite FPR-dispersion / fairness lineage; report JFI(FPR) alongside CV(FPR) | Pentyala arXiv 2408.08214; FedBEF Qiu 2026 (DOI 10.1111/exsy.70247); FinP arXiv 2502.17748; FedIDA arXiv 2505.09295. | Add 1-paragraph rationale; report JFI(FPR). | Same | None | JFI(FPR), CV(FPR) | Main Methods | High |
| W15 | Calibration-size sweep | Standard CP theory. | n_cal ∈ {100, 500, 1k, 5k, 20k} per client. | N-BaIoT | — | CV(FPR), threshold MSE | Main figure | High |
| W16, W17, W18 | Threshold-variant grid: q-sweep × shrinkage × {empirical, conformal} | CP (Vovk); James-Stein shrinkage. | q∈{.90,.95,.975,.99} × α∈{0,.25,.5,.75,1}. | N-BaIoT, Edge-IIoTset | — | CV(FPR), F1 | Main heatmap | High |
| W11, W19, W22 | Failure-mode taxonomy | None required. | Subsection: AUROC<0.95 clients lose F1 under B2; family-mean fails when intra-family variance > inter-family; B4 ablation by feature. | Same | — | Per-client AUROC vs F1 delta | Main figure + table | Medium |
| W20 | Operational alert burden | Descriptive only. | FPR × benign volume per device → alerts/day. | Same | — | Alerts/day | Main paragraph | Medium |

---

# 6. Dataset Expansion Matrix

| Dataset | Add or Reject | Reason | Physical Device Split | Temporal Potential | Calibration Suitability | DATP Fit | Preprocessing Burden | Main Risk |
|---|---|---|---|---|---|---|---|---|
| **N-BaIoT** (Meidan 2018) | **Keep — confirmatory** | 9 real devices; established benchmark; Rey/Olanrewaju-George/FedMSE precedents. | 9 physical devices | Very weak | Excellent benign-only AE calibration | Native | Low | Aging dataset — pre-empt with Edge-IIoTset. |
| **CICIoT2023** (Neto 2023, 46,686,579 records: 1,098,195 benign + 45,588,384 malicious; 105 devices = 67 IP-based + 38 Zigbee/Z-Wave) | **Re-partition, keep** | File-level partition is its own weakness; device-MAC repartition fixes it (precedent: Pradhan et al. *Scientific Reports* 2025 used 10 device-group clients on this dataset). | Device-MAC partition feasible | Moderate (capture timestamps exist) | Moderate; PCAP-derived flow features | Native after device repartition | Moderate (MAC mapping) | Confirms partition matters, not encoder. |
| **Edge-IIoTset** (Ferrag 2022, *IEEE Access*) | **ADD — primary new** | Real testbed; 10+ device types; 14 attacks; explicit centralized + federated framing. Pradhan et al. (*Scientific Reports* 2025) used a 6-client device/application-type partition. | Native | Moderate | Good | High — direct device-type federation | Moderate | Different feature schema vs N-BaIoT. |
| Bot-IoT (Koroniotis 2019) | **Reject** | Virtualized testbed; limited device-level partition realism; older feature set. | Weak | Weak | Moderate | Low | Moderate | Outdated and synthetic. |
| ToN-IoT (Moustafa 2020) | **Consider supplement only** | Multi-sensor testbed; sensor-type partition possible. | Moderate | Moderate | Moderate | Medium — feature schema differs | Heavy | Doubles preprocessing effort. |
| IoT-23 (Garcia 2020) | **Reject for primary; cite** | Stratosphere PCAPs, malware-family labeled. Device-level federation is artificial. | Weak | Strong (timestamped captures) | Moderate | Low for confirmatory | Heavy | Adds temporal value but increases scope. |
| UNSW-NB15 (Moustafa 2015) | **Reject** | Not IoT-specific; doesn't fit DATP framing. | None | Weak | Weak | Very low | — | Out of scope. |
| TII-SSRC-23 (TII 2023) | **Reject for primary; cite** | Pradhan et al. used random stratified (near-IID), so it does not stress non-IID. | Weak | Moderate | Moderate | Low | Moderate | — |
| BRIDGE benchmark (2026) | **Cite only** | First formal LODO benchmark across CICIDS17 + CIC-IoT-23 + Bot-IoT + Edge-IIoTset + N-BaIoT. | Heterogeneous | Strong | Moderate | Future direction | Heavy | Out of scope this cycle. |

**Final pick (≤2):** Add **Edge-IIoTset** (device-partition); **re-partition CICIoT2023 by device-MAC** (same source dataset, fixing the existing weakness). Net: 1 new dataset + 1 fixed partition.

---

# 7. Stronger Comparison Matrix

| Comparison | Mandatory? | Scientific Question | Cost | Reviewer Value | Scope Drift | Placement |
|---|---|---|---|---|---|---|
| B1 vs B2 vs B3 vs B4 (current) | Done | Threshold scope under fixed encoder | Done | — | None | Main Table 1 |
| B2 vs B2-conformal | Mandatory | Does coverage guarantee help? | Moderate | Critical (W01) | Low | Main Table 2 |
| B2 vs B2-shrinkage(α) | Mandatory | Smooth B1↔B2 interpolation | Immediate | High | None | Main Figure |
| q-sensitivity sweep | Mandatory | Percentile sensitivity | Immediate | High | None | Supplement table |
| Calibration-size sweep | Mandatory | Does B2 collapse at small n_cal? | Moderate | Critical (W15) | None | Main Figure |
| FedAvg vs FedProx vs FedBN encoder × {B1–B4} | Mandatory | Does model-side personalization absorb threshold gain? | Heavy | High (W02) | Low | Main Table 3 |
| Ditto local-head vs DATP threshold-only | Mandatory | Is DATP redundant with Ditto? | Heavy | High | Low | Main Table 3 |
| Sáez-de-Cámara model-parameter cluster vs DATP score-stat cluster (B4) | Recommended | Differentiate clustering basis | Heavy (full reimpl) | Medium | Medium | Supplement |
| DP-noise on shared p95 (ε∈{1,5,10}) | Mandatory | Does B2's gain survive disclosure-limited statistics? | Moderate | High (W08) | Low | Main figure + supplement |
| Drift: train-early / test-late | Recommended | Threshold aging | Moderate | Medium-high | Medium | Main subsection |
| MIA-style probe on shared statistics | Mandatory | Privacy leakage from B3/B4 | Moderate | High | Low | Supplement |
| FedYogi/FedAvgM aggregator family | Optional | Aggregator × threshold interaction | Moderate | Low | Medium | Skip |
| Hardware/edge latency benchmark | Optional | Operational feasibility | Heavy | Low for method paper | High | Skip — future work |

---

# 8. Threshold Variant Matrix

| Variant | Definition | Why It Matters | Mandatory? | Risk | Placement |
|---|---|---|---|---|---|
| q-sensitivity | q ∈ {0.90, 0.95, 0.975, 0.99} percentile on benign reconstruction error | Trivial reviewer ask; paper is q-implicit | **Mandatory** | None | Main heatmap |
| Pooled p95 | Single global p95 over pooled benign | Naïve baseline | Recommended | None | Supplement |
| Client-averaged shared (B1) | Already in paper | DATP baseline | — | — | Main |
| Sample-weighted shared | Weight by client sample count | Standard FL weighting | Recommended | None | Supplement |
| Per-client (B2) | Already in paper | DATP primary | — | — | Main |
| Family-mean (B3) | Already in paper | Negative result | — | — | Main |
| Cluster-mean (B4) | Already in paper | DATP exploratory | — | — | Main |
| Robust cluster median (B4-rob) | Median over cluster | Mitigates B3 failure when intra-family variance is high | **Mandatory** | None | Main |
| Calibration-size-aware fallback | If client n_cal < N*, fall back to B1 | Operational realism for low-data clients | **Mandatory** | None | Main |
| Shrinkage threshold (B2-shrink) | T = α·T_local + (1−α)·T_shared, α∈{0, .25, .5, .75, 1} | Smooth interpolation; closes W18 | **Mandatory** | None | Main |
| Conformal (B2-conf) | Split-conformal with marginal coverage 1−α | Closes W01 with theoretical guarantee | **Mandatory** | None | Main |
| Drift-aware recalibration (B2-drift) | Re-estimate per-client p95 every Δ from streaming benign | Operational extension; closes W07 | Recommended | Low | Main subsection |

**Final pick (≤4 new):** **(1) q-sensitivity, (2) B2-shrinkage, (3) B2-conformal, (4) calibration-size-aware fallback.** Drift-aware recalibration is folded into Section 9; B4-robust-median appears as a small variant inside the main B4 analysis.

---

# 9. Temporal Drift and Recalibration Plan

## 9.1 Feasibility
- **N-BaIoT** (2018) single-capture, no fine-grained temporal-drift labels → **cannot support real temporal analysis**.
- **CICIoT2023**: capture-session timestamps exist (169 traces). Allows chronological train-then-test splits within one testbed window.
- **IoT-23**: strong temporal structure (multi-year Stratosphere captures), but device-federation realism is weak.
- **Edge-IIoTset**: multi-day capture window — synthetic intra-dataset drift is feasible.

**Verdict**: A *strong* temporal experiment is **risky** (no real multi-year IoT FL drift dataset exists). A *minimum-viable* chronological-split experiment is feasible.

## 9.2 Minimum Viable Temporal Experiment (Recommended)
- Single dataset (CICIoT2023 or Edge-IIoTset chronological).
- Train encoder + calibrate thresholds on first 70% of benign by capture timestamp.
- Evaluate on last 30% with (a) **frozen threshold** and (b) **recalibrated threshold** (one re-fit at boundary).
- Report CV(FPR) drift over time bins.
- **Feasibility: Moderate.**

## 9.3 Strong Temporal Experiment (skip this cycle)
- Streaming sliding-window threshold updates; cross-dataset transfer (N-BaIoT → Edge-IIoTset); concept-drift detector triggering recalibration. **Heavy/Risky.**

## 9.4 Metrics
CV(FPR) over time windows; per-client FPR drift slope; recalibration trigger rate; alert-burden reduction; AUROC stability over time bins.

## 9.5 Interpretation Rules
A non-trivial drift effect is **only claimable** if (a) the chronological split shows FPR drift outside the bootstrap CI on the static split, and (b) recalibration recovers ≥50% of the lost CV(FPR) gain. Otherwise report as **null** and frame as a deployment caveat. Do **not** claim concept-drift handling if the test split is i.i.d. with train.

---

# 10. Deeper Analysis Plan

| Analysis | Purpose | Required Data | Figure or Table | Expected Insight | Priority |
|---|---|---|---|---|---|
| Client-level error CDF overlay | Show why B2 helps when benign-tail shapes differ across clients | Per-client benign errors (already computed) | Figure | Justifies B2 mechanism beyond construction | **Must-do** |
| JS-divergence ↔ DATP-benefit regression | Predict per-client gain from heterogeneity | Per-client benign feature distributions + CV(FPR) gain | Scatter + linear fit | Empirical lever: when to apply DATP | **Must-do** |
| Calibration-set size sensitivity curve | Quantify B2 fragility at low n_cal | n_cal sweep | Figure | Operational guidance | **Must-do** |
| Bootstrap CIs at 10 seeds (extended) | Strengthen statistical claims | 5 additional seeds | Update existing CI table | Reviewer satisfaction | **Must-do** |
| Failure-mode taxonomy | Explain P10 F1 drop and B3 failure | AUROC per client + per-family variance | Table + Figure | Honest negative-result framing | **Must-do** |
| Operational alert-burden quantification | Translate CV(FPR) into alerts/day | Per-client traffic volume | Table | Practitioner relevance | **Must-do** |
| Shrinkage curve | Show B1↔B2 interpolation | New shrinkage run | Figure | Mechanism clarity | **Must-do (in pick of 6)** |
| Per-device fairness (Jain Index on FPR) | Cross-validate CV(FPR) with alternate fairness metric | Existing per-client FPR | Single column | Methodological robustness (W14) | Should-do |
| B4 cluster-feature ablation (mean/std/skew/p95) | Cluster interpretability | Re-run B4 with feature subsets | Small table | Honest ablation | Should-do |
| Conformal coverage check | Verify marginal coverage = 1−α | B2-conf run | Figure | Reviewer-level rigor | Should-do |
| MIA-style leakage probe | Privacy assessment | Shared p95 + benign/attack labels | Supplement figure | W08 closure | Should-do |
| Cluster interpretability (post-hoc) | What does B4 cluster on? | Cluster assignments + device taxonomy | Sankey or table | Reviewer-friendly | Should-do |

**Final pick (≤6 must-do):** (1) Client error CDF overlay; (2) JS↔CV(FPR) regression; (3) Calibration-size curve; (4) Failure-mode taxonomy; (5) Operational alert-burden; (6) Shrinkage curve.

---

# 11. Journal Originality and Conference Extension Plan

## 11.1 What Can Be Reused
- The DATP nomenclature and B1–B4 taxonomy (verbatim).
- Regime A 5-seed N-BaIoT results table — but **must be extended to 10 seeds**.
- Regime C Dirichlet sweep — can be reused unchanged if framed as one figure among many.
- Bootstrap-CI methodology and per-client AUROC reporting.
- All conference-paper figures may be carried over, but each must be expanded with additional series or accompanied by new figures.

## 11.2 What Must Be New (≥40% rule)
- One new dataset (Edge-IIoTset device-partition) → Regime A'.
- One re-partitioned dataset (CICIoT2023 device-MAC) → Regime B'.
- Threshold-variant grid (q × shrinkage × conformal × calibration-size-aware fallback).
- Calibration-set size sensitivity figure.
- Conformal threshold variant with marginal coverage check.
- Privacy/MIA analysis section + DP-noise variant.
- Temporal recalibration MVE (§9.2).
- 3 personalized-FL baselines (FedBN, Ditto, FedProx) × {B1–B4}.
- Failure-mode taxonomy section + Ennio Doorbell deep dive.
- Operational alert-burden quantification.
- Formal Appendix A: derivation of B2's construction-implied FPR equalization and where it breaks (small n_cal, distribution shift).
- Expanded related-work section integrating Cao 2024, Sáez-de-Cámara 2023, FedMSE 2025, Olanrewaju-George 2025, DIoT 2019, Pentyala 2024, MIA-in-FL survey.

This is comfortably >40% new content.

## 11.3 Self-Plagiarism Risk
**Low if disclosed properly.** Risk vectors: (a) verbatim figure reuse — replace or expand each; (b) identical methodology sentences — paraphrase and expand; (c) reusing the same Regime A table without extension — but extending to 10 seeds + adding baselines means it is *not* identical. Keep iThenticate verbatim overlap below 15–20% of the journal manuscript and cite the conference paper explicitly in §1.

## 11.4 Cover Letter Disclosure (template)
"This manuscript is an extended version of our conference paper '[Conference Paper Title]' presented at [Venue, Year]. The conference version established the DATP framework on the N-BaIoT physical-device benchmark with a four-policy threshold-scope comparison (B1–B4) and reported the headline CV(FPR) reduction from 1.017 to 0.299 under per-client thresholding. This journal version contains approximately 50–60% new material, including: (i) a new device-partitioned Edge-IIoTset benchmark (Regime A') and a device-MAC re-partition of CICIoT2023 (Regime B'); (ii) four new threshold variants (q-sensitivity, shrinkage, split-conformal, calibration-size-aware fallback); (iii) three personalized-FL baselines (FedBN, Ditto, FedProx) under the identical threshold grid, demonstrating that DATP's threshold-scope gain is orthogonal to model-side personalization; (iv) a calibration-set-size sensitivity study and a formal Appendix A showing where B2's construction-implied equalization breaks down; (v) a privacy/MIA leakage analysis with DP-noise robustness; and (vi) a temporal recalibration experiment. The original conference results are reproduced and extended from 5 to 10 seeds with no change in the headline conclusions. No part of the conference paper is presented verbatim. We confirm the manuscript is not under consideration elsewhere."

---

# 12. Elsevier Venue Target Matrix

| Rank | Journal | Scope Match | 2024 JIF (verified) | Indexing | Best Framing Angle | Required Upgrades | Desk-Reject Risk | Recommendation |
|---|---|---|---|---|---|---|---|---|
| **1** | **Internet of Things (Elsevier)** ISSN 2542-6605 | Strong — explicit IoT scope including security and ML applications | **11.45 (2024 JIF per Resurchify)**; CiteScore 9.3; Q1; SJR 1.527 | SCIE in Telecom/EEE/CS-InfSys | IoT-security applied paper with operational alert-burden angle | Strong package (Edge-IIoTset + threshold grid + Ditto baselines + privacy + temporal) | Low–medium if AI/ML clearly tied to IoT | **Primary target** |
| 2 | **Computer Networks (Elsevier)** ISSN 1389-1286 | Strong — Rey 2022 published here | 4.6 (2024 JIF per LetPub/Elsevier JCR; older Resurchify data shows ~5.99) | SCIE Q1 | Network-traffic anomaly framing | Same package | Low | **Strong backup** — Rey (2022) lineage |
| 3 | **JNCA** ISSN 1084-8045 | Good — networked applications & security | **8.0 (2024 JIF per Clarivate JCR via wos-journal.info; 5-year IF 7.9; 95.3rd percentile rank in CS Software Engineering)** | SCIE Q1 | Distributed FL application framing | Same | Low–medium | Backup |
| 4 | **FGCS** ISSN 0167-739X | Good — distributed/eScience/IoT; explicitly permits conference extensions | **6.1 (2024 JIF per Clarivate JCR via wos-journal.info; 5-year IF 6.0; 89.8th percentile in CS Theory & Methods)**; note Resurchify's non-JCR impact score is 8.95 | SCIE Q1 | Distributed-systems framing; weaker fit for security-only | Same + emphasize distributed systems | Medium (security-only sometimes redirected) | Backup |
| 5 (**AVOID**) | **Computers & Security (COSE)** ISSN 0167-4048 | **Out of scope per official policy** | 5.4 (2024) | SCIE | — | — | **HIGH (likely desk-reject)** | **Do not submit.** Verbatim from the Elsevier journal page (sciencedirect.com/journal/computers-and-security and shop.elsevier.com/journals/computers-and-security/0167-4048): *"As of early 2024, we have instituted a moratorium on consideration of submissions that feature AI or ML as significant components. Thus, submissions about applying an AI/ML technique to system security and privacy topics will not be considered. Also, items directed to the security of AI/ML systems themselves (such as LLM and federated learning) are out of scope of the journal and should be submitted to a venue primarily about AI/ML."* Despite FedMSE (Nguyen & Beuran 2025, vol 151) and Sáez-de-Cámara et al. (2023, vol 131) having appeared in COSE, FedMSE was submitted in July 2024 and accepted in October 2024 — slipping through despite the policy. Sáez-de-Cámara pre-dates the moratorium. Any new submission today must be assumed to fall under the AI/ML exclusion. |

**FGCS extension policy (verbatim from Elsevier Guide for Authors, elsevier.com/journals/future-generation-computer-systems/0167-739x/guide-for-authors):** *"The paper should have 40% new contributions (that are not only extensions of related work). The letter to the editor should clearly state the conference or workshop where the original paper was submitted and accepted. The letter to the editor should list the new contributions and the sections where the new contributions are. The related work in the FGCS submission should have a section comparing the new material with the original paper."*

Other Elsevier journals (e.g., Pattern Recognition Letters Virtual Special Issues) require ≥30%. The Strong expansion in §13.2 comfortably exceeds 40%.

---

# 13. Three-Level Expansion Roadmap

## 13.1 Minimal Journal Extension

| Item | Detail | Effort |
|---|---|---|
| Datasets | Keep N-BaIoT; re-partition CICIoT2023 by device-MAC | Moderate |
| Baselines | FedProx encoder only | Moderate |
| Threshold variants | q-sensitivity + B2-shrinkage | Immediate |
| Temporal | None | — |
| Deeper analyses | Client-CDF overlay; failure-mode taxonomy; operational alert-burden | Immediate |
| Seeds | 10 | Immediate |
| Privacy | One paragraph + tabular disclosure | Immediate |
| **Risk** | Acceptance unlikely at IoT (JIF 11.45); possibly OK at JNCA/FGCS but desk-reject risk medium |

## 13.2 Strong Journal Extension (RECOMMENDED)

| Item | Detail | Effort |
|---|---|---|
| Datasets | N-BaIoT + Edge-IIoTset device-partition + CICIoT2023 device-MAC re-partition | Moderate-Heavy |
| Baselines | FedBN-stats + Ditto local-head + FedProx (3 families) | Heavy |
| Threshold variants | q-sensitivity + B2-shrinkage + B2-conformal + calibration-size-aware fallback | Moderate |
| Temporal | MVE on Edge-IIoTset or CICIoT2023 chronological split | Moderate |
| Deeper analyses | All 6 must-do | Moderate |
| Seeds | 10 | Immediate |
| Privacy | Bounded-disclosure table + MIA probe + DP-noise on p95 | Moderate |
| Appendix A | Formal derivation of B2 construction equality + boundary conditions | Immediate |
| **Risk** | Low–medium desk-rejection at *Internet of Things* (Elsevier) |

## 13.3 Ambitious Journal Extension

| Item | Detail | Effort |
|---|---|---|
| Datasets | Strong package + IoT-23 temporal supplement | Heavy |
| Baselines | + Sáez-de-Cámara model-parameter-cluster reimplementation | Heavy |
| Threshold | Full grid + drift-aware streaming recalibration | Heavy |
| Temporal | Strong (§9.3) | Heavy/Risky |
| Hardware | Raspberry-Pi edge profiling | Heavy |
| Adversarial | Label-flip / poisoning robustness | Heavy |
| **Risk** | Scope creep; DATP identity dilutes; **NOT recommended in this cycle** |

---

# 14. Final Recommended Package (Strong)

1. **Dataset additions (≤2):** Edge-IIoTset device-partition; CICIoT2023 device-MAC re-partition.
2. **Baseline additions (≤3 families):** FedBN-stats (local BN); Ditto local-head; FedProx encoder.
3. **Threshold additions (≤4):** q-sensitivity; B2-shrinkage; B2-conformal; calibration-size-aware fallback.
4. **Temporal/recalibration (≤1):** Chronological-split + threshold-recalibration MVE on CICIoT2023 or Edge-IIoTset.
5. **Deeper analyses (≤6):** Client-CDF overlay; JS↔gain regression; calibration-size curve; failure-mode taxonomy; operational alert-burden; shrinkage curve.
6. **New figures:** (i) per-client benign-error CDF overlay; (ii) calibration-size sensitivity curve; (iii) shrinkage curve; (iv) JS↔gain scatter; (v) threshold-variant heatmap; (vi) temporal CV(FPR) drift figure.
7. **New tables:** (i) personalized-FL baseline grid (3 baselines × 4 thresholds); (ii) threshold-variant summary; (iii) Edge-IIoTset Regime A' results; (iv) CICIoT2023 device-partition Regime B' results; (v) failure-mode taxonomy; (vi) privacy-disclosure tabulation.
8. **New sections:** (i) Threshold-variant taxonomy; (ii) Calibration-size analysis; (iii) Failure-mode and limits-of-DATP; (iv) Privacy and leakage analysis with DP-noise; (v) Temporal recalibration MVE; (vi) Comparison with personalized-FL baselines (orthogonality).
9. **Supplementary material:** Appendix A (B2 construction-equality derivation and boundary conditions); full hyperparameter tables; per-seed per-client raw results; MIA-probe code description; Docker image + git commit hash.
10. **Claims to strengthen:** "B2 collapses per-client FPR dispersion" (now backed by 2 datasets + conformal variant + calibration-size robustness); "Effect is orthogonal to model-side personalization" (3 baselines); "Effect is monotone in heterogeneity" (Dirichlet + JS regression).
11. **Claims to avoid:** Do NOT claim DATP "solves" non-IID; do NOT claim improved global F1 (P10 F1 drops in low-separability clients); do NOT claim privacy preservation without DP analysis; do NOT claim drift handling without the temporal MVE.

---

# 15. Artifact and Claim Consistency Check

| Proposed Claim | Support Status | Required Evidence | Artifact Needed | Safe Wording |
|---|---|---|---|---|
| "B2 reduces CV(FPR) by 71.8% on N-BaIoT under non-IID" | (1) Already supported | None | Existing artifacts | "B2 reduces CV(FPR) from 1.017 to 0.299 (Δ=0.718, BCa CI [0.647, 0.769]) under physical-device non-IID on N-BaIoT." |
| "Effect is monotone in α heterogeneity" | (1) Already supported | None | Existing Regime C | "Per-client threshold benefit is monotonically related to Dirichlet α, with the effect collapsing under IID." |
| "Effect generalizes beyond N-BaIoT" | (3) Requires new experiments | Edge-IIoTset + CICIoT2023 device-MAC | New runs | "On Edge-IIoTset (device-partitioned, K=…), B2 reduces CV(FPR) from X to Y (CI […])." |
| "Effect is orthogonal to model-side personalization" | (3) Requires new experiments | FedBN/Ditto/FedProx grid | New runs | "Across FedAvg/FedBN/Ditto/FedProx encoders, the B1→B2 CV(FPR) reduction is preserved within ±X% (Table 3)." |
| "Effect is not a construction tautology" | (2) Recomputation + (3) new | Calibration-size sweep + B2-conformal + Appendix A | New runs + derivation | "B2's CV(FPR) equalization is *bounded* by calibration-set size and benign-tail shape (Appendix A); empirically the effect survives n_cal ≥ N* and split-conformal calibration with marginal coverage 1−α=0.95." |
| "Privacy preserved" | (5) **Should not be claimed** without analysis | DP variant + MIA probe | New analysis | "DATP discloses per-client p95 (B3/B4); we quantify leakage via an MIA probe (AUC=Y) and show CV(FPR) gain survives DP-noise with ε≥X." |
| "Handles concept drift" | (5) **Should not be claimed** without temporal MVE | Temporal split + recalibration figure | New runs | "Under a chronological train–test split on CICIoT2023, per-client thresholds drift at a rate of Δ_FPR/window; recalibration recovers Z% of CV(FPR) gain." |
| "Reduces operational alert burden" | (2) Recomputation only | FPR × traffic volume | Existing | "Translating per-client FPR into expected alerts/day at testbed-typical benign volumes, B2 reduces the worst-client alert load from N1 to N2 alerts/day." |
| "DATP is interpretable" | (3) New analysis | B4 cluster ablation + cluster→device-type mapping | New analysis | "B4 clusters are interpretable: X% of cluster assignments align with [device-family / protocol class]." |
| "DATP outperforms FedAvg" | (5) **Should not be claimed** | DATP modifies thresholding, not aggregation | — | Reword: "DATP improves per-client FPR equity on top of FedAvg-trained encoders." |
| "B4 recovers ≈52% of B2 gain without taxonomy" | (1) Already supported | None | Existing | Keep verbatim. |

---

# 16. Reviewer-Loophole Closure Table

| Loophole | Closed By | Remaining Risk | Final Wording Discipline |
|---|---|---|---|
| "B2 trivially equalizes by construction" | Appendix A derivation + calibration-size sweep + B2-conformal + boundary-condition analysis | Persistent reviewer may still argue "you only proved B2 ≈ 1−q on calibration set" | "*On the calibration set*, per-client p_q-thresholding produces FPR≈1−q by construction. *On held-out benign*, the empirical FPR variance is non-trivial and is what we measure." |
| "Single-dataset evidence" | Edge-IIoTset Regime A' + CICIoT2023 device-MAC Regime B' | Edge-IIoTset is still one testbed | "Two physical-device benchmarks (N-BaIoT, Edge-IIoTset) and one large-scale testbed (CICIoT2023 device-partitioned)." |
| "FedBN/Ditto would obviate threshold personalization" | 3-baseline grid showing B1→B2 gain is preserved across encoders | A specific personalization method may close the gap | "Across the personalized-FL methods evaluated, threshold-scope personalization remains complementary; we do not claim exhaustiveness over the personalized-FL family." |
| "No privacy analysis" | Bounded-disclosure table + MIA probe + DP-noise on p95 | DP analysis is empirical, not formal | "We provide empirical leakage analysis; a formal DP proof of bounded threshold disclosure is left to future work." |
| "No drift modelling" | Temporal MVE in §9.2 | Single chronological split is not a full drift model | "We report a minimum-viable chronological-split drift experiment; a full streaming-drift study is outside the scope of this threshold-calibration paper." |
| "Only 5 seeds" | Extended to 10 | Some venues demand 20+ | State seed count clearly; report BCa CIs. |
| "Regime B contradicts the claim" | Reframe as **applicability boundary**: under near-IID (JS=0.004), B1 is already optimal; re-partition CICIoT2023 by device-MAC and show the claim holds when partition is non-IID | None significant after re-partition | "Regime B (file-level partition) and Regime B' (device-MAC partition) jointly delineate the applicability boundary." |
| "CV(FPR) is not a standard metric" | Cite Pentyala et al. 2024 (JFI from CV), FedBEF Qiu 2026 (CoV of accuracy), FinP 2025 (CoV-Loss); report JFI(FPR) alongside CV(FPR) | None | "Following the federated-fairness literature (Pentyala et al. 2024, Qiu et al. 2026), we report CV(FPR) and Jain's Fairness Index on FPR." |
| "P10 F1 drops under B2" | Failure-mode taxonomy: low-separability clients (AUROC<0.95) suffer; honest disclosure | Honest negative | "DATP redistributes detection cost: in low-separability clients (here Ennio Doorbell, AUROC 0.931), per-client thresholding can reduce Macro-F1; this is a deliberate fairness-vs-detection trade-off." |
| "DÏoT / FedMSE / Sáez-de-Cámara already do this" | Differentiation paragraph: DÏoT clusters models; FedMSE personalizes via aggregation; Sáez-de-Cámara clusters on model parameters. None isolates threshold scope on a frozen encoder, none reports CV(FPR). | Differentiation must be explicit, not implicit | Dedicated table comparing methodological axes (encoder, aggregation, threshold, metric). |

---

# 17. Final Recommended Decision Gate

## 17.1 Best Target Journal
**Internet of Things (Elsevier), ISSN 2542-6605, 2024 JIF 11.45 (Q1, SCIE).** Scope explicitly covers IoT security and ML applications; no AI/ML moratorium; recent FL-IDS papers fit naturally. **Backup: Computer Networks** (Rey 2022 lineage, 2024 JIF 4.6). **Do not submit to Computers & Security** under the early-2024 AI/ML moratorium.

## 17.2 Best Expansion Level
**Strong (§13.2).** Minimal is below the bar of an IF=11.45 journal; Ambitious dilutes DATP's identity and risks scope-creep reviewer pushback.

## 17.3 Exact Must-Do List Before Submission
1. Re-run experiments at 10 seeds (**Immediate**).
2. Add Edge-IIoTset device-partition Regime A' (**Moderate**).
3. Re-partition CICIoT2023 by device-MAC, re-run B1–B4 (**Moderate**).
4. Implement and run B2-shrinkage, B2-conformal, calibration-size-aware fallback, q-sensitivity (**Moderate**).
5. Implement and run FedBN/Ditto/FedProx encoders, apply B1–B4 (**Heavy**).
6. Calibration-size sensitivity sweep (**Moderate**).
7. Failure-mode taxonomy section + Ennio Doorbell deep dive (**Immediate**).
8. Operational alert-burden table (**Immediate**).
9. Privacy section: bounded-disclosure table + MIA probe + DP-noise on p95 (**Moderate**).
10. Temporal MVE: chronological split + recalibration (**Moderate**).
11. Appendix A: B2 construction-equality derivation and boundary conditions (**Immediate**).
12. JS↔CV(FPR) regression figure (**Immediate**).
13. Update related work with Cao 2024, Sáez-de-Cámara 2023, FedMSE 2025, Olanrewaju-George 2025, DÏoT 2019, Pentyala 2024, MIA-FL survey (**Immediate**).
14. Cover letter disclosure of conference origin (**Immediate**).
15. Release code + Docker + per-seed raw results (**Immediate**).

## 17.4 Exact Do-Not-Do List
1. Do NOT submit to Computers & Security under current moratorium.
2. Do NOT claim DATP "solves" non-IID.
3. Do NOT claim DATP improves global Macro-F1 — it doesn't.
4. Do NOT claim privacy preservation without the empirical leakage analysis.
5. Do NOT claim concept-drift handling without the temporal MVE.
6. Do NOT add adversarial robustness / hardware profiling / a 4th dataset in this cycle.
7. Do NOT change the encoder, aggregator, or rounds between conference and journal (would break the "extension" framing).
8. Do NOT hide the Regime B null — reframe it as an applicability boundary.
9. Do NOT reuse conference figures verbatim — expand or replace each.
10. Do NOT silently change CV(FPR) definition between conference and journal.

## 17.5 Should the Journal Extension Wait Until Conference Acceptance?
**Yes — partially.** Best practice and the stated FGCS / Elsevier extension policies presume a published, citable conference paper. Begin all new experiments immediately (they are the largest cost), but submit the journal version *after* conference camera-ready. This (a) provides a stable citation, (b) avoids self-plagiarism flags during pre-print overlap, and (c) lets you fold conference reviewer feedback into the journal version. If the conference paper is rejected, fold the strongest reviewer points into the journal manuscript and submit as an original full paper rather than as an extension.

---

# 18. Search Audit Log

| Search Query or Source | Source Type | Date Checked | Key Findings | Confirmed / Changed / Contradicted SoA | Used in Final Recommendation? |
|---|---|---|---|---|---|
| Rey 2022 (Computer Networks) | ScienceDirect; arXiv 2104.09994 | 2026-05-22 | FL MLP + AE on N-BaIoT; threshold determination flagged as open | Confirmed | Yes — primary lineage |
| FedMSE (Nguyen & Beuran COSE 2025) | ScienceDirect; arXiv 2410.14121; GitHub dino-chiio/fedmse | 2026-05-22 | Shrink-AE + Centroid + MSEAvg on N-BaIoT + Dirichlet; submitted July 2024, accepted Oct 2024 (slipped through moratorium) | Confirmed | Yes — benchmark contrast |
| Olanrewaju-George & Pranggono (CSA 2025) | ScienceDirect; Frontiers | 2026-05-22 | FL AE+DNN on N-BaIoT; 90.93% acc / 93.12% F (aggregate only) | Confirmed | Yes — adjacent reference |
| Khraisat 2025 (Discover IoT) | SpringerLink DOI 10.1007/s43926-025-00169-7 | 2026-05-22 | PEIoT-DS; FedAvg + FedAvgM | Confirmed | Yes — related work |
| DÏoT (Nguyen ICDCS 2019) | dblp; arXiv 1804.07474 | 2026-05-22 | First FL anomaly detection in IoT; 95.6% Mirai detection, zero false positives | Confirmed | Yes — foundational |
| **COSE AI/ML moratorium** | shop.elsevier.com/journals/computers-and-security/0167-4048; sciencedirect.com/journal/computers-and-security (verified via subagent) | 2026-05-22 | Verbatim policy text confirmed on official Elsevier pages | **CHANGED journal targeting**: rule out COSE | Yes — decisive |
| Internet of Things (Elsevier) | Resurchify; Scholar9; wos-journal.info | 2026-05-22 | 2024 JIF 11.45 (per Resurchify, 2025 update); Q1; SCIE | Confirmed | Yes — primary target |
| Computer Networks | Resurchify; LetPub; ScienceDirect | 2026-05-22 | 2024 JIF 4.6 (Elsevier JCR); Q1 SCIE | Confirmed | Yes — backup |
| JNCA | wos-journal.info (Clarivate JCR) | 2026-05-22 | **2024 JIF 8.0 (official Clarivate JCR); 5-year IF 7.9; Q1 in CS Software Engineering at 95.3rd percentile** | Confirmed | Yes — backup |
| FGCS | wos-journal.info (Clarivate JCR); Resurchify | 2026-05-22 | **2024 JIF 6.1 (official Clarivate JCR); 5-year IF 6.0; Q1 in CS Theory & Methods at 89.8th percentile**; Resurchify's non-JCR impact score is 8.95 | Confirmed | Yes — backup |
| **FGCS conference-extension policy** | elsevier.com Guide for Authors | 2026-05-22 | Verbatim: *"The paper should have 40% new contributions (that are not only extensions of related work). The letter to the editor should clearly state the conference or workshop where the original paper was submitted and accepted. The letter to the editor should list the new contributions and the sections where the new contributions are. The related work in the FGCS submission should have a section comparing the new material with the original paper."* | Confirmed | Yes — policy basis |
| Elsevier 30% extension policy (PRLetters VSI) | api.journals.elsevier.com | 2026-05-22 | ≥30% baseline at PRL; FGCS ≥40% | Confirmed | Yes |
| Cao et al. summary-statistics federated threshold | arXiv 2410.09284; *Scientific Reports* PMC11535521 | 2026-05-22 | Surveys local + federated thresholds; no CV(FPR) | Confirmed | Yes — direct lineage |
| Sáez-de-Cámara (COSE 2023) | ScienceDirect DOI 10.1016/j.cose.2023.103299; arXiv 2303.15986 (verified via subagent) | 2026-05-22 | 78-client Gotham testbed; AE; dynamic model-parameter clustering; does not measure CV(FPR) | Confirmed | Yes — closest adjacent |
| Pentyala Federated Fairness Analytics | arXiv 2408.08214 | 2026-05-22 | JFI as bounded function of CV; per-client TPR/FPR differences | Confirmed | Yes — metric provenance |
| FedBEF (Qiu 2026, *Expert Systems* DOI 10.1111/exsy.70247); FinP arXiv 2502.17748; FedIDA arXiv 2505.09295 | arXiv; Wiley | 2026-05-22 | CoV-of-accuracy, CoV(Loss), FPR-variance — general FL fairness, **not IoT IDS** | Confirmed; gap remains | Yes |
| Edge-IIoTset (Ferrag 2022) | IEEE Access DOI 10.1109/ACCESS.2022.3165809 | 2026-05-22 | Real testbed, 10+ device types, 14 attacks, native federated framing | Confirmed | Yes — primary new dataset |
| CICIoT2023 (Neto 2023) | MDPI Sensors 23(13):5941 | 2026-05-22 | 105 devices (67 IP + 38 Zigbee), 33 attacks, **46,686,579 labeled records (1,098,195 benign + 45,588,384 malicious, confirmed via independent preprocessing)** | Confirmed | Yes — re-partition basis |
| Pradhan et al. *Scientific Reports* 2025 ("Dataset-centric evaluation of federated intrusion detection models in IoT networks," DOI 10.1038/s41598-025-32567-w) | Nature | 2026-05-22 | **Verbatim: "CIC-IoT2023, larger in scale, was partitioned into 10 clients grouped by subsets of devices, resulting in somewhat more uniform distributions."** Edge-IIoTset partitioned into 6 clients by device/application type. | Confirmed | Yes — partitioning precedent |
| Ditto, FedBN, FedProx | general FL literature | 2026-05-22 | Implementable with frozen-encoder via local heads / BN stats / proximal term | Confirmed | Yes — baseline families |
| MIA in FL survey | ACM Computing Surveys 2024 DOI 10.1145/3704633 | 2026-05-22 | Threshold-based MIA; partial-sharing defenses | Confirmed | Yes — privacy basis |
| Conformal anomaly detection | arXiv 2604.20122; arXiv 2505.01783; GitHub OliverHennhoefer/nonconform | 2026-05-22 | Split-conformal AD; marginal coverage; calibration-set fragility | Confirmed | Yes — B2-conformal basis |
| CUMAD | arXiv 2404.13690 | 2026-05-22 | N-BaIoT AE; FPR 3.57% → 0.5% via SPRT | Confirmed | Adjacent — future direction |
| BRIDGE benchmark | arXiv 2026 | 2026-05-22 | Cross-dataset LODO benchmark for IoT IDS | Confirmed | Future direction only |

---

# 19. Final Red-Team Verdict

## 19.1 Would This Survive a Strong Elsevier Review?
**Yes, at the Strong expansion level, at the IoT / COMNET / JNCA tier, conditionally.** The DATP paper has a genuine empirical finding (CV(FPR) reduction, monotone in α, applicability boundary at IID) that is not duplicated anywhere in the FL-IoT AE literature surveyed. The construction-tautology critique is the single largest risk, and the proposed B2-conformal + calibration-size sweep + Appendix A package neutralizes it. Without those three additions, the paper does not survive a strong review.

## 19.2 What Would Still Be Attacked?
1. **"Personalized FL methods (Ditto, FedRep) would already give per-client thresholds for free via local heads."** Mitigation: explicit baselines + show orthogonality, but a reviewer can still claim the comparison set is incomplete.
2. **"You're measuring fairness, not detection — what's the operational point?"** Mitigation: operational alert-burden quantification + JFI(FPR).
3. **"P10 F1 drops — your fairness gain is a detection loss."** Mitigation: failure-mode taxonomy + honest disclosure; reviewer may still view this as a serious negative.
4. **"Single-encoder paper — would gain disappear at a larger encoder?"** Mitigation: report encoder width/depth sensitivity as a cheap supplement (recommended).
5. **"DP-noise empirical leakage analysis is not a formal guarantee."** Honest concession.
6. **"Temporal MVE is too thin to claim drift handling."** Mitigation: word modestly; do not claim drift "handling," only "preliminary drift evidence."
7. **"Why CV(FPR) and not Jain's Fairness Index alone?"** Mitigation: report both.

## 19.3 Final Priority Order (top 10 actions)
1. **Add B2-conformal variant + Appendix A derivation** (closes W01 — most critical attack).
2. **Calibration-size sensitivity sweep** (closes W15).
3. **Edge-IIoTset device-partition Regime A'** (closes W03, W12).
4. **CICIoT2023 device-MAC re-partition (Regime B')** (closes W04, reframes Regime B).
5. **FedBN + Ditto + FedProx encoder baselines × B1–B4 grid** (closes W02).
6. **Extend seeds to 10; recompute all CIs** (closes W05).
7. **Failure-mode taxonomy section** (P10 F1, B3 family-mean, Ennio Doorbell — closes W11, W19).
8. **Privacy / MIA section + DP-noise on p95** (closes W08).
9. **Temporal MVE: chronological split + recalibration on Edge-IIoTset or CICIoT2023** (closes W07 modestly).
10. **Submit to *Internet of Things* (Elsevier), with *Computer Networks* as backup. Do NOT submit to Computers & Security under current moratorium.**

---

**Brutal honest closing summary.** DATP's headline finding is real and not duplicated in the literature surveyed (Rey 2022, DÏoT 2019, FedMSE 2025, Cao 2024, Sáez-de-Cámara 2023, Olanrewaju-George 2025). The paper's biggest existential risk is **not** technical novelty but reviewer dismissal on the construction-tautology critique and on the dataset narrowness — both fixable at moderate cost. The Computers & Security moratorium is the most consequential single finding of this audit; the authors must not waste a submission cycle there. The Internet of Things (Elsevier) journal at 2024 JIF 11.45 is the correct target, the Strong expansion is the correct level, and the Strong package is feasible in approximately 4–6 months of additional work without changing DATP's threshold-personalization identity.