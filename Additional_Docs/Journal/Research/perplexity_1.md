# 1. Executive Verdict

## 1.1 One-Sentence Verdict
The current DATP paper is strong conference-level work with clear niche novelty on threshold personalization, but it is not yet journal-ready and requires a structured extension to reach Elsevier journal standards.[1]

## 1.2 Journal Extension Feasibility
A strong journal extension is feasible because DATP already has a precise problem formulation, controlled experimental design, and open artifact; however, it lacks broader dataset coverage, personalization baselines, temporal behavior analysis, and any explicit privacy or adversarial treatment expected in top-tier security and networking journals.[2][1]

## 1.3 Most Important Upgrade
The single most important upgrade is to embed DATP’s threshold-personalization study inside a richer FL-IoT IDS space by adding one more well-chosen IoT dataset and a minimal but explicit comparison against model-personalization baselines (e.g., FedBN / Per-FedAvg) under the same threshold framework, without turning the work into a generic FL-IDS paper.[3][1]

## 1.4 Main Danger
The main danger is uncontrolled scope creep: adding too many datasets, baselines, and orthogonal concerns (privacy, robustness, deployment) could dilute DATP’s core identity as a threshold-calibration paper and produce an unfocused generic FL-IDS study that still lacks depth on any single axis.[1]

# 2. Current Paper Reconstruction

| Item | Extracted From Paper | Reviewer Interpretation |
|---|---|---|
| Core contribution | Threshold-only controlled study of client-averaged vs per-client vs family-mean vs cluster-mean reconstruction-error thresholds in a fixed FedAvg autoencoder for FL IoT anomaly detection.[1] | Clear, narrow methodological contribution: isolates threshold scope as the only changed variable in a realistic FL-AE IoT setting; strong internal validity but limited external breadth. |
| Main claim | Under physical-device heterogeneity on N-BaIoT, per-client p95 calibration substantially reduces cross-client FPR dispersion compared to a shared client-averaged threshold, with moderate detection-quality trade-offs, while cluster-mean calibration recovers about half of the benefit without taxonomy; under near-homogeneous CICIoT2023 file-level partitioning, personalization provides no benefit.[1] | Well-bounded claim about FPR-dispersion fairness, not overall accuracy; limited to Mirai/BASHLITE N-BaIoT regime, a single AE, FedAvg, q=0.95, E=1, and specific partitions. |
| Confirmatory evidence | Regime A: N-BaIoT with K=9 physical-device clients, E=1 FedAvg AE, q=0.95; five seeds; B1 vs B2 vs B3 vs B4 comparisons with CV(FPR), IQR, max–min FPR, Macro-F1, Worst-BA, P10 Macro-F1; Dirichlet sweep in Regime C confirming stronger gains at high non-IID and null effect near IID.[1] | Solid controlled evidence that shared thresholds can create large FPR dispersion and that per-client p95 equalizes FPRs; seed-level deltas and bootstrap CI are transparent, though statistical power is limited. |
| Supporting evidence | Regime B CICIoT2023 file-level pseudo-clients as a near-homogeneous applicability boundary where B1 is already good, B2/B4 offer no dispersion benefit; qualitative privacy-leakage discussion for B4 fingerprints; q-sensitivity and shared-threshold construction checks; literature positioning versus FL-AE IoT IDS and FedMSE.[1] | Helpful for interpretation and external validity bounds, but CICIoT2023 use is weakly IoT-device-grounded (file pseudo-clients), privacy is only discussed, and no adversarial or hardware results are provided. |
| Exploratory evidence | Cluster-mean B4 calibration on N-BaIoT (K=3), silhouette-based K for synthetic regimes; Dirichlet α sweep with synthetic clients; JS divergence analysis for CICIoT2023; sensitivity analyses for threshold quantile and shared-threshold construction.[1] | Valuable exploratory layer, but B4 is explicitly marked as exploratory at this fleet size; synthetic Dirichlet regime is secondary and should not anchor strong deployment claims. |
| Main baselines | B0 centralized AE, B1 client-averaged shared p95, B2 per-client p95, B3 family-mean thresholds, B4 cluster-mean; no comparison against model-personalization FL baselines or heterogeneous FL aggregators.[1] | Baselines are appropriate for threshold-scope comparison but incomplete for a journal paper—key FL personalization and aggregation methods are absent. |
| Main datasets | N-BaIoT (nine physical IoT devices, Mirai/BASHLITE botnet attacks), CICIoT2023 (flows aggregated into 63 file-defined pseudo-clients).[1] | N-BaIoT is still standard but aging; CICIoT2023 is timely but used in a way that hides device structure; no Bot-IoT, ToN-IoT, IoT-23, or Edge-IIoTset coverage. |
| Main metrics | Per-client FPR, TPR, Macro-F1, balanced accuracy, P10 Macro-F1, CV(FPR), CV(TPR), IQR(FPR), max–min FPR, coverage ratio; pairwise JS divergence for CICIoT2023.[1] | Metric set is strong for dispersion and fairness; however, there is no ROC/PR curve analysis, no confidence intervals for most metrics, and no temporal or resource metrics. |
| Scope boundaries | No adversarial robustness, no inference-time attacks, no formal privacy guarantees, no hardware or communication-cost evaluation; E=1, full participation; five seeds; claims explicitly scoped to tested datasets, partitions, and protocols.[1] | Scope is honestly declared but narrow for a journal; reviewers will accept bounded claims but expect at least some movement on robustness, temporal behavior, or deployment cost. |
| Current limitations | Small N-BaIoT fleet (K=9), CICIoT2023 pseudo-clients instead of devices, no concept drift, no adversarial evaluation, no privacy mechanism, no hardware or runtime measurements, limited seed count, and no model-personalization comparison.[1] | Limitations section is unusually clear; however, without at least partially addressing some, a journal may view the work as an incremental calibration note rather than a full article. |

# 3. State of the Art Alignment

