# Audit Round 02: Numerical, Table, Figure, and Result Consistency

## Checks
- Compared baseline table values against `outputs/tables/table3_nbaiot.csv`.
- Checked bootstrap baseline pairwise comparisons against `outputs/analysis/bootstrap_cis.csv`.
- Checked protocol constants against `docs/DATP_CP_Roadmap.md`, implementation, and tests.
- Checked policy names, seed counts, N-BaIoT scope, `K=3`, `q=0.95`, `n_cal >= 100`, `ddof=0`, and AUROC wording.

## Findings

1. MUST_FIX: Fixed-budget formula mismatch was confirmed against code.
   - Evidence: `src/datp/attacks/injection/injector.py` uses `m = max(1, round(fraction * n))`; tests assert the same formula.
   - Fix: same as Round 01.

2. SHOULD_FIX: Lower bullet should remain tied to the fixed-budget variable after the Raise bullet defines it.
   - Fix: kept `replace $m$ positions` after defining `m` in the Raise bullet.

3. REJECTED: Regenerate figures solely to improve aesthetics.
   - Reason: current figures are readable in final PDF; regeneration would be tooling churn without a correctness defect.

4. REJECTED: Add new negative-control figure lines beyond existing table/caption disclosure.
   - Reason: page-budget risk; Table 3 includes Random-Benign rows and Fig. 3 caption reports near-null controls.

## Result
PASS. Table 2 matches `outputs/tables/table3_nbaiot.csv` rounding. Baseline CI claims match `outputs/analysis/bootstrap_cis.csv`. No numeric contradiction found after the fixed-budget correction.
