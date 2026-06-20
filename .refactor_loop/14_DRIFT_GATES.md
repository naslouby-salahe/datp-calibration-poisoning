# 14_DRIFT_GATES.md — Scientific Drift Gate Checklist

Run this checklist after every implementation loop.
Any FAIL row blocks merge. FAIL rows must be reviewed by Hermes before proceeding.

Status values: `PASS` | `FAIL` | `N/A` | `NOT_YET_CHECKED`

---

## How to Use

1. After an implementation loop, read every row.
2. For each row, inspect the actual code (file+line) and set status.
3. Write the evidence (file path + line) in the Evidence column.
4. Any FAIL row must be written to `agents/BLOCKERS.md` with severity CRITICAL.
5. Route FAIL rows to Hermes for review before any merge.

---

## Current Gate State

**Last run:** NOT YET RUN
**Runner:** —
**Phase:** DOCS_INITIALIZATION_ONLY — no implementation has occurred

---

## Attack Boundary

| # | Gate | Status | Evidence |
|---|---|---|---|
| 1 | Calibration-only poisoning — only benign calibration scores are modified | NOT_YET_CHECKED | — |
| 2 | Training data not mutated | NOT_YET_CHECKED | — |
| 3 | Model weights not mutated | NOT_YET_CHECKED | — |
| 4 | FedAvg aggregation not mutated | NOT_YET_CHECKED | — |
| 5 | Test scores not mutated | NOT_YET_CHECKED | — |
| 6 | Test labels not mutated | NOT_YET_CHECKED | — |
| 7 | Clean artifacts used read-only | NOT_YET_CHECKED | — |

## Regime and Artifacts

| # | Gate | Status | Evidence |
|---|---|---|---|
| 8 | E=1 validation — artifacts are conference-faithful | NOT_YET_CHECKED | — |
| 9 | N-BaIoT (REGIME_A_NBAIOT) is primary dataset | NOT_YET_CHECKED | — |

## Policy Locks

| # | Gate | Status | Evidence |
|---|---|---|---|
| 10 | Default policies: B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER only | NOT_YET_CHECKED | — |
| 11 | B3 not in default policy enum or dispatch path | NOT_YET_CHECKED | — |

## Reservoir and Injection

| # | Gate | Status | Evidence |
|---|---|---|---|
| 12 | Reservoirs are victim-local benign calibration scores only | NOT_YET_CHECKED | — |
| 13 | No train-score leakage into reservoir | NOT_YET_CHECKED | — |
| 14 | No test-score leakage into reservoir | NOT_YET_CHECKED | — |
| 15 | RANDOM_BENIGN present as negative control | NOT_YET_CHECKED | — |
| 16 | HIGH_SCORE_BENIGN produces signed threshold raise | NOT_YET_CHECKED | — |
| 17 | LOW_SCORE_BENIGN produces signed threshold lower | NOT_YET_CHECKED | — |
| 18 | Fixed-size replacement: `m_i = max(1, round(f · n_i))` | NOT_YET_CHECKED | — |
| 19 | With-replacement resampling | NOT_YET_CHECKED | — |
| 20 | Cardinality preserved: `n_i` constant after injection | NOT_YET_CHECKED | — |
| 21 | Clean arrays never mutated in place | NOT_YET_CHECKED | — |

## Pairing and Seeds

| # | Gate | Status | Evidence |
|---|---|---|---|
| 22 | Clean and poisoned runs paired by training_seed and victim plan | NOT_YET_CHECKED | — |
| 23 | Poisoning is the sole stochastic difference between paired runs | NOT_YET_CHECKED | — |
| 24 | Seed scheme uses `SeedSequence([training_seed, poisoning_seed, client_id, scope_id])` | NOT_YET_CHECKED | — |
| 25 | No integer seed addition | NOT_YET_CHECKED | — |

## B4 Locks

| # | Gate | Status | Evidence |
|---|---|---|---|
| 26 | B4 uses K=3 for Regime A | NOT_YET_CHECKED | — |
| 27 | B4 uses k-means++, n_init=10, max_iter=300, random_state=42 | NOT_YET_CHECKED | — |
| 28 | B4 produces client-effective threshold deltas | NOT_YET_CHECKED | — |
| 29 | No raw k-means label-ID comparison across runs | NOT_YET_CHECKED | — |

## Manifest and Provenance

| # | Gate | Status | Evidence |
|---|---|---|---|
| 30 | Sweep manifest is complete (all client/seed/fraction combinations present) | NOT_YET_CHECKED | — |
| 31 | Provenance metadata written alongside results | NOT_YET_CHECKED | — |

## Scope Boundaries

| # | Gate | Status | Evidence |
|---|---|---|---|
| 32 | No journal-extension scope in any active code path | NOT_YET_CHECKED | — |
| 33 | No broad robustness claims beyond calibration channel | NOT_YET_CHECKED | — |
| 34 | No privacy guarantees claimed | NOT_YET_CHECKED | — |
| 35 | No deployment-readiness claims | NOT_YET_CHECKED | — |
| 36 | No evasion claims | NOT_YET_CHECKED | — |

---

## Gate Run History

| Run ID | Date | Runner | Phase | PASS count | FAIL count | N/A count | Outcome |
|---|---|---|---|---|---|---|---|
| — | — | — | DOCS_INITIALIZATION_ONLY | — | — | — | NOT YET RUN |
