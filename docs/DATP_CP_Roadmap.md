# CP2 Research Protocol
## Calibration-Channel Poisoning of Federated Threshold Personalization in IoT Anomaly Detection: A Policy-Differentiated Vulnerability Analysis

**Status:** pre-registered empirical protocol. Ready for the Phase-A read-only audit. Phase-B protocol lock and attack implementation are gated on the four Phase-A confirmations in §18.

> **Quick reference.**
> - **Hypothesis (one sentence):** CP2 tests whether poisoning *only* the benign threshold-calibration set of one to three eligible clients can shift DATP-style thresholds enough to cause security failures (raise → victim TPR degradation) or alarm-burden/disparity failures (lower → FPR dispersion), and whether the threshold policies B1/B2/B4 exhibit *different* vulnerability profiles — with training, aggregation, and test data left clean.
> - **5 non-negotiables:** (1) calibration channel only; (2) N-BaIoT primary, clean and poisoned regimes are CP2-generated under conference-faithful **E=1** settings; (3) policy set = **B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER**; (4) clean-vs-poisoned **paired by training_seed and victim plan**, poisoning is the sole stochastic difference; (5) no journal assets and no broad model-/aggregation-/training-poisoning/evasion/privacy/deployment claims.
> - **3 kill triggers:** no material `Δτ` for B2 at the largest fraction across the eligible-victim sweep; threshold shifts that produce no interpretable downstream movement; B1/B2/B4 indistinguishable even after blast radius and spillover are measured.
> - **MVP matrix (locked):** N-BaIoT, {B1,B2,B4}, score-level proxy, fixed-size replacement with victim-local with-replacement resampling, sources {RANDOM_BENIGN, HIGH_SCORE_BENIGN, LOW_SCORE_BENIGN}, objectives {raise, lower}, fractions {0, 0.10, 0.20, 0.40}, all **eligible** single-client victims, `training_seed=[0,1,2,3,4]`, `poisoning_seed=[100,101,102,103,104]`, no retraining if artifacts pass audit.

---

## 1. Paper Identity

- **Working title:** as above. (Internal codename only, never in the manuscript: "The Price of Personalization.")
- **One sentence:** CP2 isolates the threshold-calibration set as an attack surface and measures whether contaminating only a few clients' benign calibration data shifts DATP-style thresholds enough to cause security or alarm-burden failures, and whether B1/B2/B4 differ in vulnerability.
- **Relationship to DATP:** identical model family, FedAvg training (E=1), score artifacts, threshold policies, and N-BaIoT client definition. CP2 follows the DATP clean pipeline protocol as the conceptual unattacked baseline; all clean and poisoned runs are executed in this repository.
- **New vs DATP:** DATP has no adversary. CP2 adds a calibration-only threat model, an attack on the threshold channel, and a per-device-disparity vs detection tradeoff under contamination.
- **Not part of the paper:** new FL algorithms, model personalization, aggregation variants, privacy mechanisms, training/model/test poisoning, deployment validation, journal datasets/comparators. No robustness claim beyond the calibration channel is made or implied.
- **Why conference-sized:** one primary dataset, one CP2-trained model, three policies, two objectives, a small fraction grid, 5 seeds, score-level sharing across policies, and one optional defense.
- **Manuscript vocabulary:** lead with "per-device FPR disparity," "alarm-burden predictability," and "operating-point disparity" rather than "fairness"; the CV(FPR) mathematics is unchanged.

## 2. Research Questions

**Main RQ.** Does poisoning only the benign threshold-calibration set of one to three eligible clients shift DATP-style thresholds enough to induce interpretable downstream failures, and do B1/B2/B4 exhibit different vulnerability profiles?

- **RQ-A:** Does calibration-only poisoning produce material, correctly-signed threshold shifts under the gray-box model?
- **RQ-B:** Do B1/B2/B4 differ in victim sensitivity and in cross-client spillover (blast radius, B4 reassignment)?
- **RQ-C:** Do raise vs lower attacks produce distinct failure modes (security harm vs alarm-burden/disparity)?
- **RQ-D:** Does impact scale from single to limited multi-client compromise?
- **RQ-E (secondary):** Can one trimmed-calibration defense reduce attack impact without erasing the clean-setting DATP benefit?

## 3. Threat Model

Three nested variants; all main empirical claims use the gray-box variant only.

- **Capability (main):** compromises the **local calibration-curation process** of 1–3 eligible clients (admission/retention control over which benign records enter the benign calibration buffer). Cannot alter training data, model updates, server aggregation, or test data.
- **Goal:** raise or lower the victim's effective threshold to cause missed detections (raise) or excess/uneven false alarms (lower).
- **Knowledge (main, gray-box):** local reconstruction scores of candidate calibration records. Realistic because in FL each client holds the broadcast AE and can score candidates locally; gray-box access is a property of FL, not an extra assumption.
- **Location / timing:** the victim's benign calibration set, after training, before threshold computation, within the CP2 clean run; no retraining implied.
- **Targeting:** eligible clients only; MVP single-victim sweep over all eligible clients; Full adds pre-registered pairs/triples.
- **Cannot do:** modify the model, gradients, aggregation, server code, or test set; relabel test data; observe other clients' raw data.
- **Grounding scenario (committed):** a compromised local data collector / rogue device operator that selectively admits or retains benign-looking traffic into the victim device's (or its gateway's) calibration buffer.
- **Minimal-realistic variant (anchor + control):** local calibration admission on one client with little or no score feedback; justifies `RANDOM_BENIGN` as a negative control.
- **Diagnostic upper bound (appendix only):** direct edits to the calibration score array with full score knowledge; used solely to distinguish "channel intrinsically robust" from "attack instantiation too weak." Never used for main claims.

