# CP2 Paper Notes (Consolidated)

Append manuscript-relevant evidence as it is produced. Each note records:
**claim enabled / claim blocked / limitation / figure-table / reviewer-risk /
do-not-claim** with an **evidence path**. CP2-T058 consolidates and audits these.

> A claim is only writable if it is traceable to a real evidence path. Phase 00
> notes are scope/boundary reminders, not results.

---

## CP2-T002 — Additional_Docs alignment (scope & boundary seeds)

### Claims CP2 may build on (DATP conference identity, reuse)

- **DATP substrate is N-BaIoT physical-device federated AE anomaly detection**
  (Rey et al. lineage; Claims.md P003). CP2 reuses the fixed encoder, FL split, and
  per-client benign calibration scores — poisoning is the *only* added variable.
- **B1 (global) vs B2 (personalized) vs B4 (cluster) threshold policies** and
  **CV(FPR)** as the personalization-dispersion metric are DATP-owned and reused.
- Evidence path: `docs/DATP_CP_Roadmap.md`, `Additional_Docs/Synthesis/Claims.md`.

### Claims CP2 must NOT restate or make (do-not-claim list)

- **No privacy/DP claim.** Every corpus paper (P001-C4, P002-C3, P003-C7, P004-C4,
  P034-C2, P035-C4, P039-C3, P040-C3) lacks formal privacy; CP2 adds no privacy
  mechanism and must not imply one. (`Claims.md` privacy-gap pattern.)
- **No deployment / on-device / hardware-overhead claim** (P005/P036/P037/P040
  hardware gaps). CP2 runs on saved artifacts; it is not a deployment study.
- **No broad FL-robustness or generic-poisoning claim.** CP2 is *calibration-
  channel* poisoning only — never training-data, model-weight, aggregation, or
  test-data poisoning (contrast P003-C4/C5 model-poisoning, P036/P037 defenses).
- **No "first work" / novelty-supremacy overclaim.** Frame as a focused,
  policy-differentiated calibration-channel vulnerability analysis.
- **No evasion / backdoor claim.** Out of scope.

### CP2 / journal boundary (must NOT import)

Forbidden imports from `Additional_Docs/Journal/Journal_Extension_Master_Roadmap.md`
(context-only): **Edge-IIoTset**, **FedProx / Ditto / FedRep / FedPer / Laridi /
B-FedStatsBenign** comparators, **conformal thresholding**, **temporal
recalibration**. CICIoT2023 is stretch-only and FB4-gated.

### Reviewer-risk reminders (carry into analysis & paper)

- **Statistics unit:** never treat 9×5 victim-seed deltas as 45 independent
  samples; use seed-level aggregates; bootstrap CI on the 5 seed-level aggregates;
  sign test supporting only; Holm descriptive only.
- **Coverage:** always report coverage ratio alongside `CV(FPR) = σ/µ` (no ε).
- **AUROC invariance:** test scores are unchanged by calibration-channel attack →
  AUROC must be reported as invariant (sanity check, not a result).
- **B4 deltas** are client-indexed effective-threshold deltas; never compare raw
  k-means label IDs across runs.
- Evidence path: `Additional_Docs/Synthesis/Gap & Limitation Ledger.md`,
  `docs/DATP_CP_Roadmap.md` §14–§15.

---

## CP2-T012 — Statistics & reporting reuse

- **Claim enabled (future):** Bootstrapped 95% CI on 5 seed-level aggregates
  (percentile or BCa); sign-consistency ≥4/5 as supporting evidence; Holm
  p-values descriptive only.
- **Reviewer-risk:** Two-layer unit of analysis — policy-level inference uses 5
  seed-level aggregates, NOT 9×5=45 independent samples. Must be stated explicitly.
- **Do-not-claim:** Do not claim Wilcoxon or Holm results are primary; they are
  supporting/descriptive only.
- **Evidence path:** `_ai_tracking/audits/CP2-T012_statistics_reporting_audit.md`