| Item | Extracted From State of the Art | Relevance to DATP | Needs Fresh Verification? |
|---|---|---|---|
| Closest direct papers | P003, P011, P014, P029, P028, FedMSE, Fed-ANIDS (FL-AE or anomaly-based FL IDS on N-BaIoT, TON-IoT, CICIoT2023).[4][5][3] | Provide the main FL-AE IoT anomaly context and show non-IID fragility, poisoning vulnerability, and limited privacy/deployment evidence; DATP currently cites Rey et al., Khraisat et al., Olanrewaju-George et al., and FedMSE but not Fed-ANIDS or CICIoT2023 FL-AE work.[1][6] | Yes – update citations with Fed-ANIDS and recent CICIoT2023 FL works (e.g., Fed-ANIDS CICIoT2023 extension, Fed-ANIDS for IoT in Systems and Soft Computing). |
| Closest adjacent papers | FL IDS on enterprise/CAN traffic, privacy-preserving FL surveys, FL robustness for IDS, green FL-IDS, and surveys of FL IDS.[4][2][7] | Adjacent on methodology (non-IID handling, robustness, privacy, energy) but not IoT malware-specific; useful for discussion and journal framing, but not for direct quantitative comparison. | Yes – incorporate at least one recent FL-IDS survey and the green FL-IDS review to show awareness of energy and sustainability angles. |
| Transferable FL methods | FedBN, Per-FedAvg, APFL, Ditto, FedProx, FedYogi, clustered FL, robust aggregation (median, trimmed mean, Krum, FreqFed), partial-sharing methods.[4][5][3][8] | Provide model-personalization and heterogeneity baselines against which DATP’s threshold-personalization niche must be positioned; they are currently only mentioned at high level in the SoA, not connected to DATP experimentally. | Yes – identify 1–2 methods (e.g., FedBN, Per-FedAvg) as explicit baselines for a lightweight comparison on the same datasets. |
| Dataset gaps | Over-reliance on N-BaIoT, limited use of CICIoT2023, almost no cross-dataset FL evaluation, little use of Bot-IoT, ToN-IoT, IoT-23, Edge-IIoTset for FL-IoT IDS.[4][9][10][11][12][13] | DATP partially addresses this by adding CICIoT2023, but only with file-level pseudo-clients; there is still no cross-dataset or device-level CICIoT2023 analysis, and no Bot-IoT/ToN-IoT/IoT-23 coverage. | Yes – reassess which newer IoT datasets provide real device splits and reasonable preprocessing; choose a maximum of one additional dataset that best reinforces DATP’s story. |
| Privacy gaps | Most FL-IoT IDS papers rely on structural privacy; only a few integrate DP or secure aggregation, and almost none measure leakage from calibration summaries, prototypes, or embeddings.[4][6][8] | DATP explicitly acknowledges that B4 cluster fingerprints leak distributional metadata but does not analyze privacy risks or propose mitigations. | Yes – cross-check with recent privacy-preserving FL-IDS surveys to appropriately bound DATP’s privacy claims and possibly add a small leakage-oriented discussion. |
| Heterogeneity gaps | Non-IID FL is often modeled with IID-friendly splits or single Dirichlet α; few works disentangle device-level heterogeneity from label skew or perform systematic sweeps.[4][8] | DATP’s Regime A and Regime C directly relieve this gap for threshold calibration but not for model-personalization; it is correctly aligned with the SoA but can be better positioned as part of a heterogeneity–fairness story. | Partially – existing SoA is strong, but newer works like FedMADE and dataset-centric evaluations (e.g., dataset-centric FL IDS evaluations) must be integrated.[14][15] |
| Deployment gaps | Most FL-IDS works are simulation-only; only a few (e.g., DÏoT) provide gateway deployment; communication, memory, and energy are rarely measured.[4][16][2] | DATP is explicitly simulation-only and does not present system-level metrics. | No for experiments (outside scope), but Yes for discussion – explicitly link DATP’s controlled calibration results to deployment trade-offs (local vs shared thresholds, storage). |
| Claim-support gaps | Many FL-IDS works overclaim generality, lack per-client metrics, or omit non-IID severity reporting.[17][18] | DATP is comparatively disciplined, with clear per-client metrics and non-IID sweeps, but it underplays connections to fairness, operational workload, and integration with model personalization. | Yes – ensure that any strengthened claims in the journal version remain tightly bounded and explicitly supported. |

# 4. Weakness Matrix

| ID | Weakness | Severity | Evidence From Paper | Why Reviewer Cares | Fix Type | New Experiment Needed | Effort | Scope Drift Risk |
|---|---|---|---|---|---|---|---|---|
| W01 | Dataset core limited to N-BaIoT + CICIoT2023 pseudo-clients, both used in narrow regimes. | Major | Only 9 physical devices in N-BaIoT; CICIoT2023 uses file-level pseudo-clients with randomized benign ordering and no temporal structure.[1] | Limits generality of threshold personalization; looks fragile to dataset idiosyncrasies. | Mandatory | Yes (if adding a second dataset) | Medium | Medium |
| W02 | No cross-dataset or cross-regime model generalization analysis (e.g., train on N-BaIoT, test on CICIoT2023). | Major | Each regime trains and evaluates on its own data; no cross-dataset transfer.[1] | Journals expect some evidence that findings are not dataset-specific. | Recommended | Yes | Medium | Medium |
| W03 | No comparison to model-personalization baselines (FedBN, Per-FedAvg, etc.) under the same non-IID conditions. | Critical | Related work section mentions model personalization conceptually but DATP only varies thresholds while keeping a single shared AE.[1][4] | Reviewers may see DATP as ignoring strong existing tools for heterogeneity; need to show threshold personalization is complementary, not obsolete. | Mandatory | Yes | Medium | Medium |
| W04 | No comparison against alternative threshold calibration strategies beyond p95 percentile (e.g., pooled global percentile, sample-weighted global percentile, shrinkage). | Major | Only q-sensitivity and shared-threshold construction variants are tested; threshold family is narrow.[1] | A journal reviewer can argue that conclusions might depend on the chosen percentile rule; richer threshold variants would strengthen robustness. | Recommended | Yes | Medium | Low |
| W05 | No temporal drift or recalibration analysis; assumption of stable benign calibration distributions. | Major | Paper explicitly states that temporal drift is not modeled; splits are static and offline.[1] | Threshold calibration is fundamentally about distributions; reviewers will ask how thresholds age over time. | Recommended | Yes | Medium | Medium |
| W06 | No adversarial or robustness analysis (poisoning, backdoor, or evasion). | Major | Paper explicitly notes that Mirai/BASHLITE attacks are fixed and no adversarial robustness is considered.[1] | For security journals, ignoring poisoning/evasion entirely is a red flag; at least some discussion or small experiment is expected. | Recommended | Maybe (lightweight) | Medium | High |
| W07 | No privacy leakage quantification for B4 cluster fingerprints or other summaries. | Moderate | Paper notes that mean/variance/skew/p95 can leak device-specific behavior but leaves it as future work.[1] | Journals in security/privacy care about whether shared statistics can leak sensitive information; even qualitative bounds matter. | Recommended | No (analysis only) | Low | Low |
| W08 | No deployment cost metrics (communication overhead, local storage for per-client thresholds, computational cost). | Moderate | Experiments report runtime environment but not communication or storage costs; E=1 with full participation approximates synchronous training only.[1] | Systems-oriented reviewers want to know if DATP’s scheme is operationally cheap or expensive. | Recommended | No (estimation from existing logs) | Low | Low |
| W09 | Limited statistical power and reporting (five seeds, descriptive summary only). | Minor | Five seeds, bootstrap CI only for main delta; no CIs for other metrics, no effect sizes. [1] | Statistical reviewers may request stronger uncertainty quantification. | Optional | No (recompute from saved scores) | Low | Low |
| W10 | N-BaIoT is aging and relatively simple; Mirai/BASHLITE only, no modern IoT malware families. | Major | Dataset is from 2018; more recent benchmarks like IoT-23, Edge-IIoTset, and updated Bot-IoT exist.[10][12][13] | Using only N-BaIoT may be seen as insufficiently challenging for a 2026 journal paper. | Mandatory (for at least one additional dataset) | Yes | Medium | Medium |
| W11 | CICIoT2023 usage ignores natural device or time-based partitioning; only file-level pseudo-clients. | Major | Regime B constructs pseudo-clients by merging CSV files and shuffling benign records; no device mapping or temporal continuity.[1] | Reviewers may argue that this is not an IoT-fleet interpretation and that conclusions about personalization not helping may be artifacts. | Mandatory (for revised CICIoT2023 design or explicit downgrading of its role) | Yes | Medium | Low |
| W12 | No explicit fairness or operational false-alarm burden analysis beyond dispersion statistics. | Moderate | CV(FPR) and per-client FPRs are reported but not explicitly linked to fairness or operational alarm workloads. [1] | Security/operations reviewers want to see how thresholds change who carries the false-alarm burden. | Recommended | No (from existing scores) | Low | Low |
| W13 | No link to energy or green computing despite FL overhead; no discussion of energy-aware calibration. | Minor | Energy consumption not discussed, despite recent focus on green FL-IDS.[2] | For some venues (FGCS), energy/efficiency is part of the scope. | Optional | No | Low | Medium |
| W14 | Conference-to-journal novelty gap not yet demonstrated (only one paper so far). | Critical | Journal version would be an extended version; DATP currently has one main experimental block and several secondary analyses.[1] | Editors must be convinced that the journal manuscript adds substantial new content beyond the conference paper. | Mandatory | Yes (new experiments + analyses) | High | Medium |
| W15 | No explicit comparison with Fed-ANIDS and other recent FL-AE IDS using CICIoT2023 or N-BaIoT. | Major | Fed-ANIDS and subsequent works provide federated autoencoder IDS for NIDS and CICIoT2023 but are not yet integrated.[3][19] | Reviewers will expect discussion of and comparison with the latest FL-AE methods, especially those using CICIoT2023. | Mandatory (at least citation and qualitative comparison; limited quantitative comparison if feasible) | Maybe | Medium | Medium |
| W16 | No explicit mapping from DATP’s threshold personalization to classical calibration notions (e.g., conformal prediction, Bayesian shrinkage). | Minor | DATP does not connect to broader calibration literature outside percentiles. | Optional | No | Low | Low |