## 4. Experimental Regimes

- **`REGIME_A_NBAIOT` (primary).** N-BaIoT; one physical device = one client, K=9; eligibility `n_cal ≥ 100` (DATP reports all 9 eligible in Regime A). Clean baseline = CP2-generated per-client calibration/test score arrays produced by CP2-controlled clean runs in this repository, under B1/B2/B4. Poisoned variants = {raise, lower} × {RANDOM, HIGH, LOW} × fractions, single-victim sweep over all eligible clients (MVP); pairs/triples (Full). Seeds = 5 paired. Rounds = 40 initial → 150 max under E=1 (clean artifacts must be CP2-generated in this repository; FB1 activates if no confirmed CP2-controlled clean artifacts exist).
- **`REGIME_STRETCH_CIC` (optional, FB4-gated).** CICIoT2023 file-level pseudo-clients (DATP partition: 63 pseudo-clients, near-homogeneous benign distributions). Documented file/chunk pseudo-clients only; eligibility/calibration only if CP2-safe artifact semantics exist. Clean baseline + reduced poisoned set (one or two best variants); 3–5 seeds. Interpretation is a contrast, **not** natural-client equivalence. **B4 K rule:** the silhouette-selected K is chosen once on the clean condition and **frozen** for every clean/poisoned paired comparison; poisoning may move assignments but never the cluster count. If K cannot be held stable, B4 is dropped from the stretch regime and only B1/B2 run there.
- **`REGIME_SMOKE_SYNTHETIC`.** Synthetic score arrays, precedes both for invariant validation (§10).

## 5. Threshold Policies

| Policy | Meaning | Tests | Supports | Cannot prove |
|---|---|---|---|---|
| `B1_GLOBAL` | single shared threshold = simple arithmetic mean of eligible clients' `p95` thresholds | spillover via shared-pool contamination | broad but diluted blast radius | localized victim sensitivity |
| `B2_PERSONALIZED` | per-client `p95` threshold; the attacked mechanism | high local victim sensitivity, near-zero spillover | victim-level fragility of personalization | cross-client spillover |
| `B4_CLUSTER` | cluster-mean threshold via the frozen DATP procedure on (possibly poisoned) fingerprints | intermediate sensitivity + cluster spillover + reassignment | middle-ground tradeoff and a distinct spillover mechanism | a clustering-quality result |

`B3` (family-mean) is appendix-only and is **not** in the default `ThresholdPolicy` enum.

**B4 specification.** Fingerprint `v_i = [mean(E_i), std(E_i), skew(E_i), p95(E_i)]` from the (possibly poisoned) calibration errors; StandardScaler-normalized; k-means++ `n_init=10`, `max_iter=300`, `random_state=42`, **K=3** (Regime A). `τ_c` = arithmetic mean of eligible clients' `τ_i` within the cluster. "Frozen" = this exact procedure/hyperparameter set, **not** a fixed cluster-to-device map. **All B4 deltas are client-indexed:** client `i` receives its assigned cluster's threshold (its *effective threshold* `τ_i^eff`), and `Δτ_i = τ_i^{eff,pois} − τ_i^{eff,clean}` for the same client. Raw k-means label IDs (which can permute) are never compared across runs.

**B4 decomposition** (on client-effective thresholds). From the clean fingerprints obtain assignments `A_clean`, scaler `S_clean`, and `τ_i^{eff,clean}`. For a poisoned condition, per client `i`:
- **Component 1 — within-cluster aggregation:** hold `A_clean` and `S_clean` fixed; recompute each `τ_j` from the poisoned calibration and re-average within frozen clusters → `τ_i^{eff,agg}`; `Δτ_i^agg = τ_i^{eff,agg} − τ_i^{eff,clean}`.
- **Total:** run the full frozen procedure on the poisoned fingerprints — refit StandardScaler (`S_pois`), re-run k-means (`random_state=42`, K=3) → `τ_i^{eff,pois}`; `Δτ_i^total = τ_i^{eff,pois} − τ_i^{eff,clean}`.
- **Component 2 — churn (residual):** `Δτ_i^churn = Δτ_i^total − Δτ_i^agg`. The two components sum exactly to the total; report both signed (they may oppose) plus the total. Churn bundles reassignment and the normalization-mediated effect (one poisoned fingerprint shifts `S_pois`, perturbing non-victim standardized coordinates and thus assignments) — logged as B4 spillover.
- **Optional sub-diagnostic:** if `|Δτ_i^churn|` is material, re-cluster the poisoned fingerprints with the scaler frozen at `S_clean`; the gap to the full `S_pois` run isolates the pure normalization-mediated component. This component is reported **per client** and summarized into `SpilloverCount` only as an aggregate. No new clustering method is introduced anywhere.

## 6. Attack Design

