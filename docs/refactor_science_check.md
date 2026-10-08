# Refactor science check

Question: did the refactor (module merge, checkpoint removal, YAML config, parallel seed workers) change the science?
Compared: new full run (`outputs/`, `results/`) vs `backup_runs_2/` (pre-refactor outputs) vs `backup_runs/outputs/` (older run).
Machine: 10 CPUs, CPU training, `sweep_workers: 5`.

## Verdict

1. **Training is not reproducible run to run, independent of the refactor.** Retraining seed 0 gives scores that differ by about 12-17 % (relative L2) between any two runs, including two runs of the *new* code and one run of the *original* `HEAD` code. New-vs-old differences are the same size as old-vs-old differences.
2. **Everything downstream of the scores is unchanged.** Feeding the *old* scores through the new evaluation, poisoning, sensitivity and report stages reproduces the old outputs: analysis files and tables byte-identical, manifests and metrics equal within 1e-9 (relative), PNG figures identical.
3. **Aggregate science is statistically consistent** across all three runs (clean metrics within about 1-2 standard errors; poisoning group means correlate at 0.88-0.9999, with new-vs-old differences no larger than old-vs-old differences). AUROC is invariant under poisoning in all 4,320 rows of every run.

## 1. Training reproducibility (seed 0, GLOBAL, 150 rounds, same data)

Relative L2 difference of reconstruction-error scores, per score file (27 files per run):

| pair | identical files | median rel. L2 | max rel. L2 |
|---|---:|---:|---:|
| new run A1 vs new run A2 (same code, same seed) | 0/27 | 0.122 | 0.198 |
| new A1 vs original HEAD code | 0/27 | 0.162 | 0.216 |
| new A2 vs original HEAD code | 0/27 | 0.155 | 0.229 |
| original HEAD code vs backup_runs_2 | 0/27 | 0.170 | 0.341 |
| new A1 vs backup_runs_2 | 0/27 | 0.141 | 0.286 |
| full new run vs backup_runs_2 (seed 0) | 0/27 | 0.164 | 0.249 |

The same code with the same seed does not reproduce its own scores, so a score-level comparison cannot show a regression. Likely causes (not investigated): asynchronous Ray/Flower client execution and floating-point ordering amplified over 150 rounds. Reproducibility could be tested by making client execution deterministic.

## 2. New downstream pipeline on the old scores

`backup_runs_2/scores` (plus convergence files) copied to a scratch directory; scoring manifests given a `model_hash`; results, manifests, analysis, figures and tables regenerated with the new code.

| area | files | byte-identical | equal within tolerance | different |
|---|---:|---:|---:|---:|
| analysis (csv/json) | 40 | 37 | 1 | 2 (only file-path lists in `reporting_audit.json`, `metrics_schema_validation.json`) |
| tables (`table3_nbaiot`) | 2 | 2 | 0 | 0 |
| poisoning + sensitivity manifests | 2 | 0 | 2 | 0 |
| per-policy `metrics.json` | 30 | 0 | 30 | 0 (only provenance fields differ) |
| figures | 15 | 7 | 0 | 8 (5 PDFs differ in embedded metadata; 3 sidecar JSONs differ only in source-path lists) |
| `resolved_config.yaml` | 30 | 0 | 0 | 30 (format changed, intended) |

Old-only files: legacy figure copies (`figure1_seed1.*` etc.), old comparison csvs, `checkpoints/`. New-only files: `audit/` (17 files), `convergence_*` inside the score directories.

## 3. Statistical consistency (full new run vs both older runs)

## Clean baseline metrics: mean ± sd over 10 training seeds

