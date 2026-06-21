# datp-cp Implementation Checklist

Derived from `docs/DATP_CP_Roadmap.md`. This is the single source of truth for
implementation status. Do not derive status from existing code — derive it from
the roadmap and then audit the code.

---

## 1. Project Identity and Naming

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 1.1 | `datp-cp` shorthand used consistently | implemented | README.md, CLAUDE.md, Makefile | Consistent | — |
| 1.2 | No stale `CP2`/`cp2` in active code | implemented | src/, tests/ | Guards remain in .claude agents | Update .claude guards |
| 1.3 | No stale `regime` in active code paths | implemented | All fixed: bounded_sweep_cell.py docstring, test_smoke_harness.py, agents, skills | — | — |
| 1.4 | No `B1`/`B2`/`B3`/`B4` in active code as policy labels | implemented | results.py, _warnings.py, figures.py, test files all renamed | — | — |
| 1.5 | No `baseline` used as threshold-policy concept | implemented | `AuditOutputName.POLICY_INVARIANTS`; test functions renamed `test_policy_run_paths_*` | — | — |
| 1.6 | `BaselineRunPaths` removed from active code | implemented | artifacts/layout.py uses `PolicyRunPaths`; test allowlist updated | — | — |

---

## 2. Allowed Experiment Stages

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 2.1 | `ExperimentStage` enum has exactly the 5 canonical values | implemented | config/stages.py | FINAL_AUDIT, SYNTHETIC_SMOKE, NBAIOT_MAIN, NBAIOT_FULL_OPTIONAL, STRETCH_DIAGNOSTIC_ONLY | — |
| 2.2 | Stage configs map each stage to correct dataset/gate | implemented | config/stages.py | Correct | — |
| 2.3 | No old stage/regime labels in active configs | implemented | All enum-based | — | — |

---

## 3. Allowed Threshold Policies

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 3.1 | `ThresholdPolicy` enum: GLOBAL/LOCAL/CLUSTER only | implemented | attacks/enums.py | Correct | — |
| 3.2 | No `B1`/`B2`/`B4` in policy enum or validators | implemented | attacks/enums.py | Clean | — |
| 3.3 | No `baseline: ThresholdPolicy` pattern | implemented | No such field found | — | — |
| 3.4 | No compatibility aliases for old policy names | implemented | Parsers accept only enum values | — | — |

---

## 4. Makefile Public Workflow

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 4.1 | `make help` target | implemented | Makefile | Present | — |
| 4.2 | `make check` target | implemented | Makefile | Present | — |
| 4.3 | `make datp-cp-clean` target | implemented | Makefile | Present | — |
| 4.4 | `make datp-cp-smoke` target | implemented | Makefile | Present | — |
| 4.5 | `make datp-cp-dry-run` target | implemented | Makefile | Present | — |
| 4.6 | `make datp-cp-run` target | implemented | Makefile | Present | — |
| 4.7 | `make datp-cp-report` target | implemented | Makefile | Present | — |
| 4.8 | `make status` target | implemented | Makefile | Present | — |
| 4.9 | `make audit-results` target | implemented | Makefile | Present | — |
| 4.10 | `make clean` target | implemented | Makefile | Present | — |
| 4.11 | No old regime/diagnostic Makefile targets | implemented | Makefile | Confirmed clean | — |

---

## 5. CLI/Config Surface

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 5.1 | `datp config preview` uses `--stage` / `--policy` | implemented | app/cli/config.py | Uses canonical enum args | — |
| 5.2 | `datp poison smoke` / `dry-run` / `run-bounded-sweep` | implemented | app/cli/poison.py | Canonical | — |
| 5.3 | `datp report all` | implemented | app/cli/report.py | Canonical | — |
| 5.4 | `datp audit results` | implemented | app/cli/audit.py | Canonical | — |
| 5.5 | `COMMANDS.md` references only canonical CLI | implemented | COMMANDS.md updated: `--stage`/`--policy`, "per stage" | — | — |
| 5.6 | No hidden legacy CLI branches | implemented | No old branches found | — | — |

---

