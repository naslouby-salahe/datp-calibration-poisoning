# DATP Journal Extension Audit

## Executive Summary

Your current paper is already scientifically coherent because it isolates **threshold calibration scope** as the only changing variable over a fixed FedAvg autoencoder, then shows that the threshold choice alone can strongly change **held-out false-positive-rate dispersion** across clients. In its current form, the paper’s strongest and safest claim is narrow: on **N-BaIoT physical-device heterogeneity**, per-client p95 calibration materially reduces cross-client FPR dispersion, while **cluster-mean calibration** partially recovers the gain without device taxonomy; on the **current CICIoT2023 randomized file-defined pseudo-client regime**, no personalization gain is observed. Those claims are well bounded and should be preserved, not broadened. fileciteturn2file0

The main problem is not internal inconsistency. The main problem is **journal sufficiency**. A harsh reviewer can still attack the paper on external validity, novelty framing, stronger-comparison discipline, and temporal calibration realism. Fresh literature since 2022 makes those attacks more dangerous. In particular, the field now contains stronger non-IID FL IDS baselines, explicit personalized FL intrusion-detection frameworks, a federated autoencoder paper that studies thresholding through aggregated summary statistics, and a 2026 dataset-centric benchmark showing that single-dataset FL-IDS evaluation badly overestimates generalization. That means the journal version must stop sounding like “thresholding is underexplored in FL anomaly detection” in the broad sense, and instead defend a **more precise novelty claim**: DATP is a **controlled threshold-scope study** for **device-aware fairness of false-alarm burden** under a **frozen federated encoder**, on **real IoT device heterogeneity**, with bounded claims about when the effect appears and when it does not. citeturn16search5turn18search0turn15search1turn19view0turn29search0

The best journal strategy is **not** to push toward a generic “better FL IDS” paper. That would destroy the paper’s identity and place it into direct competition with broader personalized-FL, aggregation, and cross-dataset IDS papers. The right move is a **Strong** expansion package that preserves DATP’s identity while closing the largest review loopholes. The package I recommend is: **one new external dataset** (Edge-IIoTset), **one redesigned CICIoT2023 partition family** with meaningful heterogeneity instead of randomized pseudo-clients, **one mandatory stronger FL baseline family** (FedProx), **one optional but valuable model-personalization comparator** (Ditto), **four focused threshold extensions** that still look like DATP rather than a new paper, **one temporal threshold-aging / recalibration experiment family**, and **six deeper analyses** that explain mechanisms and failure modes rather than merely adding more scores. citeturn28search7turn27view2turn18search0turn9search1turn20search23

The best Elsevier target is **Cyber Security and Applications**. It is in scope for cybersecurity, IoT security, and machine-learning-based cyber defense, and its journal page explicitly states that it **accepts substantially extended conference papers**. By contrast, **Computers & Security should be ruled out**: its current scope page says that, as of early 2024, submissions with AI/ML as significant components are not considered, and it explicitly says items directed to the security of AI/ML systems, including federated learning, are out of scope. citeturn23view3turn22view0

My final decision is therefore clear. **Best target journal:** *Cyber Security and Applications*. **Best expansion level:** *Strong*. **The journal submission should wait until the conference outcome is known and, if accepted, be disclosed and cited as prior work**; simultaneous or ambiguous overlap is a needless ethics and desk-rejection risk under Elsevier’s general originality rules and the journal-specific extension expectations used by explicit conference-friendly titles. citeturn25view0turn23view3turn21view4turn21view5

## What DATP Already Proves

The current paper is titled **“Device-Aware Threshold Personalization: A Controlled Threshold-Calibration Study for Non-IID Federated IoT Anomaly Detection.”** It explicitly frames its core move as a **threshold-only controlled comparison** over a fixed FedAvg autoencoder with shared training protocol, shared seeds, and reused per-client score artifacts, using **B1 shared threshold**, **B2 per-client threshold**, **B3 family-mean threshold**, and **B4 cluster-mean threshold**. It also states that the primary confirmatory regime is **N-BaIoT with nine physical devices**, while **CICIoT2023** is used as an applicability-boundary regime with file-level pseudo-clients, and synthetic Dirichlet partitions of N-BaIoT are used as a heterogeneity-severity sweep. fileciteturn2file0