# 5. Research-Backed Fix Matrix

| Weakness ID | Proposed Fix | Literature Support | Exact Experiment or Analysis | Dataset Needed | Baselines Needed | Metrics | Main or Supplement | Expected Reviewer Value |
|---|---|---|---|---|---|---|---|---|
| W01, W10 | Add one modern IoT-IDS dataset with meaningful client partitions (e.g., IoT-23 with device-based clients or ToN-IoT with IP-based clients) and rerun B1–B2–B4 threshold study. | IoT-23 and ToN-IoT are widely used IoT security datasets with device/host-level partitions suitable for FL; they cover newer attacks than N-BaIoT.[11][12] | Implement FedAvg AE with same encoder family and threshold framework; define clients as devices (IoT-23) or IPs/gateways (ToN-IoT); evaluate CV(FPR), CV(TPR), Macro-F1, P10 Macro-F1 under B1–B2–B4; compare heterogeneity patterns to N-BaIoT. | IoT-23 or ToN-IoT (choose one, not both, for must-do) | Same as DATP (FedAvg AE, B0–B4) | CV(FPR), IQR, max–min FPR, Macro-F1, P10 Macro-F1, coverage | Main | Shows that DATP’s findings are not N-BaIoT-specific and remain relevant on newer malware traffic. |
| W11 | Redesign CICIoT2023 partition to better reflect device or attack heterogeneity (e.g., victim-MAC/device-level clients) and rerun B1–B2–B4. | CICIoT2023 has device and attack labels that can be used to define more realistic FL clients; recent Fed-ANIDS-like works and CICIoT2023-based FL papers rely on such splits.[4][19][20] | Build a second CICIoT2023 regime: define clients by victim device/MAC or by attack source; keep file-level regime as near-homogeneous boundary; compare CV(FPR) and personalization effects between near-homogeneous and heterogeneous splits. | CICIoT2023 | Same as DATP (FedAvg AE) | CV(FPR), JS divergence between clients, Macro-F1, P10 Macro-F1 | Main | Strengthens application of DATP to CICIoT2023 and shows that null results are due to near-homogeneity, not dataset choice. |
| W03 | Introduce a minimal model-personalization baseline (e.g., FedBN or Per-FedAvg) and compare with DATP’s threshold personalization in terms of FPR dispersion and detection metrics. | FedBN and Per-FedAvg are standard personalization baselines for non-IID FL.[4][8] | Implement FedBN (local batch-norm statistics) or Per-FedAvg (local head) on N-BaIoT and the new dataset; evaluate with shared threshold and with B2 threshold personalization; compare CV(FPR), Macro-F1, and P10 Macro-F1; keep E=1 to avoid scope explosion. | N-BaIoT + new dataset | FedAvg + DATP (current), FedBN+shared threshold, FedBN+B2 (optional) | CV(FPR), Macro-F1, P10 Macro-F1, per-client FPR | Main | Demonstrates that threshold personalization remains useful even when simple model personalization is applied; positions DATP as complementary, not competitive. |
| W04 | Add 2–3 additional threshold variants (e.g., pooled global percentile, sample-weighted percentile, shrinkage between global and per-client thresholds) and show that core conclusions are robust. | Classical calibration and shrinkage methods suggest combining global and local statistics; percentile-based variants are simple to implement.[3] | Using existing stored scores, compute: (1) pooled global p95, (2) sample-count weighted mean of local p95, (3) shrinkage thresholds τk = λτglobal + (1−λ)τk,local for one λ (e.g., 0.5); compare CV(FPR)/Macro-F1 where feasible. | None new (reuse N-BaIoT, CICIoT2023) | Existing B0–B4 | CV(FPR), IQR, Macro-F1, P10 Macro-F1 | Supplement | Shows that DATP’s conclusion about FPR dispersion is not an artifact of a single threshold construction rule. |
| W05 | Add a small temporal-drift experiment using N-BaIoT or the new dataset, with calibration at t0 and evaluation at later time slices. | Temporal drift and threshold aging are central concerns in anomaly detection; FL-IDS work rarely measures this.[4][2] | For a dataset with temporal structure (e.g., CICIoT2023 or ToN-IoT), define t0 calibration window and t1–t2 test windows; keep thresholds fixed from t0; measure CV(FPR), Macro-F1 over time; optionally add a simple recalibration after t1. | Prefer CICIoT2023 or ToN-IoT with time stamps | Existing FedAvg AE + B1/B2/B4 | Time-labeled CV(FPR), Macro-F1 trajectories; stability ratios | Main (as one temporal experiment family) | Shows whether threshold personalization is stable or fragile under drift; minimal extension but high conceptual value. |
| W06 | Add at least a lightweight robustness discussion and, if feasible, a small poisoning/backdoor sensitivity check borrowing from FL-IDS robustness literature. | FL-IoT IDS robustness studies (e.g., poisoning/backdoor attacks on FL AE, FedMADE) show vulnerability; Fed-ANIDS also focuses on anomaly FL IDS.[8][14][21] | If feasible: simulate a simple label-flipping or gradient-scaling poisoning client on N-BaIoT, observing how shared vs per-client thresholds behave in terms of FPR/TPR; otherwise, integrate robustness discussion explicitly acknowledging lack of experiments. | N-BaIoT (optional) | FedAvg+B1/B2 | FPR, TPR under poisoning; narrative only if experiment too heavy | Supplement | Shows awareness of robustness issues without redefining the paper as adversarial FL; even a small experiment helps. |
| W07 | Add a privacy-leakage section analyzing what B4 fingerprints can reveal and how secure aggregation could mitigate it; keep it analytical rather than experimental. | Privacy-preserving FL surveys and secure aggregation frameworks (e.g., SecAgg+) highlight leakage from shared statistics and available mitigations.[4][17][6] | Derive bounds on what mean/variance/skew/p95 distributions can reveal about device behavior (e.g., heavy tails, unusual patterns); discuss trade-offs between B2 (local) and B4 (fingerprint-sharing) under secure aggregation/DP. | None | None | Qualitative privacy risk matrix | Main (short section) | Addresses privacy expectations without promising full DP; demonstrates serious handling of leakage concerns. |
| W08 | Estimate communication and storage overhead of DATP’s threshold policies using existing experimental parameters. | Green FL-IDS review emphasizes energy, communication, and storage metrics for FL-IDS.[2] | Compute per-round bytes for model updates and per-client thresholds/fingerprints; compute per-client and per-round storage requirements; present a short table comparing B1 vs B2 vs B4 overheads. | None | None | Bytes per round, per-client state size, percentage overhead vs model | Supplement | Provides the minimal systems-level evidence journals expect, without full hardware experiments. |
| W09 | Recompute effect sizes and confidence intervals for key metrics using stored per-client scores and seeds. | Statistical reporting best practices in ML and security increasingly require uncertainty quantification.[17] | Use stored scores to compute bootstrap CIs for CV(FPR), Macro-F1, and P10 Macro-F1; report effect sizes (absolute and relative) for B1 vs B2 vs B4 on key regimes. | None | None | CIs and effect sizes | Supplement | Addresses statistical rigor concerns with low implementation effort. |
| W12 | Add fairness and operational burden analysis from existing FPR distributions. | Fairness and per-client burden are increasingly emphasized in security analytics.[4] | Derive per-client share of total false alarms and show how B1 vs B2 vs B4 changes this burden; add a short fairness interpretation section. | None | None | False alarms per client, Lorenz-like concentration ratios | Main | Makes DATP’s contribution legible as a fairness mechanism, which many journals care about. |
| W15 | Integrate and, if feasible, lightly compare with Fed-ANIDS and newer FL-IDS works using CICIoT2023. | Fed-ANIDS and subsequent works provide federated anomaly IDS with autoencoders and CICIoT2023; they are natural comparators.[3][19][22] | Cite Fed-ANIDS (ESWA 2023 + CICIoT2023 extension) and describe how DATP differs (threshold scope vs combined FL+AE design); if code and features align, run one limited Fed-ANIDS baseline with its threshold rule and compare FPR dispersion vs DATP B1/B2. | CIC-IDS2017 / CICIoT2023 (if reused) | Fed-ANIDS baseline (optional) | FPR, Macro-F1; CV(FPR) | Supplement | Shows DATP is aware of and distinct from state-of-the-art FL-AE NIDS; mitigates novelty concerns. |

