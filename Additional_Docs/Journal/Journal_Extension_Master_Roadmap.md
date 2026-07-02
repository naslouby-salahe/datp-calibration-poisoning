# Journal Extension Master Roadmap for DATP

> **ARCHIVED INPUT CONTEXT — NOT AN OPERATIONAL ROADMAP.**
>
> This file is archived input context only. The active journal planning package is limited to:
> - `docs/journal/PRE_CODING_PLAN.md`
> - `docs/journal/CODING_PLAN.md`
> - `docs/journal/EXPERIMENT_PLAN.md`
> - `docs/journal/POST_EXPERIMENT_PLAN.md`
>
> If this file conflicts with those four files, the four-file package wins.
>
> **Stale file references in this document.** The following files referenced below were never created and do not exist. Their content has been merged into the four-file planning package. All references to them in this document are archive-only and non-operational. Do not create, consult, or update any of these files:
> - `docs/journal/claim_survival_matrix.md` → fallback wording is in `docs/journal/POST_EXPERIMENT_PLAN.md §2`
> - `docs/journal/LIVE_VERIFICATION_REGISTER.md` → source-status records are in `docs/journal/PRE_CODING_PLAN.md §5.8`
> - `docs/journal/CICIOT2023_BB_FEASIBILITY.md` → B-b feasibility logic is in `docs/journal/PRE_CODING_PLAN.md §5.4`
> - `docs/journal/EDGE_IIOTSET_FEASIBILITY.md` → Regime D feasibility logic is in `docs/journal/PRE_CODING_PLAN.md §5.5`
> - `docs/journal/journal_extension_overlap_report.md` → overlap guidance is in `docs/journal/POST_EXPERIMENT_PLAN.md §8`
> - `docs/journal/ciciot2023_metadata_feasibility.md` → metadata check is in `docs/journal/PRE_CODING_PLAN.md §5.4`
>
> **Stale comparator label.** `LocalHead-PersonalizedAE` was a rejected placeholder. The canonical label is: Ditto if implemented faithfully; otherwise `FedRep-AE` or `FedPer-AE` fallback, clearly labeled as a recognized shared-representation/local-head personalization family and never called Ditto. Use `FedRep-AE/FedPer-AE fallback` as the compact label. See `docs/journal/PRE_CODING_PLAN.md §6.4`.

---

## 0. Locked Main Journal Claim

> **DATP's threshold-scope effect remains observable under a stronger journal protocol that adds external validation, a matched federated-threshold comparator, and model/aggregation stress tests, while preserving the fixed-encoder threshold-calibration identity.**

- Sole confirmatory endpoint: Regime A, B1 vs B2, CV(FPR), 10-seed BCa CI on per-seed Δₛ.
- Everything else (Regime B-a, conditional Regime B-b, Regime C, Regime D, all threshold variants, all stress tests, all mechanism analyses) is *supportive*, *external validation*, *stress test*, *mechanism analysis*, *exploratory*, or *boundary condition*.
- B4 canonical K for the main paper: **K = 3**. K = 9 and other K values are exploratory / supplementary only (SB-32).
- See `docs/journal/POST_EXPERIMENT_PLAN.md §2` for every pre-specified fallback wording. *(ARCHIVE NOTE: `claim_survival_matrix.md` was never created.)*

---

## 1. Executive Summary

The journal version of DATP targets **Computer Networks (Elsevier)** as the primary venue, with **Internet of Things (Elsevier)** as a principled backup. **Computers & Security is excluded**: its Aims & Scope page carries a moratorium, in effect since early 2024, on submissions whose primary subject is the security of AI/ML systems themselves (including federated learning) **and** on submissions that feature AI/ML as significant components (including applying AI/ML techniques to security/privacy topics). FedMSE (COSE 2025) and earlier FL-IDS papers in COSE predated the moratorium and are not a safe precedent. *(ARCHIVE NOTE: `LIVE_VERIFICATION_REGISTER.md` V-06 — file not created; fact merged into PRE_CODING_PLAN.md §5.8.)*

The expansion follows the **Strong** level defined in §14: more than the Minimal package needed to survive Q1 review, but well short of the Ambitious option, which would dissolve DATP's identity into a generic FL-IDS paper.

Experiments begin immediately, but the journal submission waits until the conference camera-ready is set. This protects against Elsevier's redundancy and originality rules and lets the conference paper serve as a citable anchor.

The one-line strategy is to keep DATP a *threshold-scope-only, fixed-encoder, FPR-equity* study, and to extend it along five disciplined axes: one new device-partitioned dataset (Edge-IIoTset), three external stress-test comparator families that close the strongest novelty and "model-personalization-makes-it-obsolete" attack lines, four threshold variants that deepen the calibration story, one chronological-split temporal recalibration experiment, and six mechanism analyses.

The most significant residual risk is **novelty collapse against Laridi et al. (Sci. Rep. 2024)**. The original Laridi method uses summary statistics from **both normal and anomalous validation data** *(ARCHIVE NOTE: verified — `LIVE_VERIFICATION_REGISTER.md` V-01 not created; fact in PRE_CODING_PLAN.md §5.8)*. DATP must cite, contrast, and quantitatively compare against two clearly separated variants:

- **`B-LaridiFaithful`** — a relaxed reproduction that uses normal and anomalous summary statistics (only when attack-labeled calibration data is allowed; out of DATP's calibration assumption);
- **`B-FedStatsBenign`** — a DATP-compatible benign-only comparator that diverges from the original Laridi method by removing access to anomaly-labeled validation data.

A benign-only adaptation alone **does not** resolve the Laridi novelty risk. If `B-LaridiFaithful` is not implemented because it falls outside DATP's benign-only assumption, this is documented explicitly; DATP is then framed as benign-only local threshold personalization, not as globally superior thresholding.

---

## 2. Input Corpus Inventory

| File | Role | Used | Main Contribution | Reliability |
|---|---|---|---|---|
| DATP.pdf | Current paper | Yes | Threshold-scope-only controlled study; CV(FPR) 1.017→0.299 on N-BaIoT; B4 ≈52% recovery; CICIoT2023 null under file-level pseudo-clients | Primary anchor |
| State_of_the_Art.md | Literature context | Yes | 40-study corpus with 6 gap clusters | Primary anchor |
| Blueprint.md | Methodology lock | Yes | RQ hierarchy, claim discipline, statistical tests, null-finding contingencies; confirms no BN in encoder | Primary anchor |
| Audit A | Strategy note | Partial | Cyber Security and Applications + Edge-IIoTset; correctly rules out COSE | Mixed |
| Audit B | Strategy note | Partial | COSE + ToN-IoT; misses moratorium | Partially wrong |
| Audit C | Detailed analysis | Yes | Strongest baseline and threshold analysis; cites COSE moratorium; recommends Internet of Things | Highly reliable |
| Audit D | Detailed analysis | Yes | Best novelty-threat analysis (Laridi 2024, Sáez-de-Cámara 2023); recommends Computer Networks via Rey 2022 lineage | Highly reliable |
| Audit E | Strategy note | Partial | JNCA + FedBN/temporal; misses moratorium | Mixed |
| Audits F, G | Strategy notes | Rejected for venue | Recommend COSE; miss moratorium | Wrong on venue |

Two limitations of this corpus deserve a flag. First, no audit independently verified Laridi's performance on N-BaIoT score distributions, so the DATP-compatible adaptation must be pre-specified before results are inspected (see B-FedStatsBenign Protocol Lock in `docs/journal/PRE_CODING_PLAN.md`). Second, Blueprint.md / Algorithm 1 confirms the current AE has no BatchNorm layers; FedBN therefore requires altering the encoder, which is incompatible with the frozen-encoder discipline. FedBN is rejected throughout this roadmap. *(ARCHIVE NOTE: §8.4 was the old roadmap reference; the operational lock now lives in PRE_CODING_PLAN.md.)*

---

## 3. Current DATP Identity

DATP is a fixed-encoder, fixed-FedAvg, **threshold-scope-only** controlled comparison: *Device-Aware Threshold Personalization: A Controlled Threshold-Calibration Study for Non-IID Federated IoT Anomaly Detection*.

The sole confirmatory experimental variable is threshold calibration scope. The AE architecture, optimizer, round budget, seeds, and per-client score artifacts are identical across B1, B2, B3, and B4. FedProx and Ditto are *external stress-test comparators* and are not part of this causal ladder.

**Datasets.** N-BaIoT (9 physical-device clients, Mirai/BASHLITE); CICIoT2023 (63 file-defined pseudo-clients, JS mean 0.004); N-BaIoT Dirichlet repartition (α ∈ {0.1, 0.3, 0.5, 1.0, 10.0, IID}, K=20 synthetic clients).

**Regimes.** Regime A (N-BaIoT natural physical-device split, confirmatory); Regime B-a (CICIoT2023 file-level pseudo-clients, near-homogeneous boundary); Regime B-b (conditional CICIoT2023 device-MAC **or** device-group repartition — exact basis depends on Gate 0 B-b outcome in PRE_CODING_PLAN.md §5.4 *(ARCHIVE: CICIOT2023_BB_FEASIBILITY.md not created)*); Regime C (N-BaIoT Dirichlet severity sweep, α ∈ {0.1, 0.3, 0.5, 1.0, 10.0, IID}, K=20 synthetic clients); Regime D (Edge-IIoTset external validation — device-client or group-client depending on Gate 0 Regime D outcome in PRE_CODING_PLAN.md §5.5 *(ARCHIVE: EDGE_IIOTSET_FEASIBILITY.md not created)*). Regime labels are stable and used identically in the Roadmap, PRE_CODING_PLAN, CODING_PLAN, EXPERIMENT_PLAN, POST_EXPERIMENT_PLAN, tables, and figure plans.

**Baselines.** B0 centralized AE; B1 client-averaged shared τ; B2 per-client p95; B3 family-mean (Regime A only); B4 k-means cluster-mean on a 4-scalar fingerprint [µₑ, σₑ, skewₑ, p95(e)].

**Metrics.** CV(FPR) primary; CV(TPR), IQR(FPR), max−min FPR, worst-client BA, Macro-F1, P10 Macro-F1, coverage ratio, and mean pairwise JS as descriptive severity.

**Statistical logic.** Per-seed Δₛ = CV(FPR)[B1,s] − CV(FPR)[B2,s] across 5 seeds (extended to 10 in the journal version); 95% BCa bootstrap CI on Δ; Wilcoxon and Cliff's δ as secondary descriptive evidence.

**Sole confirmatory claim (locked).** Under Regime A natural device split, B2 reduces CV(FPR) by a magnitude whose 95% BCa bootstrap CI excludes zero.

**Supportive claims.** Regime C shows the B1–B2 gap is largest at low α and vanishes under IID; Regime B-a shows near-homogeneous file-level pseudo-clients are an applicability boundary; q-sensitivity preserves B2 < B4 < B1; pooled and sample-weighted shared variants show the reduction is not driven solely by arithmetic-mean construction.

**Exploratory claims.** B4 with K=3 recovers ≈52% of B2's improvement without taxonomy (exploratory at K=9); JS divergence is a descriptive severity statistic; B3 underperforms because device-type labels do not align with reconstruction-error calibration structure.

**Out of scope (deferred).** Poisoning, backdoor, evasion, formal privacy, hardware or edge profiling, communication-cost measurement, concept drift, E>1 sensitivity, deployment-scale fleets, and model-level personalization beyond the single Ditto stress test.

**Claims that must not be disturbed.** The threshold-scope-only experimental discipline; the Regime A confirmatory result and its bootstrap CI; the Regime B-a negative result framed as an applicability boundary only; the explicit non-privacy framing of B4; and the scoping of all claims to "the tested datasets, partitions, and protocol."

---

## 4. Cross-Audit Consensus and Disagreements

| Topic | Agreement | Disagreement | Decision | Reason |
|---|---|---|---|---|
| Preserve DATP identity | 6/6 | None | Locked | All audits recommend Strong, not Ambitious |
| One new physical-device dataset | 6/6 | Edge-IIoTset (4) vs ToN-IoT (2) | **Edge-IIoTset** | Native FL framing; cleaner client mapping; partitioning decided by first-principles feasibility audit (PRE_CODING_PLAN.md §5.5 — *ARCHIVE: EDGE_IIOTSET_FEASIBILITY.md not created*), not by appeal to any external precedent |
| CICIoT2023 file-level is weak | 6/6 | None | Device-MAC or device-group redesign, conditional on Priority 0 | Priority 0 determines feasibility (PRE_CODING_PLAN.md §5.4 — *ARCHIVE: CICIOT2023_BB_FEASIBILITY.md not created*) |
| Stronger FL training stress test | 6/6 | FedProx (5) vs FedAvgM (3) vs FedYogi (1) | **FedProx** | Belarbi 2023 precedent; Flower-native; framed as external stress test |
| Model-personalization comparator | 5/6 | FedBN (3) vs Ditto (2) vs Per-FedAvg (1) | **Ditto (or `FedRep-AE/FedPer-AE fallback`)** *(ARCHIVE: the obsolete "named local-head variant" placeholder is rejected; see Ditto / FedRep-AE Fallback Lock in `docs/journal/PRE_CODING_PLAN.md`)* | FedBN incompatible with encoder; Ditto is encoder-agnostic |
| Privacy framing | 6/6 | Add MIA probe? | **Qualitative only** | MIA on percentile summaries lacks established IoT literature |
| Temporal experiment | 6/6 | MVE (3) vs full drift (2) vs none (1) | **MVE chronological split + one-shot recalibration**, with three pre-specified outcomes | Outcome interpretations locked before results |
| Target journal | Split | COSE (3) / CN (1) / IoT (1) / CSA (1) / JNCA (1) | **Computer Networks primary; IoT backup** | COSE moratorium; CN extension policy + Rey 2022 lineage |
| Conference-extension novelty threshold | 5/6 cite 30% or 40% | No Elsevier-wide policy | **≥40% substantive new material** | Conservative; aligns with FGCS's explicit rule |
| Wait for conference acceptance | 6/6 | None | **Yes** | Protects against duplicate-publication concerns |
| Conformal thresholding | 3 add / 3 reject | — | **Split-conformal B2-conf** | Closes construction-tautology critique with finite-sample coverage |
| Adversarial robustness | 5/6 out of scope | Audit C suggests light experiment | **Out of scope; discuss only** | Adversarial branch is its own paper |

---

## 5. Weak-Point Register

| # | Weak Point | Severity | Why It Matters | Fix Type | Effort |
|---|---|---|---|---|---|
| W01 | "B2 equalizes FPR by construction" tautology | Critical | Headline result is dismissible if untreated | Mandatory | Moderate |
| W02 | 9 physical clients in confirmatory regime | Critical | External-validity ceiling; N-BaIoT is aging | Mandatory | Moderate |
| W03 | CICIoT2023 at file-level only | Major | File-level pseudo-clients are near-homogeneous; a MAC- or group-based repartition is required for heterogeneity evaluation, conditional on metadata feasibility (PRE_CODING_PLAN.md §5.4 — *ARCHIVE: CICIOT2023_BB_FEASIBILITY.md not created*) | Mandatory (conditional on Priority 0) | Moderate |
| W04 | No comparison to Laridi 2024 | Critical | Closest direct competitor; novelty contested if omitted. Original Laridi uses normal + anomalous summary statistics (V-01); benign-only adaptation alone does not resolve the novelty risk | Mandatory | Moderate |
| W05 | No model-personalization comparator | Major | "Would Ditto make B2 redundant?" | Mandatory | Heavy |
| W06 | No stronger FL aggregation stress test | Major | Belarbi 2023 and FedMSE 2025 compare FedProx/FedAvgM | Mandatory | Moderate |
| W07 | No temporal drift or recalibration | Major | Operational reality | Mandatory | Moderate |
| W08 | B4 metadata leakage not quantified | Moderate | Reviewers may push for DP/SecAgg | Recommended | Low |
| W09 | Five seeds only | Moderate | Statistical power | Recommended | Immediate (10 seeds) |
| W10 | No calibration-size sensitivity beyond n_min=100 | Moderate | Operational realism for low-data clients | Recommended | Immediate |
| W11 | No operational alert-burden translation | Moderate | Practitioners read alerts/day, not abstract CVs | Recommended | Immediate |
| W12 | P10 Macro-F1 degradation under-discussed | Moderate | Ennio Doorbell failure-mode is the honest negative | Recommended | Immediate |
| W13 | B4 cluster-feature ablation absent | Moderate | Interpretability | Recommended | Immediate |
| W14 | q=0.95 sensitivity check is brief | Minor | Easy reviewer ask | Recommended | Immediate |
| W15 | Conference-extension overlap not disclosed | Critical (ethical) | Desk-rejection risk without explicit ≥40% disclosure | Mandatory | Immediate |
| W16 | No conformal / calibration-coverage analysis | Major | Closes W01 theoretically | Recommended | Moderate |
| W17 | No shrinkage threshold variant | Moderate | Smooths B1↔B2 interpolation; mitigates P10 F1 loss | Recommended | Immediate |

---

## 6. Reviewer Risk Mitigation

| Reviewer Attack | How It Is Addressed | Residual Risk | Safe Wording |
|---|---|---|---|
| "B2 equalizes FPR by construction" | Appendix A derivation (equality is exact only on calibration data); split-conformal B2-conf; calibration-size sweep | A persistent reviewer may still call it tautological | "On the calibration set, per-client q-percentile thresholding produces FPR ≈ 1−q by construction. On held-out test data, the empirical FPR variance is non-trivial and is what we measure." |
| "DATP is too narrow for a journal" | Edge-IIoTset + FedProx/Ditto stress tests + temporal MVE + six mechanism analyses + conformal variant + expanded related work | Editor may still see it as a narrow calibration paper | Framed as "a fairness-oriented threshold-calibration study under non-IID FL" |
| "Dataset coverage is limited" | Edge-IIoTset device-type partition + CICIoT2023 device-MAC repartition (conditional on Priority 0) | MAC repartition may be infeasible | "Two physically-partitioned IoT benchmarks (N-BaIoT, Edge-IIoTset); CICIoT2023 is included as a device-grouped evaluation where metadata permits, or as a near-homogeneous boundary otherwise." |
| "N-BaIoT has only 9 devices" | Edge-IIoTset gives K ∈ {6, 15}; CICIoT2023 device-MAC adds K ≈ 10 if feasible | Combined K remains modest | "Fleet-scale validation (K > 100) is reserved for future work." |
| "CICIoT2023 clients are pseudo-clients" | Device-MAC or device-group repartition (basis determined by Gate 0 B-b outcome in PRE_CODING_PLAN.md §5.4 — *ARCHIVE: CICIOT2023_BB_FEASIBILITY.md not created*); retain file-level as Regime B-a regardless | Repartition conditional | "Regime B-a is a near-homogeneous applicability boundary; Regime B-b is the heterogeneous evaluation where metadata permits, on a MAC-based or device-group basis depending on the feasibility outcome." |
| "Missing model-personalization baselines" | Ditto (or `FedRep-AE/FedPer-AE fallback` per the Ditto / FedRep-AE Fallback Lock in `docs/journal/PRE_CODING_PLAN.md`) with pre-specified absorption interpretation rule *(ARCHIVE: "explicitly named local-head variant" was a rejected placeholder)* | One method, not exhaustive | "We compare against one representative model-personalization stress test; exhaustive comparison is out of scope." |
| "Missing aggregation baselines" | FedProx as heterogeneity-aware aggregation stress test | One method | "We add the most-cited heterogeneity-aware aggregation stress test (FedProx); further aggregation sensitivity is future work." |
| "Missing federated thresholding SOTA comparison" | Two clearly separated variants — `B-LaridiFaithful` (relaxed, uses anomaly-labeled summaries; only when attack-labeled calibration is permitted) and `B-FedStatsBenign` (DATP-compatible benign-only). See B-FedStatsBenign Protocol Lock and B-LaridiFaithful Scope Decision in `docs/journal/PRE_CODING_PLAN.md` *(ARCHIVE: previously labeled §8.4)* | Adaptation framing; benign-only result alone does not resolve the novelty risk under attack-labeled calibration | "We implement a DATP-compatible benign-only `B-FedStatsBenign` comparator; the relaxed `B-LaridiFaithful` variant is reported only when attack-labeled calibration access is permitted." |
| "Missing temporal drift" | Chronological split on Edge-IIoTset + one-shot recalibration with three pre-specified outcomes | Single split, not streaming | Outcome-specific wording (§10.1) |
| "Missing privacy/leakage discussion" | Bounded-disclosure table + qualitative MIA-risk analysis | No empirical leakage quantification | "B4 fingerprints constitute distributional metadata; we provide a bounded-disclosure analysis and discuss SecAgg/DP as future work." |
| "Missing deployment-cost discussion" | Bytes-per-round table for B1/B2/B4 communication and storage, estimated from message sizes | No hardware measurement | "Per-round communication and per-client storage overhead are estimated from message sizes; hardware-level profiling is future work." |
| "Journal version insufficiently different from conference" | ≥40% substantive new material with explicit cover-letter enumeration | Editor judgment | Cover letter lists each new section by number |
| "Scope drift from adding too much" | Hard limits: 1 new dataset, 1 conditional repartition, 3 stress-test comparators, 4 threshold variants, 1 temporal family, 6 mechanism analyses | Some reviewers always want more | "We hold the encoder, AE architecture, and mainline FedAvg training fixed; all extensions are threshold-scope or evaluation-side." |

---

## 7. Dataset Expansion

The dataset decision is built around two hard constraints: do not add more than one new dataset, and do not weaken the threshold-scope-only design by introducing modalities (network + host telemetry, traffic + system logs) that would compete with calibration scope as the primary variable.

| Dataset | Decision | Rationale |
|---|---|---|
| N-BaIoT | Keep (existing) | Real 9-device physical partition; Rey 2022 lineage |
| CICIoT2023 | Redesign by device-MAC **or device-group**, conditional on Priority 0 (PRE_CODING_PLAN.md §5.4 — *ARCHIVE: CICIOT2023_BB_FEASIBILITY.md not created*) | File-level partition is itself a weakness; Regime B-a retained regardless. No appeal to any unverified external precedent is used. |
| **Edge-IIoTset (Ferrag 2022)** | **Add — primary new dataset (Regime D)** | Native FL framing; 10+ device types; multi-day capture window enables a chronological split. Partition (device-client vs group-client) determined by first-principles Priority-0 feasibility audit (PRE_CODING_PLAN.md §5.5 — *ARCHIVE: EDGE_IIOTSET_FEASIBILITY.md not created*), not by external precedent. |
| ToN-IoT | Reject | Multi-modal nature complicates the threshold-scope-only design; doubles preprocessing |
| Bot-IoT, IoT-23, MedBIoT, FedAIoT bundle | Reject | Scope drift; insufficient DATP fit |
| UNSW-NB15 | Reject | Not IoT-specific |

**CICIoT2023 benign-volume threshold.** Regime B-b is used as a main-paper regime only if at least 8 clients each have nₖ ≥ 100 benign calibration samples (matching DATP's existing n_min). Otherwise, only Regime B-a is retained.

The final dataset addition is Edge-IIoTset with native device or application-type partitioning. The CICIoT2023 device-MAC repartition is the same dataset evaluated under a new regime and does not count against the one-new-dataset limit.

---

## 8. Baseline Expansion

### 8.1 Stress-Test Comparators vs Core Causal Ladder

The journal paper preserves a sharp distinction between two kinds of comparison:

- **Core DATP causal ladder (B1–B4).** Threshold scope is the only changing variable. AE encoder, training protocol, aggregator, and score artifacts are identical across B1, B2, B3, and B4. Results from this ladder support the confirmatory claim.
- **External stress-test comparators (FedProx, Ditto, Laridi-style).** These change the training protocol or threshold-generation mechanism to examine whether the B1→B2 gain survives under different conditions. They are reported as robustness checks, not as part of the core causal isolation. No stress-test result is presented as if it shared the experimental control of the B1–B4 ladder.

### 8.2 Selected Comparators

| Family | Decision | Question Addressed | Placement |
|---|---|---|---|
| **FedProx** | Add (stress test) | Does the B1→B2 CV(FPR) gain survive heterogeneity-aware aggregation? | Main stress-test table |
| FedBN | Reject | Would require BatchNorm in the encoder; breaks frozen-encoder discipline | — |
| FedAvgM, FedYogi | Defer | Diminishing return for this cycle | Future work |
| **Ditto (or `FedRep-AE/FedPer-AE fallback`)** *(ARCHIVE: the obsolete "named local-head variant" placeholder is rejected; see Ditto / FedRep-AE Fallback Lock in `docs/journal/PRE_CODING_PLAN.md`)* | Add (stress test) | Does the B1→B2 gain survive model-side personalization? | Main stress-test table |
| FedPer, APFL, Per-FedAvg | Reject | Exhaustive personalized-FL benchmarking is out of scope | — |
| Clustered FL (Sáez-de-Cámara 2023) | Qualitative only | Full reimplementation is heavy; cite and contrast | Related work |
| **`B-FedStatsBenign`** (DATP-compatible benign-only Laridi-style comparator) | Add (threshold comparator) | Does device-aware per-client thresholding provide stronger FPR equity than a benign-summary federated threshold under heterogeneity? | Main comparator table |
| **`B-LaridiFaithful`** (relaxed reproduction with anomaly-labeled summaries) | Add only when attack-labeled cal data is permitted | Does DATP outperform the original Laridi method when attack-labeled calibration is available? | Supplementary or main if implementable; otherwise documented as out of DATP assumption |
| Local-only bounding case | Optional | Supplementary | Supplementary |
| Centralized B0 | Keep | Existing | Main |

The final stress-test set comprises three comparator families: FedProx (aggregation-side), Ditto or an explicitly named **`FedRep-AE/FedPer-AE fallback`** variant (model-side, never called Ditto unless implemented faithfully), and a matched-operating-point benign-only **`B-FedStatsBenign`** comparator (with the relaxed **`B-LaridiFaithful`** variant reported only when attack-labeled calibration is permitted). *(ARCHIVE NOTE: `LocalHead-PersonalizedAE` was a rejected placeholder; canonical label is `FedRep-AE/FedPer-AE fallback`.)*

**Nomenclature Table (Locked).**

| Identifier | Meaning |
|---|---|
| B0 | Centralized AE reference (not part of the FL ladder) |
| B1 | Client-averaged shared τ |
| B2 | Per-client p95 threshold |
| B3 | Family-mean threshold (Regime A only) |
| B4 | Fingerprint cluster-mean threshold |
| τ-shrink (aka LGS) | Local-global shrinkage variant τₖ(λ) = λ·τₖ,p95 + (1−λ)·τ_global |
| B2-conf | Split / federated conformal variant of B2 (anchor: Lu et al. ICML 2023) |
| `B-FedStatsBenign` | DATP-compatible benign-only Laridi-style comparator |
| `B-LaridiFaithful` | Relaxed reproduction with anomaly-labeled summaries (optional) |
| FedProx | Heterogeneity-aware aggregation stress-test encoder |
| Ditto | Personalized FL with proximal regularization toward the global model (Li et al. ICML 2021) |
| `FedRep-AE/FedPer-AE fallback` | Frozen shared encoder + per-client local head (FedRep or FedPer style, adapted to DATP AE; not called "Ditto") *(ARCHIVE: `LocalHead-PersonalizedAE` was a rejected placeholder name)* |

`B-FedStatsBenign` and `B-LaridiFaithful` replace the prior label `B5`
to avoid collision with any existing baseline numbering and to make the
two calibration-assumption variants unambiguous. `τ-shrink` / LGS
replace the prior label `B3-LGS` (B3 is family-mean and must not be
reused). The local-head model-personalization variant is **never**
called "Ditto" in any output, table, figure, or prose.

### 8.3 Ditto: Implementation and Interpretation

The Ditto implementation choice must be documented in writing before any training begins. Selecting after results are seen is not permitted.

**Preferred: standard Ditto-style personalization.** Each client maintains a personalized local AE with the same architecture as the FedAvg AE. The personalized model trains with a proximal regularization term toward the current global model: `loss_local = loss_recon + (µ/2) · ||w_local − w_global||²`. Thresholds B1–B4 are evaluated over the personalized model's benign reconstruction-error scores. Reported as "Ditto-style model-side personalization stress test" with µ ∈ {0.001, 0.01, 0.1}.

**Fallback: local-head personalization comparator.** Freeze the FedAvg-trained shared encoder; train a lightweight local reconstruction head per client. Apply B1–B4 over local-head score artifacts. This variant is *not* called Ditto; it is labeled "local-head personalization comparator" and the paper states explicitly that it is a simplified stress test with a frozen shared encoder and a local reconstruction head, not a full Ditto reproduction.

**Absorption interpretation (pre-specified).** Let `Δ_FedAvg = CV(FPR)[FedAvg+B1] − CV(FPR)[FedAvg+B2]` and `Δ_Ditto = CV(FPR)[Ditto+B1] − CV(FPR)[Ditto+B2]`.

- If `Δ_Ditto ≥ 0.75 · Δ_FedAvg`: threshold personalization remains strongly useful under model personalization. Reported as corroborating evidence.
- If `0.25 · Δ_FedAvg ≤ Δ_Ditto < 0.75 · Δ_FedAvg`: model personalization partially absorbs the threshold-scope effect. Reported as a partial-absorption boundary condition.
- If `Δ_Ditto < 0.25 · Δ_FedAvg`: model personalization largely absorbs the effect. The DATP claim is narrowed to FedAvg-style and shared-encoder settings, and this is reported explicitly rather than hidden.
- If `CV(FPR)[Ditto+B1]` is already within 0.05 of `CV(FPR)[FedAvg+B2]`: model personalization may be an alternative path to FPR equity. This is reported as an informative positive finding about Ditto, not a failure of DATP.

This rule is documented before training and applied without adjustment after results are seen.

### 8.4 `B-FedStatsBenign` Comparator Protocol (and `B-LaridiFaithful` Disclosure)

**Context** *(ARCHIVE NOTE: verified — `LIVE_VERIFICATION_REGISTER.md` V-01 not created; fact in PRE_CODING_PLAN.md §5.8)*. The original Laridi et al. 2024 method aggregates summary statistics from **both normal and anomalous validation data**. Any benign-only adaptation **cannot** be called "faithful." DATP therefore separates two clearly named variants:

- **`B-LaridiFaithful`** — relaxed reproduction using normal + anomalous summary statistics. Implemented only when DATP's benign-only calibration assumption is explicitly relaxed for this comparator. If not implemented, the docs state so explicitly and DATP is framed as benign-only local threshold personalization, not as globally superior thresholding.
- **`B-FedStatsBenign`** — DATP-compatible benign-only comparator. Diverges from the original Laridi method by removing anomaly-labeled validation access. If `B-FedStatsBenign` underperforms B2, the result applies **only under benign-only calibration**.

If `B-LaridiFaithful` outperforms DATP, the paper states explicitly: "DATP is framed as benign-only local threshold personalization, not as globally superior thresholding." If `B-FedStatsBenign` underperforms B2, the paper states: "The result applies only under benign-only calibration and does not establish a single dominant federated thresholding policy."

The protocol below is locked for **`B-FedStatsBenign`** before any computation begins. No element is tuned after seeing results. `B-LaridiFaithful` follows the same skeleton but additionally exchanges anomaly-labeled summaries; its full protocol is locked only if and when implementation is approved.

| Element | Specification |
|---|---|
| Client message | Local benign-only summary statistics: count nₖ, mean µₖ, variance σₖ². No raw scores, no attack labels. |
| Mean aggregation | Sample-count-weighted: `µ_global = Σ nₖ·µₖ / Σ nₖ`. |
| Variance aggregation | **Full pooled variance** including the between-client mean-shift term: `σ²_global = Σ nₖ · [σₖ² + (µₖ − µ_global)²] / Σ nₖ`. |
| Variance diagnostic (main paper) | Report `within_term = Σ nₖ·σₖ² / Σ nₖ`, `between_term = Σ nₖ·(µₖ − µ_global)² / Σ nₖ`, and `between_ratio = between_term / (within_term + between_term)`. If `between_ratio > 0.5`, the paper states: "The between-client mean shift dominates the global variance, indicating that a single global summary-statistics threshold is structurally strained under this level of heterogeneity." |
| Matched-exceedance count exchange | Server broadcasts a fixed candidate grid `τ(k) = µ_global + k · σ_global`, with `k ∈ {0.00, 0.01, …, 5.00}`. Each client returns its benign exceedance count `cₖ(k) = #{e ∈ Eₖ,benign_cal : e > τ(k)}` and its benign calibration count nₖ. No raw scores or attack labels are exchanged. The grid is fixed before any result inspection. |
| Primary global threshold | Server computes `exceedance(k) = Σ cₖ(k) / Σ nₖ`, then selects `k* = argmin_k |exceedance(k) − 0.05|`. On ties, the larger k is chosen to avoid a post-hoc permissive selection. The matched Laridi-style threshold is `τ_Laridi = µ_global + k* · σ_global`. The paper reports k*, the achieved exceedance, and its absolute deviation from 5%. |
| Operating-point framing | "To avoid comparing B2 and the Laridi-style threshold at different operating points, the main comparison matches the benign calibration exceedance target of q = 0.95. Fixed-k variants (k ∈ {2.0, 2.5, 3.0}) are reported only as supplementary sensitivity checks." |
| Fixed-k variants | Computed and reported as supplementary sensitivity only; not the main Laridi comparator. |
| When applied | Once per seed, per dataset and regime, using the same benign calibration split as B1 and B2. |
| Overlap-region search | If the original Laridi method depends on attack-labeled calibration data for an overlap-region search, the adaptation uses only benign calibration data and documents this divergence. |
| Disclosure wording | ARCHIVE — superseded by the locked disclosure wording in `docs/journal/PRE_CODING_PLAN.md` (B-LaridiFaithful Scope Decision). The phrase "faithful DATP-compatible adaptation" used here is obsolete and must not be used in any operational document or manuscript; B-FedStatsBenign is the benign-only comparator and B-LaridiFaithful is out of scope under the canonical Scope Decision. |

---

## 9. Threshold Variants

The threshold-variant additions extend the calibration story without leaving the threshold-scope-only design.

| Variant | Definition | Decision | Role |
|---|---|---|---|
| **q-sensitivity sweep** | B1/B2/B4 at q ∈ {0.90, 0.95, 0.975, 0.99} | Add | Shows the headline is not a q = 0.95 artefact |
| Global pooled p95 | Single global p95 over pooled benign scores | Existing | Sensitivity check |
| Sample-weighted shared | Weighted mean of local p95 | Existing | Sensitivity check |
| Per-client B2 | Local p95 | Existing | DATP core |
| Family-mean B3 | Per-family arithmetic mean | Existing | DATP core (Regime A only) |
| Cluster-mean B4 | k-means cluster-mean | Existing | DATP core |
| Robust cluster median | Cluster-wise median of τₖ | Supplementary | Outlier robustness |
| **Local-global shrinkage** | τₖ(λ) = λ·τₖ,p95 + (1−λ)·τ_global, λ ∈ {0, 0.25, 0.5, 0.75, 1} | Add | Interpolates B1↔B2; mitigates P10 Macro-F1 loss |
| **Calibration-size-aware fallback** | Size-dependent λ(nₖ); smooth transition as nₖ drops | Add | Replaces the hard n_min = 100 fallback |
| **Split-conformal B2 (B2-conf)** | Per-client split-conformal calibration with marginal coverage 1 − α. **Primary anchor: Lu et al. ICML 2023 "Federated Conformal Predictors for Distributed Uncertainty Quantification" (V-07); co-anchor: Humbert et al. ICML 2023 "One-Shot Federated Conformal Prediction".** Plassier et al. is demoted to label-shift-related secondary background only. α = 0.05 is chosen deliberately to match the q = 0.95 operating point used by B2; if q changes, α changes accordingly as α = 1 − q. The variant addresses finite-sample calibration/coverage framing; it does **not** prove DATP is non-tautological in all settings. | Add | Closes W01 with a finite-sample coverage guarantee at the same operating point as B2 |
| Empirical-Bayes / James-Stein | Bayesian shrinkage | Reject | Heavier apparatus; scope drift |
| Drift-aware periodic recalibration | Folded into §10 | — | Temporal section |
| Full conformal anomaly detection (Byzantine-robust) | — | Reject | Scope drift |

The four added variants are: q-sensitivity sweep, local-global shrinkage τₖ(λ), calibration-size-aware fallback, and split-conformal B2.

---

## 10. Temporal Recalibration

N-BaIoT has chronological traces but limited drift magnitude. Edge-IIoTset has a multi-day capture window and is the preferred temporal substrate. CICIoT2023 Regime B-a discards within-file time and is unusable for temporal analysis; Regime B-b preserves capture timestamps if Priority 0 confirms metadata.

**Minimum viable temporal experiment.** Chronological 70/30 split on Edge-IIoTset. AE training and threshold calibration (B1/B2/B4) use the first 70% of each client's benign data by capture timestamp. Evaluation on the last 30% reports two settings: frozen thresholds, and one-shot recalibration at the temporal boundary. The temporal regime begins only once Edge-IIoTset preprocessing is stable (Gate 2 exit criteria satisfied).

**Rejected as scope drift:** streaming sliding-window recalibration; cross-dataset transfer; Page-Hinkley drift detection; FLARE/FLAME-style drift mitigation; Byzantine-robust federated conformal prediction.

**Metrics.** Per-time-window CV(FPR); mean FPR drift; per-client FPR slope vs. time; Macro-F1 stability; one-shot recalibration recovery ratio (recovered CV(FPR) gain / original gain).

### 10.1 Pre-Specified Outcome Interpretations

All three outcomes are valid findings; interpretation is not adjusted after results are seen.

**Outcome A — drift exists and one-shot recalibration helps** (recovery ratio ≥ 50% of the original CV(FPR) gain). Report recovery percentage. Claim: "Under the available temporal window, one-shot threshold recalibration recovers a meaningful portion of the CV(FPR) gain; periodic recalibration is a viable operational policy for device-aware thresholds."

**Outcome B — drift exists and one-shot recalibration does not help** (drift detectable, recovery ratio < 50%). Report as a limitation. Claim: "Device-aware thresholds exhibit temporal fragility in this benchmark; one-shot recalibration is insufficient; a continuous drift-mitigation mechanism would be required, which is future work." No streaming drift detector is added retroactively to rescue the result.

**Outcome C — no meaningful drift observed** (FPR drift within the bootstrap CI of the static split). Report as a stability finding. Claim: "Under the available chronological window of Edge-IIoTset, device-aware thresholds appear stable; this does not establish general temporal robustness, but it reduces concern that the observed DATP effect is purely a static-split artefact."

The temporal addition is a single family: Edge-IIoTset chronological split + one-shot threshold recalibration, with the three pre-specified outcome interpretations above.

---

## 11. Mechanism Analyses

| Analysis | Decision | What It Shows | Artifact |
|---|---|---|---|
| **Per-client benign + attack score CDFs with B1/B2/B4 overlays + Ennio Doorbell failure-mode deep dive** | Add | Mechanism of FPR concentration; why P10 Macro-F1 drops in low-separability devices | Figure |
| **JS divergence ↔ DATP-benefit correlation** | Add | Heterogeneity severity predicts DATP value (not causality) | Scatter + table |
| **Threshold shift vs ΔFPR/ΔTPR scatter** | Add | Quantifies the fairness-vs-sensitivity trade-off surface | Scatter |
| **Calibration-size sensitivity sweep** (nₖ ∈ {50, 100, 250, 500, 1k, 5k}) | Add | When DATP remains usable under low calibration data | Figure |
| **Operational false-alarm burden** (with declared traffic-volume source) | Add | Translates CV(FPR) into alerts/device/day under a declared assumption | Table |
| **B4 cluster-feature ablation + interpretability** | Add | Defends B4 as a meaningful taxonomy-free approximation | Table + cluster-to-device-type contingency table or small heatmap (Sankey is not appropriate at K = 3 / K = 9 scale) |
| Bootstrap CIs and effect sizes for all key metrics | Optional | Statistical rigor | Supplementary |
| Worst-client BA deep dive | Optional | Worst-case behavior | Table |
| Seed-level stability (Cliff's δ, Wilcoxon) | Optional | Supplementary statistical evidence | Supplementary |
| Sáez-de-Cámara vs B4 | Qualitative only | Differentiates clustering basis | Related work |
| Conformal coverage check | Integrated with B2-conf | Verifies guarantee | Figure |
| MIA-style empirical leakage probe | Reject | Lacks established IoT-threshold literature | — |

### 11.1 Alert-Burden Traffic-Volume Specification

The operational alert-burden table declares its traffic-volume assumption using one of:

- **Preferred:** derive volume from each dataset's own benign test-set record count per client per unit time, using capture timestamps where available.
- **Acceptable:** cite a published IoT traffic-profile study for typical rates per device type.
- **Fallback:** ARCHIVE — the obsolete "normalized hypothetical" fallback is rejected. Use only the Preferred or Acceptable options above; if neither is available, the alert-burden metric is omitted per `docs/journal/POST_EXPERIMENT_PLAN.md` Section 1 (Alert burden row) and Section 3 (Forbidden Post-Result Moves). The phrases "normalized hypothetical" and "hypothetical alert" are stale and must not appear in any operational document.

If no real-rate or cited-operational-rate source is available, the alert-burden metric is omitted entirely per the canonical rule in `docs/journal/POST_EXPERIMENT_PLAN.md`. Invented or assumed flow rates are forbidden.

The six mechanism analyses are: per-client CDF overlays with Ennio Doorbell deep dive; JS↔DATP-benefit correlation; threshold-shift vs ΔFPR/ΔTPR scatter; calibration-size sensitivity sweep; operational alert burden; and B4 cluster-feature ablation with contingency-table interpretability.

---

## 12. Target Journal Matrix

| Rank | Journal | Scope Match | Policy Evidence | Extension Risk | Desk-Rejection Risk |
|---|---|---|---|---|---|
| 1 | **Computer Networks** (Elsevier, ISSN 1389-1286, 2024 JIF 4.6, Q1) | Strongest — Rey et al. 2022 (CN 204:108693) is the foundational FL-IoT-malware paper on N-BaIoT; identical dataset lineage | Verbatim: "Enhanced, extended versions of quality papers presented at conferences or workshops can be submitted to our journal for review" | Low if extension is substantial and conference is cited | Low–Medium |
| 2 | **Internet of Things (Elsevier)** (ISSN 2542-6605, 2024 JIF ≈ 7.6, Q1) | Strong — IoT security and ML applications | Standard Elsevier originality language | Medium — editor may want stronger systems framing | Medium |
| 3 | Cyber Security and Applications (Elsevier OA) | Good — cybersecurity + AI + IoT scope; Olanrewaju-George 2025 (DATP ref [7]) published here | To verify at submission time | Medium | Medium |
| 4 | JNCA (Elsevier, 2024 JIF ≈ 8.0, Q1) | Strong — networked applications + security | Standard Elsevier originality language | Low–Medium | Medium |
| 5 | FGCS (Elsevier, 2024 JIF ≈ 6.1, Q1) | Moderate — distributed systems; security allowed but not central | Verbatim 40% new contributions; different title; cite original | Medium–High | Medium–High |
| Excluded | **Computers & Security** | Topically appealing | Verbatim moratorium since early 2024 on submissions whose primary subject is the security of AI/ML systems, including federated learning | Very high | Very high |

---

## 13. Conference-to-Journal Originality Plan

The conference paper contributes: the controlled threshold-scope study (B1–B4) under fixed FedAvg AE on N-BaIoT (confirmatory), CICIoT2023 file-level (applicability boundary), and the N-BaIoT Dirichlet sweep; the CV(FPR) reduction from 1.017 to 0.299; B4 ≈ 52% recovery; bootstrap CIs on per-seed deltas.

The journal paper adds, in total: an Edge-IIoTset device-partition regime; the CICIoT2023 device-MAC repartition (conditional on Priority 0); three stress-test comparator families crossed with the B1–B4 threshold grid; four new threshold variants; a chronological-split + one-shot recalibration regime; six mechanism analyses; Appendix A; and an expanded related work.

**Reused.** DATP nomenclature and B1–B4 taxonomy verbatim; the Regime A N-BaIoT confirmatory result (extended to 10 seeds); the Regime C Dirichlet sweep; the B0 centralized reference; theoretical definitions and notation; the reproducibility artifact structure.

**Rewritten or redrawn.** Every figure is either redrawn with additional series or replaced; every table is extended; sections with more than 50% reused prose are rewritten.

**Novelty threshold.** The cover letter targets at least 40% substantive new material **as a self-imposed conservative internal benchmark, aligned with explicit Elsevier-family extension guidance such as FGCS, not as a Computer Networks requirement.** Computer Networks' guide for authors states only that "Enhanced, extended versions of quality papers presented at conferences or workshops can be submitted to our journal for review" (verified — V-04); no fixed percentage is prescribed. The 40% benchmark is voluntarily exceeded. See `docs/journal/POST_EXPERIMENT_PLAN.md §8` for the exact section / table / figure split and the iThenticate protocol. *(ARCHIVE: `journal_extension_overlap_report.md` was never created.)*

**Cover letter disclosure template.**

> This manuscript is an extended version of our conference paper "[title]" (Reference [X]). The conference version established the DATP framework with the four-policy threshold-scope comparison on N-BaIoT and reported CV(FPR) reduction from 1.017 to 0.299 under per-client thresholding. The present journal manuscript contains at least 40% substantive new material, including: (i) a new device-partitioned Edge-IIoTset benchmark, and where Priority 0 confirms metadata, a device-MAC repartition of CICIoT2023; (ii) four new threshold variants — q-sensitivity sweep, local-global shrinkage, calibration-size-aware fallback, and split-conformal B2; (iii) three stress-test comparator families (FedProx, a Ditto-style or local-head model-personalization comparator, and a matched-operating-point Laridi-style federated summary-statistics threshold) evaluated under the identical threshold grid; (iv) a formal Appendix A delineating where B2's construction-implied FPR equality holds and breaks down; (v) a temporal chronological-split and one-shot recalibration regime with pre-specified outcome interpretations; and (vi) six mechanism analyses. No figures or text passages are reused verbatim. The manuscript is not under consideration elsewhere.

**Self-plagiarism and duplicate-publication controls.** Keep iThenticate verbatim overlap below approximately 15–20%; redraw or substantially extend every figure; rewrite the introduction, related work, and methodology sections; avoid simultaneous submission; wait for the conference camera-ready before journal submission; cite the conference paper as [X] in the introduction.

**Seed-extension honesty rule.** If the 10-seed extension widens the CI or brings it close to zero, the 10-seed result becomes the main result and the 5-seed conference result is explicitly labeled preliminary. If the 10-seed CI includes zero, the claim is revised accordingly. The 10-seed result is not suppressed when it is less favorable than the 5-seed result.

---

## 14. Expansion Levels

### 14.1 Minimal Extension

Keep N-BaIoT and (conditionally) redesign CICIoT2023 by device-MAC; FedProx stress test only; q-sensitivity and shrinkage; no temporal experiment; client-CDF overlays + failure-mode taxonomy + operational burden. This package leaves the dataset story fragile against a Q1 reviewer, omits both the model-personalization stress test and the federated-thresholding comparison, and ignores temporal drift. Net risk: high desk-reject risk at Computer Networks.

### 14.2 Strong Extension (Selected)

N-BaIoT + Edge-IIoTset + CICIoT2023 device-MAC (conditional on Priority 0); the full three-family stress-test grid (FedProx + Ditto/named variant + matched-operating-point Laridi-style) crossed with B1–B4; four new threshold variants; the chronological + one-shot recalibration MVE with three pre-specified outcomes; all six mechanism analyses; Appendix A; 10-seed extension reported honestly; qualitative privacy bounded-disclosure analysis. Net risk: low–medium at Computer Networks.

### 14.3 Ambitious Extension (Not Pursued)

Adds multiple datasets, a broad personalized-FL benchmark, streaming drift detection, hardware profiling, and adversarial robustness. DATP identity dissolves; the paper becomes a generic FL-IDS study. Not pursued this cycle.

---

## 15. Execution Priorities

### 15.1 Core (Must Be in the Journal Paper)

Priority 0 metadata feasibility check; Appendix A construction-equality note; locked Laridi protocol (matched exceedance, full pooled variance with between-client term); q-sensitivity sweep; calibration-size sweep; local-global shrinkage τₖ(λ); split-conformal B2-conf with coverage check; Laridi-style baseline with between-ratio diagnostic; B4 cluster-feature ablation with contingency table; JS↔DATP-benefit regression; per-client error CDF overlays with Ennio Doorbell deep dive; operational alert-burden table with declared traffic-volume source; threshold-shift vs ΔFPR/ΔTPR scatter; 10-seed extension reported honestly; Ditto implementation choice and absorption rule documented before training; Edge-IIoTset preprocessing, device partitioning, and FedAvg AE training; CICIoT2023 device-MAC repartition where Priority 0 confirms it; FedProx and Ditto/named-variant stress-test training; temporal MVE on Edge-IIoTset; privacy bounded-disclosure analysis; expanded related work.

### 15.2 Supplementary (Time Permitting)

Full communication/storage cost table; bootstrap CIs for all metrics beyond the primary CV(FPR) BCa CI; complete per-seed per-client raw result tables; full-metric Wilcoxon and Cliff's δ; Sáez-de-Cámara quantitative reimplementation; full personalized-FL benchmark across APFL, FedPer, Per-FedAvg; temporal experiment on CICIoT2023 device-MAC (only after the Edge-IIoTset MVE is stable); robust cluster-median variant; fixed-k Laridi variants (k ∈ {2.0, 2.5, 3.0}) as sensitivity checks.

### 15.3 Excluded

See §21 (Scope Boundaries).

---

## 16. Priority 0 — CICIoT2023 Metadata Feasibility

Priority 0 precedes all Gate 1 work and all CICIoT2023-related drafting.

| Step | Action | Output |
|---|---|---|
| P0.1 | Inspect current CICIoT2023 processed feature files for MAC address, source/destination MAC, device identifier, device-group label, or any recoverable device metadata | Field-by-field findings recorded under CICIoT2023 B-b Feasibility in `docs/journal/PRE_CODING_PLAN.md` *(ARCHIVE: `ciciot2023_metadata_feasibility.md` was never created and is non-operational)* |
| P0.2 | If processed metadata is absent, inspect upstream raw or source data (PCAP, CSV, logs) for recoverable device-group or MAC-level labels | Appended to the same report |
| P0.3 | Estimate benign sample counts per candidate device-group client | Benign-per-client table |
| P0.4 | Declare one of three outcomes | Final outcome in the same report |

**Outcomes.**

- **CONFIRMED — Regime B-b feasible from current artifacts.** Device-group or MAC metadata is present in processed files; at least 8 clients each have nₖ ≥ 100 benign calibration samples from stored data.
- **REPROCESS REQUIRED — Regime B-b feasible only from raw or source data.** Metadata is absent in processed files but recoverable from raw upstream data; reprocessing is feasible within the project timeline.
- **REJECTED — Regime B-b not feasible.** Metadata is unavailable or fewer than 8 clients satisfy nₖ ≥ 100. Regime B-b is removed from all sections.

**Downstream dependencies.** Gate 2 Regime B-b tasks are gated on this outcome. If REJECTED, all G2.0–G2.1 Regime B-b actions are removed, Regime B-b references in §7, §15, §17, and §20 are inactive, and the paper proceeds with Regime B-a as the CICIoT2023 entry. Regime B-b sections (results, method subsection, analysis) are not drafted until the outcome is CONFIRMED or REPROCESS REQUIRED and at least G2.1 is complete.

---

## 17. Three-Gate Execution Plan

### Gate 1 — Existing-Score Extensions

Gate 1 operates on stored per-client score artifacts and fingerprints. No retraining is required, which makes this the lowest-risk stage and the right place to close the most critical reviewer attacks before any new dataset or training infrastructure is touched.

| # | Action | Go/No-Go Criterion | Fallback |
|---|---|---|---|
| G1.1 | Write Appendix A: formal explanation of calibration-set vs held-out-test FPR behavior; bound construction equality by nₖ and distribution stability | Reviewed by 1 statistician; claims are bounded | Simplify to a formal note without full derivation |
| G1.2 | Lock and document the Laridi-style protocol (full pooled variance, within/between diagnostic terms, matched-exceedance operating point) before any computation | Protocol finalized and documented before any result is inspected | — |
| G1.3 | q-sensitivity heatmap at q ∈ {0.90, 0.95, 0.975, 0.99} on stored N-BaIoT scores | Ordering B2 < B4 < B1 across q, or any inversion reported honestly | Report inversion; does not invalidate DATP |
| G1.4 | Calibration-size sweep (nₖ ∈ {50, 100, 250, 500, 1k, 5k}) by subsampling stored N-BaIoT scores | Curve reaches plateau; shrinkage maps cleanly | Reduce granularity if compute is limited |
| G1.5 | Local-global shrinkage τₖ(λ) at λ ∈ {0, 0.25, 0.5, 0.75, 1} | λ-curve reported; P10 Macro-F1 per λ reported | Report any non-monotone behavior honestly |
| G1.6 | Split-conformal B2-conf with marginal coverage check at α = 0.05 | Empirical coverage within ±0.02 of 1 − α | Report coverage failure as a conformal-adaptation limitation |
| G1.7 | Run the pre-specified Laridi-style baseline on stored N-BaIoT scores (full pooled variance, fixed candidate grid, benign exceedance counts only, matched-exceedance k*); report between_ratio in main text | Protocol pre-specified; candidate grid fixed before result inspection; no raw scores or attack labels shared; between_ratio reported | Benign-only fallback if the overlap-region search would require attack labels |
| G1.8 | B4 cluster-feature ablation (4 subsets + all-four) on stored fingerprints | Each subset's CV(FPR) reported; cluster assignments mapped to device labels | If unstable across seeds, report the instability |
| G1.9 | JS divergence ↔ DATP-benefit regression on stored per-client benign distributions | R² and ρ reported with caveats | Weak R² is a real result |
| G1.10 | Operational alert-burden table (FPR × declared traffic volume) | Traffic-volume source documented and justified | ARCHIVE — the obsolete "normalized hypothetical, labeled as such" fallback is rejected. Canonical rule: omit the metric entirely if no real timestamped rate or cited operational rate is available, per `docs/journal/POST_EXPERIMENT_PLAN.md` Section 1 (Alert burden) and Section 3 (Forbidden Post-Result Moves). |
| G1.11 | Threshold shift vs ΔFPR/ΔTPR scatter | All 9 N-BaIoT devices reported; no filtering | — |
| G1.12 | Extend to 10 seeds where compute allows; recompute all BCa CIs | 10-seed result reported honestly; claim revised if CI widens or approaches zero | 5-seed result with explicit power limitation |
| G1.13 | Privacy bounded-disclosure table and qualitative MIA-risk discussion | No formal-privacy claim; all wording bounded | — |
| G1.14 | Expanded related work | Covers Laridi 2024, Sáez-de-Cámara 2023, FedMSE 2025, Belarbi 2023, Plassier ICML 2023, Pradhan et al. 2025 | — |

**Gate 1 exit criteria.** Priority 0 is already complete; all G1.* analyses are reproducible from stored artifacts without retraining; Appendix A is drafted and reviewed; the Laridi protocol is locked and the between-client diagnostic is reported in main text; the matched-exceedance operating point is the primary Laridi comparator; the construction-tautology critique is addressed by Appendix A + B2-conf + the calibration-size sweep; all claims remain centered on threshold scope; and the 10-seed extension (or its explicit power limitation) is documented.

### Gate 2 — Dataset Expansion

| # | Action | Go/No-Go Criterion | Fallback |
|---|---|---|---|
| G2.0 | Apply Priority 0 outcome to determine Regime B-b feasibility | Outcome documented and applied | If REJECTED, remove G2.1–G2.4 Regime B-b actions |
| G2.1 | If feasible, build CICIoT2023 device-MAC partition on first-principles feasibility audit grounds (see CICIoT2023 B-b Feasibility in `docs/journal/PRE_CODING_PLAN.md`); audit eligibility *(ARCHIVE: the obsolete "per Pradhan et al. (Sci. Rep. 2025)" precedent is rejected and non-operational; partitioning is decided on first-principles feasibility only)* | At least 8 clients each with nₖ ≥ 100 benign calibration samples | Fewer than 8 eligible clients: retain Regime B-a only |
| G2.2 | Download and preprocess Edge-IIoTset; validate feature schema; audit capture timestamps | Coverage ≥ 90% (nₖ ≥ 100 for ≥ 90% of clients); timestamps available | Reduce K or defer temporal MVE to supplementary |
| G2.3 | Train FedAvg AE on Edge-IIoTset (K ∈ {6, 15}); compute per-client score artifacts | Convergence per seed; calibration coverage logged | Reduce K |
| G2.4 | If Regime B-b is confirmed: train FedAvg AE on CICIoT2023 device-MAC partition; compute score artifacts | ≥ 8 clients each with nₖ ≥ 100; convergence per seed | Fall back to Regime B-a only |
| G2.5 | Run B1–B4 + matched-exceedance Laridi-style + q-sensitivity on Edge-IIoTset and (if confirmed) CICIoT2023 Regime B-b, using the same fixed-grid benign exceedance-count protocol from the B-FedStatsBenign Protocol Lock in `docs/journal/PRE_CODING_PLAN.md` *(ARCHIVE: §8.4 reference is stale)* | All deltas reported with BCa CIs; candidate grid fixed before result inspection; no raw scores or attack labels shared; between_ratio reported | Negative result reported and discussed |

**Gate 2 exit criteria.** Priority 0 outcome applied; Edge-IIoTset artifacts validated with documented client counts, benign calibration counts, attack counts, and eligibility coverage; Regime B-b feasibility either confirmed or explicitly rejected; Edge-IIoTset timestamp availability verified; all partitions documented before any training-side stress tests begin.

### Gate 3 — Training-Side Stress Tests

| # | Action | Go/No-Go Criterion | Fallback |
|---|---|---|---|
| G3.0 | Document Ditto implementation choice (standard Ditto vs FedRep-AE/FedPer-AE fallback per the Ditto / FedRep-AE Fallback Lock in `docs/journal/PRE_CODING_PLAN.md`) and the absorption interpretation rule from that same canonical lock *(ARCHIVE: §8.3 references and the rejected "local-head comparator" label are stale)* | Choice and rule finalized in writing before training | No post-hoc switching based on which performs better |
| G3.1 | Run FedProx (µ ∈ {0.0, 0.001, 0.01, 0.1, 1.0}; µ = 0.0 is the FedAvg sanity check) on N-BaIoT and Edge-IIoTset; apply B1–B4. **Local epoch count E locked equal to FedAvg E** (do not study E sensitivity unless explicitly added). | All seeds converge; labeled as stress-test comparator; µ-grid frozen before result inspection | If all pre-specified µ values fail to converge on Regime D, report convergence failure; no µ search beyond the locked grid. Any additional µ value introduced after seeing results is explicitly labeled exploratory and cannot support the main stress-test claim. |
| G3.2 | Run Ditto/named-variant on N-BaIoT and Edge-IIoTset; apply B1–B4; report absorption ratio Δ_Ditto / Δ_FedAvg; apply the pre-specified interpretation rule | Personalized model converges; absorption ratio computed; interpretation applied | All three absorption outcomes are valid findings |
| G3.3 | Temporal MVE: chronological 70/30 split on Edge-IIoTset; frozen vs one-shot recalibration; apply the pre-specified outcome interpretation (§10.1) | Pre-specified outcome applied without adjustment | If Edge-IIoTset timestamps are unsuitable, defer to supplementary and document the reason |
| G3.4 | Finalize Gate 3 runs; recompute BCa CIs to 10 seeds where not already done | 10-seed rule applied honestly regardless of direction | 5-seed with power limitation |

**Gate 3 exit criteria.** FedProx and Ditto/named-variant are labeled stress-test comparators throughout and are never presented as part of the core B1–B4 causal isolation; the Ditto absorption ratio is reported according to the pre-specified rule; the temporal MVE outcome interpretation is applied without adjustment; no result is hidden because it weakens the original story.

---

## 18. Final Recommended Package

The selected package is the Strong Extension (§14.2). The primary venue is Computer Networks; the backup is Internet of Things (Elsevier). Computers & Security is excluded.

- **Datasets (≤ 2).** Edge-IIoTset (device or application-type partition, K ∈ {6, 15}); CICIoT2023 device-MAC repartition (conditional on Priority 0; same dataset, new regime).
- **Stress-test comparators (≤ 3 families; all external, not core causal).** FedProx; Ditto or a `FedRep-AE/FedPer-AE fallback` with a pre-specified absorption rule (see Ditto / FedRep-AE Fallback Lock in `docs/journal/PRE_CODING_PLAN.md`); a matched-operating-point Laridi-style federated summary-statistics threshold. *(ARCHIVE: the obsolete "named local-head variant" placeholder is rejected and must not be used.)*
- **Threshold variants (≤ 4).** q-sensitivity sweep; local-global shrinkage τₖ(λ); calibration-size-aware fallback; split-conformal B2-conf.
- **Temporal addition (≤ 1).** Edge-IIoTset chronological 70/30 split; frozen vs one-shot recalibration; three pre-specified outcomes.
- **Mechanism analyses (≤ 6).** Per-client CDF overlays + Ennio Doorbell deep dive; JS↔DATP-benefit correlation; threshold-shift vs ΔFPR/ΔTPR scatter; calibration-size sensitivity sweep; operational false-alarm burden; B4 cluster-feature ablation with contingency table.
- **New figures.** Per-client benign-error CDF overlay; calibration-size sensitivity curve; shrinkage λ-curve; JS↔gain scatter; threshold-variant q-heatmap; temporal CV(FPR) drift trajectory; split-conformal coverage diagnostic; B4 feature-ablation heatmap.
- **New tables.** Stress-test comparator grid (FedAvg / FedProx / Ditto-or-named × B1–B4 + matched-Laridi threshold); Edge-IIoTset Regime A' results; CICIoT2023 Regime B-b results (conditional); failure-mode analysis; privacy disclosure; communication and storage overhead; B4 cluster-feature ablation; alert burden; Laridi between-ratio diagnostic.
- **New sections.** Threshold-Variant Taxonomy; Calibration-Size Analysis; Failure-Mode and Limits of DATP; Privacy and Leakage Analysis; Temporal Recalibration MVE; Comparison with Federated Thresholding SOTA and Model-Personalization Stress Test; Post-2022 Related Work.
- **Supplementary / Appendix.** Appendix A (construction-equality note + boundary conditions); fixed-k Laridi sensitivity; full hyperparameter tables; per-seed per-client raw results; Docker image + git commit hash; extended Zenodo artifact.
- **Claims to strengthen.** (a) Threshold scope alone changes the false-alarm distribution — supported by two datasets, the conformal variant, and calibration-size robustness. (b) The gain is not absorbed by heterogeneity-aware aggregation or model-side personalization — supported by pre-specified stress-test results. (c) The effect is monotone in heterogeneity — supported by the Dirichlet sweep and the JS-divergence regression.
- **Claims to avoid.** DATP "solves" non-IID; improved global Macro-F1; privacy preservation; concept-drift handling beyond one-shot recalibration; universal dominance over Laridi-style federated thresholding.

---

## 19. Artifact and Claim Consistency

| Claim | Support | Required Evidence | Safe Wording |
|---|---|---|---|
| B2 reduces CV(FPR) from 1.017 to 0.299 on N-BaIoT | Already supported | 10-seed extension reported honestly | "B2 reduces CV(FPR) from 1.017 to 0.299 (10-seed BCa CI: [a, b]) under the tested N-BaIoT protocol" |
| Effect is monotone in Dirichlet α | Already supported | Regime C | "Per-client threshold benefit is monotonically related to Dirichlet α and collapses under IID" |
| B4 recovers ≈ 52% of B2's improvement | Already supported | Existing | "B4 recovers ≈ 52% of B2's improvement at K=3 (exploratory at N=9)" |
| Effect generalizes to Edge-IIoTset | New | Gate 2–3 device-partition runs | "On Edge-IIoTset (device-partitioned, K=X), B2 reduces CV(FPR) from Y to Z (95% BCa CI: [a, b])" |
| Threshold-scope gain not absorbed by FedProx/Ditto | New | FedProx/Ditto × B1–B4 grid; absorption rule applied | Absorption-category wording per the Ditto / FedRep-AE Fallback Lock in `docs/journal/PRE_CODING_PLAN.md` *(ARCHIVE: §8.3 reference is stale)*; if Δ_Ditto < 0.25·Δ_FedAvg, the claim is narrowed to FedAvg-style settings |
| DATP vs Laridi-style federated threshold | New | Matched-operating-point Laridi-style baseline; between-ratio diagnostic | "Under heterogeneous device partitions, the matched-exceedance Laridi-style federated threshold reduces FPR dispersion vs B1 but achieves lower dispersion reduction than B2; between_ratio = [X] indicates [the relevant interpretation] under this heterogeneity level" |
| B2 is not a construction tautology | Appendix A + new experiments | Calibration-size sweep + B2-conf | "B2's CV(FPR) equalization is exact on calibration data; on held-out test data it is bounded by nₖ and distribution stability (Appendix A); the gain survives split-conformal calibration with marginal coverage 1 − α" |
| DATP can handle limited calibration data | Recomputation | n_cal sweep on stored scores | "For n_cal ≥ N*, B2 with shrinkage remains effective; below N*, the calibration-size-aware fallback recovers B1-equivalent FPR" |
| DATP threshold aging | New | Temporal MVE | Outcome-specific wording per §10.1 |
| DATP preserves privacy | Should not be claimed | — | "B4 fingerprints constitute distributional metadata; B4 is not a privacy mechanism" |
| B4 is privacy-safe | Should not be claimed | — | Not claimed |
| Threshold personalization helps in CICIoT2023 generally | Should not be claimed | — | "Regime B-a is an applicability boundary; Regime B-b is the heterogeneous evaluation where Priority 0 confirms metadata" |
| DATP reduces operational alert burden | Recomputation | FPR × declared traffic volume | "Translating per-client FPR into expected alerts/day under [declared traffic assumption], B2 reduces worst-client alert load from N₁ to N₂ alerts/day" |
| DATP improves global Macro-F1 | Should not be claimed | — | "DATP improves per-client FPR equity; P10 Macro-F1 degrades in low-separability clients (Ennio Doorbell on N-BaIoT)" |

---

## 20. Implementation-Ready Action Plan

| Priority | Action | Depends On | Feasibility |
|---|---|---|---|
| **P0** | Priority 0: inspect CICIoT2023 processed and raw data for MAC/device metadata; document outcome under CICIoT2023 B-b Feasibility in `docs/journal/PRE_CODING_PLAN.md` *(ARCHIVE: `ciciot2023_metadata_feasibility.md` was never created and is non-operational)* | Nothing | Immediate |
| G1.1 | Appendix A: construction-equality formal note, calibration vs held-out behavior, nₖ boundary conditions | — | Immediate |
| G1.2 | Confirm the B-FedStatsBenign protocol is locked in `docs/journal/PRE_CODING_PLAN.md` before any computation; B-LaridiFaithful remains out of scope under the B-LaridiFaithful Scope Decision. | G1.1 | Immediate |
| G1.3 | q-sensitivity heatmap on stored N-BaIoT scores | Stored scores | Immediate |
| G1.4 | Calibration-size sweep | Stored scores | Immediate |
| G1.5 | Local-global shrinkage τₖ(λ) | Stored scores | Immediate |
| G1.6 | Split-conformal B2-conf + coverage check | Stored scores | Moderate |
| G1.7 | Pre-specified Laridi-style baseline on N-BaIoT; report between_ratio in main text | G1.2; stored scores | Moderate |
| G1.8 | B4 cluster-feature ablation + contingency table | Stored fingerprints | Immediate |
| G1.9 | JS divergence ↔ DATP-benefit regression | Stored distributions | Immediate |
| G1.10 | Alert-burden table with declared traffic-volume source | Stored scores + declared source | Immediate |
| G1.11 | Threshold shift vs ΔFPR/ΔTPR scatter | Stored scores + thresholds | Immediate |
| G1.12 | Extend to 10 seeds where compute allows; recompute BCa CIs | Existing pipeline | Immediate |
| G1.13 | Privacy bounded-disclosure table + qualitative MIA-risk discussion | G1.1–G1.7 | Immediate |
| G1.14 | Expanded related work | G1.1–G1.13 | Immediate |
| G2.0 | Apply Priority 0 to determine Regime B-b tasks | Priority 0 | Immediate |
| G2.1 | If feasible: build CICIoT2023 device-MAC partition | G2.0 | Moderate |
| G2.2 | Preprocess Edge-IIoTset; validate schema; audit timestamps | Gate 1 complete | Moderate–Heavy |
| G2.3 | Train FedAvg AE on Edge-IIoTset; compute score artifacts | G2.2 | Moderate–Heavy |
| G2.4 | If confirmed: train FedAvg AE on CICIoT2023 device-MAC; compute scores | G2.0; G2.1 | Moderate–Heavy |
| G2.5 | Run B1–B4 + matched-exceedance Laridi + q-sensitivity on Edge-IIoTset and (if confirmed) Regime B-b | G2.2–G2.4 | Heavy |
| G3.0 | Document Ditto implementation choice and absorption rule | Gate 2 | Immediate |
| G3.1 | FedProx on N-BaIoT + Edge-IIoTset; apply B1–B4 | G2.2–G2.3 | Moderate |
| G3.2 | Ditto/named-variant on N-BaIoT + Edge-IIoTset; apply B1–B4; report absorption ratio | G3.0; G2.2–G2.3 | Heavy |
| G3.3 | Temporal MVE on Edge-IIoTset; apply pre-specified outcome interpretation | G2.2 timestamp confirmation | Moderate |
| G3.4 | Finalize Gate 3 runs; recompute BCa CIs to 10 seeds | G3.1–G3.3 | — |
| Draft | Rewrite Introduction + Related Work + Methodology to ≥ 40% new prose; draft cover letter | All above | Moderate |
| Submit | Submit to Computer Networks after the conference camera-ready is set | Conference decision | — |

---

## 21. Scope Boundaries

Each item carries a stable label `SB-NN`. Other planning docs must reference these labels rather than ad-hoc section numbers.

- **SB-01**. Do not submit to Computers & Security. The COSE moratorium excludes submissions that feature AI/ML as significant components, including applying AI/ML to security/privacy topics **and** the security of AI/ML systems themselves (such as federated learning) (V-06).
- **SB-02**. Do not add FedBN. The current AE has no BatchNorm layers; adding BN changes the encoder and breaks the frozen-encoder discipline.
- **SB-03**. Do not add more than one new IoT dataset (Edge-IIoTset). ToN-IoT, IoT-23, Bot-IoT, MedBIoT, UNSW-NB15, TII-SSRC-23, and the FedAIoT bundle are out of scope for this cycle.
- **SB-04**. Do not add more than three stress-test comparator families. Per-FedAvg, FedPer, APFL, pFedMe, FedAvgM, FedYogi, FedAdam, and a Sáez-de-Cámara clustered-FL reimplementation are excluded.
- **SB-05**. Do not claim DATP "solves" non-IID FL.
- **SB-06**. Do not claim improved global Macro-F1; P10 Macro-F1 degrades and is reported as a real negative.
- **SB-07**. Do not claim privacy preservation without formal DP or SecAgg.
- **SB-08**. Do not claim concept-drift handling; the temporal probe is one-shot recalibration only.
- **SB-09**. Do not add adversarial robustness, poisoning, backdoor, or evasion experiments.
- **SB-10**. Do not add hardware or edge profiling.
- **SB-11**. Do not add streaming drift-detection frameworks (FLARE/FLAME-style).
- **SB-12**. Do not add Byzantine-robust federated conformal prediction.
- **SB-13**. Do not change the mainline AE architecture, FedAvg aggregator, or round budget between conference and journal versions for a given dataset. (A dataset-specific AE is trained per dataset and seed with input_dim matched to the dataset feature count; the frozen-encoder constraint applies within each dataset/regime/baseline ladder, not across datasets — see PRE_CODING_PLAN.md §5.5 *(ARCHIVE: EDGE_IIOTSET_FEASIBILITY.md not created)*.)
- **SB-14**. Do not reuse conference figures verbatim; redraw or substantially extend each.
- **SB-15**. Do not silently change the CV(FPR) definition between conference and journal.
- **SB-16**. Do not frame the CICIoT2023 file-level null result as a general CICIoT2023 statement; it remains Regime B-a.
- **SB-17**. Do not invoke FedMSE (COSE 2025) as evidence that COSE accepts FL submissions today.
- **SB-18**. Do not target FGCS as a primary venue.
- **SB-19**. Do not use a Sankey diagram for B4 cluster interpretability at K = 3 / K = 9 scale; use a contingency table or small heatmap.
- **SB-20**. Do not present hypothetical alert/day numbers as deployment measurements. *(ARCHIVE: the obsolete "normalized hypothetical" fallback and "hypothetical alert" wording are rejected and non-operational.)* The canonical rule is in `docs/journal/POST_EXPERIMENT_PLAN.md` Section 1 (Alert burden) and Section 3 (Forbidden Post-Result Moves): derive from real timestamped rates or a cited operational rate, or omit the metric.
- **SB-21**. Do not suppress the 10-seed result when it is less favorable than the 5-seed result; the 10-seed result is the main one. Apply the discrepancy rule from `docs/journal/POST_EXPERIMENT_PLAN.md §2.1` if the reproduced 5-seed BCa CI differs materially from the published/reference CI or is > 20% wider. *(ARCHIVE: `claim_survival_matrix.md` was never created; wording is in POST_EXPERIMENT_PLAN.md §2.1.)*
- **SB-22**. Do not tune the `B-FedStatsBenign` / `B-LaridiFaithful` protocol after seeing results; it is finalized at G1.2 before any computation.
- **SB-23**. Do not claim Regime B-b if Priority 0 returns any `B_B_REJECTED_*` status. Do not collapse MAC-based and group-based partitions into the same label.
- **SB-24**. Do not call the Ditto fallback "Ditto" if it is only a frozen-body local-head variant; use the explicit label `FedRep-AE` or `FedPer-AE` fallback, clearly labeled as a recognized shared-representation/local-head personalization family. *(ARCHIVE: `LocalHead-PersonalizedAE` was a rejected placeholder name and must not be used.)*
- **SB-25**. Do not present FedProx, Ditto, or FedRep-AE/FedPer-AE fallback results as part of the core B1–B4 causal ladder; they are external stress-test comparators. *(ARCHIVE: `LocalHead-PersonalizedAE` is a rejected placeholder; canonical label is FedRep-AE/FedPer-AE fallback.)*
- **SB-26**. Do not use the simple pooled-variance formula `σ²_global = Σ nₖ·σₖ² / Σ nₖ` for the `B-FedStatsBenign` threshold; always use the full formula from the B-FedStatsBenign Protocol Lock in `docs/journal/PRE_CODING_PLAN.md` *(ARCHIVE: §8.4 reference is stale)*.
- **SB-27**. Do not use any fixed k as the primary `B-FedStatsBenign` comparator; the main comparison uses the matched-exceedance operating point. Fixed-k values are supplementary sensitivity only.
- **SB-28**. Do not appeal to "Pradhan et al. 2025" or any unverified precedent to justify a dataset partition; partitioning is decided on first-principles feasibility audits (PRE_CODING_PLAN.md §5.4 and §5.5 — *ARCHIVE: CICIOT2023_BB_FEASIBILITY.md and EDGE_IIOTSET_FEASIBILITY.md not created*).
- **SB-29**. Do not call a benign-only Laridi adaptation "faithful"; the term `B-LaridiFaithful` is reserved for the relaxed normal + anomalous variant only (V-01).
- **SB-30**. Do not claim fleet-scale validation (K > 100). Combined K across the tested benchmarks is modest and explicitly scoped as such.
- **SB-31**. Do not use Plassier et al. as the primary federated conformal anchor; primary anchor is Lu et al. ICML 2023 (V-07), co-anchor Humbert et al. ICML 2023.
- **SB-32**. Do not lock B4 K post-hoc. Canonical main-paper K is **K = 3**; K = 9 and other K values are exploratory / supplementary only.

---

## 22. Residual Risks

After the full package is in place, several limitations remain. All are acceptable, are scoped explicitly, and have safe wording.

1. **Modest K.** Evaluation comprises K ∈ [9, 15] physical-device clients across benchmarks. Fleet-scale validation at K > 100 is reserved for future work.
2. **One aggregation stress test.** FedProx is the only aggregation-side comparator. Further aggregation sensitivity is future work.
3. **One model-personalization stress test.** Ditto (or the `FedRep-AE/FedPer-AE fallback` per the Ditto / FedRep-AE Fallback Lock in `docs/journal/PRE_CODING_PLAN.md`) is the only model-side comparator. *(ARCHIVE: the obsolete "named local-head variant" placeholder is rejected.)* Exhaustive personalized-FL benchmarking is out of scope.
4. **Qualitative privacy analysis.** Formal DP or SecAgg integration is future work.
5. **Single chronological split.** The temporal regime is a one-shot recalibration MVE; streaming drift handling is future work.
6. **Laridi adaptation.** ARCHIVE — the obsolete "faithful DATP-compatible adaptation" phrasing is rejected and non-operational. The canonical position is in the B-LaridiFaithful Scope Decision in `docs/journal/PRE_CODING_PLAN.md`: B-FedStatsBenign is a DATP-compatible benign-only adaptation (not "faithful"); B-LaridiFaithful is out of scope. The full pooled-variance formula and the matched-operating-point protocol are documented adaptations of B-FedStatsBenign.
7. **Wider 10-seed CIs.** The 10-seed result is reported honestly; CIs may be wider than the 5-seed result.

The dominant residual risk is **Ditto absorption**. Whether DATP's gain survives Ditto + B1 — that is, whether model personalization makes threshold personalization redundant — is handled by the pre-specified absorption rule in the Ditto / FedRep-AE Fallback Lock in `docs/journal/PRE_CODING_PLAN.md` *(ARCHIVE: §8.3 reference is stale)*. All three outcomes (strong retention, partial absorption, near-full absorption) are valid findings with pre-specified interpretations; nothing is suppressed.

The secondary residual risk is **Laridi operating-point fairness**. A reviewer familiar with the Laridi method may question whether the matched-exceedance adaptation is fair. The protocol is chosen specifically so the Laridi comparator operates at the same target exceedance as B2 at q = 0.95, which is the most favorable comparison for Laridi. The between-ratio diagnostic gives reviewers additional context on why the comparison is informative under heterogeneity.

What would satisfy a careful reviewer: Appendix A and B2-conf close the tautology critique; Edge-IIoTset provides cross-dataset evidence; the matched-exceedance Laridi comparison closes the federated-thresholding novelty question; the Ditto stress test with absorption rule answers the "why not just personalize the model" line; the temporal MVE addresses threshold aging; and the alert-burden table grounds CV(FPR) in practitioner terms.

---

## 23. Verification Sources

| Query or Source | Type | Date | Key Finding |
|---|---|---|---|
| DATP.pdf | Project knowledge | 2026-05-23 | CV(FPR) 1.017→0.299, B4 ≈52%, 9 physical devices, 5 seeds, E=1, q=0.95; B4-is-not-privacy framing |
| State_of_the_Art.md | Project knowledge | 2026-05-23 | 6 gap clusters |
| Blueprint.md | Project knowledge | 2026-05-23 | Sole confirmatory claim: Regime A B1-vs-B2 CV(FPR); RQ hierarchy; no BN in encoder |
| sciencedirect.com/journal/computers-and-security (Aims & Scope) | Official Elsevier page | 2026-05-23 | Verbatim moratorium on AI/ML/federated-learning submissions |
| sciencedirect.com/journal/computer-networks/publish/guide-for-authors | Official Elsevier page | 2026-05-23 | Verbatim conference-extension policy |
| Rey et al. (2022). Computer Networks 204:108693 | Peer-reviewed | 2026-05-23 | FL MLP+AE on N-BaIoT; foundational predecessor |
| Laridi, Palmer & Tam (2024). Sci. Rep. 14:26704 | Peer-reviewed | 2026-05-23 | Federated thresholding via summary statistics; closest novelty threat |
| Sáez-de-Cámara et al. (2023). Computers & Security 131:103299 | Peer-reviewed | 2026-05-23 | Clustered FL; Local-Largest-MSE thresholds; clusters models, not thresholds |
| Belarbi et al. (2023). GLOBECOM 2023 | Peer-reviewed | 2026-05-23 | FedAvg vs FedProx vs FedYogi on TON-IoT |
| Pradhan et al. (2025). Sci. Rep. | **NOT FOUND** | 2026-05-23 | Could not be located on Nature.com or via web search. Every "per Pradhan et al. 2025" claim is REMOVED. Edge-IIoTset and CICIoT2023 B-b partitioning are decided on first-principles feasibility audits (PRE_CODING_PLAN.md §5.5 and §5.4 — *ARCHIVE: EDGE_IIOTSET_FEASIBILITY.md and CICIOT2023_BB_FEASIBILITY.md not created; LIVE_VERIFICATION_REGISTER.md V-10 not created*). |
| Lu, Yu, Karimireddy, Jordan, Raskar (2023). ICML | Conference | 2026-05-23 | "Federated Conformal Predictors for Distributed Uncertainty Quantification" — primary B2-conf anchor; replaces Plassier as primary (V-07) |
| Humbert et al. (2023). ICML | Conference | 2026-05-23 | "One-Shot Federated Conformal Prediction" — co-anchor for B2-conf |
| Li, Sahu, Zaheer, Sanjabi, Talwalkar, Smith (2020). MLSys | Peer-reviewed | 2026-05-23 | FedProx — generalization of FedAvg with proximal term µ; local epochs E confound comparison if not locked (V-08) |
| Li, Hu, Beirami, Smith (2021). ICML | Peer-reviewed | 2026-05-23 | Ditto — personalized local model regularized toward the global model; frozen-encoder + local-head is NOT Ditto (V-09) |
| Plassier et al. (2023). ICML 2023, PMLR 202:27907 | Conference | 2026-05-23 | Federated conformal prediction |
| Ferrag (2022). Edge-IIoTset. IEEE Access | Peer-reviewed | 2026-05-23 | Native FL framing; 10+ device types |
| FGCS Guide for Authors | Official Elsevier page | 2026-05-23 | 40% new contributions requirement |
| ACM Computing Surveys 2024, DOI 10.1145/3704633 | Peer-reviewed survey | 2026-05-23 | MIA risk; defenses include SecAgg, DP, partial sharing |
| Neto et al. (2023). CICIoT2023. Sensors 23(13):5941 | Dataset paper | 2026-05-23 | 105 devices, 33 attacks; structure permits device-MAC repartition |

---

## 24. Decision Summary

The primary target is **Computer Networks (Elsevier)**, ISSN 1389-1286, 2024 JIF 4.6, Q1. The backup is **Internet of Things (Elsevier)**, then Cyber Security and Applications, then JNCA. The expansion level is **Strong** (§14.2).

The exact must-do list before submission is: (i) Priority 0 metadata check; (ii) Appendix A formal note; (iii) Laridi protocol locked (matched exceedance, full pooled variance with between-client term); (iv) q-sensitivity, calibration-size sweep, shrinkage, and B2-conf; (v) Laridi-style comparator with between-ratio diagnostic; (vi) B4 ablation with contingency table; (vii) JS↔gain regression, alert-burden table, threshold-shift scatter; (viii) 10-seed extension reported honestly; (ix) privacy bounded-disclosure and expanded related work; (x) Edge-IIoTset preprocessing and training; (xi) CICIoT2023 device-MAC repartition if Priority 0 confirms; (xii) FedProx and Ditto/named-variant stress tests with pre-specified interpretation rules; (xiii) temporal MVE with pre-specified outcome interpretation; (xiv) cover letter with explicit extension disclosure.

The do-not-do list is §21 (27 items). The journal extension waits until conference acceptance: all experiments can begin now, but submission is held until the conference camera-ready is set.

Confidence ratings: high for venue exclusion, Computer Networks selection, dataset choice, threshold variants, scope control, and Laridi operating-point fairness; medium–high for the stress-test comparator grid; medium for the temporal MVE outcome (the three pre-specified interpretations cover all directions honestly).

The DATP conference paper has a real and defensible empirical finding and a clean experimental discipline. The journal version's job is to do five things: close the construction-tautology critique via Appendix A, B2-conf, and the calibration-size sweep; show generalization on Edge-IIoTset and, conditionally, on the redesigned CICIoT2023; demonstrate via pre-specified stress tests that the threshold-scope gain is not absorbed by heterogeneity-aware aggregation (FedProx) or model-side personalization (Ditto), and is not dominated by a matched-operating-point Laridi-style federated threshold; show threshold-aging behavior under a chronological split; and ground CV(FPR) in an operational alert-burden metric. The COSE moratorium is binding. The Laridi comparison — matched exceedance, full pooled variance, between-ratio diagnostic — is both the dominant novelty risk and its own resolution.

---

## Appendix. Consistency Check

A short consistency check across this document confirms that: Computer Networks is the primary venue throughout; Computers & Security is excluded throughout; the Strong extension is selected throughout; Edge-IIoTset is the only new dataset; the CICIoT2023 device-MAC repartition is consistently gated on Priority 0 with a benign-volume threshold of ≥ 8 clients at nₖ ≥ 100; FedBN is rejected on encoder-architecture grounds; FedProx and Ditto are framed as external stress-test comparators rather than core causal baselines; the Laridi-style protocol uses the full pooled variance with the between-client term and the matched-exceedance operating point (fixed-k variants are supplementary only); the implementable Laridi protocol exchanges only benign exceedance counts on a fixed candidate grid; the FedProx convergence-failure wording is non-retroactive; the Ditto absorption margins are pre-specified (75% / 25%); the Laridi between-ratio diagnostic appears in the main paper rather than the supplementary; the temporal MVE has three pre-specified outcomes; the 10-seed reporting rule explicitly admits adverse CI changes; the cover-letter language is consistently "at least 40% substantive new material"; the B4 interpretability artifact is a contingency table or small heatmap rather than a Sankey diagram; and no privacy, poisoning, hardware, or broad personalized-FL scope drift is introduced anywhere.
