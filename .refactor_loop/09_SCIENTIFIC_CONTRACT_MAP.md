# 09_SCIENTIFIC_CONTRACT_MAP.md — Scientific Contract Map

**Status:** PENDING — awaiting inventory completion (SCI-001)
**Owner:** OpenClaw subagent + Hermes / DeepSeek Pro (review)
**Last updated:** 2026-06-20T21:27:24Z (scaffold only)

> WARNING: Do not edit source files during this inventory.
> This is a read-only analysis document.

---

## Purpose

Document the scientific contracts that the refactor must preserve.
Every calibration-poisoning, threshold, reservoir, injection, and policy
boundary must be catalogued with file+line evidence.

Future implementation agents must read this file before modifying any
poisoning, calibration, or policy logic.

---

## Instructions for SCI-001 Agent

1. Read `CLAUDE.md` §3 (scientific locks) before doing anything.
2. Read `09_SCIENTIFIC_CONTRACT_MAP.md` (this file) to understand the expected structure.
3. Inspect all modules under `src/` related to: poisoning, calibration, injection, reservoir, threshold, policy dispatch, B4 clustering.
4. For each contract element below, fill in the file, function/method, and line range where it is implemented.
5. Mark any element that violates the contract as VIOLATION with a description.
6. Report every finding with file+line evidence — no speculation.
7. Do not modify any source file.

---

## CP2 Scientific Contract

### Attack Boundary

| Contract element | Locked value | Implementation location | Status |
|---|---|---|---|
| Calibration-only poisoning | Benign threshold-calibration inputs/scores only | PENDING | — |
| Training data untouched | No poisoning of training samples | PENDING | — |
| Model weights untouched | No modification of model parameters | PENDING | — |
| FedAvg aggregation untouched | No modification of aggregation logic | PENDING | — |
| Test scores untouched | Test scores are never part of a reservoir | PENDING | — |
| Test labels untouched | Test labels are never modified | PENDING | — |
| Clean artifacts read-only | Clean run outputs used read-only | PENDING | — |

### Dataset and Regime

| Contract element | Locked value | Implementation location | Status |
|---|---|---|---|
| Primary dataset | REGIME_A_NBAIOT | PENDING | — |
| E=1 validation | Artifacts must be conference-faithful E=1 | PENDING | — |
| CICIoT2023 gating | Requires FB4 feasibility gate | PENDING | — |
| Edge-IIoTset forbidden | Must not appear in any code path | PENDING | — |

### Policy Locks

| Contract element | Locked value | Implementation location | Status |
|---|---|---|---|
| Default policies | B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER only | PENDING | — |
| B3 excluded from default | B3 not in default policy enum | PENDING | — |
| No journal scope | No journal-extension assets or logic | PENDING | — |

### Attack Mechanics

| Contract element | Locked value | Implementation location | Status |
|---|---|---|---|
| Injection rule | REPLACE_FIXED_BUDGET | PENDING | — |
| Budget formula | `m_i = max(1, round(f · n_i))` | PENDING | — |
| Cardinality preserved | `n_i` stays constant after injection | PENDING | — |
| Replacement mode | With-replacement resampling | PENDING | — |
| Reservoir source | Victim-local benign calibration scores | PENDING | — |
| No in-place mutation | Clean arrays always copied before modification | PENDING | — |
| No test-score reservoir | Test scores never used as reservoir | PENDING | — |
| No train-score reservoir | Training scores never used as reservoir | PENDING | — |

### Objectives and Sources

| Contract element | Locked value | Implementation location | Status |
|---|---|---|---|
| MVP objectives | THRESHOLD_RAISE, THRESHOLD_LOWER | PENDING | — |
| MVP sources | RANDOM_BENIGN, HIGH_SCORE_BENIGN, LOW_SCORE_BENIGN | PENDING | — |
| MVP fractions | {0, 0.10, 0.20, 0.40} | PENDING | — |
| RANDOM_BENIGN as negative control | Must be present in all runs | PENDING | — |
| HIGH/LOW signed behavior | HIGH raises threshold; LOW lowers threshold | PENDING | — |

### Seed Locks

| Contract element | Locked value | Implementation location | Status |
|---|---|---|---|
| training_seed values | [0, 1, 2, 3, 4] | PENDING | — |
| poisoning_seed values | [100, 101, 102, 103, 104] | PENDING | — |
| analysis_seed values | [300, 301, 302, 303, 304] | PENDING | — |
| compromise_pattern_seed | 400 | PENDING | — |
| Seed scheme | `SeedSequence([training_seed, poisoning_seed, client_id, scope_id])` | PENDING | — |
| No integer seed addition | Integer addition forbidden | PENDING | — |

### B4 Locks

| Contract element | Locked value | Implementation location | Status |
|---|---|---|---|
| K for Regime A | K=3 | PENDING | — |
| k-means init | k-means++ | PENDING | — |
| n_init | 10 | PENDING | — |
| max_iter | 300 | PENDING | — |
| random_state | 42 | PENDING | — |
| Fingerprint | `[mean(E_i), std(E_i), skew(E_i), p95(E_i)]` | PENDING | — |
| Delta decomposition | `Δτ_total = Δτ_agg + Δτ_churn` | PENDING | — |
| No raw label comparison | k-means label IDs not compared across runs | PENDING | — |

### Metric and Statistics Locks

| Contract element | Locked value | Implementation location | Status |
|---|---|---|---|
| CV(FPR) formula | σ/µ with no epsilon | PENDING | — |
| Coverage ratio reported | Always alongside CV(FPR) | PENDING | — |
| AUROC invariance | Test scores unchanged | PENDING | — |
| Seed independence | 9×5 deltas not treated as 45 independent samples | PENDING | — |
| Bootstrap CI basis | 5 seed-level aggregates | PENDING | — |
| Sign test role | Supporting evidence only | PENDING | — |
| Holm p-values | Descriptive only | PENDING | — |
| mu_flag_threshold | `round(M_clean / 8, 2 s.f.)` locked before any poisoned run | PENDING | — |

### Calibration-Pending Clients

| Contract element | Locked value | Implementation location | Status |
|---|---|---|---|
| n_min threshold | 100 benign calibration samples | PENDING | — |
| Fallback threshold | tau_global for Calibration-Pending clients | PENDING | — |
| CV(FPR) exclusion | Calibration-Pending clients excluded from CV(FPR) | PENDING | — |
| Victim set exclusion | Calibration-Pending clients excluded from victim sets | PENDING | — |
| B4 clustering exclusion | Calibration-Pending clients excluded from B4 | PENDING | — |
| Coverage ratio reported | Required | PENDING | — |

---

## Evidence Rules

- Every PENDING row must be resolved with file path and line range before implementation begins.
- Any VIOLATION row blocks implementation until Hermes reviews and resolves it.
- Do not mark a row PASS without reading the actual code.
