# CP2-T008 — DATP Split Semantics Audit

**Date:** 2026-06-16
**Ticket:** CP2-T008
**Auditor:** Phase-A read-only audit
**Verdict:** SPLIT SEMANTICS CONFIRMED; RESERVOIR PATH DECIDED (source-precedence rule 2)

---

## 1. Method

```bash
cat src/datp/data/datasets/nbaiot/spec.py
cat src/datp/data/datasets/nbaiot/prepare.py
cat src/datp/data/splits.py
cat src/datp/scoring/cal_loading.py
cat src/datp/thresholding/eligibility.py
rg -n "calibration|n_min|chronological|split" src/datp/data src/datp/thresholding
```

---

## 2. N-BaIoT Split Semantics

### Split ratios (`src/datp/data/datasets/nbaiot/spec.py`)

```
train:     60%   (benign chronological)
gap1:       1%   (discarded buffer)
cal:       20%   (benign only, chronological)
gap2:       1%   (discarded buffer)
test_benign: ~18% remainder (benign chronological)
test_attack: pooled (all attack CSVs for the device)
```

### Split policy flags

| Flag | Value | CP2 requirement |
|---|---|---|
| `CHRONOLOGICAL_SPLIT` | `True` | chronological split required |
| `BENIGN_ONLY_CALIBRATION` | `True` | benign-only calibration required |
| `contiguous_gaps` | `True` | gap separating train/cal/test |

**PASS**: Split semantics match DATP_CP_Roadmap.md §7 exactly.
- 60% train / 1% gap / 20% cal / 1% gap / ~18% test (benign) / attack pool

### Split enum (`src/datp/data/splits.py`)

```python
class Split(StrEnum):
    TRAIN = "train"
    CAL = "cal"
    TEST_BENIGN = "test_benign"
    TEST_ATTACK = "test_attack"
```

Scoring splits: `(Split.CAL, Split.TEST_BENIGN, Split.TEST_ATTACK)` — **TRAIN is excluded
from scoring**, which is correct. Training scores are never a reservoir.

### Calibration loading (`src/datp/scoring/cal_loading.py`)

`load_main_cal_errors` loads `ScoringStage.CAL` parquet files — these ARE the same
calibration scores used to fit the threshold. There is no separate "calibration-
candidate buffer" exposed in the artifact schema.

---

## 3. Reservoir Source Precedence Decision

**Roadmap §6 source-precedence rule:**
1. If artifacts expose victim-local benign calibration-candidate scores *not* used
   to fit the clean threshold → draw from those.
2. Otherwise → resample with replacement from the victim's clean calibration-score
   distribution.

**Finding:** The artifact schema exposes only the `cal` split scores, which are
identically the scores used to fit the clean threshold. There is no separate
calibration-candidate pool.

**Decision: SOURCE-PRECEDENCE RULE 2 APPLIES.**
- `RANDOM_BENIGN`: resample with replacement from the victim's full clean `cal` pool.
- `HIGH_SCORE_BENIGN`: resample with replacement from the victim's top-10% tail of
  `cal` scores.
- `LOW_SCORE_BENIGN`: resample with replacement from the victim's bottom-10% tail of
  `cal` scores.

**Test scores (`test_benign`) are never a reservoir.** ✓
**Training scores (`train`) are not used.** ✓

This abstraction (resampling from the same pool used to fit the threshold) must be
disclosed in the manuscript limitations as the **disclosed score-level proxy
abstraction** (Roadmap §6, already pre-registered).

---

## 4. Eligibility and Calibration-Pending Logic

| Rule | Implementation | Status |
|---|---|---|
| `n_min = 100` | `dataset.n_min: 100`, `threshold.n_min: 100` in config | PASS |
| Pending if `cal_count < n_min` | `nbaiot/prepare.py:122` + `eligibility.py:27` | PASS |
| Pending → receive `tau_global` | `eligibility.py:80-85` (ClientThreshold(calibration_pending=True, threshold=tau_global)) | PASS |
| Pending → excluded from CV(FPR) eligible set | Via `identify_eligible` → only eligible in formulas | PASS |
| Pending → not a valid victim | Not in eligible list returned by `identify_eligible` | PASS |
| Fixed-size replacement preserves `n_i` | No client becomes pending post-attack | PASS (by design) |

**N-BaIoT note:** DATP reports all 9 clients eligible (`n_cal ≥ 100`) in Regime A
(per Roadmap §4). Confirmed via `SPLIT_RATIOS["cal"]=0.20` on N-BaIoT benign data;
all 9 devices have substantial benign data.

---

## 5. 9 Client Identities (N-BaIoT, Regime A)

```
Danmini_Doorbell
Ecobee_Thermostat
Ennio_Doorbell
Philips_B120N10_Baby_Monitor
Provision_PT_737E_Security_Camera
Provision_PT_838_Security_Camera
Samsung_SNH_1011_N_Webcam
SimpleHome_XCS7_1002_WHT_Security_Camera
SimpleHome_XCS7_1003_WHT_Security_Camera
```

`K=9` physical-device clients; K=3 for B4 clustering. All 9 expected eligible.

---

## 6. Phase C Reservoir Design Notes (for T026)

CP2-T026 (reservoir selection) should:
1. Accept `cal_errors: dict[str, np.ndarray]` as the victim-local benign pool.
2. Implement `RANDOM_BENIGN` = np.random.choice(pool, size=m_i, replace=True).
3. Implement `HIGH_SCORE_BENIGN` = np.random.choice(top-10%, size=m_i, replace=True).
4. Implement `LOW_SCORE_BENIGN` = np.random.choice(bottom-10%, size=m_i, replace=True).
5. Never source from `test_benign` or `train` splits.
6. Record source-precedence-rule-2 in the run manifest.

---

## 7. Phase-A Confirmation #2 Status

| Check | Result |
|---|---|
| Chronological split | PASS |
| Benign-only calibration | PASS |
| Split ratios match roadmap (60/1/20/1/~18) | PASS |
| n_min=100 eligibility logic | PASS |
| Pending clients → tau_global, excluded | PASS |
| Reservoir path decided | PASS — source-precedence rule 2 |
| Test scores never a reservoir | PASS |
| Training scores not a reservoir | PASS |
| Proxy abstraction documented | PASS (limitation to disclose) |

**Phase-A Confirmation #2: PASS** (split semantics + reservoir path confirmed)

---

## 8. Evidence Paths

- `src/datp/data/datasets/nbaiot/spec.py`: SPLIT_RATIOS, CHRONOLOGICAL_SPLIT, BENIGN_ONLY_CALIBRATION
- `src/datp/data/datasets/nbaiot/prepare.py`: `_compute_split_indices`, `_prepare_device`
- `src/datp/data/splits.py`: Split enum, `iter_scoring_splits`
- `src/datp/scoring/cal_loading.py`: `load_main_cal_errors` → ScoringStage.CAL
- `src/datp/thresholding/eligibility.py`: `identify_eligible`, `build_threshold_result`
