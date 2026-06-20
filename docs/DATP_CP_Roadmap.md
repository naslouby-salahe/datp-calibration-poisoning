# datp-cp Research Protocol

## Calibration-Channel Poisoning of Federated Threshold Personalization in IoT Anomaly Detection: A Policy-Differentiated Vulnerability Analysis

**Status:** pre-registered empirical roadmap ready for final audit and protocol-lock validation. N-BaIoT main execution is gated on audit pass, clean-artifact provenance, synthetic smoke pass, and `CLUSTER_THRESHOLD` reproducibility.

> **Core hypothesis:** datp-cp tests whether poisoning only benign threshold-calibration data can shift threshold policies enough to induce detection degradation under threshold-raising attacks or alarm-burden degradation under threshold-lowering attacks, while training data, aggregation, model parameters, test scores, and test labels remain clean and unchanged.
>
> **Main confirmatory scope:** all eligible single-client victims on N-BaIoT.
>
> **Optional full extension:** all feasible eligible pairs and a deterministic pre-registered sample of triples. Claims about one-to-three-client compromise require this extension. The main study alone supports only single-client compromise claims.
>
> **Policy names:** `GLOBAL_THRESHOLD`, `LOCAL_THRESHOLD`, and `CLUSTER_THRESHOLD`. These correspond to the previous global, local, and cluster threshold policies; stale operational labels are not used.
>
> **Threshold percentile:** all local threshold components use the locked percentile `q = 95`.
>
> **Primary claim gate:** a claim requires material correctly signed `Δτ` plus interpretable downstream movement under paired clean-vs-poisoned comparison.

---

## 1. Paper Identity

**Project shorthand:** `datp-cp`.

**Working title:** Calibration-Channel Poisoning of Federated Threshold Personalization in IoT Anomaly Detection: A Policy-Differentiated Vulnerability Analysis.

**One-sentence identity:** datp-cp isolates the threshold-calibration channel as an attack surface and measures whether contaminating only benign calibration data changes operating points enough to create detection or alarm-burden failures.

**Scientific contribution:** datp-cp does not introduce a new federated optimizer, model architecture, personalization algorithm, privacy mechanism, or deployment system. It isolates a post-training threshold-calibration vulnerability in a federated IoT anomaly-detection pipeline.

**Causal isolation:** clean and poisoned comparisons share the same training seed, model parameters, aggregation process, clean test scores, clean test labels, victim plan, and threshold policy. Poisoning is the only stochastic difference.

**Primary dataset:** N-BaIoT, using physical devices as clients.

**Primary object of study:** threshold-stage isolation, not score-distribution learning. AUROC invariance is a sanity check confirming that the score geometry and test labels were not changed; it is not a contribution.

**Manuscript vocabulary:**

* calibration-channel poisoning;
* threshold-stage isolation;
* per-device FPR disparity;
* operating-point disparity;
* alarm-burden predictability;
* score-level proxy limitation.

**Forbidden framing:**

* no universal vulnerability claim;
* no broad FL robustness claim;
* no privacy guarantee claim;
* no deployment-readiness claim;
* no raw-traffic realizability claim from score-level results;
* no training-poisoning, model-poisoning, aggregation-poisoning, backdoor, or evasion claim.

---

## 2. Scope and Non-Negotiables

### 2.1 Included scope

The protocol includes:

* N-BaIoT main study;
* `GLOBAL_THRESHOLD`, `LOCAL_THRESHOLD`, and `CLUSTER_THRESHOLD`;
* benign calibration-score poisoning only;
* score-level proxy attack;
* fixed-size replacement;
* victim-local reservoirs;
* all eligible single-client victims in the main study;
* paired clean-vs-poisoned comparisons;
* five paired training and poisoning seeds;
* optional full extension with all feasible eligible pairs and deterministic eligible triples;
* optional `TRIMMED_CALIBRATION` defense only if it passes pre-specified gates.

### 2.2 Excluded scope

The protocol excludes:

* journal-extension datasets as main evidence;
* Edge-IIoTset;
* journal-only threshold variants;
* conformal thresholding;
* temporal recalibration;
* FedProx, Ditto, FedRep, FedPer, FedBN, or other model-personalization comparators;
* training-data poisoning;
* model poisoning;
* aggregation poisoning;
* Byzantine aggregation studies;
* backdoor attacks;
* evasion attacks;
* privacy mechanisms;
* privacy guarantees;
* deployment, latency, memory, communication, or energy claims;
* raw-traffic injection claims;
* broad “secure FL” or “robust FL” language.

### 2.3 Main versus optional claim boundary

The main confirmatory study supports only single-client compromise claims.

The optional full extension may support limited one-to-three-client compromise claims only if:

* pairs and triples are executed exactly as pre-registered;
* paired clean-vs-poisoned semantics are preserved;
* claim gates are met separately for the multi-client stage;
* multi-client results are not inferred from single-client results.

### 2.4 Non-negotiable isolation rules

The attack may modify only benign threshold-calibration data.

The attack must not modify:

* training data;
* training labels;
* local model updates;
* global aggregation;
* model parameters;
* test scores;
* test labels;
* client eligibility logic;
* threshold-policy definitions after lock.

Test scores are never reservoirs. Training scores are never reservoirs. Attack labels never enter calibration.

Candidate reservoirs, if available, must be benign and victim-local. Cross-client reservoirs are diagnostic-only and cannot support main claims.

---

## 3. Research Questions

### 3.1 Main research question

Does poisoning only the benign threshold-calibration set of eligible clients shift threshold policies enough to induce interpretable downstream failures, and do `GLOBAL_THRESHOLD`, `LOCAL_THRESHOLD`, and `CLUSTER_THRESHOLD` exhibit different vulnerability profiles?

### 3.2 Confirmatory research questions

**RQ1 — Threshold mechanism:**
Does calibration-only poisoning produce material, correctly signed `Δτ` under the gray-box score-access threat model?

**RQ2 — Policy differentiation:**
Do `GLOBAL_THRESHOLD`, `LOCAL_THRESHOLD`, and `CLUSTER_THRESHOLD` differ in victim sensitivity, blast radius, spillover, and operating-point disparity?

**RQ3 — Objective differentiation:**
Do threshold-raising and threshold-lowering attacks produce separable failure modes?

* Threshold raising is evaluated through victim detection degradation.
* Threshold lowering is evaluated through alarm-burden and FPR-dispersion degradation.

**RQ4 — Single-client compromise:**
Across all eligible N-BaIoT victims, does single-client calibration compromise produce consistent effects under paired seeds?

### 3.3 Optional research questions

**RQ5 — Limited multi-client compromise:**
Do pre-registered pairs and triples amplify or change the policy-differentiated vulnerability profile?

**RQ6 — Lightweight mitigation:**
Can `TRIMMED_CALIBRATION` reduce the declared primary harm metric without material clean-setting regression?

---

## 4. Threat Model

### 4.1 Main adversary

The main adversary compromises the local calibration-curation process of an eligible client after training and before threshold computation.

The adversary can:

* influence which benign local records are admitted to or retained in the victim’s calibration buffer;
* score local benign candidate records using the locally available model;
* choose high-score or low-score benign candidates according to the declared source strategy.

The adversary cannot:

* alter training data;
* alter model weights;
* alter gradients or updates;
* alter server aggregation;
* alter test scores;
* alter test labels;
* observe or use other clients’ raw data;
* insert attack-labeled samples into calibration;
* poison the evaluation set.

### 4.2 Knowledge model

The main study uses:

```text
PoisoningKnowledge = GRAY_BOX_SCORE_ACCESS
```

This means the attacker has local reconstruction scores for local benign candidate records. This is justified because each FL client holds the trained anomaly detector and can score its own local candidates.

### 4.3 Attack objectives

```text
AttackerObjective =
  THRESHOLD_RAISE
  THRESHOLD_LOWER
```

`THRESHOLD_RAISE` attempts to increase the victim-effective threshold, causing missed detections.

`THRESHOLD_LOWER` attempts to decrease the victim-effective threshold, increasing false alarms or operating-point disparity.

### 4.4 Valid source-objective pairs

Only the following source-objective combinations are valid in the main matrix:

| Source strategy     | Valid objective role                                                           | Main interpretation                                                     |
| ------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| `HIGH_SCORE_BENIGN` | `THRESHOLD_RAISE`                                                              | Directional raising attack                                              |
| `LOW_SCORE_BENIGN`  | `THRESHOLD_LOWER`                                                              | Directional lowering attack                                             |
| `RANDOM_BENIGN`     | objective-matched negative control for `THRESHOLD_RAISE` and `THRESHOLD_LOWER` | Same random operation, evaluated against the matched directional attack |

Invalid main combinations:

```text
HIGH_SCORE_BENIGN + THRESHOLD_LOWER
LOW_SCORE_BENIGN + THRESHOLD_RAISE
```

These invalid combinations must fail config validation.

`RANDOM_BENIGN` is operationally objective-independent, but it may be recorded under the matched objective label so that each directional attack has a paired negative control.

### 4.5 Threat-model variants

```text
MINIMAL_NEGATIVE_CONTROL
```

Uses `RANDOM_BENIGN`. It is expected to be near-null and is used to audit threshold instability and injector correctness.

```text
MAIN_GRAY_BOX
```

Uses victim-local score access and benign candidate reservoirs. This is the only variant that supports main claims.

```text
DIAGNOSTIC_UPPER_BOUND
```

Uses direct score edits or stronger-than-main reservoir access. It is appendix-only and cannot support main claims.

### 4.6 Score-level proxy limitation

datp-cp operates at the reconstruction-score level. This isolates the calibration stage, but it does not prove that an attacker can generate raw network traffic with arbitrary target scores. All raw-traffic realizability claims are out of scope.

At high poison fractions, with-replacement score resampling can duplicate score values. This is disclosed as a proxy limitation, not hidden as realistic traffic generation.

---

## 5. Experiment Stages

### 5.1 `FINAL_AUDIT`

Purpose:

* confirm protocol consistency;
* confirm absence of stale policy labels in code-facing contracts;
* confirm clean-artifact provenance;
* confirm no journal-scope contamination;
* confirm cluster-threshold reproducibility;
* lock materiality and instability thresholds before poisoned execution.

N-BaIoT main execution cannot begin until this stage passes.

### 5.2 `SYNTHETIC_SMOKE`

Purpose:

* validate poisoning invariants on controlled score arrays;
* verify threshold direction;
* verify no in-place mutation;
* verify deterministic paired outputs;
* verify cluster-threshold decomposition;
* verify AUROC invariance under unchanged test scores.

Failure blocks N-BaIoT main execution.

### 5.3 `NBAIOT_MAIN`

Primary confirmatory study.

Scope:

* N-BaIoT;
* physical device equals client;
* all eligible single-client victims;
* policies `{GLOBAL_THRESHOLD, LOCAL_THRESHOLD, CLUSTER_THRESHOLD}`;
* valid source-objective pairs only;
* fractions `{0, 0.10, 0.20, 0.40}`;
* five paired seeds.

### 5.4 `NBAIOT_FULL_OPTIONAL`

Optional full extension.

Scope:

* all feasible eligible pairs;
* deterministic eligible triples sampled from lexicographic triples using `compromise_pattern_seed = 400`;
* optional fraction `0.05` only if locked before execution;
* optional defense;
* optional mandatory-for-cluster diagnostics if `CLUSTER_THRESHOLD` is included.

The optional full extension is not required for the main single-client paper claim.

### 5.5 `STRETCH_DIAGNOSTIC_ONLY`

Optional contrast stage.

Allowed only if it remains clearly diagnostic and does not introduce journal-scope claims.

CICIoT2023 may be used only as a pseudo-client contrast if artifact semantics and client definitions are safe. It cannot support natural-device claims.

---

## 6. Dataset and Clean Artifact Rules

### 6.1 Primary dataset

```text
Dataset = N_BAIOT
ClientDefinition = PHYSICAL_DEVICE
K = 9
```

Each physical device is treated as one client.

### 6.2 Split semantics

The clean pipeline must preserve the inherited DATP-style split semantics:

* benign training data for model learning;
* benign calibration data for threshold computation;
* held-out test scores and labels for evaluation;
* no overlap between calibration reservoirs and test data;
* no attack-labeled records in calibration.

### 6.3 Clean artifact provenance

Before protocol lock, the audit must confirm that clean artifacts are:

* generated inside the datp-cp repository or explicitly reproduced there;
* produced under conference-faithful `E=1` settings;
* tied to exact code commit, config, and seed;
* tied to the correct client identity;
* tied to the correct split;
* complete for calibration scores and test scores;
* free of journal-only threshold variants;
* free of test-score leakage into calibration or reservoirs;
* compatible with all three threshold policies.

If clean artifacts fail provenance, the clean baseline must be regenerated inside the datp-cp repository before poisoned runs.

### 6.4 Clean retraining contingency

Clean retraining is allowed only if clean artifacts fail audit.

Retraining must follow the inherited DATP clean reproduction protocol exactly:

```text
model_family = autoencoder
federated_algorithm = FedAvg
local_epochs = 1
participation = full
aggregation_weighting = local benign training sample count
initial_round_budget = 40
maximum_round_budget = 150
split_semantics = inherited DATP chronological train / calibration / test semantics
threshold_percentile_q = 95
```

Architecture, optimizer, loss function, preprocessing, normalization, convergence criterion, and checkpoint-selection rule must be inherited from the confirmed DATP conference clean pipeline.

Checkpoint selection rule:

* choose the checkpoint selected by the inherited DATP clean reproduction protocol;
* if the inherited protocol selects by convergence, use the first checkpoint satisfying the locked convergence criterion;
* if no convergence checkpoint is reached before the maximum round budget, use the final round and mark the run as `MAX_ROUND_CHECKPOINT`;
* never choose a checkpoint by poisoned performance.

No hyperparameter tuning against poisoned outcomes is allowed.

Safe wording:

> Clean baselines were regenerated under the locked DATP clean reproduction protocol before any poisoned condition was executed.

### 6.5 Eligibility

A client is eligible if:

```text
n_cal >= 100
```

Eligible clients:

* can be victims;
* contribute to threshold-policy computation;
* enter eligible-client dispersion metrics.

Ineligible clients:

* cannot be victims;
* do not contribute to `GLOBAL_THRESHOLD`;
* do not enter `CLUSTER_THRESHOLD` clustering;
* do not enter `CV(FPR)` claims;
* may receive fallback thresholds only if the clean pipeline already defines such behavior.

### 6.6 Reservoir rules

Reservoirs must satisfy:

```text
reservoir.client_id == victim.client_id
reservoir.label == benign
reservoir.split != test
reservoir.split != training
```

Allowed reservoirs:

* victim-local benign calibration-candidate scores not used to compute the clean threshold, if available;
* otherwise victim-local benign calibration-score values under score-level resampling, with the abstraction recorded in the manifest.

Forbidden reservoirs:

* test scores;
* training scores;
* attack-labeled scores;
* other-client scores for main claims;
* post-hoc values derived from poisoned test outcomes.

Cross-client reservoirs are diagnostic-only and must be labeled as outside the main threat model.

---

## 7. Threshold Policies

### 7.1 Policy enum

```text
ThresholdPolicy =
  GLOBAL_THRESHOLD
  LOCAL_THRESHOLD
  CLUSTER_THRESHOLD
```

No stale operational names are used in code-facing configs, manifests, tables, or figures.

### 7.2 Locked percentile

All local threshold components use:

```text
threshold_percentile_q = 95
```

This percentile applies to:

* `LOCAL_THRESHOLD`;
* each client-local component used to compute `GLOBAL_THRESHOLD`;
* each client-local component used inside `CLUSTER_THRESHOLD`;
* clean and poisoned threshold recomputation;
* optional `TRIMMED_CALIBRATION` after trimming.

No poisoned run may alter `q`.

### 7.3 `GLOBAL_THRESHOLD`

`GLOBAL_THRESHOLD` computes one shared threshold from eligible clients’ local clean or poisoned calibration thresholds.

Definition:

```text
τ_i_local = percentile_95(S_i_cal)
τ_global = mean_i(τ_i_local) over eligible clients
```

Every eligible client receives the same threshold.

Primary interpretation:

* diluted victim sensitivity;
* possible cross-client spillover;
* shared operating-point shift.