**Common contract.** For client `i`, clean benign calibration scores `S_i^cal` and fixed clean test scores `S_i^tst`. For each policy, compute the clean threshold from `S_i^cal` and the poisoned threshold from the contaminated calibration. Model, test scores, and labels are unchanged. Procedure: (1) start from clean artifacts; (2) contaminate calibration scores; (3) recompute thresholds (including B4 re-clustering); (4) reclassify unchanged test scores; (5) compare.

**Injection (`REPLACE_FIXED_BUDGET`).** For poison fraction `f>0` on a victim with `n_i` calibration scores, `m_i = max(1, round(f·n_i))`. Replace `m_i` randomly chosen positions with **values resampled with replacement** from the source reservoir; total size stays `n_i`. This holds cardinality constant, isolating *content* contamination. Because values are sampled with replacement, any `m_i` (including `f=0.40`) is supplied without widening the tail — modeling an attacker repeatedly admitting/retaining similar high- or low-error benign candidates.

**Source strategies (score-level, victim-local).** All reservoirs are victim-local value reservoirs; cross-client reservoirs are diagnostic-only (they imply stronger access than gray-box grants). Source precedence: (1) if the artifacts expose victim-local benign **calibration-candidate** scores *not* used to fit the clean threshold, draw from those; (2) otherwise resample values with replacement from the victim's clean calibration-score distribution (its tail for HIGH/LOW; full pool for RANDOM), recording the abstraction in the manifest. Test scores are **never** a reservoir; training scores are **not** used.
- `RANDOM_BENIGN` — negative control: values resampled from the victim's own full benign pool. Pre-registered near-null criterion: median `|Δτ_i|` below the materiality cutoff `δ_{τ,i}`; **and**, *only when the matched HIGH/LOW effect at the same fraction is itself material*, also below 0.25× that effect (if the matched attack is non-material, the absolute criterion alone applies). A `RANDOM_BENIGN` deviation is an **audit flag** (investigate sampling variance / pipeline), not an automatic kill trigger.
- `HIGH_SCORE_BENIGN` (raise): values resampled from the victim's own upper tail (fixed top **10%** mass) → threshold rises → victim TPR degrades; FPR flat/down.
- `LOW_SCORE_BENIGN` (lower): values resampled from the victim's own lower tail (bottom 10% mass) → threshold lowers → victim FPR rises, dispersion worsens.
- `LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY` (diagnostic, used only if `LOW_SCORE_BENIGN` is null): replace *upper-tail* positions with lower-tail values for maximum threshold-lowering pressure. Distinguishes "channel robust to lowering" from "random replacement did not remove quantile-supporting values." Never enters the main matrix or gray-box claims.

**Reservoir feasibility.** The tail mass is fixed at 10% and defines attack *shape*, not supply. FB2 (INFEASIBLE) fires only in a degenerate case — a victim whose 10% tail contains fewer than two distinct values (`n_cal` so small the tail is undefined). Such a (client, fraction) cell, if infeasible in any seed, is excluded from all seeds to keep the paired design balanced. Does not bind on N-BaIoT.

**Disclosed proxy artifact.** At high fractions, with-replacement resampling from a fixed 10% tail produces repeated injection values (e.g., ~40 replacements drawn from ~`0.10·n_i` distinct scores), yielding a more uniform contaminated tail than a realistic attack might. This is a known property of the score-level proxy abstraction, disclosed in the limitations and recorded in the Phase-A manifest alongside the general realizability caveat. It is not a validity threat to the calibration-channel claim.

**Target scopes.** MVP: `SINGLE_CLIENT`, sweeping all eligible victims per seed. Full: `MULTI_CLIENT` = all `C(9,2)` eligible pairs + exactly `N_triples=20` triples sampled without replacement from the lexicographically sorted eligible triples using `compromise_pattern_seed=400` (selection not conditioned on MVP results). In a multi-client run, each co-victim is injected with an **independent** stream (see §10 child-seed rule), so replacements are not correlated across co-victims. Diagnostic: `ALL_CLIENTS_DIAGNOSTIC_ONLY`.

**Defense (Full, optional, `TRIMMED_CALIBRATION`).** Symmetrically trim the top-`t%` and bottom-`t%` of the victim's calibration reconstruction errors **before** both the threshold percentile and the B4 fingerprint are computed (applied consistently to every calibration-derived quantity). **Primary setting `t=5%`; `t=10%` is appendix-only sensitivity**; both are reported if run, and `t=5%` carries any main-text mitigation claim unless the protocol declares both co-primary before Full. The defense is decided before Full; once run it is reported regardless of outcome, with clean-setting regression reported for all policies including B4.
- **Recovery ratio** for a harm metric `H`: `Recovery = (H_pois − H_defended) / max(|H_pois − H_clean|, ε_num)`, sign-oriented so positive recovery always means harm reduction (`ε_num` a small numerical stabilizer). The declared primary harm metric is victim `ΔTPR` for raise and worst-client FPR / `ΔCV(FPR)` for lower, alongside `Δτ`.
- **Material clean-setting regression** (thresholds locked before Full): any clean-condition degradation exceeding one of — `|Δτ_clean_defense| ≥ δ_{τ,i}`; victim/client TPR drop ≥ 1 percentage point; Macro-F1 drop ≥ 1 percentage point; or CV(FPR) worsening ≥ 10% relative to the undefended clean policy.
- **Placement:** the defense appears in the **main results** iff `Recovery ≥ 0.5` on the declared primary harm metric **without** material clean-setting regression; otherwise it is reported in the **appendix**. It is never hidden.