The current paper’s strongest result is also its cleanest one: under N-BaIoT physical-device heterogeneity, **B2 reduces CV(FPR) from 1.017 to 0.299**, with a reported bootstrap confidence interval for the mean delta and positive B1–B2 deltas across all five seeds; **B4 recovers about 52%** of that gain without requiring device taxonomy. At the same time, the paper already honestly reports a trade-off: **P10 Macro-F1 degradation** is concentrated in the **Ennio Doorbell** client, whose benign-vs-attack separability is weakest, while the high-FPR tail under B1 is driven by **SimpleHome XCS7**. The current manuscript correctly interprets DATP as an **FPR-dispersion calibration policy**, not as a universal detection-quality improvement. That framing is exactly right and should remain intact in the journal version. fileciteturn2file0

The paper also already does more than many conference papers in terms of boundary discipline. It states its limits explicitly: **nine devices**, **E=1 with full participation**, **five seeds**, no online drift modeling, no poisoning/backdoor/evasion evaluation, no privacy mechanism, and a CICIoT2023 conclusion that applies only to the **tested randomized pseudo-client partition**. Those limitations are not weaknesses to hide; they are evidence that the paper already understands its boundary conditions. A strong journal extension should preserve that honesty while adding evidence exactly where it matters most. fileciteturn2file0

The attached state-of-the-art document is aligned with that logic. It argues that the field’s real deficits are not just “better model accuracy,” but weakly standardized heterogeneity treatment, shallow privacy validation, incomplete adversarial stress-testing, and thin deployment evidence. It also places **heterogeneity benchmarking and convergence mapping** at the top of the thesis priority order. That means DATP is already well positioned conceptually, but it underuses that positioning in its current experimental package. fileciteturn2file1

## What Fresh Literature Changes

Fresh literature does **not** kill DATP’s novelty, but it **does** force a narrower and more defensible novelty statement. The most important novelty threat is not a direct IoT clone of DATP. It is the existence of adjacent work showing that **federated anomaly-threshold design is no longer an untouched space**. In particular, Laridi et al. propose a federated autoencoder thresholding method based on aggregated summary statistics, using both normal and anomalous validation data to produce a global threshold. That paper is not an IoT paper, does not study device-level FPR fairness, and does not perform DATP’s frozen-encoder threshold-scope audit; however, it means the journal version must **not** claim that thresholding in federated anomaly detection is broadly unstudied. DATP should instead claim novelty in its **controlled threshold-scope attribution**, **real IoT device heterogeneity**, **held-out FPR-dispersion fairness objective**, and **taxonomy-free grouped approximation via B4**. citeturn15search1

The second major change is that recent FL-IoT IDS work has become broader and more competitive. Mothukuri et al. already framed FL-based anomaly detection for IoT security attacks in 2022. Belarbi et al. showed in 2023 that realistic non-IID IoT IDS on TON-IoT suffers under realistic client partitions, and they explicitly compared **FedAvg, FedProx, and FedYogi**, with central training still stronger. Olanrewaju-George et al. used N-BaIoT in a 2025 federated IDS study with both supervised and unsupervised deep models. FedMSE in 2025 proposed a semi-supervised autoencoder-plus-centroid approach with a new aggregation rule for IoT intrusion detection. FD-IDS in 2025 combined a proximal term and knowledge distillation for Non-IID IoT intrusion detection on Edge-IIoTset and N-BaIoT. pFedCross in 2025 pushed the personalized-model direction in intrusion detection rather than threshold-only calibration. None of these papers invalidates DATP’s controlled design, but all of them raise the reviewer expectation that a journal paper should show whether DATP survives at least one **stronger FL training baseline** and at least one **modern external benchmark**. citeturn16search7turn18search3turn16search1turn16search5turn18search0turn29search0

The third major change is benchmark realism. The official CICIoT2023 dataset page states that the dataset was built from **105 devices** and **33 attacks** grouped into seven categories. Edge-IIoTset was explicitly created for use in both **centralized and federated learning** and was generated from a purpose-built IoT/IIoT testbed. MedBIoT provides **83 devices**, including real and emulated devices, with **Mirai, BashLite, and Torii**, and its official page says it supports both supervised and **unsupervised anomaly/outlier detection**. Meanwhile, a 2026 dataset-centric Scientific Reports study shows that FL IDS models evaluated on a single dataset can look good in-domain yet lose up to **30 macro-F1 points** under cross-dataset shift, and that combined-dataset training materially restores transfer. Even if DATP does not adopt a full cross-dataset generalization program, this literature makes it much harder to defend a journal paper that relies on **N-BaIoT plus a weak CICIoT2023 pseudo-client construction**. citeturn27view2turn28search7turn27view0turn19view0