### 7.4 `LOCAL_THRESHOLD`

`LOCAL_THRESHOLD` computes one threshold per eligible client.

Definition:

```text
τ_i_local = percentile_95(S_i_cal)
```

where `S_i_cal` is the client’s benign calibration-score distribution under clean or poisoned condition.

Primary interpretation:

* direct victim sensitivity;
* minimal cross-client spillover;
* strongest test of calibration personalization fragility.

### 7.5 `CLUSTER_THRESHOLD`

`CLUSTER_THRESHOLD` computes client fingerprints from calibration errors, clusters clients, and assigns each client a cluster-level threshold.

Fingerprint:

```text
v_i = [mean(S_i_cal), std(S_i_cal), skew(S_i_cal), p95(S_i_cal)]
```

N-BaIoT main clustering rule:

```text
scaler = StandardScaler
algorithm = k-means++
K = 3
n_init = 10
max_iter = 300
random_state = 42
```

Cluster threshold:

```text
τ_i_local = percentile_95(S_i_cal)
τ_cluster_c = mean(τ_i_local) for eligible clients assigned to cluster c
```

Client-effective threshold:

```text
τ_i_eff = τ_cluster_assignment(i)
```

All `CLUSTER_THRESHOLD` deltas are client-effective threshold deltas:

```text
Δτ_i = τ_i_eff,poisoned - τ_i_eff,clean
```

Raw cluster label IDs are never compared directly.

### 7.6 Cluster-count lock

Cluster-count changes are forbidden for N-BaIoT main.

```text
K = 3
```

Poisoning may change fingerprints, scaler statistics, assignments, and client-effective thresholds. It may not change the policy definition or cluster count.

### 7.7 Main cluster total effect

The main `CLUSTER_THRESHOLD` total effect refits the scaler because the deployed policy recomputes fingerprints and normalization from the available calibration population.

This total effect captures:

* within-cluster threshold aggregation changes;
* reassignment effects;
* normalization-mediated effects.

### 7.8 Cluster decomposition: mandatory versus diagnostic outputs

Mandatory for `CLUSTER_THRESHOLD` claims:

```text
Δτ_i_total
Δτ_i_aggregation
Δτ_i_churn
```

Diagnostic but required for audit completeness:

```text
Δτ_i_frozen_scaler
Δτ_i_normalization_gap
```

Definitions:

```text
Δτ_i_total = τ_i_eff,poisoned_full_refit - τ_i_eff,clean
```

```text
Δτ_i_aggregation = τ_i_eff,poisoned_clean_assignment - τ_i_eff,clean
```

```text
Δτ_i_churn = Δτ_i_total - Δτ_i_aggregation
```

Frozen-clean-scaler diagnostic:

```text
Δτ_i_frozen_scaler = τ_i_eff,poisoned_frozen_clean_scaler - τ_i_eff,clean
```

Normalization-mediated gap:

```text
Δτ_i_normalization_gap = Δτ_i_total - Δτ_i_frozen_scaler
```

The frozen-clean-scaler variant is diagnostic only. The main reported cluster effect remains the deployed full-refit total effect.

---

## 8. Attack Design

### 8.1 Injection rule

```text
CalibrationInjectionRule = REPLACE_FIXED_BUDGET
```

For victim `i` and poison fraction `f`:

```text
m_i = 0                         if f = 0
m_i = max(1, round(f * n_i))    if f > 0
```

The injector selects `m_i` positions in the victim’s benign calibration array and replaces them with values sampled with replacement from the declared victim-local reservoir.

Calibration size remains constant.

### 8.2 Fractions

Main fractions:

```text
poison_fraction = {0, 0.10, 0.20, 0.40}
```

Optional full extension may add:

```text
poison_fraction = 0.05
```

only if locked before full-extension execution.

### 8.3 Source strategies

```text
PoisoningSourceStrategy =
  RANDOM_BENIGN
  HIGH_SCORE_BENIGN
  LOW_SCORE_BENIGN
  LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY
```

### 8.4 Main source-objective matrix

The main matrix contains only:

```text
RANDOM_BENIGN + THRESHOLD_RAISE
RANDOM_BENIGN + THRESHOLD_LOWER
HIGH_SCORE_BENIGN + THRESHOLD_RAISE
LOW_SCORE_BENIGN + THRESHOLD_LOWER
```

`RANDOM_BENIGN + THRESHOLD_RAISE` is the objective-matched negative control for `HIGH_SCORE_BENIGN + THRESHOLD_RAISE`.

`RANDOM_BENIGN + THRESHOLD_LOWER` is the objective-matched negative control for `LOW_SCORE_BENIGN + THRESHOLD_LOWER`.

The random operation is identical across objective labels; the label only determines which directional attack it audits.

### 8.5 `RANDOM_BENIGN`

`RANDOM_BENIGN` samples from the victim-local benign reservoir without tail targeting.

Role:

* negative control;
* injector sanity check;
* calibration natural-instability check.

Expected behavior:

```text
near-null
```

Near-null is evaluated at the seed-level aggregate, consistent with the two-layer statistical plan.

For each seed, compute the mean `|Δτ|` over all eligible and feasible victims for the `RANDOM_BENIGN` cell. Then compute the median across the five seed-level aggregates.

Absolute near-null criterion:

```text
median_seed(mean_victim(|Δτ_RANDOM|)) < median_seed(mean_victim(δτ_i))
```

Relative near-null criterion, applied only when the matched directional attack at the same policy, objective, and fraction is material:

```text
median_seed(mean_victim(|Δτ_RANDOM|))
  < 0.25 * median_seed(mean_victim(|Δτ_MATCHED_DIRECTIONAL|))
```

A `RANDOM_BENIGN` deviation is an audit flag. It is not an automatic kill trigger.

### 8.6 `HIGH_SCORE_BENIGN`

`HIGH_SCORE_BENIGN` samples from the victim-local upper 10% benign score tail.

Used only for:

```text
THRESHOLD_RAISE
```

Expected threshold sign:

```text
Δτ > 0
```

Expected downstream direction:

* negative victim `ΔTPR`;
* negative victim `ΔBA`;
* negative victim `ΔMacroF1`.

### 8.7 `LOW_SCORE_BENIGN`

`LOW_SCORE_BENIGN` samples from the victim-local lower 10% benign score tail.

Used only for:

```text
THRESHOLD_LOWER
```

Expected threshold sign:

```text
Δτ < 0
```

Expected downstream direction:

* positive `ΔCV(FPR)`;
* positive `ΔWorstClientFPR`;
* positive `ΔIQR(FPR)`;
* positive `Δmax-min FPR`.

Lowering success is conditional because random fixed-budget insertion of low scores may fail to lower a high percentile unless upper-tail support is displaced.

### 8.8 `LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY`

This variant replaces upper-tail calibration positions with lower-tail benign values.

It is used only if the main lowering attack is null and the protocol needs to distinguish a robust calibration channel from a weak lowering instantiation.

It cannot support main claims.

### 8.9 Tail feasibility

Tail mass is fixed at:

```text
tail_mass = 0.10
```

A victim-source cell is infeasible if the relevant tail contains fewer than two distinct values in any paired training seed.

If a victim-fraction-source cell is infeasible in any seed, it is excluded consistently across seeds and reported in the infeasibility manifest.

### 8.10 Target scopes

```text
PoisoningTargetScope =
  SINGLE_CLIENT
  MULTI_CLIENT
  ALL_CLIENTS_DIAGNOSTIC_ONLY
```

`SINGLE_CLIENT` is the main confirmatory scope.

`MULTI_CLIENT` is optional full extension only.

`ALL_CLIENTS_DIAGNOSTIC_ONLY` cannot support main claims.

### 8.11 Optional multi-client sampling rule

For optional full extension:

* run all feasible eligible pairs if compute allows;
* if all feasible pairs are not compute-feasible, run the first `N_pair_lock` feasible pairs in lexicographic order after locking `N_pair_lock` before execution;
* for triples, enumerate all feasible eligible triples in lexicographic client-ID order;
* sample exactly `N_triple_lock` triples using `compromise_pattern_seed = 400`;
* lock `N_triple_lock` before execution;
* record the selected pairs and triples in `multi_client_plan.json`;
* never select pairs or triples after inspecting poisoned outcomes.