## 6. Required Enums

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 6.1 | `ThresholdPolicy` | implemented | attacks/enums.py | GLOBAL/LOCAL/CLUSTER | — |
| 6.2 | `AttackerObjective` | implemented | attacks/enums.py | RAISE/LOWER | — |
| 6.3 | `PoisoningSourceStrategy` | implemented | attacks/enums.py | All 4 values | — |
| 6.4 | `CalibrationInjectionRule` | implemented | attacks/enums.py | REPLACE_FIXED_BUDGET | — |
| 6.5 | `PoisoningKnowledge` | implemented | attacks/enums.py | GRAY_BOX/WHITE_BOX | — |
| 6.6 | `PoisoningTargetScope` | implemented | attacks/enums.py | SINGLE/MULTI/ALL | — |
| 6.7 | `PoisoningDefense` | implemented | attacks/enums.py | NONE/TRIMMED_CALIBRATION | — |
| 6.8 | `ExperimentStage` | implemented | config/stages.py | All 5 stages | — |
| 6.9 | `RunKind` has no unused stale values | implemented | Only CORE_LADDER remains | — | — |

---

## 7. Dead/Obsolete Code

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 7.1 | `AbsorptionClass` / `classify_absorption` removed | implemented | Removed from core/enums.py | — | — |
| 7.2 | `ExperimentConfig.absorption_strong_retention/partial` removed | implemented | Removed from config/models.py and tests | — | — |
| 7.3 | `experiments/baselines/` empty directory | obsolete-code-conflict | src/datp/experiments/baselines/ | Ghost directory | Remove |
| 7.4 | No other dead feature areas | implemented | diagnostics.py (blast/spillover/ASR) is roadmap-needed | — | — |

---

## 8. Data / Artifact Assumptions

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 8.1 | N-BaIoT as primary dataset, physical devices | implemented | data/datasets/nbaiot/spec.py | 9 devices | — |
| 8.2 | CICIoT2023 as diagnostic stretch only | implemented | config/stages.py | STRETCH_DIAGNOSTIC_ONLY | — |
| 8.3 | Raw data read-only, linked from shared location | implemented | README.md + roadmap §12.2 | Documented | — |
| 8.4 | Output root: `outputs/conference_calibration_poisoning/` | partial | config/attack_config.py to verify | Check path template | Verify |
| 8.5 | `n_cal >= 100` eligibility threshold | implemented | attacks/score_containers.py | n_min=100 | — |

---

## 9. Clean Artifact Validation

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 9.1 | Clean artifact audit module | implemented | data/common/audit.py | Present | — |
| 9.2 | Provenance validation (commit, config hash, seed) | implemented | core/provenance.py | Present | — |
| 9.3 | `E=1` locked | implemented | attacks/run_manifest.py local_epochs=1 default | Locked | — |
| 9.4 | FedAvg, split semantics inherited | implemented | federated/protocols/fedavg.py | Present | — |
| 9.5 | Clean artifact manifest (`clean_score_artifacts.json`) | partial | run_manifest.py | Check manifest schema | Verify |

---

## 10. Score-Level Poisoning

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 10.1 | `inject_fixed_budget` implements REPLACE_FIXED_BUDGET | implemented | attacks/injector.py | Present | — |
| 10.2 | No in-place mutation of clean calibration arrays | implemented | injector.py returns new array | Verified by test | — |
| 10.3 | `m_i = max(1, round(f * n_i))` for f > 0; 0 for f=0 | implemented | attacks/injector.py | Present | — |
| 10.4 | With-replacement resampling from reservoir | implemented | attacks/reservoir.py | Present | — |
| 10.5 | Valid source-objective pairs enforced | implemented | attacks/guardrails.py | Present | — |
| 10.6 | Invalid pairs (HIGH_SCORE + LOWER, LOW_SCORE + RAISE) rejected | implemented | attacks/guardrails.py | Present | — |

---