# 6. Dataset Expansion Matrix

| Dataset | Add or Reject | Reason | Physical Device Split | Temporal Potential | Calibration Suitability | DATP Fit | Preprocessing Burden | Main Risk |
|---|---|---|---|---|---|---|---|---|
| N-BaIoT | Keep (already used) | Natural physical-device clients and known Mirai/BASHLITE attacks; DATP already uses it effectively as confirmatory regime.[1][23] | Yes (nine IoT devices) | Limited (captures but not rich multi-week drift) | Strong: benign-device tails differ significantly, good calibration testbed.[1] | Core confirmatory dataset; must remain central. | Moderate (115-dim features already handled) | Aging, narrow attack variety; risk of overfitting conclusions to this dataset. |
| CICIoT2023 | Add refined usage | Contemporary IoT dataset with multiple attacks and richer network structure; already used but only with pseudo-clients.[1][4] | Yes, but requires reconstructing device or MAC-level clients from metadata.[4] | Good: multi-day capture allows time-based splits. | Good: large benign volumes enable stable percentile calibration. | Excellent for testing threshold personalization across modern IoT attacks if partitioned by device/attack. | Moderate–High (feature extraction, partition design) | Complexity of building reliable client partitions; risk of inconsistent splits with other works. |
| Bot-IoT | Reject (for main DATP) | Large-scale dataset but more enterprise-style, heavy imbalance, and often criticized for simulation artifacts; mapping to FL clients is non-trivial.[10] | No natural device splits; would require artificial grouping. | Some time structure but not central to IoT-device fleets. | Possible but less natural due to extreme imbalance and synthetic traffic patterns. | Moderate; could be used as future work, but adds little to threshold-personalization story. | High (72M+ flows, heavy feature engineering) | High engineering effort with unclear added value specific to DATP. |
| ToN-IoT | Maybe add (candidate 1) | Realistic Industry 4.0/IoT testbed; multi-source telemetry including network flows with host/IP-level structure.[11][24] | Yes (hosts, services, and IPs can be clients). | Good; collected over time with multiple attack windows.[11] | Reasonable; benign volumes per host may vary but can be capped. | Strong candidate for a second dataset: different domain and richer attacks than N-BaIoT; FL partitioning matches heterogeneity interest.[8] | Moderate–High (requires flow preprocessing and partition design). | Complexity of constructing a clean FL client map and balancing benign/attack counts. |
| IoT-23 | Maybe add (candidate 2) | Device-centric captures with labeled malware and benign traffic; widely used IoT malware dataset.[12] | Yes (each capture/device can be a client). | Good within capture windows but more fragmented across campaigns. | Strong if benign traffic per client is sufficient; thresholds can be per-device. | Highly aligned with device-aware personalization narrative. | High (PCAP to flow conversion, per-device aggregation). | Preprocessing and ensuring enough benign samples per client may be challenging. |
| Edge-IIoTset | Reject (for main paper) | Strong IIoT dataset but more industrial and multi-layer; FL client definition is unclear; better suited for separate study.[13][25] | Not clearly; would require scenario-based clients. | Yes, but more complex testbed semantics. | Possible but with significant curation. | Only loosely aligned with DATP’s current N-BaIoT/CICIoT2023 pipeline. | High | Overly heavy for the extension; likely to cause scope drift. |
| UNSW-NB15 | Reject (except brief discussion) | General-purpose intrusion dataset, heavily used but not IoT-specific; SoA already treats it as systems context rather than direct IoT malware evidence.[4] | No natural IoT device splits. | Some | Moderate | Low direct IoT-alignment; better as background comparison only. | Moderate | Risk of diluting IoT focus and inviting criticism about non-IoT data. |

# 7. Stronger Comparison Matrix

| Comparison | Mandatory? | Scientific Question | Implementation Cost | Reviewer Value | Scope Drift Risk | Recommended Placement |
|---|---|---|---|---|---|---|
| FedAvg+B1 vs FedAvg+B2 on new dataset (IoT-23 or ToN-IoT) | Yes | Does per-client percentile calibration still reduce FPR dispersion and at what detection cost on a modern dataset? | Medium | Directly tests generality of main claim; high value. | Low | Main paper (results section). |
| FedAvg+B1 vs FedBN+B1 (shared threshold) | Yes | Does simple model personalization already equalize FPR dispersion, or is threshold personalization still needed? | Medium | Addresses concern that personalization at model level might dominate; clarifies complementary roles. | Medium | Main paper. |
| FedBN+B1 vs FedBN+B2 | Yes | Does threshold personalization still confer FPR fairness gains when using a personalized model? | Medium | Shows unique contribution of DATP in presence of FedBN. | Medium | Main paper. |
| DATP B2 vs global pooled percentile threshold | No (Recommended) | Are gains sensitive to the choice of global threshold construction? | Low (derived from stored scores) | Demonstrates robustness of findings to plausible variants. | Low | Supplementary. |
| DATP B2 vs sample-weighted global threshold | No (Recommended) | Is CV(FPR) reduction due to arithmetic mean, or is any shared quantile poor for heterogeneous devices? | Low | Reinforces that issue is shared scope, not mean type. | Low | Supplementary. |
| DATP B2 vs shrinkage threshold (local-global blend) | No (Recommended) | Can a simple shrinkage rule approximate B2 while reducing variance? | Medium | Suggests operationally attractive compromise; interesting for practitioners. | Medium | Supplementary. |
| DATP B2 vs family-mean (B3) vs cluster-mean (B4) on new dataset | Yes | Does unsupervised clustering remain a viable taxonomy-free proxy on other datasets? | Medium | Clarifies whether B4 generalizes or is N-BaIoT-specific. | Medium | Main paper (short section) or supplement depending on space. |

# 8. Threshold Variant Matrix