The fourth change concerns threshold realism. Recent anomaly-detection work increasingly emphasizes **false-alarm control**, **adaptive thresholds**, and **recalibration under drift** rather than static one-shot thresholds. Conformal anomaly detection papers now make the false-positive-rate target explicit, and adaptive thresholding work outside IoT keeps pushing the same point: a threshold that looks good on one calibration slice may age poorly when distributions move. That does not mean DATP should become a conformal anomaly-detection paper. It does mean a journal reviewer can now reasonably ask for a **minimum viable threshold-aging experiment**. citeturn20search23turn20search11turn11search21

The fifth change is privacy framing. The state-of-the-art already warns that structural data locality is not the same thing as formal privacy. Fresh literature continues to support that caution for FL in general, including leakage risk through updates and incomplete privacy guarantees even under secure aggregation. I did **not** find threshold-specific empirical leakage papers for shared percentiles, local benign p95 summaries, or B4 cluster fingerprints in the sources reviewed. The safe consequence is simple: the journal version should state that client-level thresholds and B4 fingerprints are **distributional metadata** and therefore **should not be marketed as privacy-preserving artifacts** unless protected by an explicit mechanism. fileciteturn2file1 citeturn12search6turn12search16turn13search1

### Fresh-literature impact matrix

| Paper or source | What it changes for DATP | Use in journal version |
|---|---|---|
| Laridi et al., *Scientific Reports* 2024 | Broad “thresholding in federated anomaly detection is unexplored” claim is no longer safe; however, their method uses a **global threshold** from summary statistics and anomalous validation data, not DATP’s device-aware held-out fairness analysis. | **Must cite** and **must contrast**, but **experimental comparison is optional**, because the label assumptions and objective differ. citeturn15search1 |
| Belarbi et al., GLOBECOM 2023 | Reviewers can reasonably ask for **FedProx/FedYogi-style non-IID aggregation baselines** in IoT IDS. | **Must compare to at least FedProx**. citeturn18search3 |
| FedMSE 2025 | Shows an autoencoder-centered IoT FL paper can claim stronger non-IID handling through aggregation changes. | **Must cite**; **comparison optional** if scope/time is tight. citeturn16search5 |
| FD-IDS 2025 | Raises the bar for non-IID IoT IDS baselines and modern dataset validation. | **Must cite**; **comparison optional**, unless Edge-IIoTset becomes central. citeturn18search0 |
| pFedCross 2025 | Brings **personalized FL** directly into intrusion detection, creating a novelty threat if DATP is framed as “personalization” in the broad model-level sense. | **Must cite**; **one model-personalization comparator is advisable**. citeturn29search0 |
| Bilal et al., *Scientific Reports* 2026 | Makes cross-dataset external validation far more important and makes single-dataset FL IDS evaluation easier to attack. | **Must use as motivation** for at least one modern external dataset. citeturn19view0 |
| Official Edge-IIoTset page/paper | Gives an FL-ready modern IoT/IIoT benchmark that is easier to justify than older synthetic options. | **Best dataset addition**. citeturn28search7 |
| Official CICIoT2023 page | Undercuts the current pseudo-client regime, because the dataset itself contains a much richer real-device topology than the present construction exploits. | **Current regime should be redesigned or explicitly downgraded**. citeturn27view2 |

## Reviewer Attack Surface

The highest-risk review attacks are the ones below. These are the attacks that a harsh reviewer could make **immediately**, and they are the ones the journal extension must close first.

