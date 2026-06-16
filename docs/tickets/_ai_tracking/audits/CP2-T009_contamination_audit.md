# CP2-T009 — Journal-Contamination & Forbidden-Scope Audit

**Date:** 2026-06-16
**Ticket:** CP2-T009
**Auditor:** Phase-A read-only audit
**Verdict:** NO CONTAMINATION IN CP2-RELEVANT CODE PATHS; two pre-existing DATP
substrate items require Phase B isolation (non-blocking).

---

## 1. Method

```bash
rg -ni "edge-?iiot|fedprox|ditto|fedrep|fedper|laridi|fedstatsbenign|conformal|temporal.recalibration|journal" src tests docs/tickets 2>/dev/null
rg -rni "E=5|epochs.*=.*5" src
rg -n "B3|Baseline" src/datp/core/enums.py
rg -n "conformal" src/
rg -n "B3|conformal" src/datp/attacks/
```

---

## 2. Forbidden-scope scan — `src/` and `tests/`

### 2.1 Forbidden comparators and algorithms

| Term | Result in src/ | Result in tests/ |
|---|---|---|
| `edge-?iiot` | 0 matches | 0 matches |
| `fedprox` | 0 matches | 0 matches |
| `ditto` | 0 matches | 0 matches |
| `fedrep` | 0 matches | 0 matches |
| `fedper` | 0 matches | 0 matches |
| `laridi` | 0 matches | 0 matches |
| `fedstatsbenign` | 0 matches | 0 matches |
| `temporal.recalibration` | 0 matches | 0 matches |

**PASS**: All forbidden comparators/algorithms absent from `src/` and `tests/`.

### 2.2 E=5 in Python code

`rg -rni "E=5|epochs.*=.*5" src` → no matches in `.py` files.
**PASS**: No E=5 hardcode in Python.
(The `local_epochs: 5` in `config.yaml` was flagged in T007; not a `.py` issue.)

---

## 3. Substrate items requiring Phase B isolation

### 3.1 `conformal_threshold` in `src/datp/thresholding/thresholds.py`

**Present:** `def conformal_threshold(errors, alpha)` at line 46.

**Status: DATP substrate, NOT wired to CP2 policy paths.**

`derive_threshold` dispatches only to B1/B2/B3/B4 strategy modules using
`percentile_threshold` (not `conformal_threshold`). The function exists but is
unreachable from any CP2 threshold policy path.

**CP2 policy lock:** CP2 policies {B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER} must never
call `conformal_threshold`. This is currently satisfied by the substrate design.

**Phase B action (T016/T022):** The new CP2 `ThresholdPolicy` enum and guardrails
must explicitly exclude conformal paths. Consider quarantining or marking
`conformal_threshold` as journal-only in Phase C cleanup.

### 3.2 `B3` in `src/datp/core/enums.py`

**Present:** `Baseline.B3 = "b3"` in `REGIME_BASELINES[Regime.A]` and
`MAIN_BODY_BASELINES`.

**Status: DATP substrate enum, NOT the CP2 `ThresholdPolicy` enum.**

CP2's `ThresholdPolicy` enum (to be created in T016) must be `{B1_GLOBAL,
B2_PERSONALIZED, B4_CLUSTER}` — B3 must NOT appear in it. The existing DATP
`Baseline` enum is substrate and will not be replaced; CP2 creates a parallel
CP2-specific enum.

**Phase B action (T016):** Create `ThresholdPolicy` enum without B3; tests must
assert B3 is excluded from CP2 runs.

### 3.3 "journal" string in DATP substrate module docstrings

**Present in:**
- `src/datp/checkpointing/__init__.py`: "Journal checkpoint protocol helpers."
- `src/datp/app/cli/checkpoint_protocol.py`: "Journal checkpoint protocol commands."

**Context:** "journal" here refers to DATP's internal checkpoint-protocol naming
(the `CheckpointProtocolMode` enum), NOT the journal-extension research scope
(which would contain Edge-IIoTset/FedProx etc.). These are DATP substrate modules
with no journal-extension content.

**Status: NOT a contamination.** No action required in Phase A.

---

## 4. Attacks module check

`rg -n "B3|conformal" src/datp/attacks/` → 0 matches.

The legacy CP2 prototype in `src/datp/attacks/` does not reference B3 or conformal
thresholding. **CLEAN.**

---

## 5. CICIoT2023 scope check

`src/datp/data/datasets/ciciot2023/` exists as DATP substrate for Regime B.
This is NOT a contamination — CICIoT2023 is the designated stretch regime (CP2-FB4-
gated). Its presence as DATP substrate is acceptable; CP2 code must not reference it
in default policy paths. Stretch is addressed in Phase F (T054/FB4).

---

## 6. Summary verdict

| Check | Result |
|---|---|
| Edge-IIoTset absent | PASS |
| FedProx/Ditto/FedRep/FedPer/Laridi/FedStatsBenign absent | PASS |
| Temporal recalibration absent | PASS |
| conformal_threshold not wired to CP2 policies | PASS (substrate only) |
| B3 not in CP2 policy enum (future) | N/A — Phase B will create correct enum |
| B3 absent from attacks/ | PASS |
| E=5 in .py code | PASS (none) |
| journal string in module docstring = checkpoint protocol | NOT contamination |
| CICIoT2023 as DATP substrate | PASS — stretch, gated |

**Phase A Confirmation #3: PASS** (no journal-extension contamination in CP2-relevant paths)

---

## 7. Phase B Required Actions (non-blocking for Phase A)

1. T016: Create `ThresholdPolicy` enum `{B1_GLOBAL, B2_PERSONALIZED, B4_CLUSTER}`;
   assert B3 excluded.
2. T022: Scientific guardrails must ensure no CP2 run dispatches to `conformal_threshold`
   or B3 through the CP2 policy path.
3. Phase C or cleanup ticket: quarantine `conformal_threshold` from CP2 imports
   (mark as DATP-only / journal-only).

---

## 8. Evidence Paths

- `src/datp/core/enums.py`: Baseline enum, REGIME_BASELINES (B3 present, DATP only)
- `src/datp/thresholding/thresholds.py`: `conformal_threshold` defined but not wired
- `src/datp/attacks/` scan: no B3/conformal references
- Prior T001 audit: confirmed no Edge-IIoTset/FedProx/etc. in src/
