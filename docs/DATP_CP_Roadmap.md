# Updated Roadmap Audit and Rewrite
### Conference Paper 2 (CP2): Calibration-Channel Poisoning of DATP-Style Federated IoT Anomaly Detection

> **Fast-read (implementation quick reference).**
> - **Paper in one sentence:** CP2 tests whether poisoning *only* the benign threshold-calibration set of one to three eligible clients can shift DATP-style thresholds enough to cause security failures (raise attack → victim TPR degradation) or alarm-burden/disparity failures (lower attack → FPR dispersion), and whether the three threshold policies (B1/B2/B4) exhibit *different* vulnerability profiles, with training, aggregation, and test data left clean.
> - **5 non-negotiables:** (1) calibration channel only; (2) N-BaIoT primary, all reuse is conference-faithful **E=1** artifacts; (3) policy set = **B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER**; (4) clean-vs-poisoned **paired by training_seed and victim plan**, poisoning is the sole stochastic difference; (5) no journal assets and **no broad model-level, aggregation-level, training-poisoning, evasion, privacy, or deployment claims** (CP2 *is* a calibration-robustness study; it claims nothing beyond the calibration channel).
> - **3 kill triggers:** no material `Δτ` for B2 at the largest fraction across the eligible-victim sweep; threshold shifts that produce no interpretable downstream movement; B1/B2/B4 indistinguishable even after blast-radius and spillover are measured.
> - **MVP matrix (locked):** N-BaIoT, {B1,B2,B4}, score-level proxy, fixed-size replacement, **victim-local** reservoirs, sources {RANDOM_BENIGN, HIGH_SCORE_BENIGN, LOW_SCORE_BENIGN}, objectives {raise, lower}, fractions {0, 0.10, 0.20, 0.40}, all **eligible** single-client victims, `training_seed=[0,1,2,3,4]`, `poisoning_seed=[100,101,102,103,104]`, no retraining if artifacts pass audit.

---

## 1. Executive Verdict

**Readiness grade: A as a research plan after incorporating three rounds of audit; ready for the Phase-A read-only audit now, but not for the Phase-B protocol lock or attack implementation until three Phase-A facts are confirmed against the codebase (artifact E-value, DATP bootstrap variant, B4 reproducibility).** The roadmap is scientifically viable and correctly conference-sized. Scope separation from DATP and the journal extension is enforced well. The core causal isolation (poison calibration content only; recompute thresholds; reclassify fixed clean test scores) is the strongest asset and survives reviewer attack. The round-3 patches were precision-only — reservoir source, the two-layer statistical unit, fully pre-registered triples, the formal B4 decomposition (including the StandardScaler-mediated effect), the locked `µ_floor` rule, the percentile-bootstrap default, and CPU-safe testing — none of which changed the paper's identity.

**What changed most substantially:**

1. **B4 under poisoning was re-specified, and the feedback's own fix was corrected.** Two feedback documents framed "frozen B4" as clustering on *clean* fingerprints with only within-cluster aggregation poisoned. That is the wrong threat model: in DATP, B4's fingerprint `[mean, std, skew, p95]` is computed from the *calibration* reconstruction errors (DATP.pdf, Sec. IV), so an attacker who poisons the calibration window perturbs the fingerprint too. CP2 therefore runs B4 **end-to-end on the poisoned calibration** through the *frozen DATP procedure* (k-means++, `n_init=10`, `max_iter=300`, `random_state=42`, StandardScaler, K=3 for Regime A), and decomposes B4's threshold change into a within-cluster-aggregation component and a cluster-reassignment component. "Frozen" means frozen *procedure and hyperparameters*, never a fixed cluster-to-device map. This both fixes the threat model and converts a liability into a finding (reassignment as a B4 spillover mechanism).

2. **The ε_cv dispute was resolved by deleting ε_cv.** One reviewer wanted `ε_cv = 0.001`, another `1e-6`, both "consistent with DATP." DATP does **not** use an ε stabilizer in CV(FPR); it reports `CV(FPR) = σ/µ` and guards the small-denominator case with **IQR(FPR)** and **max–min FPR** (DATP.pdf, Eq. 3 and surrounding text). CP2 inherits that exact guard instead of inventing a constant, and keeps FPR-range (one reviewer wanted it dropped) precisely because it is the documented small-denominator guard — load-bearing under threshold-raise attacks that push mean FPR toward zero.

3. **Calibration-pending victims were resolved more cleanly than the feedback proposed.** A calibration-pending client neither contributes to `τ_global` nor receives a personal/cluster threshold; poisoning its calibration set changes no threshold under B1/B2/B4. So such clients are not valid victims at all. CP2 sweeps **eligible clients only**. DATP reports zero calibration-pending clients in Regime A, and fixed-size replacement preserves `n_cal`, so on N-BaIoT the eligible set is the full 9 by construction.

4. **E=1 vs E=5 conflict was adjudicated.** Blueprint.md lists `E=5` (stale, pre-amendment); the published conference artifact (DATP.pdf) states `E=1`. CP2 inherits the **conference artifact**, so `E=1`, and artifact-provenance validation now hard-rejects any `E=5` score artifact.

5. **Threat model was mechanistically grounded and "novelty" was reclassified as a kill criterion** rather than a reviewer objection with a tidy fix.

**Residual risks:** the paper's value is contingent on a non-trivial empirical `Δτ` under the *gray-box* (not diagnostic) model; B4 reproducibility must be confirmed in Phase A before B4 is locked as a third protagonist; and one external dependency (venue deadline) gates the Full-vs-MVP cut order. None of these is blocking for starting Phase A (read-only audit).

---

## 2. Feedback Resolution Matrix

