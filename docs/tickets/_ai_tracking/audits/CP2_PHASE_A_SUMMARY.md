# CP2 Phase-A Summary — Audit-Phase Cleanup Checkpoint

**Date:** 2026-06-16
**Ticket:** CP2-T013
**Status:** All T007–T012 complete. T013 consolidation. T014 and T015 pending.

---

## 1. Phase-A Confirmations Status

| Confirmation | Status | Evidence |
|---|---|---|
| #1 — Clean artifacts exist + E=1 | **PENDING (FB1 triggered)** | T007: artifacts absent; `local_epochs: 5` config flag |
| #2 — Split semantics + reservoir path | **PASS** | T008: 60/1/20/1/~18; benign-only; source-precedence rule 2 |
| #3 — B4 reproducible; FB3 not triggered | **PASS** | T011: K=3, n_init=10, random_state=42 confirmed; 123 tests pass |
| #4 — No journal contamination in CP2 paths | **PASS** | T009: forbidden scope absent from src/tests |

---

## 2. Reuse / Replace / Quarantine Decision Map

| Module / File | Decision | Target Ticket | Evidence |
|---|---|---|---|
| `src/datp/thresholding/strategies/b1_global.py` | **REUSE** | T030 wraps | T011: arithmetic mean of eligible taus |
| `src/datp/thresholding/strategies/b2_personalized.py` | **REUSE** | T030 wraps | T011: per-client p95 |
| `src/datp/thresholding/strategies/b4_cluster.py` | **REUSE + HARDEN** | T031: decomposition; explicit init/max_iter kwargs | T011: core B4 PASS |
| `src/datp/thresholding/eligibility.py` | **REUSE** | T030 | T011 |
| `src/datp/thresholding/thresholds.py` (`conformal_threshold`) | **SUBSTRATE — ISOLATE** | T022: guardrail; Phase C cleanup | T009: not wired to CP2 policies |
| `src/datp/thresholding/thresholds.py` (`percentile_threshold`, `arithmetic_mean_threshold`, `derive_threshold`) | **REUSE** | T030/T031 | T011 |
| `src/datp/scoring/generation.py` | **REUSE** | FB1 (when authorized) | T007: infrastructure correct |
| `src/datp/scoring/cal_loading.py` | **REUSE** | T025/T026 | T008: loads cal split correctly |
| `src/datp/scoring/schema.py` | **REUSE** | — | T007: reconstruction_error |
| `src/datp/validation/score_manifest.py` | **REUSE** | T021: provenance gate extends this | T007 |
| `src/datp/statistics/bootstrap.py` | **REUSE** | T035 | T012: percentile + BCa both present |
| `src/datp/statistics/cv.py` | **REUSE** | T033 | T012: σ/µ no ε |
| `src/datp/statistics/wilcoxon.py` | **REUSE (supporting only)** | T035 | T012 |
| `src/datp/evaluation/metrics.py` (DispersionMetrics/BinaryMetrics) | **REUSE** | T033 | T012 |
| `src/datp/evaluation/ranking.py` (AUROC) | **REUSE** | T033 | T012 |
| `src/datp/attacks/calibration_poisoning.py` | **QUARANTINE → REPLACE** | T027 | T010 |
| `src/datp/attacks/poisoning_config.py` | **QUARANTINE → REPLACE** | T017/T027 | T010 |
| `src/datp/attacks/poisoning_metrics.py` | **QUARANTINE → REPLACE** | T033 | T010 |
| `src/datp/experiments/calibration_poisoning.py` | **QUARANTINE → REPLACE** | T027/T029 | T010 |
| `src/datp/core/enums.py` (`Baseline.B3`) | **SUBSTRATE — DO NOT REMOVE** | T016: new ThresholdPolicy enum excludes B3 | T009 |
| `src/datp/data/datasets/nbaiot/` | **REUSE** | T025/T042 | T008 |
| `src/datp/data/splits.py` | **REUSE** | T025 | T008 |

---

## 3. Missing CP2 Machinery (to build in Phase B/C)

