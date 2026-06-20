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

---

## CP2-T042 — Phase E entry gate: FB1 re-confirmed, no real-data MVP results exist

### Claim blocked / do-not-claim

- **No real N-BaIoT MVP results exist in this repository as of 2026-06-16.** Phase E
  (CP2-T042–T049) could not proceed past the entry gate: no clean per-client N-BaIoT
  calibration/test score artifacts exist, and the only in-repo training config is
  `local_epochs: 5` (E=5), not the conference-faithful E=1. Do NOT cite any MVP
  number, kill-trigger outcome, or continue/stop/pivot decision — none was produced.
  CP2-T049 recorded no decision (would be unevidenced).
- Do NOT imply Phase E ran and found a null/clean result — it did not run at all.
  This is an artifact-availability blocker, not a scientific finding.

### Limitation to disclose

- The manuscript's empirical section depends on FB1 (one supervised federated
  retrain at E=1) being authorized and executed. As of this note, FB1 is
  **TRIGGERED, awaiting explicit human authorization** (heavy training + GPU
  may be required; config-semantics change `local_epochs: 5 → 1`). Until resolved,
  all Phase E–G results are absent, not merely unaudited.

### Reviewer-risk relevance

- Pre-empts "why are there no real-data results / why does Phase E close with no
  numbers?" — the answer is a documented, evidenced provenance gate failure (E=5
  config + missing artifacts), not a dropped or cherry-picked result.

### Evidence path

- `docs/tickets/_ai_tracking/diagnostics/CP2-T042_nbaiot_load_dryrun.md`
- `docs/tickets/_ai_tracking/run_logs/CP2_PHASE_E_ENTRY_GATE.md`
- `docs/tickets/_ai_tracking/decisions/CP2_FALLBACK_REGISTER.md`
- `docs/tickets/_ai_tracking/manifests/clean_score_artifacts.json` (`"verdict":
  "ARTIFACTS_MISSING"`, `"e5_in_yaml_config": true`)
- Decision log: `2026-06-16 | CP2-T042 | FB1 RE-CONFIRMED at Phase E gate`

### SUPERSEDED (2026-06-16, same day)

The blocker above is resolved. The user explicitly authorized FB1; `config.yaml`
was fixed to `local_epochs: 1` and the one authorized E=1 retrain was executed
(25/25 sweep cells). Real clean N-BaIoT score artifacts now exist for all 5
training seeds and pass `verify_all_score_cells` (18/18 checks each). The
"no real-data MVP results exist" claim-block above no longer holds as of this
note; see CP2-T043 below for the first real-data results. Evidence:
`docs/tickets/_ai_tracking/diagnostics/CP2-T042_nbaiot_load_dryrun.md` (rewritten,
verdict PASS), decision log FB1 execution entries.

---

## CP2-T043 — One-seed real-data diagnostics: directionally correct, policy-differentiated blast radius

### Claim enabled

- On real N-BaIoT `training_seed=0` data, calibration-channel poisoning with
  `HIGH_SCORE_BENIGN` raises τ and `LOW_SCORE_BENIGN` lowers τ, monotonically in
  the injection fraction, across all three default policies (B1_GLOBAL,
  B2_PERSONALIZED, B4_CLUSTER). `RANDOM_BENIGN` stays near-null and
  non-monotonic by comparison. This is the first real-data confirmation of the
  CP2 core mechanism (prior confirmation was synthetic-only, CP2-T038–T041).
- Blast radius is policy-differentiated in the hypothesized qualitative order:
  B2 (personalized, victim-only) = 11.1% (1/9) < B4 (cluster) = 88.9% (8/9) <
  B1 (global) = 100% (9/9), at f=0.40, HIGH_SCORE_BENIGN, single seed.
- AUROC invariance and cardinality preservation hold exactly (abs_tol=1e-12;
  exact n_i match) across all 36 one-victim cells — confirms the
  calibration-channel-only boundary held in the real-data pipeline, not just
  in synthetic smoke tests.

### Limitation to disclose

