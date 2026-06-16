# CP2-T048 — MVP Drift Check

**Date:** 2026-06-16
**Ticket:** CP2-T048 (scientific-drift)
**Auditor:** automated session

**Verdict: PASS — no protocol-lock drift found in the real-data MVP execution
path.** Every lock in roadmap §5–§12 that applies to the bounded MVP holds on
the real 1620-cell artifact and the code that produced it.

---

## 1. Calibration-channel-only boundary (roadmap §12 scope lock)

- `auroc_invariant == True` on all 1620/1620 manifest rows (re-confirmed from
  CP2-T046; AUROC is computed on the fixed clean test scores, never touched
  by calibration poisoning — the load-bearing check that training, model
  weights, aggregation, and test data were never attack targets).
- `mvp_run.py`'s `run_nbaiot_mvp` only ever mutates calibration-derived
  thresholds (`compute_b1_pair`/`compute_b2_pair`/`compute_b4_pair` via
  `cell_runner.py`); no path in the bounded-MVP run touches
  `client_data.train`, model weights, or `FedAvg` aggregation. Confirmed by
  inspection — `mvp_run.py`/`cell_runner.py`/`mvp_runner.py` import only
  `score_containers`, `injector`, `threshold_recompute`, `b4_recompute`,
  `metric_engine`, none of `federated.protocols.fedavg` or model modules.

## 2. E=1, shared scores, SINGLE_CLIENT, default policies, B3 absent

- `provenance.local_epochs == 1` on the manifest (re-confirmed CP2-T046).
- `target_scope` is `single_client` on all 1620 rows and at the manifest
  top level — re-verified directly against the live artifact this session
  (not just cited from T046).
- `policies` field on the manifest is exactly
  `['b1_global', 'b2_personalized', 'b4_cluster']` — re-verified directly;
  no `b3` value appears anywhere in the 1620 rows.
- `rg -ni "B3"` across `mvp_matrix.py`, `mvp_manifest.py`, `mvp_run.py`,
  `source_strategies.py`, `cell_runner.py`, `mvp_runner.py`,
  `app/cli/poison.py`, `poison_enums.py`: the only hits are prohibition-context
  docstrings (`ThresholdPolicy` docstring: "B3 ... is excluded by protocol";
  `mvp_matrix.py` docstring: "default policies (B1/B2/B4, no B3)";
  `poison.py` comment listing gate names `CP2-T043, CP2-T044, FB3, FB4` —
  `FB3`/`FB4` are fallback-register IDs, not the `B3` policy). No drift.

## 3. REPLACE_FIXED_BUDGET, victim-local, no in-place mutation, AUROC invariant

- `injection_rule == "replace_fixed_budget"` on the manifest, and
  `reservoir_mode == "victim_local_benign_cal_source_precedence_rule_2"` —
  both re-verified directly against the live artifact.
- No-in-place-mutation and victim-local-reservoir guarantees are enforced and
  unit-tested at the injector level (`tests/unit/attacks/test_injector.py`,
  23 tests, CP2-T027) and were spot-checked via `assert_no_inplace_mutation`
  at CP2-T043's one-seed diagnostics — re-run this session as part of the
  broader unit suite (§6) with zero regressions; not re-derived from the
  manifest itself (the manifest has no field for this — it is a property of
  the injector call, not the result).
- AUROC invariance: see §1.

## 4. Two-layer stats; CV(FPR)+coverage; `mu_flag_threshold` locked pre-poison

- `cv_fpr`, `mean_fpr`, `coverage_ratio`, `n_eligible` present on every row
  (re-confirmed CP2-T046; `coverage_ratio == 1.0`, `n_eligible == 9`
  throughout — no Calibration-Pending clients on N-BaIoT).
- Two-layer statistical machinery (`datp.attacks.inference`) was exercised
  fresh this session at CP2-T047 against the real manifest data (not just
  unit-tested in isolation) — seed-level aggregates (Layer 2) computed from
  per-victim, per-seed deltas (Layer 1), never treating the 9×5=45
  `(victim, seed)` pairs as 45 independent replicates. Confirmed structurally:
  `compute_seed_aggregates` takes the mean over feasible victims **per seed**,
  and `bootstrap_seed_aggregates` resamples only the resulting 5
  seed-level values.