---

## CP2-T011 — B4 procedure reuse

- **Claim enabled:** "B4 clustering procedure is identical to the DATP conference
  implementation (K=3, k-means++, n_init=10, random_state=42, StandardScaler
  fingerprint [mean, std, skew, p95])."
- **Reviewer-risk:** Reviewer may ask how we can claim B4 clusters are comparable
  across poisoned/clean conditions when k-means labels permute. Response: all deltas
  are client-indexed effective thresholds, never raw label IDs. The decomposition
  (Δτ_agg + Δτ_churn) captures the reassignment effect separately.
- **Do-not-claim:** Do not claim the DATP cluster quality result; CP2 uses B4 for
  threshold derivation, not as a clustering quality result.
- **Evidence path:** `_ai_tracking/audits/CP2-T011_thresholding_b4_audit.md`

---

## CP2-T008 — Split semantics & reservoir path

### Limitation to disclose

- **Limitation:** Score-level proxy abstraction: reservoir is the victim's own clean
  calibration-score distribution (source-precedence rule 2, because no separate
  calibration-candidate pool is exposed). At high fractions (`f=0.40`), with-
  replacement resampling from a fixed 10% tail produces repeated injection values
  (e.g. ~40 draws from ~`0.10·n_i` distinct scores), yielding a more uniform
  contaminated tail than a realistic attack. This is pre-registered and must be
  disclosed in manuscript limitations.
- **Claim enabled:** "Calibration set uses benign-only, chronological DATP split
  (60/20/~18); all 9 N-BaIoT devices are eligible (`n_cal ≥ 100`)."
- **Do-not-claim:** Do not claim any cross-client reservoir knowledge; all reservoirs
  are victim-local.
- **Evidence path:** `_ai_tracking/audits/CP2-T008_split_semantics_audit.md`,
  `src/datp/data/datasets/nbaiot/spec.py`.

---

## CP2-T007 — Clean artifact provenance audit

### Limitation to disclose

- **Claim enabled (conditional):** "Clean baselines were produced under the
  published DATP conference protocol (E=1, rounds_initial=40, rounds_max=150,
  FedAvg) within this repository; no hyperparameters were re-tuned." — **SAFE
  WORDING** once FB1 completes and E=1 artifacts are verified.
- **Claim blocked (now):** This claim is NOT yet writable. Artifacts are absent.
  FB1 must complete with authorization.
- **Limitation:** Score-level proxy artifact means with-replacement resampling from
  a fixed 10% tail at high fractions produces repeated injection values (disclosed
  proxy, Roadmap §6). Record in manuscript limitations.
- **Reviewer-risk:** Reviewers may question whether clean artifacts are truly
  independent of any CP2-influenced hyperparameter choices. Safe wording: "same
  DATP conference-faithful protocol; no CP2-specific tuning."
- **Do-not-claim:** Do not claim E=1 artifact compliance until FB1 completes and
  `verify_all_score_cells` confirms provenance.
- **Evidence path:** `_ai_tracking/audits/CP2-T007_artifact_audit.md`,
  `_ai_tracking/manifests/clean_score_artifacts.json`.

---

## CP2-T015 — Phase-A gate report (bootstrap variant + mu_flag_threshold plan)

- **Claim enabled (future):** "Percentile bootstrap CI on 5 seed-level CV(FPR)
  aggregates (inherited verbatim from DATP conference reporting pipeline)."
- **Do-not-claim:** Do not claim BCa as the primary method; it is secondary only.
  Do not claim any CI result until FB1 artifacts exist and seed-level aggregates
  are computed.
- **Method note:** `mu_flag_threshold = round(M_clean/8, 2 s.f.)` must be computed
  from clean FB1 artifacts and locked **before** any poisoned run. It is a CV-instability
  flag, not a denominator stabilizer. Record in methods section with the lock rationale.