| Reviewer attack | Why it lands today | What closes it | Feasibility |
|---|---|---|---|
| “B2 equalizes FPR by construction; where is the science?” | The paper itself already notes that per-client p95 should equalize benign-tail false alarms under stable calibration/test distributions. Without more analysis, a reviewer can say the result is mechanical. | Add **held-out calibration mismatch analysis**, **threshold-aging / recalibration**, **calibration-size sensitivity**, and **distribution-divergence vs. benefit correlation**. That turns the journal claim from “it works” into “here is when and why it works, and when it fails.” | Immediate to Moderate, depending on timestamp access. fileciteturn2file0 citeturn20search23turn20search11 |
| “Nine devices on N-BaIoT is too small and too old.” | True for journal-level external validity. N-BaIoT is still useful, but no longer enough by itself. | Add **one modern external dataset**, preferably **Edge-IIoTset**. | Moderate. citeturn27view5turn28search7 |
| “CICIoT2023 is underused and the pseudo-clients are not meaningful clients.” | Also true. The official dataset is much richer than the current file-level randomized client construction. | Rebuild CICIoT2023 clients by **device/application/source-session / chronology** if metadata permit; otherwise explicitly demote the current regime to a weak boundary check. | Moderate to Heavy. fileciteturn2file0 citeturn27view2 |
| “Maybe DATP’s gain disappears under a better FL optimizer or heterogeneity-aware training.” | Recent IoT FL IDS papers now routinely compare stronger FL methods. | Add **FedProx** as the mandatory stronger baseline family; optionally add one personalization comparator. | Moderate. citeturn18search3turn18search0turn29search0 |
| “This is threshold personalization, but where are the model-personalization baselines?” | Because personalized FL is now an established comparison class. | Add **one** model-personalization comparator, ideally **Ditto**, not a whole zoo. | Heavy but high reviewer value. citeturn9search1turn9search0turn10search7 |
| “There is no temporal analysis, so stability in deployment is unknown.” | Recent thresholding literature makes this omission more salient. | Add **one threshold-aging and recalibration experiment family**. | Moderate. citeturn20search23turn20search11 |
| “B4 is interesting, but I do not understand what the clusters reflect.” | Without interpretability or ablation, B4 looks ad hoc. | Add **cluster-feature ablation** and **cluster interpretability analysis**. | Immediate to Moderate. fileciteturn2file0 |
| “You mention privacy, but where is the privacy mechanism?” | The current manuscript already says B4 is not private, but reviewers will attack any loose wording. | Remove all privacy-positive phrasing; use only **bounded metadata-leakage language**. | Immediate. fileciteturn2file0 citeturn12search6turn13search1 |

## The Recommended Strong Package

### Exact package

This is the single package I recommend. It is intentionally **not** an unlimited wishlist.

| Component | Recommendation | Why it is needed | Feasibility | Support status |
|---|---|---|---|---|
| New dataset | **Add Edge-IIoTset** | Modern, FL-ready, explicitly designed for centralized and federated learning; strongest single external validation add-on without changing the paper’s identity. | Moderate | Requires new dataset and new runs. citeturn28search7 |
| Current secondary dataset | **Redesign CICIoT2023 partitioning** | The official dataset has 105 devices and 33 attacks; the present randomized pseudo-client regime underuses it. | Moderate to Heavy | Requires new experiments, not a new dataset. citeturn27view2 |
| Stronger FL baseline family | **Add FedProx** | Most defensible “better-than-FedAvg under non-IID” comparator that does not change the paper into a different research program. | Moderate | Requires new experiments. citeturn18search3turn9search11 |
| Model-personalization comparator | **Add Ditto if feasible** | Answers the reviewer question: does threshold personalization still matter when the model itself is personalized? | Heavy | Requires substantial new experiments. citeturn9search1 |
| Threshold variant | **Local-global shrinkage threshold** | Directly tests whether part-way personalization can recover fairness while limiting TPR loss. | Immediate | Requires recomputation from existing score artifacts. |
| Threshold variant | **Robust cluster-median threshold** | Tests whether B4 is being driven by outlier clients inside clusters. | Immediate | Requires recomputation from existing score artifacts. |
| Threshold variant | **Calibration-size-aware fallback** | Closes the real deployment loophole created by small benign calibration sets. | Immediate | Requires recomputation from existing score artifacts. |
| Threshold sensitivity | **Expanded q-grid** | Reviewers will ask whether the DATP effect is only a p95 artifact. | Immediate | Requires recomputation from existing score artifacts. |
| Temporal family | **Threshold aging + one-shot recalibration** | The minimum journal-level temporal addition that still preserves DATP’s identity. | Moderate | Requires chronological or session-aware runs. citeturn20search23turn20search11 |
| Deeper analysis | **Six focused analyses** | Converts results into mechanism and boundary understanding. | Immediate to Moderate | Mostly recomputation from existing score artifacts. |

### The six deeper analyses that are actually worth doing

These six analyses add the most reviewer value without scope drift.

