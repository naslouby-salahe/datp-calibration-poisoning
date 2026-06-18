# DATP / CP2 Targeted Remediation — Final Report

**Scope:** External-audit remediation tickets R1–R11 (evidence-first).
**Method:** Each concern verified directly against code/tests/artifacts before acting; narrowest
justified fix only; DATP/CP2 scientific contracts preserved; per-ticket evidence inventories under
`/tmp/datp-remediation-audit/R*.md`.

---

## 1. Executive Summary

All 11 tickets resolved. Of the audit's mixed concerns, most production code was already correct;
3 tickets required minimal production changes (all behaviour-preserving or fail-early-only), and the
remainder were verified correct with test-only scope guards added where a genuine coverage gap existed.

| Ticket | Concern | Verdict | Production change |
|--------|---------|---------|-------------------|
| R1 | Canonical Regime-A B4 K=3 fixed | PARTIALLY VALID → mostly already correct | none (test-only) |
| R2 | CV(FPR) near-zero semantics + dispersion | PARTIALLY VALID | yes — manifest reload validator |
| R3 | Checkpoint summary completeness (B1/B2) | INVALID (correct by design) | none (test-only) |
| R4 | Per-client artifact validation completeness | INVALID | none (test-only) |
| R5 | Full-participation failure diagnostics | PARTIALLY VALID | yes — diagnostics only |
| R6 | Early regime/baseline matrix validation | INVALID / already correct | none |
| R7 | Regime B feature-schema provenance | PARTIALLY VALID | none (test-only) |
| R8 | Ray object-store capacity | PARTIALLY VALID | yes — preflight/observability |
| R9 | Directional concordance vs significance | INVALID / already correct | none |
| R10 | JSON/provenance determinism | INVALID / already correct | none |
| R11 | BatchNorm/weight-decay scope guard | PARTIALLY VALID | none (test-only) |

---

## 2. Production Changes (4 files)