## 7. Calibration and Eligibility Rules

- **Calibration set:** benign-only holdout from DATP's N-BaIoT chronological split (60% train / gap / 20% calibration / gap / ~19% test), per device.
- **Benign-only:** thresholds are computed from benign calibration scores; attack labels never enter calibration.
- **Minimum samples:** `n_min = 100`; below this → calibration-pending.
- **Calibration-pending clients:** receive `τ_global`, do **not** contribute to `τ_global`, do **not** enter B4 clustering, and are excluded from CV(FPR). They affect no threshold and are **not valid victims**; excluded from the victim sweep.
- **Eligibility under attack:** fixed-size replacement preserves `n_i`, so no client becomes pending due to the attack; the eligible set is fixed, making every (victim, seed) pair balanced.
- **Fallback threshold:** the only fallback threshold in scope is DATP's existing `τ_global` for calibration-pending clients; CP2 introduces none.
- **Artifact provenance (manifest must confirm):** CP2-generated within this repository (not from another repository, not journal); conference protocol with **E=1**; exact checkpoint/round; DATP train/calibration/test semantics; per-client calibration scores present; clean test scores present; no journal-only threshold variants; safe read-only paths. **Any E=5 artifact is rejected.** Manifest also records reservoir-sampling mode and the locked `mu_flag_threshold`.

## 8. Metrics

Let `i` index clients, `p` index policies.