| Analysis | What it proves | What it does not prove | Priority |
|---|---|---|---|
| Client-level benign and attack score distributions with B1/B2/B4 overlays | Shows the mechanism of false-alarm concentration and client-specific threshold movement. | Does not prove deployment drift robustness. | Must-do |
| JS or Wasserstein divergence of benign score distributions vs. DATP gain | Tests whether heterogeneity severity predicts DATP value. | Does not prove causality beyond the tested protocol. | Must-do |
| Threshold shift vs. ΔFPR and ΔTPR scatter | Shows how much fairness gain costs in detection sensitivity. | Does not solve the trade-off. | Must-do |
| Ennio Doorbell failure-mode deep dive | Explains why P10 Macro-F1 drops and prevents overgeneralized trade-off claims. | Does not prove the same failure mode elsewhere. | Must-do |
| Calibration-set size sensitivity and coverage/fallback simulation | Tests whether DATP remains usable when benign calibration is limited. | Does not replace real online cold-start evaluation. | Must-do |
| B4 cluster-feature ablation and interpretability | Defends B4 as a meaningful taxonomy-free approximation rather than a lucky heuristic. | Does not make B4 private. | Should-do |

### Must-do, should-do, optional, do-not-do

**Must-do** before journal submission:

1. Add **Edge-IIoTset** as the main new external benchmark. citeturn28search7  
2. Replace or meaningfully redesign the current **CICIoT2023 pseudo-client regime**. citeturn27view2  
3. Add **FedProx** as the mandatory stronger FL baseline family. citeturn18search3turn9search11  
4. Add the three threshold extensions that keep the paper recognizably DATP: **shrinkage**, **robust cluster median**, **calibration-size-aware fallback**, plus the expanded **q-grid**.  
5. Add **one threshold-aging / recalibration experiment family**. citeturn20search23turn20search11  
6. Add the six mechanism analyses above.  

**Should-do** if time allows:

1. Add **Ditto** as exactly one model-personalization comparator. citeturn9search1  
2. Translate fairness into an **operational false-alarm burden** table or figure.  
3. Expand the replication artifact so that the journal version is visibly more reproducible than the conference version.  

**Optional** supplementary or future work:

1. A second added dataset, preferably **MedBIoT**, if preprocessing is tractable and time permits. It is highly aligned with botnet/anomaly framing and supports unsupervised use, but it is not necessary for the first journal submission. citeturn27view0  
2. A second stronger FL baseline such as **FedNova** or **FedYogi**, only if you already have the infrastructure and the results add a clear story rather than noise. citeturn19view0turn18search3  
3. A conformal or risk-controlling thresholding add-on, but only as supplement or future work; it is useful literature context, not the center of this journal extension. citeturn20search23turn20search11  

**Do-not-do**:

1. Do **not** add many FL models, many datasets, and privacy/robustness/deployment bundles all at once. That turns DATP into a generic FL-IDS paper and weakens the contribution.  
2. Do **not** claim that DATP is a privacy mechanism.  
3. Do **not** claim that threshold personalization always improves detection quality.  
4. Do **not** continue to frame CICIoT2023’s current null result as a general statement about that dataset.  
5. Do **not** target **Computers & Security** for this work. Its current scope page explicitly excludes papers where AI/ML is a significant component and says federated learning is out of scope. citeturn22view0

### Claim consistency check

| Proposed claim | Current support status | Safe wording |
|---|---|---|
| DATP materially reduces held-out FPR dispersion on N-BaIoT physical-device heterogeneity under a fixed FedAvg AE. | Already supported by current paper/results. | “Under the tested N-BaIoT protocol, threshold scope alone strongly changes false-alarm dispersion across clients.” fileciteturn2file0 |
| B4 is a useful taxonomy-free approximation to B2. | Already supported for current protocol. | “Under the tested N-BaIoT protocol, B4 recovers part of B2’s fairness gain.” fileciteturn2file0 |
| DATP generalizes to modern IoT benchmarks. | Requires new datasets. | Claim only after Edge-IIoTset results are in. |
| DATP remains useful under stronger non-IID FL training. | Requires new experiments. | Claim only after FedProx comparison. |
| DATP complements rather than duplicates model personalization. | Requires new experiments. | Claim only after Ditto-style comparator. |
| DATP can handle limited benign calibration. | Requires recomputation from existing score artifacts. | “Sensitivity suggests…” rather than absolute deployment claims. |
| DATP is robust to threshold aging and drift. | Requires new experiments. | Claim only after temporal/recalibration study. |
| DATP preserves privacy. | Should not be claimed. | Replace with bounded metadata wording only. |
| B4 is privacy-safe. | Should not be claimed. | Do not claim. |
| Threshold personalization helps in CICIoT2023 generally. | Should not be claimed. | Keep the current partition-scoped null result. fileciteturn2file0 |

