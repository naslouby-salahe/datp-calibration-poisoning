# Roadmap Contract — datp-cp

Extracted from `docs/DATP_CP_Roadmap.md`. This is the binding spec for the rework.

---

## Project Identity

- **Project shorthand:** `datp-cp`
- **Full title:** Calibration-Channel Poisoning of Federated Threshold Personalization in IoT Anomaly Detection: A Policy-Differentiated Vulnerability Analysis
- **Core hypothesis:** datp-cp tests whether poisoning only benign threshold-calibration data can shift threshold policies enough to induce detection/alarm-burden degradation while training, aggregation, model parameters, test scores, and test labels remain clean.
- **Output root:** `outputs/conference_calibration_poisoning/`
- **Raw data symlink:** `data/raw -> /home/naslouby/Projects/datp-shared-data/raw`

---

## Scope

### Included
- N-BaIoT main study
- `GLOBAL_THRESHOLD`, `LOCAL_THRESHOLD`, `CLUSTER_THRESHOLD`
- Benign calibration-score poisoning only (calibration-channel only)
- Score-level proxy attack
- Fixed-size replacement
- Victim-local reservoirs
- All eligible single-client victims (main study)
- Paired clean-vs-poisoned comparisons
- Five paired training and poisoning seeds
- Optional full extension: eligible pairs + deterministic triples
- Optional `TRIMMED_CALIBRATION` defense

### Excluded (hard boundary)
- Journal-extension datasets as main evidence
- Edge-IIoTset (FORBIDDEN)
- Training-data poisoning
- Model poisoning / aggregation poisoning
- Backdoor / evasion attacks
- Privacy mechanisms / guarantees
- Deployment / latency / memory / communication claims
- Raw-traffic injection claims
- Broad "secure FL" or "robust FL" language
- FedProx, Ditto, FedRep, FedPer, FedBN comparators
- Conformal thresholding / temporal recalibration
- B3/family threshold (not in CP2 default policy enum)

---

## Canonical Names

### Threshold policies (ONLY these three)
```
ThresholdPolicy:
  GLOBAL_THRESHOLD
  LOCAL_THRESHOLD
  CLUSTER_THRESHOLD
```

### Experiment stages (ONLY these)
```
ExperimentStage:
  FINAL_AUDIT
  SYNTHETIC_SMOKE
  NBAIOT_MAIN
  NBAIOT_FULL_OPTIONAL
  STRETCH_DIAGNOSTIC_ONLY
```

### Attacker objectives
```
AttackerObjective:
  THRESHOLD_RAISE
  THRESHOLD_LOWER
```

### Source strategies
```
PoisoningSourceStrategy:
  RANDOM_BENIGN
  HIGH_SCORE_BENIGN
  LOW_SCORE_BENIGN
  LOW_SCORE_TARGETED_REMOVAL_DIAGNOSTIC_ONLY
```

### Injection rule
```
CalibrationInjectionRule:
  REPLACE_FIXED_BUDGET
```

### Knowledge model
```
PoisoningKnowledge:
  GRAY_BOX_SCORE_ACCESS
  WHITE_BOX_DIAGNOSTIC_ONLY
```

### Target scopes
```
PoisoningTargetScope:
  SINGLE_CLIENT
  MULTI_CLIENT
  ALL_CLIENTS_DIAGNOSTIC_ONLY
```

### Defense
```
PoisoningDefense:
  NONE
  TRIMMED_CALIBRATION
```

---

## Dataset and Clients

- Primary: N-BaIoT, physical device = client, K=9
- Optional stretch: CICIoT2023 (pseudo-client contrast only, diagnostic)
- Forbidden: Edge-IIoTset

---

## Threshold Policy Definitions

### GLOBAL_THRESHOLD
```
τ_i_local = percentile_95(S_i_cal)
τ_global = mean_i(τ_i_local) over eligible clients
```
All eligible clients share the same threshold.

### LOCAL_THRESHOLD
```
τ_i_local = percentile_95(S_i_cal)
```
Each eligible client has its own threshold.

### CLUSTER_THRESHOLD
- Fingerprint: `v_i = [mean(S_i_cal), std(S_i_cal), skew(S_i_cal), p95(S_i_cal)]`
- Clustering: StandardScaler + k-means++, K=3 (locked for N-BaIoT), n_init=10, max_iter=300, random_state=42
- `τ_cluster_c = mean(τ_i_local)` for eligible clients in cluster c
- `τ_i_eff = τ_cluster_assignment(i)`
- All deltas are client-effective threshold deltas
- Raw cluster label IDs are NEVER compared

**Mandatory decomposition:**
- Δτ_i_total = τ_i_eff,poisoned_full_refit - τ_i_eff,clean
- Δτ_i_aggregation = τ_i_eff,poisoned_clean_assignment - τ_i_eff,clean
- Δτ_i_churn = Δτ_i_total - Δτ_i_aggregation
- Δτ_i_frozen_scaler (diagnostic)
- Δτ_i_normalization_gap (diagnostic)

---

## Attack Design

### Injection rule: REPLACE_FIXED_BUDGET
- m_i = 0 if f = 0
- m_i = max(1, round(f * n_i)) if f > 0
- Replace m_i positions with-replacement from victim-local reservoir
- Calibration size stays constant
- Clean arrays NEVER mutated in place

### Main fractions
{0, 0.10, 0.20, 0.40}

Optional extension: 0.05 (locked before execution)

### Valid source-objective pairs (ONLY these four)
| Source | Objective |
|--------|-----------|
| RANDOM_BENIGN | THRESHOLD_RAISE (negative control) |
| RANDOM_BENIGN | THRESHOLD_LOWER (negative control) |
| HIGH_SCORE_BENIGN | THRESHOLD_RAISE |
| LOW_SCORE_BENIGN | THRESHOLD_LOWER |

