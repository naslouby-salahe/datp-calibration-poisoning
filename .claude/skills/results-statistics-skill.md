# results-statistics-skill

> **datp-cp active.** Protocol of record: `docs/DATP_CP_Roadmap.md`.
> No backward compatibility by default. Tests: unit → integration (`tests/`).
> Forbidden: training/model/aggregation/test-data poisoning, Edge-IIoTset,
> conformal/temporal recalibration, journal-extension scope.
> Canonical policies: `GLOBAL_THRESHOLD`, `LOCAL_THRESHOLD`, `CLUSTER_THRESHOLD`.

## Purpose

Validate statistical and metric reporting for datp-cp results. Protocol of record: `docs/DATP_CP_Roadmap.md` §10–11.

## Required Metrics (roadmap §10)

**Mechanism endpoint:**
- `Δτ_i,p`, `|Δτ_i,p|`, `Δτ_rel_i,p`
- Materiality: `|Δτ_i,p| >= δτ_i`

**Detection metrics (THRESHOLD_RAISE):**
- `TPR`, `FPR`, `TNR`, `BA`, `MacroF1`, `P10_MacroF1`, `WorstClientBA`

**Dispersion metrics (THRESHOLD_LOWER):**
- `CV(FPR)`, `IQR(FPR)`, `max-min FPR`, `WorstClientFPR`
- `CV(FPR) = std(FPR_i, ddof=0) / mean(FPR_i)` over eligible clients

**Blast radius and spillover:**
- `BlastRadius`: non-victim eligible clients with material `|Δτ|`
- `SpilloverCount`: non-victim eligible clients with correctly signed downstream degradation

**AUROC sanity check:**
- Must be zero; movement indicates protocol leakage

## Statistical Design Rules (roadmap §11)

1. All comparisons are paired by training seed, victim plan, threshold policy, source-objective pair, and fraction.
2. Two-layer unit of analysis:
   - Layer 1: victim-level paired deltas (sign consistency, victim heterogeneity)
   - Layer 2: seed-level aggregates (one aggregate per training seed by averaging over eligible victims)
3. Primary CIs operate on 5 seed-level aggregates, not on the 9×5 grid.
4. Sign consistency: expected sign in at least 4/5 seeds.
5. Strict-majority victim rule: ≥5 of 9 eligible N-BaIoT clients.
6. Bootstrap CI: 95% percentile bootstrap over seed aggregates.
7. Exact paired sign test: supporting evidence only, does not gate inference at n=5.
8. Holm-adjusted p-values: descriptive within the primary family.

## CV(FPR) Handling Rules

1. `CV(FPR)` must always be paired with eligible-client count and seed count.
2. `CV` is undefined when mean FPR is zero — exclude from CV-based claims for that cell.
3. `CV` is flagged when mean FPR is below `mu_flag_threshold`.
4. Absolute dispersion metrics (`IQR`, `max-min`, `WorstClientFPR`) remain valid when CV is undefined or unstable.

## Required Output

1. Metric validity
2. Missing statistics
3. Invalid comparisons
4. Statistical design issues
5. CV handling issues
6. Claim risks
7. Required corrections