## Venue Strategy and Conference-Extension Decision

### Target-journal matrix

| Journal | Scope fit | Conference-extension policy found in official source | Main risk | Verdict |
|---|---|---|---|---|
| **Cyber Security and Applications** | Strong match: cyber attacks, machine learning for cybersecurity, IoT cybersecurity are explicitly in scope. | **Yes.** The journal page explicitly says it accepts “substantially extended version of the conference papers.” | Newer journal and open-access positioning, but policy clarity is excellent. | **Best target.** citeturn23view3turn4search3 |
| **Journal of Information Security and Applications** | Strong match in information security and technical contributions. | **Not found clearly** in the guide; the guide uses the standard Elsevier submission declaration, while the journal page says it regularly invites best papers from renowned venues. | Policy ambiguity for ordinary conference extensions; requires careful editor-facing disclosure. | **Second choice.** citeturn21view1turn23view0turn23view2turn4search1 |
| **Computer Networks** | Good if the journal paper emphasizes networked IoT anomaly detection, practical analyses, and systems implications. | **Yes.** The guide explicitly allows enhanced, extended versions of quality conference/workshop papers. | Slightly less security-specific than CSA/JISA. | **Strong fallback.** citeturn21view5turn4search25 |
| **Internet of Things** | Strong if framed around IoT device heterogeneity, AIoT, and IoT security/privacy rather than generic cybersecurity. | **Not found clearly** in the sources reviewed. | Reviewers may expect a stronger IoT-system narrative and broader deployment implications. | **Good but less certain than CSA.** citeturn23view4turn23view5turn4search5 |
| **Future Generation Computer Systems** | Methodologically possible, but only if the paper becomes broader in FL systems contribution. | **Yes.** The guide explicitly requires **40% new contributions**, a different title, citation of the original paper, and a cover letter listing the new sections. | Page limit, higher breadth expectation, and higher scope-drift risk. | **Ambitious stretch target, not my recommendation.** citeturn21view4turn2search1 |
| **Computers & Security** | Historically attractive, but no longer suitable. | Conference-extension policy is not the issue. **Scope is the issue.** | Its current scope page says AI/ML-heavy submissions and federated learning are out of scope. | **Do not target.** citeturn22view0 |

### Originality threshold for the journal version

The current conference paper contribution is a **controlled threshold-scope study**. The minimum acceptable journal extension is therefore **not** cosmetic rewriting, additional related work, or a few more plots. The journal version must add a **materially stronger evidentiary package**: at least one modern external benchmark, at least one stronger FL training comparator, a threshold-aging / recalibration result, and mechanism-level analysis that explains both the gains and the failure mode. That is what makes the extension “substantially extended” in practice, even for journals that do not publish a numerical novelty percentage. citeturn23view3turn21view5turn25view0

For cover-letter disclosure, the safest position is straightforward: state that the journal manuscript extends the conference paper by adding new dataset validation, stronger non-IID federation baselines, additional threshold variants, temporal recalibration analysis, and new mechanism/failure-mode analyses; cite the conference version directly; provide a side-by-side list of new sections and experiments; and keep the title different from the conference title. That advice is mandatory for journals with explicit extension rules such as CSA, FGCS, and Computer Networks, and prudent everywhere else under Elsevier’s general originality and redundancy guidance. citeturn23view3turn21view4turn21view5turn25view0

### Final decision gate

**Best target journal:** **Cyber Security and Applications.** citeturn23view3turn4search3

**Best expansion level:** **Strong.**

**Exact must-do list before submission:**  
Add Edge-IIoTset; redesign CICIoT2023 client construction; add FedProx; add shrinkage / robust-cluster-median / calibration-size-aware fallback thresholds plus expanded q-sensitivity; add one threshold-aging and one-shot recalibration family; add six deeper analyses; tighten wording so DATP is presented as a fairness-oriented threshold-scope study, not a universal accuracy or privacy paper. citeturn28search7turn27view2turn18search3turn20search23

**Exact do-not-do list to avoid scope drift:**  
Do not add many datasets; do not add many personalized-FL baselines; do not bolt on full privacy-preserving FL or adversarial-robust FL as primary contributions; do not claim universal accuracy gains; do not target Computers & Security. citeturn22view0