| Variant | Definition | Why It Matters | Mandatory? | Risk | Main or Supplement |
|---|---|---|---|---|---|
| q = 0.90, 0.95, 0.99 | Different percentile thresholds applied per-client or globally (already partially explored). [1] | Shows robustness of conclusions to choice of operating point. | Already partly done; extending to new dataset is Recommended, not mandatory. | Low | Supplement (brief). |
| Global pooled percentile | One p95 threshold from pooled benign scores across all clients. | Standard central calibration baseline; tests whether client-specific pooling changes fairness. | Recommended, not mandatory. | Low | Supplement. |
| Client-averaged percentile (B1) | Arithmetic mean of local p95 thresholds across eligible clients (current B1). [1] | Baseline shared threshold modeled as server-broadcast scalar. | Mandatory (already present). | Low | Main. |
| Sample-weighted client percentile | Weighted mean of local p95 thresholds with weights proportional to calibration-sample count. | More realistic if some clients have much more data; could slightly alter fairness. | Recommended | Low | Supplement. |
| Per-client percentile (B2) | Local p95 of benign reconstruction error per client. [1] | Main DATP mechanism; directly controls per-client FPR. | Mandatory | Low | Main. |
| Family mean threshold (B3) | Mean of local thresholds within manually defined device families. [1] | Tests whether coarse device taxonomy helps; currently performs poorly. | Mandatory to keep (already present) but not to extend. | Low | Main (short). |
| Cluster mean threshold (B4) | k-means clustering on (µe, σe, skewe, p95(e)) with cluster-specific mean thresholds.[1] | Taxonomy-free grouping; approximates B2 while reducing metadata overhead. | Mandatory (key contribution). | Medium (privacy leakage, complexity). | Main. |
| Local-global shrinkage | τk = λτglobal + (1−λ)τk,local for fixed λ (e.g., 0.5). | Represents realistic compromise between shared and fully local thresholds; may be more stable under limited data. | Recommended | Medium | Supplement. |
| Drift-aware recalibration threshold | τk recomputed periodically using sliding window of recent benign data. | Connects DATP to temporal drift; helps define recalibration frequency. | Optional (tied to temporal experiment) | Medium | Supplement. |

# 9. Temporal Drift and Recalibration Plan

## 9.1 Feasibility
The current DATP datasets can support only proxy temporal analysis: N-BaIoT and CICIoT2023 provide time stamps or capture days, but the paper’s present splits discard temporal order for CICIoT2023 and use gapped chronological splits for N-BaIoT; there is enough structure to define calibration at time t0 and evaluation at later windows, but not a full live streaming study.[4][1]

## 9.2 Minimum Viable Temporal Experiment
Use CICIoT2023 with a device- or MAC-based client partition; select an early calibration window (e.g., first 20–30% of benign traffic per client) to estimate τk and τglobal; evaluate FPR, TPR, Macro-F1, CV(FPR), and CV(TPR) on later windows (e.g., mid and late capture segments) without recalibration; compare B1 vs B2 vs B4 over time.

## 9.3 Strong Temporal Experiment
On the same CICIoT2023 regime or ToN-IoT, implement a simple recalibration scheme: recalibrate τk and τglobal after a fixed number of new benign samples or at time cut t1, and compare detection-quality trajectories with and without recalibration; explore one drift-aware rule (e.g., recalibrate if benign MSE distribution’s mean or variance shifts beyond a threshold).

## 9.4 Metrics
Metrics should include time-indexed CV(FPR), CV(TPR), Macro-F1, P10 Macro-F1, and coverage ratio per time window, as well as drift indicators (e.g., change in mean reconstruction error per client between calibration and test windows). 

## 9.5 Interpretation Rules
If CV(FPR) remains low and Macro-F1 stable over time under B2, threshold calibration appears robust to mild drift; if CV(FPR) grows while B1 stays stable, then local thresholds may age faster than global ones; if recalibration restores fairness with acceptable TPR loss, DATP can claim that per-client thresholds support periodic recalibration as a practical policy; if both global and local thresholds degrade sharply, the paper must explicitly state that threshold personalization alone does not solve concept drift and should only claim fairness gains under approximately stationary benign distributions.

# 10. Deeper Analysis Plan

| Analysis | Purpose | Required Data | Figure or Table | Expected Insight | Priority |
|---|---|---|---|---|---|
| Client-level false-alarm burden distribution | Quantify how B1 vs B2 vs B4 redistribute the share of false alarms across clients. | Existing per-client FPR and counts for N-BaIoT and CICIoT2023.[1] | Table of per-client contribution to total false alarms; optional bar or Lorenz-style plot. | Makes fairness and operational burden explicit, reinforcing FPR-equity framing. | High |
| Benign-tail overlap analysis | Show how benign distribution differences drive FPR dispersion and explain when B2 helps. | Stored benign reconstruction-error scores per client.[1] | ECDF or density plots similar to Fig. 2 but extended; possibly a summary table of μe, σe, skew, p95 per client. | Links calibration benefit to specific distributional differences; supports B4 fingerprint choice. | High |
| Attack-benign separability per client | Explain Macro-F1 trade-offs and why some clients degrade under B2. | Stored attack and benign scores per client.[1] | Table of per-client AUROC, AUPRC, and P10 Macro-F1; scatter of AUROC vs change in FPR. | Clarifies that B2 failure modes occur when benign-attack overlap is high (e.g., Ennio Doorbell). | High |
| Correlation between heterogeneity and DATP benefit | Connect non-IID severity (e.g., JS divergence or Dirichlet α) to CV(FPR) reduction. | Existing JS metrics (CICIoT2023) and Dirichlet regime results.[1] | Scatter or small table correlating JS or α with CV(FPR) reduction. | Supports claim that threshold personalization is most valuable in high-heterogeneity regimes. | Medium |
| Calibration-set size sensitivity | Assess robustness when some clients have limited benign data. | Subsampled calibration sets from existing scores. | Table comparing CV(FPR) and Macro-F1 for different nmin thresholds (e.g., 50, 100, 200). | Shows where B2/B4 remain safe; helps define practitioner guidance on calibration data volume. | Medium |
| Bootstrap confidence intervals and effect sizes | Improve statistical rigor of main comparisons. | Existing per-seed metrics. [1] | Table with CIs and standardized effect sizes for B1 vs B2 vs B4 on key regimes. | Addresses Reviewer 2 concerns about small sample statistics. | Medium |

# 11. Journal Originality and Conference Extension Plan

## 11.1 What Can Be Reused
The journal version can reuse: core problem formulation; FL-AE pipeline and notation; Regime A N-BaIoT experiments (with five seeds); existing CICIoT2023 file-level regime as a documented near-homogeneous boundary; Regime C Dirichlet sweep; main figures (FPR distributions, CV(FPR) vs α); and the replication artifact structure.[1]

## 11.2 What Must Be New
To justify journal submission, the paper must add: at least one additional IoT malware or IoT IDS dataset with device- or host-level clients; a refined CICIoT2023 regime with realistic clients; a minimal model-personalization baseline under the same conditions; one temporal or drift-oriented calibration experiment; a deeper fairness and separability analysis; a privacy-leakage analysis for B4 (and discussion of mitigation); and stronger statistical reporting.

## 11.3 Self-Plagiarism Risk
Reusing text, figures, and results from the conference version is acceptable if clearly declared and if new contributions are substantial (typically at least 30–40% new material, including new experiments and analyses), in line with common publisher norms. The main risk is submitting a journal manuscript that looks too similar in structure and results; this is mitigated by explicitly labeling sections as extended from the conference paper and clearly enumerating new components in the introduction and cover letter.[26][27][28]

## 11.4 Cover Letter Disclosure
A possible 5–8 sentence disclosure:

"This manuscript is an extended version of our conference paper on Device-Aware Threshold Personalization (DATP), which introduced a controlled threshold-calibration study for federated IoT anomaly detection using N-BaIoT and CICIoT2023. The present journal version substantially extends the earlier work along four axes. First, it adds a second modern IoT security dataset with realistic client partitions, demonstrating that our threshold-personalization findings generalize beyond N-BaIoT. Second, it incorporates a lightweight model-personalization baseline, showing that device-aware thresholds remain beneficial even when FedBN-style personalization is applied. Third, it introduces a temporal calibration experiment and deeper fairness analyses, clarifying when per-client thresholds are stable and how they redistribute the false-alarm burden across devices. Fourth, it analyzes privacy implications of sharing calibration fingerprints and provides a quantitative overhead and deployment discussion. All reused figures and results from the conference paper are clearly marked, and the new material represents a significant expansion in experimental depth, analysis, and practical guidance." 

# 12. Elsevier Venue Target Matrix

| Rank | Journal | Scope Match | Indexing Status To Verify | Best Framing Angle | Required Upgrades | Desk-Rejection Risk | Recommendation |
|---|---|---|---|---|---|---|---|
| 1 | Computers & Security (COSE) | Strong: IT security, intrusion detection, IoT security, privacy, and FL-based security systems.[29] | Clarivate/JCR, Scopus, SCImago security & cryptography category. | Security-centric framing: federated IoT anomaly detection with focus on fairness of alarm rates, calibration, and privacy considerations. | Must add second dataset, model-personalization baseline, temporal/fairness analyses, and explicit privacy/robustness discussion. | Medium – depends on perceived novelty beyond existing FL-IDS works. | High priority. |
| 2 | Computer Networks | Strong: computer communications, network security, FL for IDS; explicitly open to extended versions of quality conference papers.[30][26] | Clarivate/JCR, Scopus (Computer Networks & Communications). | Networking-centric framing: collaborative IDS in IoT networks with a focus on threshold calibration under non-IID FL and distributed decision policies. | Similar upgrades as COSE; an emphasis on communication overhead and potential deployment topologies will help. | Medium – expects clear network angle and sufficient extension. | High priority. |
| 3 | Future Generation Computer Systems (FGCS) | Strong: distributed systems, cloud/edge, FL, and security applications; guide explicitly welcomes extended conference papers with significant novelty.[27] | Clarivate/JCR, Scopus (Computer Science, Theory & Methods; Hardware & Architecture). | Systems/FL framing: federated calibration in edge/IoT systems; can connect to green FL-IDS and life-cycle considerations. | Needs more explicit systems and possibly energy-related discussion (communication, compute), plus the same experimental upgrades. | Medium–High – more competitive and expects broader systems impact. | Medium–High priority. |
| 4 | Journal of Network and Computer Applications (JNCA) | Strong: networked applications, security, and distributed systems.[31][32] | Clarivate/JCR, Scopus. | Application-centric framing: federated IoT anomaly detection for networked applications with threshold personalization as a service-level mechanism. | Same core upgrades; may need clearer application scenarios and perhaps a small case-study narrative. | Medium | Medium priority. |
| 5 | Internet of Things (Elsevier) | Moderate–Strong: IoT systems and services, including security and analytics.[33] | Clarivate/Scopus status to verify for 2026. | IoT-centric framing: device-aware FL anomaly detection in IoT fleets, focusing on threshold fairness and deployment guidance. | Same upgrades plus stronger IoT-system narrative; may be slightly less security-focused than COSE. | Medium | Medium priority. |
| 6 | Computer Standards & Interfaces | Moderate: standardization/architectural aspects; may fit if DATP is framed as a standardized calibration policy. | Clarivate/Scopus to verify. | Framing DATP as a calibration policy candidate for IoT FL IDS deployments. | Would require more emphasis on standardization, interoperability, and interfaces than currently planned. | High | Low priority. |
| 7 | Ad Hoc Networks | Weak–Moderate: focused on ad hoc/mesh networks; security is possible but network routing usually central.[34] | Clarivate/Scopus. | Only fits if DATP is heavily couched in network topology and routing issues, which would be scope-drifting. | Would need additional experiments on ad-hoc topologies or routing contexts. | High | Do not prioritize. |
| 8 | Engineering Applications of Artificial Intelligence (EAAI) | Moderate: AI applications; IDS is acceptable but security-specific contributions may be less central. | Clarivate/Scopus. | Emphasize methodological novelty (calibration study) more than security; risk of misalignment with core AI audience. | Would need more AI/ML methodological contributions beyond threshold personalization. | Medium | Low–Medium priority. |

# 13. Three-Level Expansion Roadmap

## 13.1 Minimal Journal Extension

| Component | Required Action | Why It Is Needed | Effort | Risk |
|---|---|---|---|---|
| Dataset | Add one modern IoT dataset (IoT-23 or ToN-IoT) with device/host clients and rerun B1–B2–B4. | Establish that DATP’s main findings hold beyond N-BaIoT. | Medium | Moderate (dataset engineering). |
| Baseline | Keep FedAvg AE only; no model personalization baselines. | Avoids scope drift but risks reviewers citing missing comparison. | Low | High (novelty critique). |
| Threshold variants | Extend existing q-sensitivity and shared-threshold variants to new dataset. | Shows robustness of conclusions. | Low | Low. |
| Temporal | None or minimal time-split analysis on existing data. | Reduces workload but leaves temporal question largely open. | Low | Moderate. |
| Deeper analysis | Add fairness/false-alarm burden analysis and better statistical reporting (CIs). | Increases interpretability and rigor. | Low | Low. |

## 13.2 Strong Journal Extension

| Component | Required Action | Why It Is Needed | Effort | Risk |
|---|---|---|---|---|
| Dataset | Add one well-chosen dataset (IoT-23 or ToN-IoT) and refine CICIoT2023 partition to device/MAC-level clients. | Provides both cross-dataset and within-dataset heterogeneity perspectives. | Medium | Medium. |
| Baseline | Implement one model-personalization baseline (FedBN or Per-FedAvg) and integrate into B1/B2 framework. | Addresses key novelty and baseline concerns. | Medium | Medium. |
| Threshold variants | Add pooled and sample-weighted global thresholds plus one shrinkage variant (local-global mix). | Demonstrates robustness of threshold conclusions and offers operational alternatives. | Medium | Low–Medium. |
| Temporal | Add a small, well-defined temporal drift and recalibration experiment on CICIoT2023 or ToN-IoT. | Elevates work to journal-level depth regarding threshold aging. | Medium | Medium. |
| Deeper analyses | Implement fairness, separability, calibration-set size sensitivity, and CIs/effect sizes. | Converts results from descriptive to insight-driven; high reviewer value. | Medium | Low. |

## 13.3 Ambitious Journal Extension

| Component | Required Action | Why It Is Needed | Effort | Risk |
|---|---|---|---|---|
| Dataset | Add two new datasets (e.g., IoT-23 and ToN-IoT) plus refined CICIoT2023 regime. | Maximizes generality but risks overextension. | High | High (time, complexity). |
| Baseline families | Implement multiple model-personalization and robust aggregation baselines (FedBN, Per-FedAvg, FedMSE-like, FedProx variants). | Enables broad comparison across FL techniques. | Very High | High (paper becomes general FL-IDS work). |
| Threshold variants | Explore conformal, empirical Bayes, and multiple shrinkage and drift-aware thresholds. | Substantially enriches threshold methodology. | Very High | High (math and validation load). |
| Temporal | Multi-dataset, multi-regime temporal and recalibration study. | Very strong but extremely time-consuming. | Very High | High. |
| Privacy/robustness | Add formal DP or SecAgg implementation plus poisoning and evasion studies. | Turns paper into a combined privacy-robustness-calibration work. | Very High | Very High (identity shift). |

# 14. Final Recommended Package