- `mu_flag_threshold` lock ordering: re-inspected `mvp_run.py`'s
  `run_nbaiot_mvp` — `mu_flag_by_seed[training_seed] = lock_mu_flag_threshold(collection)`
  is computed inside the per-training-seed loading loop, **before**
  `enumerate_mvp_matrix(...)` is called and before any `_row_for_cell` (which
  performs the poisoning injection) executes for that seed. This is an
  architectural guarantee, not just a value coincidence — confirmed by
  reading the control flow, not only by the value match already noted in
  CP2-T046 (`{0:0.005,1:0.0049,2:0.0056,3:0.0053,4:0.005}` identical to the
  CP2-T044 stability-sweep values). Hard-stop condition "`mu_flag_threshold`
  would be set after, not before, poisoned runs" — **not triggered**.

## 5. `REGIME_A_NBAIOT` only

- `dataset == "nbaiot"` on the manifest top level and implicitly on every
  row (single dataset field, no per-row override). `mvp_run.py` hardcodes
  `regime=Regime.A` in its `load_real_score_collection` call — there is no
  code path in the bounded-MVP runner that can load CICIoT2023 or
  Edge-IIoTset; the stretch/forbidden datasets are architecturally
  unreachable from this run, not merely unused by convention.

## 6. Seed-scheme integrity (re-verified at full scale, not spot-check only)

- Re-verified `seed_record.entropy == [training_seed, poisoning_seed,
  client_idx, scope_idx]` programmatically against **all 1620 rows** this
  session (not just the CP2-T046 single spot-check): `entropy[1] !=
  poisoning_seed` count is **0/1620**. No integer-addition pattern anywhere
  in the real artifact. Hard-stop condition "integer seed addition would be
  used instead of `SeedSequence`" — **not triggered**.

## 7. Regression check (broader tests, per CLAUDE.md §5 escalation for drift tickets)

```text
pytest tests/unit/attacks tests/unit/thresholding tests/unit/statistics -q
  → 484 passed in 144.65s
pytest tests/integration/attacks/test_cp2_smoke.py -q
  → 19 passed in 5.06s
pyright src/datp/attacks
  → 0 errors, 0 warnings, 0 informations
ruff check src/datp/attacks
  → All checks passed
```

**Note (out of CP2 scope, recorded for transparency):** a bare `pytest -k
cp2_smoke -q` (full-tree discovery, no path) aborts at collection with 4
errors in `tests/e2e/{diagnostic,regime_a,regime_b,regime_c}/test_*_e2e.py`
(`ImportError: cannot import name 'SplitFilename' from 'datp.data.splits'`).
Confirmed via `git log` that neither these test files nor
`src/datp/data/splits.py` have been touched in this session or by any CP2
ticket (last touch: pre-CP2 commits `dead951`/`71f9fc5`) — this is
pre-existing DATP-substrate breakage, the same category already noted as
"8 pre-existing DATP substrate breakages out of scope" in the Phase A–D
audit-reconcile row, just in a different test directory (`tests/e2e/`) than
the 4 files the earlier `DATP-TEST-FIX` ticket repaired
(`tests/integration/...`). Not a CP2 drift; not actioned here (outside
ticket scope); flagged for whoever next touches the DATP substrate e2e
suite.

## 8. Acceptance criteria check (ticket §11)

- Drift report confirms MVP runs preserved all locks: **YES**, no violation
  found in any of §1–§6.
- `pyright`: 0 errors on the attacks surface.

**Next:** CP2-T049 (continue/stop/pivot decision) — the final gate for this
phase. T049 should weigh: this drift-clean result, CP2-T046's PASS verdict
(4 flagged-but-explained B4 anomalies), and CP2-T047's "no kill trigger
fires, one evidentiary gap on downstream-metric movement" verdict together.