## 11. Calibration-Only Attack Surface

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 11.1 | Attack modifies only benign calibration scores | implemented | injector.py scope | Present | — |
| 11.2 | Test scores never enter reservoir | implemented | attacks/reservoir.py + guardrails.py | Validated | — |
| 11.3 | Training scores never enter reservoir | implemented | Validated by smoke invariant 21 | Present | — |
| 11.4 | Attack-labeled samples never enter calibration | implemented | Validated by smoke invariant 22 | Present | — |
| 11.5 | AUROC invariance check | implemented | attacks/metric_engine.py | Present | — |

---

## 12. Victim-Local Reservoir Logic

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 12.1 | Reservoir is victim-local benign calibration scores | implemented | attacks/reservoir.py | Present | — |
| 12.2 | `HIGH_SCORE_BENIGN`: upper 10% tail | implemented | attacks/source_strategies.py | tail_mass=0.10 | — |
| 12.3 | `LOW_SCORE_BENIGN`: lower 10% tail | implemented | attacks/source_strategies.py | tail_mass=0.10 | — |
| 12.4 | `RANDOM_BENIGN`: no tail targeting | implemented | attacks/source_strategies.py | Present | — |
| 12.5 | Infeasible tail: < 2 distinct values → cell excluded | implemented | attacks/reservoir.py | ReservoirStatus | — |
| 12.6 | `tail_mass = 0.10` locked constant | implemented | attacks/cell_runner.py default | Present | — |

---

## 13. Replacement / Injection Rules

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 13.1 | `REPLACE_FIXED_BUDGET` is the only injection rule | implemented | attacks/enums.py + injector.py | Enforced | — |
| 13.2 | Calibration size stays constant | implemented | inject_fixed_budget contract | Present | — |
| 13.3 | Main fractions: {0, 0.10, 0.20, 0.40} | implemented | attacks/bounded_sweep_matrix.py | Present | — |
| 13.4 | Optional fraction 0.05 gated behind lock | not-in-scope | Not yet implemented | Future | — |

---

## 14. Threshold Recomputation

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 14.1 | `GLOBAL_THRESHOLD`: mean of eligible local q=95 percentiles | implemented | attacks/threshold_recompute.py | Present | — |
| 14.2 | `LOCAL_THRESHOLD`: per-client q=95 percentile | implemented | attacks/threshold_recompute.py | Present | — |
| 14.3 | `CLUSTER_THRESHOLD`: cluster fingerprint + k-means + cluster mean | implemented | attacks/cluster_threshold_recompute.py | Present | — |
| 14.4 | `q = 95` locked across all policies | implemented | poison_names.py THRESHOLD_QUANTILE | Locked | — |
| 14.5 | `ε_num = 1e-12` locked | implemented | attacks/metric_engine.py | Present | — |

---

## 15. Cluster Threshold Behavior

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 15.1 | Fingerprint: [mean, std, skew, p95] | implemented | CLUSTER_FINGERPRINT_FEATURES | Locked | — |
| 15.2 | N-BaIoT: K=3, StandardScaler, k-means++, n_init=10 | implemented | cluster_threshold_recompute.py | Present | — |
| 15.3 | Client-effective threshold deltas (not raw cluster IDs) | implemented | cluster_threshold_recompute.py | Present | — |
| 15.4 | Cluster decomposition: Δτ_total = Δτ_agg + Δτ_churn | implemented | cluster_threshold_recompute.py | Present | — |
| 15.5 | Frozen-clean-scaler diagnostic | implemented | cluster_threshold_recompute.py | Present | — |
| 15.6 | Normalization-gap diagnostic | implemented | cluster_threshold_recompute.py | Present | — |

---

## 16. Paired Clean-vs-Poisoned Metrics

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 16.1 | Paired by training_seed, victim, policy, source, objective, fraction | implemented | attacks/bounded_sweep_cell.py | Present | — |
| 16.2 | Δτ, |Δτ|, Δτ_rel computed | implemented | attacks/metric_engine.py | Present | — |
| 16.3 | Materiality threshold δτ_i computed from IQR | implemented | attacks/metric_engine.py | Present | — |
| 16.4 | Detection metrics: TPR, FPR, TNR, BA, MacroF1, WorstClientFPR | implemented | evaluation/metrics.py + metric_engine.py | Present | — |
| 16.5 | Dispersion metrics: CV(FPR) ddof=0, IQR(FPR), max-min, WorstClientFPR | implemented | attacks/metric_engine.py | Present | — |
| 16.6 | CV(FPR) undefined when mean=0; flagged near-zero | implemented | attacks/metric_engine.py | Present | — |
| 16.7 | AUROC sanity check | implemented | attacks/metric_engine.py | Present | — |
| 16.8 | Blast radius and spillover computation | implemented | attacks/diagnostics.py | Present | — |

