# results-statistics-skill

## Purpose

Validate statistical and metric reporting for DATP results.

## Required Metrics

1. CV(FPR)
2. Coverage ratio
3. Macro-F1
4. Worst-client balanced accuracy
5. Bootstrap confidence intervals
6. FPR
7. TPR
8. Per-seed metrics
9. Per-client metrics
10. Calibration-Pending counts

## Rules

1. CV(FPR) must be reported with coverage ratio.
2. Bootstrap CI must accompany baseline comparisons when required.
3. Regime A is confirmatory.
4. Regime B is supportive.
5. Regime C is exploratory.
6. Missing clients must be explained.
7. Ineligible clients must be handled consistently.
8. B5 must not support the core claim.
9. B0 must remain a reference comparator.
10. Metrics must match artifact provenance.

## Required Output

1. Metric validity
2. Missing statistics
3. Invalid comparisons
4. Claim risks
5. Required corrections