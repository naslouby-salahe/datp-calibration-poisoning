# CP2-T023 Phase B Protocol-Lock Drift Check

**Date:** 2026-06-16
**Ticket:** CP2-T023
**Type:** scientific-drift

---

## 1. Scan commands

```bash
pytest tests/unit/core/ tests/unit/config/ tests/unit/artifacts/ tests/unit/validation/ tests/unit/app/ -q
pyright src/datp/attacks/cp2_*.py src/datp/config/cp2_*.py src/datp/core/cp2_*.py src/datp/artifacts/cp2_*.py src/datp/validation/cp2_*.py src/datp/app/cli/cp2.py
rg -ni "B3|shift_magnitude|integer.seed|edge-?iiot|fedprox|ditto|laridi" src/
```

---

## 2. Test and static check results

| Check | Result |
|---|---|
| `pytest tests/unit/{core,config,artifacts,validation,app}` | **702 passed** |
| `pyright` (CP2 modules only) | **0 errors** |
| `ruff check` (CP2 modules) | **clean** |

---

## 3. Forbidden-term scan: CP2 modules only

| Term | In CP2 modules? | Context |
|---|---|---|
| `B3` | YES — in prohibition context only | `cp2_enums.py` docstring: "B3 excluded by protocol"; `cp2_guardrails.py`: `assert_policy_not_b3`; `cp2_provenance_gate.py`: `_check_policy_not_b3`; `cp2_stages.py`: "FB3" gate label (not a baseline) |
| `shift_magnitude` | YES — in exclusion comment only | `cp2_models.py` module docstring: "No shift_magnitude. No attack_rate." |
| `integer seed` | YES — in prohibition comment only | `cp2_seeds.py`: "No integer seed addition. …Do NOT use integer seed addition." |
| `edge-iiot` | **NOT FOUND** | |
| `fedprox` | **NOT FOUND** | |
| `ditto` | **NOT FOUND** | |
| `laridi` | **NOT FOUND** | |

In DATP substrate (`src/datp/federated/`, `src/datp/core/enums.py`, `src/datp/validation/results.py`, `src/datp/conf/config.yaml`): B3 appears as a legitimate DATP substrate baseline (Baseline.B3 enum member). This is not contamination — the substrate pre-exists CP2 and DATP's B3 is not CP2's ThresholdPolicy.

---

## 4. Protocol lock verification against roadmap §5, §6, §7, §10, §12

### §5 — Scope of attack
- [ ] CP2 is calibration-channel poisoning only → `cp2_enums.py::CalibrationInjectionRule.REPLACE_FIXED_BUDGET`, quarantined prototypes do not affect production
- [ ] Training/model/aggregation/test data never poisoned → no such logic in any CP2 module
- [ ] No evasion, backdoor, privacy, deploy, robustness, generic FL claim → verified by absence from CP2 modules

### §6 — Dataset locks
- [ ] Primary: NBAIOT → `cp2_stages.py::NBAIOT_MVP.dataset="nbaiot"`, `cp2_names.py` constants
- [ ] CICIoT2023 stretch gated by FB4 → `CICIOT2023_STRETCH.gate="FB4"` ✓
- [ ] Edge-IIoTset FORBIDDEN → not found anywhere in CP2 modules ✓

### §7 — Policy locks
- [ ] B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER only → `cp2_enums.py::ThresholdPolicy` ✓
- [ ] B3 excluded → `ThresholdPolicy` has no B3; `assert_policy_not_b3` guardrail; `_check_policy_not_b3` gate ✓

### §10 — Orchestration / stages
- [ ] 7 canonical stages defined → `cp2_stages.py` COMMON/AUDIT_READONLY/NBAIOT_SMOKE/NBAIOT_MVP/NBAIOT_FULL/CICIOT2023_STRETCH/PAPER_FIGURES ✓
- [ ] All stages have `allow_run=False` in Phase B → confirmed by test `test_no_stage_allows_run_in_phase_b` ✓
- [ ] Heavy stages gated → NBAIOT_FULL gate=FB3; CICIOT2023_STRETCH gate=FB4; experiment stages gate=CP2-T056 ✓