- **Primary endpoint — mechanism + downstream link:** `Δτ_{i,p} = τ^pois − τ^clean`; `|Δτ|`; relative `Δτ_rel = (τ^pois − τ^clean)/max(|τ^clean|, ε)` (denominator uses `|τ^clean|` so the numerator sign is preserved; `ε` numerical only). A primary claim requires `Δτ` with correct sign **and** movement in at least one downstream metric.
- **Secondary:** victim `ΔTPR` (raise), `ΔBA`, `ΔMacroF1`, `ΔP10-ClientF1`.
- **Per-device disparity:** `CV(FPR) = σ/µ` over eligible clients (**no ε**); `IQR(FPR)` and `max–min FPR` as small-denominator guards; `WorstClientFPR = max_i FPR_i`; `ΔCV(FPR)`. When `µ_FPR < mu_flag_threshold`, CV is flagged unstable and the absolute-dispersion metrics become primary for that condition.
  - `mu_flag_threshold = round(M_clean/8, 2 significant figures)`, where `M_clean` is the clean B1 eligible-client mean FPR from Phase-A artifacts, fixed and written to the manifest **before any poisoned run** (≈0.005 at DATP's clean FPR scale). It is purely a CV-instability flag, **not** a denominator stabilizer.
- **Attack success:** materiality scale `δ_{τ,i} = 0.1 · IQR(S_i^{cal,clean})`; if `IQR(S_i^{cal,clean}) = 0` (degenerate clean calibration), substitute the median absolute deviation, or the minimum positive score gap if MAD is also zero. `ASR_raise = mean 1[Δτ ≥ δ]`, `ASR_lower = mean 1[Δτ ≤ −δ]` over attacked (victim, seed) pairs.
- **Diagnostics:** `BlastRadius_p = (1/|K_elig|) Σ 1[|Δτ_i| ≥ δ_i]`; `SpilloverCount_p = Σ_{i ∉ compromised} 1[|Δτ_i| ≥ δ_i]`; B4 reassignment count; `AUROC` on the fixed clean test scores (invariant by construction — see §14).

**Interpretation rule.** Because a raise attack can lower FPR while lowering TPR, no single disparity metric tells the whole story; CP2 jointly reports `Δτ`, victim `ΔTPR`, and FPR dispersion. The raise narrative is anchored on victim TPR/BA; the lower narrative on worst-client FPR / `ΔCV(FPR)`.

## 9. Statistical Plan

- **Two-layer unit of analysis.** Layer 1 (per-victim): the 5 paired seed deltas per victim drive sign consistency and descriptive heterogeneity. Layer 2 (policy-level inference): for each policy×objective×fraction, form one seed-level aggregate per seed = the mean paired delta over all eligible-and-feasible victims, yielding 5 aggregates; primary CIs and tests operate on these 5. The 9×5 (victim, seed) deltas are never treated as 45 independent replicates.
- **Sign consistency:** per victim, a directional effect must hold in **≥4/5 seeds**.
- **Aggregate claim rule (no post-hoc victim selection):** an RQ-A/RQ-B claim requires the directional effect to hold for a strict majority of eligible-and-feasible victims (`≥ floor(m/2)+1` of the `m` such victims; m=9 on N-BaIoT absent infeasibility → ≥5) at ≥4/5 sign consistency. The victim with the largest effect is not used to anchor the claim.
- **Confidence intervals:** 95% bootstrap CI on the mean of the 5 seed-level aggregates, using the same bootstrap variant as the DATP conference implementation. If undocumented, default to the **percentile** bootstrap (stable at n=5); BCa only if DATP used it or the smoke stage confirms BCa is stable at n=5 (BCa can be anti-conservative at this sample size).
- **Hypothesis test:** exact paired sign test on the 5 aggregates, as a supporting statistic.
- **Multiple comparisons:** Holm-adjusted p-values are reported **only as descriptive annotations** within the pre-registered primary family {N-BaIoT; B1/B2/B4; single-victim; HIGH→raise; LOW→lower; fractions 0.10/0.20/0.40}. At n=5 the exact sign test cannot attain two-sided p < ≈0.06, so Holm cannot gate inference. The **decision gate** is the five-part rule: material effect size + correct direction + ≥4/5 seed consistency + strict-majority-of-victims + downstream-metric movement.
- **Effect sizes:** report the median paired delta and bootstrap CI for every primary comparison.
- **Negative-result handling:** if the primary family fails the aggregate rule, the kill/pivot path (§16) activates; a bounded-vulnerability or null result is reported honestly, never reframed.
- **Move to 10 seeds only if:** sign consistency is borderline, seed variance is large, the B1/B2/B4 ordering flips across seeds, or the central claim rests on an unstable effect.

## 10. Implementation Plan

- **Repository:** `/home/naslouby/Projects/datp-calibration-poisoning`, isolated from the control and journal repos. `data/raw` → `…/datp-shared-data/raw` (read-only). Outputs only under `outputs/conference_calibration_poisoning/`.
- **Enums (stable):** `ThresholdPolicy = {B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER}` (B3 excluded from the default enum; appendix-only behind an explicit CLI flag); `AttackerObjective = {THRESHOLD_RAISE, THRESHOLD_LOWER}`; `PoisoningSourceStrategy = {RANDOM_BENIGN, HIGH_SCORE_BENIGN, LOW_SCORE_BENIGN, LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY}`; `CalibrationInjectionRule = {REPLACE_FIXED_BUDGET}` (append diagnostic-only); `PoisoningKnowledge = {GRAY_BOX_SCORE_ACCESS, WHITE_BOX_DIAGNOSTIC_ONLY}`; `PoisoningTargetScope = {SINGLE_CLIENT, MULTI_CLIENT, ALL_CLIENTS_DIAGNOSTIC_ONLY}`; `PoisoningDefense = {NONE, TRIMMED_CALIBRATION}`; `ExperimentScale = {SMOKE, MVP, FULL, STRETCH}`; `AuditDisposition = {KEEP_CORE, REFACTOR_CORE, QUARANTINE_JOURNAL, REMOVE_STALE, BLOCK_UNSAFE}`.
- **Seeds:** `training_seed=[0,1,2,3,4]`; `poisoning_seed=[100,101,102,103,104]`; `analysis_seed=[300,301,302,303,304]`; `split_seed=[200,201,202,203,204]` only if new splits must be generated; `compromise_pattern_seed=400` for multi-client victim-set sampling; `cluster_seed` unused (k-means is `random_state=42`). **Per-injection randomness uses a deterministic child seed** `SeedSequence([training_seed, poisoning_seed, client_id, scope_id])` rather than integer addition; every derived seed is recorded in the manifest. Co-victims in a multi-client run differ by `client_id`, giving independent injection streams by construction.
- **Module responsibilities:** attack-config parsing; calibration poisoning injector (no in-place mutation of clean arrays; with-replacement value resampling from the victim-local tail); threshold recomputation (B1/B2/B4 including B4 re-clustering + client-indexed decomposition); paired clean-vs-poisoned metric comparison; artifact-manifest validation (E=1 enforcement; record reservoir mode and `mu_flag_threshold`); synthetic-smoke harness.
- **Orchestration:** stage-scoped configs (`common`, `audit_readonly`, `nbaiot_smoke`, `nbaiot_mvp`, `nbaiot_full`, `ciciot2023_stretch`, `paper_figures`). Run-path: `…/<scale>/<dataset>/<policy>/<objective>/<source>/f_<fraction>/scope_<scope>/train_<seed>/poison_<seed>/`.
- **Logging/artifacts:** MLflow tracking; manifests `project_audit_report.json`, `clean_score_artifacts.json`, `nbaiot_mvp_manifest.json`, `paper_figure_manifest.json`.
- **Reproducibility:** `PYTHONHASHSEED=0`; seed Python/NumPy/PyTorch CPU+GPU/dataloader/split/poison-selection/bootstrap via the child-seed scheme; clean and poisoned differ only by the poisoning intervention.
- **Compute / tests:** score-level smoke/MVP threshold recomputation is **CPU-safe**; tests must not require CUDA. GPU-only enforcement via `pytest.fail()` applies **only to the FB1 retraining path**. Tests cover the smoke invariants, determinism (same seeds → identical outputs), no-in-place-mutation, and output isolation to temp during smoke.
- **Validation gates:** Phase-A audit pass → protocol lock → smoke pass → MVP result audit → Full.

**Smoke invariants (synthetic).** (1) `f=0` → zero `Δτ`; (2) `RANDOM_BENIGN` → near-null; (3) `HIGH_SCORE_BENIGN` raises B2 thresholds; (4) `LOW_SCORE_BENIGN` lowers B2 thresholds; (5) B1 victim shift < B2 victim shift under the same single-client attack; (6) B4 threshold delta and the client-indexed within-cluster/churn decomposition are computable and finite (measurability invariant — not "B4 lies between B1 and B2," which is a hypothesis); (7) AUROC on unchanged test scores invariant; (8) clean calibration arrays never mutated in place; (9) reproducibility; (10) outputs in temp only; (11) B4 K stays fixed at 3 on N-BaIoT under clean and poisoned conditions — the procedure is never silently overridden to a data-adaptive K.

## 11. Analysis, Figures, and Tables

- **Tables:** T1 threat-model summary (minimal/main/diagnostic); T2 experiment matrix; T3 dataset & client summary (why N-BaIoT primary; CICIoT2023 cautions); T4 main results (clean vs poisoned per policy, mechanism + one downstream metric, split into a raise panel and a lower panel); T5 claims↔evidence; T6 failure/pivot interpretation (appendix if tight).
- **Figures:** F1 system + attack surface (calibration is the only manipulated stage); F2 calibration-poisoning mechanism (fixed-size replacement in score space; caption states it models calibration-set *composition*, not direct score editing); F3 `Δτ` vs fraction per policy/objective (main mechanism); F4 `ΔCV(FPR)`/worst-client FPR vs fraction (lower-attack disparity); F5 B1/B2/B4 vulnerability profile (victim `|Δτ|`, blast radius, spillover, B4 reassignment); F6 victim `ΔTPR` vs worst-client `ΔFPR` (failure-mode separation).
- **Outline↔figure map:** Intro→F1,T1; Background→F2; Policies→T2; Threat model→T1; Attacks→F2,F3; Setup→T2,T3; Results→F3–F6,T4; Discussion→F5/F6,T5/T6.
- **Diagnostics:** AUROC-invariance check; B4 reassignment heatmap (appendix).
- **Ablations:** fraction grid; trimmed-calibration `t=5%`/`t=10%` (Full); diagnostic upper bound (appendix).
- **Appendix:** infeasible (client, fraction) report; eligibility/coverage per seed; diagnostic-upper-bound results; B4 decomposition; high-fraction with-replacement disclosure.

## 12. Non-Negotiable Locks

- **Scope:** calibration-channel poisoning only; training data, model weights, aggregation, and test data are never attack targets; no broad model-/aggregation-/training-poisoning/evasion/privacy/deployment/model-personalization claims.
- **Datasets:** N-BaIoT primary (one device = one client, K=9, all eligible); CICIoT2023 stretch only (FB4-gated); Edge-IIoTset forbidden.
- **Policies:** `B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER`; B3 appendix-only, not in the default enum.
- **Attack:** objectives {raise, lower}; sources {RANDOM_BENIGN, HIGH_SCORE_BENIGN, LOW_SCORE_BENIGN}; `REPLACE_FIXED_BUDGET` with victim-local **with-replacement** value resampling from a fixed 10% tail (full pool for RANDOM); `SCORE_LEVEL_PROXY` (raw-sample is stretch only).
- **Fractions:** MVP `{0, 0.10, 0.20, 0.40}`; Full adds `0.05`.
- **Seeds:** as in §10; per-injection child seeds via `SeedSequence`; `cluster_seed` unused.
- **Rounds (only if retraining):** `rounds_initial=40`, `rounds_max=150`, DATP convergence criterion. **Local epochs `E=1`** (manifest rejects E=5).
- **Pairing:** clean and poisoned share the same training_seed, AE, test scores, split, and victim plan; poisoning is the only stochastic difference.
- **Eligibility:** `n_min=100`; eligible-only victim sweep; calibration-pending excluded from CV(FPR) and the victim set; replacement preserves eligibility.
- **Dispersion:** `CV(FPR)=σ/µ` (no ε), guarded by `IQR(FPR)` and `max–min FPR`; `mu_flag_threshold` as defined in §8.
- **Statistics:** two-layer unit; ≥4/5 sign consistency; bootstrap CI on 5 seed-level aggregates (percentile default); strict-majority (`floor(m/2)+1`) aggregate rule; Holm descriptive only; B4 deltas client-indexed.
- **Primary endpoint:** material `Δτ` with correct sign linked to ≥1 downstream metric (victim ΔTPR for raise; ΔCV(FPR)/worst-client FPR for lower).
- **Venue/deadline/submission strategy:** intentionally out of scope; must not gate protocol or ticket progress.

## 13. Fallback Register

**FB1 — Clean score artifacts fail provenance audit.** Trigger: manifest cannot confirm conference-faithful (E=1, T=40→150, DATP split semantics, CP2-generated within this repository) clean per-client calibration/test score arrays. Fallback: one CP2-controlled clean retrain executed within this repository — exactly `E=1`, `rounds_initial=40`, `rounds_max=150`, same convergence criterion, FedAvg weighted by local benign size, Flower; write fresh score artifacts with a complete manifest. Safe wording: "Clean baselines were reproduced under the published DATP conference protocol; no hyperparameters were re-tuned."

**FB2 — Victim tail reservoir is degenerate.** Trigger: a victim's fixed 10% tail has fewer than two distinct values in at least one training seed. (Supply is otherwise unconstrained via with-replacement resampling, so `f=0.40` is feasible.) Fallback: mark the (client, fraction) cell INFEASIBLE; exclude from all seeds; report per-client. Does not bind on N-BaIoT.

**FB3 — B4 procedure not reproducible from artifacts.** Trigger: if the DATP manifest stores per-seed clean B4 assignments or client-effective thresholds, re-running the frozen procedure does not reproduce them exactly; else (no assignment manifest) the procedure cannot be reconstructed or its summary-level B4 metrics diverge from DATP's reported values. The cross-seed ARI (mean 0.79, range [0.64, 1.0]) is a stability descriptor, not the per-seed pass/fail criterion. Fallback: downgrade B4 to a secondary diagnostic; if still unstable, drop B4 and run B1 vs B2 only. Safe wording: "B4 results are reported as a secondary diagnostic; the primary policy contrast is B1 vs B2."

**FB4 — CICIoT2023 client semantics unsafe, or B4 K shifts under poison.** Trigger: no reproducible documented pseudo-client partition; or the silhouette-selected K differs between clean and poisoned in the stretch regime. Fallback: if semantics are unsafe, drop CICIoT2023 (N-BaIoT-only, narrowed external-validity claims); if only K-stability is the issue, drop B4 from the stretch and run B1/B2 there. Safe wording: "On the optional larger corpus, B4's cluster count is fixed from the clean condition so that poisoning alters assignments, not the policy definition."

## 14. Reviewer Risk Register

| Reviewer attack | Roadmap defense | Safe wording |
|---|---|---|
| "Just data poisoning." | calibration *channel* is structurally distinct from the training pipeline; analog to conformal-calibration contamination imported into FL-IoT AD for the first time | "We attack the threshold-calibration set, not training, aggregation, or test data." |
| "Threat model unrealistic." | committed grounding scenario (compromised local calibration curation); gray-box = local scoring with the broadcast AE | "An adversary controlling local calibration admission can score candidates with the locally held model." |
| "Gray-box is an oracle." | FL clients already hold the model; diagnostic upper bound kept out of the main text | "Local scoring is a property of FL, not an added assumption." |
| "Score-level proxy is abstract." | exact stage isolation + AUROC invariance; high-fraction repetition disclosed; raw-sample stretch | "Score-level poisoning isolates the calibration stage; raw-traffic realization is future work." |
| "AUROC doesn't change → trivial." | AUROC measures score ordering; score-level recalibration cannot change ordering, so invariance verifies stage isolation — the object is the operating point, not score geometry | "AUROC invariance is the expected sanity check for a threshold-only intervention." |
| "B2-most-vulnerable is obvious." | claim is policy-differentiated profiles; measure blast radius, spillover, B4 reassignment | "Personalization concentrates victim sensitivity; shared/cluster policies trade it for spillover." |
| "B4 is arbitrary." | frozen DATP procedure (random_state=42, K=3); no new clustering | "B4 reuses the DATP clustering procedure unchanged." |
| "Only one dataset." | N-BaIoT natural device clients; optional CIC contrast | "We demonstrate the mechanism on physical-device clients; broader corpora are future work." |
| "Only 5 seeds / weak stats." | two-layer paired design, sign test, bootstrap CI, ≥4/5 + strict-majority rule | "Evidence is paired effect magnitude, seed-level consistency, and strict-majority-of-victims support, not high-powered significance." |
| "No defense." | optional trimmed-calibration (Full) with clean-regression report and a recovery-based placement rule | "A lightweight trimmed-calibration defense partially mitigates the lower attack." |
| "Overlap with DATP." | adversary + channel are new; no DATP mechanism re-run | "CP2 adds an adversary to DATP's clean pipeline." |
| "Results depend on one client." | eligible-victim sweep + strict-majority aggregate rule | "The claim requires a strict majority of eligible victims, not a single device." |
| "Disparity ≠ security." | manuscript uses per-device disparity / alarm burden; victim TPR foregrounded for security | "Disparity is one operational consequence; detection harm is reported separately." |

## 15. Claim Discipline

- **If positive:** "Poisoning only the benign calibration set of one to three eligible clients shifts DATP-style thresholds materially under a gray-box adversary, with policy-differentiated profiles; raise attacks degrade victim detection while lower attacks degrade per-device FPR disparity."
- **If mixed:** foreground the objective/policy that works; "Under the tested settings, [raise/lower] produced consistent [security/disparity] harm, while [the other] was bounded." Report blast radius/spillover descriptively.
- **If negative:** "Under the tested gray-box settings and fractions, calibration-only poisoning did not produce material threshold shifts; the calibration channel appears robust to composition-only contamination in this protocol" — paired with the diagnostic-upper-bound result to localize the cause; trigger the pivot path.
- **Never claim:** first poisoning work in FL-IDS; B2 universally worst; broad FL/model robustness; privacy/DP guarantees; deployment readiness; raw-traffic realizability from score-level results; significance from tiny unpaired samples.
- **Novelty is a kill criterion, not an objection:** if the work cannot be defended as a calibration-channel contribution distinct from generic poisoning, pivot per §16 rather than weakening wording.

## 16. Kill and Pivot Criteria

**Kill CP2 if, after audit and the N-BaIoT MVP:** (1) no material threshold shift for B2 under HIGH/LOW even at the largest fraction, across the eligible-victim sweep; (2) threshold shifts do not translate into any interpretable downstream movement; (3) B1/B2/B4 remain indistinguishable even after blast radius and spillover; (4) the effect appears only under the diagnostic upper bound, not the gray-box model; (5) the repository cannot be cleaned without a timeline-breaking refactor; (6) the work cannot be cleanly separated from journal assets; (7) it cannot survive review without collapsing into "generic poisoning."

**Ranked pivots (reuse what exists):** (1) client-definition sensitivity; (2) partial-participation/dropout threshold stability; (3) operational alert burden; (4) evaluation-protocol sensitivity / SoK; (5) DP-noise and FPR equity; (6) cold-start threshold personalization. Pivot fast when a kill criterion fires; do not weaken claims to avoid a pivot.

**Cut order if time is tight:** raw-sample stretch → CICIoT2023 → defense → multi-client → extra diagnostics. Never cut the audit or the main N-BaIoT B1/B2/B4 paired clean-vs-poisoned design.

## 17. Out-of-Scope Boundary

Edge-IIoTset; FedProx/FedRep/FedPer/Ditto; conformal thresholding; temporal recalibration; the 10-seed journal regime by default; calibration-size sweeps; model-level personalization; training-data/model/backdoor/evasion poisoning; secure-/robust-aggregation baselines; live-device, latency, or energy claims; the Laridi-style comparator and B-FedStatsBenign (journal-reserved). Client-definition realism, dropout, DP-noise, cold-start, and alert burden remain pivots/discussion only, never primary studies here.

## 18. Phase Plan and Execution Checklist

**Phases.** A — read-only project audit (paths, stale regimes, journal contamination, CP2 self-containment audit, clean-artifact provenance, E=1 check, B4 reproducibility, bootstrap-variant location). B — scientific protocol lock. C — MVP implementation (injector, threshold recompute, manifest validation, synthetic tests). D — smoke validation (synthetic invariants 1–11). E — N-BaIoT MVP (eligible-victim sweep), then result audit. F — Full (fractions, multi-client, optional defense, optional CIC). G — paper package.

**Phase-A protocol confirmations (gate the Phase-B lock; none blocks the Phase-A audit itself):**
1. CP2-generated clean score artifacts confirmed under **E=1** in this repository (else activate FB1 to generate within this repository).
2. **DATP bootstrap variant** (percentile vs BCa) — locate the bootstrap-CI implementation in this repository's DATP training/evaluation or threshold-computation module; inherit verbatim, else default percentile.
3. **B4 procedural reproducibility** — confirm the frozen B4 procedure on CP2 clean artifacts yields reproducible per-seed assignments and metrics (else FB3).
4. Venue/deadline/submission strategy is intentionally out of scope for this CP2 cleanup and must not gate protocol or ticket progress.

**Checklist.**
- *Pre-coding:* the protocol confirmations above; surface CP1 calibration/test split semantics; confirm CICIoT2023 client semantics (or pre-drop); lock `mu_flag_threshold = round(M_clean/8, 2 s.f.)` and the material-clean-regression thresholds from clean artifacts before any poisoned run.
- *Coding:* injector (no in-place mutation; with-replacement victim-local resampling; child-seed scheme; independent co-victim streams); B1/B2/B4 recompute + client-indexed B4 decomposition; manifest validation (E=1 reject; record reservoir mode and `mu_flag_threshold`); synthetic smoke; B3 absent from the default enum.
- *Experiment:* smoke invariants pass → MVP → result audit before Full.
- *Defense (if run):* trim threshold **and** B4 fingerprint; primary `t=5%`, `t=10%` appendix; main-text iff `Recovery ≥ 0.5` without material clean regression, else appendix; report regardless of outcome.
- *Post-experiment:* per-victim sign consistency; strict-majority aggregate; bootstrap CIs; INFEASIBLE-cell report; eligibility/coverage per seed; client-indexed B4 decomposition; AUROC-invariance check.
- *Paper-writing:* raise/lower narrative split; per-device-disparity vocabulary; T5 claims↔evidence; verify Nguyen et al. and Kravchik et al. against primaries (Kravchik = online/training-time ICS, distinct from calibration); nearest-neighbor related-work distinctions; limitations (score-level proxy incl. high-fraction repetition, N-BaIoT age, 9 clients, no deployment).
- *Final audit:* terminology/enum/regime/metric consistency; no journal asset; manifests complete; claims match the results tier.

## 19. Residual Risks to Watch

- The paper's existence depends on a non-trivial `Δτ` under the gray-box model across a strict majority of eligible victims; if only the diagnostic upper bound moves thresholds, kill criterion (4) fires.
- B4 reproducibility must be confirmed before the protocol lock (FB3), not after.
- Watch during implementation: in-place mutation of clean arrays; any test- or training-score leakage into a reservoir; cluster-label IDs compared instead of client-effective thresholds; any E=5 artifact slipping through; B4 K silently changing on N-BaIoT (must stay 3); scope creep from pivots/discussion into the main matrix.

---

**Strongest claim defensible if the primary endpoint is met:** CP2 introduces and empirically isolates a calibration-channel poisoning threat for DATP-style federated IoT anomaly detection — contaminating only one to three eligible clients' benign threshold-calibration sets, with training, aggregation, and test data clean — and characterizes whether B1/B2/B4 exhibit distinct vulnerability profiles, with raise and lower attacks inducing separable security-detection and per-device-disparity failure modes. The verb "shows" is earned only after the primary endpoint is met; all stronger phrasings remain out of scope by design.