| Missing | Ticket |
|---|---|
| `ThresholdPolicy` enum `{B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER}` (no B3) | T016 |
| `AttackerObjective`, `SourceStrategy`, `TargetScope` enums | T016 |
| `fraction` discrete grid `{0, 0.10, 0.20, 0.40}` in typed config | T017 |
| `local_epochs: 1` config fix + FederationConfig validator | T017/T022 |
| `SeedSequence([training_seed, poisoning_seed, client_id, scope_id])` child seeds | T019 |
| `mu_flag_threshold = round(M_clean/8, 2 s.f.)` locked before poisoned runs | T033 |
| `REPLACE_FIXED_BUDGET` injector (replaces shift_magnitude prototype) | T027 |
| Reservoir selection (RANDOM/HIGH/LOW, victim-local, tail strategies) | T026 |
| Artifact provenance gate (reject E=5, journal, missing) | T021 |
| B4 decomposition `Δτ_total = Δτ_agg + Δτ_churn` | T031 |
| `Δτ`, `Δτ_rel`, `δ_{τ,i}` metric engine | T033 |
| ASR, BlastRadius, SpilloverCount | T033/T034 |
| Sign test (exact paired) | T035 |
| Holm correction | T035 |
| Seed-level aggregates + paired comparison | T035 |
| Coverage ratio | T033 |

---

## 4. Blockers for Phase B

| Blocker | Action |
|---|---|
| Clean artifacts absent (FB1 triggered) | Fix `local_epochs: 1` in Phase B (T017/T022); then activate FB1 with authorization |
| `local_epochs: 5` in config | Phase B T017/T022: fix to `1` |

Phase B can proceed without clean artifacts (protocol lock, enum design). FB1 runs
after Phase B config fix.

---

## 5. Confirmed CP2 Locks (from audit)

| Lock | Status |
|---|---|
| No Edge-IIoTset | CONFIRMED ABSENT |
| No FedProx/Ditto/FedRep/FedPer/Laridi/FedStatsBenign | CONFIRMED ABSENT |
| No temporal recalibration | CONFIRMED ABSENT |
| No conformal in CP2 policy paths | CONFIRMED (substrate only) |
| B3 NOT in default policy enum | CONFIRMED (DATP Baseline enum is substrate; CP2 ThresholdPolicy will exclude B3) |
| E=5 in .py code: NONE | CONFIRMED |
| `local_epochs: 5` in YAML → fix needed | FLAGGED (T017/T022) |
| Benign-only chronological split | CONFIRMED (CHRONOLOGICAL_SPLIT=True, BENIGN_ONLY_CALIBRATION=True) |
| n_min=100, pending → tau_global, excluded from CV(FPR) | CONFIRMED |
| Reservoir = source-precedence rule 2 (victim-local cal pool) | CONFIRMED |
| Test/training scores not a reservoir | CONFIRMED |
| B4 K=3, n_init=10, random_state=42 | CONFIRMED |
| CV(σ/µ, no ε) | CONFIRMED |
| 45 independent samples NOT used | CONFIRMED (two-layer unit not yet enforced; T035 to build) |

---

## 6. Graphify Status

```
graphify update . → 6365 nodes, 15697 edges, 413 communities (2026-06-16)
```

Graph rebuilt successfully. Too large for HTML viz (limit 5000); `graph.json` and
`GRAPH_REPORT.md` updated under `graphify-out/`. No API key used (code-only).

---

## 7. Audit Notes Index

| File | Ticket | Verdict |
|---|---|---|
| `CP2_INITIAL_REPO_AUDIT.md` | T001 | Prototype mismatch; conformal_threshold flag |
| `CP2-T002_additional_docs_alignment.md` | T002 | DATP→CP2 reuse map; journal boundary |
| `CP2-T003_claude_github_audit.md` | T003 | Agents/skills CP2-aligned |
| `CP2-T005_consistency_checkpoint.md` | T005 | 59+4 confirmed; links resolve |
| `CP2-T006_setup_drift_check.md` | T006 | NO DRIFT |
| `CP2-T007_artifact_audit.md` | T007 | ARTIFACTS MISSING; FB1 triggered; E=5 config |
| `CP2-T008_split_semantics_audit.md` | T008 | Split confirmed; reservoir rule 2 |
| `CP2-T009_contamination_audit.md` | T009 | NO CONTAMINATION; B3/conformal substrate |
| `CP2-T010_attack_prototype_audit.md` | T010 | QUARANTINE+REPLACE all 4 proto files |
| `CP2-T011_thresholding_b4_audit.md` | T011 | B4 PASS; 2 hardening notes; FB3 NOT triggered |
| `CP2-T012_statistics_reporting_audit.md` | T012 | Reuse map; sign test/Holm missing |
| `CP2_PHASE_A_SUMMARY.md` | T013 | This file |