Recommended journal-extension package (one final package, respecting hard limits):

1. Dataset additions:
   - Add exactly one new dataset: ToN-IoT or IoT-23 (choose based on calibration-friendly benign volume and client mapping feasibility).
   - Redesign CICIoT2023 with device/MAC-based clients while keeping file-level regime as a near-homogeneous boundary.
2. Baseline additions:
   - Add one model-personalization baseline (FedBN or Per-FedAvg) integrated with B1/B2 thresholds.
   - Do not add more than this one baseline family.
3. Threshold additions:
   - Keep existing B1–B4.
   - Add pooled and sample-weighted global thresholds, plus one shrinkage variant τk = 0.5 τglobal + 0.5 τk,local.
   - Do not go beyond these four new variants.
4. Temporal/recalibration additions:
   - Implement a single temporal experiment family on CICIoT2023 or ToN-IoT with calibration at t0 and evaluation at later windows, plus one simple recalibration policy.
5. Deeper analyses:
   - Fairness/false-alarm burden analysis; attack-benign separability diagnostics; heterogeneity vs benefit correlation; calibration-set size sensitivity; bootstrap CIs/effect sizes; and a privacy-leakage discussion for B4.
6. New figures:
   - One new figure for temporal CV(FPR)/Macro-F1 trajectories.
   - One new figure for false-alarm burden distribution (e.g., per-client bar or Lorenz-like curve).
7. New tables:
   - One table for new dataset results (B1/B2/B4, plus FedBN baseline).
   - One table for temporal experiment results.
   - One table for fairness and separability diagnostics (possibly extending current Table V).
8. New sections:
   - Section on model personalization vs threshold personalization; section on temporal calibration behavior; subsection on privacy and deployment overhead.
9. Supplementary material:
   - Extended threshold-variant results (pooled, weighted, shrinkage); detailed per-client statistics and additional seed-level tables; any robustness micro-experiments.
10. Claims to strengthen:
   - DATP as a fairness-oriented threshold-calibration mechanism for FL IoT anomaly detection that is robust across at least two heterogeneous datasets and complementary to simple model personalization.
11. Claims to avoid:
   - Avoid claiming universal detection performance improvement, full robustness, or formal privacy guarantees; avoid suggesting that threshold personalization alone solves non-IID FL challenges.

# 15. Artifact and Claim Consistency Check

| Proposed Claim | Current Support Status | Required Evidence | Artifact Needed | Safe Wording |
|---|---|---|---|---|
| DATP’s per-client thresholds consistently reduce FPR dispersion across heterogeneous IoT fleets. | Already supported on N-BaIoT and synthetic Dirichlet regimes.[1] | Replication on one additional dataset with heterogeneous clients. | New dataset experiments; updated plots and tables. | "In both N-BaIoT and [Dataset X], per-client percentile calibration significantly reduces cross-client FPR dispersion under the tested FL AE and partitions." |
| Cluster-mean calibration offers a robust taxonomy-free approximation to per-client calibration. | Requires new experiments (currently only N-BaIoT and synthetic). | Evaluate B4 on new dataset and refined CICIoT2023; study stability of clusters. | New dataset + CICIoT2023 redesign results. | "On two datasets with heterogeneous clients, cluster-mean calibration recovers roughly half of the FPR-dispersion reduction achieved by full per-client calibration, without requiring an explicit device taxonomy." |
| Threshold personalization remains beneficial even with model personalization (FedBN/Per-FedAvg). | Requires new experiments. | Implement FedBN or Per-FedAvg and compare B1/B2 on N-BaIoT and new dataset. | New baseline experiments. | "In our experiments, combining FedBN with per-client thresholds further reduces FPR dispersion compared with FedBN and a shared threshold, suggesting that model and threshold personalization address complementary aspects of heterogeneity." |
| DATP thresholds are stable under mild temporal drift. | Requires new experiments. | Temporal calibration study as described in Section 9. | Time-sliced results. | "On [Dataset X], per-client thresholds calibrated on an early window maintained low FPR dispersion and stable Macro-F1 over subsequent windows without recalibration, under the observed level of drift." |
| B4 fingerprints pose manageable privacy leakage when used with secure aggregation. | Requires recomputation from existing artifacts plus conceptual argument; no new dataset. | Analytical privacy assessment; link to secure aggregation frameworks. | No new experimental artifact; maybe simple synthetic examples. | "Sharing cluster fingerprints leaks distributional statistics but not raw traffic; when combined with standard secure aggregation protocols, this leakage can be reduced, although formal differential-privacy guarantees are left to future work." |
| DATP improves overall detection performance. | Should not be claimed. | Would require broader baseline and scoring analysis, including ACC, AUROC, AUPRC and multiple models. | New models and metrics beyond scope. | "DATP primarily targets FPR-dispersion fairness; its impact on detection rates is mixed and depends on per-device separability, with some clients experiencing lower-tail Macro-F1 degradation." |

# 16. Reviewer-Loophole Closure Table

| Loophole | Closed By | Remaining Risk | Final Wording Discipline |
|---|---|---|---|
| "Results are N-BaIoT-specific" | Adding a modern dataset (IoT-23 or ToN-IoT) and refining CICIoT2023 partition to device-based clients. | Still only 2–3 datasets; some reviewers may want even more. | Always phrase generality as "on the datasets considered" and avoid universal language. |
| "Threshold personalization ignores model personalization" | Adding FedBN/Per-FedAvg baseline and showing complementary effects. | Comparison limited to one FL AE architecture and a subset of personalization methods. | Emphasize complementarity and scoped evidence; avoid ranking all personalization methods. |
| "Temporal drift is ignored" | Including at least one temporal calibration and recalibration experiment. | Limited time horizon and datasets; no live deployment. | Explicitly limit claims to offline temporal slices and note that online drift management is future work. |
| "Privacy of B4 fingerprints is unexamined" | Dedicated section analyzing leakage and discussing secure aggregation/DP mitigations. | No formal privacy proofs; no quantitative attack experiments. | Use cautious language: "may leak", "can be mitigated", "formal guarantees are not established here". |
| "No robustness or poisoning analysis" | Brief robustness discussion referencing FL-IDS robustness literature; optional micro-experiment. | No comprehensive adversarial study; may still be flagged. | State explicitly that robustness is out of scope and any robustness comments are speculative; present any experiments as early indications only. |
| "Conference extension is too incremental" | New dataset, refined CICIoT2023 regime, model personalization baseline, temporal study, fairness and privacy analyses. | Editors may still question novelty if new material is not highlighted clearly. | Clearly enumerate new contributions in abstract and introduction; cite conference version as prior work. |
| "Deployment aspects are ignored" | Communication and storage overhead estimates; discussion of operational calibration workflows. | No hardware energy measurements or field deployment. | Present overhead estimates as indicative; avoid claiming full deployment validation. |

# 17. Final Recommended Decision Gate

## 17.1 Best Target Journal
The best single Elsevier target is Computers & Security, because it is explicitly focused on IT and network security, regularly publishes FL-IDS and IoT-security work, and is receptive to extended conference papers when novelty and security relevance are clear.[29][26]

## 17.2 Best Expansion Level
The recommended expansion level is Strong: more than Minimal (requires a second dataset, model personalization baseline, and temporal/fairness analyses) but short of the Ambitious plan that would add multiple datasets, full robustness/privacy stacks, and complex threshold families.