- **Evidence path:** `audits/CP2_PHASE_A_GATE_REPORT.md`,
  `src/datp/reporting/build.py:64,312`, `src/datp/checkpointing/summary.py:206`.

---

## CP2-T006 — Claim-discipline reminder (drift gate)

**Do-not-claim (locked before any implementation/experiment):**

- Do **not** claim privacy or differential-privacy protection.
- Do **not** claim deployment, on-device, or hardware-overhead results.
- Do **not** claim broad FL robustness or generic poisoning resistance/attack.
- Do **not** claim evasion or backdoor capability.
- Do **not** claim "first work" / novelty supremacy.
- Do **not** restate DATP conference results as new CP2 contributions.

**Always pair with evidence (when results exist):** coverage ratio with every
`CV(FPR)`; AUROC reported invariant; seed-level statistics (never 9×5 = 45
independent); B4 deltas client-indexed.

Drift gate result: **no drift** at setup (see
`_ai_tracking/audits/CP2-T006_setup_drift_check.md`). Evidence path:
`docs/DATP_CP_Roadmap.md`, `Additional_Docs/Synthesis/Claims.md`.

---

## CP2-T023 — Phase-B protocol-lock drift check

**Drift gate result: NO DRIFT.** Protocol-lock architecture confirmed faithful to
roadmap §5, §6, §7, §10, §12.

- **Claim-discipline reminders (carried forward from T006):** All do-not-claim rules
  remain active. No CP2 implementation results exist yet; nothing new is writable.
- **Architecture observations (for methods section when results exist):**
  - `REPLACE_FIXED_BUDGET` injection rule is the *only* injection variant; no
    shift_magnitude and no add/remove variants. Record in methods §attack.
  - `victim_local_benign_cal_source_precedence_rule_2` is the only reservoir mode;
    test scores and training scores are explicitly excluded. Record in methods §attack.
  - `assert_no_inplace_mutation` guardrail is defence-in-depth, not a methods claim.
  - `assert_policy_not_b3` guardrail is defence-in-depth; B3 is DATP substrate only.
- **Do-not-claim (Phase B):** Do not claim that guardrails or config validators
  constitute experimental evidence. They are protocol-enforcement code.
- **Do-not-claim (Phase B):** Do not claim Phase C/D results until CP2-T056 runs.
- **Evidence path:** `audits/CP2-T023_phase_b_drift_check.md`; 702 tests pass;
  pyright 0 errors.

## CP2-T029 — Source Strategies

### Claims enabled

- **RANDOM_BENIGN as negative control:** RANDOM_BENIGN samples from the full victim
  calibration pool with replacement. Because it draws from the same distribution,
  expected threshold change is near-null. This is the negative control in the source
  strategy comparison. Near-null criterion is an audit flag (`|Δτ| ≤ threshold`),
  not an auto-kill; anomalies are flagged for review.
- **HIGH_SCORE_BENIGN raises threshold:** Upper-tail reservoir injection increases
  the quantile, shifting the threshold upward. Direction verified on synthetic data.
- **LOW_SCORE_BENIGN lowers threshold:** Lower-tail reservoir injection decreases
  the quantile, shifting the threshold downward. Direction verified on synthetic data.

### Limitations / do-not-claim

- **Do-not-claim:** `LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY` does not appear in
  the MVP/full experiment matrix and must not be cited as evidence in gray-box claims.
  It is gated behind `allow_diagnostic=True`.
- **Do-not-claim:** Near-null for RANDOM is an expected property of the construction,
  not a measured result. Record directional effects from real N-BaIoT runs (Phase E).

### Reviewer risk

- Reviewers may ask why RANDOM is included if it is a negative control. Answer:
  it validates that threshold change is attributable to the tail bias, not to
  cardinality change or random sampling noise.

### Evidence path

- `src/datp/attacks/source_strategies.py`
- `tests/unit/attacks/test_source_strategies.py`
- Directional effect tests pass on synthetic data; pyright 0 errors.

## CP2-T031 — B4 Decomposition