| policy | metric | NEW | backup_runs_2 | backup_runs | max |Δmean| / pooled SE (NEW vs OLD2) | (NEW vs OLD1) |
|---|---|---:|---:|---:|---:|---:|
| global_threshold | cv_fpr | 0.9124 ± 0.0441 | 0.9121 ± 0.0317 | 0.9051 ± 0.0394 | 0.02 | 0.39 |
| global_threshold | cv_tpr | 0.2617 ± 0.0304 | 0.2589 ± 0.0232 | 0.2554 ± 0.0301 | 0.23 | 0.46 |
| global_threshold | mean_fpr | 0.0412 ± 0.0017 | 0.0412 ± 0.0016 | 0.0411 ± 0.0019 | 0.06 | 0.13 |
| global_threshold | std_fpr | 0.0398 ± 0.0016 | 0.0398 ± 0.0016 | 0.0394 ± 0.0013 | 0.05 | 0.66 |
| global_threshold | worst_client_fpr | 0.1301 ± 0.0033 | 0.1300 ± 0.0031 | 0.1302 ± 0.0033 | 0.10 | 0.02 |
| global_threshold | p10_macro_f1 | 0.3882 ± 0.0626 | 0.3842 ± 0.0601 | 0.3977 ± 0.0532 | 0.14 | 0.37 |
| global_threshold | worst_ba | 0.6547 ± 0.0107 | 0.6544 ± 0.0112 | 0.6574 ± 0.0078 | 0.06 | 0.64 |
| global_threshold | tau_global | 0.3813 ± 0.0298 | 0.3830 ± 0.0288 | 0.3818 ± 0.0283 | 0.13 | 0.04 |
| local_threshold | cv_fpr | 0.3391 ± 0.0523 | 0.3245 ± 0.0420 | 0.3333 ± 0.0342 | 0.69 | 0.29 |
| local_threshold | cv_tpr | 0.2892 ± 0.0615 | 0.3101 ± 0.0224 | 0.2959 ± 0.0359 | 1.01 | 0.29 |
| local_threshold | mean_fpr | 0.0427 ± 0.0021 | 0.0428 ± 0.0022 | 0.0427 ± 0.0021 | 0.08 | 0.06 |
| local_threshold | std_fpr | 0.0154 ± 0.0027 | 0.0148 ± 0.0024 | 0.0151 ± 0.0017 | 0.56 | 0.32 |
| local_threshold | worst_client_fpr | 0.0657 ± 0.0076 | 0.0658 ± 0.0077 | 0.0681 ± 0.0063 | 0.02 | 0.77 |
| local_threshold | p10_macro_f1 | 0.3302 ± 0.0653 | 0.3129 ± 0.0426 | 0.3352 ± 0.0575 | 0.70 | 0.18 |
| local_threshold | worst_ba | 0.6713 ± 0.0593 | 0.6527 ± 0.0030 | 0.6545 ± 0.0048 | 0.99 | 0.89 |
| local_threshold | tau_global | 0.3813 ± 0.0298 | 0.3830 ± 0.0288 | 0.3818 ± 0.0283 | 0.13 | 0.04 |
| cluster_threshold | cv_fpr | 0.6282 ± 0.1215 | 0.6141 ± 0.1018 | 0.6145 ± 0.1428 | 0.28 | 0.23 |
| cluster_threshold | cv_tpr | 0.2964 ± 0.0264 | 0.2972 ± 0.0267 | 0.3131 ± 0.0086 | 0.07 | 1.90 |
| cluster_threshold | mean_fpr | 0.0436 ± 0.0043 | 0.0447 ± 0.0049 | 0.0434 ± 0.0039 | 0.53 | 0.10 |
| cluster_threshold | std_fpr | 0.0294 ± 0.0082 | 0.0295 ± 0.0077 | 0.0286 ± 0.0086 | 0.03 | 0.21 |
| cluster_threshold | worst_client_fpr | 0.1139 ± 0.0247 | 0.1136 ± 0.0259 | 0.1115 ± 0.0278 | 0.03 | 0.21 |
| cluster_threshold | p10_macro_f1 | 0.3262 ± 0.0566 | 0.3265 ± 0.0571 | 0.2995 ± 0.0002 | 0.01 | 1.49 |
| cluster_threshold | worst_ba | 0.6555 ± 0.0057 | 0.6538 ± 0.0073 | 0.6556 ± 0.0043 | 0.60 | 0.02 |
| cluster_threshold | tau_global | 0.3813 ± 0.0298 | 0.3830 ± 0.0288 | 0.3818 ± 0.0283 | 0.13 | 0.04 |

Largest standardized difference of means across all 24 policy/metric cells: NEW vs backup_runs_2 = 1.01 SE, NEW vs backup_runs = 1.90 SE.

## Poisoning matrix (4,320 rows each)

- NEW: rows=4320, AUROC invariant in all rows: True, rows with mu_flag triggered: 0, rows with delta_tau>0 (any nonzero): 3210
- OLD2: rows=4320, AUROC invariant in all rows: True, rows with mu_flag triggered: 0, rows with delta_tau>0 (any nonzero): 3199
- OLD1: rows=4320, AUROC invariant in all rows: True, rows with mu_flag triggered: 0, rows with delta_tau>0 (any nonzero): 3199

Group means per (policy, source, objective, fraction), averaged over victims and seeds. Agreement between runs:

| metric | groups | corr(NEW,OLD2) | corr(NEW,OLD1) | corr(OLD2,OLD1) | sign agreement NEW/OLD2 | sign agreement NEW/OLD1 | mean |Δ| NEW-OLD2 | mean |Δ| NEW-OLD1 | mean |Δ| OLD2-OLD1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| delta_tau | 48 | 0.9996 | 0.9997 | 0.9999 | 0.806 | 0.861 | 0.00352 | 0.00298 | 0.00324 |
| delta_cv_fpr | 48 | 0.9803 | 0.9793 | 0.9781 | 0.806 | 0.778 | 0.00340 | 0.00406 | 0.00495 |
| delta_mean_fpr | 48 | 0.9709 | 0.9858 | 0.9809 | 0.889 | 0.806 | 0.00017 | 0.00016 | 0.00020 |
| delta_worst_client_fpr | 48 | 0.8778 | 0.8961 | 0.8811 | 0.917 | 0.861 | 0.00084 | 0.00102 | 0.00109 |
| victim_delta_tpr | 48 | 0.9510 | 0.9788 | 0.9679 | 0.861 | 0.861 | 0.00800 | 0.00417 | 0.00688 |
| victim_delta_ba | 48 | 0.8947 | 0.9589 | 0.9325 | 0.694 | 0.778 | 0.00389 | 0.00201 | 0.00329 |
| victim_delta_macro_f1 | 48 | 0.9495 | 0.9744 | 0.9797 | 0.806 | 0.861 | 0.01252 | 0.00804 | 0.00876 |

### Headline groups (fraction 0.40, RANDOM_BENIGN): mean over victims & seeds

| policy | objective | metric | NEW | backup_runs_2 | backup_runs |
|---|---|---|---:|---:|---:|
| global_threshold | threshold_raise | delta_tau | -0.00014 | -0.00016 | -0.00009 |
| global_threshold | threshold_raise | delta_cv_fpr | -0.00046 | 0.00001 | -0.00011 |
| global_threshold | threshold_raise | victim_delta_tpr | 0.00000 | 0.00000 | 0.00000 |
| global_threshold | threshold_lower | delta_tau | -0.00058 | 0.00007 | -0.00035 |
| global_threshold | threshold_lower | delta_cv_fpr | -0.00101 | 0.00020 | -0.00061 |
| global_threshold | threshold_lower | victim_delta_tpr | 0.00000 | 0.00268 | 0.00537 |
| local_threshold | threshold_raise | delta_tau | -0.00126 | -0.00146 | -0.00084 |
| local_threshold | threshold_raise | delta_cv_fpr | -0.00089 | -0.00098 | -0.00131 |
| local_threshold | threshold_raise | victim_delta_tpr | 0.00000 | 0.00806 | 0.00537 |
| local_threshold | threshold_lower | delta_tau | -0.00524 | 0.00067 | -0.00318 |
| local_threshold | threshold_lower | delta_cv_fpr | -0.00013 | -0.00031 | 0.00032 |
| local_threshold | threshold_lower | victim_delta_tpr | 0.00452 | 0.01343 | 0.01258 |
| cluster_threshold | threshold_raise | delta_tau | 0.00230 | -0.00062 | -0.01000 |
| cluster_threshold | threshold_raise | delta_cv_fpr | -0.01450 | -0.00600 | 0.01036 |
| cluster_threshold | threshold_raise | victim_delta_tpr | -0.00739 | -0.01979 | -0.00570 |
| cluster_threshold | threshold_lower | delta_tau | -0.01175 | -0.00039 | -0.00881 |
| cluster_threshold | threshold_lower | delta_cv_fpr | -0.01769 | -0.00956 | 0.01356 |
| cluster_threshold | threshold_lower | victim_delta_tpr | 0.01289 | -0.01260 | 0.01442 |


## 4. File-level comparison of the full new run

- vs `backup_runs_2`: scores differ in all files (see section 1); downstream files differ accordingly. Largest within-tolerance numeric noise outside scores is below 1e-9.
- vs `backup_runs/outputs`: same picture; that run is older and has fewer artifacts (no sensitivity manifest, 4 analysis files).

## Not verified

- The source of the run-to-run training nondeterminism.
- Bitwise equivalence of training itself (impossible to test while training is nondeterministic).
- `results/` vs paper tables (paper sources are not in the repo).

## Follow-up: cause of the training nondeterminism

Flower's `FedAvg` sums client updates in the order the clients finish (and `aggregate_evaluate` sums the weighted loss in the same order). Floating-point addition is not associative, so each of the 150 rounds carries tiny order-dependent differences that compound.

Test (scratch script, repository code unchanged): override `DatpFedAvg.aggregate_fit` and `aggregate_evaluate` to sort results by `num_examples` (distinct per client) before aggregating, then train seed 0 twice concurrently. Result: **27/27 score files bitwise identical** (unsorted runs differ by 12-17 %).