Default triple count if not otherwise locked:

```text
N_triple_lock = min(12, number_of_feasible_eligible_triples)
```

### 8.12 Seed pairing

Each poisoned condition is paired with its clean counterpart by:

* `training_seed`;
* victim identity or victim set;
* threshold policy;
* objective;
* source strategy;
* fraction.

Poisoning seed controls only the replacement-position and reservoir-sampling randomness.

---

## 9. Calibration and Eligibility Rules

### 9.1 Calibration semantics

Threshold calibration uses benign calibration scores only.

Attack-labeled samples do not enter calibration.

Test labels and test scores do not influence threshold computation.

### 9.2 Victim eligibility

A victim must satisfy:

```text
n_cal >= 100
```

A victim must have a feasible reservoir for the requested source strategy.

### 9.3 Materiality threshold

For victim `i`:

```text
δτ_i_raw = 0.1 * IQR(S_i_cal_clean)
```

A clean-artifact-derived floor is locked before poisoned runs:

```text
δτ_floor = 0.01 * median_j(IQR(S_j_cal_clean))
```

The `0.01` multiplier is a policy floor representing 1% of the typical cross-client clean calibration spread, preventing microscopic shifts from being counted as material on unusually tight score distributions.

Final threshold materiality:

```text
δτ_i = max(δτ_i_raw, δτ_floor)
```

If `IQR(S_i_cal_clean) = 0`, use:

```text
MAD(S_i_cal_clean)
```

If both IQR and MAD are zero, use the smallest positive clean calibration score gap for that client. If no positive gap exists, the client is marked degenerate for threshold-shift materiality and excluded from threshold-shift claims.

### 9.4 Numerical epsilon

All divisions using numerical stabilization use the locked constant:

```text
ε_num = 1e-12
```

`ε_num` must be stored in config and manifests.

This applies to:

* `Δτ_rel`;
* recovery denominator fallback;
* any explicitly stabilized diagnostic ratio.

### 9.5 Clean regression threshold for optional defense

Before defense execution, lock the clean-setting regression threshold for the declared clean metric.

A defense causes material clean regression if it worsens the clean metric by more than the locked clean-regression threshold.

### 9.6 Locked instability threshold for CV

Before poisoned execution, lock:

```text
mu_flag_threshold
```

from clean eligible-client FPR values across clean policies.

Rule:

```text
mu_flag_threshold =
  smallest_positive_mean_FPR_across_clean_policies / 8
```

where `mean_FPR` is computed over eligible clients for:

```text
GLOBAL_THRESHOLD
LOCAL_THRESHOLD
CLUSTER_THRESHOLD
```

If no positive clean eligible-client mean FPR exists across policies, all CV-based claims are disabled and absolute dispersion metrics become primary for FPR disparity.

---

## 10. Metrics

### 10.1 Mechanism endpoint

Primary mechanism endpoint:

```text
Δτ_i,p = τ_i,p,poisoned - τ_i,p,clean
```

Also report:

```text
|Δτ_i,p|
Δτ_rel_i,p = Δτ_i,p / max(|τ_i,p,clean|, ε_num)
```

A threshold shift is material if:

```text
|Δτ_i,p| >= δτ_i
```

A threshold shift is correctly signed if:

```text
Δτ_i,p >= δτ_i      for THRESHOLD_RAISE
Δτ_i,p <= -δτ_i     for THRESHOLD_LOWER
```

### 10.2 Downstream movement

A primary claim requires material correctly signed `Δτ` plus downstream movement.

Downstream movement is directional, but it must survive paired seed-level aggregation and be visible in reported effect sizes. Tiny single-cell numerical sign changes do not satisfy the gate by themselves.

For `THRESHOLD_RAISE`, downstream movement is interpretable if at least one of the following is correctly signed at the paired seed-aggregate level:

```text
ΔTPR_victim < 0
ΔBA_victim < 0
ΔMacroF1_victim < 0
```

For `THRESHOLD_LOWER`, downstream movement is interpretable if at least one of the following is correctly signed at the paired seed-aggregate level:

```text
ΔCV(FPR) > 0
ΔWorstClientFPR > 0
ΔIQR(FPR) > 0
Δmax-min FPR > 0
```

Downstream movement does not require a separate materiality threshold unless a metric-specific threshold is locked before poisoned execution. Direction, seed-aggregate persistence, and visible effect-size reporting are required.

### 10.3 Detection metrics

Report per client and aggregate where appropriate:

```text
TPR
FPR
TNR
BA
MacroF1
P10_MacroF1
WorstClientBA
WorstClientFPR
```

### 10.4 Dispersion metrics

Primary FPR-dispersion metrics:

```text
CV(FPR)
IQR(FPR)
max-min FPR
WorstClientFPR
```

`CV(FPR)` is computed over eligible clients only:

```text
CV(FPR) = std(FPR_i, ddof=0) / mean(FPR_i)
```

`ddof=0` is locked because the eligible client set is the complete descriptive population for the executed cell, not a sample used to estimate a larger hidden client population.

No denominator stabilizer is used.

### 10.5 CV zero and near-zero behavior

If eligible-client mean FPR is zero:

```text
CV(FPR) = undefined
```

That cell is excluded from CV-based claims.

If eligible-client mean FPR is below `mu_flag_threshold`, report `CV(FPR)` with an instability flag.

Unstable CV can be interpreted only alongside:

```text
IQR(FPR)
max-min FPR
WorstClientFPR
```

Absolute dispersion metrics remain valid even when CV is undefined or unstable.

### 10.6 Blast radius and spillover

For each poisoned cell:

```text
BlastRadius = number of non-victim eligible clients with material |Δτ|
```

```text
SpilloverCount = number of non-victim eligible clients with correctly signed downstream degradation
```

For `GLOBAL_THRESHOLD`, spillover is expected because all clients receive the same threshold.

For `LOCAL_THRESHOLD`, spillover should be near-zero.

For `CLUSTER_THRESHOLD`, spillover may arise through cluster aggregation, reassignment, or normalization-mediated effects.

### 10.7 AUROC sanity check

AUROC is computed on unchanged test scores and labels.

Expected behavior:

```text
ΔAUROC = 0
```

Any material AUROC movement indicates protocol leakage or implementation error.

AUROC invariance confirms threshold-stage isolation. It is not a claimed contribution.

---

## 11. Statistical Plan

### 11.1 Paired design

All comparisons are paired by:

* `training_seed`;
* victim plan;
* threshold policy;
* valid source-objective pair;
* fraction.

The clean and poisoned cells differ only by the poisoning intervention.

### 11.2 Seeds

```text
training_seed = [0, 1, 2, 3, 4]
poisoning_seed = [100, 101, 102, 103, 104]
analysis_seed = [300, 301, 302, 303, 304]
```

If new splits are generated:

```text
split_seed = [200, 201, 202, 203, 204]
```

Optional multi-client compromise pattern seed:

```text
compromise_pattern_seed = 400
```

### 11.3 Two-layer unit of analysis

Layer 1: victim-level paired deltas.

Used for:

* victim heterogeneity;
* sign consistency;
* strict-majority victim support.

Layer 2: seed-level aggregates.

For each policy-objective-source-fraction cell, compute one aggregate per `training_seed` by averaging over all eligible and feasible victims.

Primary confidence intervals operate on the five seed-level aggregates, not on the victim-seed grid as if all entries were independent.

### 11.4 Sign consistency

A victim-level directional effect is seed-consistent if the expected sign appears in at least:

```text
4 / 5 seeds
```

### 11.5 Strict-majority victim rule

A policy-level claim requires a strict majority of eligible and feasible victims to meet the claim gate.

For nine eligible N-BaIoT clients:

```text
strict_majority = 5
```

### 11.6 Primary claim gate

A primary claim requires:

1. material `Δτ`;
2. correct sign;
3. sign consistency in at least `4/5` seeds;
4. strict-majority victim support;
5. interpretable downstream movement visible at paired seed-aggregate level;
6. no unresolved audit flag from `RANDOM_BENIGN`, AUROC movement, reservoir leakage, or cluster-count drift.

### 11.7 Confidence intervals

Use 95% bootstrap confidence intervals over seed-level aggregates.

Default:

```text
percentile bootstrap
```

Use BCa only if the inherited implementation is confirmed and stable at `n=5`.

### 11.8 Supporting test

Use an exact paired sign test on the five seed-level aggregates as supporting evidence only.

P-values do not gate inference at five seeds. The primary gate is the pre-specified claim rule.

### 11.9 Multiple comparisons

Holm-adjusted p-values are descriptive within the primary family:

```text
Dataset = N_BAIOT
Scope = SINGLE_CLIENT
Policies = GLOBAL_THRESHOLD, LOCAL_THRESHOLD, CLUSTER_THRESHOLD
SourceObjectivePairs =
  HIGH_SCORE_BENIGN + THRESHOLD_RAISE
  LOW_SCORE_BENIGN + THRESHOLD_LOWER
Fractions = 0.10, 0.20, 0.40
```

`RANDOM_BENIGN` is analyzed as a negative-control audit family, not as a primary directional attack family.

### 11.10 Ten-seed expansion

Expand to ten seeds only if:

* sign consistency is borderline;
* policy ordering flips across seeds;
* seed variance is large enough to threaten the main conclusion;
* a claim rests on one unstable seed;
* reviewer-facing evidence would otherwise be ambiguous.

Ten-seed expansion must preserve pairing and cannot alter the locked matrix.

---

## 12. Implementation Contract

### 12.1 Repository

```text
/home/naslouby/Projects/datp-calibration-poisoning
```

### 12.2 Raw data

```text
data/raw -> /home/naslouby/Projects/datp-shared-data/raw
```

Raw data is read-only.

### 12.3 Output root

```text
outputs/conference_calibration_poisoning/
```

No experiment output may be written outside this root except temporary smoke files under an explicitly configured temporary path.

### 12.4 Required enums

```text
ThresholdPolicy =
  GLOBAL_THRESHOLD
  LOCAL_THRESHOLD
  CLUSTER_THRESHOLD
```

```text
AttackerObjective =
  THRESHOLD_RAISE
  THRESHOLD_LOWER
```

```text
PoisoningSourceStrategy =
  RANDOM_BENIGN
  HIGH_SCORE_BENIGN
  LOW_SCORE_BENIGN
  LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY
```

```text
CalibrationInjectionRule =
  REPLACE_FIXED_BUDGET
```

```text
PoisoningKnowledge =
  GRAY_BOX_SCORE_ACCESS
  WHITE_BOX_DIAGNOSTIC_ONLY
```

```text
PoisoningTargetScope =
  SINGLE_CLIENT
  MULTI_CLIENT
  ALL_CLIENTS_DIAGNOSTIC_ONLY
```

```text
PoisoningDefense =
  NONE
  TRIMMED_CALIBRATION
```

```text
ExperimentStage =
  FINAL_AUDIT
  SYNTHETIC_SMOKE
  NBAIOT_MAIN
  NBAIOT_FULL_OPTIONAL
  STRETCH_DIAGNOSTIC_ONLY
```

### 12.5 Type discipline

Configuration should use explicit enums and typed dataclasses.

Do not accept raw strings where enums are required.

Do not implement backward-compatible aliases for stale policy names.

Do not use ambiguous union types such as enum-or-string for protocol-critical fields.

Invalid config should fail early.

Invalid source-objective combinations should fail config validation.

### 12.6 Determinism

Required:

```text
PYTHONHASHSEED = 0
```

Seed all relevant libraries and processes:

* Python;
* NumPy;
* PyTorch CPU;
* PyTorch GPU if used;
* data loaders;
* split generation;
* poisoning position selection;
* reservoir sampling;
* bootstrap analysis.

Child seeds must be deterministic functions of:

```text
training_seed
poisoning_seed
client_id
scope_id
source_strategy
objective
fraction
```

Every derived seed is recorded in the manifest.

### 12.7 No in-place mutation

Clean arrays are immutable inputs.

The injector must return new contaminated arrays and must not mutate clean artifacts in place.

Smoke and unit tests must assert this.

### 12.8 Manifests

Required manifests:

```text
project_audit_report.json
clean_score_artifacts.json
synthetic_smoke_manifest.json
nbaiot_main_manifest.json
cluster_threshold_manifest.json
reservoir_manifest.json
infeasible_cells.json
multi_client_plan.json
paper_figure_manifest.json
```

Each poisoned result must record:

* code commit;
* config hash;
* dataset;
* client IDs;
* eligible clients;
* victim plan;
* valid source-objective pair;
* fraction;
* injection rule;
* reservoir source;
* reservoir split;
* reservoir size;
* replacement count;
* threshold percentile `q`;
* `ε_num`;
* `ddof`;
* seeds;
* threshold policy;
* clean artifact IDs;
* output artifact paths.

### 12.9 Output path template

```text
<scale>/<dataset>/<policy>/<objective>/<source>/f_<fraction>/scope_<scope>/train_<training_seed>/poison_<poisoning_seed>/
```

### 12.10 Required modules

Implementation must support:

* config parsing and validation;
* source-objective pair validation;
* clean artifact audit;
* victim eligibility computation;
* victim-local reservoir construction;
* poisoning injection;
* threshold recomputation at `q = 95`;
* `GLOBAL_THRESHOLD`;
* `LOCAL_THRESHOLD`;
* `CLUSTER_THRESHOLD`;
* cluster decomposition;
* frozen-clean-scaler diagnostic;
* paired metric computation;
* CV zero and near-zero handling;
* AUROC sanity check;
* synthetic smoke tests;
* manifest writing;
* result audit;
* figure and table generation.

---

## 13. Synthetic Smoke Invariants

The synthetic smoke stage must pass before N-BaIoT main execution.

Required invariants:

1. Fraction `0` produces zero `Δτ`.
2. `RANDOM_BENIGN` is near-null under the locked seed-level aggregate criterion.
3. `HIGH_SCORE_BENIGN` is rejected if paired with `THRESHOLD_LOWER`.
4. `LOW_SCORE_BENIGN` is rejected if paired with `THRESHOLD_RAISE`.
5. `HIGH_SCORE_BENIGN + THRESHOLD_RAISE` produces positive `Δτ`.
6. `LOW_SCORE_BENIGN + THRESHOLD_LOWER` produces negative `Δτ` in a synthetic distribution where lowering is feasible.
7. `THRESHOLD_RAISE` connects to negative victim detection movement when synthetic test scores are constructed to expose it.
8. `THRESHOLD_LOWER` connects to positive FPR-dispersion movement when synthetic test scores are constructed to expose it.
9. `GLOBAL_THRESHOLD` produces shared threshold spillover.
10. `LOCAL_THRESHOLD` confines threshold movement to the attacked victim.
11. All threshold policies use `q = 95`.
12. `CLUSTER_THRESHOLD` computes finite client-effective deltas.
13. Raw cluster labels are not compared directly.
14. `CLUSTER_THRESHOLD` uses fixed `K=3` for N-BaIoT main.
15. Full-refit, aggregation, churn, frozen-scaler, and normalization-gap components are computable.
16. AUROC is invariant when test scores and labels are unchanged.
17. Clean calibration arrays are not mutated in place.
18. The same seeds reproduce identical outputs.
19. Different poisoning seeds can change replacement positions while preserving paired clean artifacts.
20. Test scores are rejected as reservoirs.
21. Training scores are rejected as reservoirs.
22. Attack-labeled samples are rejected from calibration.
23. CV uses `std(..., ddof=0)`.
24. CV is undefined when mean FPR is zero.
25. CV is flagged when mean FPR is below `mu_flag_threshold`.
26. Absolute dispersion metrics are still reported when CV is undefined or unstable.
27. `ε_num = 1e-12` is applied consistently.
28. All outputs stay under the configured output root.
29. Manifests contain all required provenance fields.

Failure of any invariant blocks main execution.

---

## 14. Main N-BaIoT Execution Plan

### 14.1 Main matrix