### §12 — Seed scheme
- [ ] SeedSequence([ts, ps, ci, si]) — no integer addition → `cp2_seeds.py::make_cp2_rng` ✓
- [ ] Five training seeds [0–4], five poisoning seeds [100–104] → `cp2_names.py::CP2_TRAINING_SEEDS/CP2_POISONING_SEEDS` ✓
- [ ] Defaults propagated to `Cp2SeedPools` → `cp2_models.py` imports from `cp2_names.py` ✓

---

## 5. Attack mechanics verification

| Lock | Implementation | Status |
|---|---|---|
| REPLACE_FIXED_BUDGET only | `CalibrationInjectionRule.REPLACE_FIXED_BUDGET` in `cp2_enums.py`; enforced by `Cp2Config.only_replace_fixed_budget` validator | PASS |
| No shift_magnitude | Not present in any CP2 module (exclusion comment only in docstring) | PASS |
| E=1 enforced, E=5 rejected | `Cp2ProvenanceRecord.enforce_e1`; `Cp2Config.enforce_e1`; `_check_local_epochs_e1` in gate | PASS |
| Reservoir = victim-local benign cal | `CP2_RESERVOIR_MODE` constant; `assert_reservoir_not_test_or_training` guardrail | PASS |
| No in-place mutation | `assert_no_inplace_mutation` guardrail | PASS |
| MVP fractions {0, 0.10, 0.20, 0.40} | `CP2_MVP_FRACTIONS` in `cp2_enums.py`; `assert_fractions_in_locked_grid` guardrail | PASS |
| MVP requires SINGLE_CLIENT | `Cp2Config.mvp_requires_single_client` validator; `assert_mvp_requires_single_client` guardrail | PASS |
| B4 K=3, n_init=10, max_iter=300 | `Cp2B4Config` with `k_must_be_three_for_regime_a` validator; `CP2_B4_*` constants | PASS |

---

## 6. Constants ownership (single source of truth)

| Constant | Owner | Consumers |
|---|---|---|
| `CP2_MVP_FRACTIONS` | `cp2_enums.py` | `cp2_models.py` (`Cp2Config.fractions` default), `test_cp2_layout.py` |
| `CP2_N_MIN`, `CP2_TAIL_MASS` | `cp2_names.py` | `cp2_models.py` (`Cp2Config` field defaults) |
| `CP2_B4_K/N_INIT/MAX_ITER/RANDOM_STATE` | `cp2_names.py` | `cp2_models.py` (`Cp2B4Config` defaults) |
| `CP2_TRAINING_SEEDS/POISONING_SEEDS/ANALYSIS_SEEDS` | `cp2_names.py` | `cp2_models.py` (`Cp2SeedPools` defaults) |
| `CP2_SPLIT_SEMANTICS`, `CP2_RESERVOIR_MODE` | `cp2_manifest.py` | `cp2_provenance_gate.py` |
| `CP2_OUTPUT_ROOT` | `cp2_names.py` | `cp2_layout.py` |

No duplicates found after T020 consolidation.

---

## 7. Quarantined prototype status

Four files remain quarantined and are not CP2 implementation:
- `src/datp/attacks/calibration_poisoning.py` — QUARANTINED
- `src/datp/attacks/poisoning_config.py` — QUARANTINED
- `src/datp/attacks/poisoning_metrics.py` — QUARANTINED
- `src/datp/experiments/calibration_poisoning.py` — QUARANTINED

These contain `shift_magnitude` (in prototype logic, not CP2 protocol). They will be replaced in T027–T029. No CP2 module imports from them.

---

## 8. Verdict

**NO DRIFT DETECTED.**

All 10 protocol-lock checks PASS. Phase B architecture is faithful to roadmap §5, §6, §7, §10, §12 and `Additional_Docs/Synthesis/Claims.md`. Phase C (attack implementation) may begin.