| Feedback / Concern | Validity | Risk | Required Roadmap Change | Status After Rewrite |
|---|---|---|---|---|
| C1 — Calibration-pending clients as victims undefined | Valid (but feedback's fix was partly wrong) | Critical | Victim sweep over **eligible clients only**; calibration-pending clients are not valid victims because they affect no threshold; replacement preserves eligibility; DATP reports zero pending in Regime A | Resolved (7.4, 7.7) |
| C2 — Multi-client targets not pre-specified | Valid | Critical (Full) | Pre-register: **all C(9,2) eligible pairs + `N_triples=20` triples** (dedicated `compromise_pattern_seed=400`, refined in round-3), not conditioned on MVP results | Resolved (7.6) |
| C3 — Threat model not mechanistically bounded | Valid | Critical (reviewer) | Commit to one grounding scenario: **compromised local calibration-curation (admission/retention over the benign calibration buffer)** on 1–3 clients; gray-box = local scoring with the broadcast AE | Resolved (7.3) |
| C4 — B4 "frozen map" semantics | Valid; feedback fix corrected | Critical | "Frozen" = frozen **procedure/hyperparameters**, re-run on **poisoned** fingerprints; add reassignment-vs-aggregation decomposition | Resolved + improved (7.5) |
| C5 — Reservoir feasibility breaks pairing | Valid | Critical (impl.) | Deterministic tail-widening 10→20→25%; cell INFEASIBLE if it fails **in any seed**, excluded from **all** seeds (balanced design) | Resolved (7.6, 7.7) |
| M1 — Title overclaims a net cost | Valid | Major | Manuscript title = policy-differentiated framing; "Price of Personalization" demoted to **internal codename** | Resolved (7.1) |
| M2 — ε_cv unspecified / conflicting values | Valid; both proposed values wrong | Major | Delete ε_cv; inherit DATP guard (σ/µ + IQR + max–min; µ_floor flag) | Resolved (7.8) |
| M3 — Bootstrap estimand unspecified | Valid | Major | 95% bootstrap CI on the **mean of paired seed-level deltas**, DATP-matched variant (verify percentile-vs-BCa in Phase A) | Resolved (7.9) |
| M4 — Inferential unit ambiguity | Valid; reject "anchor to clearest victim" | Major | Unit = **(victim, seed)** delta; aggregate claim requires a **pre-specified majority of eligible victims** at ≥4/5 sign consistency; no post-hoc victim selection | Resolved (7.9) |
| M5 — "Not enough novelty" miscategorized | Valid | Major | Move to **kill criteria**; remove from "objection-with-fix" framing | Resolved (7.13, Section 8) |
| M6 — Venue unspecified | Valid | Major | Lock **IEEE CNS** primary (characterization standard, defense optional); confirm deadline + backup pre-Phase-C | Resolved (7.1; pre-coding checklist) |
| m1 — AUROC-invariance defense weak | Valid | Minor | Structural restatement: AUROC = score ordering, invariant by construction, verifies stage isolation | Resolved (7.12) |
| m2 — FPR-range redundant | Partially valid; corrected | Minor | **Keep** as DATP small-denominator guard (not redundant); demote to dispersion-guard tier | Resolved (7.8) |
| m3 — B3 enum invites instantiation | Valid | Minor | Remove B3 from default `ThresholdPolicy` enum; appendix-only behind explicit flag | Resolved (7.10) |
| m4 — Trimmed-calibration undefined | Valid | Minor | Symmetric trim of top/bottom-t% of calibration errors, t∈{5,10}, report clean-setting regression | Resolved (7.6) |
| m5 — E=1 vs E=5 inheritance | Valid | Minor→correctness | Lock **E=1**; manifest hard-rejects E=5 artifacts | Resolved (7.7) |
| m6 — Two citations need primary verification | Valid | Minor | Mark Nguyen et al. and Kravchik et al. **verify-before-submission**; Kravchik distinction (online/training-time ICS, not calibration) must appear in the related-work sentence | Resolved (7.11) |
| Doc4 — Fairness vocabulary in security venues | Valid | Minor | Manuscript uses "per-device FPR disparity"/"alarm-burden predictability"; CV(FPR) math unchanged | Resolved (7.8, 7.13) |
| Doc5 — Smoke Invariant 6 conflates hypothesis with invariant | Valid | Minor | Reframe to a **measurability** invariant (B4 delta and decomposition computable), not "B4 between B1 and B2" | Resolved (7.10) |
| Doc5 — Relative-Δτ sign convention | Valid | Minor | State convention: `|τ_clean|` in denominator preserves numerator sign; ε numerical only | Resolved (7.8) |
| Doc5 — Document navigability (fast-read, kill criteria placement) | Valid | Minor | Fast-read header added; kill criteria cross-referenced in Section 1 and 8 | Resolved (header, Sections 1/8) |

**Round-3 feedback (audits of this rewrite).**

| Feedback / Concern | Validity | Risk | Required Roadmap Change | Status After Rewrite |
|---|---|---|---|---|
| R3-B1 — Reservoir source pool unspecified | Valid | Critical | Reservoirs are **victim-local**; `RANDOM_BENIGN` samples the victim's own benign pool (true null control); cross-client reservoirs are diagnostic-only (imply stronger access) | Resolved (7.6) |
| R3-B2 — Statistical unit still conflated (risk of treating 9×5 as 45 independent obs) | Valid | Critical | Two explicit layers: per-victim (5 seed deltas → sign consistency); policy-level (5 **seed-level aggregates**, each = mean paired delta over eligible-and-feasible victims) → bootstrap CI/sign test on the 5 | Resolved (7.9) |
| R3-B3 — Triples not fully pre-specified; seed collides with `split_seed` | Valid | Major | Lock `N_triples=20`, sampled without replacement from lexicographically sorted eligible triples with dedicated **`compromise_pattern_seed=400`** | Resolved (7.6) |
| R3-B4/N1 — B4 decomposition not formally defined; StandardScaler refit is a third mechanism | Valid | Major | Formal 2-component definition (aggregation vs churn-as-residual, summing to total); scaler refit folded into churn with an optional scaler-frozen sub-diagnostic | Resolved (7.5) |
| R3-B5/N3 — CICIoT2023 B4 K may change under poison | Valid | Major | For any stretch dataset, **K is selected once on clean condition and frozen** for all paired comparisons; poison may move assignments, not K | Resolved (7.4, FB4) |
| R3-M1/N4 — Premature "shows"/"collapse"/"minority" language | Valid | Major | Hypothesis-framed verbs pre-results; "TPR degradation" not "collapse"; "one to three" not "minority" | Resolved (header, 7.13, 9) |
| R3-M2 — "No robustness claims" contradicts identity | Valid | Major | Reworded to "no **broad** model/aggregation/training-poisoning/evasion/privacy/deployment claims" | Resolved (header, 6, 7.1, 7.14) |
| R3-M3 — Defense reporting selective | Valid | Major | Defense decided before Full; once run, **reported regardless of outcome** (appendix at minimum); may leave main narrative but not be hidden | Resolved (7.6) |
| R3-M4/N2 — µ_floor pre-spec gap, no rule | Valid | Major | `µ_floor = round(M_clean/8, 2 s.f.)`, `M_clean` = clean B1 eligible-client mean FPR from Phase-A artifacts, locked in the manifest before any **poisoned** run (≈0.005 at DATP's clean scale) | Resolved (7.8) |
| R3-M5 — GPU-only enforcement wrong for score-level | Valid | Major | GPU enforcement applies **only to the retraining fallback**; score-level smoke/MVP recomputation is CPU-safe and tests must not require CUDA | Resolved (7.10) |
| R3-Doc8 — Bootstrap-variant fallback unspecified; BCa not safe at n=5 | Valid | Major | Inherit DATP variant; if undocumented, **default to percentile** (stable at n=5); use BCa only if DATP used it or the smoke stage confirms n=5 stability | Resolved (7.9) |
| R3-Doc8 — B4 K-invariance not a smoke invariant | Valid | Minor | Added **Smoke Invariant 11**: K stays 3 on N-BaIoT, never silently data-adaptive | Resolved (7.10) |
| R3-m1 — Fallback IDs `F1..F4` collide with F1-score | Valid | Minor | Renamed **FB1–FB4** | Resolved (Section 4) |
| R3-m4 — `RANDOM_BENIGN` "near-null" needs a tolerance | Valid | Minor | Near-null = median `|Δτ_i|` below the materiality cutoff `δ_{τ,i}` **and** control effect < 0.25× the matched HIGH/LOW effect | Resolved (7.6) |

---

## 3. Design Choice Resolution Matrix

| Design Choice | Options Considered | Selected | Why Best | Rejected Alternatives (kept for defense/future) | Fallback Needed? |
|---|---|---|---|---|---|
| B4 behavior under poisoning | (a) cluster on clean fingerprints, poison only within-cluster aggregation; (b) re-run frozen procedure on poisoned fingerprints; (c) new clustering | **(b)** | Matches the DATP pipeline (fingerprint is computed from calibration errors); (a) understates B4 vulnerability and assumes an artificial clustering-before-poisoning timing; (c) is out of scope | (a) becomes a diagnostic decomposition component; (c) forbidden | Yes — if B4 procedure is not bit-reproducible from artifacts, downgrade/drop B4 |
| Victim set | all 9 devices vs eligible-only | **Eligible-only** | Calibration-pending clients affect no threshold; targeting them is a null by construction | — | No (eligible = 9 on N-BaIoT per DATP) |
| Dispersion stabilizer | invent ε_cv (0.001 / 1e-6) vs inherit DATP guard | **Inherit DATP guard** (σ/µ + IQR + max–min, µ_floor flag) | DATP has no ε; inventing one diverges from the inherited protocol and is itself a reviewer target | ε_cv constant | No |
| Local epochs | E=1 (conference) vs E=5 (Blueprint) | **E=1** | DATP.pdf is the published artifact CP2 inherits; E=5 is stale | E=5 | No (manifest enforces) |
| Inferential unit | per-seed averaged over victims vs (victim, seed) vs clearest-victim anchor | **(victim, seed)** with majority-of-victims aggregate | Preserves the client-heterogeneity story without post-hoc victim cherry-picking | clearest-victim anchor (post-hoc, rejected) | No |
| Attack input mode (MVP) | score-level proxy vs raw-sample | **Score-level proxy** | Cleanest causal isolation of the threshold stage; reuses artifacts; conference-scaled | raw-sample (stretch) | Yes — raw-sample pilot only if reviewers force realizability |
| Injection rule | fixed-size replacement vs append | **Fixed-size replacement** | Holds calibration cardinality constant, preventing a calibration-size confound | append (diagnostic-only) | No |
| Multi-client selection | exhaustive vs top-k-from-MVP vs pre-registered random | **Pre-registered (all pairs + seeded triple sample)** | Avoids post-hoc, p-hacking-equivalent victim selection; score-only cost is trivial | top-k-from-MVP (rejected) | No |
| Primary venue | IEEE CNS vs workshop vs top-tier security | **IEEE CNS** | DATP lineage; characterization paper acceptable; defense optional | top-tier security would force a mandatory defense (out of scope) | Confirm deadline (external) |
| Defense (Full) | omit vs trimmed-calibration vs taxonomy | **One trimmed-calibration, optional** | Lightweight; answers "no mitigation, no value" without exploding scope | robust aggregation / conformal defenses (journal) | No (omit if it erases the clean DATP gain) |

---

## 4. Fallback Register

Four fallbacks are genuinely feasibility-gated. All others were removed.

**FB1 — Clean score artifacts fail provenance audit.**
- Trigger: Phase-A manifest cannot confirm conference-faithful (E=1, T=40→150, DATP split semantics, control-repo origin) clean per-client calibration and test score arrays.
- Preferred: reuse audited clean score artifacts; no retraining.
- Fallback: one CP1-faithful retrain — exactly `E=1`, `rounds_initial=40`, `rounds_max=150`, same convergence criterion, FedAvg weighted by local benign size, Flower; write fresh score artifacts with a complete manifest.
- Why acceptable: the protocol is copied verbatim from the published conference artifact, not re-tuned, so the clean baseline remains DATP-equivalent.
- Weakened claim: none scientifically; only timeline cost rises.
- Safe wording if activated: "Clean baselines were reproduced under the published DATP conference protocol (E=1, identical round budget and convergence criterion); no hyperparameters were re-tuned for CP2."

**FB2 — Reservoir cannot supply m_i replacements within 25% tail mass.**
- Trigger: for some (client, fraction), the tail reservoir at 10%, widened to 20% then 25%, still cannot supply `m_i` distinct replacement scores in at least one training seed.
- Preferred: 10% tail; widen deterministically only as defined.
- Fallback: mark the (client, fraction) cell **INFEASIBLE**; exclude it from **all** seeds (balanced paired design); report per-client.
- Why acceptable: prevents seed-dependent attack parameters from contaminating the paired analysis; infeasibility is reported, not hidden.
- Weakened claim: the dose-response curve is truncated for that client; the cross-victim claim is unaffected.
- Safe wording: "For clients whose calibration tail could not supply the requested replacement budget without exceeding a 25% reservoir, the corresponding fraction is reported as infeasible and excluded from all seeds."

**FB3 — B4 procedure not bit-reproducible from artifacts.**
- Trigger: re-running the frozen DATP k-means procedure on the inherited clean fingerprints does not reproduce the DATP-reported B4 assignments (adjusted Rand index inconsistent with DATP's reported mean 0.79, range [0.64, 1.0]).
- Preferred: B4 runs end-to-end via the frozen procedure (selected design).
- Fallback: downgrade B4 to a **secondary diagnostic** (reported, not a third protagonist); if still unstable, drop B4 and run B1 vs B2 only, stating the constraint.
- Why acceptable: the core RQ (B1 vs B2 vulnerability profiles) survives without B4; B4 is the "middle ground," not the paper.
- Weakened claim: lose the intermediate-policy and cluster-spillover findings (RQ-B partial).
- Safe wording: "B4 results are reported as a secondary diagnostic; the primary policy contrast is B1 vs B2."

**FB4 — CICIoT2023 client semantics unsafe, or B4 K shifts under poison.**
- Trigger: dataset cards/processed artifacts do not expose a reproducible, documented pseudo-client partition (DATP's CICIoT2023 is a **file-level** 63-pseudo-client partition, not physical devices); **or** the silhouette-selected B4 K differs between the clean and poisoned conditions in the stretch regime.
- Preferred: include as an optional larger-corpus contrast, with **K selected once on the clean condition and frozen** for every clean/poisoned paired comparison (poison may move assignments, not K).
- Fallback: if client semantics are unsafe, drop CICIoT2023 entirely (N-BaIoT-only, narrowed external-validity claims); if only B4-K stability is the issue, drop B4 from the stretch regime and run B1/B2 there.
- Why acceptable: CICIoT2023 was never an MVP requirement; a K that changes under attack would convert the study into adaptive policy selection rather than calibration poisoning, which is out of scope.
- Weakened claim: external validity is single-corpus, or B4 is N-BaIoT-only.
- Safe wording: "Results are demonstrated on N-BaIoT physical-device clients; on the optional larger corpus, B4's cluster count is fixed from the clean condition so that poisoning alters assignments, not the policy definition."

---

## 5. Critical Fixes Applied

1. **B4 threat-model correction** (scientific validity + reviewer defense): poisoned fingerprints flow through the frozen clustering procedure; reassignment vs within-cluster-aggregation decomposition added.
2. **ε_cv removed; DATP small-denominator guard inherited** (scientific validity): prevents a divergence-from-protocol reviewer attack and an arbitrary-constant attack simultaneously.
3. **Eligible-only victim sweep** (validity): removes a null-by-construction confound and pre-empts "you attacked a client that has no personal threshold."
4. **E=1 locked + manifest enforcement** (correctness/reproducibility): blocks silent reuse of stale E=5 artifacts.
5. **(victim, seed) inferential unit with majority-of-victims aggregation** (claim safety): kills the cherry-picked-client attack without the post-hoc anchoring the feedback suggested.
6. **Pre-registered multi-client selection** (claim safety): closes a p-hacking-equivalent path before any result is seen.
7. **Deterministic, any-seed INFEASIBLE rule for reservoirs** (feasibility): preserves a balanced paired design.
8. **Mechanistically grounded gray-box threat model** (reviewer defense): "compromised local calibration curation + local scoring with the broadcast AE" makes gray-box realistic rather than oracle-like.
9. **Title and "fairness" vocabulary aligned to a security venue** (scope/claim safety): manuscript leads with per-device disparity / alarm burden; CV(FPR) math unchanged.
10. **B3 removed from the default enum; novelty risk elevated to a kill criterion** (scope discipline).

---

## 6. Non-Negotiable Locks

- **Scope:** calibration-channel poisoning only. Training data, model weights, aggregation, and test data are never the attack target. No **broad** model-level, aggregation-level, training-poisoning, evasion, privacy, deployment, or model-personalization claims. (CP2 *is* a calibration-robustness study; it makes no robustness claim beyond the calibration channel.)
- **Primary dataset:** N-BaIoT, one client = one physical device, K=9, all eligible.
- **Secondary/optional:** CICIoT2023 file-level pseudo-clients (stretch, FB4-gated). Edge-IIoTset forbidden.
- **Policies (enum, stable):** `B1_GLOBAL`, `B2_PERSONALIZED`, `B4_CLUSTER`. `B3` appendix-only, not in default enum.
- **Attacker objectives (enum):** `THRESHOLD_RAISE`, `THRESHOLD_LOWER`.
- **Source strategies (enum):** `RANDOM_BENIGN` (negative control), `HIGH_SCORE_BENIGN`, `LOW_SCORE_BENIGN`.
- **Reservoir source:** **victim-local** for all MVP/Full conditions (`RANDOM_BENIGN` samples the victim's own benign pool; HIGH/LOW draw the victim's own upper/lower tail). Cross-client reservoirs are diagnostic-only.
- **Injection rule:** `REPLACE_FIXED_BUDGET` (calibration cardinality constant); tail 10%→20%→25%→INFEASIBLE; a cell INFEASIBLE in any seed is excluded from all seeds.
- **Attack mode (MVP):** `SCORE_LEVEL_PROXY`; raw-sample is stretch only.
- **Poison fractions:** MVP `{0, 0.10, 0.20, 0.40}`; Full adds `0.05`.
- **Seeds:** `training_seed=[0,1,2,3,4]`; `poisoning_seed=[100,101,102,103,104]`; `analysis_seed=[300,301,302,303,304]`; `split_seed=[200,201,202,203,204]` only if new splits must be generated; `compromise_pattern_seed=400` for multi-client victim-set sampling (Full); `cluster_seed` unused (k-means is `random_state=42`).
- **Rounds (only if retraining):** `rounds_initial=40`, `rounds_max=150`, DATP convergence criterion.
- **Local epochs:** `E=1`. Manifest rejects E=5 artifacts.
- **Pairing:** clean and poisoned share the same training_seed, AE, test scores, split, and victim plan; poisoning is the only stochastic difference.
- **Calibration/eligibility:** `n_min=100` benign calibration samples; eligible-only victim sweep; calibration-pending clients excluded from CV(FPR) and from the victim set; fixed-size replacement preserves eligibility.
- **Dispersion metric:** `CV(FPR)=σ/µ` (no ε), guarded by `IQR(FPR)` and `max–min FPR`; `µ_floor = round(M_clean/8, 2 s.f.)` where `M_clean` is the clean B1 eligible-client mean FPR from Phase-A artifacts, locked in the manifest **before any poisoned run** (≈0.005 at DATP's clean FPR scale); below `µ_floor`, CV is flagged unstable and the absolute-dispersion metrics become primary.
- **Statistics (two layers):** per-victim = 5 paired seed deltas → ≥4/5 sign consistency (descriptive heterogeneity); policy-level primary inference = **5 seed-level aggregates**, each the mean paired delta over eligible-and-feasible victims → 95% bootstrap CI + exact sign test; the (victim, seed) deltas are **not** treated as 45 independent replicates. Bootstrap variant = DATP-matched; if undocumented, default **percentile** (stable at n=5), BCa only if DATP used it or smoke confirms n=5 stability. Holm within a pre-registered primary family. Aggregate claim needs a majority of eligible-and-feasible victims at ≥4/5.
- **Primary endpoint:** material threshold shift `Δτ` with correct sign **linked to** at least one downstream metric (victim ΔTPR for raise; ΔCV(FPR)/worst-client FPR for lower).
- **Secondary endpoints:** policy-differentiated blast radius and spillover; multi-client dose-response; optional trimmed-calibration defense.
- **Out of scope (explicit):** Edge-IIoTset; FedProx/FedRep/FedPer/Ditto; conformal thresholding; temporal recalibration; 10-seed journal regime by default; calibration-size sweeps; training/model/backdoor/evasion poisoning; live-device or latency/energy claims.
- **Venue:** IEEE CNS primary (characterization standard, defense optional); deadline + backup confirmed pre-Phase-C.
- **Working title (manuscript):** *Calibration-Channel Poisoning of Federated Threshold Personalization in IoT Anomaly Detection: A Policy-Differentiated Vulnerability Analysis.* Internal codename only: "The Price of Personalization."

---

## 7. Fully Updated Roadmap

### 7.1 Paper Identity

- **Working title (manuscript):** *Calibration-Channel Poisoning of Federated Threshold Personalization in IoT Anomaly Detection: A Policy-Differentiated Vulnerability Analysis.*
- **One sentence:** CP2 isolates the threshold-calibration set as an attack surface and measures whether contaminating only a few clients' benign calibration data shifts DATP-style thresholds enough to cause security or alarm-burden failures, and whether the B1/B2/B4 policies differ in vulnerability.
- **Relationship to DATP:** identical model family, FedAvg training (E=1), score artifacts, threshold policies, and N-BaIoT client definition. CP2 reuses DATP's clean pipeline as the unattacked baseline.
- **New vs DATP:** DATP has no adversary. CP2 introduces a calibration-only threat model, an attack on the threshold channel, and a fairness–robustness (per-device disparity vs detection) tradeoff under contamination — none of which exist in DATP.
- **Not part of the paper:** new FL algorithms, model personalization, aggregation variants, privacy mechanisms, training/model/test poisoning, deployment validation, journal datasets/comparators. No claim of robustness beyond the calibration channel is made or implied.
- **Why conference-sized:** one dataset (primary), one inherited model, three policies, two objectives, a small fraction grid, 5 seeds, score-level reuse, and an optional single defense.

### 7.2 Core Research Question

**Main RQ:** Does poisoning only the benign threshold-calibration set of one to three eligible clients shift DATP-style thresholds enough to induce interpretable downstream failures, and do B1/B2/B4 exhibit different vulnerability profiles?

**Secondary, testable:**
- RQ-A: Does calibration-only poisoning produce material, correctly-signed threshold shifts under the gray-box model?
- RQ-B: Do B1/B2/B4 differ in victim sensitivity and in cross-client spillover (blast radius, B4 reassignment)?
- RQ-C: Do raise vs lower attacks produce distinct failure modes (security harm vs alarm-burden/disparity)?
- RQ-D: Does impact scale from single to limited multi-client compromise?
- RQ-E (secondary): Can one trimmed-calibration defense reduce attack impact without erasing the clean-setting DATP benefit?

### 7.3 Threat Model

Three nested variants; main empirical claims use the gray-box variant only.

- **Attacker capability (main):** compromises the **local calibration-curation process** of 1–3 eligible clients (admission/retention control over which benign records enter the client's benign calibration buffer). Cannot alter training data, model updates, server aggregation, or test data.
- **Attacker goal:** raise or lower the victim's effective threshold to cause missed detections (raise) or excess/uneven false alarms (lower).
- **Attacker knowledge (main, gray-box):** local reconstruction scores of candidate calibration records. This is realistic because in FL each client holds the broadcast AE and can score candidates locally; gray-box access is not an oracle.
- **Poisoning location:** the victim client's benign calibration set, after training, before threshold computation.
- **Poisoning timing:** within the calibration window of the inherited clean run; no retraining is implied.
- **Victim/client targeting:** eligible clients only; MVP single-victim sweep over all eligible clients; Full adds pre-registered pairs/triples.
- **Cannot do:** modify the model, gradients, aggregation, server code, or test set; relabel test data; observe other clients' raw data.
- **Out of scope:** training-data poisoning, model poisoning, backdoors, evasion, Sybil/aggregation attacks.
- **Grounding scenario (committed):** a compromised local data collector / rogue device operator that selectively admits or retains benign-looking traffic into the calibration buffer of the victim device or its gateway.
- **Diagnostic upper bound (appendix only):** direct edits to the calibration **score array** with full score knowledge — used solely to distinguish "channel is intrinsically robust" from "attack instantiation too weak." Never used for main claims.

### 7.4 Experimental Regimes

Regime names are stable; CP2 reuses DATP's Regime-A construction and deliberately does **not** re-run DATP's Regime C severity sweep.

- **`REGIME_A_NBAIOT` (primary).** Purpose: main evidence. Dataset: N-BaIoT. Client construction: one physical device = one client, K=9. Eligibility: `n_cal ≥ 100` (DATP reports all 9 eligible in Regime A). Clean baseline: inherited clean per-client calibration/test score arrays under B1/B2/B4. Poisoned variants: {raise, lower} × {RANDOM, HIGH, LOW} × fractions, single-victim sweep over all eligible clients (MVP); pairs/triples (Full). Seeds: 5 paired (training 0–4 / poisoning 100–104). Rounds: unchanged (artifact reuse) or 40→150 if FB1 fires. Interpretation: per-victim and per-policy paired clean-vs-poisoned deltas.
- **`REGIME_STRETCH_CIC` (optional, FB4-gated).** Purpose: larger-corpus contrast. Dataset: CICIoT2023 file-level pseudo-clients (DATP partition: 63 pseudo-clients, near-homogeneous benign distributions). Client construction: documented file/chunk pseudo-clients only. Eligibility/calibration: only if CP2-safe artifact semantics exist. Clean baseline + reduced poisoned set (one or two best variants). Seeds: 3–5. Interpretation: contrast, **not** natural-client equivalence. **B4 K rule:** in the stretch regime, the silhouette-selected K is chosen **once on the clean condition and frozen** for every clean/poisoned paired comparison, so poisoning can move cluster assignments but never the cluster count (FB4); if K cannot be held stable, B4 is dropped from the stretch regime and only B1/B2 are run there.

A `REGIME_SMOKE_SYNTHETIC` (synthetic score arrays) precedes both for invariant validation (7.10).

### 7.5 Baselines and Comparators (Threshold Policies)

| Policy | Meaning in CP2 | Tests | Supports claim | Cannot prove |
|---|---|---|---|---|
| `B1_GLOBAL` | single shared threshold = simple arithmetic mean of eligible clients' `p95` thresholds (DATP B1) | spillover via shared-pool contamination | broad but diluted blast radius | localized victim sensitivity |
| `B2_PERSONALIZED` | per-client `p95` threshold (DATP B2); the attacked mechanism | high local victim sensitivity, near-zero spillover | victim-level fragility of personalization | cross-client spillover |
| `B4_CLUSTER` | cluster-mean threshold via the **frozen DATP procedure** run on (possibly poisoned) fingerprints | intermediate sensitivity + cluster spillover + reassignment | middle-ground tradeoff and a distinct spillover mechanism | a clustering-quality result |

**B4 specification (locked).** Fingerprint `v_i = [mean(E_i), std(E_i), skew(E_i), p95(E_i)]` from the (possibly poisoned) calibration errors; StandardScaler-normalized; k-means++ `n_init=10`, `max_iter=300`, `random_state=42`, **K=3** (Regime A). `τ_c` = arithmetic mean of eligible clients' `τ_i` within the cluster. "Frozen" = this exact procedure/hyperparameter set, **not** a fixed cluster-to-device map.

**B4 decomposition (formal, locked).** Let `A_clean`, `S_clean` (StandardScaler), and `τ_c^clean` come from the clean fingerprints. For a poisoned condition:
- **Component 1 — within-cluster aggregation.** Hold `A_clean` and `S_clean` fixed; recompute each `τ_i` from the poisoned calibration and re-average within the frozen clusters → `τ_c^agg`. Define `Δτ_agg = τ_c^agg − τ_c^clean`.
- **Total.** Run the full frozen procedure on the poisoned fingerprints — **refit StandardScaler** (`S_pois`), re-run k-means (`random_state=42`, K=3) → `A_pois`, `τ_c^pois`. Define `Δτ_total = τ_c^pois − τ_c^clean`.
- **Component 2 — churn (residual).** `Δτ_churn = Δτ_total − Δτ_agg`. By construction the two components sum exactly to the total; report both **signed** (they may oppose) plus the total. Churn bundles cluster reassignment and the normalization-mediated effect (one poisoned fingerprint shifts `S_pois`, perturbing non-victim standardized coordinates and thus assignments) — this is logged as part of B4 spillover.
- **Optional sub-diagnostic.** If `|Δτ_churn|` is material, re-cluster the poisoned fingerprints with the scaler frozen at `S_clean`; the gap between that and the full `S_pois` run isolates the pure normalization-mediated component. No new clustering method is introduced anywhere.

### 7.6 Attack Variants

Common contract: for client `i`, clean benign calibration scores `S_i^cal` and fixed clean test scores `S_i^tst`. For each policy compute clean threshold from `S_i^cal` and poisoned threshold from the contaminated calibration. Model, test scores, and labels are unchanged. Only calibration content changes: (1) start from clean artifacts; (2) contaminate calibration scores; (3) recompute thresholds (including B4 re-clustering); (4) reclassify unchanged test scores; (5) compare.

**Injection (`REPLACE_FIXED_BUDGET`).** For poison fraction `f>0` on a victim with `n_i` calibration scores, `m_i = max(1, round(f·n_i))`. Replace `m_i` randomly chosen positions (`poisoning_seed`) with values drawn from the source reservoir; total size stays `n_i`. This holds cardinality constant, isolating *content* contamination.

**Source strategies (score-level, victim-local).** All reservoirs are drawn from the **victim client's own** benign score pool; cross-client reservoirs are diagnostic-only because they imply stronger attacker access than the gray-box model grants.
- `RANDOM_BENIGN` — negative control: replacements drawn uniformly from the **victim's own** benign score pool, so composition drifts without shifting the distribution's shape. Pre-registered near-null criterion: median `|Δτ_i|` below the materiality cutoff `δ_{τ,i}` **and** the control effect below 0.25× the matched HIGH/LOW effect at the same fraction. Detects pipeline bugs/confounds. (A global benign pool is forbidden in MVP because device heterogeneity would make even "random" replacement shift the threshold, destroying the control.)
- `HIGH_SCORE_BENIGN` (raise): replacements from the victim's **own** upper-tail reservoir → threshold rises → victim TPR degrades; FPR flat/down. Failure mode: tail too weak to move the quantile.
- `LOW_SCORE_BENIGN` (lower): replacements from the victim's **own** lower-tail reservoir → threshold lowers → victim FPR rises, dispersion worsens. Failure mode: reservoir too concentrated.

**Reservoir + INFEASIBLE rule (locked).** Tail width starts at **10%**; if it cannot supply `m_i` distinct replacements, widen deterministically to 20% then 25%, logging the step. Tail-widening is determined from the **clean** per-client distribution; a (client, fraction) cell that would exceed 25% **in any training seed** is marked **INFEASIBLE** and excluded from **all** seeds, keeping the paired design balanced. (Unlikely to bind on N-BaIoT, whose per-device calibration sets are large, but it binds the protocol.)

**Target scopes.** MVP: `SINGLE_CLIENT`, sweeping all eligible victims per seed. Full: `MULTI_CLIENT` = **all C(9,2) eligible pairs** + **exactly `N_triples=20` triples** sampled without replacement from the lexicographically sorted eligible triples using a dedicated **`compromise_pattern_seed=400`** (distinct from `split_seed=[200..204]`; selection not conditioned on MVP results). Diagnostic: `ALL_CLIENTS_DIAGNOSTIC_ONLY`. (Score-level cost is trivial, so exhaustive triples are available on request, but the pre-registered set is fixed at 20.)

**Defense (Full, optional, `TRIMMED_CALIBRATION`).** Before percentile computation, symmetrically trim the top-`t%` and bottom-`t%` of calibration reconstruction errors, `t∈{5,10}` pre-specified. The defense is decided **before** Full begins; once run, it is **reported regardless of outcome** (appendix at minimum). Report (a) poisoned-vs-defended recovery and (b) **clean-setting regression** (whether trimming erodes DATP's clean fairness gain). It may be excluded from the main narrative if it fails, but it is never hidden.

**Safety boundary:** all attacks operate on benign calibration content; none touches training, aggregation, or test stages; no claim of raw-traffic realizability from score-level results.

### 7.7 Calibration and Eligibility Rules

- **Calibration set:** benign-only holdout, inherited from DATP's N-BaIoT chronological split (60% train / gap / 20% calibration / gap / ~19% test), per device.
- **Benign-only assumption:** thresholds are computed from benign calibration scores; attack labels never enter calibration.
- **Minimum samples:** `n_min=100`. Below → calibration-pending.
- **Calibration-pending clients:** receive `τ_global`, do **not** contribute to `τ_global`, do **not** enter B4 clustering, and are excluded from CV(FPR). Therefore they affect no threshold and are **not valid victims**; excluded from the victim sweep.
- **Effect of attacks on eligibility:** fixed-size replacement preserves `n_i`, so eligibility is preserved; no client becomes pending due to the attack.
- **Paired analysis:** because the eligible set is fixed and replacement preserves it, every (victim, seed) clean-vs-poisoned pair is balanced.
- **Fallback threshold behavior:** the only fallback threshold in scope is DATP's existing `τ_global` for calibration-pending clients; CP2 introduces none.
- **Artifact provenance (manifest must confirm before reuse):** control-repo origin (not journal); conference protocol with **E=1**; exact checkpoint/round; DATP train/calibration/test semantics; per-client calibration scores present; clean test scores present; no journal-only threshold variants; safe read-only paths. **Any E=5 artifact is rejected.**

### 7.8 Metrics

Let `i` index clients, `p` index policies.

- **Primary endpoint — threshold mechanism + downstream link:** `Δτ_{i,p} = τ^pois − τ^clean`; `|Δτ|`; relative `Δτ_rel = (τ^pois − τ^clean)/max(|τ^clean|, ε)` (denominator uses `|τ^clean|` so the **numerator sign is preserved**; ε is a numerical stabilizer only). A primary claim requires `Δτ` with correct sign **and** movement in at least one downstream metric.
- **Secondary endpoints:** victim `ΔTPR` (raise), `ΔBA`, `ΔMacroF1`, `ΔP10-ClientF1`.
- **Fairness / disparity metrics (manuscript term: "per-device FPR disparity"):** `CV(FPR)=σ/µ` over eligible clients (**no ε**); `IQR(FPR)` and `max–min FPR` as small-denominator guards; when `µ_FPR < µ_floor`, CV is flagged unstable and the absolute-dispersion metrics become primary for that condition. **`µ_floor` rule (locked):** `µ_floor = round(M_clean/8, 2 significant figures)`, where `M_clean` is the clean B1 eligible-client mean FPR computed from Phase-A artifacts; it is fixed and written to the protocol manifest **before any poisoned run** (≈0.005 at DATP's clean FPR scale), so the flag is data-derived but never contingent on poisoned results. `WorstClientFPR = max_i FPR_i`; `ΔCV(FPR)`.
- **Robustness metrics:** victim `ΔTPR`, `ΔBA`, worst-client metrics under raise.
- **Utility metrics:** `MacroF1`, `BA` deltas (aggregate; flagged as potentially masking victim-level harm).
- **Attack-success metrics:** material scale `δ_{τ,i}=0.1·IQR(S_i^{cal,clean})`; `ASR_raise = mean 1[Δτ ≥ δ]`, `ASR_lower = mean 1[Δτ ≤ −δ]` over attacked (victim, seed) pairs.
- **Diagnostic metrics:** `BlastRadius_p = (1/|K_elig|) Σ 1[|Δτ_i| ≥ δ_i]`; `SpilloverCount_p = Σ_{i ∉ compromised} 1[|Δτ_i| ≥ δ_i]`; B4 reassignment count; `AUROC` on fixed clean test scores (invariant by construction — see 7.12).

**Interpretation rule (locked):** because a raise attack can lower FPR while lowering TPR, no single fairness metric tells the whole story; CP2 jointly reports `Δτ`, victim `ΔTPR`, and FPR dispersion. Raise-attack narrative is anchored on victim TPR/BA; lower-attack narrative on worst-client FPR / `ΔCV(FPR)`.

### 7.9 Statistical Plan

- **Two-layer unit of analysis (locked).** Layer 1 (per-victim evidence): for each victim, the 5 paired seed deltas drive sign consistency and descriptive client heterogeneity. Layer 2 (policy-level inference): for each policy×objective×fraction, form **one seed-level aggregate per seed** = the mean paired delta over all eligible-**and-feasible** victims, yielding 5 aggregates; primary CIs and tests operate on these 5. The 9×5 (victim, seed) deltas are **never** treated as 45 independent replicates.
- **Paired comparisons:** clean vs poisoned, matched on training_seed and victim plan.
- **Sign consistency:** per victim, a directional effect must hold in **≥4/5 seeds**.
- **Aggregate claim rule (no post-hoc victim selection):** an RQ-A/RQ-B claim requires the directional effect to hold for a **pre-specified majority of eligible-and-feasible victims** (≥⌈m/2⌉ of the `m` such victims; m=9 on N-BaIoT absent infeasibility) at ≥4/5 sign consistency; the all-victim sweep is the evidence base, and the victim with the largest effect is **not** used to anchor the claim.
- **Confidence intervals:** 95% bootstrap CI on the **mean of the 5 seed-level aggregates** (Layer 2), using the **same bootstrap variant as the DATP conference implementation** (confirm percentile vs BCa in Phase A). If the DATP variant is undocumented, **default to the percentile bootstrap**, which is the stable choice at n=5; BCa is used only when DATP used it or the smoke stage confirms BCa is stable at n=5 (BCa can be anti-conservative at this sample size and is not adopted by default).
- **Hypothesis test:** exact paired sign test as the default for the small-n primary family; effect magnitude and sign consistency carry the evidence, not p-values alone.
- **Effect sizes:** report median paired delta and bootstrap CI for every primary comparison.
- **Multiple comparisons:** Holm correction **within a pre-registered primary family only** — {N-BaIoT; B1/B2/B4; single-victim; HIGH→raise; LOW→lower; fractions 0.10/0.20/0.40}. Everything else is secondary/descriptive.
- **Negative-result handling:** if the primary family fails the aggregate rule, the kill/pivot path (Section 8, 7.13) activates; a bounded-vulnerability or null result is reported honestly, not reframed.
- **Move to 10 seeds only if:** sign consistency is borderline, seed variance is large, the B1/B2/B4 ordering flips across seeds, or the central claim rests on an unstable effect.
- **Claim fallback wording (post-result):** see 7.13.

### 7.10 Implementation Plan (no code)

- **Repository:** `/home/naslouby/Projects/datp-calibration-poisoning`, isolated from control and journal repos. `data/raw` → `…/datp-shared-data/raw` (read-only). Outputs only under `outputs/conference_calibration_poisoning/`.
- **Enums (stable):** `ThresholdPolicy = {B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER}` (B3 **excluded** from the default enum; appendix-only behind an explicit CLI flag); `AttackerObjective = {THRESHOLD_RAISE, THRESHOLD_LOWER}`; `PoisoningSourceStrategy = {RANDOM_BENIGN, HIGH_SCORE_BENIGN, LOW_SCORE_BENIGN}`; `CalibrationInjectionRule = {REPLACE_FIXED_BUDGET}` (append diagnostic-only); `PoisoningKnowledge = {GRAY_BOX_SCORE_ACCESS}` main, `WHITE_BOX_DIAGNOSTIC_ONLY` appendix; `PoisoningTargetScope = {SINGLE_CLIENT, MULTI_CLIENT, ALL_CLIENTS_DIAGNOSTIC_ONLY}`; `PoisoningDefense = {NONE, TRIMMED_CALIBRATION}`; `ExperimentScale = {SMOKE, MVP, FULL, STRETCH}`; `AuditDisposition = {KEEP_CORE, REFACTOR_CORE, QUARANTINE_JOURNAL, REMOVE_STALE, BLOCK_UNSAFE}`.
- **Module responsibilities:** attack-config parsing; calibration poisoning injector (no in-place mutation of clean arrays); threshold recomputation (B1/B2/B4 including B4 re-clustering + decomposition); paired clean-vs-poisoned metric comparison; artifact-manifest validation (incl. E=1 enforcement); synthetic-smoke harness.
- **Orchestration:** stage-scoped configs (`common`, `audit_readonly`, `nbaiot_smoke`, `nbaiot_mvp`, `nbaiot_full`, `ciciot2023_stretch`, `paper_figures`). Run-path: `…/<scale>/<dataset>/<policy>/<objective>/<source>/f_<fraction>/scope_<scope>/train_<seed>/poison_<seed>/`.
- **Logging/artifacts:** MLflow tracking; manifests `project_audit_report.json`, `clean_score_artifacts.json`, `nbaiot_mvp_manifest.json`, `paper_figure_manifest.json`.
- **Reproducibility:** `PYTHONHASHSEED=0`; seed Python/NumPy/PyTorch CPU+GPU/dataloader/split/poison-selection/bootstrap; clean and poisoned differ only by the poisoning intervention.
- **Tests:** the smoke invariants below; determinism (same seeds → identical outputs); no-in-place-mutation; output isolation to temp during smoke. **Compute:** score-level smoke/MVP threshold recomputation is **CPU-safe**; tests must **not** require CUDA. GPU-only enforcement via `pytest.fail()` applies **only to the FB1 retraining path**, never to the score-level pipeline.
- **Validation gates:** Phase-A audit pass → protocol lock → smoke pass → MVP result audit → Full.

**Smoke invariants (synthetic, locked):** (1) `f=0` → zero `Δτ`; (2) `RANDOM_BENIGN` → near-null; (3) `HIGH_SCORE_BENIGN` raises B2 thresholds; (4) `LOW_SCORE_BENIGN` lowers B2 thresholds; (5) B1 victim shift < B2 victim shift under the same single-client attack; (6) **B4 threshold delta and the within-cluster/reassignment decomposition are computable and finite** (measurability invariant — *not* "B4 lies between B1 and B2," which is a scientific hypothesis); (7) AUROC on unchanged test scores invariant; (8) clean calibration arrays never mutated in place; (9) reproducibility; (10) outputs in temp only; (11) **B4 K stays fixed at 3 on N-BaIoT** under both clean and poisoned conditions — the procedure is never silently overridden to a data-adaptive K (distinct from Invariant 6).

### 7.11 Analysis and Figures

- **Tables:** T1 threat-model summary (minimal/main/diagnostic); T2 experiment matrix; T3 dataset & client summary (why N-BaIoT primary; CICIoT2023 cautions); T4 main results (clean vs poisoned per policy, mechanism + one downstream metric, split into a raise panel and a lower panel); T5 reviewer-safe claims↔evidence; T6 failure/pivot interpretation (appendix if tight).
- **Figures (with the outline mapping below):** F1 system + attack surface (calibration is the only manipulated stage); F2 calibration-poisoning mechanism (fixed-size replacement in score space; caption must say it models calibration-set *composition*, not direct score editing); F3 `Δτ` vs fraction per policy/objective (main mechanism); F4 `ΔCV(FPR)`/worst-client FPR vs fraction (lower-attack disparity); F5 B1/B2/B4 vulnerability profile (victim `|Δτ|`, blast radius, spillover, B4 reassignment); F6 victim `ΔTPR` vs worst-client `ΔFPR` (failure-mode separation).
- **Outline↔figure map:** Intro→F1,T1; Background→F2; Policies→T2(policies); Threat model→T1; Attacks→F2,F3; Setup→T2,T3; Results→F3–F6,T4; Discussion→F5/F6,T5/T6.
- **Diagnostic plots:** AUROC-invariance check; B4 reassignment heatmap (appendix).
- **Ablations:** fraction grid; trimmed-calibration (Full); diagnostic upper bound (appendix).
- **Appendix:** infeasible (client, fraction) report; eligibility/coverage per seed; diagnostic-upper-bound results; B4 decomposition.
- **Each artifact proves:** F3 = channel is real; F4 = lower-attack disparity harm; F5 = policy-differentiated profiles; F6 = distinct failure modes; T4 = the headline numbers; T5/T6 = claim discipline under positive/mixed/negative outcomes.

### 7.12 Reviewer Risk Register

| Reviewer attack | Why dangerous | Roadmap defense | Residual risk | Safe wording |
|---|---|---|---|---|
| "Just data poisoning." | generic framing | calibration *channel* is structurally distinct from the training pipeline; analog to conformal-calibration contamination (Scholten & Günnemann; Bashari et al.) imported into FL-IoT AD for the first time | Low–Med | "We attack the threshold-calibration set, not training, aggregation, or test data." |
| "Threat model unrealistic." | calibration access feels niche | committed grounding scenario (compromised local calibration curation); gray-box = local scoring with the broadcast AE | Med | "An adversary controlling local calibration admission can score candidates with the locally held model." |
| "Gray-box is an oracle." | score access sounds strong | FL clients already hold the model; diagnostic upper bound kept out of main text | Med | "Local scoring is a property of FL, not an additional assumption." |
| "Score-level proxy is abstract." | realizability | exact stage isolation + AUROC invariance; raw-sample stretch | Med | "Score-level poisoning isolates the calibration stage; raw-traffic realization is future work." |
| "AUROC doesn't change → trivial." | misreads threshold papers | **AUROC measures score ordering; score-level recalibration cannot change ordering, so invariance verifies stage isolation — the object is the operating point, not score geometry** | Low | "AUROC invariance is the expected sanity check for a threshold-only intervention." |
| "B2-most-vulnerable is obvious." | intuition | claim is *policy-differentiated profiles*; measure blast radius, spillover, B4 reassignment | Low | "Personalization concentrates victim sensitivity; shared/cluster policies trade it for spillover." |
| "B4 is arbitrary." | clustering looks ad hoc | frozen DATP procedure (random_state=42, K=3); no new clustering | Low–Med | "B4 reuses the DATP clustering procedure unchanged." |
| "Only one dataset." | external validity | N-BaIoT natural device clients; optional CIC contrast | Med | "We demonstrate the mechanism on physical-device clients; broader corpora are future work." |
| "Only 5 seeds / weak stats." | small n | paired (victim,seed) design, sign test, bootstrap CI, ≥4/5 + majority-of-victims rule | Med | "Evidence is seed-level consistency, not high-powered significance." |
| "No defense." | security venues | optional trimmed-calibration (Full) with clean-regression report | Med | "A lightweight trimmed-calibration defense partially mitigates the lower attack." |
| "Overlap with DATP." | same model/policies | adversary + channel are new; no DATP mechanism re-run | Med | "CP2 adds an adversary to DATP's clean pipeline." |
| "Results depend on one client." | 9-client set | eligible-victim sweep + majority-of-victims aggregate rule | Med | "The claim requires a majority of eligible victims, not a single device." |
| "Fairness ≠ security." | conceptual | manuscript uses per-device disparity / alarm burden; victim TPR foregrounded for security | Low | "Disparity is one operational consequence; detection harm is reported separately." |

### 7.13 Claim Discipline

- **If positive:** "Poisoning only the benign calibration set of one to three eligible clients shifts DATP-style thresholds materially under a gray-box adversary, with policy-differentiated profiles; raise attacks degrade victim detection while lower attacks degrade per-device FPR disparity."
- **If mixed:** foreground the objective/policy that works; "Under the tested settings, [raise/lower] produced consistent [security/disparity] harm, while [the other] was bounded." Report blast radius/spillover descriptively.
- **If negative:** "Under the tested gray-box settings and fractions, calibration-only poisoning did not produce material threshold shifts; the calibration channel appears robust to composition-only contamination in this protocol" — paired with the diagnostic-upper-bound result to localize the cause. Trigger the pivot ranking.
- **Never claim:** first poisoning work in FL-IDS; B2 universally worst; broad FL robustness; privacy/DP guarantees; deployment readiness; raw-traffic realizability from score-level results; significance from tiny unpaired samples.
- **Novelty is a kill criterion, not an objection:** if the work cannot be defended as a calibration-channel contribution distinct from generic poisoning, pivot per Section 8 rather than weakening wording.

### 7.14 Out-of-Scope Boundary

Edge-IIoTset; FedProx/FedRep/FedPer/Ditto; conformal thresholding; temporal recalibration; default 10-seed journal regime; calibration-size sweeps; model-level personalization; training-data/model/backdoor/evasion poisoning; secure-aggregation/robust-aggregation baselines; live-device, latency, or energy claims; client-definition-realism, dropout, DP-noise, cold-start, and alert-burden as *primary* studies (these remain pivots/discussion only). The Laridi-style comparator and B-FedStatsBenign are journal-reserved and excluded.

### 7.15 Execution Checklist

- **Pre-coding:** confirm venue + deadline (gates cut order); confirm clean score-artifact provenance (E=1, T=40→150, split semantics, control-repo origin); confirm B4 procedure reproduces DATP assignments; confirm bootstrap variant; surface CP1 calibration/test split semantics; confirm CICIoT2023 client semantics (or pre-drop).
- **Coding:** implement injector (no in-place mutation), B1/B2/B4 recompute + B4 decomposition, manifest validation (E=1 reject), synthetic smoke; B3 absent from default enum.
- **Experiment:** smoke invariants pass → MVP (eligible-victim sweep, fractions, paired seeds) → result audit before Full.
- **Post-experiment:** per-victim sign consistency; majority-of-victims aggregate; bootstrap CIs; INFEASIBLE-cell report; eligibility/coverage per seed; B4 decomposition; AUROC-invariance check.
- **Paper-writing:** raise/lower narrative split; per-device-disparity vocabulary; T5 claims↔evidence; verify Nguyen et al. and Kravchik et al. against primaries (Kravchik = online/training-time ICS, distinct from calibration); related-work nearest-neighbor distinctions; limitations (score-level proxy, N-BaIoT age, 9 clients, no deployment).
- **Final audit:** terminology/enum/regime/metric consistency; no journal asset; manifests complete; claims match results tier.

---

## 8. Residual Risk Audit

**Critical (watch, not blocking):**
- The paper's existence depends on a non-trivial `Δτ` under the **gray-box** model across a majority of eligible victims. If only the diagnostic upper bound moves thresholds, kill criterion #4 fires → pivot.
- B4 reproducibility (FB3): if the frozen procedure does not reproduce DATP's assignments, B4 must be downgraded before the protocol lock, not after.

**Major:**
- **Novelty defensibility** (now a kill criterion): if hostile review collapses CP2 to "generic poisoning," pivot to client-definition sensitivity (rank 1).
- **CICIoT2023 client semantics** (FB4): if unsafe, drop; do not let it become a client-realism sub-paper.
- **Venue/deadline** external dependency: gates the Full-vs-MVP cut and the defense decision.

**Minor:**
- `µ_floor` is now a locked rule (`round(M_clean/8, 2 s.f.)` from clean Phase-A artifacts, before any poisoned run); the only residual action is to record the computed value in the manifest.
- Multi-client table density (compute is trivial; presentation is the constraint) — keep pairs/triples in appendix unless they change the story.
- Citation verification (Nguyen, Kravchik) before submission.

**Blocking?** No risk blocks Phase A (read-only audit). The first three pre-coding confirmations (artifact E-value, bootstrap variant, B4 reproducibility) must close before the Phase-B protocol lock.

**Watch during implementation:** in-place mutation of clean arrays; seed-dependent reservoir widening; any E=5 artifact slipping through; B4 re-clustering silently changing K on N-BaIoT (it must not — K=3 is fixed); scope creep from pivots/discussion into the main matrix.

---

## 9. Final Readiness Verdict

- **Ready for a coding agent?** Almost. The agent can begin the **Phase-A read-only audit immediately** (inventory, contamination scan, artifact-provenance and E=1 check, B4-reproducibility check, path safety). It should **not** implement attacks or run experiments until Phase-A closes and the three pre-coding confirmations (artifact E-value, bootstrap variant, B4 reproducibility) are resolved, after which Phase B (protocol lock) and the synthetic smoke can proceed.
- **Ready as a research plan?** Yes. The design is scientifically defensible, conference-sized, internally consistent, and pre-specified before any result inspection.
- **Verify first:** (1) clean score-artifact provenance under E=1; (2) DATP bootstrap variant (percentile vs BCa); (3) B4 procedural reproducibility; (4) venue deadline.
- **Strongest contribution claim that would be defensible if the primary endpoint is met:** *CP2 introduces and empirically isolates a calibration-channel poisoning threat for DATP-style federated IoT anomaly detection — contaminating only one to three eligible clients' benign threshold-calibration sets, with training, aggregation, and test data clean — and characterizes whether the threshold-personalization policies (B1/B2/B4) exhibit distinct vulnerability profiles, with raise and lower attacks inducing separable security-detection and per-device-disparity failure modes.* This is the *target* claim; the verb "shows" is earned only after the primary endpoint (material `Δτ` linked to a downstream metric across a majority of eligible victims under the gray-box model) is met. All stronger phrasings (universal B2 fragility, broad FL/model robustness, deployment, privacy) remain out of bounds; by design, this paper's scope does not reach them.