```text
Dataset = N_BAIOT
Policies = GLOBAL_THRESHOLD, LOCAL_THRESHOLD, CLUSTER_THRESHOLD
Scope = SINGLE_CLIENT
Victims = all eligible clients
ValidSourceObjectivePairs =
  RANDOM_BENIGN + THRESHOLD_RAISE
  RANDOM_BENIGN + THRESHOLD_LOWER
  HIGH_SCORE_BENIGN + THRESHOLD_RAISE
  LOW_SCORE_BENIGN + THRESHOLD_LOWER
Fractions = 0, 0.10, 0.20, 0.40
TrainingSeeds = 0, 1, 2, 3, 4
PoisoningSeeds = 100, 101, 102, 103, 104
ThresholdPercentile = 95
CVStdConvention = ddof=0
Epsilon = 1e-12
```

### 14.2 Execution order

1. Run clean artifact audit.
2. Lock `q = 95`.
3. Lock `ε_num = 1e-12`.
4. Lock materiality thresholds.
5. Lock `mu_flag_threshold`.
6. Validate source-objective pairs.
7. Run synthetic smoke.
8. Execute fraction `0` cells.
9. Execute `RANDOM_BENIGN` objective-matched control cells.
10. Execute `HIGH_SCORE_BENIGN + THRESHOLD_RAISE` cells.
11. Execute `LOW_SCORE_BENIGN + THRESHOLD_LOWER` cells.
12. Run paired result audit.
13. Run cluster decomposition audit.
14. Generate main tables and figures.
15. Decide whether optional full extension is justified.

### 14.3 Main success interpretation

A positive main result is supported only when:

* `LOCAL_THRESHOLD` shows material correctly signed `Δτ` for a strict majority of victims;
* downstream movement is interpretable, correctly signed, and visible at paired seed-aggregate level;
* policy differences are visible in victim sensitivity, spillover, or blast radius;
* `RANDOM_BENIGN` remains near-null or any deviation is resolved by audit;
* AUROC remains invariant;
* no leakage or cluster-count violation is detected.

### 14.4 Main negative interpretation

A negative result is valid if the matrix executes and the claim gate fails.

Do not search for unregistered variants to rescue the main claim.

A null result may support:

* bounded vulnerability under the tested gray-box score-level setting;
* calibration-channel robustness under the tested fractions;
* evidence that the attack instantiation is insufficient.

It does not support claims of universal robustness.

---

## 15. Optional Full and Stretch Stages

### 15.1 Optional full extension

The optional full extension may include:

```text
PoisoningTargetScope = MULTI_CLIENT
```

with:

* all feasible eligible pairs unless a smaller locked pair budget is declared before execution;
* deterministic eligible triples sampled from lexicographic triples using `compromise_pattern_seed = 400`;
* the same paired seed logic;
* the same reservoir rules;
* the same valid source-objective pairs;
* the same threshold policies;
* the same claim gates.

Claims about one-to-three-client compromise require this stage.

### 15.2 Pair and triple selection

Eligible clients are sorted by canonical client ID.

Pairs:

```text
all lexicographic eligible pairs
```

If compute requires a pair subset, lock:

```text
N_pair_lock
```

before execution and take the first `N_pair_lock` feasible lexicographic pairs.

Triples:

```text
all feasible eligible triples are enumerated in lexicographic order
N_triple_lock = min(12, number_of_feasible_eligible_triples)
sample using compromise_pattern_seed = 400
```

The exact selected pairs and triples are written before execution to:

```text
multi_client_plan.json
```

No pair or triple may be selected, removed, or reordered after inspecting poisoned outcomes.

### 15.3 Optional additional fraction

The optional full extension may add:

```text
poison_fraction = 0.05
```

only if locked before execution.

### 15.4 Stretch contrast

A stretch dataset may be used only as diagnostic contrast.

CICIoT2023 is allowed only if:

* client semantics are explicitly documented;
* pseudo-client status is disclosed;
* calibration/test semantics are safe;
* no natural-device equivalence is claimed.

### 15.5 Stretch cluster policy

For any stretch dataset, the cluster count must be selected from the clean condition and frozen before poisoned runs.

Poisoning may alter assignments but cannot alter the policy definition.

If stable cluster semantics cannot be maintained, `CLUSTER_THRESHOLD` is removed from the stretch stage.

---

## 16. Optional Defense

### 16.1 Defense enum

```text
PoisoningDefense =
  NONE
  TRIMMED_CALIBRATION
```

### 16.2 Defense definition

`TRIMMED_CALIBRATION` symmetrically trims calibration reconstruction errors before threshold computation.

Primary trim:

```text
trim_fraction = 0.05
```

Appendix sensitivity:

```text
trim_fraction = 0.10
```

Trimming applies consistently to:

* local percentile thresholds;
* global threshold components;
* cluster fingerprints;
* cluster thresholds.

### 16.3 Recovery metric

For declared harm metric `H`:

```text
Recovery = (H_poisoned - H_defended) / max(|H_poisoned - H_clean|, ε_num)
```

Positive recovery indicates harm reduction.

### 16.4 Main-result admission gate

`TRIMMED_CALIBRATION` enters main results only if:

```text
Recovery >= 0.5
```

on the declared primary harm metric, and it causes no material clean-setting regression.

If the denominator falls back to `ε_num`, the case is logged because it indicates that original attack harm was absent or too small for meaningful recovery.

### 16.5 Failed defense handling

If `TRIMMED_CALIBRATION` fails the recovery or clean-regression gate, it appears only in appendix or diagnostics.

Do not frame a failed defense as effective.

### 16.6 Defense appendix table

The defense appendix table is pre-numbered as:

```text
Table A1 — TRIMMED_CALIBRATION recovery and clean-regression diagnostics
```

This table reports:

* clean metric;
* poisoned harm metric;
* defended harm metric;
* recovery;
* clean-setting regression;
* pass or fail against main-result admission gates.

---

## 17. Analysis, Figures, and Tables

### 17.1 Main tables

**Table 1 — Protocol identity and threat model**

* calibration-only attack;
* allowed and forbidden adversary actions;
* score-level proxy limitation.

**Table 2 — Experiment matrix**

* dataset;
* policies;
* valid source-objective pairs;
* fractions;
* seeds;
* target scopes.

**Table 3 — N-BaIoT client and eligibility summary**

* client ID;
* calibration size;
* reservoir feasibility;
* clean threshold statistics;
* materiality threshold.

**Table 4 — Main threshold-shift results**

* `Δτ`;
* `|Δτ|`;
* `Δτ_rel`;
* materiality rate;
* sign consistency;
* victim-majority support.

**Table 5 — Downstream movement**

* raising: victim `ΔTPR`, `ΔBA`, `ΔMacroF1`;
* lowering: `ΔCV(FPR)`, `ΔIQR(FPR)`, `Δmax-min FPR`, `ΔWorstClientFPR`.

**Table 6 — Policy-differentiated vulnerability profile**

* victim sensitivity;
* blast radius;
* spillover;
* cluster churn;
* normalization-mediated effect.

**Table 7 — Claims-to-evidence map**

* claim;
* required gate;
* observed result;
* allowed wording.

### 17.2 Main figures

**Figure 1 — datp-cp attack surface**

Shows training, aggregation, calibration, and testing, with poisoning restricted to benign calibration.

**Figure 2 — Score-level poisoning mechanism**

Shows fixed-size replacement and victim-local reservoirs.

**Figure 3 — Threshold shift versus fraction**

Separate panels for policy and valid source-objective pair.

**Figure 4 — Detection degradation under threshold raising**

Victim `ΔTPR`, `ΔBA`, or `ΔMacroF1`.

**Figure 5 — Alarm-burden degradation under threshold lowering**

`IQR(FPR)`, `max-min FPR`, `WorstClientFPR`, and CV where defined.

**Figure 6 — Policy vulnerability profile**

Compares `GLOBAL_THRESHOLD`, `LOCAL_THRESHOLD`, and `CLUSTER_THRESHOLD`.

**Figure 7 — Cluster-threshold decomposition**

Reports mandatory aggregation and churn components, plus diagnostic frozen-scaler and normalization-mediated components.

### 17.3 Appendix and diagnostic tables

**Table A1 — TRIMMED_CALIBRATION recovery and clean-regression diagnostics**

Reports optional defense results only if the defense stage is executed.

### 17.4 Diagnostics

Appendix or diagnostic outputs:

* `RANDOM_BENIGN` near-null audit;
* AUROC invariance;
* infeasible-cell report;
* reservoir provenance;
* CV undefined and instability flags;
* cluster reassignment heatmap;
* duplicate score disclosure at high fractions;
* optional defense recovery and clean regression;
* optional multi-client extension;
* optional stretch contrast.