## 17.3 Exact Must-Do List Before Submission
- Add exactly one new IoT-security dataset with realistic client partitions (ToN-IoT or IoT-23) and rerun the DATP threshold framework (B0–B4) on it.
- Redefine CICIoT2023 clients at device/MAC or host level, preserving the existing file-level regime as a near-homogeneous applicability boundary.
- Implement one model-personalization baseline (FedBN or Per-FedAvg) and compare shared vs per-client thresholds on N-BaIoT and the new dataset.
- Add a small temporal calibration experiment (fixed thresholds across time windows, with one simple recalibration variant) on CICIoT2023 or the new dataset.
- Perform deeper fairness and separability analyses using existing and new scores, including false-alarm burden distribution, per-client AUROC, and calibration-set size sensitivity.
- Add a privacy-leakage and overhead analysis for B4 fingerprints and per-client thresholds, grounded in existing secure aggregation and FL-privacy literature.
- Improve statistical reporting with bootstrap CIs and effect sizes for main metrics.

## 17.4 Exact Do-Not-Do List
- Do not add more than two new datasets; limit to N-BaIoT + one additional main dataset plus refined CICIoT2023 regimes.
- Do not add more than one model-personalization baseline family; avoid full-scale comparison of multiple personalization and aggregation methods.
- Do not attempt to integrate full DP or secure aggregation implementations, or comprehensive robustness/evasion experiments, as main contributions.
- Do not reframe the paper as a general FL-IDS, privacy, or robustness study; keep threshold personalization and fairness as the central identity.
- Do not claim universal generalization across all IoT malware contexts, or that DATP solves non-IID FL challenges beyond FPR-dispersion fairness.

## 17.5 Should the Journal Extension Wait Until Conference Acceptance?
If the conference submission is under review, it is preferable to wait for its decision before submitting the extended journal version, to avoid conflicts and ensure accurate citation of the conference version as prior work; however, journal planning and preliminary experiments for the extension can proceed in parallel, as long as double submission of overlapping manuscripts is avoided in line with Elsevier policies.[28]

# 18. Search Audit Log

| Search Query or Source | Source Type | Date Checked | Key Findings | Confirmed / Changed / Contradicted SoA | Used in Final Recommendation? |
|---|---|---|---|---|---|
| "Fed-ANIDS: Federated learning for anomaly-based network intrusion detection systems" ESWA 2023 | Web (ESWA article and author PDF) | 2026-05-22 | FL AE-based NIDS using FedProx on USTC-TFC2016, CIC-IDS2017, CSE-CIC-IDS2018; uses global threshold based on reconstruction error; no device-aware threshold personalization.[3][35] | Confirms SoA view that FL-AE NIDS exist but do not isolate threshold scope; adds a key baseline to cite. | Yes |
| "Federated autoencoder IDS for IoT: A Fed-ANIDS Approach Using CICIoT2023" | Web (Systems and Soft Computing volume in progress) | 2026-05-22 | Journal extension of Fed-ANIDS using CICIoT2023; likely device- or scenario-based partitions; confirms the importance of CICIoT2023 for FL-AE IDS.[22][36] | Extends SoA by adding a direct FL-AE+IoT IDS benchmark on CICIoT2023; increases need to position DATP carefully. | Yes |
| "Federated Deep Learning for Intrusion Detection in IoT Networks" (TON-IoT FL) | Web (preprint/PDF) | 2026-05-22 | Uses TON-IoT with IP-address-based clients; shows severe performance drops under realistic non-IID and partial recovery via pretraining and aggregation tweaks.[8][24] | Confirms SoA claim about non-IID fragility; suggests ToN-IoT as strong candidate dataset. | Yes |
| "The TON_IoT Datasets" UNSW page | Web (official dataset page) | 2026-05-22 | Describes ToN-IoT as multi-source Industry 4.0/IoT datasets with realistic traffic, heterogeneous sources, and multiple attacks; suitable for IDS and FL.[11] | Confirms dataset suitability and adds option for new DATP dataset. | Yes |
| "IoT-23 Dataset: A labeled dataset of Malware and Benign IoT Traffic" | Web (dataset site) | 2026-05-22 | Provides malware and benign captures for IoT devices; device-level structure, widely used in IoT malware research.[12] | Adds alternative candidate dataset for extension; not in original SoA. | Yes |
| "Federated learning for anomaly-based network intrusion detection" (Fed-ANIDS ESWA) | Web (ScienceDirect/OpenReview) | 2026-05-22 | Confirms use of autoencoders under FL with FedProx, centralized thresholding, multiple NIDS datasets; highlights that thresholds are global, not device-aware.[3][37][35] | Confirms threshold-scope gap motivating DATP; updates list of key AE-FL NIDS baselines. | Yes |
| "Computer Networks guide for authors extended versions" | Web (Elsevier shop and guide) | 2026-05-22 | States that enhanced, extended versions of quality conference papers may be submitted; novelty and ethical rules apply.[26][30] | Confirms that extended conference papers are acceptable given substantial new content. | Yes |
| "Future Generation Computer Systems guide for authors" | Web (FGCS guide) | 2026-05-22 | Explicitly notes that manuscripts extending work presented at conferences or workshops are welcome, provided there is substantial novelty.[27] | Confirms that FGCS will consider well-extended versions. | Yes |
| "Computers & Security" journal homepage and scope | Web (ScienceDirect and external summaries) | 2026-05-22 | Focus on IT and network security, including IDS, IoT security, and FL-based defenses; multiple past FL-IDS papers appear in this journal.[29][38] | Confirms suitability of COSE as primary target. | Yes |
| FL-IDS green computing review | Web (ScienceDirect) | 2026-05-22 | Survey of federated learning for sustainable IDS; highlights need for energy and communication metrics and life-cycle perspective.[2] | Extends SoA to include energy/efficiency angle; informs recommendation to include minimal overhead analysis. | Yes |

# 19. Final Red-Team Verdict

## 19.1 Would This Survive a Strong Elsevier Review?
If the Strong extension package is implemented carefully—with one new dataset, a refined CICIoT2023 regime, a model-personalization baseline, a minimal temporal experiment, and deeper fairness/privacy analyses—the resulting journal version should be able to survive a strong review at Computers & Security or Computer Networks, provided that claims are kept tightly bounded to FPR-dispersion fairness under specified conditions and that the conference extension is clearly disclosed and substantial.

## 19.2 What Would Still Be Attacked?
Reviewers may still question the limited number of datasets, the absence of comprehensive robustness and formal privacy guarantees, the reliance on a single AE architecture and E=1 FedAvg, and the offline nature of temporal analysis. Some may argue for more diverse model families or topologies, but those concerns can be contained if the paper clearly frames DATP as a targeted threshold-calibration study rather than a complete FL-IDS system.

## 19.3 Final Priority Order
Top 10 actions in order of priority:
1. Add one modern IoT dataset with realistic clients (ToN-IoT or IoT-23) and replicate DATP’s B1–B2–B4 study.
2. Redefine CICIoT2023 clients at device/MAC level and repeat threshold personalization experiments alongside file-level regime.
3. Implement one model-personalization baseline (FedBN or Per-FedAvg) and compare it with DATP’s threshold personalization on both N-BaIoT and the new dataset.
4. Add a small temporal calibration and recalibration experiment on CICIoT2023 or the new dataset.
5. Conduct fairness and false-alarm burden analyses using existing and new results.
6. Add attack-benign separability diagnostics to explain lower-tail Macro-F1 degradation and failure modes.
7. Perform calibration-set size sensitivity analysis to define practical nmin guidance.
8. Strengthen statistical reporting with bootstrap CIs and effect sizes for main metrics.
9. Include a privacy-leakage and overhead analysis for B4 and per-client thresholds, referencing secure aggregation and FL privacy literature.
10. Carefully frame the journal paper’s contributions as a threshold-calibration and fairness study complementary to model personalization and robustness, and explicitly disclose the extension over the conference paper in the introduction and cover letter.