# CP2-T040 — Smoke & Test Consolidation Checkpoint

**Date:** 2026-06-16
**Ticket:** CP2-T040 (refactor / test-suite consolidation)
**Auditor:** automated session
**Verdict: PASS — CP2 test suite is consolidated; no hidden skips/xfails mask CP2
failures; CP2 smoke is CPU-only and real-data-independent.**

---

## 1. Skip / xfail / commented-test audit

Command:
```
rg -n "@pytest.mark.skip|xfail|# def test_|pytest.skip" tests
```

**Result:** 0 matches in any CP2 test (`tests/unit/attacks`, `tests/integration/attacks`,
`tests/unit/statistics`, `tests/unit/thresholding`, `tests/unit/evaluation`). The CP2
synthetic smoke suite (`tests/integration/attacks/test_cp2_smoke.py`) contains **no**
skip, xfail, or commented-out test — every invariant is asserted unconditionally.

All `pytest.skip` calls are in **DATP substrate** tests, outside CP2 scope, and are
justified real-data / hardware gates (allowed by CP2-T040 §12):

| File | Skip reason | Justification |
|---|---|---|
| `tests/e2e/conftest.py:30,37,64,74` | N-BaIoT / CICIoT raw data not available | real-data gate; CP2 smoke never needs raw data |
| `tests/unit/experiments/test_sweep.py:118,136` | checkpoint protocol not in base YAML | DATP config gate |
| `tests/unit/checkpointing/test_training_protocol.py:65` | checkpoint protocol not in base YAML | DATP config gate |
| `tests/unit/modeling/test_centralized_training.py:67` | CUDA not available | DATP GPU training gate |
| `tests/integration/data/ciciot2023/test_data_ciciot.py:101,175,247,282,309` | sample too small / dir missing | DATP data-prep gates |

None of these gate a CP2 calibration-poisoning invariant. No skip hides a CP2 failure.

---

## 2. CUDA / GPU / real-data audit (CP2 surface)

Command:
```
rg -ni "cuda|gpu|real data|outputs/conference_calibration_poisoning" tests src/datp/testsupport
```

**Result for CP2 surface:** the only matches inside CP2 files
(`src/datp/testsupport/synthetic_scores.py`, `src/datp/testsupport/cp2_smoke_harness.py`,
`tests/integration/attacks/test_cp2_smoke.py`) are **docstrings asserting** "CPU-only,
deterministic, no real data". Zero CUDA/GPU calls, zero real-data reads in the CP2
smoke path.

All other CUDA/GPU matches are DATP substrate (`tests/unit/federated`,
`tests/unit/modeling`, `tests/unit/models`, `tests/unit/core/test_device.py`,
`tests/unit/scoring`, `tests/unit/config`, `tests/integration/scoring`,
`tests/integration/federated`) — they exercise the FL training/scoring substrate, not
the calibration-channel attack. Out of CP2 scope.

**Conclusion:** the smoke harness is CPU-only and real-data-independent (roadmap §10
invariant "outputs in temp only" + the agent-prompt CPU-only/no-real-data rule).

---

## 3. Fixture consolidation

CP2 synthetic fixtures are already centralized:

- `src/datp/testsupport/synthetic_scores.py` — single home for synthetic per-client
  score generators (eligible / Calibration-Pending / degenerate-tail builders).
- `src/datp/testsupport/cp2_smoke_harness.py` (new, CP2-T038/T039) — single
  orchestration layer wiring the full pipeline; the smoke test imports from it rather
  than re-deriving pipeline glue.

No duplicate CP2 fixture builders exist. `tests/fixtures/payloads.py` is DATP substrate
(unrelated to CP2 calibration scores). No consolidation action required.

**Observation (out of scope, not actioned):** DATP substrate has a duplicated
`test_cuda_placement.py` under both `tests/unit/modeling/` and `tests/unit/models/`.
This is pre-existing DATP substrate, unrelated to CP2; left untouched (no
backward-compat obligation, but also not a CP2 artifact).

---

## 4. Behavior-vs-mock check

The CP2 smoke suite uses **no mocks**. Every assertion runs the real pipeline
(reservoir → injector → B1/B2/B4 recompute → metric engine → inference → manifest)
over real NumPy arrays and the real scikit-learn k-means in B4. Assertions are on
observable behavior (threshold shifts, cardinality, CV(FPR), decomposition identity,
manifest round-trip), not on call spies.

---

## 5. Dependency hygiene fix (carried from CP2-T038)

`src/datp/attacks/inference.py` imported `statsmodels` at module top level but
`statsmodels` was undeclared in `pyproject.toml` and uninstalled — `test_inference.py`
did not collect. Installed statsmodels 0.14.6 and declared it in `pyproject.toml`
dependencies. See decision log 2026-06-16 (CP2-T038 statsmodels entry). After the fix
`tests/unit/attacks/test_inference.py` collects and passes.

---

## 6. Test results

- `tests/integration/attacks/test_cp2_smoke.py` — **19 passed**.
- `tests/unit/attacks` + `tests/integration/attacks` — **301 passed**.
- CP2-relevant broad suite (`tests/unit/{attacks,statistics,thresholding,evaluation,
  core,config,artifacts,validation}` + `tests/integration/attacks`) — **1241 passed**.
- `pyright` on changed files (`cp2_smoke_harness.py`, `test_cp2_smoke.py`) — 0 errors.
- `ruff --select E,F` on changed files — clean.

### Collection-error reconciliation

Full `pytest tests/unit tests/integration --collect-only` initially reported **1845
collected, 4 errors** (down from 8 — the statsmodels fix in §5 resolved the
inference-import failures). The remaining 4 were **pre-existing DATP substrate** API
drift. **All 4 were subsequently repaired** (user request, post-T041); collection is
now **1878 collected, 0 errors**.

| File | Cause | Fix |
|---|---|---|
| `tests/integration/data/nbaiot/test_data_nbaiot.py` | `GAP1_KEY`/`GAP2_KEY`/`SplitFilename` removed; `_compute_split_indices` now returns a dict | local gap-key consts; `filename_for_split(Split.X)`; dict subscript access |
| `tests/integration/data/ciciot2023/test_data_ciciot.py` | `SplitFilename` removed | `filename_for_split(Split.X)` |
| `tests/integration/data/regime_c/test_data_regime_c.py` | `SplitFilename` removed | `filename_for_split(Split.X)` |
| `tests/integration/diagnostic/test_prepare_load_path_consistency.py` | `datp.baselines.common.data_loading` relocated | import from `datp.federated.data_loading`; `device=torch.device("cpu")` |

These were test-only updates to the current source API (no source backward-compat
shims, per CLAUDE.md). After the fix: 33 tests in the 4 modules pass; 0 new ruff
errors introduced (3 pre-existing E501 remain in an untouched method). See progress
log entry "DATP-TEST-FIX". CP2 smoke suite re-run green (19 passed) — no regression.

---

## 7. Gate

CP2 test suite consolidated; no hidden skips/xfails; CP2 smoke CPU-only and
real-data-independent; fixtures centralized. **CP2-T040 COMPLETE.**