---

## 18. Claims and Safe Wording

### 18.1 Positive result wording

If the primary claim gate is met:

> datp-cp shows that poisoning only benign threshold-calibration data can materially shift threshold policies in federated IoT anomaly detection while training, aggregation, model parameters, and test data remain clean. Under the tested N-BaIoT setting, threshold-raising attacks degrade victim detection, threshold-lowering attacks degrade alarm-burden predictability, and global, local, and cluster threshold policies exhibit distinct vulnerability profiles.

### 18.2 Mixed result wording

If only one objective or one policy meets the claim gate:

> Under the tested N-BaIoT setting, calibration-channel poisoning produced bounded and policy-dependent effects. The observed harm was consistent for the supported objective or policy subset, while the remaining cells did not meet the pre-registered claim gate.

### 18.3 Negative result wording

If the main claim gate fails:

> Under the tested gray-box score-level setting and poison fractions, calibration-only poisoning did not produce material, correctly signed threshold shifts with interpretable downstream movement. The result bounds this attack instantiation rather than proving general robustness of threshold calibration.

### 18.4 Defense wording

If `TRIMMED_CALIBRATION` passes gates:

> A lightweight trimmed-calibration variant reduced the declared primary harm metric by at least half without material clean-setting regression under the tested setting.

If it fails gates:

> Trimmed calibration did not satisfy the pre-registered recovery and clean-regression gates and is reported only as a diagnostic result.

### 18.5 Stretch wording

For CICIoT2023 or pseudo-client contrast:

> The stretch experiment is a pseudo-client contrast and does not establish natural-device behavior.

### 18.6 Forbidden claims

Do not claim:

* universal threshold vulnerability;
* universal threshold robustness;
* raw-traffic attack realizability;
* broad FL robustness;
* secure aggregation robustness;
* privacy preservation beyond structural data locality;
* deployment readiness;
* real-time feasibility;
* model-poisoning robustness;
* training-poisoning robustness;
* evasion robustness;
* superiority over model-personalization methods;
* conclusions from diagnostic variants as main evidence.

---

## 19. Kill and Pivot Criteria

### 19.1 Kill criteria

Kill the main datp-cp vulnerability claim if any of the following holds after valid N-BaIoT main execution:

1. no material `Δτ` occurs for `LOCAL_THRESHOLD` under the strongest directional attack at the largest fraction;
2. material `Δτ` occurs but no interpretable downstream movement appears at paired seed-aggregate level;
3. `GLOBAL_THRESHOLD`, `LOCAL_THRESHOLD`, and `CLUSTER_THRESHOLD` are indistinguishable after victim sensitivity, blast radius, spillover, and cluster decomposition;
4. effects appear only under diagnostic upper-bound variants, not under the main gray-box model;
5. `RANDOM_BENIGN` deviation remains unresolved and undermines attack specificity;
6. AUROC moves materially;
7. reservoir leakage is detected;
8. test scores or training scores enter reservoirs;
9. attack labels enter calibration;
10. cluster count changes in N-BaIoT main;
11. clean artifact provenance cannot be established or regenerated;
12. journal-scope assets contaminate the main claim;
13. invalid source-objective pairs are executed as main cells.

### 19.2 Audit flags that are not automatic kills

The following trigger investigation but not automatic termination:

* `RANDOM_BENIGN` exceeding near-null;
* CV instability due to near-zero mean FPR;
* infeasible reservoir cells;
* high cluster churn;
* high duplicate score count at large fractions;
* borderline seed consistency;
* main lowering attack failing while diagnostic targeted removal succeeds.

### 19.3 Pivot hierarchy

If the main claim fails, allowed pivots are:

1. bounded-vulnerability paper;
2. calibration-channel robustness under score-level attack;
3. threshold policy stability analysis;
4. alarm-burden predictability under clean calibration;
5. client-definition sensitivity;
6. operational threshold-monitoring diagnostic.

Forbidden pivots:

* training poisoning;
* model poisoning;
* robust aggregation paper;
* privacy paper;
* deployment paper;
* journal-extension expansion.

### 19.4 Cut order under time pressure

Cut in this order:

```text
stretch contrast
optional defense
multi-client full extension
extra diagnostic variants
additional fractions
```

Never cut:

```text
final audit
synthetic smoke
N-BaIoT main
paired clean-vs-poisoned design
GLOBAL_THRESHOLD / LOCAL_THRESHOLD / CLUSTER_THRESHOLD comparison
valid source-objective pair validation
q = 95 threshold lock
reservoir leakage checks
AUROC sanity check
```

---

## 20. Contingencies

### 20.1 Clean artifact contingency

Trigger:

* clean artifacts are missing, malformed, stale, non-`E=1`, or not datp-cp generated.

Action:

* regenerate clean artifacts inside the datp-cp repository;
* preserve the inherited DATP clean reproduction protocol;
* preserve `E=1`;
* preserve FedAvg;
* preserve sample-count-weighted aggregation;
* preserve chronological split semantics;
* preserve checkpoint-selection rule;
* record full provenance;
* do not tune against poisoned outcomes.

Safe wording:

> Clean baselines were regenerated under the locked DATP clean reproduction protocol before any poisoned condition was executed.

### 20.2 Reservoir contingency

Trigger:

* victim-local benign reservoir is infeasible for a source strategy.

Action:

* mark the affected cell infeasible;
* exclude consistently across paired seeds;
* report infeasibility;
* do not substitute test, training, attack-labeled, or cross-client reservoirs for main claims.

### 20.3 Cluster-threshold contingency

Trigger:

* `CLUSTER_THRESHOLD` cannot be reproduced under the locked procedure;
* client-effective thresholds cannot be validated;
* cluster count changes;
* mandatory decomposition fails.

Action:

* block `CLUSTER_THRESHOLD` main claims;
* report only `GLOBAL_THRESHOLD` and `LOCAL_THRESHOLD` as primary;
* move cluster outputs to diagnostics only if safe.

Safe wording:

> Cluster-threshold results are diagnostic because the locked cluster-threshold reproducibility gate was not satisfied.

### 20.4 CV contingency

Trigger:

* mean eligible-client FPR is zero or below `mu_flag_threshold`.

Action:

* if zero, exclude CV from claims for that cell;
* if near-zero, report CV with instability flag;
* rely on `IQR(FPR)`, `max-min FPR`, and `WorstClientFPR`.

### 20.5 Lowering null contingency

Trigger:

* `LOW_SCORE_BENIGN + THRESHOLD_LOWER` produces no material lowering effect.

Action:

* do not claim lowering vulnerability;
* optionally run `LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY`;
* frame diagnostic results as attack-instantiation analysis only.

### 20.6 Optional defense contingency

Trigger:

* defense recovery below `0.5`;
* material clean-setting regression;
* denominator fallback dominates recovery.

Action:

* move defense to Table A1, appendix, or omit from main narrative;
* do not call it effective.

### 20.7 Stretch contingency

Trigger:

* CICIoT2023 pseudo-client semantics are unsafe;
* calibration/test semantics are unsafe;
* cluster count cannot be frozen safely.

Action:

* do not execute stretch;
* or execute only safe policies as diagnostic contrast.

---

## 21. Reviewer-Risk Controls

### 21.1 “This is just data poisoning.”

Control:

* The protocol attacks threshold calibration only.
* Training data, updates, aggregation, model parameters, test scores, and test labels remain clean.

Safe wording:

> This is calibration-channel poisoning, not training-data poisoning.

### 21.2 “The score-level attack is unrealistic.”

Control:

* Score-level attack is explicitly bounded as a proxy.
* It isolates the calibration stage.
* Raw-traffic realizability is future work.

Safe wording:

> Score-level poisoning isolates the threshold-calibration mechanism; it does not prove raw-traffic realizability.

### 21.3 “AUROC does not change, so nothing happened.”

Control:

* AUROC should not change because test scores and labels are unchanged.
* The object of study is operating-point movement.

Safe wording:

> AUROC invariance verifies threshold-stage isolation; the failure mode is threshold-induced operating-point movement.

### 21.4 “Local threshold sensitivity is obvious.”