---

## 17. Synthetic Smoke Behavior

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 17.1 | f=0 → Δτ=0 | implemented | tests/unit/attacks/test_injector.py | Test present | — |
| 17.2 | RANDOM_BENIGN near-null criterion | implemented | attacks/metric_engine.py + test_smoke_harness.py | Present | — |
| 17.3 | HIGH_SCORE+RAISE → Δτ > 0 | implemented | test_smoke_harness.py | Present | — |
| 17.4 | LOW_SCORE+LOWER → Δτ < 0 (when feasible) | implemented | test_smoke_harness.py | Present | — |
| 17.5 | GLOBAL spillover; LOCAL confinement | implemented | test_smoke_harness.py | Present | — |
| 17.6 | CLUSTER: finite client-effective deltas | implemented | test_cluster_threshold_recompute.py (renamed) | Present | — |
| 17.7 | No in-place mutation | implemented | test_injector.py | Present | — |
| 17.8 | Determinism across seeds | implemented | test_b4_recompute.py → test_cluster_threshold_recompute.py | Present | — |
| 17.9 | AUROC invariance | implemented | test_smoke_harness.py | Present | — |
| 17.10 | Test/training scores rejected as reservoirs | implemented | test_reservoir.py + test_smoke_harness.py | Present | — |
| 17.11 | CV ddof=0 | implemented | test_smoke_harness.py | Present | — |
| 17.12 | All 29 roadmap smoke invariants | partial | test_smoke_harness.py | Most covered; verify completeness | Verify |

---

## 18. N-BaIoT Main Matrix Enumeration

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 18.1 | Dry-run enumerates correct matrix dimensions | implemented | app/cli/poison.py + bounded_sweep_matrix.py | Present | — |
| 18.2 | Policies × sources × fractions × victims × seeds matrix | implemented | attacks/bounded_sweep_matrix.py | Present | — |
| 18.3 | Only valid source-objective pairs in matrix | implemented | attacks/guardrails.py | Enforced | — |
| 18.4 | Five training seeds {0,1,2,3,4}, five poisoning seeds {100..104} | implemented | core/seeds.py | Locked | — |
| 18.5 | All eligible N-BaIoT clients swept | implemented | attacks/bounded_sweep_matrix.py | Present | — |

---

## 19. Manifest / Provenance Requirements

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 19.1 | Per-run manifest records all required provenance fields | implemented | attacks/run_manifest.py | Present | — |
| 19.2 | Code commit recorded | implemented | core/provenance.py | Present | — |
| 19.3 | Config hash recorded | implemented | run_manifest.py | Present | — |
| 19.4 | Seeds, reservoir source, injection rule recorded | implemented | run_manifest.py | Present | — |
| 19.5 | ε_num, q, ddof recorded | implemented | run_manifest.py | Present | — |

---

## 20. Stats / Tables / Figures Hooks

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 20.1 | Bootstrap CI over seed-level aggregates | implemented | attacks/inference.py | Present | — |
| 20.2 | Sign consistency (4/5 seeds) | implemented | attacks/inference.py | Present | — |
| 20.3 | Strict-majority victim rule | implemented | attacks/inference.py | Present | — |
| 20.4 | Holm-adjusted p-values (descriptive) | implemented | attacks/inference.py | Present | — |
| 20.5 | Main tables (Table 1–7) hooks | partial | reporting/tables.py | Check figure/table completeness | Verify |
| 20.6 | Main figures (Figure 1–7) hooks | partial | reporting/figures.py + build.py | Check figure completeness | Verify |
| 20.7 | `TRIMMED_CALIBRATION` defense | partial | attacks/defenses.py | Present; gated | — |