A fix is therefore a deterministic aggregation order (for example sort by client id, returned in the fit/evaluate metrics because Flower's client proxy ids are random per run). It changes the trained models once, so all results would need regenerating.

## Follow-up: which findings are robust to retraining

Mean over victims and seeds at fraction 0.40 (values: new run | backup_runs_2 | backup_runs; ± is standard error over the 10 training seeds):

| ΔCV(FPR) | Cluster | Local | Global |
|---|---|---|---|
| HIGH_SCORE_BENIGN / THRESHOLD_RAISE | +0.174±0.045 \| +0.175±0.029 \| +0.201±0.038 | +0.104 \| +0.106 \| +0.105 | +0.062 \| +0.064 \| +0.058 |
| LOW_SCORE_BENIGN / THRESHOLD_LOWER | +0.052±0.040 \| +0.051±0.024 \| +0.059±0.033 | +0.056 \| +0.059 \| +0.053 | −0.019 \| −0.020 \| −0.019 |

- Stable in all three runs: Cluster > Local > Global for the raise objective; Global and Local values reproduce to within about 0.003; AUROC invariance; the claim-gate outcomes (16 `full_vulnerability`, 1 `calibration_instability`, 1 `null_or_conditional`) are identical in the new run and `backup_runs_2`.
- Not stable: the Cluster-vs-Local ordering for the lowering objective (Cluster's seed-to-seed SE is about 0.03-0.04, ten times Local's), the sign of Cluster effects near zero (random-control Cluster ΔCV(FPR) is -0.014, -0.006, +0.010 across runs), and small-fraction (0.10) Cluster effects.

## Deterministic run (aggregation sorted by client id)

`DatpFedAvg` now sorts fit and evaluate results by client id before aggregating. Verification:

- Seed 0 trained twice standalone and once inside the 5-worker sweep: **27/27 score files bitwise identical in all three pairings.**
- Full pipeline re-run (baseline, poisoning, sensitivity, report): 30/30 policy runs, 0 failures. Timings in the earlier follow-up apply (baseline about 18 min without competing load).
- Claim-gate decisions are identical to the previous run and to `backup_runs_2` (16 `full_vulnerability`, 1 `calibration_instability`, 1 `null_or_conditional`). AUROC is invariant in all 4,320 rows.

Results of the four available runs (means over 10 training seeds; this run is now exactly reproducible, the other three are not):

| metric | this run | backup_runs_3 | backup_runs_2 | backup_runs |
|---|---|---|---|---|
| clean CV(FPR) Global / Local / Cluster | 0.917 / 0.334 / 0.612 | 0.912 / 0.339 / 0.628 | 0.912 / 0.325 / 0.614 | 0.905 / 0.333 / 0.615 |
| Global − Local clean CV(FPR), 95 % CI | +0.582 [0.535, 0.630] | +0.573 [0.516, 0.631] | +0.588 [0.547, 0.628] | +0.572 [0.529, 0.615] |
| P10 macro-F1 Global / Local / Cluster | 0.398 / 0.398 / 0.322 | 0.388 / 0.330 / 0.326 | 0.384 / 0.313 / 0.327 | 0.398 / 0.335 / 0.300 |
| ΔCV(FPR) f=0.40, HIGH/RAISE Cluster / Local / Global | +0.208 / +0.106 / +0.052 | +0.174 / +0.104 / +0.062 | +0.175 / +0.106 / +0.064 | +0.201 / +0.105 / +0.058 |
| ΔCV(FPR) f=0.40, LOW/LOWER Cluster / Local / Global | +0.078 / +0.052 / −0.022 | +0.052 / +0.056 / −0.019 | +0.051 / +0.059 / −0.020 | +0.059 / +0.053 / −0.019 |

Read-across:

- Robust in all four runs: Global − Local clean CV(FPR) about +0.57 to +0.59; Cluster > Local > Global for the raise objective; Global and Local ΔCV(FPR) to within about 0.01; AUROC invariance; claim-gate outcomes.
- Fragile: "Global has the best P10 macro-F1". It holds in three runs and ties Local in this run, because per-seed Local P10 macro-F1 is bimodal (about 0.30 or 0.42-0.47, with an outlier at 0.88 for seed 8). Worst-client BA for Local shows the same outliers (this run 0.692 vs 0.65-0.67 before). Cluster-vs-Local ordering for the lowering objective is also not stable across runs.
- The older paper figure of +0.276 / +0.107 / +0.054 (Cluster / Local / Global at f=0.40) was not reproduced by any run under the metric used here (mean `delta_cv_fpr` over victims and seeds).