- **Single seed, single poisoning-seed.** This is a feasibility/direction
  diagnostic (CP2-T043 scope), not a statistical result — n=1 per cell, no
  multi-seed aggregation, no bootstrap CI, no sign test. Do not cite these
  specific Δτ or blast-radius numbers as the paper's reported effect sizes;
  cite only "direction and feasibility confirmed pre-MVP" until CP2-T046/T047
  multi-seed results exist.
- **B4 blast-radius magnitude (88.9%) is higher than a naive cluster-size
  heuristic (~33%, cluster_size/9) would predict.** The qualitative ordering
  (B2 < B4 < B1) is correct and was the acceptance bar for this ticket, but
  the close-to-B1 magnitude should not be over-interpreted from one seed/one
  fraction. Flagged for re-examination once CP2-T046/T047 multi-seed B4
  statistics exist — if the pattern holds across seeds, it is a real and
  citable finding (cluster-churn propagation, `Δτ_total = Δτ_agg + Δτ_churn`,
  can extend beyond the victim's literal cluster); if it does not replicate,
  it was a single-seed artifact.

### Figure/table affected

- Candidate input to a future "blast radius by policy" figure/table (Phase G),
  pending multi-seed confirmation. Not citable as a standalone figure yet.

### Reviewer-risk relevance

- Pre-empts "does B4 actually behave like an intermediate/clustered policy, or
  does it just track B1?" — this note honestly discloses the single-seed
  magnitude is closer to B1 than a naive heuristic predicts, rather than
  silently rounding it to "as expected."
- Pre-empts "did you only test synthetic data?" — this is the first
  confirmation on real per-client N-BaIoT scores.

### Do-not-claim reminder

- Do not claim "B4 blast radius ≈ 89%" as a headline MVP number; it is a
  single-seed diagnostic observation pending CP2-T046/T047 confirmation.
- Do not claim statistical significance of any Δτ at this rung — no CI, no
  sign test, n=1.

### Evidence path

- `docs/tickets/_ai_tracking/diagnostics/CP2-T043_one_seed_diagnostics.md`
- `src/datp/attacks/real_score_loader.py`, `mvp_runner.py`, `cell_runner.py`
- `tests/integration/attacks/test_real_score_loader.py`,
  `tests/unit/attacks/test_mvp_runner.py`

## CP2-T046 — MVP manifest & result-sanity audit: full-scale (1620-cell) confirmation

### Claim enabled

- The full bounded-MVP matrix (9 victims × 3 policies × 3 sources × 4 fractions
  × 5 training/poisoning-seed pairs = 1620 cells, all real N-BaIoT data) is
  complete and schema-valid: every cell has a non-empty result, AUROC
  invariance holds on **1620/1620** rows, and the `f=0.0` no-op invariant
  (`delta_tau == 0.0` etc.) holds exactly on all 405 zero-fraction rows.
  `mu_flag_threshold` was confirmed locked per-training-seed from clean B1
  data before any poisoned cell ran, with values identical to the
  independently-derived CP2-T044 stability-sweep values
  (`{0: 0.005, 1: 0.0049, 2: 0.0056, 3: 0.0053, 4: 0.005}`).
- Directional confirmation now holds at full scale, not just one seed:
  `HIGH_SCORE_BENIGN` raises τ in 403/405 non-zero-fraction cells (mean
  Δτ = +0.392), `LOW_SCORE_BENIGN` lowers τ in 403/405 (mean Δτ = −0.0662),
  `RANDOM_BENIGN` is near-null (mean Δτ = −0.0003, pos/neg roughly balanced
  200/190, 15 exact zeros). This resolves the CP2-T043 caveat that direction
  was confirmed on n=1 only.
- **The CP2-T043 flagged concern about B4 magnitude is resolved at full
  scale, and the resolution changes the headline number.** CP2-T043's
  single-seed observation was B4 blast radius (88.9%) sitting unexpectedly
  close to B1 (100%). At full scale (mean blast_fraction across all non-zero
  cells): B1_GLOBAL = 0.559, B4_CLUSTER = 0.447, B2_PERSONALIZED = 0.091. The
  qualitative ordering B2 < B4 < B1 replicates, but B4 is now roughly
  midway between the two boundary policies, not clustered near B1 — the
  single-seed magnitude was **not** representative and must not be reused.
- Four cells (0.25% of 1620), all `B4_CLUSTER`, show a directional sign
  reversal relative to their source's expected direction. All four are
  mechanistically explained by the locked `Δτ_total = Δτ_agg + Δτ_churn`
  decomposition (CP2-T031): cluster-reassignment churn after poisoning can
  act against the direct injection effect for a specific victim. This is a
  measurability property of B4, not an injector or metric-engine defect, and
  is not large enough (`|Δτ| <= 0.033`) to be evidence against the ≥4/5-seed
  sign-consistency rule at the per-victim level (that evaluation belongs to
  CP2-T047/T049).

### Limitation to disclose

- This audit is descriptive only — no significance testing, no
  sign-consistency-rule application, no bootstrap CI, no claim-worthy
  decision. `is_victim_significant` is computed per-cell (849/1620 = 52.4%)
  but is not yet aggregated to the seed level or run through the locked
  statistical plan (roadmap §9: 5 seed-level aggregates, percentile
  bootstrap, sign test as supporting evidence only). Do not cite the 52.4%
  figure, the per-policy mean blast_fraction figures, or the 403/405
  directional-consistency counts as the paper's reported effect sizes until
  CP2-T047 (kill triggers) and CP2-T049 (continue/stop/pivot) have run the
  proper seed-level inference.
- The 4 B4 sign-reversal cells are flagged, not resolved into a statistical
  statement — whether they survive the ≥4/5-seed sign-consistency rule at
  the per-victim level is CP2-T047/T049's job, not this audit's.

### Figure/table affected

- Now the primary candidate input to the Phase G "blast radius by policy"
  figure/table, superseding the CP2-T043 single-seed placeholder — but still
  pending CP2-T047/T049's statistical sign-off before being treated as
  citable. The B1/B4/B2 = 0.559/0.447/0.091 triple is the full-scale
  descriptive analog of CP2-T043's single-seed 100%/88.9%/11.1% triple.
- Candidate input to a "B4 cluster-churn anomaly" footnote or appendix table
  (4 flagged cells), if CP2-T047/T049 decide the anomaly is worth disclosing
  in the main paper rather than just the audit trail.

### Reviewer-risk relevance

- Directly pre-empts "you only checked one seed" (CP2-T043's own flagged
  risk) — this is now full-scale, all 5 locked training/poisoning seed
  pairs, all 9 eligible victims.
- Pre-empts "is B4 just B1 with a different label?" — the full-scale mean
  blast_fraction shows real separation (0.447 vs 0.559), not the
  near-coincidence the single-seed number suggested.
- Pre-empts "did you cherry-pick clean cells?" — the audit explicitly
  surfaced and explained the 4 anomalous cells rather than omitting them.

### Do-not-claim reminder

- Do not cite the single-seed CP2-T043 numbers (100%/88.9%/11.1%) anywhere
  in the paper now that full-scale numbers exist and differ materially.
- Do not claim "B4 blast radius = 44.7%" or any other figure from this audit
  as a statistically validated result — these are unweighted means over all
  non-zero-fraction cells, not the seed-level bootstrap aggregate the
  roadmap's statistical plan requires (CP2-T047/T049 own that step).
- Do not claim the 4 B4 sign-reversals are resolved or explained away as
  "not real" — they are real, measured, and mechanistically attributed to
  churn, but their statistical weight is still pending.

### Evidence path

- `docs/tickets/_ai_tracking/audits/CP2-T046_mvp_manifest_result_sanity_audit.md`
- `outputs/conference_calibration_poisoning/nbaiot_mvp_manifest.json`
- `docs/tickets/_ai_tracking/decisions/CP2_DECISION_LOG.md` (CP2-T045 entry,
  real-execution provenance)

## CP2-T047 — Kill-trigger evaluation: no trigger fires; one evidentiary gap flagged

### Claim enabled

- None of the 7 pre-registered kill triggers (roadmap §16) fire on the
  full-scale bounded-MVP evidence. In particular, kill-trigger (1) ("no
  material threshold shift for B2 under HIGH/LOW even at f=0.40") is
  strongly refuted: `B2_PERSONALIZED` shows monotone, fully sign-consistent,
  materially significant `Δτ` at every fraction (`f=0.40`: `+0.914` raise /
  `−0.167` lower; bootstrap CI excludes zero by a wide margin; 9/9 victims
  sign-consistent; ASR materiality rate `1.000`).
- Kill-trigger (3) ("B1/B2/B4 indistinguishable") is refuted with a clean
  mechanistic cross-check, not just a numeric difference: `B1 ≈ B2/9`
  (`0.1015 ≈ 0.9139/9`) because B1's `tau_global` is the mean of 9 per-client
  thresholds and only one shifts; this is the first time the B1 dilution
  mechanism has been verified arithmetically against real data, not just
  asserted qualitatively.
- This is the strongest evidence to date that the CP2 hypothesis is viable
  and the paper's primary mechanism claim (raise/lower, policy-differentiated)
  is supportable on real N-BaIoT data at full MVP scale.

### Limitation to disclose

- **Kill-trigger (2) (downstream-metric movement) is not fully closeable
  with the current MVP artifacts and must not be claimed as resolved.** The
  roadmap (§8, §12) requires a primary claim to show `Δτ` with correct sign
  **linked to ≥1 downstream metric** (victim `ΔTPR` for raise;
  `ΔCV(FPR)`/worst-client FPR for lower) — but the bounded-MVP manifest
  schema (`Cp2MvpResultRow`) does not carry literal per-victim `ΔTPR`/`ΔBA`.
  The closest available evidence is the `Δτ`-materiality (ASR) proxy
  (`is_victim_significant`), which is strongly positive across all
  directional cells — but this is evidence the threshold moved by a material
  amount, not direct evidence the victim's detection rate measurably
  changed. **Do not claim the roadmap §12 primary-endpoint rule is fully
  satisfied** until a dedicated downstream-metric pass is run (a bounded,
  low-risk follow-on that reuses already-tested `cell_runner.py` threshold
  primitives against each victim's already-loaded `test_attack` scores — no
  new scientific design, just an unbuilt computation).
- **One RANDOM_BENIGN cell is not exactly null.** `B4_CLUSTER`/
  `RANDOM_BENIGN`/`f=0.40` is the sole cell (of 9 RANDOM cells) where the
  bootstrap CI on the seed-level aggregate excludes zero
  (`[-0.0233, -0.0065]`). Mechanistically attributed to cluster-reassignment
  churn variance under unbiased resampling at the largest fraction (the
  locked `Δτ_total = Δτ_agg + Δτ_churn` decomposition, CP2-T031) — magnitude
  is 6–13× smaller than the directional B4 effects at the same fraction, so
  RANDOM remains a usable near-null control in relative terms, but this
  specific cell should not be cited as "exactly null" without the caveat.

### Figure/table affected

- Strengthens the case for the candidate "blast radius by policy" and "Δτ
  vs fraction per policy" figures (F3/F5, roadmap §11) — the B1≈B2/9
  mechanistic identity is a strong candidate footnote/derivation for the
  methods or discussion section.
- The trigger-(2) gap affects T4 (main results table) and T5
  (claims↔evidence table): T4/T5 should not list a downstream-metric column
  as populated until the follow-on diagnostic exists.

### Reviewer-risk relevance

- Directly pre-empts "you only measured Δτ, not actual detection harm" —
  this note proactively discloses that exact gap rather than letting a
  reviewer find it, and proposes the fix is bounded and already
  architecturally possible (test_attack scores are already loaded).
- The B1≈B2/9 arithmetic identity pre-empts "is B1's small effect just
  noise?" — it is not; it is the predicted, falsifiable consequence of B1's
  definition.

### Do-not-claim reminder

- Do not claim the roadmap §12 five-part primary-endpoint decision gate is
  fully satisfied — the downstream-metric leg is unverified, not satisfied.
- Do not claim "RANDOM_BENIGN is exactly null in every cell" — one B4 cell
  at the largest fraction has a non-null bootstrap CI; report this with its
  mechanistic explanation if RANDOM near-nullness is cited in the paper.
- Do not claim B1's small effect size as evidence against the attack's
  severity without noting it is the global-mean-dilution mechanism, not a
  weaker attack — B2's undiluted victim shift (`0.914`) is the more
  conservative severity number for the "personalized policy is most
  vulnerable" claim.

### Evidence path

- `docs/tickets/_ai_tracking/audits/CP2-T047_kill_trigger_evaluation.md`
- `outputs/conference_calibration_poisoning/nbaiot_mvp_manifest.json`
- `src/datp/attacks/inference.py` (two-layer statistical machinery reused,
  unchanged)

## CP2-T048 — MVP drift check: no protocol-lock drift in the real-data run path

### Claim enabled

- The real-data bounded-MVP execution path (loader → injector → threshold
  recompute → metric engine → manifest writer) preserves every applicable
  roadmap §5–§12 lock: calibration-channel-only boundary (the code imports
  nothing from `federated.protocols.fedavg` or model modules — the
  isolation is structural, not just behaviorally observed via AUROC
  invariance), E=1, SINGLE_CLIENT, default policies with B3 architecturally
  absent, REPLACE_FIXED_BUDGET with victim-local reservoirs, the two-layer
  statistical unit of analysis, `mu_flag_threshold` locked before any
  poisoned cell by control-flow construction (not just by matching values),
  and `REGIME_A_NBAIOT`-only (no code path can reach CICIoT2023 or
  Edge-IIoTset from the bounded-MVP runner).
- Seed-scheme integrity was re-verified at full scale (all 1620 rows, not a
  spot check): `seed_record.entropy[1] == poisoning_seed` on every row — 0
  mismatches, ruling out integer-seed-addition drift across the entire
  artifact, not just a sample of it.

### Limitation to disclose

- This is a code-and-artifact drift check, not a new statistical result —
  it adds confidence that CP2-T046/T047's evidence is protocol-clean, it
  does not add new effect-size evidence.
- An unrelated, pre-existing DATP-substrate test-collection issue was
  observed (4 `tests/e2e/*` files fail to import `SplitFilename`) and
  confirmed via `git log` to predate all CP2 work — explicitly not a CP2
  drift and not actioned, but noted here so it isn't silently rediscovered
  as a surprise later.

### Figure/table affected

- None directly — this strengthens the credibility of the evidence behind
  F3–F6/T4/T5, it isn't itself a figure/table input.

### Reviewer-risk relevance

- Directly supports the "calibration channel is structurally distinct from
  the training pipeline" defense (roadmap §14 row 1) with a code-level
  claim (no import path to FL training/aggregation code), not only a
  metric-level claim (AUROC invariance).

### Do-not-claim reminder

- Do not claim this drift check is a substitute for CP2-T046/T047's result
  audits — it confirms protocol fidelity of the run path, not the
  statistical validity of the findings.

### Evidence path

- `docs/tickets/_ai_tracking/audits/CP2-T048_mvp_drift_check.md`
- `outputs/conference_calibration_poisoning/nbaiot_mvp_manifest.json`
- `src/datp/attacks/mvp_run.py`, `cell_runner.py` (control-flow inspection)

---

## CP2-T049 — MVP CONTINUE decision: LOWER narrative fully evidenced; RAISE downstream metric pending

### Claim enabled

**LOWER narrative primary endpoint satisfied (Δτ + ΔCV(FPR)):** the bounded
MVP establishes that LOW_SCORE_BENIGN poisoning produces material, monotone,
policy-differentiated ΔCV(FPR) movement: B2 disparity increases to a mean
ΔCV = +0.069 at f=0.40 (9/9 victims, 5 seeds), B4 similarly (+0.090), B1
homogenizes (−0.022) — a mechanistically interpretable policy contrast
consistent with B1's global-averaging dilution vs B2/B4's per-client/cluster
concentration. Combined with T047's Δτ evidence (B2 lower: −0.167 at f=0.40,
CI excludes zero, 9/9 strict majority), this satisfies roadmap §8/§12's
primary-endpoint requirement for the LOWER objective (material Δτ + movement
in ΔCV(FPR)/worst-client FPR).

**RAISE narrative Δτ leg well-established:** B2 raise: +0.914 at f=0.40, CI
excludes zero, 9/9 strict majority; B1/B4 show smaller, sign-consistent
raise effects. This evidence supports the raise narrative alongside the
downstream measurement still pending (below).

### Limitation to disclose

**RAISE narrative downstream metric (victim ΔTPR) not yet computed:** no
literal TPR, BA, or F1 score change per victim has been measured anywhere in
the MVP pipeline (`Cp2MvpResultRow` schema carries no TPR/BA/F1 field). This
is not a null finding — it is an unmeasured quantity. The raise claim cannot
currently be stated as "Δτ linked to ≥1 downstream metric" per roadmap §12's
exact wording until ΔTPR is computed and shows consistent movement.

Must be closed in CP2-T057 (final analysis): compute victim ΔTPR using
already-existing `tau_clean`/`tau_poisoned` values (from `Cp2ThresholdPair`)
against each victim's `Cp2ClientScores.test_attack` scores — no new
poisoning, no new seeds, no scope expansion needed. Table T4 and Figure F6
("victim ΔTPR vs worst-client ΔFPR") explicitly require this.

### Figure or table affected

- **F3** (Δτ vs fraction): already supported by T046/T047 Δτ evidence for
  all three objectives.
- **F4** (ΔCV(FPR)/worst-client FPR vs fraction): LOWER narrative now
  evidenced with real data from this ticket's aggregation (the formal,
  committed version to appear in CP2-T057's reporting module).
- **F6** (victim ΔTPR vs worst-client ΔFPR): RAISE-side half is blocked
  until ΔTPR is computed; LOWER-side worst-client FPR is derivable from
  existing `mean_fpr` fields.
- **T4** (main results: clean vs poisoned, mechanism + one downstream metric):
  LOWER row can be completed; RAISE row's "downstream metric" column is
  pending ΔTPR.
- **T5** (claims↔evidence): RAISE claim cannot be marked fully supported
  until ΔTPR closes.

### Reviewer-risk relevance

**RQ-B (lower) is now doubly evidenced** — both Δτ and ΔCV(FPR) downstream
movement. This is the stronger, cleaner result and should be foregrounded in
the disparity narrative. B1's homogenizing effect (opposite sign) is a
differentiated finding, not a failure — it directly supports the
policy-comparison narrative (B1's global averaging absorbs the disparity
that B2/B4 amplifies).

**RQ-A (raise) has a strong Δτ leg but an incomplete primary-endpoint
chain** — do not finalize the paper's claim posture for RAISE until CP2-T057
closes the ΔTPR leg. The paper's reviewer defensibility for RAISE depends on
the final ΔTPR values being consistent (or on explicitly disclosing that
ΔTPR is reported as a secondary metric if the primary Δτ link is stated
differently per §15's mixed wording).

### Do-not-claim reminder

- **Do not claim the RAISE narrative's primary endpoint is fully satisfied**
  until CP2-T057 computes victim ΔTPR. Do not include RAISE in Table T4's
  "one downstream metric" column until that column has real ΔTPR values.
- **Do not claim the ΔCV(FPR) values here as final** — they were computed
  via ad hoc read-only aggregation (not a committed reporting module); the
  official, committed version must appear in CP2-T057 with a provenance
  sidecar. The values above are for decision-gate evidence only.
- **Do not claim §15 "if positive" wording** (the fully positive claim)
  until both RAISE and LOWER are individually supported at the
  primary-endpoint level. Use §15's "if mixed" wording until RAISE ΔTPR
  is confirmed.
- **Do not claim Phase F results** — fraction 0.05, multi-client, defense,
  CICIoT2023 — until CP2-T056 executes and CP2-T055 drift-checks them.

### Evidence path

- `docs/tickets/_ai_tracking/decisions/CP2_DECISION_LOG.md` (CP2-T049 entry)
- `docs/tickets/_ai_tracking/audits/CP2-T047_kill_trigger_evaluation.md`
- `outputs/conference_calibration_poisoning/nbaiot_mvp_manifest.json`
  (fields: `cv_fpr`, `mean_fpr`, `coverage_ratio`, `n_eligible`)
- `src/datp/attacks/mvp_manifest.py` (`Cp2MvpResultRow` schema — confirms
  no TPR/BA/F1 field)

---

## CP2-T050–T055 + FB4 — Phase F full-scope IMPLEMENTATION (no runs) — 2026-06-17

**Context:** CP2-T049 = CONTINUE opened Phase F. Under the implementation-only
authorization (execution gated at CP2-T056), the full-scope code/config and the
read-only feasibility/drift audits were completed; **no Phase-F experiment ran.**

### Claims enabled (capability, not results)
- The codebase can now enumerate the full-scope matrix (fraction grid
  `{0,0.05,0.10,0.20,0.40}`), run multi-client (pairs + 20 triples) with
  independent per-co-victim SeedSequence streams (`compromise_pattern_seed=400`),
  and apply a trimmed-calibration defense (`t=5%` primary, `t=10%` appendix)
  before the threshold percentile and B4 fingerprint. These are *methods*
  available for the paper's full-scope/defense sections **once executed**.

### Claims blocked / do-not-claim
- **Do not report any Phase-F numbers** (0.05 dose-response, multi-client
  compound/spillover, defense recovery/regression, CICIoT2023) — nothing has run.
  Phase-F results require CP2-T056 execution + CP2-T053/T055 run-output audits.
- **Defense — do not overclaim robustness.** Trimmed calibration is *partial,
  conditional* mitigation: it removes injected tail contamination only when the
  trim fraction covers it; in the realistic in-range-reservoir regime (sources
  sample the victim's clean tail) symmetric trimming at q=0.95 can leave |Δτ|
  barely changed or slightly worse, and it imposes a calibration-cardinality
  (coverage/utility) cost. Frame as "partial mitigation with cost," report the
  defense regardless of outcome, and disclose failure/over-trim cases.
- **CICIoT2023 — INFEASIBLE-NOW.** No processed features / E=1 scores /
  provenance exist; the stretch cannot run under current artifacts/gate. If ever
  run, it is **external-validity only, never confirmatory**, with the mandatory
  **pseudo-client caveat** (file-level `MERGED_FILE`, not physical devices).
  N-BaIoT (physical devices) remains the sole primary regime. Edge-IIoTset
  forbidden.

### Limitations to disclose
- Full-scope, multi-client, and defense results are pending execution; the paper
  must not present Phase-F capability as Phase-F evidence.

### Figures/tables affected (when executed)
- Dose-response figure gains a low-budget point at f=0.05.
- New (future) tables: multi-client compound/spillover; defense recovery vs
  regression per policy. None populated yet.

### Reviewer-risk relevance
- A reviewer will probe defense overclaims and CICIoT2023 device framing — the
  honest "partial mitigation / pseudo-client / external-validity" posture above
  is the defensible wording.

### Evidence path
- `_ai_tracking/audits/CP2-T054_ciciot2023_feasibility_preaudit.md`
- `_ai_tracking/audits/CP2-T055_full_scope_drift_check.md`
- `_ai_tracking/audits/CP2-T053_defense_regression_audit_GATED.md`
- `_ai_tracking/decisions/CP2_FALLBACK_REGISTER.md` (FB4 detail)
- `src/datp/attacks/{compromise_patterns,defenses}.py`,
  `src/datp/attacks/{poison_enums,bounded_sweep_matrix,cell_runner,guardrails}.py`

---

## PRE-T056 gate — Victim downstream metrics added to bounded sweep manifest

### Claim enabled

- **RAISE narrative — victim detection loss claim (claim-critical):** Every
  `BoundedSweepResultRow` now carries `victim_tpr_clean`, `victim_tpr_poisoned`,
  `victim_delta_tpr`, `victim_ba_clean`, `victim_ba_poisoned`, `victim_delta_ba`,
  `victim_macro_f1_clean`, `victim_macro_f1_poisoned`, `victim_delta_macro_f1`.
  When CP2-T056 executes the bounded sweep, CP2-T057 can directly analyze whether
  a threshold-raise translates into a detection-rate drop (negative `victim_delta_tpr`)
  without rerunning the pipeline.
- Label polarity confirmed unambiguous: `test_attack` arrays = positive class
  (malicious/anomalous); `test_benign` arrays = negative class. Prediction rule:
  score > threshold → predicted malicious. This is consistent with the existing
  `recompute_binary_metrics` convention in `evaluation/metrics.py` and the AUROC
  computation in `evaluation/ranking.py`.

### Metrics: formulas locked

- `TPR = TP / (TP + FN)` where TP = `sum(test_attack > threshold)`.
- `FPR = FP / (FP + TN)` where FP = `sum(test_benign > threshold)`.
- `TNR = 1 - FPR`.
- `BA = (TPR + TNR) / 2`.
- `macro_F1 = (F1_positive + F1_negative) / 2` (binary, as in `recompute_binary_metrics`).
- delta = poisoned − clean for all metrics.
- NaN when the required array is empty.
- All formulas are implemented via `recompute_binary_metrics` from `evaluation/metrics.py`
  — no custom float arithmetic, no ε.

### Important scope note (LOWER narrative)

- LOWER cells also carry these fields and they can be inspected (e.g., whether a
  threshold-lower incidentally improves victim TPR). However, the **primary** LOWER
  endpoint is `cv_fpr`, `mean_fpr`, `worst_client_fpr`, and dispersion — those are
  unchanged. `victim_delta_tpr` is a measurement addition for completeness, not a
  LOWER-primary claim.

### Invariant: f=0 rows have delta=0

- When fraction=0.0, the attack is a no-op (injection replaces 0 positions). The
  clean and poisoned effective thresholds are identical, so `victim_delta_tpr=0`,
  `victim_delta_ba=0`, and `victim_delta_macro_f1=0` (or NaN if arrays are empty).
  This is verified by the integration test.

### Do-not-claim

- Do NOT claim victim detection loss from the threshold-raise alone without `victim_delta_tpr`
  evidence. The CP2-T047 open gap (T047 flag "(2)") is now closeable by CP2-T057 using
  `victim_delta_tpr` from the manifest. Do not pre-empt that analysis here.
- Do NOT use victim downstream metrics as a LOWER primary claim (they are supplemental there).

### Reviewer-risk relevance

- Reviewers asking "but does the threshold-raise actually reduce attack detection?" can now
  be answered with empirical `victim_delta_tpr` values from the manifest rather than
  requiring an extra pipeline run.
- Balanced accuracy and macro F1 provide interpretability across different base-rate regimes.

### Limitation to disclose

- Metrics are computed from the unchanged test arrays at each effective threshold. If the
  test set's attack fraction differs substantially across policies (it does not in N-BaIoT,
  which uses fixed splits), BA would need to be reported alongside base rates.

### Evidence path

- `src/datp/attacks/metric_engine.py`: `VictimDownstreamMetrics` dataclass +
  `compute_victim_downstream_metrics` function (reuses `recompute_binary_metrics`).
- `src/datp/attacks/bounded_sweep_manifest.py`: 9 new fields on `BoundedSweepResultRow`.
- `src/datp/attacks/bounded_sweep_run.py`: wired into `_row_for_cell`; clean threshold
  from `DeltaTauEntry.tau_clean`, poisoned from `DeltaTauEntry.tau_pois`.
- `tests/unit/attacks/test_victim_downstream_metrics.py`: 15 tests pass (correctness,
  direction invariants, zero-fraction invariant, no-mutation, edge cases).
- `tests/unit/attacks/test_bounded_sweep_manifest.py`: 12 tests pass (6 new schema tests).
- `tests/integration/attacks/test_bounded_sweep_run.py`: 2 integration tests pass
  including zero-fraction delta assertions.
- `pyright src/datp/attacks/` → 0 errors; `ruff check src/ tests/` → clean.