---

## 21. Documentation and .claude Alignment

| # | Item | Status | Files | Notes | Action |
|---|------|--------|-------|-------|--------|
| 21.1 | README.md is canonical datp-cp | implemented | README.md | Clean | — |
| 21.2 | CLAUDE.md is canonical datp-cp | implemented | CLAUDE.md | Clean | — |
| 21.3 | COMMANDS.md reflects actual CLI | implemented | COMMANDS.md updated | — | — |
| 21.4 | `.claude/agents/` are datp-cp canonical | implemented | All agent files updated: CP2/regime/baseline replaced | — | — |
| 21.5 | `.claude/skills/` are datp-cp canonical | implemented | All skill files updated: regime/baseline replaced | — | — |

---

## 22. Excluded / Out-of-Scope Items

| # | Item | Status | Notes |
|---|------|--------|-------|
| 22.1 | Training-data poisoning | excluded | Must never appear as a claim |
| 22.2 | Model poisoning | excluded | Must never appear as a claim |
| 22.3 | Aggregation poisoning | excluded | Must never appear as a claim |
| 22.4 | Privacy guarantees | excluded | Out of scope |
| 22.5 | Deployment readiness | excluded | Out of scope |
| 22.6 | Edge-IIoTset | excluded | Not primary dataset |
| 22.7 | Journal-extension threshold variants | excluded | Out of scope |
| 22.8 | FedProx/Ditto/FedRep comparators | excluded | Out of scope |
| 22.9 | Raw-traffic realizability claims | excluded | Score-level proxy limitation applies |
| 22.10 | Diagnostics as its own feature area | excluded | blast_radius/spillover functions are roadmap-needed; no standalone diagnostics module needed beyond attacks/diagnostics.py |

---

## Summary of Completed Cleanup Actions

All critical cleanup actions have been completed. The following items remain for further work:

| Status | Item | Notes |
|--------|------|-------|
| done | Remove experiments/baselines/ ghost directory | Removed — was empty except __pycache__ |
| done | Rename test_roadmap_b4_k_fixed_at_three | → test_roadmap_cluster_threshold_k_fixed_at_three |
| done | Rename test_lock_mu_flag_threshold_is_deterministic_and_b1_derived | → test_lock_mu_flag_threshold_is_deterministic |
| done | Replace stale run_id="a_b1_seed0" fixtures | → "nbaiot_main_global_threshold_seed0" |
| done | Fix 'baseline cell' message in validation/results.py | → 'clean run cell' |
| done | Fix 'no baseline dimension' comment in artifacts/layout.py | → canonical wording |
| done | Rename test_build_imports_controlled_baselines | → test_build_uses_threshold_policy_not_controlled_baselines |
| done | Fix stale STATS_REPORTING_BASELINES error messages | Now refer to ThresholdPolicy directly |
| done | Rename TestBaselineEnum + methods | → TestThresholdPolicyEnum, canonical method names |
| done | Remove test_b0_not_present and test_deprecated_policy_not_present | Old-name rejection tests; set equality already covers this |
| done | Remove test_collision_proof_no_flat_file_pattern | Old format rejection test; format is already positively asserted |
| done | Rename test_baseline_types_importable, test_baseline_result_required_keys | → test_threshold_result_* |
| done | Rename test_all_baselines_accepted, test_b0_accepted, test_rejects_non_baseline_value | → canonical policy names |
| done | Rename b1_rows variable in test_results_audit.py | → global_rows |
| remaining | Verify §8.4 output root path template | Check config/attack_config.py |
| remaining | Verify §9.5 clean artifact manifest schema | Check run_manifest.py |
| remaining | Verify §17.12 all 29 smoke invariants covered | Check test_smoke_harness.py |
| remaining | Verify §20.5 Table 1–7 hooks complete | Check reporting/tables.py |
| remaining | Verify §20.6 Figure 1–7 hooks complete | Check reporting/figures.py + build.py |

---

*Last updated: Phase 2 cleanup — test stale naming eliminated. Static inspection and ruff/pyright clean.*