1. **R2 — `src/datp/attacks/bounded_sweep_manifest.py`**
   Added a `field_validator(mode="before")` on `BoundedSweepResultRow.cv_fpr`/`mean_fpr` mapping JSON
   `null` → `math.nan`. `model_dump_json` serializes NaN to `null`; without this, a manifest containing
   any undefined CV(FPR) was non-reloadable. Undefined (NaN) stays distinct from a genuine 0.0 — never
   coerced to zero. No epsilon floor (respects rejected-rec #6). Latent-only: the real 1620-row artifact
   has no nulls and still reloads.

2. **R5 — `src/datp/federated/strategies.py`**
   Added `ParticipationFailureReport` (frozen, slots) + `_build_participation_failure_report`. Both
   `aggregate_fit`/`aggregate_evaluate` now log a structured error (round/stage/successful/failed/
   failed_ids/reasons) then raise. Behaviour unchanged — still aborts on ANY client failure; NO retry,
   NO partial aggregation (respects rejected-rec #9). Diagnostics only.

3. **R8 — `src/datp/federated/runtime.py` + `src/datp/federated/simulation.py`**
   Added `check_object_store_capacity(object_store_mb) -> ObjectStorePreflight`: validates the existing
   config-driven `ray_object_store_mb` against observed available RAM (`get_available_ram_gb`), raising a
   clear error early instead of a cryptic Ray plasma init failure; returns observed facts. `simulation.py`
   calls it and logs a `ray object-store preflight` line. The configured memory value is NEVER altered or
   guessed (respects rejected-rec #10).

No other production behaviour was changed.

---

## 3. Test Changes (added/extended)

- R1: `tests/unit/checkpointing/test_training_protocol.py::test_canonical_regime_a_b4_is_fixed_k3`
- R2: `test_statistics.py::test_near_zero_positive_mean_is_finite`;
  `test_metric_engine.py::test_companion_dispersion_populated`;
  `test_bounded_sweep_manifest.py::test_undefined_cv_serializes_as_null_and_round_trips_to_nan`
- R3: `test_summary_selection.py::test_selection_ignores_cluster_policy_metrics`
- R4: `test_artifact_validation.py::test_non_first_client_missing_confusion_matrix_fails`
- R5: `test_strategies.py::TestFullParticipationDiagnostics` (fit ids+message; evaluate exception)
- R7: `tests/unit/data/common/test_feature_artifact_schema.py` (6 tests incl. `test_reordered_columns_fail`
  — locks the ordered-schema contract that the integration test's `set()==set()` comparison missed)
- R8: `test_runtime.py::TestObjectStoreCapacity` (fits/exceeds/equal)
- R11: `test_autoencoder.py::TestBatchNormScopeGuard` (BN-free path has no BatchNorm1d; gate is genuine);
  `test_models.py::test_canonical_config_disables_batchnorm`;
  `test_local_training.py::test_optimizer_uses_no_weight_decay`
  (complements existing `test_centralized_training.py::...weight_decay == 0.0`)

R6, R9, R10: no new test — existing coverage already complete; adding more would be redundant churn.

---

## 4. Quality Gates

- **Ruff:** clean on all changed production and test files.
- **Pyright:** 0 errors / 0 warnings on the 4 changed production files.
- **Consolidated suite** (`tests/unit/{attacks,federated,data,modeling,config,evaluation,checkpointing,
  core,validation,experiments}`): **1459 passed, 3 skipped, 1 failed** in ~355s.

### 4.1 The single failure is PRE-EXISTING and out of scope
`tests/unit/core/test_dataclass_architecture.py::...test_no_unjustified_defaults_in_src` fails. All
reported violations live in `src/datp/validation/_audit_types.py` (`_CellPanel`, `_AuditAccumulator`) —
a file NOT touched by this remediation. Verified by stashing all working-tree changes (`git stash -u`):
the test fails identically at HEAD without any of my edits. My new dataclasses
(`ParticipationFailureReport`, `ObjectStorePreflight`) do NOT appear in the violation list. This failure
is unrelated to R1–R11 and is left untouched (outside the remediation scope).

- **Exact file:** `src/datp/validation/_audit_types.py` (dataclass fields with defaults not in
  `_DEFAULTS_ALLOWLIST`).
- **Reason it remains:** pre-existing; outside the 11-ticket scope; not introduced by these changes.
- **Risk:** none introduced by this work; an existing architecture-policy debt for the audit-types module.
- **Next action (separate ticket):** either add the `_CellPanel`/`_AuditAccumulator` fields to
  `_DEFAULTS_ALLOWLIST` with documented justification, or remove the defaults.

---

## 5. Cross-Cutting Final Audits

1. **Cross-package integration:** New `ParticipationFailureReport`/`ObjectStorePreflight` are local to
   `federated/`; manifest validator local to `attacks/`. No import cycles; consolidated federated/attacks/
   data/config/checkpointing suites green.
2. **Protocol/scientific drift:** No change to baseline semantics, regime semantics, shared-encoder/
   shared-score invariants, threshold-scope isolation, CV(FPR) definition (no epsilon), coverage reporting,
   two-layer statistics, or checkpoint-selection science. B1-vs-B2 anchoring untouched.
3. **Config/manifest integrity:** R2 makes manifests strictly MORE robust (reloadable when CV undefined)
   while preserving NaN≠0.0. `ray_object_store_mb` remains config-driven; no value changed.
4. **Partial/failed-run safety:** R5 strictly improves failure observability; abort-on-any-failure
   behaviour preserved (no silent partial aggregation, no auto-retry). R8 converts a cryptic Ray OOM/init
   failure into an early, actionable error.
5. **Minimality/code quality:** 4 production files, +127 net production lines (mostly R5 report dataclass
   and R8 preflight). 8 of 11 tickets required no production change. Ruff/pyright clean.

---

## 6. Rejected-Recommendation Compliance (explicit)

This remediation did NOT, in any ticket:
- add a sigmoid/decoder output activation (decoder final layer remains raw — verified R11);
- introduce or alter BatchNorm (kept config-gated and off in the canonical config — R11);
- add speculative optimizer regularization / weight decay (all optimizers remain `weight_decay=0.0` — R11);
- treat the CP2 calibration reserve as leakage;
- turn the 4/5 paired-seed sign rule into a significance claim (`consistent`, not `significant` — R9);
- add an epsilon floor to CV(FPR) (R2);
- round JSON floats before hashing (R10);
- make checkpoint selection depend on threshold-policy metrics (R3);
- add auto-retry of failed FL clients (R5);
- set arbitrary Ray object-store memory values (R8).

---

## 7. Definition of Done

- Code/doc/scientific reality inspected per ticket: yes.
- Tickets fixed at narrowest scope or verified already-correct: yes.
- Impacted tests added/updated and passing: yes.
- Ruff/pyright clean on changed files: yes.
- Consolidated impacted suite run once: yes (1 pre-existing, out-of-scope failure documented).
- Scientific invariants preserved: yes.
- Evidence inventories: `/tmp/datp-remediation-audit/R1..R11_*.md`.

**Status: REMEDIATION COMPLETE** (with one documented pre-existing, out-of-scope test failure in
`validation/_audit_types.py`).
