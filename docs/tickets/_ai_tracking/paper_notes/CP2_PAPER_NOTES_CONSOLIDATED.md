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