### Claims enabled

- **Client-indexed Δτ decomposition:** Each victim's threshold change is decomposed as
  `Δτ_total = Δτ_agg + Δτ_churn`. The aggregation component (Δτ_agg) captures within-cluster
  threshold change with frozen clean cluster assignments. The churn component (Δτ_churn)
  captures the residual: cluster reassignment and normalization-mediated spillover.
  The identity holds exactly (verified per client in tests).
- **Spillover framing:** B4 cluster spillover to co-cluster clients is a mechanism,
  not an independence violation. Non-victim co-cluster clients' thresholds may change
  via Δτ_agg (intra-cluster aggregation effect of the victim's poisoning).
- **Raw cluster labels never compared:** All B4 deltas are client-indexed. Raw k-means
  label IDs are not compared across clean and poisoned runs.

### Limitations / do-not-claim

- **Do-not-claim:** Δτ_churn magnitude on synthetic data is not a real-data result.
  The decomposition is measurable and structurally valid; quantitative claims wait until
  Phase E real N-BaIoT runs (Phase G: T056).
- **Do-not-claim:** B4 does not necessarily lie between B1 and B2. This is a hypothesis,
  not an assumption. Record empirical evidence in Phase E/G.

### Reviewer risk

- Reviewers may ask about scaler refitting mediation (S_pois vs S_clean). The churn
  component bundles pure normalization-mediated shifts (S_pois ≠ S_clean) alongside
  assignment churn. Optional sub-diagnostic (Roadmap §5) can isolate this if needed.
- B4 decomposition is an aggregate diagnostic, not a statistical test.

### Evidence path

- `src/datp/attacks/b4_recompute.py`
- `tests/unit/attacks/test_b4_recompute.py`
- 11 tests pass including decomposition identity: Δτ_agg + Δτ_churn = Δτ_total ✓

## CP2-T033 — Metric Engine

### Claims enabled

- **CV(FPR) no ε:** CV(FPR) = σ/µ with no epsilon in denominator. Returns nan when
  µ=0 (undefined). This is the correct treatment per protocol. Record in methods §metrics.
- **Coverage always reported:** Coverage ratio = n_eligible / n_total accompanies every
  CV(FPR) value. Clients with n_cal < n_min are Calibration-Pending and excluded.
- **mu_flag_threshold locked pre-poison:** `mu_flag_threshold = round(M_clean/8, 2 s.f.)`
  is computed from clean artifacts only. This module accepts it as input; the caller
  must lock it before running any poisoned condition.
- **AUROC invariant:** AUROC is computed from test scores (unchanged by calibration
  poisoning). Identical across clean and poisoned conditions by construction. This is
  the AUROC-invariance honesty point: calibration-channel attack does not improve ranking.
- **δ_τ,i = 0.1 × IQR(clean cal scores_i):** Per-client significance scale computed from
  clean calibration IQR. `is_significant = |Δτ| > δ_τ,i`.

### Limitations / do-not-claim

- **Do-not-claim:** Metric values on synthetic data are not paper results. Record real
  N-BaIoT values from Phase E/G (T056).
- **Do-not-claim:** CV(FPR)=nan when mean_fpr=0 does not indicate a good result; it
  indicates a degenerate condition (report coverage and flag).

### Evidence path

- `src/datp/attacks/metric_engine.py`
- `tests/unit/attacks/test_metric_engine.py`: 20 tests pass
- CV(FPR) no-ε confirmed: test_cv_fpr_no_epsilon verifies nan when mean=0.

## CP2-T034 — ASR, Blast Radius, Spillover Diagnostics

### Claims enabled

- **Blast-radius contrast (B1 vs B2 vs B4):** B2 blast radius = 1 (victim-local) by
  construction for single-victim attack. B1 blast radius = fleet-wide (all eligible
  clients affected via tau_global shift). B4 blast radius = cluster-local. This contrast
  is the policy-differentiation headline.
- **Spillover as mechanism:** B4/B1 spillover to non-victims is logged as a mechanistic
  effect of policy propagation, not as a violation of victim independence. B2 has zero
  spillover by construction.
- **ASR directional:** ASR counts clients with Δτ > δ_τ,i (THRESHOLD_RAISE) or Δτ < -δ_τ,i
  (THRESHOLD_LOWER). Direction must match the attacker objective.

### Limitations / do-not-claim

- **Do-not-claim:** ASR/blast-radius/spillover on synthetic data are not paper results.
  Record real N-BaIoT values from Phase E/G.
- **Do-not-claim:** B4 blast radius does not necessarily lie between B1 and B2; it depends
  on cluster composition.

### Reviewer risk

- Reviewers may confuse blast radius with independence. Clarify: blast radius is a
  mechanistic description of how many clients' thresholds change, not a claim about
  statistical dependence.

### Evidence path

- `src/datp/attacks/diagnostics.py`
- `tests/unit/attacks/test_diagnostics.py`: 14 tests pass
- B2 single-victim blast radius ≤ 1 verified; B1 blast ≥ B2 verified; B2 no spillover.

---

## CP2-T035 — Two-layer inference, manifest, run logging

### Claims enabled

- **Two-layer design is the primary statistical design:** Never treat 9 victims × 5 seeds
  = 45 deltas as 45 independent samples. Layer 1 = per-victim paired seed deltas (Δτ_{v,s});
  Layer 2 = seed-level aggregates δ_s = mean over feasible victims. Bootstrap CI is on the
  **5 seed-level aggregates** (primary evidence). Sign test (≥4/5 sign consistency) is
  supporting evidence only. Holm correction is descriptive only — never used to claim
  significance alone.
- **Manifest provenance:** Every CP2 cell run records E=1, reservoir mode, locked
  mu_flag_threshold, and the full SeedSequence entropy tuple (training_seed, poisoning_seed,
  client_idx, scope_idx) in a serialized manifest. Any claim of reproducibility is
  backed by the manifest round-trip.

### Limitations / do-not-claim

- **Do-not-claim:** "5 seed aggregates gives N=5 bootstrap." The bootstrap resamples from
  the 5 seed-level means — report this sample size explicitly in the methods section.
- **Do-not-claim:** Holm p-values as evidence of significance. Paper must state "descriptive
  only, not used for inference."
- **Reduced power flag:** If fewer than 2 feasible victims remain for a cell,
  `bootstrap_seed_aggregates` raises ValueError — record as a reduced-power limitation
  in the results.

### Reviewer risk

- Reviewers versed in paired-comparison statistics may challenge the bootstrap approach
  on N=5. Pre-empt by disclosing the sample size and citing the two-layer design explicitly
  in the methods.

### Figure/table affected

- Methods section: "Statistical inference" subsection — must state two-layer design,
  bootstrap on 5 aggregates, sign test supporting only, Holm descriptive.

### Evidence path

- `src/datp/attacks/inference.py`: two-layer inference (collect_paired_deltas,
  compute_seed_aggregates, sign_test, holm_adjust, bootstrap_seed_aggregates, compute_inference)
- `src/datp/attacks/run_logger.py`: manifest emission + run log (build_manifest,
  emit_manifest, write_run_log_entry)
- `tests/unit/attacks/test_inference.py`: 37 tests pass
- `tests/unit/attacks/test_run_logger.py`: 17 tests pass; mu_flag_threshold=None emission
  raises ManifestEmissionError; round-trip verified

---

## CP2-T037 — Phase C final drift check

### Claim-discipline confirmation (all locks verified)

- **Two-layer design is the primary statistical design** (restated from T035):
  Methods section must explicitly state N=5 seed-level aggregates for bootstrap CI.
- **Sign test is supporting evidence only** (≥4/5 sign consistency = "consistent",
  not "significant").
- **Holm correction is descriptive only** — paper must state this.
- **AUROC is invariant** — calibration-channel attack does not alter test scores;
  AUROC is recorded for completeness only, not as a metric of attack success.
- **CV(FPR) without ε** — paper must state no epsilon stabilizer was used.

### Do-not-claim list (refreshed)

- Do NOT claim 45 independent replicates.
- Do NOT claim Holm p-values are inferential.
- Do NOT claim synthetic smoke results as paper results.
- Do NOT claim experiments ran before Phase E.
- Do NOT claim AUROC improvement/degradation.
- Do NOT claim broad FL robustness.
- Do NOT claim deployment or on-device results.

### Evidence path

- `docs/tickets/_ai_tracking/audits/CP2-T037_phase_c_drift_check.md`
- All 13 lock checks: PASS
- 538 unit tests pass; pyright 0 errors; ruff 0 errors

---

## CP2-T041 — Phase D smoke-validation drift gate

### Claim enabled

- **Reproducibility / methods-section claim:** the full CP2 pipeline (reservoir →
  REPLACE_FIXED_BUDGET injection → B1/B2/B4 recompute + B4 Δτ decomposition → metric
  engine → two-layer inference → manifest) is validated end-to-end on synthetic score
  arrays before any real data is touched. 11 prompt invariants + 4 distinct roadmap
  invariants (15 total) are asserted and passing, CPU-only and deterministic.
- The methods section may state that protocol invariants are machine-checked
  (`tests/integration/attacks/test_cp2_smoke.py`) and that all randomness derives from
  `numpy.random.SeedSequence([training_seed, poisoning_seed, client_id, scope_id])`.

### Claim blocked / do-not-claim (refreshed)

- **Do NOT report any synthetic smoke number as a result.** The smoke harness uses
  fabricated score arrays; ASR/blast-radius/Δτ values from it are validation artifacts
  only, never paper results. First real results come from Phase E.
- Do NOT claim 45 independent replicates — bootstrap CI is on **5** seed-level
  aggregates (invariant 8 enforces this).
- Do NOT claim Holm p-values are inferential (descriptive only).
- Do NOT claim AUROC improvement/degradation — invariant by construction (invariant
  10); test scores are never altered by the calibration-channel attack.
- Do NOT claim "B4 lies between B1 and B2" from smoke — the smoke only proves the B4
  shift/decomposition is **computable and finite** and that B1 victim shift < B2 victim
  shift (dilution); the B1<B4<B2 ordering is a Phase-E/F hypothesis, not an invariant.

### Limitation to disclose

- The smoke harness validates pipeline correctness, not scientific magnitude. The
  near-null behaviour of RANDOM_BENIGN and the HIGH-raises/LOW-lowers direction are
  qualitative invariants checked on synthetic distributions; effect sizes are
  Phase-E/F empirical questions.

### Figure / table affected

- Reproducibility / methods subsection (no results figure). Underpins the
  invariant-table the paper may include to document protocol fidelity.

### Reviewer-risk relevance

- Pre-empts "are your 9×5 victim-seed deltas treated as 45 independent samples?" —
  invariant 8 demonstrates the two-layer aggregation in code.
- Pre-empts "did the attack secretly change test scores / AUROC?" — invariant 10.
- Pre-empts "is CV(FPR) ε-stabilized?" — invariant 11 shows µ=0 → `nan`, no ε.

### Dependency note

- `statsmodels` (descriptive Holm correction) was an undeclared dependency that broke
  `inference.py` import; now installed (0.14.6) and declared in `pyproject.toml`. The
  inferential core (bootstrap CI) depends only on scipy/numpy. See decision log.

### Evidence path

- `docs/tickets/_ai_tracking/audits/CP2-T041_smoke_validation_drift_check.md`
- `docs/tickets/_ai_tracking/audits/CP2-T040_smoke_test_consolidation.md`
- `tests/integration/attacks/test_cp2_smoke.py` — 19 passed
- 15 distinct invariants asserted and passing; pyright 0 errors; ruff clean