**INVALID (must fail config validation):**
- HIGH_SCORE_BENIGN + THRESHOLD_LOWER
- LOW_SCORE_BENIGN + THRESHOLD_RAISE

### Tail mass
`tail_mass = 0.10` (upper/lower 10%)

### Seed scheme
```
training_seed       = [0, 1, 2, 3, 4]
poisoning_seed      = [100, 101, 102, 103, 104]
analysis_seed       = [300, 301, 302, 303, 304]
split_seed          = [200, 201, 202, 203, 204] (if new splits)
compromise_pattern_seed = 400
```
Use numpy.random.SeedSequence(). NO integer addition.

---

## Eligibility

- n_cal >= 100 to be eligible
- Ineligible clients: excluded from CV(FPR), victim sets, CLUSTER_THRESHOLD clustering

---

## Metrics

### Materiality
- δτ_i_raw = 0.1 * IQR(S_i_cal_clean)
- δτ_floor = 0.01 * median_j(IQR(S_j_cal_clean))
- δτ_i = max(δτ_i_raw, δτ_floor)

### Numerical epsilon
- ε_num = 1e-12 (in config and manifests)

### CV(FPR)
- std(FPR_i, ddof=0) / mean(FPR_i) over eligible clients
- Undefined when mean=0
- Flagged when mean < mu_flag_threshold

### mu_flag_threshold
- smallest_positive_mean_FPR_across_clean_policies / 8
- Locked BEFORE any poisoned run

### Detection metrics
TPR, FPR, TNR, BA, MacroF1, P10_MacroF1, WorstClientBA, WorstClientFPR

### Dispersion metrics
CV(FPR), IQR(FPR), max-min FPR, WorstClientFPR

### AUROC
Must be invariant (test scores unchanged). Any movement = protocol error.

---

## Statistical Plan

- Two-layer: victim-level deltas + seed-level aggregates
- 5 seed-level aggregates drive primary CIs
- 4/5 seed sign consistency required
- Strict majority: 5/9 eligible N-BaIoT victims
- 95% bootstrap CI over seed aggregates (percentile default)
- Sign test: supporting only, does not gate
- Holm p-values: descriptive only

---

## Required Manifests

```
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

---

## Output Path Template
```
<scale>/<dataset>/<policy>/<objective>/<source>/f_<fraction>/scope_<scope>/train_<training_seed>/poison_<poisoning_seed>/
```

---

## Makefile Targets (canonical public workflow)
```
help             — show help
check            — tests + typecheck + lint
datp-cp-clean    — generate clean N-BaIoT E=1 artifacts
datp-cp-smoke    — run synthetic smoke invariants
datp-cp-dry-run  — validate N-BaIoT main matrix without running
datp-cp-run      — run N-BaIoT main calibration-poisoning experiment
datp-cp-report   — audit results + build stats, figures, tables
clean            — remove generated artifacts
```

---

## Synthetic Smoke Required Invariants (all 29)

1. Fraction 0 → zero Δτ
2. RANDOM_BENIGN → near-null
3. HIGH_SCORE_BENIGN + THRESHOLD_LOWER → REJECTED
4. LOW_SCORE_BENIGN + THRESHOLD_RAISE → REJECTED
5. HIGH_SCORE_BENIGN + THRESHOLD_RAISE → positive Δτ
6. LOW_SCORE_BENIGN + THRESHOLD_LOWER → negative Δτ (feasible distribution)
7. THRESHOLD_RAISE → negative victim detection movement (synthetic)
8. THRESHOLD_LOWER → positive FPR-dispersion movement (synthetic)
9. GLOBAL_THRESHOLD → shared threshold spillover
10. LOCAL_THRESHOLD → confinement to attacked victim
11. All policies use q=95
12. CLUSTER_THRESHOLD → finite client-effective deltas
13. Raw cluster labels NOT compared
14. K=3 fixed for N-BaIoT main
15. Full-refit, aggregation, churn, frozen-scaler, normalization-gap computable
16. AUROC invariant when test scores/labels unchanged
17. Clean calibration arrays NOT mutated in place
18. Same seeds → identical outputs
19. Different poisoning seeds → different replacement positions, same clean artifacts
20. Test scores rejected as reservoirs
21. Training scores rejected as reservoirs
22. Attack-labeled samples rejected from calibration
23. CV uses std(..., ddof=0)
24. CV undefined when mean FPR = 0
25. CV flagged when mean FPR < mu_flag_threshold
26. Absolute dispersion metrics reported when CV undefined/unstable
27. ε_num = 1e-12 applied consistently
28. All outputs under configured output root
29. Manifests contain all required provenance fields

---

## FINAL_AUDIT Pre-Execution Gates (§22.10)

```
FINAL_AUDIT = PASS
CLEAN_ARTIFACT_PROVENANCE = PASS
SYNTHETIC_SMOKE = PASS
CLUSTER_THRESHOLD_REPRODUCIBILITY = PASS
RESERVOIR_LEAKAGE_CHECK = PASS
VALID_SOURCE_OBJECTIVE_PAIR_CHECK = PASS
```

All gates must pass before NBAIOT_MAIN execution.

---

## Kill Criteria (§19.1)

1–13 specific conditions that kill the main vulnerability claim.
Key: no in-place mutation, no test/training/attack-label reservoir pollution,
AUROC must stay invariant, no journal-scope contamination, no invalid source-obj pairs.

---

## Claim Boundaries

- No universal vulnerability claim
- No broad FL robustness claim
- No privacy guarantee
- No deployment readiness
- No raw-traffic realizability
- No training/model/aggregation/backdoor/evasion claims
- Claims bounded to N-BaIoT nine-device single-client main study