Control:

* The paper compares policy vulnerability profiles, not only local sensitivity.
* It measures victim harm, blast radius, spillover, cluster churn, and normalization-mediated effects.

Safe wording:

> The contribution is the policy-differentiated vulnerability profile under isolated calibration-channel poisoning.

### 21.5 “K=9 is too small for FL.”

Control:

* N-BaIoT provides natural physical-device clients.
* The claim is dataset-bounded.
* The study sweeps all eligible victims and uses paired seeds.

Safe wording:

> N-BaIoT is used because it provides physical-device client identity; the claims are bounded to this nine-device setting.

### 21.6 “Why no training-data poisoning comparison?”

Control:

* Training poisoning is intentionally out of scope.
* The protocol isolates a distinct post-training calibration channel.

Safe wording:

> Training-data poisoning is a different attack surface; datp-cp holds training fixed to isolate threshold calibration.

### 21.7 “The RANDOM control moved.”

Control:

* `RANDOM_BENIGN` has a pre-registered seed-level aggregate audit rule.
* Deviation triggers investigation and may narrow claims.

Safe wording:

> RANDOM deviation is treated as an instability audit flag, not as evidence of targeted poisoning.

### 21.8 “CV explodes when FPR is tiny.”

Control:

* CV is undefined at zero mean FPR.
* Near-zero means are flagged.
* Absolute dispersion metrics are always reported.

Safe wording:

> CV-based conclusions are disabled or flagged when mean FPR is zero or near zero, and absolute FPR dispersion metrics carry the interpretation.

### 21.9 “Cluster labels permute.”

Control:

* Raw labels are never compared.
* All cluster deltas are client-effective threshold deltas.

Safe wording:

> Cluster-threshold analysis compares each client’s effective threshold, not raw cluster IDs.

### 21.10 “Scaler refit creates artificial spillover.”

Control:

* Full-refit is the deployed-policy effect.
* Frozen-clean-scaler is reported as diagnostic.
* Normalization-mediated gap is quantified.

Safe wording:

> The full-refit result measures the deployed cluster-threshold policy; the frozen-scaler diagnostic separates normalization-mediated movement.

### 21.11 “Only one dataset.”

Control:

* N-BaIoT is primary because of physical-device clients.
* Stretch results are diagnostic only.
* Claims remain dataset-bounded.

Safe wording:

> The study demonstrates the mechanism on physical-device clients and does not claim dataset-universal behavior.

### 21.12 “No privacy mechanism.”

Control:

* Privacy is not claimed.
* FL data locality is not framed as a formal privacy guarantee.

Safe wording:

> datp-cp does not make privacy guarantees; privacy mechanisms are outside scope.

### 21.13 “No deployment evidence.”

Control:

* Deployment is out of scope.
* The study is a controlled empirical vulnerability analysis.

Safe wording:

> datp-cp evaluates a threshold-stage vulnerability mechanism, not deployment readiness.

### 21.14 “Defense failed.”

Control:

* Defense has pre-specified entry gates.
* Failed defense is diagnostic only.

Safe wording:

> The defense is reported in the main text only if it satisfies recovery and clean-regression gates.

### 21.15 “The lowering attack is weak.”

Control:

* The protocol pre-registers lowering as conditional.
* `LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY` is available to distinguish a robust channel from a weak random-replacement lowering instantiation.

Safe wording:

> Lowering results are interpreted conditionally because random fixed-budget insertion may not displace upper-tail support in a percentile threshold.

---

## 22. Final Protocol-Lock Checklist

### 22.1 Identity lock

* `datp-cp` shorthand used consistently.
* Calibration-channel poisoning only.
* No stale operational threshold labels.
* No journal-extension assets.
* No broad FL robustness, privacy, deployment, training-poisoning, model-poisoning, aggregation-poisoning, backdoor, or evasion claims.

### 22.2 Artifact lock

* Clean artifacts confirmed or regenerated inside datp-cp.
* `E=1` confirmed.
* FedAvg confirmed.
* Aggregation weighting confirmed.
* Architecture, optimizer, loss, convergence criterion, and checkpoint-selection rule confirmed from inherited DATP clean reproduction protocol.
* Splits confirmed.
* Calibration scores confirmed benign-only.
* Test scores and labels confirmed unchanged.
* Reservoir sources confirmed victim-local and benign.
* No test-score reservoirs.
* No training-score reservoirs.
* No attack labels in calibration.

### 22.3 Policy lock

* `q = 95` locked.
* `GLOBAL_THRESHOLD` implemented and validated.
* `LOCAL_THRESHOLD` implemented and validated.
* `CLUSTER_THRESHOLD` implemented and validated.
* N-BaIoT `CLUSTER_THRESHOLD` uses fixed `K=3`.
* Raw cluster labels are not compared.
* Client-effective threshold deltas are used.
* Full-refit cluster effect is main.
* Mandatory cluster decomposition outputs implemented.
* Frozen-clean-scaler diagnostic implemented.
* Cluster decomposition outputs are assigned figure or table slots.

### 22.4 Attack lock

* `REPLACE_FIXED_BUDGET` implemented.
* Fractions locked.
* Victim sweep locked.
* Valid source-objective pairs locked.
* Invalid source-objective pairs rejected.
* Tail mass locked.
* With-replacement behavior recorded.
* Infeasible-cell behavior implemented.
* `RANDOM_BENIGN` seed-level aggregate near-null criterion implemented.
* Diagnostic-only variants cannot enter main claims.

### 22.5 Metric lock

* `δτ_i` materiality rule locked.
* `δτ_floor` locked from clean artifacts.
* `ε_num = 1e-12` locked.
* `CV(FPR)` uses `std(..., ddof=0)`.
* Downstream movement rules locked.
* `CV(FPR)` zero behavior implemented.
* `mu_flag_threshold` locked from the smallest positive eligible-client mean FPR across clean policies divided by 8.
* Absolute dispersion metrics implemented.
* AUROC sanity check implemented.

### 22.6 Statistical lock

* Paired seed design implemented.
* Two-layer unit of analysis implemented.
* Seed-level aggregates implemented.
* `4/5` sign consistency implemented.
* Strict-majority victim rule implemented.
* Bootstrap CI method locked.
* Exact paired sign test implemented as supporting evidence only.

### 22.7 Optional full-extension lock

* Pair enumeration rule locked.
* Triple enumeration rule locked.
* `N_pair_lock` locked if pair subset is used.
* `N_triple_lock` locked before execution.
* `compromise_pattern_seed = 400` locked.
* `multi_client_plan.json` written before execution.
* No multi-client plan changes after poisoned outcomes are inspected.

### 22.8 Defense lock

* `TRIMMED_CALIBRATION` remains optional.
* Main admission gate is `Recovery >= 0.5`.
* Clean-setting regression gate locked.
* Table A1 reserved for defense diagnostics.
* Failed defense cannot enter main results.

### 22.9 Smoke lock

* All synthetic smoke invariants pass.
* No in-place mutation.
* Determinism confirmed.
* Output-root isolation confirmed.
* Manifests complete.

### 22.10 Main execution lock

N-BaIoT main execution may begin only after:

```text
FINAL_AUDIT = PASS
CLEAN_ARTIFACT_PROVENANCE = PASS
SYNTHETIC_SMOKE = PASS
CLUSTER_THRESHOLD_REPRODUCIBILITY = PASS
RESERVOIR_LEAKAGE_CHECK = PASS
VALID_SOURCE_OBJECTIVE_PAIR_CHECK = PASS
```

### 22.11 Claim lock

Before writing results:

* classify each result as positive, mixed, negative, diagnostic, or failed gate;
* map every claim to a pre-registered gate;
* remove unsupported claims;
* preserve dataset-bounded wording;
* disclose score-level proxy limitation;
* disclose CV undefined or instability cases;
* disclose infeasible cells;
* disclose optional-stage status.

### 22.12 Final lock sentence

The protocol is locked only when the audit confirms that datp-cp remains a strictly scoped calibration-channel poisoning study with paired clean-vs-poisoned threshold-stage isolation, N-BaIoT as the primary physical-device dataset, `q = 95` threshold semantics, valid source-objective pairs only, and claims limited to the evidence produced by the locked main and optional matrices.
