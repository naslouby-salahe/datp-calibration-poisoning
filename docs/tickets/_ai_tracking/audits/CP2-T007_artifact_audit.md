# CP2-T007 — Clean Score Artifact Discovery, Provenance & E=1 Audit

**Date:** 2026-06-16
**Ticket:** CP2-T007
**Auditor:** Phase-A read-only audit
**Verdict:** **ARTIFACTS MISSING + E=5 CONFIG FLAG → CP2-FB1 TRIGGERED**

---

## 1. Method

```bash
ls -la outputs/
find outputs/ -name "*.parquet" -o -name "*.json" -o -name "*.pt" 2>/dev/null
rg -n "E=5|local_epochs" src docs outputs 2>/dev/null     # E=5 literal scan
rg -rn "local_epochs" src/ 2>/dev/null                    # confirms E=5 in config
cat src/datp/conf/config.yaml                              # direct read
cat src/datp/validation/score_manifest.py                  # scoring infrastructure
```

---

## 2. Artifact Discovery

### Outputs directory

`outputs/` contains only `console_logs/`. **No score artifacts present.**

```
outputs/
  console_logs/
    2026-06-15_23-02-30__datp__help.log
```

- No `.parquet` files anywhere (outside `.venv/`)
- No `scoring_manifest.json` files
- No model checkpoints (`.pt` / `.pth`)
- No score cell directories (`scores/<regime>/seed_N/`)

**Verdict: Artifacts ABSENT.** CP2-FB1 trigger criterion is met.

---

## 3. E=1 Configuration Audit

### Critical finding: `local_epochs: 5` in `src/datp/conf/config.yaml`

```yaml
federation:
  convergence:
    rounds_initial: 40
    rounds_max: 150
    relative_threshold: 0.005
    window: 10
    round_timeout_s: 400.0
  local_epochs: 5        ← E=5 (forbidden for CP2)
```

`local_epochs: 5` propagates to `FederationConfig.local_epochs` (config/models.py:88)
→ `DatpClient._local_epochs` (federated/clients.py:40)
→ `local_training.train_local(epochs=…)`.

CP2 requires **E=1** for all clean artifacts. Running training with this config
would produce **E=5 artifacts, which must be rejected** (CLAUDE.md §3.1,
DATP_CP_Roadmap.md §7, README §9).

**This config must be corrected to `local_epochs: 1` before FB1 can execute.**
Phase A is read-only; this fix is deferred to Phase B (T017 config schema or
T022 scientific guardrails).

### E=5 in Python code: NONE

- `rg -ni "epochs *= *5|E=5" src/` → no matches in `.py` files
- Prior T001 scan: "No E=5 / epochs = 5 literals in src/" — confirmed for `.py`
- The YAML `local_epochs: 5` was missed by the T001 pattern (`epochs *= *5` requires
  `=` separator; YAML uses `:`). This is a new finding.

---

## 4. Scoring Infrastructure Audit (code, not artifacts)

The scoring pipeline infrastructure is **present and well-structured**:

| Module | Status |
|---|---|
| `src/datp/scoring/schema.py` | SCORE_COLUMN = "reconstruction_error"; schema version "1" |
| `src/datp/scoring/generation.py` | `compute_reconstruction_errors` batched; writes parquet |
| `src/datp/scoring/loading.py` | present |
| `src/datp/scoring/cal_loading.py` | present |
| `src/datp/validation/score_manifest.py` | full per-cell verification; hash check; sentinel check |
| `src/datp/validation/discovery.py` | `iter_score_cells`, `parse_score_cell_dir` present |
| `src/datp/evaluation/artifact_validation.py` | present |
| `src/datp/artifacts/layout.py` | `ArtifactLayout` with `checkpoint_dir` |
| `src/datp/core/provenance.py` | `git_commit`, `hash_file`, `utc_timestamp` |

Manifest fields required: `dataset`, `regime`, `seed`, `alpha`,
`expected_client_ids`, `model_checkpoint_hash`, `model_checkpoint_path`,
`expected_splits`, `actual_client_ids`, `actual_splits`, `completion_status`,
`score_column_name`, `records`.

The validation code is CP2-compatible: checks `reconstruction_error` column,
checks sentinel, verifies checkpoint hash, validates per-client split files
(calibration / test_benign / test_attack).

---

## 5. Convergence Config Audit

| Config field | Value | CP2 requirement | Status |
|---|---|---|---|
| `federation.convergence.rounds_initial` | 40 | 40 | PASS |
| `federation.convergence.rounds_max` | 150 | 150 | PASS |
| `federation.local_epochs` | **5** | **1** | **FAIL** |
| `model.epochs` | 200 | (AE internal; not E=) | N/A |
| `experiment.seeds` | [0,1,2,3,4] | [0,1,2,3,4] | PASS |
| `threshold.n_min` | 100 | 100 | PASS |
| `threshold.b4_k_regime_a` | 3 | 3 | PASS |
| `threshold.b4_n_init` | 10 | 10 | PASS |
| `threshold.b4_random_state` | 42 | 42 | PASS |
| `threshold.q` | 0.95 | p95 | PASS |

---

## 6. FB1 Trigger Decision

**Trigger met:** No CP2-controlled clean N-BaIoT per-client calibration/test score
artifacts exist in this repository.

**FB1 status:** TRIGGERED (see CP2_DECISION_LOG.md).

**FB1 execution blocked by:** `local_epochs: 5` config must be corrected to
`local_epochs: 1` in Phase B before any retraining. Phase A is read-only.

**FB1 safe actions for Phase A:**
- Document absence of artifacts (this file)
- Write decision record
- Write provenance evidence file (manifests/)
- No retraining

---

## 7. Phase-A Confirmation #1

| Check | Result |
|---|---|
| Artifacts present | NO — ABSENT |
| Artifacts E=1 | CANNOT CONFIRM (no artifacts + config is E=5) |
| Artifacts CP2-generated | CANNOT CONFIRM (no artifacts) |
| Artifacts have DATP split semantics | CANNOT CONFIRM (no artifacts) |
| Artifacts have per-client calibration scores | CANNOT CONFIRM (no artifacts) |
| Scoring infrastructure ready | YES (code present, correct schema) |
| No E=5 in Python code | YES |
| Config E lock | FAIL (`local_epochs: 5` must be fixed to 1 in Phase B) |
| FB1 triggered | YES |

**Phase-A Confirmation #1: PENDING** (requires FB1 completion post Phase B config fix)

---

## 8. Phase B Actions Required

1. Fix `src/datp/conf/config.yaml` `local_epochs: 5` → `local_epochs: 1` (T017/T022).
2. Add a Pydantic validator to `FederationConfig` that rejects `local_epochs != 1` for
   CP2 runs (scientific guardrail, T022).
3. After Phase B, activate FB1 with authorization: retrain E=1, write artifacts +
   manifest, verify with `verify_all_score_cells`.

---

## 9. Evidence Paths

- `outputs/` inspection: no artifacts found (this session, 2026-06-16)
- `src/datp/conf/config.yaml`: `local_epochs: 5` (line 41)
- `src/datp/validation/score_manifest.py`: scoring infrastructure confirmed
- Decision record: `_ai_tracking/decisions/CP2_DECISION_LOG.md`
- Provenance evidence: `_ai_tracking/manifests/clean_score_artifacts.json`
