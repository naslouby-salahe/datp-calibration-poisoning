# DATP-CP Roadmap Amendments

`docs/DATP_CP_Roadmap.md` is absent from the working tree. This file records the scientific-boundary decisions taken for the review-response analyses, so the contract in `CLAUDE.md` stays complete.

## Scientific boundary

The bounded sweep (`NBAIOT_MAIN`) is unchanged and uses only victim-local benign calibration scores drawn `WITH_REPLACEMENT`.

- The attack remains calibration-channel only. It replaces benign threshold-calibration scores of one eligible victim. Training data, labels, weights, gradients, aggregation and test data are never touched.
- Clean calibration arrays are copied before replacement. AUROC stays invariant; `auroc_invariant` is recorded per row.
- The review-response draw variants below run only in `datp sensitivity`. They never enter the bounded matrix, claim gates, or main tables.

### Amendment: sensitivity-only reservoir variants

Reviewer feedback asked for interventions that do not reweight the victim's own buffer. Three variants are added, each as a `ReservoirDraw` member:

| Draw | Values come from | Inside the original boundary? |
|---|---|---|
| `WITHOUT_REPLACEMENT` | victim-local benign calibration scores, each used at most once | yes |
| `DISJOINT_RESERVOIR` | victim-local benign calibration scores at positions that are not replaced (a separate reservoir) | yes |
| `INTERPOLATED_TAIL` | uniform interpolation between adjacent order statistics of the victim-local benign reservoir | no: values are synthesized, so they are flagged `synthesized_values` and reported separately |

`INTERPOLATED_TAIL` is the only departure. It is a distribution-constrained synthesis: every value lies inside the range of the victim's own benign reservoir and no value repeats. It stays diagnostic-only (`SYNTHESIZED_DRAWS`) and is never described as a victim-local calibration score.

Distinct-source variants are capped by pool size: a tail reservoir is 10% of the buffer, so `WITHOUT_REPLACEMENT` and `DISJOINT_RESERVOIR` cannot reach the 20% and 40% budgets for tail sources. `effective_n_replaced` and `full_budget_feasible_rate` record the cap.

### Not added

- Feature perturbation and traffic generation are out of scope: they change the scoring path, not only the calibration scores.

### Trust boundary (threshold overwrite versus score-buffer write)

The `trust_boundary` analysis compares, per policy, the score-buffer shift with:

- trimmed-calibration defenses (`TRIM_FRACTION_PRIMARY` and `TRIM_FRACTION_APPENDIX`), applied to every eligible client's calibration array before threshold derivation;
- a direct-overwrite reference: the shift to the extreme victim-local benign calibration score in the attack direction. A direct overwrite is not bounded by that range; a buffer writer is, and `buffer_to_overwrite_ratio` reports how much of it the buffer attack uses.

The main sweep also records `delta_tau_bound_utilization` per row.

## Vocabulary additions

| Enum | Members | Purpose |
|---|---|---|
| `ReservoirDraw` | `WITH_REPLACEMENT`, `WITHOUT_REPLACEMENT`, `DISJOINT_RESERVOIR`, `INTERPOLATED_TAIL` | Draw mode at injection. Only `WITH_REPLACEMENT` enters the bounded sweep. |
| `SensitivityAnalysis` | `CLUSTER_STABILITY`, `SCALE_NORMALIZATION`, `DRAW_VARIANT`, `TRUST_BOUNDARY` | Analyses in `datp sensitivity`. |

`CalibrationInjectionRule` stays `REPLACE_FIXED_BUDGET`. Threshold policies, source strategies, objectives, and stages are unchanged.

## Added analyses

| Analysis | Output | Notes |
|---|---|---|
| Non-victim downstream | `nonvictim_*` row fields, `downstream_extended` | Mean and worst TPR/FPR change, BA, macro-F1, absolute FP/FN totals, recomputed under each policy. |
| Absolute burden | `victim_fp_*`, `victim_fn_*`, `victim_delta_fp`, `victim_delta_fn` | Counts, not only rates or CV. |
| Fixed clean clusters | `fixed_cluster_*` row fields, `cluster_stability_summary` | `CLUSTER_THRESHOLD` with clean assignments frozen and per-cluster means over poisoned per-client quantiles. |
| Cluster diagnostics | `cluster_sizes_*`, `cluster_n_reassigned`, `cluster_silhouette_*` | Reassignment counts clients whose cluster-mate set changes, so label permutations do not count. |
| Cluster K and init sensitivity | `sensitivity_manifest.json`, `cluster_stability_sensitivity` | K in {2,3,4}, `n_init` in {1,10}, five `random_state` values. |
| Scale comparability | `scale_normalization_summary` | Clean per-client threshold dispersion, plus a median-normalized GLOBAL variant. Sensitivity only, not a new policy. |
| Gate sensitivity | `gate_sensitivity` | Grid over seed consistency 6-10, victim majority 3-7, materiality factor 0.05/0.1/0.2, IQR floor 0.005/0.01/0.02. Protocol defaults are 8, 5, 0.1, 0.01. |
| Full Gate 2 | `directional_excess_over_random` | Per policy, fraction and objective, against the objective-matched Random-Benign control. Adds per-seed excess, mean, bootstrap CI, exact sign-flip p. |
| Downstream uncertainty | `downstream_*`, `downstream_extended` | Seed-level values, percentile bootstrap CI, exact sign-flip p. With 10 seeds the bootstrap interval is unstable; the exact test is the cross-check. |
| Duplicate detectability | `cal_duplicate_rate_*`, `draw_variant_summary` | Duplicate rate before and after injection, and the threshold shift under each draw variant. |
| Trust boundary | `trust_boundary_summary` | Buffer shift versus trimmed-calibration defenses and the direct-overwrite reference. |
| Client-level plots | Figures 5 and 6 | Per-victim effect with seed range; seed-level distributions of victim-averaged effects. |
| Representative seed rule | Figure 1 and 2 sidecars | Seed with lower-median GLOBAL CV(FPR); clients at lowest, median and highest GLOBAL FPR. |

## Metric definitions

Written to `analysis/metric_definitions.json` from `datp.reporting.constants.METRIC_DEFINITIONS`, including Worst BA and P10 client Macro-F1.