**Should the journal extension wait until conference acceptance?** **Yes.** Prepare it now, but do not submit the journal version while the conference paper is still in editorial limbo. If the conference is accepted, cite it and disclose the extension clearly. If it is rejected, the journal paper can proceed as an original submission with the stronger package, but you still should not run simultaneous overlapping submissions. citeturn25view0turn23view3turn21view5

## Search Audit and Open Questions

### Search audit log

| Search/source checked | Source type | Date checked | Key finding | Confirmed, changed, or contradicted the attached state of the art | Used in final recommendation |
|---|---|---:|---|---|---|
| DATP.pdf | Attached primary artifact | 2026-05-22 | Confirmed the frozen-encoder threshold-only design, the N-BaIoT result, B4 recovery, the CICIoT2023 boundary result, and stated limitations. | Confirmed | Yes. fileciteturn2file0 |
| State_of_the_Art.md | Attached synthesis artifact | 2026-05-22 | Confirmed heterogeneity, privacy, deployment, and reproducibility gap framing. | Confirmed | Yes. fileciteturn2file1 |
| Laridi et al. 2024 | Peer-reviewed paper | 2026-05-22 | Federated autoencoder thresholding via aggregated summary statistics exists outside IoT. | **Changed** novelty framing | Yes. citeturn15search1 |
| Belarbi et al. 2023 | Conference paper / primary PDF | 2026-05-22 | Realistic non-IID IoT IDS comparisons with FedAvg, FedProx, and FedYogi already exist. | Confirmed and strengthened baseline-comparison need | Yes. citeturn18search3 |
| FedMSE 2025 | Journal abstract/source page | 2026-05-22 | Semi-supervised autoencoder + new aggregation for IoT intrusion detection; strengthens aggregation-comparison expectations. | Confirmed and strengthened | Yes. citeturn16search5 |
| FD-IDS 2025 | Journal abstract/source page | 2026-05-22 | Non-IID IoT IDS with proximal term + knowledge distillation on Edge-IIoTset and N-BaIoT. | Confirmed and strengthened dataset/baseline pressure | Yes. citeturn18search0 |
| Bilal et al. 2026 | Peer-reviewed paper | 2026-05-22 | Cross-dataset FL IDS generalization is fragile; multi-dataset evidence matters. | **Strengthened** external-validation requirement | Yes. citeturn19view0 |
| Official CICIoT2023 page | Official dataset page | 2026-05-22 | Dataset has 105 devices and 33 attacks; current pseudo-client use clearly underexploits it. | **Contradicted** any strong use of current Regime B as rich external validation | Yes. citeturn27view2 |
| Official Edge-IIoTset paper/page | Dataset paper/repository page | 2026-05-22 | Explicitly positioned for centralized and federated learning. | Confirmed best dataset-add choice | Yes. citeturn28search7 |
| Official MedBIoT page | Official dataset page | 2026-05-22 | 83 devices, Mirai/BashLite/Torii, unsupervised use possible. | Added optional second-dataset option | Yes, as optional. citeturn27view0 |
| Elsevier and journal pages | Official publisher/journal pages | 2026-05-22 | CSA explicitly accepts extended conference papers; Computer Networks and FGCS do too; Computers & Security currently excludes AI/ML-heavy and FL papers. | **Changed** venue ranking decisively | Yes. citeturn23view3turn21view5turn21view4turn22view0 |

### Open questions and limitations

A few decisions remain contingent on artifacts you already have but that were not fully verifiable in the attached materials. The most important are whether your current stored score artifacts preserve enough ordering or timestamp information for a meaningful threshold-aging study, and whether your CICIoT2023 preprocessing retains enough source/session/device structure to rebuild clients in a way that reflects real heterogeneity rather than arbitrary file identity. If the answer to either is no, the paper should **say so explicitly**, downgrade the corresponding claim, and avoid pretending that a weak proxy is real deployment drift. fileciteturn2file0 citeturn27view2

I also did not find a direct empirical literature on privacy leakage from **shared percentile thresholds**, **shared benign-tail summaries**, or **cluster fingerprints** in exactly the DATP setting. The safe interpretation is therefore conservative: discuss them as potentially sensitive **distributional metadata**, not as a quantified privacy result, and leave formal privacy protection to future work unless you actually add a mechanism. citeturn12search6turn13search1