# DATP Invariant Check Skill

Use this skill whenever a task touches calibration-channel poisoning science, experiment logic, datasets, threshold policies, attack mechanics, metrics, reporting, or manuscript claims.

The goal is to prove that the change preserves the datp-cp scientific contract.

Protocol of record: `docs/DATP_CP_Roadmap.md`.

---

## 1. Required Inputs

Before applying this skill, inspect:

1. `docs/DATP_CP_Roadmap.md` — protocol of record
2. `CLAUDE.md` — active vocabulary and coding rules
3. Relevant source code and tests
4. Relevant configs and manifests
5. Relevant manuscript text, if any

Do not rely on memory. Do not rely on archived or stale roadmap context.

---

## 2. Core Scientific Invariants

Check these whenever touching datp-cp code:

1. Calibration-channel poisoning only — never poison training data, model weights, aggregation, or test data.
2. Injection rule is `REPLACE_FIXED_BUDGET`: replace `m_i = max(1, round(f·n_i))` positions with values resampled **with replacement** from the victim-local reservoir.
3. Clean calibration arrays must never be mutated in place; always work on a copy.
4. Reservoirs must be victim-local benign calibration scores. Test scores and training scores are never reservoirs.
5. Attack-labeled samples must not enter calibration.
6. Poisoning seed controls only replacement-position and reservoir-sampling randomness. Training is unaffected.
7. AUROC must remain invariant because test scores and labels are unchanged by a calibration-channel attack.
8. `GLOBAL_THRESHOLD`, `LOCAL_THRESHOLD`, and `CLUSTER_THRESHOLD` are the only valid threshold policies.
9. `CLUSTER_THRESHOLD` for N-BaIoT uses fixed `K=3`, k-means++, `n_init=10`, `max_iter=300`, `random_state=42`; fingerprint is `[mean, std, skew, p95]`; all deltas use client-effective thresholds, never raw cluster label IDs.
10. `CV(FPR)` uses `std(..., ddof=0) / mean(...)` over eligible clients; no epsilon denominator; `CV` is undefined when mean FPR is zero.
11. Two-layer statistics: per-victim paired seed deltas → 5 seed aggregates → bootstrap CI. Never treat 9×5 as 45 independent samples.
12. `mu_flag_threshold` must be locked from clean artifacts before any poisoned run.
13. `q = 95` threshold percentile is locked; no poisoned run may alter `q`.
14. `ε_num = 1e-12` is locked for all stabilized ratios.
15. Edge-IIoTset is forbidden. CICIoT2023 is optional stretch contrast only, never main evidence.

---

## 3. Policy Invariant Checklist

### `GLOBAL_THRESHOLD`

Required:

1. One shared threshold computed from eligible clients' local calibration thresholds.
2. `τ_global = mean(τ_i_local)` over eligible clients.
3. Every eligible client receives the same threshold.
4. No attack labels in calibration.

### `LOCAL_THRESHOLD`

Required:

1. Per-eligible-client threshold at `q = 95`.
2. Direct victim sensitivity; no cross-client spillover by design.
3. No attack labels in calibration.

### `CLUSTER_THRESHOLD`

Required:

1. Fingerprint `[mean, std, skew, p95]` over benign calibration errors.
2. Clustering on eligible clients only; ineligible clients excluded.
3. Client-effective threshold delta `Δτ_i = τ_i_eff,poisoned - τ_i_eff,clean`.
4. Raw cluster label IDs never compared directly.
5. `K = 3` locked for N-BaIoT main.
6. Mandatory decomposition outputs: `Δτ_total`, `Δτ_aggregation`, `Δτ_churn`.
7. Diagnostic outputs: `Δτ_frozen_scaler`, `Δτ_normalization_gap`.

---

## 4. Attack Validity Checklist

| Source strategy     | Valid objective   |
|---------------------|-------------------|
| `HIGH_SCORE_BENIGN` | `THRESHOLD_RAISE` |
| `LOW_SCORE_BENIGN`  | `THRESHOLD_LOWER` |
| `RANDOM_BENIGN`     | Either (as negative control) |

Invalid main combinations that must fail config validation:

```text
HIGH_SCORE_BENIGN + THRESHOLD_LOWER
LOW_SCORE_BENIGN  + THRESHOLD_RAISE
```

---

## 5. Stage Boundary Checklist

Valid stage flow:

```text
prepare → score → threshold/result → report
```

Forbidden crossings:

1. Threshold module calls training.
2. Result module prepares data.
3. Reporting module recomputes scores.
4. Figure/table code recomputes metrics from raw data.
5. CLI command silently performs multiple scientific stages without clear naming.
6. Stored-score analysis retrains.

---

## 6. Metric Checklist

Required context around every reported metric:

1. Eligible client count and seed count.
2. Coverage ratio when CV(FPR) is shown.
3. Absolute dispersion metrics (`IQR(FPR)`, `max-min FPR`, `WorstClientFPR`) alongside any CV.
4. Delta definition and materiality threshold `δτ_i`.
5. Bootstrap CI when required.
6. Sign consistency across seeds (≥4/5 required for primary claims).

Reject:

1. CV(FPR) alone without coverage or absolute dispersion.
2. Claims based on single-seed results.
3. Missing materiality definition.
4. AUROC movement (must be zero; any movement signals implementation error).

---

## 7. Claim Checklist

Allowed if the primary claim gate is met:

```text
datp-cp shows that calibration-channel poisoning can materially shift threshold policies
while training, aggregation, model parameters, and test data remain clean.
```

Forbidden:

1. Universal threshold vulnerability claim.
2. Universal threshold robustness claim.
3. Raw-traffic attack realizability claim.
4. Broad FL robustness claim.
5. Privacy guarantee claim.
6. Deployment-readiness claim.
7. Model-poisoning, training-poisoning, aggregation-poisoning, backdoor, or evasion claim.
8. Claims from diagnostic-only variants as main evidence.
9. Multi-client claims from single-client data.

---

## 8. Required Output

```text
# DATP Invariant Check

Verdict:
Scope:
Files inspected:
Commands run:

## Core Invariants
1. Calibration-only isolation:
2. REPLACE_FIXED_BUDGET:
3. No in-place mutation:
4. Reservoir validity:
5. AUROC invariance:
6. q=95 locked:
7. ε_num locked:

## Policy Checks
GLOBAL_THRESHOLD:
LOCAL_THRESHOLD:
CLUSTER_THRESHOLD:

## Attack Validity
Source-objective pairs:
Config validation:

## Stage Boundaries
prepare → score:
score → threshold/result:
threshold/result → report:

## Metrics
CV(FPR) context:
Materiality:
Statistics:

## Claims
Allowed claims:
Rejected claims:
Required wording changes:

## Final Decision
Can proceed:
Reason:
Invalidation rule:
```
