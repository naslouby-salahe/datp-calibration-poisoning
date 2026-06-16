# CP2 Decision Log

Record blockers, pivots, fallback activations, and hard-stops here. Each entry:
exact blocker / decision, command or action involved, evidence, fallbacks
attempted, remaining safe work, next action.

> No blocker is resolved by prose alone — link to the real evidence path.

---

## Entries

---

## 2026-06-16 | CP2-T007 | FB1 TRIGGERED — Clean score artifacts absent; E=5 config flag

**Ticket:** CP2-T007

**Trigger:** CP2-FB1 trigger condition met. No CP2-controlled clean N-BaIoT
per-client calibration/test score artifacts exist in this repository. `outputs/`
contains only `console_logs/`.

**Evidence:**
- `outputs/` inspection: no `.parquet`, no `scoring_manifest.json`, no model
  checkpoints (2026-06-16 audit).
- `src/datp/conf/config.yaml` line 41: `local_epochs: 5` (E=5, forbidden for CP2).
- Scoring infrastructure (generation, validation, manifest) is present and correct.
- Evidence files: `_ai_tracking/audits/CP2-T007_artifact_audit.md`,
  `_ai_tracking/manifests/clean_score_artifacts.json`.

**Additional finding:** `local_epochs: 5` in `src/datp/conf/config.yaml` was missed
by the T001 scan because the rg pattern `epochs *= *5` requires `=`, but YAML
uses `:`. If training were run now, artifacts would be E=5 (rejected).

**Fallback attempted:** CP2-FB1 triggered but **NOT YET EXECUTED**.

**FB1 execution blocked by:** Phase A is read-only. Additionally, `local_epochs: 5`
must be corrected to `local_epochs: 1` before FB1 can produce valid E=1 artifacts.

**Remaining safe Phase-A work:** All other Phase-A tickets (T008–T015) are
independent of artifact existence for the code audit. They proceed as read-only.

**Next action:**
1. Phase B (T017/T022): fix `local_epochs: 1` and add FederationConfig validator.
2. After Phase B config lock: activate FB1 with explicit authorization (retraining
   authorization required per FB1 §12).
3. Phase-A confirmation #1 remains PENDING until FB1 completes.
